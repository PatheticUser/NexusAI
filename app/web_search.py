"""
Web search module using Tavily.
Falls back gracefully if search fails.
"""

from __future__ import annotations
import os
from typing import List, Dict


def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the web using Tavily.

    Returns a list of dicts with keys: title, snippet, url
    """
    try:
        from tavily import TavilyClient

        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not api_key:
            return [
                {
                    "title": "Search Error",
                    "snippet": "TAVILY_API_KEY is not set.",
                    "url": "",
                }
            ]

        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
        )

        results = []
        for r in response.get("results", []):
            results.append(
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("content", ""),
                    "url": r.get("url", ""),
                }
            )
        return results

    except Exception as e:
        return [{"title": "Search Error", "snippet": str(e), "url": ""}]


def format_search_results(results: List[Dict[str, str]]) -> str:
    """Format search results into a readable string for the LLM context."""
    if not results:
        return "No results found."

    formatted = []
    for i, r in enumerate(results, 1):
        formatted.append(
            f"[{i}] {r['title']}\n    {r['snippet']}\n    Source: {r['url']}"
        )
    return "\n\n".join(formatted)
