"""상태 머신 (ARCHITECTURE §2).

핵심 구조 원칙: 오케스트레이션은 애플리케이션이 소유하고, LLM은 각 단계 안에서만 판단한다.
상태 전이는 이 표가 결정하며, LLM이 "다음에 뭘 할지"를 정하지 않는다.
DEGRADED는 프로바이더 장애와 JOB_TIMEOUT_SECONDS 초과가 공유한다 (D-13) —
어느 쪽이든 사용자 경험은 "부분 증거로 결정론적으로 끝났다"로 동일해야 하기 때문.
"""
from __future__ import annotations

from enum import Enum


class JobState(str, Enum):
    INTAKE = "INTAKE"
    TRIAGE = "TRIAGE"
    CLASSIFYING = "CLASSIFYING"
    CACHE_CHECK = "CACHE_CHECK"
    RESEARCHING = "RESEARCHING"
    EVALUATING = "EVALUATING"
    SYNTHESIZING = "SYNTHESIZING"
    PERSISTING = "PERSISTING"
    DEGRADED = "DEGRADED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


ALLOWED_TRANSITIONS: dict[JobState, set[JobState]] = {
    JobState.INTAKE: {JobState.TRIAGE, JobState.FAILED},
    JobState.TRIAGE: {JobState.COMPLETE, JobState.CLASSIFYING, JobState.FAILED},
    JobState.CLASSIFYING: {JobState.CACHE_CHECK},
    JobState.CACHE_CHECK: {JobState.SYNTHESIZING, JobState.RESEARCHING},
    JobState.RESEARCHING: {JobState.EVALUATING, JobState.DEGRADED},
    JobState.EVALUATING: {JobState.SYNTHESIZING, JobState.DEGRADED},
    JobState.DEGRADED: {JobState.SYNTHESIZING},
    JobState.SYNTHESIZING: {JobState.PERSISTING},
    JobState.PERSISTING: {JobState.COMPLETE},
    JobState.COMPLETE: set(),
    JobState.FAILED: set(),
}


class StateMachine:
    def __init__(self, initial: JobState = JobState.INTAKE):
        self.state = initial
        self.history: list[JobState] = [initial]

    def transition(self, to: JobState) -> None:
        if to not in ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"허용되지 않은 상태 전이: {self.state.value} → {to.value}")
        self.state = to
        self.history.append(to)


# get_job_state(job_id)가 trace_event로부터 상태를 유도할 때 쓰는 매핑 (BUILD_PLAN §1.1 —
# 별도 job 상태 테이블은 만들지 않는다)
EVENT_TO_STATE: dict[str, JobState] = {
    "job.created": JobState.INTAKE,
    "intake.completed": JobState.TRIAGE,
    "claim.extracted": JobState.TRIAGE,
    "claim.triaged": JobState.CLASSIFYING,
    "route.decided": JobState.CLASSIFYING,
    "industry.classified": JobState.CACHE_CHECK,
    "cache.decision": JobState.RESEARCHING,
    "tool.call": JobState.RESEARCHING,
    "tool.result": JobState.RESEARCHING,
    "candidate.evaluated": JobState.EVALUATING,
    "verdict.assembled": JobState.PERSISTING,
    "job.completed": JobState.COMPLETE,
    "job.failed": JobState.FAILED,
    "job.degraded": JobState.DEGRADED,
}


def derive_state(events: list[dict]) -> JobState | None:
    """trace_event 목록(seq 오름차순)에서 현재 상태를 유도."""
    state: JobState | None = None
    for ev in events:
        mapped = EVENT_TO_STATE.get(ev["event_type"])
        if mapped is not None:
            state = mapped
    return state
