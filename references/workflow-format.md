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

## Hidden inputs (do NOT include in your JSON)

The server injects these automatically. Including them in your submission either is silently ignored or causes validation errors:

- `PROMPT` — the full graph (server uses this to reference the workflow)
- `UNIQUE_ID` — the current node's ID
- `EXTRA_PNGINFO` — metadata dict for `SaveImage`
- `API_KEY_COMFY_ORG` — Partner-Node auth, sourced from `extra_data.api_key_comfy_org` at the *submission* level (not inside any node's `inputs`)

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

## Combo input enums

Inputs typed as combos (e.g. `sampler_name`, `scheduler`, `ckpt_name`, `lora_name`) only accept values from the **legal enum** for the current Cloud instance. The enum lives at `/api/object_info → <class_type> → input → required → <input_name> → [0]`.

A workflow that worked yesterday may fail today if a model file was removed. Always validate combo values against a current `object_info` cache before submission.

## Open RFC: formal JSON Schema

There's an open RFC for a formal JSON Schema of the prompt format ([ComfyUI#8899](https://github.com/comfyanonymous/ComfyUI/issues/8899)). Not merged. Until then, schema validation is best-effort, driven by `/api/object_info` introspection.

## Cross-references

- Submission endpoint and lifecycle: [`api-endpoints.md`](./api-endpoints.md)
- WebSocket monitoring after submission: [`websocket-protocol.md`](./websocket-protocol.md)
- Common workflow recipes: [`pipeline-patterns.md`](./pipeline-patterns.md)
