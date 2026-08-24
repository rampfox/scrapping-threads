"""
Threads data parser.
Extracts post data from Threads page HTML and hidden JSON.
Inspired by scrapfly/scrapfly-scrapers threads-scraper approach.
"""
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger


def parse_thread_post(data: Dict) -> Optional[Dict]:
    """
    Parse a single thread post from Threads JSON data structure.
    Threads embeds post data in various JSON formats within the page.
    """
    try:
        post = data.get("post") or data.get("node", {}).get("thread_items", [{}])[0].get("post") or data
        
        if not post:
            return None

        # Extract user info
        user = post.get("user", {})
        username = user.get("username", "")
        if not username:
            return None

        # Extract text content
        caption = post.get("caption", {})
        text = ""
        if isinstance(caption, dict):
            text = caption.get("text", "")
        elif isinstance(caption, str):
            text = caption

        # Extract timestamp
        taken_at = post.get("taken_at", 0)
        posted_at = None
        if taken_at:
            try:
                if isinstance(taken_at, (int, float)):
                    posted_at = datetime.fromtimestamp(taken_at)
                elif isinstance(taken_at, str):
                    posted_at = datetime.fromisoformat(taken_at.replace("Z", "+00:00"))
            except (ValueError, OSError):
                pass

        # Extract images
        images = []
        carousel = post.get("carousel_media", [])
        if carousel:
            for media in carousel:
                candidates = media.get("image_versions2", {}).get("candidates", [])
                if candidates and len(candidates) > 1:
                    images.append(candidates[1].get("url", ""))
                elif candidates:
                    images.append(candidates[0].get("url", ""))

        # Single image
        if not images:
            single_candidates = post.get("image_versions2", {}).get("candidates", [])
            if single_candidates:
                images.append(single_candidates[0].get("url", ""))

        # Extract videos
        videos = []
        video_versions = post.get("video_versions", [])
        if video_versions:
            videos = list(set(v.get("url", "") for v in video_versions if v.get("url")))

        # Build post code/URL
        code = post.get("code", "")
        url = f"https://www.threads.net/@{username}/post/{code}" if code else ""

        result = {
            "thread_id": str(post.get("id", "") or post.get("pk", "")),
            "code": code,
            "username": username,
            "display_name": user.get("full_name", username),
            "user_pic": user.get("profile_pic_url", ""),
            "is_verified": user.get("is_verified", False),
            "content": text,
            "posted_at": posted_at,
            "url": url,
            "like_count": post.get("like_count", 0),
            "reply_count": (
                post.get("text_post_app_info", {}).get("direct_reply_count", 0)
                if isinstance(post.get("text_post_app_info"), dict) else 0
            ),
            "images": [img for img in images if img],
            "videos": videos,
        }

        return result

    except Exception as e:
        logger.error(f"Error parsing thread post: {e}")
        return None


def extract_hidden_json(html: str) -> List[Dict]:
    """
    Extract hidden JSON data from Threads page HTML.
    Threads embeds data in script tags with __require and other patterns.
    """
    results = []

    try:
        # Pattern 1: Look for JSON data in script tags
        # Threads uses various script formats to embed data
        script_patterns = [
            r'<script[^>]*>.*?requireLazy\(\["RelayPrefetchedStreamCache"\],\s*function\(m\)\s*\{m\.prefetchQuery\((.*?)\)\}\);.*?</script>',
            r'"result":\s*(\{.*?"data":\s*\{.*?"searchResults".*?\})',
            r'"thread_items":\s*(\[.*?\])',
        ]

        for pattern in script_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    results.append(data)
                except json.JSONDecodeError:
                    # Try to fix common JSON issues
                    try:
                        # Sometimes the JSON is nested in the middle
                        cleaned = match.strip()
                        if cleaned.startswith("{") or cleaned.startswith("["):
                            data = json.loads(cleaned)
                            results.append(data)
                    except json.JSONDecodeError:
                        pass

        # Pattern 2: Look for __require data
        require_pattern = r'__require\("ScheduledServerJS"\)\.handle\((.*?)\);'
        for match in re.findall(require_pattern, html, re.DOTALL):
            try:
                data = json.loads(match)
                results.append(data)
            except json.JSONDecodeError:
                pass

        # Pattern 3: Search for data in JSON-LD or embedded data
        json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
        for match in re.findall(json_ld_pattern, html, re.DOTALL):
            try:
                data = json.loads(match)
                results.append(data)
            except json.JSONDecodeError:
                pass

    except Exception as e:
        logger.error(f"Error extracting hidden JSON: {e}")

    return results


def find_posts_in_data(data: Any, posts: List[Dict] = None) -> List[Dict]:
    """
    Recursively search through nested JSON data to find thread posts.
    Uses nested lookup approach to find post objects regardless of depth.
    """
    if posts is None:
        posts = []

    if isinstance(data, dict):
        # Check if this is a post object
        if "post" in data and isinstance(data["post"], dict):
            post = data["post"]
            if "user" in post and "caption" in post:
                parsed = parse_thread_post(data)
                if parsed and parsed.get("thread_id"):
                    posts.append(parsed)

        # Check for thread_items array
        if "thread_items" in data and isinstance(data["thread_items"], list):
            for item in data["thread_items"]:
                find_posts_in_data(item, posts)

        # Check for edges/nodes (GraphQL pattern)
        if "edges" in data and isinstance(data["edges"], list):
            for edge in data["edges"]:
                node = edge.get("node", {})
                find_posts_in_data(node, posts)

        # Recurse into all dict values
        for value in data.values():
            if isinstance(value, (dict, list)):
                find_posts_in_data(value, posts)

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                find_posts_in_data(item, posts)

    return posts


def parse_search_results(data: Dict) -> List[Dict]:
    """
    Parse Threads search results from XHR response data.
    """
    posts = []

    try:
        # Navigate through the search result structure
        search_results = (
            data.get("data", {})
            .get("xdt_api__v1__feed__text_post_app_search_connection", {})
            .get("edges", [])
        )

        if not search_results:
            # Try alternative paths
            search_results = (
                data.get("data", {})
                .get("searchResults", {})
                .get("edges", [])
            )

        for edge in search_results:
            node = edge.get("node", {})
            thread_items = node.get("thread_items", [])
            for item in thread_items:
                parsed = parse_thread_post(item)
                if parsed and parsed.get("thread_id"):
                    posts.append(parsed)

    except Exception as e:
        logger.error(f"Error parsing search results: {e}")

    # Also try recursive approach as fallback
    if not posts:
        posts = find_posts_in_data(data)

    return posts


def parse_profile_posts(data: Dict) -> List[Dict]:
    """
    Parse posts from a Threads user profile page data.
    """
    posts = []

    try:
        # Profile threads are usually in threads[] array
        threads = data.get("threads", [])
        for thread in threads:
            thread_items = thread.get("thread_items", [])
            for item in thread_items:
                parsed = parse_thread_post(item)
                if parsed and parsed.get("thread_id"):
                    posts.append(parsed)
    except Exception as e:
        logger.error(f"Error parsing profile posts: {e}")

    # Fallback to recursive search
    if not posts:
        posts = find_posts_in_data(data)

    return posts
