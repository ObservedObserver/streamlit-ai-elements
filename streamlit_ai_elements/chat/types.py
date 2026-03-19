"""Public types and timeline helpers for the chat subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict
from uuid import uuid4


ChatEventType = Literal[
    "message_started",
    "text_delta",
    "reasoning_delta",
    "tool_call_started",
    "tool_call_delta",
    "tool_call_completed",
    "renderer_placeholder_started",
    "renderer_completed",
    "message_completed",
    "message_error",
]

MessageRole = Literal["user", "assistant", "system", "tool"]
MessageStatus = Literal["streaming", "completed", "error"]
ToolStatus = Literal["streaming", "completed", "rendering", "error"]
ToolCardPolicy = Literal["replace", "augment"]
ChatBackendName = Literal["responses", "chat_completions"]


class ChatEvent(TypedDict, total=False):
    type: ChatEventType
    event_id: str
    message_id: str
    role: MessageRole
    delta: str
    content: str
    error: str
    tool_call_id: str
    tool_name: str
    arguments: str
    output: str
    element: dict[str, Any]
    card_policy: ToolCardPolicy
    backend_response_id: str


@dataclass(slots=True)
class ChatBackendConfig:
    """Backend and model selection for streamed chat."""

    model: str
    backend: ChatBackendName = "responses"
    reasoning_effort: str | None = None
    reasoning_summary: str | None = "auto"
    temperature: float | None = None
    max_output_tokens: int | None = None
    extra_request_options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AssistantChunk:
    """A visible streamed chunk within an assistant message."""

    kind: Literal["text", "thinking"]
    content: str = ""
    status: MessageStatus = "streaming"


@dataclass(slots=True)
class ToolCallEventState:
    """Runtime state for one tool call inside a message."""

    id: str
    tool_name: str
    status: ToolStatus = "streaming"
    arguments: str = ""
    output: str = ""
    element: dict[str, Any] | None = None
    card_policy: ToolCardPolicy = "replace"
    error: str | None = None


@dataclass(slots=True)
class ToolCallCard:
    """Presentation-oriented state for a tool call card."""

    id: str
    tool_name: str
    status: ToolStatus
    argument_preview: str = ""
    output_preview: str = ""
    element: dict[str, Any] | None = None
    card_policy: ToolCardPolicy = "replace"


@dataclass(slots=True)
class ChatMessage:
    """A reconstructed chat message from timeline events."""

    id: str
    role: MessageRole
    status: MessageStatus = "streaming"
    content: str = ""
    reasoning: str = ""
    tool_calls: list[ToolCallCard] = field(default_factory=list)
    rendered_elements: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class StreamingSessionState:
    """Append-only timeline plus reconstructed message state."""

    session_id: str
    timeline: list[ChatEvent] = field(default_factory=list)
    messages: list[ChatMessage] = field(default_factory=list)


def new_event_id() -> str:
    return f"evt_{uuid4().hex}"


def new_message_id() -> str:
    return f"msg_{uuid4().hex}"


def new_session_id() -> str:
    return f"session_{uuid4().hex}"


def make_event(event_type: ChatEventType, **payload: Any) -> ChatEvent:
    event: ChatEvent = {"type": event_type, "event_id": new_event_id()}
    event.update(payload)
    return event


def create_session_state(
    *,
    session_id: str | None = None,
    timeline: list[ChatEvent] | None = None,
) -> StreamingSessionState:
    return replay_timeline(timeline or [], session_id=session_id)


def append_event(state: StreamingSessionState, event: ChatEvent) -> StreamingSessionState:
    state.timeline.append(event)
    replayed = replay_timeline(state.timeline, session_id=state.session_id)
    state.messages = replayed.messages
    return state


def replay_timeline(
    timeline: list[ChatEvent],
    *,
    session_id: str | None = None,
) -> StreamingSessionState:
    state = StreamingSessionState(session_id=session_id or new_session_id(), timeline=list(timeline))
    messages_by_id: dict[str, ChatMessage] = {}
    tool_states: dict[tuple[str, str], ToolCallEventState] = {}

    for event in timeline:
        event_type = event["type"]
        message_id = event.get("message_id")
        if event_type == "message_started":
            if not message_id:
                continue
            message = ChatMessage(
                id=message_id,
                role=event.get("role", "assistant"),
                status="streaming",
            )
            messages_by_id[message_id] = message
            state.messages.append(message)
            continue

        if not message_id or message_id not in messages_by_id:
            continue

        message = messages_by_id[message_id]
        if event_type == "text_delta":
            message.content += event.get("delta", "")
        elif event_type == "reasoning_delta":
            message.reasoning += event.get("delta", "")
        elif event_type == "tool_call_started":
            tool_call_id = event.get("tool_call_id")
            if not tool_call_id:
                continue
            existing_tool_state = tool_states.get((message_id, tool_call_id))
            if existing_tool_state is None:
                tool_state = ToolCallEventState(
                    id=tool_call_id,
                    tool_name=event.get("tool_name", "tool"),
                    status="streaming",
                    arguments=event.get("arguments", ""),
                )
                tool_states[(message_id, tool_call_id)] = tool_state
                message.tool_calls.append(
                    ToolCallCard(
                        id=tool_call_id,
                        tool_name=tool_state.tool_name,
                        status=tool_state.status,
                        argument_preview=tool_state.arguments,
                    )
                )
            else:
                existing_tool_state.tool_name = event.get("tool_name", existing_tool_state.tool_name)
                existing_tool_state.arguments = event.get("arguments", existing_tool_state.arguments)
                existing_tool_state.status = "streaming"
                _sync_tool_card(message, existing_tool_state)
        elif event_type == "tool_call_delta":
            tool_call_id = event.get("tool_call_id")
            tool_state = tool_states.get((message_id, tool_call_id or ""))
            if tool_state is None:
                continue
            tool_state.arguments += event.get("delta", "")
            _sync_tool_card(message, tool_state)
        elif event_type == "tool_call_completed":
            tool_call_id = event.get("tool_call_id")
            tool_state = tool_states.get((message_id, tool_call_id or ""))
            if tool_state is None:
                continue
            tool_state.status = "completed"
            tool_state.arguments = event.get("arguments", tool_state.arguments)
            tool_state.output = event.get("output", tool_state.output)
            _sync_tool_card(message, tool_state)
        elif event_type == "renderer_placeholder_started":
            tool_call_id = event.get("tool_call_id")
            tool_state = tool_states.get((message_id, tool_call_id or ""))
            if tool_state is None:
                continue
            tool_state.status = "rendering"
            tool_state.card_policy = event.get("card_policy", tool_state.card_policy)
            _sync_tool_card(message, tool_state)
        elif event_type == "renderer_completed":
            tool_call_id = event.get("tool_call_id")
            tool_state = tool_states.get((message_id, tool_call_id or ""))
            if tool_state is None:
                continue
            tool_state.status = "completed"
            tool_state.element = event.get("element")
            tool_state.card_policy = event.get("card_policy", tool_state.card_policy)
            if tool_state.element is not None:
                message.rendered_elements.append(tool_state.element)
            _sync_tool_card(message, tool_state)
        elif event_type == "message_completed":
            message.status = "completed"
        elif event_type == "message_error":
            message.status = "error"
            message.error = event.get("error") or "Unknown streaming error."

    return state


def _sync_tool_card(message: ChatMessage, tool_state: ToolCallEventState) -> None:
    for index, tool_card in enumerate(message.tool_calls):
        if tool_card.id != tool_state.id:
            continue
        message.tool_calls[index] = ToolCallCard(
            id=tool_state.id,
            tool_name=tool_state.tool_name,
            status=tool_state.status,
            argument_preview=tool_state.arguments,
            output_preview=tool_state.output,
            element=tool_state.element,
            card_policy=tool_state.card_policy,
        )
        return
