"""테스트용 인메모리 Fake들.

FakeDb는 chk_evidence_only_if_refuted 제약을 코드로 흉내낸다 —
실 DB(T9)와 별개로, 파이프라인 배선 실수를 로컬 테스트에서도 잡기 위해.
"""
from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone

from counter.clients.liner import SearchResponse, SearchResult
from counter.db import normalized_hash


class FakeDb:
    def __init__(self):
        self.trace_events: list[dict] = []
        self.verdicts: list[dict] = []
        self.candidates: list[dict] = []
        self.feedback: list[dict] = []
        self.search_logs: list[dict] = []
        self.canonicals: dict[tuple[int, str], dict] = {}
        self.categories: list[dict] = [
            {"id": 1, "code": "cosmetics_beauty", "label_ko": "화장품/뷰티",
             "created_by": "seed", "similarity": 0.9},
        ]
        self._ids = itertools.count(100)
        self.claim_types = {
            "SUPERLATIVE_FIRST": {"code": "SUPERLATIVE_FIRST", "default_search_budget": 4,
                                  "max_evidence_per_query": 5, "default_ttl_days": 180},
            "CLINICAL_COMPLETION": {"code": "CLINICAL_COMPLETION", "default_search_budget": 3,
                                    "max_evidence_per_query": 5, "default_ttl_days": 90},
            "GENERAL_FACTUAL": {"code": "GENERAL_FACTUAL", "default_search_budget": 4,
                                "max_evidence_per_query": 5, "default_ttl_days": 60},
        }
        self.falsifier_specs = {
            "SUPERLATIVE_FIRST": {"required_match_fields": {
                "scope_match": True, "metric_match": True,
                "timeframe_match": True, "target_match": False}},
            "CLINICAL_COMPLETION": {"required_match_fields": {
                "scope_match": True, "metric_match": False,
                "timeframe_match": False, "target_match": True}},
            "GENERAL_FACTUAL": {"required_match_fields": {
                "scope_match": True, "metric_match": False,
                "timeframe_match": True, "target_match": True}},
        }

    # trace
    def insert_trace_event(self, job_id, seq, event_type, provider, payload):
        for ev in self.trace_events:
            if ev["job_id"] == job_id and ev["seq"] == seq:
                raise AssertionError("uq_trace_event_job_seq 위반")
        self.trace_events.append({"job_id": job_id, "seq": seq, "event_type": event_type,
                                  "provider": provider, "payload": payload,
                                  "created_at": datetime.now(timezone.utc)})

    def fetch_trace_events(self, job_id, after_seq=0):
        return sorted([e for e in self.trace_events
                       if str(e["job_id"]) == str(job_id) and e["seq"] > after_seq],
                      key=lambda e: e["seq"])

    # 참조 데이터
    def get_claim_type(self, code):
        return self.claim_types.get(code)

    def get_falsifier_spec(self, code):
        return self.falsifier_specs.get(code)

    # 카테고리
    def nearest_categories(self, embedding, k=5):
        return list(self.categories)

    def create_category(self, code, label_ko, embedding):
        row = {"id": next(self._ids), "code": code, "label_ko": label_ko,
               "created_by": "agent_generated"}
        self.categories.append({**row, "similarity": 0.99})
        return row

    def get_default_category(self):
        return {"id": 0, "code": "uncategorized", "label_ko": "미분류", "created_by": "seed"}

    # canonical (파티션 키 = industry_category_id — D-08)
    def find_canonical_by_hash(self, category_id, nhash):
        return self.canonicals.get((category_id, nhash))

    def find_canonical_by_vector(self, category_id, embedding, threshold):
        for (cid, _), row in self.canonicals.items():
            if cid == category_id:
                return row
        return None

    def upsert_canonical(self, *, category_id, claim_type_code, normalized_text,
                         embedding, verdict_code, evidence_link, evidence_date,
                         explanation, executed_queries, ttl_days):
        if verdict_code != "REFUTED" and evidence_link is not None:
            raise AssertionError("chk_evidence_only_if_refuted 위반 (canonical)")
        key = (category_id, normalized_hash(normalized_text))
        row = self.canonicals.get(key) or {"id": next(self._ids), "reuse_count": 0,
                                           "agree_count": 0, "dispute_count": 0}
        row.update({
            "industry_category_id": category_id, "claim_type_code": claim_type_code,
            "normalized_text": normalized_text, "verdict_code": verdict_code,
            "evidence_link": evidence_link, "evidence_date": evidence_date,
            "explanation": explanation, "executed_queries": executed_queries,
            "ttl_days": ttl_days, "verified_at": datetime.now(timezone.utc),
            "needs_reverification": False,
        })
        self.canonicals[key] = row
        return row["id"]

    def bump_canonical_reuse(self, canonical_id):
        for row in self.canonicals.values():
            if row["id"] == canonical_id:
                row["reuse_count"] += 1

    def expire_canonical(self, canonical_id, days=999):
        for row in self.canonicals.values():
            if row["id"] == canonical_id:
                row["verified_at"] -= timedelta(days=days)

    # verdict / candidate / feedback / log
    def insert_verdict(self, row):
        if row["verdict_code"] != "REFUTED" and row.get("evidence_link") is not None:
            raise AssertionError("chk_evidence_only_if_refuted 위반 (verdict)")
        row = dict(row)
        row["id"] = f"v{next(self._ids)}"
        self.verdicts.append(row)
        return row["id"]

    def fetch_verdicts(self, job_id):
        return [v for v in self.verdicts if str(v["job_id"]) == str(job_id)]

    def get_verdict(self, verdict_id):
        return next((v for v in self.verdicts if v["id"] == verdict_id), None)

    def insert_candidate(self, **kw):
        self.candidates.append(kw)

    def insert_feedback(self, verdict_id, reaction, note):
        self.feedback.append({"verdict_id": verdict_id, "reaction": reaction, "note": note})

    def bump_canonical_feedback(self, canonical_id, reaction):
        col = "agree_count" if reaction == "AGREE" else "dispute_count"
        for row in self.canonicals.values():
            if row["id"] == canonical_id:
                row[col] += 1

    def apply_dispute_policy(self, canonical_id, count_threshold, ratio_threshold):
        for row in self.canonicals.values():
            if row["id"] == canonical_id:
                total = max(row["agree_count"] + row["dispute_count"], 1)
                if (row["dispute_count"] >= count_threshold
                        and row["dispute_count"] / total >= ratio_threshold):
                    row["needs_reverification"] = True
                    return True
        return False

    def insert_search_log(self, **kw):
        self.search_logs.append(kw)


class FakeOpenAI:
    """stage 이름으로 canned 응답을 돌려준다. 호출 내역을 기록."""

    def __init__(self, responses: dict):
        self.responses = responses  # stage → dict | callable | list(순차)
        self.calls: list[str] = []

    def structured(self, *, model, effort, system, user, schema_name, schema,
                   emitter=None, stage=None):
        self.calls.append(stage)
        if emitter is not None:
            emitter.emit("tool.call", {"stage": stage, "request": {"model": model}},
                         provider="openai")
            emitter.emit("tool.result", {"stage": stage}, provider="openai")
        resp = self.responses[stage]
        if isinstance(resp, list):
            resp = resp.pop(0) if len(resp) > 1 else resp[0]
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
                  "target_match": True, "evidence_quote": "2019년 출시",
                  "is_syndicated_copy": False, "insufficient_access": False,
                  "reasoning": "동일 범주·지표·시점"}

EVAL_PARTIAL = {**EVAL_ALL_MATCH, "timeframe_match": False}

DEFAULT_RESPONSES = {
    "S1_TRIAGE": TRIAGE_SUPERLATIVE,
    "S2A_ROUTER": {"route": "GENERAL", "reasoning": "일반 사실관계"},
    "S2B_LABELER": {"code": "new_industry", "label_ko": "신규 업종"},
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
