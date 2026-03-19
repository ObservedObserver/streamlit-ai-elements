"""Streaming chat runtime and session orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from .adapters import ChatCompletionsStreamAdapter, ResponsesStreamAdapter, StreamingAdapterRequest
from .tools import build_system_prompt, execute_tool_call, parse_tool_arguments
from .types import (
    ChatBackendConfig,
    ChatEvent,
    StreamingSessionState,
    append_event,
    create_session_state,
    make_event,
    new_message_id,
)


@dataclass(slots=True)
class _CycleToolCall:
    id: str
    tool_name: str
    arguments: str = ""


@dataclass(slots=True)
class _CycleState:
    text: str = ""
    reasoning: str = ""
    tool_calls: dict[str, _CycleToolCall] = field(default_factory=dict)
    response_id: str | None = None
    errored: bool = False


def ensure_session_state(state: StreamingSessionState | None = None) -> StreamingSessionState:
    return state or create_session_state()


def append_user_message(
    state: StreamingSessionState | None,
    content: str,
    *,
    message_id: str | None = None,
) -> StreamingSessionState:
    session = ensure_session_state(state)
    user_message_id = message_id or new_message_id()
    for event in (
        make_event("message_started", message_id=user_message_id, role="user"),
        make_event("text_delta", message_id=user_message_id, delta=content),
        make_event("message_completed", message_id=user_message_id),
    ):
        append_event(session, event)
    return session


def stream_chat_turn(
    client: Any,
    prompt: str,
    *,
    state: StreamingSessionState | None = None,
    config: ChatBackendConfig,
    resources: dict[str, Any] | None = None,
) -> Iterator[ChatEvent]:
    session = append_user_message(state, prompt)
    yield from stream_assistant_turn(client, state=session, config=config, resources=resources)


def stream_assistant_turn(
    client: Any,
    *,
    state: StreamingSessionState | None = None,
    config: ChatBackendConfig,
    resources: dict[str, Any] | None = None,
) -> Iterator[ChatEvent]:
    session = ensure_session_state(state)
    chat_messages = _build_backend_messages(session)
    assistant_message_id = new_message_id()
    started_event = make_event("message_started", message_id=assistant_message_id, role="assistant")
    append_event(session, started_event)
    yield started_event

    instructions = build_system_prompt(resources)
    previous_response_id: str | None = None
    tool_outputs: list[dict[str, Any]] = []

    for _ in range(8):
        adapter = _build_adapter(config.backend)
        cycle = _CycleState()
        request = StreamingAdapterRequest(
            config=config,
            instructions=instructions,
            messages=chat_messages,
            tool_outputs=tool_outputs,
            previous_response_id=previous_response_id,
        )

        for event in adapter.stream(client, request):
            event["message_id"] = assistant_message_id
            append_event(session, event)
            yield event
            _apply_cycle_event(cycle, event)

        previous_response_id = cycle.response_id or getattr(adapter, "last_response_id", previous_response_id)

        if cycle.errored:
            return

        if not cycle.tool_calls:
            completed_event = make_event("message_completed", message_id=assistant_message_id)
            append_event(session, completed_event)
            yield completed_event
            return

        tool_outputs = []
        assistant_tool_calls_payload: list[dict[str, Any]] = []
        tool_message_payloads: list[dict[str, Any]] = []
        for tool_call in cycle.tool_calls.values():
            raw_arguments = tool_call.arguments
            tool_args = parse_tool_arguments(raw_arguments)
            assistant_tool_calls_payload.append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.tool_name,
                        "arguments": raw_arguments,
                    },
                }
            )

            try:
                execution = execute_tool_call(tool_call.tool_name, tool_args, resources=resources)
            except Exception as exc:  # pragma: no cover - defensive path
                error_event = make_event(
                    "message_error",
                    message_id=assistant_message_id,
                    error=str(exc),
                )
                append_event(session, error_event)
                yield error_event
                return

            if execution.get("element") is not None:
                placeholder_event = make_event(
                    "renderer_placeholder_started",
                    message_id=assistant_message_id,
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.tool_name,
                    card_policy=execution.get("card_policy", "replace"),
                )
                append_event(session, placeholder_event)
                yield placeholder_event

            if execution.get("element") is not None:
                rendered_event = make_event(
                    "renderer_completed",
                    message_id=assistant_message_id,
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.tool_name,
                    element=execution["element"],
                    card_policy=execution.get("card_policy", "replace"),
                )
                append_event(session, rendered_event)
                yield rendered_event

            tool_output_text = str(execution.get("output_text", "success"))
            if tool_output_text:
                execution_result_event = make_event(
                    "tool_call_completed",
                    message_id=assistant_message_id,
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.tool_name,
                    arguments=raw_arguments,
                    output=tool_output_text,
                )
                append_event(session, execution_result_event)
                yield execution_result_event

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.id,
                    "output": tool_output_text,
                }
            )
            tool_message_payloads.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output_text,
                }
            )

        chat_messages.append(
            {
                "role": "assistant",
                "content": cycle.text or "",
                "tool_calls": assistant_tool_calls_payload,
            }
        )
        chat_messages.extend(tool_message_payloads)

    error_event = make_event(
        "message_error",
        message_id=assistant_message_id,
        error="Exceeded maximum tool-call continuations for one assistant turn.",
    )
    append_event(session, error_event)
    yield error_event


def _build_adapter(backend: str) -> ResponsesStreamAdapter | ChatCompletionsStreamAdapter:
    if backend == "responses":
        return ResponsesStreamAdapter()
    if backend == "chat_completions":
        return ChatCompletionsStreamAdapter()
    raise ValueError(f"Unsupported chat backend: {backend!r}")


def _build_backend_messages(state: StreamingSessionState) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for message in state.messages:
        if message.role not in {"user", "assistant"}:
            continue
        messages.append({"role": message.role, "content": message.content})
    return messages


def _apply_cycle_event(cycle: _CycleState, event: ChatEvent) -> None:
    event_type = event["type"]
    if event_type == "text_delta":
        cycle.text += event.get("delta", "")
    elif event_type == "reasoning_delta":
        cycle.reasoning += event.get("delta", "")
    elif event_type == "tool_call_started":
        tool_call_id = event.get("tool_call_id")
        if tool_call_id:
            cycle.tool_calls[tool_call_id] = _CycleToolCall(
                id=tool_call_id,
                tool_name=event.get("tool_name", "tool"),
                arguments=event.get("arguments", ""),
            )
    elif event_type == "tool_call_delta":
        tool_call_id = event.get("tool_call_id")
        if tool_call_id and tool_call_id in cycle.tool_calls:
            cycle.tool_calls[tool_call_id].arguments += event.get("delta", "")
    elif event_type == "tool_call_completed":
        tool_call_id = event.get("tool_call_id")
        if tool_call_id:
            cycle.tool_calls.setdefault(
                tool_call_id,
                _CycleToolCall(id=tool_call_id, tool_name=event.get("tool_name", "tool")),
            ).arguments = event.get("arguments", "")
    elif event_type == "message_error":
        cycle.errored = True
    if event.get("backend_response_id"):
        cycle.response_id = event["backend_response_id"]
