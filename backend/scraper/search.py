"""
Threads search implementation using logged-in browser session.
Captures XHR responses to extract search results data.
"""
import asyncio
import json
from typing import List, Dict, Optional
from loguru import logger
from backend.scraper.threads_parser import parse_search_results, find_posts_in_data
from backend.scraper.stealth import simulate_human_behavior, random_scroll


class ThreadsSearcher:
    """
    Performs keyword searches on Threads using Playwright browser.
    Captures API responses via XHR interception.
    """

    def __init__(self):
        self._captured_responses: List[Dict] = []

    async def search_keyword(self, page, keyword: str, max_results: int = 50) -> List[Dict]:
        """
        Search for a keyword on Threads and return parsed results.
        Requires a logged-in session.
        """
        self._captured_responses = []
        posts = []

        try:
            logger.info(f"Searching Threads for keyword: '{keyword}'")

            # Setup XHR response capture
            page.on("response", self._capture_response)

            # Navigate to Threads search
            search_url = f"https://www.threads.net/search?q={keyword}&serp_type=default"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Simulate human behavior
            await simulate_human_behavior(page, duration=2.0)

            # Scroll to load more results
            scroll_count = min(5, max_results // 10)
            for i in range(scroll_count):
                await random_scroll(page, count=2)
                await asyncio.sleep(2)

                # Check if we have enough results
                current_count = len(self._extract_posts_from_captured())
                if current_count >= max_results:
                    break

            # Also try to extract from page HTML as fallback
            try:
                page_content = await page.content()
                from backend.scraper.threads_parser import extract_hidden_json
                hidden_data = extract_hidden_json(page_content)
                for data in hidden_data:
                    found = find_posts_in_data(data)
                    posts.extend(found)
            except Exception as e:
                logger.debug(f"HTML extraction fallback: {e}")

            # Extract posts from captured XHR responses
            xhr_posts = self._extract_posts_from_captured()
            posts.extend(xhr_posts)

            # Deduplicate by thread_id
            seen_ids = set()
            unique_posts = []
            for post in posts:
                tid = post.get("thread_id")
                if tid and tid not in seen_ids:
                    seen_ids.add(tid)
                    post["keyword"] = keyword
                    unique_posts.append(post)

            logger.info(f"Found {len(unique_posts)} unique posts for keyword '{keyword}'")
            return unique_posts[:max_results]

        except Exception as e:
            logger.error(f"Search error for keyword '{keyword}': {e}")
            return posts

        finally:
            # Remove event listener
            try:
                page.remove_listener("response", self._capture_response)
            except Exception:
                pass

    async def _capture_response(self, response) -> None:
        """Capture relevant API responses from Threads."""
        try:
            url = response.url

            # Filter for Threads API endpoints that contain post data
            api_indicators = [
                "api/v1/text_feed",
                "api/v1/feed",
                "graphql",
                "text_post_app_search",
                "search",
            ]

            if any(indicator in url for indicator in api_indicators):
                content_type = response.headers.get("content-type", "")
                if "json" in content_type or "javascript" in content_type:
                    try:
                        body = await response.json()
                        self._captured_responses.append(body)
                        logger.debug(f"Captured API response from: {url[:80]}")
                    except Exception:
                        # Try text parsing
                        try:
                            text = await response.text()
                            if text.startswith("{") or text.startswith("["):
                                body = json.loads(text)
                                self._captured_responses.append(body)
                        except Exception:
                            pass
        except Exception:
            pass  # Silently ignore capture errors

    def _extract_posts_from_captured(self) -> List[Dict]:
        """Extract posts from all captured API responses."""
        all_posts = []

        for response_data in self._captured_responses:
            try:
                # Try search results format
                posts = parse_search_results(response_data)
                all_posts.extend(posts)
            except Exception:
                try:
                    # Try generic recursive extraction
                    posts = find_posts_in_data(response_data)
                    all_posts.extend(posts)
                except Exception:
                    pass

        return all_posts


# Singleton
threads_searcher = ThreadsSearcher()
