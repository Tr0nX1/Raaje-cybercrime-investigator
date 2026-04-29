from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.config.settings import Settings
from app.models.request_models import TransactionInput
from app.models.response_models import AuditResponse, OllamaHealthStatus
from app.services.prompt_builder import build_transaction_audit_prompt
from app.utils.validators import (
    build_fallback_response,
    normalize_model_payload,
    parse_json_object_from_text,
)


class OllamaLLMEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.logger = logging.getLogger("llm_service.ollama")

    async def audit_transaction(
        self,
        transaction: TransactionInput,
        request_id: str = "",
    ) -> AuditResponse:
        prompt = build_transaction_audit_prompt(transaction)
        started_at = time.perf_counter()

        for attempt in range(1, self.settings.ollama_retries + 2):
            try:
                raw_response = await self._call_ollama(prompt)
                content = self._extract_message_content(raw_response)
                parsed = parse_json_object_from_text(content)
                normalized = normalize_model_payload(parsed, transaction)
                elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
                self.logger.info(
                    "audit_success request_id=%s attempt=%s duration_ms=%s",
                    request_id,
                    attempt,
                    elapsed_ms,
                )
                return AuditResponse(**normalized)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                self.logger.warning(
                    "ollama_network_error request_id=%s attempt=%s error=%s",
                    request_id,
                    attempt,
                    exc,
                )
                if attempt > self.settings.ollama_retries:
                    break
            except (ValueError, json.JSONDecodeError) as exc:
                self.logger.warning(
                    "ollama_parse_error request_id=%s attempt=%s error=%s",
                    request_id,
                    attempt,
                    exc,
                )
                break
            except Exception as exc:  # pragma: no cover - defensive guard
                self.logger.exception(
                    "ollama_unexpected_error request_id=%s attempt=%s error=%s",
                    request_id,
                    attempt,
                    exc,
                )
                break

        fallback = build_fallback_response(transaction)
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        self.logger.info(
            "audit_fallback request_id=%s duration_ms=%s confidence=%s",
            request_id,
            elapsed_ms,
            fallback["confidence"],
        )
        return AuditResponse(**fallback)

    async def health_check(self) -> OllamaHealthStatus:
        try:
            async with self._build_client() as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
            return OllamaHealthStatus(connected=True, status="reachable")
        except Exception as exc:
            self.logger.warning("health_check_failed error=%s", exc)
            return OllamaHealthStatus(connected=False, status="unreachable")

    async def list_models(self) -> list[str]:
        try:
            async with self._build_client() as client:
                response = await client.get("/api/tags")
                response.raise_for_status()
            payload = response.json()
            return [model.get("name", "") for model in payload.get("models", []) if model.get("name")]
        except Exception as exc:
            self.logger.warning("list_models_failed error=%s", exc)
            return []

    async def _call_ollama(self, prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.settings.ollama_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only valid JSON that matches the requested schema. "
                        "Never include markdown fences or explanatory text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self.settings.ollama_temperature,
            },
        }
        async with self._build_client() as client:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            return response.json()

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.settings.ollama_base_url,
            timeout=httpx.Timeout(self.settings.ollama_timeout_seconds),
        )

    @staticmethod
    def _extract_message_content(payload: dict[str, Any]) -> str:
        message = payload.get("message", {})
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
        if isinstance(payload.get("response"), str):
            return payload["response"]
        raise ValueError("Ollama response does not contain text content")
