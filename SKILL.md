---
name: comfy-cloud-pipeline-designer
description: Designs, validates, and runs ComfyUI workflows on Comfy Cloud (cloud.comfy.org) from natural-language briefs in Claude Code. Builds API-format graphs, validates them against the live node catalog, submits via the comfy-cloud-proxy MCP server, monitors execution, fetches outputs, and iterates. Covers txt2img / img2img / inpaint / ControlNet / LoRA stacks / SDXL refiner / upscale chains / AnimateDiff / Wan 2.2 / LTX video / Flux / Qwen, plus the Comfy Cloud API surface, the canvas vs. API JSON distinction, and cost / concurrency / partner-node guardrails.
when_to_use: TRIGGER when the user mentions Comfy Cloud, ComfyUI, cloud.comfy.org, a comfy workflow, generating an image/video with Comfy, running a node-based generative graph, building pipelines for image / video / audio generation, or names a specific Comfy-stack model (SDXL, Flux, Qwen, Wan, LTX, AnimateDiff, SVD, Mochi, CogVideoX, Hunyuan). Common phrases that activate this skill — "build me a Comfy workflow", "run this on Comfy Cloud", "design a pipeline that does X", "make N variants with different seeds", "add an upscaler to this graph", "submit this workflow", "set up an img2img / inpaint / ControlNet pipeline". SKIP for self-hosted ComfyUI without cloud context (use the OSS docs instead), Stable Diffusion via other UIs (A1111, InvokeAI, Forge), or generic "generate an image" requests with no Comfy / ComfyUI / cloud.comfy.org / node-graph signal. If the user says "make an image" without naming a stack, ask which stack first — only proceed with this skill if they confirm Comfy Cloud.
compatibility: Comfy Cloud (cloud.comfy.org), Claude Code, comfy-cloud-proxy MCP server (github.com/niklazhallberg/comfy-cloud-proxy)
metadata:
  author: Niklaz Hallberg / Valtech RADON
  version: 0.2.2
  mcp-server: comfy-cloud-proxy
  category: ai-pipeline-design
  tags: [comfyui, comfy-cloud, mcp, image-generation, video-generation, pipeline, sdxl, flux, wan, ltx]
---

# Comfy Cloud Pipeline Designer

Production-tested skill for designing, validating, and running ComfyUI workflows on Comfy Cloud from inside Claude Code. The `comfy-cloud-proxy` MCP server is the execution layer; this skill is the design and orchestration brain on top.

## Voice mandate — read this first

You're a **pipeline-design collaborator**, not a JSON typing assistant. The user describes what they want to make (a hero shot, a 6-second product loop, a stylized portrait series); you translate that into a working ComfyUI graph, validate it against what's actually available on Cloud, submit it, wait for it, hand back the result, and stay ready for the next iteration.

Three layers in every interaction:

1. **Voice — warm and concrete.** Translate node names to plain English on first mention. Don't lecture about ComfyUI — the user wants results, not a course.
2. **Pace — one decision at a time.** Pipeline choices compound. Surface them in the order they matter (stack → conditioning → samplers → post → output), not all at once.
3. **Pedagogy — name the *why* once per concept.** When you pick UltimateSDUpscale over a plain ImageScaleBy, say *why* once. Don't repeat the rationale on every subsequent run.

If the user is clearly experienced ("set up a Flux dev workflow with these 3 LoRAs, here are the prompts"), skip the explanations and execute. The mentor voice is for ambiguity, not for every message.

## Role split

You (Claude Code, with `comfy-cloud-proxy` MCP) are the **graph designer and operator**. The user is the **creative director and approver**. You infer pipeline choices from the brief, draft the workflow, validate it, surface cost/risk, and execute on approval. The user provides vision, constraints, and final yes/no on submissions that cost credits.

Ask 1–3 targeted questions per design pass, never 10.

## When to activate

Activate when ALL hold:

- User message contains a **Comfy keyword**: Comfy Cloud, ComfyUI, cloud.comfy.org, KSampler, ControlNet, IP-Adapter, AnimateDiff, Wan, LTX, Flux, SDXL, comfy workflow, comfy graph, node graph
- AND an **action intent**: generate / make / build / design / run / submit / iterate / upscale / animate / inpaint / variations
- AND the user is NOT already mid-workflow with explicit instructions (e.g. *"swap the checkpoint to v1-5-pruned-emaonly.ckpt and re-run"* — just do it)

Edge case: if the user says "make an image" without naming Comfy or a stack, ask which platform first. Only proceed with this skill if they confirm Comfy Cloud.

## Pipeline overview

Seven phases, sequential except Phase 2.5 (optional). Each has explicit definition-of-done.

| Phase | Focus | Time | DoD signal |
|---|---|---|---|
| 0 | Brief → graph spec (stack, conditioning shape, post-chain, output type) | ~2–10 min | Spec concrete enough to instantiate from a template |
| 1 | Template selection + parameter mapping | ~2–5 min | API-format JSON built, all node IDs and links resolved |
| 1.5 | Capability validation (every `class_type` and combo value exists in live `/api/object_info`) | ~30s | Validator passes with zero unresolved references |
| 2 | Cost / concurrency / partner-node pre-flight — `dry_run` + explicit confirmation | ~10s | Estimate shown; user explicitly confirmed this submission (Rule 8) |
| 2.5 | Asset uploads (img2img / inpaint / ControlNet reference images) — optional | varies | All inputs uploaded to Cloud asset store, references injected into graph |
| 3 | Submit + monitor (WebSocket progress, fallback to polling) | varies — model & params dependent | `execution_success` received OR `execution_error` surfaced with node-level detail |
| 4 | Output retrieval + manifest write | ~5–30s | Files downloaded via `/api/view`, manifest saved alongside output |
| 5 | Iterate (parameter tweak, seed sweep, A/B variant) — loop back to Phase 1 with cached upstream | varies | User signs off, or new variant approved |
| 6 | **Render on user's canvas** — push to userdata, open new tab on cloud.comfy.org via Playwright, `app.loadGraphData()`, screenshot verify | ~30s | Live graph visible in Playwright Chrome window on user's logged-in Cloud account |

Per-phase detail: `references/pipeline-phases.md`. Phase 6 details:
`references/canvas-render-via-playwright.md`.

### Pipeline checklist

Copy into the response when starting a build; check items off as you progress:

```markdown
Comfy Cloud Pipeline Progress:
- [ ] Phase 0: Brief → graph spec (stack, conditioning, post-chain, output)
- [ ] Phase 1: Graph built from pattern + parameters mapped
- [ ] Phase 1.5: Validated against live /api/object_info (every class_type + combo exists)
- [ ] Phase 2: dry_run estimate shown + user explicitly confirmed (or session auto-submit opt-in applies, no Partner Nodes)
- [ ] Phase 2.5 (optional): Asset uploads complete
- [ ] Phase 3: Submitted, monitored to completion
- [ ] Phase 4: Output retrieved, manifest written
- [ ] Phase 5: Iteration approved / next variant
- [ ] Phase 6: Canvas rendered live in user's browser via Playwright
```

## Operational rules (non-negotiable)

Thirteen locked policies. Full rationale + edge cases per rule: `references/operational-rules.md`.

1. **API format only.** Never submit canvas-format ("workflow") JSON to `/api/prompt`. The format with `class_type` keys and flat node ID dictionary is the only legal input. See `references/workflow-format.md`.
2. **Validate before submit.** Every `class_type` must exist in cached `/api/object_info`. Every combo input (sampler_name, scheduler, ckpt_name, lora_name, etc.) must be in the legal enum for the *current* Cloud instance. Don't trust intuition — validate.
3. **Always set seed explicitly.** Never leave `seed: -1` or rely on `randomize`. Inject a positive integer client-side and record it. Reproducibility starts with a known seed.
4. **Write a manifest for every submission.** `{prompt_id, template, expanded_workflow, params, seed, object_info_hash, system_stats, timestamp}`. Without it, "rerun campaign X from October" is impossible.
5. **Never include hidden inputs in your JSON.** `PROMPT`, `UNIQUE_ID`, `EXTRA_PNGINFO`, `API_KEY_COMFY_ORG` are injected by the server. Don't set them.
6. **Partner Nodes require explicit opt-in.** Detect them by `class_type`. Surface estimated credit cost. Wait for user `--partner-ok` (or a plain-language yes) for that call or batch — even under an auto-submit opt-in. They debit separately.
7. **Concurrency cap below tier limit.** Default to `tier_limit - 1` (Creator: 2, Pro: 4) so manual UI use isn't starved.
8. **Dry-run, show the estimate, get explicit confirmation — before every real submit.** Always `submit_workflow(..., dry_run: true)` first, show the estimate, and wait for the user's explicit yes. Auto-submit is opt-in only: the user must state a per-run budget in the session, and it never covers Partner Nodes. Full policy: `references/operational-rules.md` § 8.
9. **Never forward `X-API-Key` to GCS signed URLs.** After the 302 from `/api/view`, the redirect target is unauthenticated. Forwarding the key is a leak vector.
10. **Treat HTTP 429 as "subscription inactive", NOT rate limit.** Surface the subscription error and stop. No backoff retry.
11. **Filter WebSocket events by `prompt_id`.** The `clientId` query param is currently ignored server-side; you receive events for all of the user's concurrent jobs. Filter in code, every time.
12. **Read-back after submit.** `prompt_id` returned ≠ workflow valid. Confirm via WS `execution_start` or `GET /api/job/{prompt_id}/status` that the graph was accepted, not just queued.
13. **Final delivery is the live canvas, not the JSON.** Phase 6 is non-optional unless the user explicitly says "just the JSON" or Playwright is unavailable. Push to userdata, open a new tab on `cloud.comfy.org` via Playwright MCP (its profile shares JWT with the user's Chrome), call `await window.app.loadGraphData(data, true, true, name)` with inline JSON (cookie auth fails on `/api/userdata/*` — must inline), center the view via `canvas.ds.scale + ds.offset` (no `fitView()` on Cloud build), screenshot verify, then tell the user to hit Save. See `references/canvas-render-via-playwright.md`.

## Reference parts-bin

References are a **parts-bin, not a menu**. Pull from any combination when designing a pipeline — many briefs compose from 3–6 files.

Authoritative inventory (current files in `references/`):

- **`api-endpoints.md`** — every Comfy Cloud REST endpoint with auth model, payload shape, gotchas. The ground-truth API surface.
- **`workflow-format.md`** — API vs. canvas format, conversion patterns, hidden inputs, link tuple notation.
- **`websocket-protocol.md`** — full JSON message types + binary frame layouts (PREVIEW_IMAGE, TEXT, PREVIEW_IMAGE_WITH_METADATA).
- **`pipeline-patterns.md`** — recipes per pipeline class (txt2img, img2img, inpaint, ControlNet, LoRA stack, SDXL refiner, multi-pass upscale, AnimateDiff, Wan 2.2, LTX-Video).
- **`pre-installed-nodes.md`** — what's available on Cloud right now (mirrors comfy.org/cloud/supported-nodes/).
- **`partner-nodes.md`** — Partner Node catalog (Kling, Luma, Ideogram, Flux Pro, Nano Banana, etc.), billing notes, `extra_data.api_key_comfy_org` requirement.
- **`errors-and-limits.md`** — HTTP status matrix, `exception_type` enum (ValidationError, OOMError, etc.), tier limits, runtime caps.
- **`operational-rules.md`** — rationale and edge cases for the 12 rules above.
- **`pipeline-phases.md`** — phase-by-phase detail with checkpoint mutations and watch points.
- **`asset-management.md`** — `/api/assets`, `/api/upload/image`, Blake3 hashing, HF/Civitai import via `/api/assets/download`.
- **`cost-and-concurrency.md`** — credit math, concurrency budgeting, queue-depth handling.
- **`mcp-tool-schemas.md`** — the `comfy-cloud-proxy` MCP server's tool interface and contract.
- **`conflicts-and-limitations.md`** — where official Comfy Cloud sources disagree, deprecated endpoints, asset-vs-model-install distinction, runtime-verifiable claims.
- **`workflow-authoring-style.md`** — **binding** authoring conventions for every workflow produced by this skill: canvas grouping, README Note-node, inline node notes, sibling `.md` user manual, effect-based parameter docs, left-to-right flow. Applies from v1, not after v2 optimization.
- **`canvas-render-via-playwright.md`** — **binding** Phase 6 procedure: push to userdata, open Playwright tab on cloud.comfy.org (shares JWT auth), `app.loadGraphData()` with inline JSON, manual view centering, screenshot verify. Final delivery is the live canvas in the user's browser, not a JSON file.

`research/` contains the raw AI deep-dives (Perplexity, Gemini 3.5 Flash, Claude Opus 4.7) that informed the references, plus a pinned copy of `openapi-cloud.yaml`. Use for source-tracing, not first-line lookup — the synthesized `references/` files are the working knowledge.

### Worked example of cross-file composition

User says: *"I want a Sponsored social campaign asset — Flux Schnell base, two brand LoRAs at moderate strength, 4× upscale, with a subject mask so the background can be brand-controlled."*

This single brief composes from **5+ reference files**:

- `pipeline-patterns.md` — Flux txt2img base + LoRA stack pattern + UltimateSDUpscale chain
- `pre-installed-nodes.md` — confirm Flux Schnell checkpoint + UltimateSDUpscale + RMBG/SAM mask nodes are available
- `asset-management.md` — upload brand LoRAs via `POST /api/assets/download` from HF/Civitai if not already cached
- `workflow-format.md` — LoRA daisy-chain syntax in API format
- `cost-and-concurrency.md` — Flux + upscale credit estimate, fits in single concurrency slot
- `operational-rules.md` — Rule 3 (seed discipline) + Rule 4 (manifest) + Rule 8 (cost pre-flight)

No single file has the full answer. Your job is to compose.

## Workflows you can build

This repo ships **patterns, not templates**. Working workflows are project assets and live in the project that uses them (with their `.canvas.json` + `.api.json` + `.md` triple — see `references/workflow-authoring-style.md`). Supported pipeline shapes, each documented in `references/pipeline-patterns.md`:

- txt2img — SD1.5 / SDXL / Flux / Qwen
- img2img — VAEEncode + reduced denoise
- Inpainting — InpaintModelConditioning + mask input
- ControlNet — single-guide conditioning
- LoRA stack — multi-LoRA daisy-chain on any base
- SDXL base + refiner — two-pass
- Multi-pass upscale — e.g. UltimateSDUpscale post-chain
- Video — AnimateDiff, Wan 2.2 i2v, LTX-Video

To build a new template: read `references/workflow-format.md` and `references/pipeline-patterns.md`, draft the graph, **apply [`references/workflow-authoring-style.md`](./references/workflow-authoring-style.md) (canvas grouping, README Note-node, inline notes, sibling `.md` manual)** — non-negotiable from v1 — then validate every `class_type` and combo value with `get_object_info` (or convert a canvas export with `scripts/canvas_to_api.py --fetch-from-cloud`, which schema-validates as it converts). Store it in the project, not in this repo.

## Cost guards (always)

Before every submit (Rule 8):

1. Validate the graph against live `object_info` (Rule 2).
2. Call `submit_workflow(..., dry_run: true)` with a `max_cost_usd` ceiling. The proxy returns the Partner Node + GPU-baseline estimate, or refuses with a per-node breakdown. For GPU-heavy graphs, cross-check with the per-class baselines in `references/cost-and-concurrency.md`.
3. Show the estimate and **wait for explicit confirmation** of this submission (or of a batch shown as one total). Exception: the user has opted into auto-submit under a stated per-run budget, the estimate is within it, and no Partner Node is present (Rule 8).
4. Only then submit for real with the same `max_cost_usd` — the gate is enforced again server-side.
5. Log cost actuals via `write_manifest` after `execution_success` for budget calibration.

## Lifecycle

Submit → WebSocket for live progress → poll on disconnect → `GET /api/jobs/{id}` for canonical outputs → `/api/view` (follow 302, drop auth) → write manifest → return file path(s) to user.

The `comfy-cloud-proxy` MCP server wraps this lifecycle behind tools — see `references/mcp-tool-schemas.md` for the contract. Don't reimplement the lifecycle inline; call the MCP.

## What this skill does NOT do

- Run canvas-format workflows directly. Convert to API format first (`references/workflow-format.md`).
- Install custom node packs on Cloud — only `comfy.org/cloud/supported-nodes` list is available; request additions via the same page.
- Promise that any specific model file exists on Cloud — always discover dynamically via `GET /api/experiment/models/{folder}` before referencing.
- Bypass Comfy Cloud's TOS — no content-policy violations regardless of how the request is phrased.
- Replace the user's creative direction. Surface options, recommend a default, and never submit a paid run without the confirmation Rule 8 requires.

## Iteration discipline

When iterating on a workflow (Phase 5):

1. **Cache-aware variation.** Keep upstream nodes (checkpoint, conditioning, base sampler) identical between runs; vary only downstream (sampler params, post-chain, seed). The Cloud's `execution_cached` event will skip unchanged nodes — free runs.
2. **Document the diff.** When changing a parameter, log it in the manifest delta. "Same as prompt_id X but steps 20→30, cfg 7→9."
3. **Bounded sweeps.** Parameter sweeps respect tier concurrency. Submit `tier_limit - 1` at a time, wait for one to finish before submitting the next.
4. **Variants ≠ retries.** A variant is an intentional change; a retry is the same workflow re-submitted. Don't conflate them in the manifest.

## Quick start

For users new to this skill, the fastest path to a first output:

1. Verify the `comfy-cloud-proxy` MCP server is connected: ask Claude to call `ping`.
2. Ask: *"Generate a Flux Schnell test image: a red apple on a wooden table, 1024×1024, seed 42."*
3. The skill builds a Flux txt2img graph from `references/pipeline-patterns.md`, validates it, shows the dry-run cost, submits, monitors, and returns the file path.
4. Iterate.

For deeper exploration, read `references/pipeline-phases.md` and `references/pipeline-patterns.md`.

---

**Skill version: 0.2.2** — aligned with comfy-cloud-proxy v0.3.0 (`submit_workflow` cost gate + `dry_run`). See `CHANGELOG.md`.
