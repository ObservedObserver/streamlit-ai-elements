import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import streamlit_ai_elements as ai
from streamlit_ai_elements import _normalize_excalidraw_connectors, _normalize_excalidraw_shapes
from streamlit_ai_elements.chat_support import TOOLS, build_api_messages, call_llm, render_element


def make_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def make_response(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=FakeCompletions(responses))


class ChatSupportTests(unittest.TestCase):
    def test_build_api_messages_includes_system_prompt(self):
        messages = build_api_messages([{"role": "user", "content": "draw a flowchart"}])
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["content"], "draw a flowchart")

    def test_build_api_messages_includes_runtime_resources(self):
        runtime_resources = ai.resources(
            warehouse=ai.resource.sql_database(
                object(),
                description="Analytics warehouse",
                schema={"orders": ["id", "amount"]},
            )
        )

        messages = build_api_messages(
            [{"role": "user", "content": "show revenue"}],
            resources=runtime_resources,
        )

        self.assertIn("Available runtime resources:", messages[0]["content"])
        self.assertIn("warehouse (sql_database)", messages[0]["content"])

    def test_call_llm_collects_excalidraw_tool_call(self):
        tool_args = {
            "component": "excalidraw",
            "zoom_to_fit": True,
            "shapes": [
                {"id": "start", "type": "rounded-rectangle", "x": 80, "y": 80, "width": 180, "height": 64, "text": "Start"},
                {"id": "decision", "type": "diamond", "x": 360, "y": 72, "width": 180, "height": 120, "text": "Valid?"},
            ],
            "connectors": [
                {"from": "start", "to": "decision", "text": "submit"},
            ],
        }
        tool_call = SimpleNamespace(
            id="tool_1",
            function=SimpleNamespace(name="prebuilt_component", arguments=json.dumps(tool_args)),
        )

        client = FakeClient(
            [
                make_response(make_message(tool_calls=[tool_call])),
                make_response(make_message(content="Created a simple flowchart.")),
            ]
        )

        result = call_llm(client, "gpt-5.4", build_api_messages([{"role": "user", "content": "Draw a simple flowchart"}]))

        self.assertEqual(len(result["elements"]), 1)
        self.assertEqual(result["elements"][0]["type"], "prebuilt_component")
        self.assertEqual(result["elements"][0]["component"], "excalidraw")
        self.assertEqual(result["elements"][0]["args"]["shapes"][0]["id"], "start")
        self.assertEqual(result["elements"][0]["args"]["connectors"][0]["from"], "start")
        self.assertIn("Created a simple flowchart.", result["content"])
        self.assertEqual(client.chat.completions.calls[0]["tools"], TOOLS)

    def test_render_element_dispatches_excalidraw_parameters(self):
        elem = {
            "type": "prebuilt_component",
            "component": "excalidraw",
            "args": {
                "component": "excalidraw",
                "zoom_to_fit": True,
                "shapes": [
                    {"id": "start", "type": "rounded-rectangle", "x": 80, "y": 80, "text": "Start"}
                ],
                "connectors": [
                    {"from": "start", "to": "end", "text": "next"}
                ],
            },
        }

        with patch("streamlit_ai_elements.chat_support.ai.excalidraw") as mock_excalidraw:
            render_element(elem, key="case_1")

        mock_excalidraw.assert_called_once_with(
            shapes=[{"id": "start", "type": "rounded-rectangle", "x": 80, "y": 80, "text": "Start"}],
            connectors=[{"from": "start", "to": "end", "text": "next"}],
            readonly=False,
            hide_ui=False,
            zoom_to_fit=True,
            camera=None,
            height=560,
            key="case_1",
        )

    def test_render_element_passes_runtime_resource_selection_to_sandbox(self):
        elem = {
            "type": "sandbox",
            "args": {
                "js": "container.innerHTML = '<div>ok</div>'",
                "resources": ["dataset"],
            },
        }
        runtime_resources = ai.resources(
            warehouse=ai.resource.sql_database(object(), description="Warehouse")
        )

        with patch("streamlit_ai_elements.chat_support.ai.sandbox") as mock_sandbox:
            render_element(elem, key="case_2", resources=runtime_resources)

        mock_sandbox.assert_called_once_with(
            js="container.innerHTML = '<div>ok</div>'",
            libraries=None,
            height=560,
            resource_names=["dataset"],
            resources=runtime_resources,
            key="case_2",
        )

    def test_excalidraw_normalizes_snake_case_fields(self):
        shapes = _normalize_excalidraw_shapes(
            [{"id": "node_1", "type": "diamond", "x": 120, "y": 80, "vertical_align": "start"}]
        )
        connectors = _normalize_excalidraw_connectors(
            [
                {
                    "from": "node_1",
                    "to": "node_2",
                    "from_anchor": {"x": 1, "y": 0.5},
                    "to_anchor": {"x": 0, "y": 0.5},
                    "end_arrowhead": "triangle",
                }
            ]
        )

        self.assertEqual(shapes[0]["verticalAlign"], "start")
        self.assertNotIn("vertical_align", shapes[0])
        self.assertEqual(connectors[0]["fromAnchor"]["x"], 1)
        self.assertEqual(connectors[0]["toAnchor"]["x"], 0)
        self.assertEqual(connectors[0]["arrowheadEnd"], "triangle")

@unittest.skipUnless(os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY is required for the live excalidraw tool-call check.")
class ExcalidrawLiveIntegrationTests(unittest.TestCase):
    def test_model_calls_prebuilt_component_for_a_simple_flowchart(self):
        from openai import OpenAI

        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ.get("OPENAI_API_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or None,
        )

        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-5.4"),
            messages=build_api_messages(
                [
                    {
                        "role": "user",
                        "content": "Use the diagram tool to draw a simple editable flowchart with Start -> Validate -> Done and keep the toolbar visible.",
                    }
                ]
            ),
            tools=TOOLS,
        )

        message = response.choices[0].message
        self.assertTrue(message.tool_calls, "Expected the model to emit a tool call.")
        self.assertEqual(message.tool_calls[0].function.name, "prebuilt_component")

        args = json.loads(message.tool_calls[0].function.arguments)
        self.assertEqual(args["component"], "excalidraw")
        self.assertGreaterEqual(len(args.get("shapes", [])), 3)
        self.assertGreaterEqual(len(args.get("connectors", [])), 2)
        self.assertNotIn("readonly", args)
        self.assertNotIn("hide_ui", args)
        connector = args["connectors"][0]
        self.assertIn("from", connector)
        self.assertIn("to", connector)


if __name__ == "__main__":
    unittest.main()
