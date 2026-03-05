"""
Web Search Service — DuckDuckGo search for cross-referencing claims.

NOTE: On systems with LibreSSL (e.g., older macOS), HTTPS connections to external
services may fail or be very slow. This module detects that and gracefully returns
empty results so the pipeline doesn't hang.
"""
from __future__ import annotations
from typing import List, Dict
import ssl
import re


def _ssl_is_compatible() -> bool:
    """Check if the system SSL is compatible with modern HTTPS APIs."""
    try:
        ver = ssl.OPENSSL_VERSION
        # LibreSSL 2.x is not compatible with modern TLS 1.3
        if "LibreSSL 2." in ver:
            return False
        return True
    except Exception:
        return True


_SSL_OK = _ssl_is_compatible()


def web_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search the web via DuckDuckGo HTML lite page.
    Returns empty list if SSL environment is incompatible (LibreSSL 2.x).
    """
    if not _SSL_OK:
        # Skip web search entirely on incompatible SSL environments
        return []
    return _try_html_fallback(query, max_results)


def _try_html_fallback(query: str, max_results: int) -> List[Dict[str, str]]:
    """Scrape DuckDuckGo HTML lite page with strict timeout."""
    try:
        import httpx

        url = "https://html.duckduckgo.com/html/"
        resp = httpx.post(
            url,
            data={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; TruthGuard/1.0)"},
            timeout=5.0,
            follow_redirects=True,
            verify=False,  # Work around older macOS SSL
        )
        resp.raise_for_status()
        html = resp.text

        results = []
        blocks = re.findall(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            html, re.DOTALL
        )

        for url_match, title_html, snippet_html in blocks[:max_results]:
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet_html).strip()
            actual_url = url_match
            if "uddg=" in actual_url:
                import urllib.parse
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(actual_url).query)
                actual_url = parsed.get("uddg", [url_match])[0]

            if title:
                results.append({
                    "title": title,
                    "url": actual_url,
                    "snippet": snippet,
                })

        return results
    except Exception as e:
        print(f"[WebSearch] failed: {e}")
        return []
