# Errors & Limits

## HTTP status codes

| Status | Meaning | Recommended action |
|---|---|---|
| 400 | Invalid workflow / bad fields | Re-validate against `object_info`; check API vs canvas format |
| 401 | Missing/invalid API key | Surface auth error, don't retry |
| 402 | Insufficient credits | Surface billing error, don't retry |
| 413 | File too large | Check upload limit via `/api/features.max_upload_size` |
| 415 | Unsupported media type | Wrong content-type header on upload |
| 422 | Validation error (e.g. HF download timeout) | Retry with backoff on 422 specifically |
| **429** | **Subscription inactive — NOT rate-limited** | Surface subscription error, **do NOT retry** |
| 500 | Internal server error | Retry once after short delay; if persists, file issue |
| 503 | Service unavailable | Retry with exponential backoff |

## `execution_error` exception_type enum

The `execution_error` WebSocket payload carries `exception_type`, one of:

| Exception | Cause | Recovery |
|---|---|---|
| `ValidationError` | Workflow graph invalid at runtime (umbrella — see subtypes below) | Inspect `node_id` + subtype; fix and resubmit |
| `ModelDownloadError` | A model referenced in the workflow couldn't be fetched | Verify model exists on Cloud; check HF/Civitai source if user-uploaded |
| `ImageDownloadError` | An input image reference failed to load | Re-upload via `/api/upload/image` or `/api/assets` |
| `OOMError` | GPU out of memory | Reduce resolution, batch size, or steps; for video, reduce frame count |
| `PanicError` | Unrecoverable server error | Surface, file issue, don't auto-retry |
| `ServiceError` | Backend service unavailable | Retry with backoff |
| `WebSocketError` | WS-layer issue | Fall back to polling `/api/job/{id}/status` |
| `DispatcherError` | Job dispatch failed | Retry after short delay |
| `InsufficientFundsError` | Credits exhausted mid-execution | Surface billing error |
| `InactiveSubscriptionError` | Plan paused / payment failed mid-execution | Surface subscription error |

Every `execution_error` includes `node_id`, `class_type`, `exception_message`, `traceback`, and `executed` (the list of node IDs that completed before the failure).

## ValidationError subtypes

`ValidationError` returns a structured `details` dict with a specific `type` code. From `execution.py:824-1098` in the upstream ComfyUI repo, the canonical subtype list:

**Per-node validation errors:**

| Subtype | Triggered by | What it means |
|---|---|---|
| `missing_node_type` | Node has no `class_type` field OR `class_type` not in NODE_CLASS_MAPPINGS | The node class doesn't exist on this Cloud instance — refresh `object_info` cache and re-validate |
| `required_input_missing` | A required input in `INPUT_TYPES().required` isn't present in the node's `inputs` | Add the missing key |
| `bad_linked_input` | An input value isn't a 2-tuple `[node_id, slot_index]` when it should be a link | Fix the link reference |
| `return_type_mismatch` | An upstream node's output type doesn't match the consuming node's input type | Insert a converter or check enum compatibility |
| `invalid_input_type` | A primitive value failed type coercion (e.g. string to int) | Provide the right type |
| `value_smaller_than_min` / `value_bigger_than_max` | Numeric input outside the range declared in `INPUT_TYPES` | Clamp to the legal range |
| `value_not_in_list` | Combo input received a value not in its enum (e.g. unknown sampler_name) | Look up legal values via `/api/object_info` |
| `custom_validation_failed` | The node's `VALIDATE_INPUTS()` classmethod returned falsy | Read the message field for node-specific reason |
| `exception_during_validation` / `exception_during_inner_validation` | An unhandled exception during the node's own validation | Treat as a node bug — file with the node author |

**Graph-level errors:**

| Subtype | Triggered by | What it means |
|---|---|---|
| `dependency_cycle` | The graph contains a cycle | A node depends on its own output transitively — restructure |
| `prompt_no_outputs` | No nodes with `OUTPUT_NODE = True` | Add a `SaveImage` / `PreviewImage` / `VHS_VideoCombine` to anchor execution |
| `prompt_outputs_failed_validation` | All output nodes have errors | At least one output node must validate clean |

The skill should surface the subtype, not just "ValidationError". For `value_not_in_list` in particular, the most common cause is a model file that was removed from Cloud — refresh `object_info` and re-validate the combo value.

## Tier limits

| Tier | Price/mo | Credits/mo | API access | Concurrency | Runtime cap |
|---|---|---|---|---|---|
| Free | $0 | trial | ❌ | n/a | n/a |
| Standard | $20 | 4,200 | ❌ | n/a | 30 min |
| Creator | $35 | 7,400 | ✅ | 3 | 30 min |
| Pro | $100 | 21,100 | ✅ | 5 | 60 min |

- Queue depth cap: 100 workflows pending.
- GPU class: Blackwell RTX 6000 Pro, 96 GB VRAM (single class, no selection).
- Credit burn: per-second of active GPU time. Idle (UI editing, queueing) is free.

## What's NOT documented

Flag in skill copy and assume conservative defaults:

- **Per-endpoint REST rate limits.** Not published. Treat 429 as `InactiveSubscriptionError`, not rate limit. Add own client-side throttling.
- **Maximum prompt JSON size.** Not published. Assume ~1–10 MB is safe; large embedded base64 images hit upload limits sooner anyway.
- **Maximum WS frame size for previews.** Not published. Server may drop oversized; design for graceful degradation.
- **Asset retention policy.** Not published. Assume content-addressed assets persist; tagged scratch may have lifecycle.

## Cross-references

- HTTP endpoint inventory: [`api-endpoints.md`](./api-endpoints.md)
- WebSocket protocol: [`websocket-protocol.md`](./websocket-protocol.md)
- Cost math and concurrency budgeting: [`cost-and-concurrency.md`](./cost-and-concurrency.md)
