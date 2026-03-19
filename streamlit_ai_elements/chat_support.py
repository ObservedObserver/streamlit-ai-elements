"""Reusable chat/demo helpers for Streamlit AI Elements."""

from __future__ import annotations

import json
from typing import Any

import streamlit_ai_elements as ai

SYSTEM_PROMPT = """\
You are an AI assistant embedded in a Streamlit chat. You can render interactive \
visual elements directly in the conversation using tool calls.

When the user asks for something visual, choose the best tool:
- js_raw:    animated SVGs, creative animations, custom HTML/Canvas
- vega_lite: data charts (bar, line, scatter, area, heatmap…)
- sandbox:   interactive dashboards with sliders, metrics, ECharts
- excalidraw: diagrams, flowcharts, canvases with nodes and arrows

Guidelines:
- Write clean, self-contained code or specifications.
- Use modern CSS (flexbox/grid) for layouts.
- Make visualizations visually polished with clear hierarchy and spacing.
- Prefer excalidraw for flowcharts, process diagrams, whiteboard-like layouts, and node-link canvases.
- For sandbox dashboards: use container.innerHTML to set the layout, echarts.init() for charts.
- For excalidraw diagrams: provide structured shapes and connectors, not JavaScript.
- Excalidraw scenes should be editable by default and keep the toolbar visible unless the user explicitly asks for a static preview.
- After rendering, briefly explain what you created.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "js_raw",
            "description": (
                "Render raw HTML/CSS/JS directly in the chat. "
                "Use for animated SVGs, creative animations, canvas drawings, custom HTML elements. "
                "JS receives `container` (root DOM element) and safe "
                "`requestAnimationFrame`/`setInterval`/`setTimeout`. "
                "For SVG elements use document.createElementNS('http://www.w3.org/2000/svg', tag)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "html": {"type": "string", "description": "HTML markup"},
                    "css": {"type": "string", "description": "CSS styles"},
                    "js": {
                        "type": "string",
                        "description": (
                            "JavaScript code. Available globals: "
                            "container (root DOM), requestAnimationFrame, setInterval, setTimeout. "
                            "Use container.querySelector() to access elements."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "vega_lite",
            "description": (
                "Render a Vega-Lite chart. Use for bar, line, scatter, area, and other data charts. "
                'Set "width": "container" for responsive sizing. Include data inline in the spec.'
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "spec": {
                        "type": "object",
                        "description": "A complete Vega-Lite v5 specification object.",
                    },
                },
                "required": ["spec"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sandbox",
            "description": (
                "Render an interactive dashboard with pre-loaded ECharts. "
                "Use for dashboards with sliders, metric cards, and dynamic charts. "
                "JS globals: container, echarts, d3, THREE, setStateValue, setTriggerValue, data, "
                "requestAnimationFrame, setInterval, setTimeout. "
                "Use container.innerHTML to build layout HTML, echarts.init(element) for charts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "js": {
                        "type": "string",
                        "description": "JavaScript code for the interactive dashboard.",
                    },
                    "libraries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Libraries to load: 'echarts', 'd3', 'three'. Default: ['echarts'].",
                    },
                },
                "required": ["js"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "excalidraw",
            "description": (
                "Render an editable diagram on an Excalidraw canvas. "
                "Use for flowcharts, node-link diagrams, mind maps, or simple whiteboard scenes. "
                "Keep the scene editable and leave the toolbar visible by default. "
                "Return structured shapes and connectors only. Do not return JavaScript."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "zoom_to_fit": {
                        "type": "boolean",
                        "description": "Whether to zoom the camera to fit all shapes after rendering. Default: true.",
                    },
                    "shapes": {
                        "type": "array",
                        "description": "Canvas nodes to render.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "rectangle",
                                        "rounded-rectangle",
                                        "ellipse",
                                        "diamond",
                                        "triangle",
                                        "hexagon",
                                        "text",
                                    ],
                                },
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "width": {"type": "number"},
                                "height": {"type": "number"},
                                "text": {"type": "string"},
                                "color": {"type": "string"},
                                "fill": {
                                    "type": "string",
                                    "enum": ["none", "semi", "solid", "pattern"],
                                },
                                "dash": {
                                    "type": "string",
                                    "enum": ["draw", "solid", "dashed", "dotted"],
                                },
                                "size": {
                                    "type": "string",
                                    "enum": ["s", "m", "l", "xl"],
                                },
                                "font": {
                                    "type": "string",
                                    "enum": ["draw", "sans", "serif", "mono"],
                                },
                                "align": {
                                    "type": "string",
                                    "enum": ["start", "middle", "end"],
                                },
                                "vertical_align": {
                                    "type": "string",
                                    "enum": ["start", "middle", "end"],
                                },
                            },
                            "required": ["type", "x", "y"],
                        },
                    },
                    "connectors": {
                        "type": "array",
                        "description": "Arrow connectors between shapes.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "from": {"type": "string"},
                                "to": {"type": "string"},
                                "text": {"type": "string"},
                                "color": {"type": "string"},
                                "dash": {
                                    "type": "string",
                                    "enum": ["draw", "solid", "dashed", "dotted"],
                                },
                                "bend": {"type": "number"},
                                "from_anchor": {
                                    "type": "object",
                                    "properties": {
                                        "x": {"type": "number"},
                                        "y": {"type": "number"},
                                    },
                                },
                                "to_anchor": {
                                    "type": "object",
                                    "properties": {
                                        "x": {"type": "number"},
                                        "y": {"type": "number"},
                                    },
                                },
                                "start_arrowhead": {"type": "string"},
                                "end_arrowhead": {"type": "string"},
                            },
                            "required": ["from", "to"],
                        },
                    },
                    "camera": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "z": {"type": "number"},
                        },
                    },
                },
                "required": ["shapes"],
            },
        },
    },
]

DEFAULT_HEIGHTS = {
    "js_raw": 420,
    "vega_lite": 400,
    "sandbox": 560,
    "excalidraw": 560,
}


def render_element(elem: dict[str, Any], key: str):
    """Dispatch a single rendered element to the right ai.* function."""
    element_type = elem["type"]
    args = elem["args"]
    height = DEFAULT_HEIGHTS.get(element_type, 400)

    if element_type == "js_raw":
        ai.js_raw(
            html=args.get("html", ""),
            css=args.get("css", ""),
            js=args.get("js", ""),
            height=height,
            key=key,
        )
    elif element_type == "vega_lite":
        ai.vega_lite(spec=args.get("spec", {}), height=height, key=key)
    elif element_type == "sandbox":
        ai.sandbox(
            js=args.get("js", ""),
            libraries=args.get("libraries"),
            height=height,
            key=key,
        )
    elif element_type == "excalidraw":
        ai.excalidraw(
            shapes=args.get("shapes", []),
            connectors=args.get("connectors"),
            readonly=False,
            hide_ui=False,
            zoom_to_fit=args.get("zoom_to_fit", True),
            camera=args.get("camera"),
            height=height,
            key=key,
        )


def build_api_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert display messages to OpenAI API format (text only, no tool history)."""
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in messages:
        api_messages.append(
            {
                "role": message["role"],
                "content": message.get("content", "") or "",
            }
        )
    return api_messages


def call_llm(client: Any, model: str, api_messages: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Call OpenAI and handle tool calls.
    Returns {"content": str, "elements": list[dict]}.
    """
    response = client.chat.completions.create(
        model=model,
        messages=api_messages,
        tools=TOOLS,
    )
    message = response.choices[0].message

    elements: list[dict[str, Any]] = []
    text_parts: list[str] = []

    if message.content:
        text_parts.append(message.content)

    if message.tool_calls:
        for tool_call in message.tool_calls:
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = {}
            elements.append({"type": tool_call.function.name, "args": args})

        api_messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in message.tool_calls
                ],
            }
        )
        for tool_call in message.tool_calls:
            api_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": "Element rendered successfully in the chat.",
                }
            )

        follow_up = client.chat.completions.create(
            model=model,
            messages=api_messages,
        )
        if follow_up.choices[0].message.content:
            text_parts.append(follow_up.choices[0].message.content)

    return {"content": "\n\n".join(text_parts), "elements": elements}
