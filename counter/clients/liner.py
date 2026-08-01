"""LINER 검색 클라이언트 (MODELS_AND_APIS §3).

역할 경계 (D-04): LINER는 검색을 '실행'하고, OpenAI는 그 검색을 계획·평가·판정한다.
검색은 전부 LINER — OpenAI 내장 web_search는 쓰지 않는다.

엔드포인트/인증 헤더는 L1 실측 완료 (공식 문서 대조, MODELS_AND_APIS §3.2).
   전부 설정(LINER_API_BASE, LINER_*_PATH)으로 빼두었으므로 필요 시 secrets에서 override.

구현 요구사항 (§3.3):
- timeout (기본 15s)
- QPS 리미터 (Scholar 기본 2 QPS로 알려짐 — 안전하게 절반)
- 429 → 지수 백오프 재시도 1회
- 모든 호출에 tool.call / tool.result 이벤트 발행 (provider="liner", raw 가공 금지)
- request_id를 search_log에 기록
- API 키는 로그/트레이스에 절대 노출 금지 (events.mask_secrets)

LINER Search는 스트리밍 응답이 아니므로 요청 전후로 자체 tool.call/tool.result row를
감싸서 INSERT한다 (ARCHITECTURE §6).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import httpx

from ..settings import Settings


@dataclass
class SearchResult:
    title: str | None
    url: str
    snippet: str | None
    date: str | None  # 발행일 문자열. 없으면 None — 추측 금지 (ARCHITECTURE §7)
    extra: dict


@dataclass
class SearchResponse:
    ok: bool
    status: str  # ok | timeout | rate_limited | error
    request_id: str | None
    results: list[SearchResult]
    raw: dict | None  # tool.result 이벤트에 가공 없이 실릴 원본


class _RateLimiter:
    def __init__(self, qps: float):
        self._min_interval = 1.0 / max(qps, 0.01)
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delta = self._min_interval - (now - self._last)
            if delta > 0:
                time.sleep(delta)
            self._last = time.monotonic()


class LinerClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self._settings = settings
        self._limiter = _RateLimiter(settings.liner_qps)
        self._client = httpx.Client(
            base_url=settings.liner_api_base,
            timeout=settings.liner_timeout_seconds,
            headers={"x-api-key": settings.liner_api_key or ""},
            transport=transport,
        )

    def search(self, mode: str, query: str, date_from: str | None = None,
               max_results: int = 10) -> SearchResponse:
        """mode: 'web' | 'scholar'. date_from은 델타 모드 전용 —
        LINER가 날짜필터를 지원할 때만 파라미터에 실린다 (L3 미확인, PRD §10-4)."""
        path = (self._settings.liner_web_search_path if mode == "web"
                else self._settings.liner_scholar_search_path)
        payload: dict = {"query": query, "max_results": max_results}
        if date_from and self._settings.liner_supports_date_filter:
            payload["published_after"] = date_from  # L3 실측 후 파라미터명 확정

        self._limiter.wait()
        resp = self._request_with_retry(path, payload)
        return resp

    def _request_with_retry(self, path: str, payload: dict) -> SearchResponse:
        # 429 → 지수 백오프 재시도 1회, 타임아웃 → 재시도 1회 (ARCHITECTURE §7)
        for attempt in (0, 1):
            try:
                r = self._client.post(path, json=payload)
            except httpx.TimeoutException:
                if attempt == 0:
                    time.sleep(1.0)
                    continue
                return SearchResponse(False, "timeout", None, [], None)
            except httpx.HTTPError as e:
                return SearchResponse(False, "error", None, [], {"error": str(e)})

            if r.status_code == 429:
                if attempt == 0:
                    time.sleep(2.0 ** 1)  # 백오프 후 1회 재시도
                    continue
                return SearchResponse(False, "rate_limited", _request_id(r), [], _safe_json(r))
            if r.status_code >= 400:
                return SearchResponse(False, "error", _request_id(r), [], _safe_json(r))

            body = _safe_json(r) or {}
            return SearchResponse(True, "ok", _request_id(r), _parse_results(body), body)
        return SearchResponse(False, "error", None, [], None)


def _request_id(r: httpx.Response) -> str | None:
    return r.headers.get("x-request-id") or r.headers.get("request-id")


def _safe_json(r: httpx.Response) -> dict | None:
    try:
        return r.json()
    except Exception:
        return {"non_json_body": r.text[:2000]}


def _parse_results(body: dict) -> list[SearchResult]:
    """응답 필드명은 L2 실측 전 미확인 — 알려진 후보 키를 방어적으로 수용.
    date가 없으면 None 유지 (추측 금지)."""
    items = body.get("results") or body.get("data") or body.get("documents") or []
    out: list[SearchResult] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        url = it.get("url") or it.get("link")
        if not url:
            continue
        out.append(SearchResult(
            title=it.get("title"),
            url=url,
            snippet=it.get("snippet") or it.get("description") or it.get("content"),
            date=it.get("date") or it.get("published_date") or it.get("published_at"),
            extra={k: v for k, v in it.items()
                   if k in ("authors", "journal", "citation_count")},
        ))
    return out
