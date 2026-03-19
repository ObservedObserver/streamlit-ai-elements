"""Reusable chat/demo helpers for Streamlit AI Elements."""

from __future__ import annotations

import json
from typing import Any

import streamlit_ai_elements as ai
from streamlit_ai_elements.runtime_resources import format_resources_for_prompt

SYSTEM_PROMPT = """\
You are an AI assistant embedded in a Streamlit chat. You can render interactive \
visual elements directly in the conversation using tool calls.

When the user asks for something visual, choose the best tool:
- js_raw:             animated SVGs, creative animations, custom HTML/Canvas
- sandbox:            interactive dashboards with sliders, metrics, ECharts
- prebuilt_component: structured pre-built renderers such as Vega-Lite and Excalidraw

Supported pre-built components:
- vega_lite: data charts (bar, line, scatter, area, heatmap…)
- excalidraw: diagrams, flowcharts, canvases with nodes and arrows

Guidelines:
- Write clean, self-contained code or specifications.
- Use modern CSS (flexbox/grid) for layouts.
- Make visualizations visually polished with clear hierarchy and spacing.
- When runtime resources are available, explicitly request them in the tool arguments instead of inventing inline data.
- Prefer component="excalidraw" for flowcharts, process diagrams, whiteboard-like layouts, and node-link canvases.
- Prefer component="vega_lite" for standard data charts.
- For sandbox dashboards: use container.innerHTML to set the layout, echarts.init() for charts. Requested runtime resources will be available in JavaScript as `resources`; if exactly one dataframe resource is requested, `data` will be that dataframe payload and `rows` will be its rows array.
- For js_raw components: requested runtime resources will be available in JavaScript as `resources`; if exactly one dataframe resource is requested, `data` will be that dataframe payload and `rows` will be its rows array.
- For prebuilt_component with component="vega_lite": set `data_resource` to one dataframe resource name when you want the chart to use runtime tabular data.
- For prebuilt_component with component="excalidraw": provide structured shapes and connectors, not JavaScript.
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
                            "container (root DOM), resources, data, resource, rows, context, "
                            "requestAnimationFrame, setInterval, setTimeout. "
                            "Use container.querySelector() to access elements."
                        ),
                    },
                    "resources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of runtime resources to expose to this component.",
                    },
                },
                "required": [],
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
                "JS globals: container, echarts, d3, THREE, setStateValue, setTriggerValue, "
                "resources, data, resource, rows, context, requestAnimationFrame, setInterval, setTimeout. "
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
                    "resources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of runtime resources to expose to this dashboard.",
                    },
                },
                "required": ["js"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prebuilt_component",
            "description": (
                "Render a structured pre-built component using a supported component type. "
                "Use component='vega_lite' for standard charts and component='excalidraw' for "
                "editable diagrams and flowcharts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "enum": ["vega_lite", "excalidraw"],
                        "description": "Which pre-built component to render.",
                    },
                    "resources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of runtime resources available to this component.",
                    },
                    "data_resource": {
                        "type": "string",
                        "description": "For component='vega_lite', the dataframe resource to inject as spec.data.values.",
                    },
                    "spec": {
                        "type": "object",
                        "description": (
                            "A complete Vega-Lite v5 specification object. "
                            "Use when component='vega_lite'. Set width='container' for responsive sizing."
                        ),
                    },
                    "zoom_to_fit": {
                        "type": "boolean",
                        "description": (
                            "Whether to zoom the camera to fit all shapes after rendering. "
                            "Use when component='excalidraw'. Default: true."
                        ),
                    },
                    "shapes": {
                        "type": "array",
                        "description": "Canvas nodes to render. Use when component='excalidraw'.",
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
                        "description": "Arrow connectors between shapes. Use when component='excalidraw'.",
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
                        "description": "Optional Excalidraw camera state. Use when component='excalidraw'.",
                        "properties": {
                            "x": {"type": "number"},
                            "y": {"type": "number"},
                            "z": {"type": "number"},
                        },
                    },
                },
                "required": ["component"],
            },
        },
    },
]

DEFAULT_HEIGHTS = {
    "js_raw": "content",
    "sandbox": "content",
}

PREBUILT_COMPONENT_HEIGHTS = {
    "vega_lite": 400,
    "excalidraw": 560,
}


def render_element(elem: dict[str, Any], key: str, resources: dict[str, ai.RuntimeResource] | None = None):
    """Dispatch a single rendered element to the right ai.* function."""
    element_type = elem["type"]
    args = elem["args"]
    component_name = elem.get("component") or args.get("component")
    requested_resources = args.get("resources")

    # Backward compatibility for older stored chat elements.
    if element_type in PREBUILT_COMPONENT_HEIGHTS:
        component_name = element_type
        element_type = "prebuilt_component"

    if element_type == "prebuilt_component":
        height = PREBUILT_COMPONENT_HEIGHTS.get(component_name, 400)
    else:
        height = DEFAULT_HEIGHTS.get(element_type, 400)

    if element_type == "js_raw":
        ai.js_raw(
            html=args.get("html", ""),
            css=args.get("css", ""),
            js=args.get("js", ""),
            height=height,
            resource_names=requested_resources,
            resources=resources,
            key=key,
        )
    elif element_type == "sandbox":
        ai.sandbox(
            js=args.get("js", ""),
            libraries=args.get("libraries"),
            height=height,
            resource_names=requested_resources,
            resources=resources,
            key=key,
        )
    elif element_type == "prebuilt_component":
        if component_name == "vega_lite":
            ai.vega_lite(
                spec=args.get("spec", {}),
                height=height,
                resource_names=requested_resources,
                data_resource=args.get("data_resource"),
                resources=resources,
                key=key,
            )
        elif component_name == "excalidraw":
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
        else:
            raise ValueError(f"Unsupported pre-built component: {component_name!r}")
    else:
        raise ValueError(f"Unsupported element type: {element_type!r}")


def build_api_messages(
    messages: list[dict[str, Any]],
    resources: dict[str, ai.RuntimeResource] | None = None,
) -> list[dict[str, Any]]:
    """Convert display messages to OpenAI API format (text only, no tool history)."""
    system_prompt = SYSTEM_PROMPT
    resource_prompt = format_resources_for_prompt(resources)
    if resource_prompt:
        system_prompt = f"{system_prompt}\n\n{resource_prompt}"

    api_messages = [{"role": "system", "content": system_prompt}]
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

            tool_name = tool_call.function.name
            if tool_name == "prebuilt_component":
                elements.append(
                    {
                        "type": "prebuilt_component",
                        "component": args.get("component"),
                        "args": args,
                    }
                )
            elif tool_name in PREBUILT_COMPONENT_HEIGHTS:
                # Backward compatibility for older tool names.
                elements.append({"type": "prebuilt_component", "component": tool_name, "args": args})
            else:
                elements.append({"type": tool_name, "args": args})

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
