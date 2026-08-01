"""
tools/web_search.py

DuckDuckGo Web Search Tool for LangChain Agent
"""

from __future__ import annotations

from langchain_core.tools import tool
from duckduckgo_search import DDGS


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    DuckDuckGo를 이용한 웹 검색 Tool

    Args:
        query: 검색어
        max_results: 최대 검색 개수

    Returns:
        검색 결과 문자열
    """
    try:
        results = []

        with DDGS() as ddgs:
            search_results = ddgs.text(
                query,
                max_results=max_results,
            )

            for idx, item in enumerate(search_results, start=1):
                title = item.get("title", "")
                body = item.get("body", "")
                href = item.get("href", "")

                results.append(
                    f"[{idx}] {title}\n"
                    f"{body}\n"
                    f"{href}"
                )

        if not results:
            return "검색 결과가 없습니다."

        return "\n\n".join(results)

    except Exception as e:
        return f"검색 오류: {e}"


if __name__ == "__main__":
    print("=" * 60)
    print("DuckDuckGo Search Tool Test")
    print("=" * 60)

    response = web_search.invoke(
        {
            "query": "LangGraph",
            "max_results": 3,
        }
    )

    print(response)
