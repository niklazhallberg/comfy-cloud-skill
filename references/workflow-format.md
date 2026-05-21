# Workflow Format

ComfyUI has **two** JSON formats. Submitting the wrong one is the #1 cause of `400 Invalid workflow`.

## API format (a.k.a. "prompt" format) — the one Cloud accepts

The shape `/api/prompt` expects:

```json
{
  "3": {
    "class_type": "KSampler",
    "inputs": {
      "seed": 156680208700286,
      "steps": 20,
      "cfg": 8.0,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1.0,
      "model":     ["4", 0],
      "positive":  ["6", 0],
      "negative":  ["7", 0],
      "latent_image": ["5", 0]
    }
  },
  "4": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": { "ckpt_name": "v1-5-pruned-emaonly.ckpt" }
  },
  "5": {
    "class_type": "EmptyLatentImage",
    "inputs": { "width": 512, "height": 512, "batch_size": 1 }
  }
}
```

Properties:

- Flat dict at top level.
- Keys are **string** node IDs.
- Each node value is `{ class_type, inputs }` — nothing else.
- Links between nodes are tuples `["source_node_id", output_index]` placed in the consuming node's `inputs`.
- No visual data — no positions, no link IDs, no groups, no `widgets_values`.

## Canvas / UI format ("workflow" format) — what the editor saves

Produced by `File → Save` in the canvas. It carries everything the editor needs but the API can't consume:

- Top-level `nodes` array with integer IDs
- `pos: [x, y]`, `size`, `color`
- `links` array with tuples `[link_id, from_node, from_slot, to_node, to_slot, type]`
- `groups`, `extra`
- `definitions.subgraphs` for the blueprint/subgraph system
- `widgets_values` — raw widget values, pre-mapping to named inputs

**Canvas format will fail submission.** If your payload contains `"nodes": [...]` and `"links": [...]`, you have canvas format. Reject at the boundary; never forward.

## Conversion

### Canvas → API

This is what the frontend does when you press "Queue". Outside the browser, options:

1. **Headless frontend** — drive `Comfy-Org/ComfyUI_frontend` programmatically using its `loadApiJson` / `graphToPrompt` path. We've validated this works against the live Cloud canvas via Playwright; see the `comfy-cloud-proxy` development logs for the `window.app.graphToPrompt` integration.
2. **ComfyScript** ([github.com/Chaoses-Ib/ComfyScript](https://github.com/Chaoses-Ib/ComfyScript)) — Python AST that generates valid API-format JSON.
3. **PNG tEXt-chunk extraction** — ComfyUI-saved PNG/WebP/FLAC files contain the API-format workflow embedded in metadata. Parse and you have the workflow back.
4. **Reject at boundary** — many production proxies require API format on input and refuse canvas format outright. Cleanest, least error-prone.

### API → Canvas

One-way lossy — positions and widget orderings are guessed. Don't rely on round-tripping.

## Hidden inputs (do NOT include in node `inputs`)

The server injects these automatically into a node's call site when the node declares them via its `hidden` attribute. Setting them inside a node's `inputs` in your submission is silently ignored or causes validation errors. There are **six**, not four — earlier docs missed two.

| Hidden input | Source | Purpose |
|---|---|---|
| `prompt` | server | The full graph (server uses this to reference the workflow) |
| `unique_id` | server | The current node's string ID in the workflow |
| `extra_pnginfo` | `extra_data.extra_pnginfo` | Metadata dict embedded by `SaveImage` into output PNGs |
| `dynprompt` | server | Dynamic prompt object — **new** field for subgraph / blueprint support |
| `auth_token_comfy_org` | `extra_data.auth_token_comfy_org` | OAuth-style token for Partner Nodes (distinct from API key) |
| `api_key_comfy_org` | `extra_data.api_key_comfy_org` | Partner-Node auth — the same X-API-Key value, passed inside the workflow submission |

Source: `comfy_api/latest/_io.py:1341-1405` in the upstream ComfyUI repo.

The last two go at the *submission level* in `extra_data`, not inside any node's `inputs`:

```json
{
  "prompt": { /* graph */ },
  "extra_data": {
    "api_key_comfy_org": "<your-X-API-key>",
    "auth_token_comfy_org": "<your-token-if-using-oauth-flow>"
  }
}
```

`SENSITIVE_EXTRA_DATA_KEYS` are stripped from history by the server, so auth tokens never appear in `/api/jobs/{id}` responses or `/api/history_v2` payloads.

## Node attributes that matter at the graph level

Two flags on a node's Python class control how it participates in execution:

- **`OUTPUT_NODE = True`** — only nodes with this attribute trigger execution when a workflow runs. Without it, the node is intermediate (its outputs are computed only if a downstream `OUTPUT_NODE` needs them). This is why a workflow with just `KSampler` (no `SaveImage` / `PreviewImage`) does nothing visible. `SaveImage` is an `OUTPUT_NODE`; `PreviewImage` also is, but its output is ephemeral.
- **`HAS_INTERMEDIATE_OUTPUT = True`** — the node can emit intermediate outputs *during* execution (streamed via WebSocket `executed` events before the node fully finishes). Relevant for nodes that produce per-step previews or partial results.

## Partner Nodes

Workflows that include Partner-Node `class_type`s (Kling, Luma, Ideogram, Flux Pro, Nano Banana, Hunyuan 3D, Runway, Seedance, Seedream, Grok) **must** include `extra_data.api_key_comfy_org` at the submission level:

```json
{
  "prompt": { /* graph */ },
  "extra_data": {
    "api_key_comfy_org": "<your-same-cloud-api-key>"
  }
}
```

The browser does this automatically; API clients must do it manually. See [`partner-nodes.md`](./partner-nodes.md) for the catalog and billing notes.

## Link tuple notation

When a node's input is sourced from another node's output, it's expressed as a 2-element tuple `["source_node_id", output_index]`:

```json
"latent_image": ["5", 0]
```

means *"this input takes the output at index 0 from the node with ID 5"*.

For nodes with multiple outputs (e.g. `CheckpointLoaderSimple` outputs `[MODEL, CLIP, VAE]`), the second element of the tuple is which output socket you want:

```json
"4": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "..." } },
"6": { "class_type": "CLIPTextEncode",
       "inputs": { "text": "...", "clip": ["4", 1] } }   // 1 = CLIP socket
```

## Widget value array wrapping (silent failure trap)

When a widget value **is itself an array**, the API serializer wraps it as `{"__value__": [...]}` to disambiguate it from a node link tuple (`["node_id", slot]`). Without this wrapping, the backend reads `[1, 2, 3]` as "connect to node 1, output 2" and either fails noisily or, worse, silently routes the wrong data.

Curve widgets get a typed variant:

```json
"some_curve_input": { "__type__": "CURVE", "__value__": [[0.0, 0.5], [1.0, 0.5]] }
```

If you're hand-authoring or mutating API-format JSON for nodes with array-typed widgets (kernel masks, schedule curves, multi-value lists), check whether the target frontend uses this wrapping and match it.

## `widget.serialize` vs `widget.options.serialize`

Two adjacent properties on a widget that look similar but control different things:

- `widget.serialize` — controls **canvas workflow** persistence (the canvas `File → Save` artifact)
- `widget.options.serialize` — controls **API-prompt** serialization (what's actually sent to `/api/prompt`)

A subtle gotcha: a widget can appear "saved" in the canvas workflow (visible after reload) but **never get included in API submissions**, because the two flags are independent. If a parameter looks set in the editor but the workflow behaves as if the default were used, check `widget.options.serialize` on the upstream widget.

## Three import paths in the frontend

The `workflowService` in `ComfyUI_frontend` exposes three formal entry points for loading a workflow into the canvas:

| Function | Input format | Use case |
|---|---|---|
| `loadGraphData(data)` | Canvas workflow JSON (with `nodes` + `links`) | Standard "open saved workflow" |
| `loadApiJson(data)` | API format (the wire format) | Load a programmatically generated graph back into the editor for visual inspection / edit |
| `importA1111(text)` | Automatic1111 parameter text | Fallback for A1111-format prompts |

`loadApiJson` is particularly useful for round-tripping: a proxy can build a workflow programmatically, submit it, and *also* hand the user the same JSON to load into the canvas for visual debugging. It can even promote widget-bound values to true inputs when needed.

## Combo input enums

Inputs typed as combos (e.g. `sampler_name`, `scheduler`, `ckpt_name`, `lora_name`) only accept values from the **legal enum** for the current Cloud instance. The enum lives at `/api/object_info → <class_type> → input → required → <input_name> → [0]`.

A workflow that worked yesterday may fail today if a model file was removed. Always validate combo values against a current `object_info` cache before submission.

## Open RFC: formal JSON Schema

There's an open RFC for a formal JSON Schema of the prompt format ([ComfyUI#8899](https://github.com/comfyanonymous/ComfyUI/issues/8899)). Not merged. Until then, schema validation is best-effort, driven by `/api/object_info` introspection.

## Cross-references

- Submission endpoint and lifecycle: [`api-endpoints.md`](./api-endpoints.md)
- WebSocket monitoring after submission: [`websocket-protocol.md`](./websocket-protocol.md)
- Common workflow recipes: [`pipeline-patterns.md`](./pipeline-patterns.md)
