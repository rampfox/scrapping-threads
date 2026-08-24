"""
Browser stealth configuration for Playwright.
Removes automation detection flags and injects realistic browser properties.
"""
import random
from typing import Optional
from loguru import logger


# Stealth JavaScript injections to evade bot detection
STEALTH_SCRIPTS = [
    # 1. Remove navigator.webdriver flag
    """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });
    """,

    # 2. Override navigator.plugins to look like a real browser
    """
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const plugins = [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
                { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
            ];
            plugins.length = 3;
            return plugins;
        },
    });
    """,

    # 3. Override navigator.languages
    """
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en', 'id'],
    });
    """,

    # 4. Override permissions API
    """
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    """,

    # 5. Spoof chrome runtime
    """
    window.chrome = {
        runtime: {
            onConnect: { addListener: function() {} },
            onMessage: { addListener: function() {} },
        },
        loadTimes: function() { return {}; },
        csi: function() { return {}; },
    };
    """,

    # 6. Override WebGL vendor/renderer
    """
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return getParameter.call(this, parameter);
    };
    """,

    # 7. Override connection type
    """
    Object.defineProperty(navigator, 'connection', {
        get: () => ({
            effectiveType: '4g',
            rtt: 50,
            downlink: 10,
            saveData: false,
        }),
    });
    """,

    # 8. Override hardware concurrency
    """
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8,
    });
    """,

    # 9. Override device memory
    """
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8,
    });
    """,

    # 10. Canvas fingerprint noise
    """
    const toDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        if (type === 'image/png' || type === undefined) {
            const context = this.getContext('2d');
            if (context) {
                const pixel = context.getImageData(0, 0, 1, 1);
                pixel.data[0] = pixel.data[0] ^ (Math.random() * 2 | 0);
                context.putImageData(pixel, 0, 0);
            }
        }
        return toDataURL.apply(this, arguments);
    };
    """,
]


async def apply_stealth(page) -> None:
    """
    Apply all stealth scripts to a Playwright page.
    Should be called before navigating to any page.
    """
    logger.debug("Applying stealth scripts to browser page")

    for script in STEALTH_SCRIPTS:
        await page.add_init_script(script)

    logger.debug(f"Applied {len(STEALTH_SCRIPTS)} stealth scripts")


async def simulate_human_behavior(page, duration: float = 2.0) -> None:
    """
    Simulate human-like behavior on the page.
    Includes random scrolling, mouse movements, and pauses.
    """
    import asyncio

    # Random scroll
    scroll_amount = random.randint(100, 500)
    await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
    await asyncio.sleep(random.uniform(0.3, 0.8))

    # Random mouse movement (Bezier-like)
    viewport = page.viewport_size or {"width": 1920, "height": 1080}
    for _ in range(random.randint(2, 5)):
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.1, 0.4))

    # Random pause
    await asyncio.sleep(random.uniform(0.5, duration))


async def random_scroll(page, count: int = 3) -> None:
    """Perform random smooth scrolling to simulate reading behavior."""
    import asyncio

    for _ in range(count):
        scroll_amount = random.randint(200, 600)
        await page.evaluate(f"""
            window.scrollBy({{
                top: {scroll_amount},
                behavior: 'smooth'
            }});
        """)
        await asyncio.sleep(random.uniform(0.8, 2.0))
