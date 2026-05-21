# Operational Rules

The 12 non-negotiable rules from `SKILL.md`, expanded with rationale and edge cases.

## 1. API format only

Never submit canvas-format ("workflow") JSON to `/api/prompt`.

**Why:** Canvas format has `nodes: [...]` + `links: [...]` with positions, link IDs, widget value arrays. The API expects a flat dict keyed by string node IDs with `{ class_type, inputs }`. Submitting canvas format returns `400 Invalid workflow`.

**How to apply:** At the proxy boundary, check `if "nodes" in payload and "links" in payload: raise FormatError`. Convert via [`workflow-format.md`](./workflow-format.md) before submission.

## 2. Validate before submit

Every `class_type` must exist in cached `/api/object_info`. Every combo input (sampler_name, scheduler, ckpt_name, lora_name, ControlNet model name, etc.) must be in the legal enum for the *current* Cloud instance.

**Why:** Cloud's pre-installed node list and model files change over time. A workflow that worked last week may have a removed checkpoint today. Server-side validation returns useful errors but costs a round-trip; client-side validation against a cached `object_info` is instant and prevents wasted submissions.

**How to apply:** Cache `/api/object_info` on first use per session (or daily). For every node in the proposed workflow, look up `class_type` and verify every combo input's value is in the enum. Refresh cache if a value fails — combo enums can change.

## 3. Always set seed explicitly

Never leave `seed: -1` or rely on `randomize`. Generate a positive integer client-side and inject it.

**Why:** Reproducibility starts with a known seed. `-1` / `randomize` lets the server pick — you lose the ability to regenerate, A/B compare, or trace anomalies. Even in "I want a random one" cases, generate the random integer client-side so you record it.

**How to apply:** `seed = random.randint(0, 2**63 - 1)` before workflow injection. Always log the chosen seed in the manifest.

## 4. Write a manifest for every submission

Save `{prompt_id, template, expanded_workflow, params, seed, object_info_hash, system_stats, timestamp}` to disk.

**Why:** Without a manifest, "rerun the campaign hero from October" is impossible. With one, it's `replay_manifest(path)`.

**How to apply:** Default location `outputs/manifests/{prompt_id}.json`. Include enough state to reconstruct the run independently — workflow as-submitted, all parameters, seed, Cloud `system_stats` snapshot, hash of the `object_info` cache that validated the workflow.

## 5. Never include hidden inputs in your JSON

`PROMPT`, `UNIQUE_ID`, `EXTRA_PNGINFO`, `API_KEY_COMFY_ORG` are server-injected. Don't set them in workflow node `inputs`.

**Why:** These are filled in by the executor based on the submission context. Setting them client-side either silently does nothing or produces ValidationErrors.

**How to apply:** When parameterizing a template, never write into these keys. For `API_KEY_COMFY_ORG` specifically: it's set at the *submission level* via `extra_data.api_key_comfy_org`, not inside any node.

## 6. Partner Nodes require explicit opt-in

Detect by `class_type`. Surface estimated credit cost. Block submission until user passes `--partner-ok` (or equivalent skill-level signal).

**Why:** Partner Nodes (Kling, Luma, Ideogram, Flux Pro, Nano Banana, etc.) call third-party APIs and bill credits separately from base GPU time. A single Partner Node run can cost 100× a normal generation. Surprise bills break trust.

**How to apply:** Maintain a list of Partner Node `class_type`s (see [`partner-nodes.md`](./partner-nodes.md)). On validation, flag presence; surface estimated cost; require explicit user confirmation. Default to refusal.

## 7. Concurrency cap below tier limit

Default to `tier_limit - 1` (Creator: 2 of 3, Pro: 4 of 5).

**Why:** The user often has the Cloud UI open while the skill runs. If the skill saturates the concurrency budget, the user's manual submissions queue indefinitely — bad collaboration UX.

**How to apply:** Track in-flight `prompt_id`s in the proxy. Refuse new submissions when at cap-minus-one. Override via `--full-concurrency` flag when the user is intentionally batch-only.

## 8. Pre-flight cost estimate

Estimate GPU-seconds from step count × per-step seconds for the chosen model class. Refuse if over the user's budget (default 180 GPU-seconds per submission).

**Why:** A Flux dev at 1024×1024 / 28 steps is ~30s; a Wan 2.2 i2v at 4 sec / 720p can be 5+ minutes. Without an estimate, the agent can casually queue work the user didn't intend to pay for.

**How to apply:** Per-class baselines in [`cost-and-concurrency.md`](./cost-and-concurrency.md). Compute, compare to `$COMFY_BUDGET_SECONDS`, surface the breakdown, wait for `--budget-ok` if over.

## 9. Never forward `X-API-Key` to GCS signed URLs

After the 302 from `/api/view`, the redirect target is unauthenticated. Forwarding the key leaks it.

**Why:** Comfy Cloud serves outputs via signed GCS URLs to keep its own auth surface narrow. The signed URL has its own time-limited auth — forwarding `X-API-Key` to GCS at best does nothing, at worst gets the key logged in third-party access logs.

**How to apply:** In the HTTP client, use `redirect: "manual"` on the `/api/view` request, then re-fetch the `Location` URL with an empty header set.

## 10. Treat HTTP 429 as "subscription inactive", NOT rate limit

Surface a "subscription needs attention" error and stop. Don't back-off-retry.

**Why:** Comfy Cloud uses 429 for `InactiveSubscriptionError` — credits exhausted, payment failed, plan paused. Treating it as transient rate-limiting and retrying just burns time before the user discovers the real problem.

**How to apply:** On any 429, return a structured error to the user with link to billing. Don't loop.

## 11. Filter WebSocket events by `prompt_id`

The `clientId` query param on the WebSocket is currently ignored server-side. You receive events for *all* of the user's concurrent jobs across *all* their open sockets.

**Why:** This is a server-side design choice that may change but hasn't. If you don't filter, parallel sweeps see each other's `executed` events and chaos ensues.

**How to apply:** Every WS message handler: `if (data.data?.prompt_id !== myPromptId) return;` before touching state.

## 12. Read-back after submit

`POST /api/prompt` returning a `prompt_id` ≠ the workflow was accepted. Confirm via WS `execution_start` OR `GET /api/job/{prompt_id}/status` before treating the submission as in-flight.

**Why:** A `prompt_id` may come back for a workflow that the server later rejects on graph traversal (e.g. missing node, type mismatch the static validator didn't catch). The early failure surfaces as a `node_errors` entry in the original response OR as an `execution_error` shortly after.

**How to apply:** Inspect `node_errors` on the submission response — if present and non-empty, the workflow is invalid. Otherwise watch the WS or poll status to confirm transition to `in_progress`.

## When in doubt

The 12 rules are derived from production incidents. If you find yourself wanting to skip one, the safer move is to ask the user explicitly rather than silently bypass.
