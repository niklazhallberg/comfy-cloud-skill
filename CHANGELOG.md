# Changelog

## 0.2.2 — 2026-09-26

Brings the skill in line with what the repo and the proxy actually ship.

**Fixed**
- `SKILL.md`, `references/pipeline-phases.md`, `references/pipeline-patterns.md` referenced a `templates/` directory and `scripts/validate_workflow.py` that were never shipped. The skill now builds from the patterns in `references/pipeline-patterns.md` and validates via `get_object_info` / `scripts/canvas_to_api.py --fetch-from-cloud`. Working workflows stay in the project that uses them.
- `references/mcp-tool-schemas.md` listed most proxy tools as "planned". Rewritten for proxy v0.3.0: all 12 shipped tools, the `submit_workflow` placeholder + `max_cost_usd` contract, `dry_run`, and the end-to-end invocation order.
- Cost guards (SKILL.md, Rule 8) now use the proxy's `max_cost_usd` gate and `dry_run` estimate instead of a local script.
- **Submission approval policy made explicit and consistent** (Rule 8 is now the single source): every real `submit_workflow` is preceded by `dry_run`, the estimate is shown, and the user must confirm explicitly. Auto-submit is an **opt-in** the user states in-session with a per-run budget, never covers Partner Nodes, and ends with the session. Removed the conflicting implicit "auto-approve up to ~60 GPU-seconds" default from `cost-and-concurrency.md`; SKILL.md, README, pipeline-phases, partner-nodes and mcp-tool-schemas now defer to Rule 8.

**Added**
- `LICENSE` (MIT), `research/README.md`.
- `references/_growth-protocol-pointer.md` now summarises the protocol inline, since the shared protocol repo is private.

**Docs**
- README rewritten: architecture diagram, phase overview, design decisions, scope & limitations, correct install path.

## 0.2.1 — 2026-06-08

Adds **Phase 6 — live canvas render** as the binding final step. Final delivery is now the live graph in the user's browser, not a JSON file or screenshot. Procedure: push to userdata for persistence, then open a new tab on cloud.comfy.org via the Playwright MCP (its profile shares JWT with the user's Chrome) and call `await window.app.loadGraphData(data, true, true, name)` with inline JSON. Cookie auth fails on `/api/userdata/*` so the JSON must be inlined into the `browser_evaluate` body — fetching from inside the browser returns 403 `auth_type_not_allowed`. `app.canvas.fitView()` does not exist on the Cloud build; center the view manually via `canvas.ds.scale + ds.offset + setDirty(true, true)`. Then screenshot, verify, hand off to the user with "hit Save to persist". New reference: `references/canvas-render-via-playwright.md`. New operational rule 13 in SKILL.md.

## 0.2.0 — 2026-05-22

Adds binding workflow authoring conventions and a generic canvas → API conversion script. Derived from learnings during the first production client pipeline build (a product-visualization A/B test). Pure-generic additions only — customer-specific templates live outside the skill.

**Added**
- `references/workflow-authoring-style.md` — **binding** authoring conventions for every workflow produced by this skill (~200 lines). Codifies the hybrid `canvas + api + md` triple-file format, README Note-node requirement, color-coded phase groups, inline node notes near key nodes, effect-based parameter documentation, left-to-right canvas flow, single-purpose over multi-mode workflows. Applies from v1, not after v2 optimization.
- `scripts/canvas_to_api.py` — generic canvas-format → API-format converter (~150 lines). Strips `Note`, `MarkdownNote`, `PrimitiveNode`, `Reroute` non-executable nodes. Handles the `control_after_generate` widget quirk on seed inputs. Schema-validates against live `/api/object_info` via `--fetch-from-cloud`. Refuses to write output if any required input is missing.

**Updated**
- `SKILL.md` — adds `references/workflow-authoring-style.md` to the parts-bin index. "To build a new template" instructions now reference the authoring-style rules as non-negotiable from v1. Frontmatter version bumped 0.1.0 → 0.2.0.

**Note on scope**
Client-specific workflows are NOT in this commit. They live in customer project directories. This commit captures only the generic patterns that any Comfy Cloud workflow should follow.

## 0.1.2 — 2026-05-21

Incorporates findings from a deep code-read of the upstream `comfy-org/ComfyUI` repository — significantly expands what the skill knows about Comfy Cloud's actual surface area.

**Corrected**
- `references/workflow-format.md` — hidden inputs are **six**, not four: added `dynprompt` (subgraph support) and `auth_token_comfy_org` (OAuth-style Partner-Node auth, separate from `api_key_comfy_org`). Added `OUTPUT_NODE` and `HAS_INTERMEDIATE_OUTPUT` node attribute documentation.
- `references/api-endpoints.md` — `POST /api/interrupt` is now granular: accepts `{ "prompt_id": "<id>" }` to target a specific job; empty body still affects all. Added dual-routing note (every `/path` is also at `/api/path`).
- `references/websocket-protocol.md` — `execution_interrupted` carries the **same payload shape** as `execution_error` (with `node_id`, `class_type`, `traceback`, etc.) — not an empty notification.

**Added**
- `references/websocket-protocol.md` — feature-flags handshake: client's first WS message can negotiate capabilities; server responds with `SERVER_FEATURE_FLAGS`. Documented `supports_preview_metadata`, `max_upload_size`, `extension.manager.supports_v4`, `node_replacements`, `assets` flags.
- `references/errors-and-limits.md` — `ValidationError` umbrella expanded with 11 specific subtype codes (`missing_node_type`, `required_input_missing`, `bad_linked_input`, `return_type_mismatch`, `invalid_input_type`, `value_smaller_than_min`/`max`, `value_not_in_list`, `custom_validation_failed`, `dependency_cycle`, `prompt_no_outputs`, `prompt_outputs_failed_validation`).
- `references/api-endpoints.md` — section listing upstream-only endpoints (`/api/secrets`, `/api/tags`, `/api/node_replacements`, `/api/vhs/*`, `/api/i18n`, `/api/feedback`) and internal routes (`/internal/logs`, `/internal/files/{type}`, `/internal/folder_paths`), with explicit "verify before relying" note.
- `references/partner-nodes.md` — expanded from ~10 to **71** Partner Node packages from upstream `comfy_api_nodes/`. Grouped by modality (video, image, 3D, LLM, audio). New providers: Bria, Recraft, Stability, Magnific, Topaz, HitPaw, Reve, Rodin, Tripo, Meshy, Sonilo, ElevenLabs, Claude (Anthropic), Gemini, OpenAI, OpenRouter, ByteDance Seedance/Seedream v1/v2/2, Sora 2, Vidu, Pixverse, Wavespeed, Veo/Veo2.
- `references/pre-installed-nodes.md` — all **28 model folder categories** documented (was ~6). Includes `text_encoders`, `diffusion_models`, `clip_vision`, `style_models`, `vae_approx`, `gligen`, `latent_upscale_models`, `hypernetworks`, `photomaker`, `classifiers`, `model_patches`, `audio_encoders`, `background_removal`, `frame_interpolation`, `geometry_estimation`, `optical_flow`, `detection`, `configs`, `diffusers`.
- `references/conflicts-and-limitations.md` — section on the docs spec being a subset of upstream; explicit pin-and-diff strategy for the two OpenAPI files.
- `CONTRIBUTING.md` — updated "Sources of truth" section to reflect the two-spec approach.
- `research/openapi-oss-upstream.yaml` — pinned copy of upstream `comfy-org/ComfyUI/openapi.yaml` (8725 lines vs docs' 3732). Sets up the two-spec source-of-truth model.

**Note on Cloud-vs-OSS scope**
The upstream `openapi.yaml` is a superset including OSS-only endpoints. Reference files mark upstream-only items as "verify before use." Probing scripts to validate which upstream endpoints Cloud actually exposes are planned but not yet shipped.

## 0.1.1 — 2026-05-21

Corrections and additions from ChatGPT deep-research (`research/chatgpt-deep-research-2026-05-21.md`).

**Corrected**
- `references/api-endpoints.md` — marked `/api/history_v2*` as **officially deprecated** in favor of `/api/jobs/*`. Documented that `prompt_id == job_id` (same identifier). Added `number` / `front` as accepted-but-ignored body parameters on `POST /api/prompt`.

**Added**
- `references/workflow-format.md` — widget value array wrapping (`{"__value__": [...]}` and `{"__type__": "CURVE", ...}`); `widget.serialize` vs `widget.options.serialize` gotcha; three frontend import paths (`loadGraphData`, `loadApiJson`, `importA1111`).
- `references/conflicts-and-limitations.md` — new file. Catalogs official source conflicts (concurrency 1-vs-3/5, BYO models scope), the asset-upload ≠ model-install distinction, MCP-output workflow-metadata gap, and the set of claims the skill should runtime-verify rather than hardcode.
- `SKILL.md` — added the new reference file to the parts-bin index.
- `research/chatgpt-deep-research-2026-05-21.md` — preserved as source provenance.

## 0.1.0 — 2026-05-21

Initial public skill structure.

**Locked**
- `SKILL.md` — frontmatter, voice mandate, 12 operational rules, pipeline phases, reference parts-bin index, quick start.
- Repository layout matching Anthropic's skill conventions and the `valtech-radon-lens-studio-skill` precedent.

**Provenance shipped**
- `research/perplexity-2026-05-21.md` — Perplexity deep-dive.
- `research/gemini-3-5-flash-2026-05-21.md` — Gemini 3.5 Flash deep-dive (with verification notes flagging fabricated endpoint names).
- `research/claude-opus-4-7-2026-05-21.md` — Claude Opus 4.7 web research (the most authoritative; cross-checked against OpenAPI).
- `research/openapi-cloud.yaml` — pinned copy of the official Comfy Cloud OpenAPI 3.0 spec.

**In-progress reference files** (stubs to be filled from research)
- `references/api-endpoints.md`
- `references/workflow-format.md`
- `references/websocket-protocol.md`
- `references/pipeline-patterns.md`
- `references/pre-installed-nodes.md`
- `references/partner-nodes.md`
- `references/errors-and-limits.md`
- `references/operational-rules.md`
- `references/pipeline-phases.md`
- `references/asset-management.md`
- `references/cost-and-concurrency.md`
- `references/mcp-tool-schemas.md`

**Not yet shipped**
- `templates/*.json` — API-format workflow templates (txt2img-flux, sdxl, img2img, inpaint, controlnet, lora-stack, refiner, upscale-ultimate, animatediff, wan22-i2v, ltx-video).
- `scripts/validate_workflow.py`, `scripts/parameter_sweep.py`, etc.
- `evals/*.json` — three required evaluation scenarios.
