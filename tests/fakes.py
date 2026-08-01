"""테스트용 인메모리 Fake들 (counter/db.py 인터페이스와 1:1).

FakeDb는 chk_evidence_only_if_refuted 제약을 코드로 흉내낸다 —
실 DB(T9)와 별개로, 파이프라인 배선 실수를 로컬 테스트에서도 잡기 위해.
"""
from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone

from counter.clients.liner import SearchResponse, SearchResult
from counter.db import normalized_hash

_counter = itertools.count(100)


def _nid(prefix: str) -> str:
    return f"{prefix}{next(_counter)}"


class FakeDb:
    def __init__(self):
        self.trace_events: list[dict] = []
        self.sessions: list[dict] = []
        self.ads: list[dict] = []
        self.claims: dict[str, dict] = {}
        self.canonicals: dict[str, dict] = {}
        self.search_logs: list[dict] = []
        self.evidences: dict[str, dict] = {}
        self.candidates: list[dict] = []
        self.verdicts: list[dict] = []
        self.feedback: list[dict] = []
        self.categories: list[dict] = [
            {"category_id": "BEAUTY_PERSONAL_CARE", "label": "뷰티/퍼스널케어",
             "created_by": "seed", "similarity": 0.9},
        ]
        self.claim_types = {
            "SUPERLATIVE_FIRST": {"claim_type_code": "SUPERLATIVE_FIRST",
                                  "requires_search": True, "default_search_budget": 4,
                                  "default_ttl_days": 180, "max_evidence_per_query": 3},
            "RANKING": {"claim_type_code": "RANKING", "requires_search": True,
                        "default_search_budget": 4, "default_ttl_days": 30,
                        "max_evidence_per_query": 3},
            "CLINICAL_COMPLETION": {"claim_type_code": "CLINICAL_COMPLETION",
                                    "requires_search": True, "default_search_budget": 3,
                                    "default_ttl_days": 60, "max_evidence_per_query": 3},
            "GENERAL_FACTUAL": {"claim_type_code": "GENERAL_FACTUAL",
                                "requires_search": True, "default_search_budget": 3,
                                "default_ttl_days": 30, "max_evidence_per_query": 3},
            "SELF_REPORTED_PRIVATE_METRIC": {
                "claim_type_code": "SELF_REPORTED_PRIVATE_METRIC",
                "requires_search": True, "default_search_budget": 3,
                "default_ttl_days": 90, "max_evidence_per_query": 3},
            "PUFFERY": {"claim_type_code": "PUFFERY", "requires_search": False,
                        "default_search_budget": 0, "default_ttl_days": 999,
                        "max_evidence_per_query": 0},
        }
        # DB_SCHEMA.md falsifier_spec 초기값 표 그대로
        self.falsifier_specs = {
            "SUPERLATIVE_FIRST": {"falsifier_spec_id": "fs1", "required_match_fields": {
                "scope": True, "metric": False, "timeframe": True,
                "target_entity": False, "geography": False}},
            "RANKING": {"falsifier_spec_id": "fs2", "required_match_fields": {
                "scope": False, "metric": True, "timeframe": True,
                "target_entity": False, "geography": True}},
            "CLINICAL_COMPLETION": {"falsifier_spec_id": "fs3", "required_match_fields": {
                "scope": False, "metric": False, "timeframe": False,
                "target_entity": True, "geography": False}},
            "GENERAL_FACTUAL": {"falsifier_spec_id": "fs4", "required_match_fields": {
                "scope": True, "metric": False, "timeframe": True,
                "target_entity": False, "geography": False}},
            "SELF_REPORTED_PRIVATE_METRIC": {"falsifier_spec_id": "fs5",
                "required_match_fields": {
                    "scope": True, "metric": True, "timeframe": True,
                    "target_entity": True, "geography": False}},
        }

    def close(self) -> None:
        """실제 Db.close()와 인터페이스 대칭 — run_job_async의 스레드 정리 경로가
        FakeDb 주입 시에도 그대로 동작하도록."""

    # trace
    def insert_trace_event(self, job_id, seq, event_type, provider, payload):
        for ev in self.trace_events:
            if ev["job_id"] == str(job_id) and ev["seq"] == seq:
                raise AssertionError("trace_event (job_id, seq) 중복")
        self.trace_events.append({"job_id": str(job_id), "seq": seq,
                                  "event_type": event_type, "provider": provider,
                                  "payload": payload,
                                  "created_at": datetime.now(timezone.utc)})

    def fetch_trace_events(self, job_id, after_seq=0):
        return sorted([e for e in self.trace_events
                       if e["job_id"] == str(job_id) and e["seq"] > after_seq],
                      key=lambda e: e["seq"])

    # session / ad
    def insert_session(self, source_app="web"):
        sid = _nid("s")
        self.sessions.append({"session_id": sid, "source_app": source_app})
        return sid

    def insert_ad(self, **kw):
        self.ads.append(kw)

    # claim
    def insert_claim(self, *, ad_id, claim_text, normalized_text, embedding,
                     claim_category, claim_type_code):
        cid = _nid("c")
        self.claims[cid] = {
            "claim_id": cid, "ad_id": ad_id, "claim_text": claim_text,
            "normalized_text": normalized_text,
            "claim_hash": normalized_hash(normalized_text), "embedding": embedding,
            "claim_category": claim_category, "claim_type_code": claim_type_code,
            "verification_route": None, "industry_category_id": None,
            "canonical_id": None,
        }
        return cid

    def update_claim_routing(self, claim_id, *, verification_route=None,
                             industry_category_id=None, industry_similarity=None,
                             canonical_id=None):
        c = self.claims[claim_id]
        if verification_route is not None:
            c["verification_route"] = verification_route
        if industry_category_id is not None:
            c["industry_category_id"] = industry_category_id
        if industry_similarity is not None:
            c["industry_similarity"] = industry_similarity
        if canonical_id is not None:
            c["canonical_id"] = canonical_id

    # 참조 데이터
    def get_claim_type(self, code):
        return self.claim_types.get(code)

    def get_falsifier_spec(self, code):
        return self.falsifier_specs.get(code)

    # 카테고리
    def nearest_categories(self, embedding, k=5):
        return list(self.categories)

    def create_category(self, category_id, label, embedding):
        row = {"category_id": category_id, "label": label,
               "created_by": "agent_generated"}
        self.categories.append({**row, "similarity": 0.99})
        return row

    def get_default_category(self):
        return {"category_id": "UNCATEGORIZED", "label": "미분류 (폴백)",
                "created_by": "seed"}

    def set_category_centroid(self, category_id, embedding):
        pass

    # canonical (파티션 키 = industry_category_id — D-08)
    def find_canonical_by_hash(self, category_id, claim_hash):
        for row in self.canonicals.values():
            if (row["industry_category_id"] == category_id
                    and row["claim_hash"] == claim_hash):
                return dict(row)
        return None

    def find_canonical_by_vector(self, category_id, embedding, threshold):
        for row in self.canonicals.values():
            if row["industry_category_id"] == category_id:
                return dict(row)
        return None

    def touch_canonical_seen(self, canonical_id):
        row = self.canonicals[canonical_id]
        row["member_count"] += 1
        row["last_seen_at"] = datetime.now(timezone.utc)

    def bump_canonical_reuse(self, canonical_id):
        self.canonicals[canonical_id]["reuse_count"] += 1

    def create_canonical(self, *, representative_claim_id, claim_type_code,
                         industry_category_id, claim_hash, embedding,
                         similarity_threshold_used):
        cid = _nid("can")
        self.canonicals[cid] = {
            "canonical_id": cid, "representative_claim_id": representative_claim_id,
            "claim_type_code": claim_type_code,
            "industry_category_id": industry_category_id, "claim_hash": claim_hash,
            "embedding_centroid": embedding, "member_count": 1, "reuse_count": 0,
            "agree_count": 0, "dispute_count": 0, "needs_reverification": False,
            "last_seen_at": datetime.now(timezone.utc),
            "last_searched_at": datetime.now(timezone.utc),
        }
        return cid

    def mark_canonical_searched(self, canonical_id):
        row = self.canonicals[canonical_id]
        row["last_searched_at"] = datetime.now(timezone.utc)
        row["needs_reverification"] = False

    def expire_canonical(self, canonical_id, days=999):
        self.canonicals[canonical_id]["last_searched_at"] -= timedelta(days=days)

    # search_log / evidence / candidate
    def insert_search_log(self, **kw):
        lid = _nid("log")
        self.search_logs.append({"log_id": lid, **kw})
        return lid

    def link_search_logs_to_canonical(self, claim_id, canonical_id):
        for log in self.search_logs:
            if log.get("claim_id") == claim_id and log.get("canonical_id") is None:
                log["canonical_id"] = canonical_id

    def insert_evidence(self, **kw):
        eid = _nid("ev")
        self.evidences[eid] = {"evidence_id": eid, **kw}
        return eid

    def insert_candidate(self, **kw):
        cid = _nid("cand")
        self.candidates.append({"candidate_id": cid, **kw})
        return cid

    # verdict / feedback
    def insert_verdict(self, *, claim_id, canonical_id, verdict_code, evidence_link,
                       evidence_date, search_count, confidence_source,
                       required_evidence_note, reasoning, assembled_by="agent"):
        if verdict_code != "REFUTED" and evidence_link is not None:
            raise AssertionError("chk_evidence_only_if_refuted 위반 (verdict)")
        vid = _nid("v")
        self.verdicts.append({
            "verdict_id": vid, "claim_id": claim_id, "canonical_id": canonical_id,
            "verdict_code": verdict_code, "evidence_link": evidence_link,
            "evidence_date": evidence_date, "search_count": search_count,
            "confidence_source": confidence_source,
            "required_evidence_note": required_evidence_note, "reasoning": reasoning,
            "assembled_by": assembled_by,
            "created_at": datetime.now(timezone.utc),
        })
        return vid

    def latest_verdict_for_canonical(self, canonical_id):
        rows = [v for v in self.verdicts if v["canonical_id"] == canonical_id]
        return dict(rows[-1]) if rows else None

    def fetch_verdicts(self, job_id):
        out = []
        for v in self.verdicts:
            claim = self.claims.get(v["claim_id"])
            if claim and claim["ad_id"] == str(job_id):
                out.append({**v, "claim_text": claim["claim_text"],
                            "claim_category": claim["claim_category"]})
        return out

    def fetch_executed_queries(self, claim_id, canonical_id):
        return sorted({log["query_text"] for log in self.search_logs
                       if log.get("claim_id") == claim_id
                       or (canonical_id and log.get("canonical_id") == canonical_id)})

    def fetch_evidence_reviewed(self, claim_id, canonical_id=None):
        log_ids = {log["log_id"] for log in self.search_logs
                  if log.get("claim_id") == claim_id
                  or (canonical_id and log.get("canonical_id") == canonical_id)}
        out = []
        for ev in self.evidences.values():
            if ev.get("log_id") not in log_ids:
                continue
            cand = next((c for c in self.candidates if c.get("evidence_id") == ev["evidence_id"]),
                       None)
            out.append({
                "url": ev.get("url"), "title": ev.get("title"), "snippet": ev.get("snippet"),
                "published_date": ev.get("published_date"), "source_domain": ev.get("source_domain"),
                "applicability_check": cand.get("applicability_check") if cand else None,
                "reasoning": cand.get("reasoning") if cand else None,
            })
        return out

    def get_verdict(self, verdict_id):
        return next((dict(v) for v in self.verdicts if v["verdict_id"] == verdict_id), None)

    def insert_feedback(self, verdict_id, reaction, note, source="end_user"):
        self.feedback.append({"verdict_id": verdict_id, "reaction": reaction,
                              "user_note": note, "source": source})

    def bump_canonical_feedback(self, canonical_id, reaction):
        col = "agree_count" if reaction == "AGREE" else "dispute_count"
        self.canonicals[canonical_id][col] += 1

    def apply_dispute_policy(self, canonical_id, count_threshold, ratio_threshold):
        row = self.canonicals[canonical_id]
        total = max(row["agree_count"] + row["dispute_count"], 1)
        if (row["dispute_count"] >= count_threshold
                and row["dispute_count"] / total >= ratio_threshold):
            row["needs_reverification"] = True
            return True
        return False


class FakeOpenAI:
    """stage 이름으로 canned 응답을 돌려준다. 호출 내역을 기록."""

    def __init__(self, responses: dict):
        self.responses = responses
        self.calls: list[str] = []

    def structured(self, *, model, effort, system, user, schema_name, schema,
                   emitter=None, stage=None):
        self.calls.append(stage)
        if emitter is not None:
            emitter.emit("tool.call", {"stage": stage, "request": {"model": model}},
                         provider="openai")
            emitter.emit("tool.result", {"stage": stage}, provider="openai")
        resp = self.responses[stage]
        return resp(user) if callable(resp) else dict(resp)

    def vision_structured(self, **kw):
        return self.structured(model=kw.get("model"), effort=kw.get("effort"),
                               system=kw.get("system"), user="[image]",
                               schema_name=kw.get("schema_name"), schema=kw.get("schema"),
                               emitter=kw.get("emitter"), stage=kw.get("stage"))

    def embed(self, text):
        return [0.1, 0.2, 0.3]


class FakeLiner:
    def __init__(self, results: list[SearchResult] | None = None, status: str = "ok"):
        self.results = results or []
        self.status = status
        self.calls: list[dict] = []

    def search(self, mode, query, date_from=None, max_results=10):
        self.calls.append({"mode": mode, "query": query, "date_from": date_from})
        if self.status != "ok":
            return SearchResponse(False, self.status, None, [], None)
        return SearchResponse(True, "ok", "req-123", self.results,
                              {"results": [r.__dict__ for r in self.results]})


def make_result(url="https://news.example.com/a", date="2019-05-01",
                title="2019년 국내 최초 진공 블렌더 출시", snippet="타사가 2019년에 먼저 출시"):
    return SearchResult(title=title, url=url, snippet=snippet, date=date, extra={})


TRIAGE_SUPERLATIVE = {
    "claims": [{
        "claim_text": "국내 최초 진공 블렌더", "normalized_text": "국내 최초 진공 블렌더",
        "claim_category": "FALSIFIABLE", "claim_type_code": "SUPERLATIVE_FIRST",
        "missing_comparator": False, "reasoning": "최초 주장",
    }],
}

TRIAGE_PUFFERY = {
    "claims": [{
        "claim_text": "우리 김밥이 제일 맛있다", "normalized_text": "김밥 제일 맛있다",
        "claim_category": "PUFFERY", "claim_type_code": None,
        "missing_comparator": False, "reasoning": "주관적 표현",
    }],
}

EVAL_ALL_MATCH = {"scope_match": True, "metric_match": True, "timeframe_match": True,
                  "target_match": True, "geography_match": True,
                  "evidence_quote": "2019년 출시", "is_syndicated_copy": False,
                  "insufficient_access": False, "reasoning": "동일 범주·지표·시점"}

EVAL_PARTIAL = {**EVAL_ALL_MATCH, "timeframe_match": False}

DEFAULT_RESPONSES = {
    "S1_TRIAGE": TRIAGE_SUPERLATIVE,
    "S2A_ROUTER": {"route": "GENERAL", "reasoning": "일반 사실관계"},
    "S2B_LABELER": {"code": "NEW_INDUSTRY", "label_ko": "신규 업종"},
    "S4_HYPOTHESIS": {"hypotheses": [{
        "hypothesis": "선행 출시 사례가 존재한다",
        "what_must_exist": "더 이른 출시 기록",
        "queries": [{"query_text": "국내 최초 진공 블렌더 2019", "language": "ko"},
                    {"query_text": "진공 블렌더 최초 출시 연도", "language": "ko"}],
    }]},
    "S5_EVALUATOR": EVAL_ALL_MATCH,
    "S6_REPORTER": {"explanation": "반례 문서가 확인되었습니다.", "executed_queries": []},
    "S6_GUARDRAIL_LLM": {"contains_banned_vocabulary": False, "reasoning": "없음"},
}


def make_pipeline(settings=None, db=None, oai_responses=None, liner=None):
    from counter.pipeline.orchestrator import Pipeline
    from counter.settings import Settings

    responses = dict(DEFAULT_RESPONSES)
    if oai_responses:
        responses.update(oai_responses)
    return Pipeline(
        settings=settings or Settings(job_timeout_seconds=300.0),
        db=db or FakeDb(),
        oai=FakeOpenAI(responses),
        liner=liner or FakeLiner([make_result()]),
    )
