"""trace_event 발행기 (대회 규칙 3 — Raw API Stream).

깨면 안 되는 규칙 (BUILD_PLAN §1.2):
- seq는 job_id 안에서 단조 증가
- 종료 이벤트(job.completed | job.failed | job.degraded)는 정확히 1회
- tool.call / tool.result payload는 가공하지 않음 — API 키·인증 헤더만 마스킹
- provider 컬럼으로 LINER/OpenAI 구분 (세컨드 화면 색 구분)
"""
from __future__ import annotations

import re
import threading
from typing import Any

TERMINAL_EVENTS = {"job.completed", "job.failed", "job.degraded"}

# 마스킹은 키/헤더에만 적용. 나머지 payload는 raw 그대로 (대회 필수 요건).
_SENSITIVE_KEY = re.compile(r"(api[_-]?key|authorization|secret|token|password)", re.I)


def mask_secrets(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: ("***MASKED***" if _SENSITIVE_KEY.search(str(k)) else mask_secrets(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [mask_secrets(x) for x in obj]
    return obj


class TraceEmitter:
    """job 1건의 이벤트 발행. 단일 프로세스(Streamlit 안에서 직접 호출 — D-14)이므로
    seq는 메모리 카운터로 관리하고, DB의 UNIQUE(job_id, seq)가 최후 방어선."""

    def __init__(self, db, job_id):
        self._db = db
        self.job_id = job_id
        self._seq = 0
        self._terminated = False
        self._lock = threading.Lock()  # S5 검색/평가 병렬화로 여러 스레드가 동시에 emit 가능

    def emit(self, event_type: str, payload: dict | None = None, provider: str = "app") -> None:
        # seq 채번 + 종료 플래그 검사/설정을 하나의 원자적 구간으로 묶는다 —
        # 아니면 두 스레드가 동시에 emit할 때 같은 seq를 뽑아 UNIQUE(job_id, seq)
        # 제약 위반으로 죽거나, 종료 이벤트 중복 발행 체크가 깨질 수 있다.
        with self._lock:
            if self._terminated:
                # 종료 이벤트는 정확히 1회 — 이후 발행은 계약 위반이므로 조용히 버리지 않고 막는다
                raise RuntimeError(f"job {self.job_id}: 종료 이벤트 이후 발행 시도 ({event_type})")
            if event_type in TERMINAL_EVENTS:
                self._terminated = True
            self._seq += 1
            seq = self._seq
        self._db.insert_trace_event(
            self.job_id, seq, event_type, provider, mask_secrets(payload or {})
        )

    @property
    def terminated(self) -> bool:
        return self._terminated
