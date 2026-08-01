"""
tools/current_time.py

Current Date & Time Tool for LangChain Agent
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

DEFAULT_TIMEZONE = "Asia/Seoul"


@tool
def current_time(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    현재 날짜와 시간을 반환합니다.

    Args:
        format: datetime.strftime 형식 문자열

    Examples
    --------
    current_time()
    current_time("%Y-%m-%d")
    current_time("%H:%M")
    """
    try:
        now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))
        return now.strftime(format)
    except Exception as e:
        return f"시간 조회 오류: {e}"


if __name__ == "__main__":
    print("=" * 60)
    print("Current Time Tool Test")
    print("=" * 60)

    print(current_time.invoke({}))
    print(current_time.invoke({"format": "%Y-%m-%d"}))
    print(current_time.invoke({"format": "%H:%M:%S"}))
