"""오케스트레이터 — S0~S6 전체를 소유한다.

핵심 구조 원칙 (ARCHITECTURE §0): 오케스트레이션은 애플리케이션이 소유하고,
LLM은 각 단계 안에서만 판단한다. 상태 전이는 counter/state.py의 표가 결정한다.
이래야 재현 가능하고, 검색 예산을 통제할 수 있고, 판정 게이트를 강제할 수 있다.

외부 계약 (BUILD_PLAN §1.1): run_job / get_job_state 두 함수.
Streamlit 페이지는 이 함수들만 안다 — 파이프라인 로직을 UI와 분리해
단계별 검증 게이트(B01~B11)를 독립적으로 테스트하기 위함.
사람의 좋아요/싫어요 피드백 수집은 없다 — 목표는 사람 큐레이션이 아니라
입력을 받는 대로 canonical/verdict DB를 축적하는 것이다.

job_id == ad_id: 한 job은 광고 입력 1건의 처리다 (DB_SCHEMA.md ad 테이블).
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from ..clients.liner import LinerClient
from ..clients.openai_client import OpenAIClient
from ..db import Db, new_id, normalized_hash
from ..events import TraceEmitter
from ..settings import Settings, load_settings
from ..state import JobState, StateMachine, derive_state
from .s0_intake import run_intake
from .s1_triage import run_triage
from .s1b_subject import resolve_subject
from .s2a_router import run_router
from .s2b_classifier import resolve_industry_category
from .s3_cache import run_cache_check
from .s4_hypothesis import run_hypothesis
from .s5_search import run_search_and_evaluate
from .s6_verdict import (assemble_from_cache, assemble_from_search,
                         assemble_unresolved_subject, persist_puffery)


class Pipeline:
    """의존성(설정/DB/클라이언트)을 묶는다. 테스트에서 전부 주입 가능."""

    def __init__(self, settings: Settings | None = None, db: Db | None = None,
                 oai: OpenAIClient | None = None, liner: LinerClient | None = None):
        self.settings = settings or load_settings()
        self.db = db or Db(self.settings)
        self.oai = oai or OpenAIClient(self.settings)
        self.liner = liner or LinerClient(self.settings)

    # ---- 계약 함수 1: run_job ----

    def run_job(self, source_type: Literal["IMAGE", "URL", "TEXT"], payload) -> str:
        """S0~S6 전체를 동기 실행 후 job_id(=ad_id) 반환 (테스트/스크립트용).
        UI에서는 스크립트 재실행/페이지 이동에도 job이 끊기지 않도록
        run_job_async를 쓴다 — 실제 처리 로직은 _run_job_body에 공유."""
        job_id = new_id()
        emitter = TraceEmitter(self.db, job_id)
        emitter.emit("job.created", {"source_type": source_type})
        self._run_job_body(job_id, source_type, payload, emitter)
        return job_id

    def run_job_async(self, source_type: Literal["IMAGE", "URL", "TEXT"], payload) -> str:
        """job_id를 즉시 반환(빠른 INSERT 1회)하고, 나머지 S0~S6은 백그라운드
        스레드에서 계속 진행한다. Streamlit은 사용자가 다른 페이지로 이동하거나
        새로고침하면 현재 실행 중이던 스크립트를 그 자리에서 죽이는데, 그 경우에도
        이 데몬 스레드는 (Streamlit 스크립트 컨텍스트와 무관한 순수 파이썬 스레드라)
        살아남아 끝까지 진행되고 trace_event/verdict를 DB에 남긴다.
        스레드 전용 Db 커넥션을 새로 만들어 다른 세션이 쓰는 공유 캐시 커넥션과
        동시에 같은 psycopg2 connection을 건드리는 경합을 피한다."""
        job_id = new_id()
        worker_db = Db(self.settings)
        emitter = TraceEmitter(worker_db, job_id)
        emitter.emit("job.created", {"source_type": source_type})
        # trace 쓰기는 비동기지만 이 한 행만은 반환 전에 확정한다 — UI가 곧바로
        # job_id로 이벤트를 조회하므로, 아직 비어 있으면 "알 수 없음" 상태가
        # 한 폴링 주기 동안 노출된다.
        emitter.flush()
        worker = Pipeline(settings=self.settings, oai=self.oai, liner=self.liner, db=worker_db)

        def _run() -> None:
            try:
                worker._run_job_body(job_id, source_type, payload, emitter)
            except Exception:
                pass  # _run_job_body가 이미 job.failed를 기록하고 재raise — 스레드 종단에서는 흡수
            finally:
                worker_db.close()

        threading.Thread(target=_run, name=f"job-{job_id[:8]}", daemon=True).start()
        return job_id

    def _run_job_body(self, job_id: str, source_type: Literal["IMAGE", "URL", "TEXT"],
                      payload, emitter: TraceEmitter) -> None:
        """run_job / run_job_async가 공유하는 실제 S0~S6 처리 로직.
        사람 개입 지점은 없다 (PRD N2 — 입력 1회 → 출력까지 독립 수행)."""
        sm = StateMachine(JobState.INTAKE)
        started = time.monotonic()

        def deadline_exceeded() -> bool:
            return time.monotonic() - started > self.settings.job_timeout_seconds

        try:
            # S0 — 범주어 없이는 반례 쿼리를 만들 수 없으므로 항상 최우선
            intake = run_intake(source_type, payload, self.oai, self.settings, emitter)
            emitter.emit("intake.completed", dict(intake))

            session_id = self.db.insert_session(source_app="web")
            self.db.insert_ad(
                ad_id=job_id, session_id=session_id, source_type=source_type,
                raw_input=str(payload)[:4000] if source_type != "IMAGE" else "[image]",
                extracted_text="\n".join(intake.get("raw_lines") or []),
                brand_name=intake.get("brand_name"),
                ocr_fallback_used=bool(intake.get("ocr_failed")),
            )

            # S1 — PUFFERY 조기 종료 게이트. 여기서 걸러지면 검색 tool_call 0건 (N4)
            sm.transition(JobState.TRIAGE)
            claims = run_triage(intake, self.oai, self.settings, emitter)
            for c in claims:
                emitter.emit("claim.extracted", c)
            emitter.emit("claim.triaged", {"count": len(claims),
                                           "categories": [c["claim_category"] for c in claims]})

            falsifiable = [c for c in claims if c["claim_category"] == "FALSIFIABLE"]
            puffery = [c for c in claims if c["claim_category"] == "PUFFERY"]

            # PUFFERY/NOT_A_CLAIM 기록. PUFFERY만 4값 판정 대상 (NOT_A_CLAIM은 계약 밖)
            for c in claims:
                if c["claim_category"] == "FALSIFIABLE":
                    continue
                claim_id = self.db.insert_claim(
                    ad_id=job_id, claim_text=c["claim_text"],
                    normalized_text=c["normalized_text"], embedding=None,
                    claim_category=c["claim_category"],
                    claim_type_code="PUFFERY" if c["claim_category"] == "PUFFERY" else None,
                )
                if c["claim_category"] == "PUFFERY":
                    persist_puffery(claim=c, claim_id=claim_id, oai=self.oai,
                                    db=self.db, settings=self.settings, emitter=emitter)

            if not falsifiable:
                # 전부 PUFFERY/NOT_A_CLAIM → 검색 0회로 직행 종료 (ARCHITECTURE §2)
                sm.transition(JobState.COMPLETE)
                emitter.emit("job.completed", {"reason": "no falsifiable claims",
                                               "search_tool_calls": 0})
                return

            sm.transition(JobState.CLASSIFYING)
            # 상태 그래프(ARCHITECTURE §2)는 클레임 1건의 생애를 기술하므로,
            # 클레임별로 독립 머신을 돌린다 (CLASSIFYING부터).
            degraded_any = self._process_falsifiable_claims(
                falsifiable, intake, job_id, emitter, deadline_exceeded
            )

            terminal = "job.degraded" if degraded_any else "job.completed"
            emitter.emit(terminal, {"claims_processed": len(claims)})
            return

        except Exception as e:
            if not emitter.terminated:
                emitter.emit("job.failed", {"error": str(e)})
            raise
        finally:
            # writer 스레드 정리 — 종료 이벤트 emit이 이미 flush했으므로 남은 건
            # 스레드 종료뿐이다. 호출자가 커넥션을 닫기 전에 실행돼야 한다.
            emitter.close()

    def _process_falsifiable_claims(self, falsifiable, intake, job_id, emitter,
                                    deadline_exceeded) -> bool:
        """FALSIFIABLE 클레임들을 처리하고 DEGRADED 경유 여부를 반환.

        클레임끼리는 공유 상태가 없으므로(각자 독립 StateMachine·claim_id) 동시에
        돌린다 — 클레임 N개짜리 광고의 대기 시간이 N배가 되던 구조를 없앤다.
        단, normalized_text가 같은 클레임들은 같은 canonical을 만들거나 찾는
        후보라 동시 실행 시 canonical이 중복 생성될 수 있다 (claim_canonical에는
        (industry_category_id, claim_hash) UNIQUE 제약이 없고 조회용 인덱스만
        있다). 해시로 묶어 같은 묶음은 순차로, 서로 다른 묶음만 병렬로 돌린다.

        LINER 호출은 liner_qps 리미터가 전역으로 직렬화하므로 검색 자체는
        빨라지지 않는다 — 줄어드는 건 LLM 구간(라우터/분류/가설/평가/리포터)이다.
        """
        lanes: dict[str, list[dict]] = {}
        for claim in falsifiable:
            lanes.setdefault(normalized_hash(claim["normalized_text"]), []).append(claim)
        lane_list = list(lanes.values())

        if len(lane_list) == 1:
            return self._run_claim_lane(lane_list[0], intake, job_id, emitter,
                                        deadline_exceeded)

        degraded_any = False
        first_error: BaseException | None = None
        with ThreadPoolExecutor(
            max_workers=min(len(lane_list), max(1, self.settings.max_parallel_claims)),
            thread_name_prefix=f"claim-{str(job_id)[:8]}",
        ) as ex:
            futures = [
                ex.submit(self._run_claim_lane, lane, intake, job_id, emitter,
                          deadline_exceeded)
                for lane in lane_list
            ]
            for fut in futures:
                try:
                    degraded_any |= fut.result()
                except BaseException as e:  # noqa: BLE001 — 첫 예외를 대표로 올린다
                    if first_error is None:
                        first_error = e
        if first_error is not None:
            # 순차 시절엔 첫 실패가 나머지 클레임을 중단시켰지만, 이미 발사된
            # 다른 레인은 끝까지 간 뒤 여기서 대표 예외를 올린다 (종료 이벤트는
            # 여전히 정확히 1회 — job.failed 경로는 호출자가 담당).
            raise first_error
        return degraded_any

    def _run_claim_lane(self, lane: list[dict], intake, job_id, emitter,
                        deadline_exceeded) -> bool:
        degraded = False
        for claim in lane:
            degraded |= self._process_falsifiable_claim(
                claim, intake, job_id, emitter,
                StateMachine(JobState.CLASSIFYING), deadline_exceeded,
            )
        return degraded

    def _process_falsifiable_claim(self, claim, intake, job_id, emitter, sm,
                                   deadline_exceeded) -> bool:
        """FALSIFIABLE 클레임 1건 처리. 반환: DEGRADED 경유 여부."""
        s = self.settings

        # S2a/S2b — 논리적으로 병렬 분기 (서로 의존 없음). 어느 쪽도 상대 결과를
        # 입력으로 받지 않으므로 실제로도 동시에 띄운다 — 순차로 두면 서로 무관한
        # LLM 왕복 두 번이 클레임마다 그대로 더해진다.
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="s2") as ex:
            f_route = ex.submit(run_router, claim, self.oai, s, emitter)
            f_category = ex.submit(resolve_industry_category,
                                   claim, intake, self.oai, self.db, s, emitter)
            route_out = f_route.result()
            category, similarity, is_new, embedding = f_category.result()

        # 이벤트는 병렬 실행과 무관하게 항상 route → industry 순으로 남긴다
        # (Raw Trace의 단계 순서가 실행 스케줄링에 따라 흔들리지 않도록).
        route = route_out["route"]
        emitter.emit("route.decided", {"claim_text": claim["claim_text"], **route_out})
        emitter.emit("industry.classified", {
            "category_id": category["category_id"], "label": category["label"],
            "similarity": similarity, "is_new": is_new,  # is_new=true는 UI에서 강조
        })

        claim_id = self.db.insert_claim(
            ad_id=job_id, claim_text=claim["claim_text"],
            normalized_text=claim["normalized_text"], embedding=embedding,
            claim_category="FALSIFIABLE", claim_type_code=claim["claim_type_code"],
        )
        self.db.update_claim_routing(
            claim_id, verification_route=route,
            industry_category_id=category["category_id"],
            industry_similarity=similarity,
        )

        claim_type_row = self.db.get_claim_type(claim["claim_type_code"]) or {
            "claim_type_code": claim["claim_type_code"], "default_search_budget": 3,
            "max_evidence_per_query": 3, "default_ttl_days": 30,
        }

        # S3 — 결정론적 캐시 라우팅 (LLM 아님)
        sm.transition(JobState.CACHE_CHECK)
        decision, date_from, canonical = run_cache_check(
            claim, category["category_id"], embedding,
            int(claim_type_row["default_ttl_days"]), self.db, s
        )
        emitter.emit("cache.decision", {  # 히트여도 반드시 INSERT (재사용이 보여야 함)
            "decision": decision, "date_from": date_from,
            "canonical_id": canonical["canonical_id"] if canonical else None,
            "reuse_count": canonical.get("reuse_count") if canonical else None,
        })

        if decision == "HIT":
            sm.transition(JobState.SYNTHESIZING)  # 캐시 히트 → S4~S6 검색 스킵
            assemble_from_cache(claim=claim, claim_id=claim_id, canonical=canonical,
                                oai=self.oai, db=self.db, settings=s, emitter=emitter)
            sm.transition(JobState.PERSISTING)
            sm.transition(JobState.COMPLETE)
            return False

        # MISS / DELTA / REVERIFY → S4 가설 → S5 검색·평가
        falsifier = self.db.get_falsifier_spec(claim["claim_type_code"]) or {
            "falsifier_spec_id": None,
            # 스펙이 없으면 가장 엄격하게 (fail-closed)
            "required_match_fields": {f: True for f in
                                      ("scope", "metric", "timeframe",
                                       "target_entity", "geography")},
        }
        delta_mode = decision == "DELTA"
        search_mode = "delta" if delta_mode else "full"

        # S1b — 판매/서비스 주체(브랜드) 해소. target_entity가 required인
        # claim_type(CLINICAL_COMPLETION, SELF_REPORTED_PRIVATE_METRIC 등)만
        # 대상 — 이 차원이 애초에 게이트에서 안 보는 claim_type(SUPERLATIVE_FIRST/
        # RANKING처럼 카테고리 전체 대비 반례를 찾는 유형)까지 브랜드 해소를
        # 강제하면 정당한 카테고리 단위 탐색까지 막아버린다 (구축 요청 [A]는
        # target_entity가 필요한 claim_type에 한정된 문제). CACHE_CHECK 상태에서
        # 처리해 실패 시 cache-HIT 경로와 같은 방식으로 SYNTHESIZING으로 바로
        # 빠질 수 있게 한다 (RESEARCHING은 실제 검색을 시작할 때만 진입).
        subject = None
        if falsifier["required_match_fields"].get("target_entity"):
            subject = resolve_subject(
                claim=claim, intake=intake, oai=self.oai, liner=self.liner,
                db=self.db, claim_id=claim_id, settings=s, emitter=emitter,
            )
            emitter.emit("subject.resolved", {
                "brand": subject.get("brand"), "product": subject.get("product"),
                "seller": subject.get("seller"), "resolved": subject["resolved"],
                "reasoning": subject.get("reasoning"),
            })
            if not subject["resolved"]:
                sm.transition(JobState.SYNTHESIZING)
                assemble_unresolved_subject(
                    claim=claim, claim_id=claim_id, oai=self.oai, db=self.db,
                    settings=s, emitter=emitter,
                )
                sm.transition(JobState.PERSISTING)
                sm.transition(JobState.COMPLETE)
                return False  # 시스템 실패가 아니라 결정론적 4값 판정 중 하나 — degraded 아님

        sm.transition(JobState.RESEARCHING)
        _hypotheses, queries = run_hypothesis(
            claim, route, claim_type_row, self.oai, s, emitter, subject=subject,
            category=category, delta_mode=delta_mode, date_from=date_from,
        )
        outcome = run_search_and_evaluate(
            claim=claim, claim_id=claim_id, route=route, queries=queries,
            claim_type_row=claim_type_row, falsifier_spec=falsifier,
            liner=self.liner, oai=self.oai, db=self.db, settings=s, emitter=emitter,
            deadline_check=deadline_exceeded, search_mode=search_mode,
            date_from=date_from if delta_mode else None,
        )

        degraded = bool(outcome["degraded_reason"]) or not outcome["any_search_succeeded"]
        if not outcome["any_search_succeeded"] and not outcome["degraded_reason"]:
            outcome["degraded_reason"] = "검색 프로바이더 응답 없음 (타임아웃/오류)"
        if degraded:
            # 무한 스피너 금지 — 프로바이더 장애든 시간 예산 소진이든 동일한
            # DEGRADED 경로로 결정론적 종료 (D-13, T6/T11)
            sm.transition(JobState.DEGRADED)
            sm.transition(JobState.SYNTHESIZING)
        else:
            sm.transition(JobState.EVALUATING)
            sm.transition(JobState.SYNTHESIZING)

        assemble_from_search(
            claim=claim, claim_id=claim_id, category_id=category["category_id"],
            cache_decision=decision, canonical=canonical, search_outcome=outcome,
            falsifier_spec=falsifier, embedding=embedding, oai=self.oai, db=self.db,
            settings=s, emitter=emitter, degraded_reason=outcome["degraded_reason"],
        )
        sm.transition(JobState.PERSISTING)
        sm.transition(JobState.COMPLETE)
        return degraded

    # ---- 계약 함수 2: get_job_state ----

    def get_job_state(self, job_id) -> str | None:
        events = self.db.fetch_trace_events(job_id, after_seq=0)
        state = derive_state(events)
        return state.value if state else None
