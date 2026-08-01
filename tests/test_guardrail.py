"""T7/T8 — 금지 어휘가 최종 JSON에 없음 (2단 가드레일)."""
from counter.guardrail import SAFE_FALLBACK, contains_banned, guard


def test_banned_vocab_triggers_regeneration():
    payload = {"explanation": "이 광고는 허위입니다."}
    out = guard(payload, lambda p: {"explanation": "반례 문서가 확인되었습니다."})
    assert not contains_banned(out)


def test_persistent_banned_vocab_falls_back_to_static():
    payload = {"explanation": "이 광고는 거짓입니다."}
    out = guard(payload, lambda p: {"explanation": "여전히 사기입니다."})
    assert out["explanation"] == SAFE_FALLBACK
    assert not contains_banned({"e": out["explanation"]})


def test_clean_payload_untouched():
    payload = {"explanation": "반례를 찾지 못했습니다."}
    assert guard(payload, lambda p: p) == payload


def test_all_banned_words_detected():
    for word in ("허위", "거짓", "위법", "불법", "사기", "처벌", "고발", "기만", "과징금"):
        assert contains_banned({"x": f"이것은 {word} 관련 표현"}), word
