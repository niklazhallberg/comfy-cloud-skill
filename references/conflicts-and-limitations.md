# Conflicts & Limitations

Comfy Cloud is **explicitly experimental** ("subject to change without notice" — own words). Several official sources currently disagree with each other. The skill should treat these as live questions, not settled facts.

## Official source conflicts

### Concurrency: "1 active job" vs "3 / 5 parallel"

- **Cloud FAQ**: "Each workflow can run up to 60 minutes with one active job at a time."
- **Cloud API Overview**: "API users can run multiple jobs in parallel — three on Creator, five on Pro."

**How the skill handles it:** follow the more specific Cloud API Overview (3 / 5 parallel via API). The FAQ likely refers to UI behavior. Track in-flight `prompt_id`s and cap at `tier_limit - 1` per Rule 7. If the cap is wrong, the worst case is graceful queueing.

Authoritative source: `research/openapi-cloud.yaml` describes per-user fair scheduling; the API allows submissions up to the documented tier cap.

### BYO models: "HF + CivitAI + direct upload" vs "CivitAI LoRAs only"

- **Cloud marketing page (body text)**: "Upload custom LoRAs or finetuned foundational models from CivitAI and Hugging Face."
- **Same page's FAQ section**: Creator/Pro users can bring in *fine-tuned LoRAs from CivitAI*; Hugging Face import and direct file upload for larger models are on the **roadmap**.

**How the skill handles it:** treat **CivitAI LoRA import** as the highest-confidence BYO path. For HF imports and direct model upload, treat the capability as runtime-verifiable, not guaranteed. The OpenAPI does include `POST /api/assets/download` for both HF and Civitai URLs, so the wire path is shipped — but production support for non-LoRA / non-Civitai imports may still be partial.

### `/api/history_v2` vs `/api/jobs`

- **Status**: `/api/history_v2*` is officially deprecated in favor of `/api/jobs/{id}` and the `/api/jobs` family.
- **`prompt_id == job_id`** — same identifier across both endpoint families.

**How the skill handles it:** prefer `/api/jobs/*` everywhere. Keep awareness of `/api/history_v2` only for backwards-compat with older proxy code.

## Asset upload ≠ Model install

A common misconception: that `POST /api/assets` uploading a `.safetensors` makes the model immediately discoverable under `/api/experiment/models/{folder}`.

**Reality:**

- `POST /api/assets` puts a file in Cloud's content-addressed asset storage.
- `/api/experiment/models/{folder}` returns the **installed model catalog** — files registered as runnable models for the relevant category (checkpoint, lora, vae, upscale_models, etc.).
- These are **two different layers.** Uploading an asset does not automatically install it as a model.

**How the skill handles it:** for stable model discovery (which checkpoints / LoRAs / VAEs / upscalers actually exist), always read from `/api/experiment/models/{folder}`. For raw blob storage (e.g. input images, mask layers, reference assets), use the asset endpoints. Document the distinction in any tool that touches both.

The path for BYO LoRAs via Civitai (`POST /api/assets/download`) does both: ingests to storage *and* installs as a runnable model. But that's the partner-flow behavior, not a guarantee that arbitrary asset uploads gain runnable-model status.

## Outputs lack workflow metadata

- The official Comfy Cloud MCP server docs note: *"Images created via the MCP server don't include workflow JSON in their metadata."*
- This is in contrast to standard ComfyUI behavior where SaveImage embeds the workflow in PNG `EXTRA_PNGINFO`, enabling drag-back-into-canvas.

**How the skill handles it:** **always populate `extra_pnginfo` on `SaveImage` nodes** in templates this skill emits. Then the output PNGs *do* carry the workflow, restoring drag-into-canvas reproducibility. The proxy-side manifest (Rule 4) is the primary reproducibility store; embedded PNG metadata is a defense-in-depth secondary.

## What's NOT publicly documented

No official numerical rate limits per second / minute on the API (only tier concurrency).

No exhaustive public list of:
- Currently installed checkpoints / LoRAs / VAEs / upscalers in Cloud
- Custom node packs in Cloud (only a curated "popular ones" page at https://comfy.org/cloud/supported-nodes)
- NSFW / content-policy moderation behavior

**How the skill handles it:** runtime discovery via `/api/object_info`, `/api/features`, and `/api/experiment/models/{folder}` is the only reliable source. The skill should refuse to make claims about specific availability without checking — never hardcode "this LoRA exists on Cloud" assumptions.

For content policy: the proxy itself is the policy-enforcement layer ([Rule 6 + Rule 8](./operational-rules.md)). Don't rely on Cloud to filter.

## Custom-node installation

- **Officially**: Cloud ships a curated list of pre-installed custom nodes (https://comfy.org/cloud/supported-nodes).
- **What you cannot do**: Git-clone or ComfyUI-Manager-install arbitrary custom node packs on Cloud.
- **What you can do**: request additions via the same supported-nodes page.

**Workaround for missing custom nodes:** subgraph splitting — run subgraph A on Cloud, download intermediate via `/api/view`, run the custom-node step locally, re-upload via `/api/upload/image`, run subgraph B on Cloud. Documented in [`pipeline-patterns.md`](./pipeline-patterns.md) where applicable.

## Docs OpenAPI spec is a subset of upstream

The Comfy Cloud docs publish `openapi-cloud.yaml` (3732 lines). The upstream ComfyUI repo publishes `openapi.yaml` (8725 lines) — a **superset** that includes both OSS-only and Cloud-only endpoints.

Both files are pinned in `research/`:
- `research/openapi-cloud.yaml` — Cloud's documented surface
- `research/openapi-oss-upstream.yaml` — upstream truth

**Endpoints in upstream that aren't in the docs spec** (may or may not be exposed on Cloud — verify by probing with your API key):

- `/api/secrets/{id}` and related — user-stored HF/Civitai tokens
- `/api/tags` — asset tag management
- `/api/node_replacements` — node-class aliases for backwards compat
- `/api/vhs/queryvideo`, `/api/vhs/viewvideo`, `/api/vhs/viewaudio` — VHS-specific media endpoints
- `/api/i18n` — frontend localization
- `/api/feedback` — user feedback submission
- `/api/files/mask-layers` — mask layer helpers
- Various `/api/experiment/*` namespaces beyond models

**Internal routes** (frontend-only, never expose in skill features):
- `/internal/logs`, `/internal/files/{type}`, `/internal/folder_paths`, `/internal/logs/subscribe`

**How the skill handles it:** treat docs `openapi-cloud.yaml` as the **contract** (what Comfy promises). Treat upstream `openapi-oss-upstream.yaml` as the **superset** (what the codebase implements). When something appears only in upstream, the skill should probe before relying on it, and never expose an unverified endpoint as a stable capability.

## Things the skill should treat as runtime-verifiable

Per the above, the skill should **not** make these guarantees in copy:

- "AnimateDiff is installed on Cloud" — verify via `object_info` first
- "SVD is available" — verify
- "Wan 2.2 templates use 4-step sampling" — verify against the current `/api/workflow_templates` and `/api/object_info`
- "ControlNet preprocessor X works" — verify the specific node exists
- "Model file Y is in the LoRA folder" — verify via `/api/experiment/models/loras`

The right pattern is to introspect before promising, then offer concrete options based on what's actually there.

## Cross-references

- Endpoint inventory + deprecation notes: [`api-endpoints.md`](./api-endpoints.md)
- Tier limits + error codes: [`errors-and-limits.md`](./errors-and-limits.md)
- Asset vs model handling: [`asset-management.md`](./asset-management.md)
- Operational rules that depend on these limits: [`operational-rules.md`](./operational-rules.md)
