"""Tool schemas, execution helpers, and renderer dispatch for chat."""

from __future__ import annotations

import json
from typing import Any, Callable

import streamlit as st

from streamlit_ai_elements.runtime_resources import RuntimeResource, format_resources_for_prompt


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
- For prebuilt_component with component="vega_lite": always include a complete non-empty Vega-Lite `spec` object that follows Vega-Lite syntax. Use `data_resource` when you want runtime tabular data injected into the spec instead of inline values.
- For Vega-Lite charts, prefer `prebuilt_component` over sandbox unless the user explicitly needs custom JavaScript behavior that Vega-Lite cannot express.
- For prebuilt_component with component="excalidraw": provide structured shapes and connectors, not JavaScript.
- Excalidraw scenes should be editable by default and keep the toolbar visible unless the user explicitly asks for a static preview.
- Keep assistant text concise when a rendered component already carries the main payload.
"""

_FUNCTION_DEFINITIONS = [
    {
        "name": "js_raw",
        "description": (
            "Render raw HTML/CSS/JS directly in the chat. "
            "Use for animated SVGs, creative animations, canvas drawings, custom HTML elements. "
            "JS receives `container` (root DOM element) and safe "
            "`requestAnimationFrame`/`setInterval`/`setTimeout`."
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
                        "container, resources, data, resource, rows, context, "
                        "requestAnimationFrame, setInterval, setTimeout."
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
    {
        "name": "sandbox",
        "description": (
            "Render an interactive dashboard with pre-loaded ECharts. "
            "Use for dashboards with sliders, metric cards, and dynamic charts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "js": {"type": "string", "description": "JavaScript code for the dashboard."},
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
    {
        "name": "prebuilt_component",
        "description": (
            "Render a structured pre-built component using a supported component type. "
            "Use component='vega_lite' for standard charts and provide a Vega-Lite `spec` object. "
            "Use component='excalidraw' for editable diagrams and include structured `shapes` / `connectors`."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "component": {
                    "type": "string",
                    "enum": ["vega_lite", "excalidraw"],
                    "description": "Which pre-built component to render. This choice determines which other fields are required.",
                },
                "resources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Names of runtime resources available to this component. Use exact resource names only.",
                },
                "data_resource": {
                    "type": "string",
                    "description": (
                        "For component='vega_lite', the dataframe resource name to inject into the Vega-Lite spec "
                        "as `spec.data.values`."
                    ),
                },
                "spec": {
                    "type": "object",
                    "description": (
                        "For component='vega_lite', a complete non-empty object that follows Vega-Lite syntax. "
                        "Use inline `data.values` or provide `data_resource` for runtime data. "
                        "Do not omit this field."
                    ),
                },
                "zoom_to_fit": {
                    "type": "boolean",
                    "description": "For component='excalidraw', whether to zoom the camera to fit all shapes after rendering.",
                },
                "shapes": {
                    "type": "array",
                    "description": "For component='excalidraw', the canvas nodes to render.",
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
                    "description": "For component='excalidraw', arrow connectors between shapes.",
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
                    "description": "For component='excalidraw', optional camera state.",
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
]

DEFAULT_HEIGHTS = {
    "js_raw": "content",
    "sandbox": "content",
}

PREBUILT_COMPONENT_HEIGHTS = {
    "vega_lite": 400,
    "excalidraw": 560,
}

ToolExecutor = Callable[[dict[str, Any], dict[str, RuntimeResource] | None], dict[str, Any]]
_TOOL_EXECUTORS: dict[str, ToolExecutor] = {}


def build_system_prompt(resources: dict[str, RuntimeResource] | None = None) -> str:
    prompt = SYSTEM_PROMPT
    resource_prompt = format_resources_for_prompt(resources)
    if resource_prompt:
        prompt = f"{prompt}\n\n{resource_prompt}"
    return prompt


def build_chat_completions_tools() -> list[dict[str, Any]]:
    return [{"type": "function", "function": definition} for definition in _FUNCTION_DEFINITIONS]


def build_responses_tools() -> list[dict[str, Any]]:
    return [{"type": "function", **definition} for definition in _FUNCTION_DEFINITIONS]


def register_tool_executor(name: str, executor: ToolExecutor) -> None:
    _TOOL_EXECUTORS[name] = executor


def execute_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    resources: dict[str, RuntimeResource] | None = None,
) -> dict[str, Any]:
    validation_error = validate_tool_call(tool_name, arguments)
    if validation_error is not None:
        return {
            "output_text": validation_error,
            "card_policy": "augment",
            "is_renderer": False,
        }

    executor = _TOOL_EXECUTORS.get(tool_name)
    if executor is not None:
        return executor(arguments, resources)

    element = element_from_tool_call(tool_name, arguments)
    if element is None:
        return {
            "output_text": json.dumps({"status": "ignored", "tool_name": tool_name}, ensure_ascii=True),
            "card_policy": "augment",
            "is_renderer": False,
        }

    return {
        "output_text": "Element rendered successfully in the chat.",
        "element": element,
        "card_policy": "replace",
        "is_renderer": True,
    }


def element_from_tool_call(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    if tool_name == "prebuilt_component":
        return {
            "type": "prebuilt_component",
            "component": arguments.get("component"),
            "args": arguments,
        }
    if tool_name in PREBUILT_COMPONENT_HEIGHTS:
        return {
            "type": "prebuilt_component",
            "component": tool_name,
            "args": arguments,
        }
    if tool_name in {"js_raw", "sandbox"}:
        return {"type": tool_name, "args": arguments}
    return None


def parse_tool_arguments(raw_arguments: str | None) -> dict[str, Any]:
    if not raw_arguments:
        return {}
    try:
        return json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {}


def validate_tool_call(tool_name: str, arguments: dict[str, Any]) -> str | None:
    if tool_name == "sandbox" and not str(arguments.get("js", "")).strip():
        return "Sandbox tool calls require a non-empty `js` field."

    if tool_name not in {"prebuilt_component", "vega_lite", "excalidraw"}:
        return None

    component_name = arguments.get("component") or tool_name
    if component_name == "vega_lite":
        spec = arguments.get("spec")
        if not isinstance(spec, dict) or not spec:
            return (
                "Vega-Lite tool calls require a non-empty `spec` object. "
                "Use `prebuilt_component` with `component=\"vega_lite\"` and include a complete chart spec."
            )
        return None

    if component_name == "excalidraw":
        shapes = arguments.get("shapes")
        if shapes is not None and not isinstance(shapes, list):
            return "Excalidraw tool calls require `shapes` to be a list when provided."
        return None

    return f"Unsupported pre-built component: {component_name!r}"


def render_element(
    elem: dict[str, Any],
    key: str,
    resources: dict[str, RuntimeResource] | None = None,
) -> None:
    """Dispatch a single rendered element to the right ai.* function."""
    import streamlit_ai_elements as ai

    element_type = elem["type"]
    args = elem["args"]
    component_name = elem.get("component") or args.get("component")
    requested_resources = args.get("resources")

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
        return

    if element_type == "sandbox":
        ai.sandbox(
            js=args.get("js", ""),
            libraries=args.get("libraries"),
            height=height,
            resource_names=requested_resources,
            resources=resources,
            key=key,
        )
        return

    if element_type != "prebuilt_component":
        raise ValueError(f"Unsupported element type: {element_type!r}")

    if component_name == "vega_lite":
        spec = args.get("spec")
        if not isinstance(spec, dict) or not spec:
            st.error("Vega-Lite tool call did not provide a non-empty `spec` object.")
            return
        ai.vega_lite(
            spec=spec,
            height=height,
            resource_names=requested_resources,
            data_resource=args.get("data_resource"),
            resources=resources,
            key=key,
        )
        return

    if component_name == "excalidraw":
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
        return

    raise ValueError(f"Unsupported pre-built component: {component_name!r}")
