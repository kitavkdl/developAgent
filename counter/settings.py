"""설정 로더.

모든 모델 ID·임계값·TTL·검색예산·타임아웃은 여기서만 읽는다 (BUILD_PLAN §5 — 하드코딩 금지).

읽기 우선순위: os.environ > st.secrets > 기본값.
Streamlit이 secrets.toml을 os.environ에 자동 반영하는지는 버전에 따라 다르므로
(MODELS_AND_APIS §2.5 — 미검증), 앱 시작 시 bridge_secrets_to_env()로 명시적으로 브리지한다.
테스트/스크립트는 streamlit 없이 os.environ만으로 동작해야 하므로 streamlit import는 지연·방어적으로.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _secrets() -> dict:
    try:
        import streamlit as st  # noqa: PLC0415

        return dict(st.secrets)
    except Exception:
        return {}


def bridge_secrets_to_env() -> None:
    """st.secrets → os.environ 브리지 (MODELS_AND_APIS §2.5). 앱 진입점에서 1회 호출."""
    for k, v in _secrets().items():
        if isinstance(v, (str, int, float, bool)):
            os.environ.setdefault(k, str(v))


def _get(key: str, default: str | None = None) -> str | None:
    if key in os.environ:
        return os.environ[key]
    sec = _secrets()
    if key in sec:
        return str(sec[key])
    return default


def _get_float(key: str, default: float) -> float:
    v = _get(key)
    try:
        return float(v) if v is not None else default
    except ValueError:
        return default


def _get_int(key: str, default: int) -> int:
    v = _get(key)
    try:
        return int(float(v)) if v is not None else default
    except ValueError:
        return default


def _get_bool(key: str, default: bool) -> bool:
    v = _get(key)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    # 키/연결 — 없어도 앱은 떠야 함 (B01 게이트). 실제 호출 시점에만 검증.
    openai_api_key: str | None = None
    liner_api_key: str | None = None
    database_url: str | None = None

    # LINER — L1 실측 완료 (공식 문서 대조, MODELS_AND_APIS §3.2)
    liner_api_base: str = "https://platform.liner.com"
    liner_web_search_path: str = "/api/v1/tools/search/web"
    liner_scholar_search_path: str = "/api/v1/tools/search/scholar"
    liner_supports_date_filter: bool = False  # L3 미확인 → 기본 false = 델타 서치 스코프 아웃
    liner_timeout_seconds: float = 15.0
    liner_qps: float = 1.0
    # S5 검색/평가 병렬 실행 상한 (D-04 역할 경계는 유지 — 병렬화는 애플리케이션
    # 코드가 LINER/OpenAI 호출을 동시에 여러 개 여는 것이지, LLM이 오케스트레이션을
    # 대신하는 게 아니다). liner_qps가 실제 발사 속도를 이미 직렬화하므로 이 값은
    # "동시에 대기 중일 수 있는 최대 개수"의 상한일 뿐이다.
    max_parallel_searches: int = 4
    max_parallel_evaluations: int = 4

    # OpenAI 모델 배정 (MODELS_AND_APIS §2.2)
    model_intake: str = "gpt-5.6-terra"
    model_triage: str = "gpt-5.6-terra"
    model_router: str = "gpt-5.6-luna"
    model_labeler: str = "gpt-5.6-luna"
    model_hypothesis: str = "gpt-5.6-sol"
    model_evaluator: str = "gpt-5.6-sol"
    model_guardrail: str = "gpt-5.6-luna"
    model_reporter: str = "gpt-5.6-terra"
    model_embedding: str = "text-embedding-3-small"
    openai_timeout_seconds: float = 60.0  # SDK 기본(~600s) 대신 상한을 둬 무한 대기 방지

    # 임계값/예산 — 전부 미검증 추정치 (DECISIONS D-11, D-13)
    job_timeout_seconds: float = 270.0
    category_reuse_threshold: float = 0.75
    canonical_threshold: float = 0.85
    dispute_count_threshold: int = 3
    dispute_ratio_threshold: float = 0.30
    trace_poll_interval_seconds: float = 1.0

    extras: dict = field(default_factory=dict)


def load_settings() -> Settings:
    return Settings(
        openai_api_key=_get("OPENAI_API_KEY"),
        liner_api_key=_get("LINER_API_KEY"),
        database_url=_get("DATABASE_URL"),
        liner_api_base=_get("LINER_API_BASE", "https://platform.liner.com"),
        liner_web_search_path=_get("LINER_WEB_SEARCH_PATH", "/api/v1/tools/search/web"),
        liner_scholar_search_path=_get("LINER_SCHOLAR_SEARCH_PATH", "/api/v1/tools/search/scholar"),
        liner_supports_date_filter=_get_bool("LINER_SUPPORTS_DATE_FILTER", False),
        liner_timeout_seconds=_get_float("LINER_TIMEOUT_SECONDS", 15.0),
        liner_qps=_get_float("LINER_QPS", 1.0),
        max_parallel_searches=_get_int("MAX_PARALLEL_SEARCHES", 4),
        max_parallel_evaluations=_get_int("MAX_PARALLEL_EVALUATIONS", 4),
        model_intake=_get("OPENAI_MODEL_INTAKE", "gpt-5.6-terra"),
        model_triage=_get("OPENAI_MODEL_TRIAGE", "gpt-5.6-terra"),
        model_router=_get("OPENAI_MODEL_ROUTER", "gpt-5.6-luna"),
        model_labeler=_get("OPENAI_MODEL_LABELER", "gpt-5.6-luna"),
        model_hypothesis=_get("OPENAI_MODEL_HYPOTHESIS", "gpt-5.6-sol"),
        model_evaluator=_get("OPENAI_MODEL_EVALUATOR", "gpt-5.6-sol"),
        model_guardrail=_get("OPENAI_MODEL_GUARDRAIL", "gpt-5.6-luna"),
        model_reporter=_get("OPENAI_MODEL_REPORTER", "gpt-5.6-terra"),
        model_embedding=_get("OPENAI_MODEL_EMBEDDING", "text-embedding-3-small"),
        openai_timeout_seconds=_get_float("OPENAI_TIMEOUT_SECONDS", 60.0),
        job_timeout_seconds=_get_float("JOB_TIMEOUT_SECONDS", 270.0),
        category_reuse_threshold=_get_float("CATEGORY_REUSE_THRESHOLD", 0.75),
        canonical_threshold=_get_float("CANONICAL_THRESHOLD", 0.85),
        dispute_count_threshold=_get_int("DISPUTE_COUNT_THRESHOLD", 3),
        dispute_ratio_threshold=_get_float("DISPUTE_RATIO_THRESHOLD", 0.30),
        trace_poll_interval_seconds=_get_float("TRACE_POLL_INTERVAL_SECONDS", 1.0),
    )
