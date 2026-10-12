"""Darkelf Cocoa compatibility coverage registry (v7.1.4).

These are TEST TARGETS, not allowlisted domains. The registry does not disable
network blocking, cosmetic rules, fingerprint defenses, or site isolation.
Add actual exceptions only after confirming a specific broken request.
"""

SOCIAL = (
    "facebook.com",
    "instagram.com",
    "threads.net",
    "x.com",
    "twitter.com",
    "reddit.com",
    "tiktok.com",
    "pinterest.com",
    "linkedin.com",
    "bsky.app",
    "snapchat.com",
    "discord.com",
    "tumblr.com",
)

NEWS = (
    "cnn.com",
    "bbc.com",
    "bbc.co.uk",
    "dw.com",
    "euronews.com",
    "reuters.com",
    "apnews.com",
    "aljazeera.com",
    "france24.com",
    "news.sky.com",
    "theguardian.com",
    "foxnews.com",
    "nbcnews.com",
    "abcnews.go.com",
    "cbsnews.com",
    "cnbc.com",
    "bloomberg.com",
    "nytimes.com",
    "washingtonpost.com",
    "usatoday.com",
    "npr.org",
    "politico.com",
    "axios.com",
    "time.com",
)

SPORTS = (
    "espn.com",
    "nba.com",
    "nfl.com",
    "nhl.com",
    "mlb.com",
    "cbssports.com",
    "foxsports.com",
    "sports.yahoo.com",
    "bleacherreport.com",
    "cricbuzz.com",
    "marca.com",
    "skysports.com",
    "formula1.com",
)

STREAMING = (
    "youtube.com",
    "youtu.be",
    "twitch.tv",
    "netflix.com",
    "disneyplus.com",
    "primevideo.com",
    "hulu.com",
    "vimeo.com",
    "dailymotion.com",
    "spotify.com",
    "peacocktv.com",
)

SEARCH_AI = (
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "search.brave.com",
    "chatgpt.com",
    "claude.ai",
    "gemini.google.com",
    "perplexity.ai",
)

SHOPPING = (
    "amazon.com",
    "ebay.com",
    "walmart.com",
    "target.com",
    "shopee.vn",
    "lazada.vn",
    "aliexpress.com",
    "etsy.com",
    "bestbuy.com",
)

PRODUCTIVITY = (
    "mail.google.com",
    "outlook.live.com",
    "outlook.office.com",
    "drive.google.com",
    "office.com",
    "github.com",
    "gitlab.com",
    "slack.com",
    "notion.so",
    "canva.com",
    "figma.com",
    "teams.microsoft.com",
)

PAYMENTS = (
    "paypal.com",
    "wise.com",
    "stripe.com",
)

TRAVEL = (
    "booking.com",
    "agoda.com",
    "airbnb.com",
    "expedia.com",
    "trip.com",
    "maps.google.com",
)

CATEGORIES = {
    "social": SOCIAL,
    "news": NEWS,
    "sports": SPORTS,
    "streaming": STREAMING,
    "search_ai": SEARCH_AI,
    "shopping": SHOPPING,
    "productivity": PRODUCTIVITY,
    "payments": PAYMENTS,
    "travel": TRAVEL,
}

# Diagnostic-only layout-safe domains: no automatic adblock bypass.
LAYOUT_DIAGNOSTIC_HOSTS = ("cnn.com", "dw.com", "euronews.com")


def matches_domain(hostname, domain):
    host = (hostname or "").lower().rstrip(".")
    domain = domain.lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def category_for_host(hostname):
    for category, domains in CATEGORIES.items():
        if any(matches_domain(hostname, domain) for domain in domains):
            return category
    return "other"
