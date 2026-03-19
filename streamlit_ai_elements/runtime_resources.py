"""Runtime resource registry and serialization helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
import json
from typing import Any, Mapping


_ACCESS_LEVELS = {"none", "summary", "schema", "full"}


@dataclass(frozen=True, slots=True)
class RuntimeResource:
    """A named resource that can be exposed to the AI runtime and/or frontend."""

    kind: str
    payload: Any
    description: str = ""
    ai_access: str = "summary"
    frontend_access: str = "full"
    max_rows: int = 1000
    sample_rows: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)
    name: str | None = None


class _ResourceFactory:
    def dataframe(
        self,
        df: Any,
        *,
        description: str = "",
        ai_access: str = "summary",
        frontend_access: str = "full",
        max_rows: int = 1000,
        sample_rows: int = 5,
    ) -> RuntimeResource:
        _validate_access(ai_access)
        _validate_access(frontend_access)
        return RuntimeResource(
            kind="dataframe",
            payload=df,
            description=description,
            ai_access=ai_access,
            frontend_access=frontend_access,
            max_rows=max(0, int(max_rows)),
            sample_rows=max(0, int(sample_rows)),
        )

    def sql_database(
        self,
        engine: Any,
        *,
        description: str = "",
        ai_access: str = "schema",
        frontend_access: str = "none",
        allowed_tables: list[str] | None = None,
        schema: dict[str, list[str]] | None = None,
        allow_write: bool = False,
    ) -> RuntimeResource:
        _validate_access(ai_access)
        _validate_access(frontend_access)
        return RuntimeResource(
            kind="sql_database",
            payload=engine,
            description=description,
            ai_access=ai_access,
            frontend_access=frontend_access,
            metadata={
                "allowed_tables": list(allowed_tables or []),
                "schema": deepcopy(schema or {}),
                "allow_write": bool(allow_write),
            },
        )


resource = _ResourceFactory()


def resources(**named_resources: RuntimeResource) -> dict[str, RuntimeResource]:
    """Build a validated runtime resource registry."""

    registry: dict[str, RuntimeResource] = {}
    for name, value in named_resources.items():
        if not isinstance(value, RuntimeResource):
            raise TypeError(
                f"Resource '{name}' must be created with ai.resource.*, got {type(value).__name__}."
            )
        registry[name] = replace(value, name=name)
    return registry


def format_resources_for_prompt(registry: Mapping[str, RuntimeResource] | None) -> str:
    """Render human-readable resource summaries for the LLM system prompt."""

    if not registry:
        return ""

    blocks: list[str] = ["Available runtime resources:"]

    for name, definition in registry.items():
        if definition.ai_access == "none":
            continue

        if definition.kind == "dataframe":
            blocks.extend(_format_dataframe_prompt_block(name, definition))
        elif definition.kind == "sql_database":
            blocks.extend(_format_sql_database_prompt_block(name, definition))

    if len(blocks) == 1:
        return ""

    blocks.extend(
        [
            "",
            "Tool usage rules for runtime resources:",
            "- For js_raw and sandbox, set `resources` to the resource names you need. In JavaScript, use the `resources` variable or the `data` alias.",
            "- For prebuilt_component with component='vega_lite', set `data_resource` to one dataframe resource name and omit inline spec.data unless you need a custom dataset.",
            "- Never invent resource names. Use only the exact names listed above.",
        ]
    )
    return "\n".join(blocks)


def resolve_frontend_resources(
    registry: Mapping[str, RuntimeResource] | None,
    requested_names: list[str] | tuple[str, ...] | None,
) -> dict[str, dict[str, Any]]:
    """Materialize the requested resources for frontend renderers."""

    if not requested_names:
        return {}
    if not registry:
        raise ValueError("This component requested runtime resources, but no resources registry was provided.")

    resolved: dict[str, dict[str, Any]] = {}
    for raw_name in requested_names:
        name = str(raw_name)
        if name in resolved:
            continue
        if name not in registry:
            raise ValueError(f"Unknown runtime resource requested by component: {name!r}")

        definition = registry[name]
        if definition.frontend_access == "none":
            raise ValueError(f"Runtime resource {name!r} is not available to frontend components.")

        if definition.kind == "dataframe":
            row_limit = definition.max_rows if definition.frontend_access == "full" else definition.sample_rows
            payload = _materialize_dataframe_payload(name, definition, row_limit=row_limit)
            if definition.frontend_access != "full":
                payload.pop("rows", None)
                payload["sample_rows"] = payload.pop("rows_preview", [])
            else:
                payload["sample_rows"] = payload["rows_preview"]
            resolved[name] = payload
        elif definition.kind == "sql_database":
            resolved[name] = {
                "kind": "sql_database",
                "name": name,
                "description": definition.description,
                "dialect": definition.metadata.get("dialect"),
                "tables": deepcopy(definition.metadata.get("schema") or {}),
                "allowed_tables": list(definition.metadata.get("allowed_tables") or []),
                "allow_write": bool(definition.metadata.get("allow_write")),
            }
        else:
            raise ValueError(f"Unsupported runtime resource kind: {definition.kind!r}")

    return resolved


def inject_vega_lite_resource_data(
    spec: dict[str, Any],
    frontend_resources: Mapping[str, dict[str, Any]] | None,
    *,
    data_resource: str | None = None,
) -> dict[str, Any]:
    """Populate Vega-Lite spec.data.values from a runtime dataframe resource."""

    resolved_spec = deepcopy(spec)
    if not frontend_resources or resolved_spec.get("data") is not None:
        return resolved_spec

    resource_name = data_resource or _pick_single_dataframe(frontend_resources)
    if not resource_name:
        return resolved_spec
    if resource_name not in frontend_resources:
        raise ValueError(f"Vega-Lite requested unknown resource {resource_name!r}.")

    resource_payload = frontend_resources[resource_name]
    if resource_payload.get("kind") != "dataframe":
        raise ValueError(f"Vega-Lite data_resource must reference a dataframe resource, got {resource_payload.get('kind')!r}.")

    rows = resource_payload.get("rows")
    if rows is None:
        raise ValueError(f"Dataframe resource {resource_name!r} is not materialized for frontend row access.")

    resolved_spec["data"] = {"values": rows}
    return resolved_spec


def build_javascript_runtime(
    frontend_resources: Mapping[str, dict[str, Any]] | None,
    *,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable runtime payload for JS-based renderers."""

    resources_payload = deepcopy(dict(frontend_resources or {}))
    context_payload = deepcopy(dict(context or {}))
    primary_resource = _pick_single_resource(resources_payload)

    if primary_resource and primary_resource.get("kind") == "dataframe":
        data_payload: Any = deepcopy(primary_resource)
        rows_payload: list[Any] = deepcopy(primary_resource.get("rows") or [])
    elif primary_resource is not None:
        data_payload = deepcopy(primary_resource)
        rows_payload = []
    elif context_payload:
        data_payload = context_payload
        rows_payload = []
    else:
        data_payload = resources_payload
        rows_payload = []

    return {
        "resources": resources_payload,
        "context": context_payload,
        "resource": deepcopy(primary_resource),
        "data": data_payload,
        "rows": rows_payload,
    }


def _validate_access(level: str) -> None:
    if level not in _ACCESS_LEVELS:
        raise ValueError(f"Unsupported access level: {level!r}")


def _format_dataframe_prompt_block(name: str, definition: RuntimeResource) -> list[str]:
    payload = _materialize_dataframe_payload(name, definition, row_limit=definition.sample_rows)
    lines = [f"- {name} (dataframe): {definition.description or 'Tabular data'}", f"  Rows: {payload['row_count']}"]
    if payload["columns"]:
        lines.append("  Columns:")
        for column in payload["columns"]:
            lines.append(f"  - {column['name']}: {column['dtype']}")
    if definition.ai_access in {"summary", "full"} and payload["rows_preview"]:
        lines.append("  Sample rows:")
        for row in payload["rows_preview"]:
            lines.append(f"  - {json.dumps(row, ensure_ascii=True)}")
    return lines


def _format_sql_database_prompt_block(name: str, definition: RuntimeResource) -> list[str]:
    schema = definition.metadata.get("schema") or {}
    allowed_tables = definition.metadata.get("allowed_tables") or []
    lines = [f"- {name} (sql_database): {definition.description or 'SQL database resource'}"]
    if schema:
        lines.append("  Tables:")
        for table_name, columns in schema.items():
            column_list = ", ".join(columns)
            lines.append(f"  - {table_name}({column_list})")
    elif allowed_tables:
        lines.append(f"  Allowed tables: {', '.join(allowed_tables)}")
    lines.append(f"  Read-only: {not bool(definition.metadata.get('allow_write'))}")
    return lines


def _materialize_dataframe_payload(
    name: str,
    definition: RuntimeResource,
    *,
    row_limit: int,
) -> dict[str, Any]:
    df = definition.payload
    if not hasattr(df, "to_json") or not hasattr(df, "dtypes") or not hasattr(df, "head"):
        raise TypeError(f"Runtime resource {name!r} is not a pandas-like DataFrame.")

    row_count = int(getattr(df, "shape")[0])
    preview_limit = min(max(definition.sample_rows, 0), row_count)
    rows_limit = min(max(row_limit, 0), row_count)
    rows = json.loads(df.head(rows_limit).to_json(orient="records", date_format="iso"))
    rows_preview = json.loads(df.head(preview_limit).to_json(orient="records", date_format="iso"))
    columns = [{"name": str(column), "dtype": str(dtype)} for column, dtype in zip(df.columns, df.dtypes)]

    return {
        "kind": "dataframe",
        "name": name,
        "description": definition.description,
        "columns": columns,
        "row_count": row_count,
        "rows": rows,
        "rows_preview": rows_preview,
        "truncated": row_count > rows_limit,
    }


def _pick_single_dataframe(frontend_resources: Mapping[str, dict[str, Any]]) -> str | None:
    dataframe_names = [
        resource_name
        for resource_name, payload in frontend_resources.items()
        if payload.get("kind") == "dataframe"
    ]
    if len(dataframe_names) == 1:
        return dataframe_names[0]
    return None


def _pick_single_resource(frontend_resources: Mapping[str, dict[str, Any]]) -> dict[str, Any] | None:
    if len(frontend_resources) != 1:
        return None
    return next(iter(frontend_resources.values()))
