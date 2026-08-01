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

# UNVERIFIED 전용 — "반증도 근거도 없음"을 "그러니 진실"로 오독하게 만드는 결론형
# 긍정 어휘. "사실"/"진실" 단독 어근은 정상적인 부정문("사실임을 확인한 것이
# 아닙니다")에도 흔히 등장하므로 넣지 않고, 문맥상 결론임이 명확한 어형만 넣는다.
POSITIVE_CONCLUSION = (
    r"(사실일 (가능성이|확률이) (높|크)|사실로 보(인|입니다)|사실입니다|"
    r"진실입니다|진실이다|믿을 수 있습니다|신뢰할 수 있습니다|"
    r"안심하(고|셔도)|문제없습니다|틀림없습니다)"
)

SAFE_FALLBACK = (
    "판정 결과와 근거 URL을 확인해 주세요. 이 서비스는 법적 판단을 하지 않으며, "
    "공개 자료에서 반례 문서의 존재 여부만 보고합니다."
)


def contains_banned(payload: dict) -> bool:
    return re.search(BANNED, json.dumps(payload, ensure_ascii=False)) is not None


def contains_positive_conclusion(payload: dict) -> bool:
    return re.search(POSITIVE_CONCLUSION, json.dumps(payload, ensure_ascii=False)) is not None


def guard(payload: dict, regenerate_once: Callable[[dict], dict]) -> dict:
    """최종 JSON에 대한 정규식 금지어 검사 (가드레일 2단). 걸리면 재생성 1회."""
    if contains_banned(payload):
        payload = regenerate_once(payload)
        if contains_banned(payload):
            payload = dict(payload)
            payload["explanation"] = SAFE_FALLBACK
    return payload
