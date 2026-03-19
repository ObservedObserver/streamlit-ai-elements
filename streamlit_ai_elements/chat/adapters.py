"""Backend adapters that normalize streaming events into one timeline model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from .tools import build_chat_completions_tools, build_responses_tools
from .types import ChatBackendConfig, ChatEvent, make_event


@dataclass(slots=True)
class StreamingAdapterRequest:
    config: ChatBackendConfig
    instructions: str
    messages: list[dict[str, Any]]
    tool_outputs: list[dict[str, Any]] = field(default_factory=list)
    previous_response_id: str | None = None


@dataclass(slots=True)
class _TrackedToolCall:
    call_id: str
    name: str
    arguments: str = ""
    raw_id: str | None = None


class ResponsesStreamAdapter:
    """Normalize Responses API SSE events into chat timeline events."""

    def __init__(self) -> None:
        self.last_response_id: str | None = None
        self._tool_calls_by_index: dict[int, _TrackedToolCall] = {}
        self._tool_calls_by_item_id: dict[str, _TrackedToolCall] = {}
        self._reasoning_done_ids: set[str] = set()

    def stream(self, client: Any, request: StreamingAdapterRequest) -> Iterator[ChatEvent]:
        kwargs: dict[str, Any] = {
            "model": request.config.model,
            "instructions": request.instructions,
            "tools": build_responses_tools(),
            "stream": True,
        }
        if request.previous_response_id:
            kwargs["previous_response_id"] = request.previous_response_id
            kwargs["input"] = list(request.tool_outputs)
        else:
            kwargs["input"] = list(request.messages)
        if request.config.reasoning_effort:
            reasoning: dict[str, Any] = {"effort": request.config.reasoning_effort}
            if request.config.reasoning_summary:
                reasoning["summary"] = request.config.reasoning_summary
            kwargs["reasoning"] = reasoning
        if request.config.temperature is not None:
            kwargs["temperature"] = request.config.temperature
        if request.config.max_output_tokens is not None:
            kwargs["max_output_tokens"] = request.config.max_output_tokens
        kwargs.update(request.config.extra_request_options)

        stream = client.responses.create(**kwargs)
        for raw_event in stream:
            yield from self._normalize_event(raw_event)

    def _normalize_event(self, raw_event: Any) -> Iterator[ChatEvent]:
        event_type = _get_value(raw_event, "type")
        if not event_type:
            return

        if event_type == "response.created":
            self.last_response_id = _first_non_empty(
                _get_value(raw_event, "response.id"),
                _get_value(raw_event, "response_id"),
            )
            return

        if event_type == "response.output_text.delta":
            yield make_event(
                "text_delta",
                delta=_get_value(raw_event, "delta", "") or "",
                backend_response_id=self.last_response_id,
            )
            return

        if event_type in {"response.reasoning_summary_text.delta", "response.reasoning.delta"}:
            yield make_event(
                "reasoning_delta",
                delta=_get_value(raw_event, "delta", "") or "",
                backend_response_id=self.last_response_id,
            )
            return

        if event_type == "response.output_item.added":
            item = _get_value(raw_event, "item") or {}
            if _get_value(item, "type") == "function_call":
                tracked = _TrackedToolCall(
                    call_id=_first_non_empty(_get_value(item, "call_id"), _get_value(item, "id"), f"call_{_get_value(raw_event, 'output_index', 0)}"),
                    name=_get_value(item, "name", "tool") or "tool",
                    arguments=_get_value(item, "arguments", "") or "",
                    raw_id=_get_value(item, "id"),
                )
                output_index = int(_get_value(raw_event, "output_index", 0) or 0)
                self._tool_calls_by_index[output_index] = tracked
                if tracked.raw_id:
                    self._tool_calls_by_item_id[tracked.raw_id] = tracked
                yield make_event(
                    "tool_call_started",
                    tool_call_id=tracked.call_id,
                    tool_name=tracked.name,
                    arguments=tracked.arguments,
                    backend_response_id=self.last_response_id,
                )
            return

        if event_type == "response.function_call_arguments.delta":
            tracked = self._tracked_tool_call(raw_event)
            if tracked is None:
                return
            delta = _get_value(raw_event, "delta", "") or ""
            tracked.arguments += delta
            yield make_event(
                "tool_call_delta",
                tool_call_id=tracked.call_id,
                tool_name=tracked.name,
                delta=delta,
                backend_response_id=self.last_response_id,
            )
            return

        if event_type == "response.function_call_arguments.done":
            item = _get_value(raw_event, "item") or {}
            tracked = self._tracked_tool_call(raw_event)
            if tracked is None:
                tracked = _TrackedToolCall(
                    call_id=_first_non_empty(_get_value(item, "call_id"), _get_value(item, "id"), "tool_call"),
                    name=_get_value(item, "name", "tool") or "tool",
                )
            tracked.arguments = _get_value(item, "arguments", tracked.arguments) or tracked.arguments
            yield make_event(
                "tool_call_completed",
                tool_call_id=tracked.call_id,
                tool_name=tracked.name,
                arguments=tracked.arguments,
                backend_response_id=self.last_response_id,
            )
            return

        if event_type == "response.output_item.done":
            item = _get_value(raw_event, "item") or {}
            if _get_value(item, "type") != "reasoning":
                return
            item_id = _get_value(item, "id")
            if item_id in self._reasoning_done_ids:
                return
            summary = _flatten_reasoning_summary(item)
            if not summary:
                return
            self._reasoning_done_ids.add(item_id)
            yield make_event(
                "reasoning_delta",
                delta=summary,
                backend_response_id=self.last_response_id,
            )
            return

        if event_type in {"response.failed", "error"}:
            yield make_event(
                "message_error",
                error=_extract_error_message(raw_event),
                backend_response_id=self.last_response_id,
            )

    def _tracked_tool_call(self, raw_event: Any) -> _TrackedToolCall | None:
        item_id = _get_value(raw_event, "item_id")
        if item_id and item_id in self._tool_calls_by_item_id:
            return self._tool_calls_by_item_id[item_id]
        output_index = _get_value(raw_event, "output_index")
        if output_index is None:
            return None
        return self._tool_calls_by_index.get(int(output_index))


class ChatCompletionsStreamAdapter:
    """Normalize Chat Completions streaming chunks into chat timeline events."""

    def __init__(self) -> None:
        self._tool_calls_by_index: dict[int, _TrackedToolCall] = {}

    def stream(self, client: Any, request: StreamingAdapterRequest) -> Iterator[ChatEvent]:
        kwargs: dict[str, Any] = {
            "model": request.config.model,
            "messages": list(request.messages),
            "tools": build_chat_completions_tools(),
            "stream": True,
        }
        if request.config.reasoning_effort:
            kwargs["reasoning"] = {"effort": request.config.reasoning_effort}
        if request.config.temperature is not None:
            kwargs["temperature"] = request.config.temperature
        kwargs.update(request.config.extra_request_options)

        stream = client.chat.completions.create(**kwargs)
        for chunk in stream:
            yield from self._normalize_chunk(chunk)

    def _normalize_chunk(self, chunk: Any) -> Iterator[ChatEvent]:
        choice = _get_first_choice(chunk)
        if choice is None:
            return

        delta = _get_value(choice, "delta") or {}
        text_delta = _coerce_text_delta(delta)
        if text_delta:
            yield make_event("text_delta", delta=text_delta)

        reasoning_delta = _coerce_reasoning_delta(delta)
        if reasoning_delta:
            yield make_event("reasoning_delta", delta=reasoning_delta)

        for tool_delta in _normalize_tool_call_deltas(delta):
            index = int(tool_delta.get("index", 0) or 0)
            tracked = self._tool_calls_by_index.get(index)
            if tracked is None:
                tracked = _TrackedToolCall(
                    call_id=_first_non_empty(tool_delta.get("id"), f"call_{index}"),
                    name=_nested_get(tool_delta, ("function", "name")) or "tool",
                )
                self._tool_calls_by_index[index] = tracked
                yield make_event(
                    "tool_call_started",
                    tool_call_id=tracked.call_id,
                    tool_name=tracked.name,
                    arguments="",
                )
            if _nested_get(tool_delta, ("function", "name")):
                tracked.name = _nested_get(tool_delta, ("function", "name"))
            arguments_delta = _nested_get(tool_delta, ("function", "arguments")) or ""
            if arguments_delta:
                tracked.arguments += arguments_delta
                yield make_event(
                    "tool_call_delta",
                    tool_call_id=tracked.call_id,
                    tool_name=tracked.name,
                    delta=arguments_delta,
                )

        finish_reason = _get_value(choice, "finish_reason")
        if finish_reason == "tool_calls":
            for tracked in self._tool_calls_by_index.values():
                yield make_event(
                    "tool_call_completed",
                    tool_call_id=tracked.call_id,
                    tool_name=tracked.name,
                    arguments=tracked.arguments,
                )
        elif finish_reason in {"stop", "length"}:
            return


def _get_first_choice(chunk: Any) -> Any | None:
    choices = _get_value(chunk, "choices")
    if isinstance(choices, list) and choices:
        return choices[0]
    if hasattr(choices, "__iter__"):
        choices = list(choices)
        return choices[0] if choices else None
    return None


def _coerce_text_delta(delta: Any) -> str:
    content = _get_value(delta, "content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") in {"text", "output_text"}:
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return ""


def _coerce_reasoning_delta(delta: Any) -> str:
    for key in ("reasoning", "reasoning_content", "thinking"):
        value = _get_value(delta, key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(str(item.get("text", "")))
            joined = "".join(parts)
            if joined:
                return joined
    return ""


def _normalize_tool_call_deltas(delta: Any) -> list[dict[str, Any]]:
    tool_calls = _get_value(delta, "tool_calls")
    if not tool_calls:
        return []
    if isinstance(tool_calls, list):
        normalized: list[dict[str, Any]] = []
        for item in tool_calls:
            if isinstance(item, dict):
                normalized.append(item)
            else:
                normalized.append(_to_dict(item))
        return normalized
    return []


def _flatten_reasoning_summary(item: Any) -> str:
    summary = _get_value(item, "summary")
    if isinstance(summary, str):
        return summary
    if not isinstance(summary, list):
        return ""

    parts: list[str] = []
    for entry in summary:
        if isinstance(entry, str):
            parts.append(entry)
            continue
        if isinstance(entry, dict):
            text = entry.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)


def _extract_error_message(raw_event: Any) -> str:
    for path in ("error.message", "message"):
        value = _get_value(raw_event, path)
        if isinstance(value, str) and value:
            return value
    return "Streaming request failed."


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value:
            return value
    return None


def _get_value(obj: Any, path: str, default: Any = None) -> Any:
    current = obj
    for part in path.split("."):
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(part, default)
            continue
        current = getattr(current, part, default)
    return current


def _nested_get(obj: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = obj
    for part in path:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    return current


def _to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return {
            key: _to_dict(value) if hasattr(value, "__dict__") else value
            for key, value in vars(obj).items()
            if not key.startswith("_")
        }
    return {}
