"""OpenAI 클라이언트 + Structured Outputs 헬퍼 (MODELS_AND_APIS §2).

공통 호출 규칙 (§2.4):
- 모든 분류/평가 단계는 Structured Outputs 강제. 자유 텍스트 파싱 금지.
- Structured Outputs는 구조만 보장하고 사실성은 보장하지 않음 → 판정은 별도 코드 게이트(N1).
- 스키마 위반 시 fail-closed + 재시도 1회. 2회 실패 시 예외 (job.failed 경로).
- 모델 ID는 설정에서만 읽음 (하드코딩 금지).

모든 호출은 tool.call / tool.result 이벤트를 발행한다 (provider="openai").
"""
from __future__ import annotations

import json
from typing import Any

from ..settings import Settings


class SchemaViolation(Exception):
    """structured output이 2회 연속 스키마를 위반 — fail-closed."""


class OpenAIClient:
    def __init__(self, settings: Settings, client: Any | None = None):
        self._settings = settings
        self._client = client  # 테스트 주입용. None이면 지연 생성.

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI  # noqa: PLC0415 — 키 없이도 앱이 떠야 하므로 지연 import

            self._client = OpenAI(api_key=self._settings.openai_api_key)
        return self._client

    def structured(self, *, model: str, effort: str, system: str, user: Any,
                   schema_name: str, schema: dict, emitter=None,
                   stage: str | None = None) -> dict:
        """Responses API + JSON Schema 강제. 위반 시 재시도 1회 후 fail-closed."""
        request = {
            "model": model,
            "reasoning": {"effort": effort},
            "input": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        }
        last_error: Exception | None = None
        for attempt in (0, 1):
            if emitter is not None:
                emitter.emit("tool.call", {"stage": stage, "attempt": attempt, "request": request},
                             provider="openai")
            resp = self.client.responses.create(**request)
            text = getattr(resp, "output_text", None)
            if emitter is not None:
                emitter.emit("tool.result",
                             {"stage": stage, "attempt": attempt, "output_text": text},
                             provider="openai")
            try:
                parsed = json.loads(text)
                if not isinstance(parsed, dict):
                    raise ValueError("최상위가 object가 아님")
                return parsed
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                last_error = e
                continue
        raise SchemaViolation(f"structured output 2회 실패 (stage={stage}): {last_error}")

    def vision_structured(self, *, model: str, effort: str, system: str,
                          image_b64: str, mime: str, schema_name: str, schema: dict,
                          emitter=None, stage: str | None = None) -> dict:
        user = [
            {"type": "input_text", "text": "이 광고 이미지를 분석하세요."},
            {"type": "input_image", "image_url": f"data:{mime};base64,{image_b64}"},
        ]
        return self.structured(model=model, effort=effort, system=system, user=user,
                               schema_name=schema_name, schema=schema,
                               emitter=emitter, stage=stage)

    def embed(self, text: str) -> list[float]:
        resp = self.client.embeddings.create(
            model=self._settings.model_embedding, input=text
        )
        return list(resp.data[0].embedding)
