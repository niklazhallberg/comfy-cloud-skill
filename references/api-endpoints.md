# API Endpoints

Comfy Cloud's HTTP and WebSocket surface. Ground truth: [`research/openapi-cloud.yaml`](../research/openapi-cloud.yaml). Cross-checked against the Claude Opus 4.7 brief.

Conventions: ✅ = officially documented and stable. ⚠️ = documented but experimental, deprecated, or marked subject-to-change. 🟡 = de-facto stable (used by the JS frontend) but not in OpenAPI.

**Identifier convention:** `prompt_id` returned from `POST /api/prompt` and `job_id` in the `/api/jobs/*` endpoints are **the same value**. Treat them as one identifier across the proxy — `jobId` internally is fine.

**Dual routing:** every route the server registers at `/path` is automatically also at `/api/path`. Examples below use the `/api/*` form (which is what docs and clients standardize on), but bare paths work too.

## Base + auth

- **Base URL**: `https://cloud.comfy.org`
- **HTTP auth**: `X-API-Key: <key>` header on every request. **Not a Bearer token.**
- **WebSocket auth**: `wss://cloud.comfy.org/ws?clientId=<uuid>&token=<api_key>`
- **Tier gate**: API access only on **Creator** ($35/mo, 7,400 credits) and **Pro** ($100/mo, 21,100 credits). Standard and Free can't use the API.
- **Concurrency**: Creator = 3, Pro = 5. Excess submissions queue automatically.
- **Runtime cap**: 30 min (Standard/Creator), 60 min (Pro). Over-cap = auto-cancel.
- **Queue depth**: up to 100 workflows queued at once.
- **GPU class**: Blackwell RTX 6000 Pro, 96 GB VRAM (no selection).

## Workflows & jobs

| Method & Path | Purpose | Notes |
|---|---|---|
| `POST /api/prompt` ✅ | Submit a workflow | Body: `{ "prompt": <api-format-json>, "extra_data?": {...}, "partial_execution_targets?": ["nodeId", ...], "number?": <ignored>, "front?": <ignored> }`. Returns `{ prompt_id, number, node_errors }`. `number` and `front` are accepted for OSS compat but **ignored** on Cloud. |
| `GET /api/prompt` ✅ | Current queue exec info | Returns `{ exec_info: { queue_remaining } }`. |
| `GET /api/job/{job_id}/status` ✅ | Poll job status | Returns `pending` / `in_progress` / `completed` / `failed` / `cancelled` / `waiting_to_dispatch` / `error`. **`job_id` is the same value as `prompt_id` returned from `/api/prompt`.** |
| `GET /api/jobs` ✅ | Paginated list | Filters: `status`, `workflow_id`, `output_type`, `sort_by`, `limit ≤ 1000`. Workflow JSON omitted from list payload. **Prefer this over `/api/history_v2`.** |
| `GET /api/jobs/{job_id}` ✅ | Full job detail | Includes `workflow`, `outputs`, `preview_output`, `execution_status`, `execution_meta`, structured `execution_error`. **Canonical "get me everything" call. Prefer over `/api/history_v2/{prompt_id}`.** |
| `GET /api/queue` ✅ | Queue state | `{ queue_running: [...], queue_pending: [...] }`. Items are tuple arrays `[job_number, prompt_id, workflow_json, output_node_ids, metadata]`. |
| `POST /api/queue` ✅ | Cancel pending | `{ "delete": [...] }` or `{ "clear": true }`. **Affects pending only.** |
| `POST /api/interrupt` ✅ | Cancel running | Distinct from `/api/queue`. **Now granular** — accepts `{ "prompt_id": "<id>" }` in the body to target a specific running job. With empty body, affects all running jobs for the authed user. The interrupted job emits `execution_interrupted` over WebSocket. |
| `GET /api/history_v2` ⚠️ DEPRECATED | Execution history (lightweight) | **Officially deprecated in favor of `GET /api/jobs`.** Kept for backwards compatibility. Workflow stripped from `extra_pnginfo`. |
| `GET /api/history_v2/{prompt_id}` ⚠️ DEPRECATED | Full history for one prompt | **Officially deprecated in favor of `GET /api/jobs/{job_id}`.** Dict keyed by `prompt_id`. |
| `POST /api/history` ✅ | Manage history | `{ "delete": [...] }` or `{ "clear": true }`. |

## Inputs & outputs

| Method & Path | Purpose | Notes |
|---|---|---|
| `POST /api/upload/image` ✅ | Multipart image upload | Fields: `image`, `overwrite`, `subfolder`, `type`. **`overwrite` and `subfolder` accepted-but-ignored** (content-addressed). Returns `{ name, subfolder, type }`. |
| `POST /api/upload/mask` ✅ | Multipart mask upload | Requires `original_ref` JSON string referencing the image. Returns layer hashes (`mask`, `paint`, `painted`, `painted_masked`). |
| `GET /api/view` ✅ | Retrieve generated file | **Returns 302 to a signed GCS URL.** Follow redirects. Auth header on the `/api/view` request only — **don't forward `X-API-Key` to the signed URL** (leak vector). Supports `channel=rgb\|alpha`. `subfolder` ignored. |
| `GET /api/files/mask-layers?filename=...` ✅ | Resolve all 4 mask layers from any one hash | Round-trip helper. |
| `GET /api/assets` ✅ | List user assets | Filters: `include_tags`, `exclude_tags`, `name_contains`, `metadata_filter` (JSON). Sort by `name\|created_at\|updated_at\|size\|last_access_time`. |
| `POST /api/assets` ✅ | Upload (multipart) **or** import from URL (JSON) | URL mode: `{ url, name, tags?, user_metadata?, preview_id? }`. Returns 200 (existing hash) or 201 (new). |
| `POST /api/assets/from-hash` ✅ | Create asset ref from existing hash | Hash must be `blake3:` or `sha256:` prefix + 64 hex. |
| `GET /api/assets/remote-metadata?url=...` ✅ | HEAD-like metadata preview | Civitai / HF. Returns content_length, content_type, suggested filename, preview, `ValidationResult` (rejects PickleTensor). |
| `POST /api/assets/download` ✅ | Background download from HF or Civitai | 200 if cached, 202 with `task_id` to poll via `GET /api/tasks/{task_id}`. **Primary mechanism for user LoRAs / models.** |
| `GET\|PUT\|DELETE /api/assets/{id}` ✅ | CRUD on asset | Update accepts `name`, `tags`, `mime_type`, `preview_id`, `user_metadata`. |
| `POST\|DELETE /api/assets/{id}/tags` ✅ | Tag add / remove | |
| `HEAD /api/assets/hash/{blake3:...}` ✅ | Existence check by hash | Trivial dedupe. |
| `GET /api/tags` ✅ | All tags with usage counts | |
| `GET /api/assets/tags/refine` ✅ | Tag histogram for filtered set | |

## Reference (node + model)

| Method & Path | Purpose | Notes |
|---|---|---|
| `GET /api/object_info` ✅ | **All** installed node definitions | `{ "<class_type>": NodeInfo, … }`. NodeInfo: `input` (required/optional, with `min`/`max`/`step`/`default`/combo enums), `output`, `output_is_list`, `output_name`, `category`, `description`, `python_module`, `deprecated`, `experimental`, `api_node`. **The single most important introspection endpoint.** |
| `GET /api/object_info/{node_class}` 🟡 | Single-node details | Documented for OSS only. Convention used by the JS frontend. Stable-by-convention. Fall back to filtering full payload if 404. |
| `GET /api/experiment/models` ⚠️ | List model folders | Replaces legacy `/models`. Returns `[{ name, folders[] }]`. Public (no auth). |
| `GET /api/experiment/models/{folder}` ⚠️ | List models in a folder | e.g. `checkpoints`, `loras`, `vae`, `upscale_models`. Returns `[{ name, pathIndex }]`. |
| `GET /api/experiment/models/preview/{folder}/{path_index}/{filename}` ⚠️ | WebP model preview | |
| `GET /api/features` ✅ | Server feature flags | `supports_preview_metadata`, `max_upload_size`, more. Optional auth. |
| `GET /api/workflow_templates` ✅ | Public workflow templates | Currently empty object on Cloud — community templates live on `comfy.org/workflows`. |
| `GET /api/global_subgraphs` ✅ | Subgraph blueprints | Map of subgraph IDs to metadata. `GET /api/global_subgraphs/{id}` returns full. |

## Account & system

| Method & Path | Purpose | Notes |
|---|---|---|
| `GET /api/user` ✅ | Current user info | Returns `{ status: "active" \| "waitlisted" }`. |
| `GET\|POST\|DELETE /api/userdata`, `/api/userdata/{file}` ✅ | Per-user JSON/file scratch storage | Used for saved workflows, settings. `split` and `full_info` query params accepted but ignored. |
| `GET /api/system_stats` ✅ | Versions + device info (public) | `comfyui_version`, `comfyui_frontend_version`, `cloud_version`, `pytorch_version`, devices with `vram_total` / `vram_free`. **Use to version-stamp every run.** |

## WebSocket

- **URL**: `wss://cloud.comfy.org/ws?clientId={uuid}&token={api_key}` ✅
- `clientId` is **currently ignored** — all of a user's connections receive the same broadcast. Pass a unique value for forward compatibility but **always filter incoming messages by `data.prompt_id === yourPromptId`** in client code.

JSON message types and binary frame layouts: see [`websocket-protocol.md`](./websocket-protocol.md).

## Cloud-vs-OSS lockdowns

Verbatim from the OpenAPI prologue:

| Field | Endpoint(s) | Cloud behavior |
|---|---|---|
| `subfolder` | `/api/view`, `/api/upload/*` | **Ignored.** Content-addressed (hash). Returned in responses for client-side organization. |
| `type` (input/output/temp) | `/api/view`, `/api/upload/*` | Partial — tag-organized buckets, not directory-organized. |
| `overwrite` | `/api/upload/*` | **Ignored.** Identical content = same hash. |
| `number`, `front` | `/api/prompt` | **Ignored.** Cloud uses its own per-user fair scheduling. |
| `split`, `full_info` | `/api/userdata` | **Ignored.** Always returns full metadata. |

OSS-only routes (in `comms_routes`) that **don't exist** on Cloud — proxy must not call them:

- `GET /embeddings`
- `GET /extensions`
- `GET /view_metadata/{folder}`
- `POST /free` (unload models)
- `GET /v2/userdata`, `POST /userdata/{file}/move/{dest}`
- `POST /users`, `GET /users`

## HTTP status codes

| Status | Meaning |
|---|---|
| 400 | Invalid workflow / bad fields |
| 401 | Missing/invalid API key |
| 402 | Insufficient credits |
| 413 | File too large |
| 415 | Unsupported media type |
| 422 | Validation error (e.g. HF download timeout) |
| 429 | **Subscription inactive** (NOT rate-limited) |
| 500 | Internal server error |
| 503 | Service unavailable |

## Upstream-only / OSS endpoints (Cloud presence unverified)

The upstream `research/openapi-oss-upstream.yaml` (8725 lines) is a superset of the docs `research/openapi-cloud.yaml` (3732 lines). The following endpoints appear in upstream but **may or may not** be exposed on Cloud — verify with a probe before relying on them:

| Method & Path | Probable purpose | Verification |
|---|---|---|
| `GET /api/secrets`, `GET\|PUT\|DELETE /api/secrets/{id}` | User-stored HF/Civitai tokens (for `/api/assets/download` of private models) | Hit with `X-API-Key`; 200/404 = exists, 401 = exists-but-auth-issue, full-page HTML = SPA fallback (doesn't exist) |
| `GET /api/tags` | List all asset tags with usage counts | Probe |
| `GET /api/node_replacements` | Backwards-compatible node aliases (when class_types are renamed) | Probe |
| `GET /api/vhs/queryvideo`, `GET /api/vhs/viewvideo`, `GET /api/vhs/viewaudio` | VideoHelperSuite-specific media playback | Probe; likely Cloud-exposed since VHS is pre-installed |
| `GET /api/i18n` | Frontend localization strings | Probably Cloud-exposed (UI needs it) |
| `POST /api/feedback` | User feedback submission | Probe |

**Internal routes** (frontend-only, not in OpenAPI, usually not exposed publicly on Cloud):

- `GET /internal/logs` — Raw server logs
- `GET /internal/files/{directory_type}` — List files in `output` / `input` / `temp`
- `GET /internal/folder_paths` — Map of all model folder categories
- `PATCH /internal/logs/subscribe` — Subscribe to live log streaming

Don't build skill features around `/internal/*` endpoints — they're not part of the public contract.

## Cross-references

- WebSocket message types and binary frame layouts: [`websocket-protocol.md`](./websocket-protocol.md)
- Workflow JSON format (API vs canvas): [`workflow-format.md`](./workflow-format.md)
- Error codes + exception_type enum: [`errors-and-limits.md`](./errors-and-limits.md)
- Asset management deep-dive: [`asset-management.md`](./asset-management.md)
- Cost / concurrency: [`cost-and-concurrency.md`](./cost-and-concurrency.md)
- Docs spec vs upstream spec diff: [`conflicts-and-limitations.md`](./conflicts-and-limitations.md)
