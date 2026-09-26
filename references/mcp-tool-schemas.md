# MCP Tool Schemas

The [`comfy-cloud-proxy`](https://github.com/niklazhallberg/comfy-cloud-proxy) MCP server is the execution layer this skill operates through. This file documents the tools it exposes (proxy **v0.3.0**) and how to invoke them.

## Shipped tools

| Tool | Signature (abridged) | Returns |
|---|---|---|
| `ping` | `()` | `pong` |
| `get_object_info` | `(nodeName?)` | Without arg: `{ totalNodes, sampleNodes }`. With arg: full NodeInfo schema for that `class_type` |
| `upload_image` | `(filePath, type="input")` | `{ name, subfolder, type, clientHash, assetSeenOnCloud }` — reference `name` in `LoadImage` |
| `upload_mask` | `(filePath, originalRef: { filename, subfolder?, type? }, type="input")` | Mask layer metadata |
| `submit_workflow` | `(workflow, max_cost_usd, inputs?, partnerNodeAuth=true, extraData?, dry_run?)` | `{ promptId, readBackStatus, cost }`, or `{ dryRun: true, cost, workflow }` |
| `get_job_status` | `(promptId)` | Full job: status, outputs, `execution_meta`, `execution_error` |
| `view_output` | `(filename, savePath, subfolder?, type="output", channel="rgba")` | `{ savedTo, sizeBytes, contentType, sha256 }` |
| `write_manifest` | `(promptId, template, workflowApiPath, params, seed, partnerNodeCosts, …, savePath)` | `{ savedTo, totalAssetCostUsd, … }` — satisfies Rule 4 |
| `upload_workflow_to_userdata` | `(localPath, remotePath?, overwrite=true)` | `{ accessibleAt }` — Phase 6 step 1 |
| `delete_workflow_from_userdata` | `(remotePath)` | `{ deletedPath, httpStatus }` |
| `submit_simple_txt2img` / `export_simple_txt2img_workflow` | `(prompt, width?, height?, steps?, cfg?, seed?)` | Minimal SD1.5 smoke test |

### `submit_workflow` — the main entry point

- **`workflow`** — API-format JSON (never canvas format; Rule 1). String values of the exact form `"{{NAME}}"` are placeholders.
- **`inputs`** — `{ NAME: value }` for every placeholder. Any unresolved placeholder → refusal, nothing submitted.
- **`max_cost_usd`** — required hard ceiling. The proxy estimates Partner Node cost (static upper-bound table) plus a GPU baseline and refuses over budget with a per-node breakdown. This is the proxy-side enforcement of Rules 6 and 8 — still surface the estimate to the user before calling.
- **`dry_run`** — resolve placeholders + run the cost gate, return the final graph and estimate, submit nothing. Needs no API key. Use it to show the user the cost before asking for approval.
- **`partnerNodeAuth`** — injects `extra_data.api_key_comfy_org` (default on). Never set hidden inputs yourself (Rule 5).

## Invocation pattern

```
1. ping                                        // verify MCP is up
2. get_object_info(nodeName)                   // Phase 1.5 — validate class_types + combo values
3. upload_image / upload_mask                  // Phase 2.5, if the graph needs inputs
4. submit_workflow(..., dry_run: true)         // Phase 2 — show cost, get approval
5. submit_workflow(...)                        // Phase 3 — returns promptId
6. get_job_status(promptId)                    // poll until success / error
7. view_output(filename, savePath)             // Phase 4
8. write_manifest(...)                         // Phase 4 — Rule 4
9. upload_workflow_to_userdata(localPath)      // Phase 6 — then render via Playwright
```

## Not yet in the proxy

Handled by the skill directly (or out of scope) until they land:

| Tool | Purpose |
|---|---|
| `wait_for_prompt(prompt_id, timeout?)` | Block on WebSocket until `execution_success` / `error` — until then, poll `get_job_status` |
| `cancel_prompt` / `interrupt_current` / `get_queue` | Queue control |
| `list_models(category)` | Wrap `GET /api/experiment/models/{folder}` |
| `upload_asset_from_url(url, tags)` | `POST /api/assets/download` from HF/Civitai |

## Configuration

See the proxy's [README](https://github.com/niklazhallberg/comfy-cloud-proxy#configuration). Key variables: `COMFY_CLOUD_API_KEY` (required for real calls), `COMFY_CLOUD_BASE_URL`, `COMFY_DRY_RUN`.

If `COMFY_CLOUD_API_KEY` is missing, tools that hit the Cloud API return an `isError` response with a clear message.

## Cross-references

- Proxy implementation: https://github.com/niklazhallberg/comfy-cloud-proxy
- Underlying API: [`api-endpoints.md`](./api-endpoints.md)
- WebSocket events (for the planned `wait_for_prompt`): [`websocket-protocol.md`](./websocket-protocol.md)
