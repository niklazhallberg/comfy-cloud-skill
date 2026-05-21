# WebSocket Protocol

`wss://cloud.comfy.org/ws?clientId={uuid}&token={api_key}`

**Critical**: `clientId` is currently ignored server-side. All of a user's open sockets receive all of that user's events. **Always filter by `data.prompt_id === yourPromptId`** in client code before reacting.

## JSON message types

| Type | Payload essentials | Use for |
|---|---|---|
| `status` | `data.status.exec_info.queue_remaining` | Queue-depth UI |
| `execution_start` | `prompt_id` | Mark "started" |
| `execution_cached` | `prompt_id`, `nodes: [...]` | Skipped (cache hit) node IDs |
| `executing` | `prompt_id`, `node` (null = workflow finished), `display_node` | Per-node progress |
| `progress` | `prompt_id`, `node`, `value`, `max` | Sampling steps |
| `progress_state` | `prompt_id`, `nodes: { id: { class_type, ... } }` | Richer multi-node state |
| `executed` | `prompt_id`, `node`, `output` | **Outputs land here** — `output.images[]`, `output.video[]`, `output.audio[]` |
| `execution_success` | `prompt_id` | Done |
| `execution_error` | `prompt_id`, `node_id`, `node_type`, `exception_type`, `exception_message`, `traceback`, `executed`, `current_inputs`, `current_outputs` | Structured error |
| `execution_interrupted` | `prompt_id` | User-cancelled |

## Binary frames (big-endian, NOT JSON)

The WebSocket switches to binary frames during sampling for previews:

### Type 1 — PREVIEW_IMAGE

```
[type:4B = 0x00000001][image_type:4B][image_data:...]
```

`image_type`: `1` = JPEG, `2` = PNG.

### Type 3 — TEXT

```
[type:4B = 0x00000003][node_id_len:4B][node_id:utf8][text:utf8]
```

Node-attributed progress text.

### Type 4 — PREVIEW_IMAGE_WITH_METADATA

```
[type:4B = 0x00000004][metadata_len:4B][metadata_json:utf8][image_data:...]
```

`metadata_json` contains `{ node_id, display_node_id, real_node_id, prompt_id, parent_node_id }`. Use the embedded `prompt_id` to attribute the preview.

## Lifecycle pattern

```
POST /api/prompt → { prompt_id }
   ↓
WS: execution_start { prompt_id }
   ↓
WS: execution_cached { nodes: [...] }   // optional, skipped nodes
   ↓
WS: executing { node }                  // per active node
   ↓                 ↓
WS: progress     WS: executed { node, output }
   ↓
WS: execution_success | execution_error | execution_interrupted
   ↓
GET /api/jobs/{prompt_id} → canonical outputs (don't rely solely on accumulated `executed` events)
   ↓
GET /api/view?filename=... (follow 302, drop auth) → download
```

## Hybrid monitoring (recommended)

Production code lands on **WebSocket for live progress + REST for canonical results**:

- WS gives previews, per-node progress, cache hits
- WS messages can drop — connection interruptions, server hiccups
- `GET /api/jobs/{prompt_id}` after `execution_success` always has the canonical output set

Don't rely on WS alone for outputs. Don't poll-only if you want previews.

## `execution_error` exception_type enum

From the OpenAPI spec:

`ValidationError`, `ModelDownloadError`, `ImageDownloadError`, `OOMError`, `PanicError`, `ServiceError`, `WebSocketError`, `DispatcherError`, `InsufficientFundsError`, `InactiveSubscriptionError`.

When `execution_error` fires, the payload includes `node_id`, `exception_type`, `exception_message`, `traceback`, plus `current_inputs` and `current_outputs` — enough to tell the user *"node 14 (KSampler) failed on input `latent_image` with shape mismatch"* rather than just "execution failed".

## Cross-references

- HTTP API: [`api-endpoints.md`](./api-endpoints.md)
- Error matrix: [`errors-and-limits.md`](./errors-and-limits.md)
- MCP wrapper: [`mcp-tool-schemas.md`](./mcp-tool-schemas.md)
