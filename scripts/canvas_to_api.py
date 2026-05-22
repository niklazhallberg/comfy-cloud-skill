#!/usr/bin/env python3
"""Convert a Comfy Cloud canvas-format workflow JSON to API-format JSON.

Canvas format = what File → Save produces (with `nodes` array, `links` array,
`groups`, Note nodes, positions).
API format = what POST /api/prompt accepts (flat dict keyed by node ID, each
value `{class_type, inputs}`).

Usage:
    python canvas_to_api.py <input.canvas.json> <output.api.json>
    python canvas_to_api.py <input.canvas.json> <output.api.json> --object-info <path>
    python canvas_to_api.py <input.canvas.json> <output.api.json> --fetch-from-cloud

If neither --object-info nor --fetch-from-cloud is given, the script falls back
to a heuristic conversion that may misorder widgets for nodes with mixed
widget/link inputs. The schema-aware path is strongly recommended.

Per workflow-authoring-style: this script is the contract between the
canvas-format source of truth and the API-format submit payload. Output should
never be hand-edited; regenerate from the canvas file whenever it changes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from typing import Any

NON_EXECUTABLE_TYPES = {"Note", "MarkdownNote", "PrimitiveNode", "Reroute"}

# User-uploaded filenames change per Cloud account / run, so the combo enum
# for these inputs doesn't constrain valid templates. Skip enum validation for
# these (input_name, class_type) pairs.
SKIP_ENUM_VALIDATION = {
    ("image", "LoadImage"),
    ("image", "LoadImageMask"),
}


def load_object_info(
    cache_path: str | None,
    fetch_from_cloud: bool,
) -> dict[str, Any] | None:
    if cache_path:
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    if fetch_from_cloud:
        base_url = os.environ.get("COMFY_CLOUD_BASE_URL", "https://cloud.comfy.org")
        api_key = os.environ.get("COMFY_CLOUD_API_KEY")
        if not api_key:
            sys.exit("COMFY_CLOUD_API_KEY env var is required for --fetch-from-cloud")
        req = urllib.request.Request(
            f"{base_url}/api/object_info",
            headers={"X-API-Key": api_key},
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    return None


def build_link_map(canvas: dict[str, Any]) -> dict[int, tuple[int, int]]:
    """Map canvas link_id → (source_node_id, source_slot_index)."""
    link_map: dict[int, tuple[int, int]] = {}
    for link in canvas.get("links", []):
        if not link or len(link) < 6:
            continue
        link_id, src_node, src_slot, _dst_node, _dst_slot, _type = link[:6]
        link_map[link_id] = (src_node, src_slot)
    return link_map


def schema_input_order(node_type: str, object_info: dict[str, Any] | None) -> list[str] | None:
    if not object_info:
        return None
    schema = object_info.get(node_type)
    if not schema:
        return None
    order = schema.get("input_order", {})
    return list(order.get("required", [])) + list(order.get("optional", []))


def convert_node(
    node: dict[str, Any],
    link_map: dict[int, tuple[int, int]],
    object_info: dict[str, Any] | None,
) -> dict[str, Any] | None:
    node_type = node.get("type")
    if not node_type or node_type in NON_EXECUTABLE_TYPES:
        return None
    if node.get("mode") in (2, 4):  # 2 = muted, 4 = bypassed in canvas
        return None

    # Index the linked inputs by name.
    linked_inputs: dict[str, tuple[str, int]] = {}
    for inp in node.get("inputs", []) or []:
        link_id = inp.get("link")
        name = inp.get("name")
        if link_id is None or name is None:
            continue
        src = link_map.get(link_id)
        if src is None:
            continue
        linked_inputs[name] = (str(src[0]), src[1])

    widgets = node.get("widgets_values", []) or []
    input_order = schema_input_order(node_type, object_info)
    schema = (object_info or {}).get(node_type, {}) if object_info else {}
    required_spec = schema.get("input", {}).get("required", {})
    optional_spec = schema.get("input", {}).get("optional", {})

    inputs: dict[str, Any] = {}

    if input_order:
        widget_iter = iter(widgets)
        for name in input_order:
            if name in linked_inputs:
                inputs[name] = list(linked_inputs[name])
                continue
            try:
                value = next(widget_iter)
            except StopIteration:
                # Optional widget with no value; skip.
                continue
            inputs[name] = value
            # If this input has `control_after_generate` (canvas UI adds an
            # extra widget value after the seed widget), consume and drop it.
            spec = required_spec.get(name) or optional_spec.get(name)
            if isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict):
                if spec[1].get("control_after_generate"):
                    try:
                        next(widget_iter)
                    except StopIteration:
                        pass
    else:
        # Fallback path: emit linked inputs first, then widgets indexed by position.
        # This works for simple nodes but can misorder widgets for nodes with
        # interleaved link/widget inputs. Use --object-info or --fetch-from-cloud
        # for robust conversion.
        for name, link in linked_inputs.items():
            inputs[name] = list(link)
        for i, value in enumerate(widgets):
            inputs[f"_widget_{i}"] = value

    return {"class_type": node_type, "inputs": inputs}


def canvas_to_api(
    canvas: dict[str, Any],
    object_info: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    link_map = build_link_map(canvas)
    api_workflow: dict[str, dict[str, Any]] = {}
    for node in canvas.get("nodes", []):
        node_id = node.get("id")
        if node_id is None:
            continue
        converted = convert_node(node, link_map, object_info)
        if converted is None:
            continue
        api_workflow[str(node_id)] = converted
    return api_workflow


def validate_against_schema(
    api_workflow: dict[str, dict[str, Any]],
    object_info: dict[str, Any] | None,
) -> list[str]:
    """Return a list of human-readable validation messages. Empty = valid."""
    errors: list[str] = []
    if not object_info:
        errors.append(
            "No object_info available — skipping schema validation. "
            "Re-run with --object-info or --fetch-from-cloud for full validation."
        )
        return errors
    for node_id, node in api_workflow.items():
        class_type = node.get("class_type")
        if class_type not in object_info:
            errors.append(f"Node {node_id}: class_type '{class_type}' not found in object_info")
            continue
        schema = object_info[class_type]
        required = schema.get("input", {}).get("required", {})
        provided = set(node.get("inputs", {}).keys())
        for name, spec in required.items():
            if name not in provided:
                errors.append(f"Node {node_id} ({class_type}): missing required input '{name}'")
            else:
                value = node["inputs"][name]
                if isinstance(spec, list) and len(spec) > 0:
                    type_or_enum = spec[0]
                    if isinstance(type_or_enum, list) and not isinstance(value, list):
                        if (name, class_type) in SKIP_ENUM_VALIDATION:
                            continue
                        if value not in type_or_enum:
                            errors.append(
                                f"Node {node_id} ({class_type}): input '{name}'='{value}' "
                                f"not in combo enum (first 5: {type_or_enum[:5]}...)"
                            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to canvas-format JSON")
    parser.add_argument("output", help="Path to write API-format JSON")
    parser.add_argument(
        "--object-info",
        help="Path to a cached /api/object_info JSON snapshot",
    )
    parser.add_argument(
        "--fetch-from-cloud",
        action="store_true",
        help="Fetch /api/object_info from Cloud (uses COMFY_CLOUD_API_KEY env var)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip schema validation after conversion",
    )
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        canvas = json.load(f)

    object_info = load_object_info(args.object_info, args.fetch_from_cloud)

    api_workflow = canvas_to_api(canvas, object_info)

    if not args.no_validate:
        errors = validate_against_schema(api_workflow, object_info)
        if errors:
            print("Validation messages:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            # Don't fail on missing-object_info warning; do fail on real errors.
            real_errors = [e for e in errors if "skipping schema validation" not in e]
            if real_errors:
                print(
                    f"\n{len(real_errors)} validation error(s) — refusing to write output.",
                    file=sys.stderr,
                )
                return 1

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(api_workflow, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(api_workflow)} API-format nodes to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
