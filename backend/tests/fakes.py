"""Deterministic stand-ins for AI providers. Tests never call a real provider."""

import json
from typing import Any

import anyio

from app.ai.gateway import ErrorKind, ModelCapability, ModelGateway, ModelRequest, ProviderError
from app.ai.gateway import RawCompletion

HANG = object()  # a provider that never answers (only the gateway timeout ends it)


class FakeProvider:
    """Replays a script of outcomes, one per call; the last step repeats forever.

    A step is: a dict/list (sent as JSON text), a str (sent as-is), a RawCompletion, an
    ErrorKind (raised as ProviderError), an Exception (raised as-is) or HANG.
    """

    def __init__(self, name: str, *script: Any, model: str = "fake-model-1") -> None:
        self.name, self.model = name, model
        self.script = list(script)
        self.calls: list[ModelRequest] = []

    async def complete(
        self, request: ModelRequest, json_schema: dict[str, Any], max_output_tokens: int
    ) -> RawCompletion:
        self.calls.append(request)
        step = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if step is HANG:
            await anyio.sleep(3600)
        if isinstance(step, ErrorKind):
            raise ProviderError(step, "scripted")
        if isinstance(step, Exception):
            raise step
        if isinstance(step, RawCompletion):
            return step
        text = step if isinstance(step, str) else json.dumps(step)
        return RawCompletion(text=text, model=self.model, finish_reason="stop",
                             provider_request_id=f"{self.name}-req", input_tokens=120,
                             output_tokens=30, total_tokens=150)


class RecordingSleep:
    """Backoff without waiting: records each requested delay."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


def make_gateway(
    *providers: FakeProvider, retries: int = 1, timeout: float = 2.0, sleep: Any = None
) -> ModelGateway:
    return ModelGateway(
        {capability: list(providers) for capability in ModelCapability},
        timeout_seconds=timeout,
        max_retries=retries,
        max_output_tokens=4096,
        sleep=sleep or RecordingSleep(),
    )
