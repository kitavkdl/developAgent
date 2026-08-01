"""trace_event 발행기 (대회 규칙 3 — Raw API Stream).

깨면 안 되는 규칙 (BUILD_PLAN §1.2):
- seq는 job_id 안에서 단조 증가
- 종료 이벤트(job.completed | job.failed | job.degraded)는 정확히 1회
- tool.call / tool.result payload는 가공하지 않음 — API 키·인증 헤더만 마스킹
- provider 컬럼으로 LINER/OpenAI 구분 (세컨드 화면 색 구분)
"""
from __future__ import annotations

import queue
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
    seq는 메모리 카운터로 관리하고, DB의 UNIQUE(job_id, seq)가 최후 방어선.

    쓰기는 전용 writer 스레드가 비동기로 처리한다. trace_event INSERT는 job 1건에
    60~90회 발생하는데, 이걸 파이프라인 스레드에서 동기로 하면 그만큼의 Neon 왕복이
    통째로 처리 시간에 얹히고, S5 병렬 워커들은 서로의 trace INSERT를 기다리느라
    Db._lock에서 직렬화된다. seq는 emit() 시점에 락 안에서 이미 확정되고 큐는
    FIFO이므로, 비동기로 옮겨도 순서와 seq 계약은 그대로다.

    쓰기 실패는 삼키지 않는다 — 첫 예외를 보관했다가 flush()에서 올린다.
    (동기 시절과 같은 방식으로 job.failed 경로를 타되, 시점만 늦어진다.)
    """

    def __init__(self, db, job_id):
        self._db = db
        self.job_id = job_id
        self._seq = 0
        self._terminated = False
        self._lock = threading.Lock()  # S5 검색/평가 병렬화로 여러 스레드가 동시에 emit 가능
        self._queue: queue.Queue = queue.Queue()
        self._write_error: BaseException | None = None
        self._writer = threading.Thread(
            target=self._drain, name=f"trace-{str(job_id)[:8]}", daemon=True)
        self._writer.start()

    def _drain(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:  # 종료 신호
                    return
                try:
                    self._db.insert_trace_event(*item)
                except BaseException as e:  # noqa: BLE001 — flush()에서 그대로 올린다
                    if self._write_error is None:
                        self._write_error = e
            finally:
                self._queue.task_done()

    def emit(self, event_type: str, payload: dict | None = None, provider: str = "app") -> None:
        # 마스킹은 payload를 통째로 재귀 순회한다 (OpenAI tool.call payload에는
        # 전체 JSON Schema가 실린다) — 락 안에서 하면 S5 병렬 워커들이 서로의
        # 순회를 기다리게 되므로, seq와 무관한 이 작업은 락 밖에서 끝낸다.
        masked = mask_secrets(payload or {})
        # seq 채번 + 종료 플래그 검사/설정을 하나의 원자적 구간으로 묶는다 —
        # 아니면 두 스레드가 동시에 emit할 때 같은 seq를 뽑아 UNIQUE(job_id, seq)
        # 제약 위반으로 죽거나, 종료 이벤트 중복 발행 체크가 깨질 수 있다.
        with self._lock:
            if self._terminated:
                # 종료 이벤트는 정확히 1회 — 이후 발행은 계약 위반이므로 조용히 버리지 않고 막는다
                raise RuntimeError(f"job {self.job_id}: 종료 이벤트 이후 발행 시도 ({event_type})")
            terminal = event_type in TERMINAL_EVENTS
            if terminal:
                self._terminated = True
            self._seq += 1
            seq = self._seq
            # 큐 적재도 락 안에서 — seq 순서와 큐 순서를 일치시킨다.
            self._queue.put((self.job_id, seq, event_type, provider, masked))
        if terminal:
            # 종료 이벤트까지 DB에 반영된 뒤에 job을 끝낸다 — UI는 종료 이벤트를
            # 보고 폴링을 멈추므로, 그 앞의 이벤트가 아직 안 써진 상태로 끝나면 안 된다.
            self.flush()

    def flush(self) -> None:
        """큐가 빌 때까지 대기. 쓰기 중 발생한 첫 예외가 있으면 여기서 올린다."""
        self._queue.join()
        if self._write_error is not None:
            err, self._write_error = self._write_error, None
            raise err

    def close(self) -> None:
        """writer 스레드 종료 — job 종료 경로에서 호출 (flush 후 커넥션 정리 전)."""
        self._queue.put(None)
        self._writer.join(timeout=5.0)

    @property
    def terminated(self) -> bool:
        return self._terminated
