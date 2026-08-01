"""S6 2단 가드레일 (ARCHITECTURE §1 S6, PROMPTS.md 말미).

왜 코드로도 검사하나: SDK output guardrail은 최종 출력 에이전트에만 적용되고
중간 출력에 자동 적용되지 않는다. LLM 가드레일 하나에만 의존하면 새는 경로가 생긴다.
그래서 ① LLM 1차 차단(가벼운 모델) 뒤에 ② 정규식 2차 검사를 코드로 강제하고,
걸리면 재생성 1회 → 그래도 걸리면 정적 안전 문구로 대체한다 (T8).
"""
from __future__ import annotations

import json
import re
from typing import Callable

BANNED = r"(허위|거짓|위법|불법|사기|처벌|고발|기만|과징금)"

SAFE_FALLBACK = (
    "판정 결과와 근거 URL을 확인해 주세요. 이 서비스는 법적 판단을 하지 않으며, "
    "공개 자료에서 반례 문서의 존재 여부만 보고합니다."
)


def contains_banned(payload: dict) -> bool:
    return re.search(BANNED, json.dumps(payload, ensure_ascii=False)) is not None


def guard(payload: dict, regenerate_once: Callable[[dict], dict]) -> dict:
    """최종 JSON에 대한 정규식 금지어 검사 (가드레일 2단). 걸리면 재생성 1회."""
    if contains_banned(payload):
        payload = regenerate_once(payload)
        if contains_banned(payload):
            payload = dict(payload)
            payload["explanation"] = SAFE_FALLBACK
    return payload
