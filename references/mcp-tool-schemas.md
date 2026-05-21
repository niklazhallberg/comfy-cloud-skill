# MCP Tool Schemas

The `comfy-cloud-proxy` MCP server (https://github.com/niklazhallberg/comfy-cloud-proxy) is the execution layer this skill operates through. This file documents the tools the server exposes and how to invoke them effectively.

## Currently shipped tools

### `ping`

Connectivity check. Returns `pong`. Use to verify the MCP server is wired before attempting a generation.

### `get_object_info`

Fetch the live node catalog from Comfy Cloud.

```
get_object_info()
  → { totalNodes: number, sampleNodes: string[] }

get_object_info(nodeName: string)
  → full NodeInfo schema for that class_type
```

**Use for:** discovering what's installed, what combo values a node accepts, what input types are required.

### `submit_simple_txt2img`

Submit a minimal SD1.5 txt2img workflow. Non-blocking; returns the `prompt_id`.

```
submit_simple_txt2img({
  prompt: string,            // required
  negativePrompt?: string,
  width?: number,            // default 512, range 64–2048
  height?: number,           // default 512
  steps?: number,            // default 20, range 1–150
  cfg?: number,              // default 7, range 0–30
  seed?: number              // generated if omitted
})
  → { promptId, number, nodeErrors, seed, checkpoint, workflow }
```

### `export_simple_txt2img_workflow`

Build the same SD1.5 txt2img workflow as above and write it to `output/simple-txt2img-workflow.json`. Doesn't call the Cloud API. Useful for inspecting or hand-editing the graph before submission.

## Planned tools (not yet shipped)

The proxy roadmap, in priority order:

| Tool | Purpose |
|---|---|
| `wait_for_prompt(prompt_id, timeout?)` | Block until `execution_success` / `error`; surface progress |
| `get_prompt_outputs(prompt_id)` | Return canonical outputs from `/api/jobs/{id}` |
| `fetch_output(filename, type)` | Wrap `/api/view`, follow 302, return bytes or MCP resource |
| `cancel_prompt(prompt_id)` | `POST /api/queue {delete: [id]}` |
| `interrupt_current()` | `POST /api/interrupt` |
| `get_queue()` | Running + pending |
| `list_capabilities()` | Cached `/api/object_info`, indexed |
| `list_models(category)` | Available checkpoints / LoRAs / VAEs / upscalers / ControlNets |
| `validate_workflow(workflow)` | Local validation against object_info before submission |
| `upload_image(path)` | `POST /api/upload/image` |
| `upload_asset_from_url(url, tags)` | `POST /api/assets/download` from HF/Civitai with task polling |
| `submit_workflow(workflow, extra_data?)` | Generic submit (any API-format JSON) |
| `submit_img2img(...)`, `submit_inpaint(...)`, etc. | Template-driven submitters per pipeline class |

When invoking the skill, prefer the highest-level tool that fits. Reach for `submit_workflow` only when no template matches.

## Configuration

The proxy reads from `.env`:

```
COMFY_CLOUD_API_KEY=<your-key>
COMFY_CLOUD_BASE_URL=https://cloud.comfy.org   # optional
```

If `COMFY_CLOUD_API_KEY` is missing, tools that hit the Cloud API return an `isError` MCP response with a clear message.

## Invocation pattern

```
1. ping                           // verify MCP is up
2. get_object_info(nodeName)     // discover capabilities for the pipeline you want to build
3. (build workflow per templates + validation)
4. submit_*                      // returns prompt_id
5. wait_for_prompt(prompt_id)    // (planned) — until then, the skill polls /api/job/{id}/status
6. get_prompt_outputs(prompt_id) // (planned) — until then, the skill calls /api/jobs/{id} directly
7. fetch_output(filename, type)  // (planned) — until then, the skill follows the 302 itself
```

## Until planned tools land

The skill scripts in `scripts/` (when shipped) bridge the gap by hitting the Cloud API directly using the same `COMFY_CLOUD_API_KEY`. This is acceptable as a transitional pattern but the eventual goal is for the MCP server to own all Cloud interactions.

## Cross-references

- Proxy implementation: https://github.com/niklazhallberg/comfy-cloud-proxy
- Underlying API: [`api-endpoints.md`](./api-endpoints.md)
- WebSocket events (for the planned `wait_for_prompt`): [`websocket-protocol.md`](./websocket-protocol.md)
