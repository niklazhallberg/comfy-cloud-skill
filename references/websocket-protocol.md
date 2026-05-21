# WebSocket Protocol

`wss://cloud.comfy.org/ws?clientId={uuid}&token={api_key}`

**Critical**: `clientId` is currently ignored server-side. All of a user's open sockets receive all of that user's events. **Always filter by `data.prompt_id === yourPromptId`** in client code before reacting.

## Connection handshake & feature flags

On connect, the server sends a `status` message immediately. The client may then send a `feature_flags` message as its **first** message to negotiate capabilities:

```json
// client → server
{ "type": "feature_flags", "data": { "supports_preview_metadata": true, ... } }

// server → client (response)
{ "type": "feature_flags", "data": { /* server's SERVER_FEATURE_FLAGS */ } }
```

The server stores the client's flags per-connection (`sockets_metadata[sid].feature_flags`) and uses them later to decide e.g. whether to emit `PREVIEW_IMAGE_WITH_METADATA` (type 4) vs the plain `PREVIEW_IMAGE` (type 1). Sending feature-rich messages to a client that didn't advertise support can break older clients.

Server-side flags currently include (from upstream `openapi.yaml`):

- `supports_preview_metadata: true`
- `max_upload_size: <bytes>`
- `extension.manager.supports_v4: true`
- `node_replacements: true`
- `assets: <bool>` (conditional on server-side `--enable-assets`)

If your client doesn't negotiate, the server falls back to the lowest common subset.

## JSON message types

| Type | Payload essentials | Use for |
|---|---|---|
| `status` | `{ status: { exec_info: { queue_remaining } }, sid: <session_id> }` | Queue-depth UI; sent on connect |
| `feature_flags` | Server's full capabilities dict | Negotiation (see above) |
| `execution_start` | `{ prompt_id }` | Mark "started" |
| `execution_cached` | `{ prompt_id, nodes: [node_id, ...] }` | Skipped (cache hit) node IDs |
| `executing` | `{ prompt_id, node, display_node }` (`node: null` = workflow finished) | Per-node progress |
| `progress` | `{ prompt_id, node, value, max }` | Sampling steps |
| `progress_state` | `{ prompt_id, nodes: { node_id: { step, max_steps, ... } } }` | Structured per-node multi-node state (not just one active node) |
| `executed` | `{ prompt_id, node, display_node, output }` — `output.images[]`, `output.video[]`, `output.audio[]` | **Outputs land here** |
| `execution_success` | `{ prompt_id }` | Done |
| `execution_error` | `{ prompt_id, node_id, class_type, executed: [node_ids], exception_message, exception_type, traceback: [lines] }` | Structured error |
| `execution_interrupted` | **Same shape as `execution_error`** — `{ prompt_id, node_id, class_type, executed, exception_message, exception_type, traceback }` | User-cancelled (or targeted via `/api/interrupt` with `prompt_id`) |

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

`ValidationError` is itself an umbrella over ~11 specific subtype codes (e.g. `required_input_missing`, `value_not_in_list`, `dependency_cycle`) — see [`errors-and-limits.md`](./errors-and-limits.md) for the full validation subtype matrix.

When `execution_error` fires, the payload includes `node_id`, `class_type`, `exception_type`, `exception_message`, `traceback`, plus `executed` (list of node IDs that completed before the failure) — enough to tell the user *"node 14 (KSampler) failed on input `latent_image` with shape mismatch, here's what completed first"* rather than just "execution failed".

## Cross-references

- HTTP API: [`api-endpoints.md`](./api-endpoints.md)
- Error matrix: [`errors-and-limits.md`](./errors-and-limits.md)
- MCP wrapper: [`mcp-tool-schemas.md`](./mcp-tool-schemas.md)
