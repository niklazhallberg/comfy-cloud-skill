# Pipeline Phases

Detail for each phase from `SKILL.md`'s six-phase pipeline.

## Phase 0 — Brief → Graph Spec

**Goal:** Translate the user's natural-language ask into a concrete spec the rest of the pipeline can instantiate.

**Inputs:** User brief, any reference images, target output type.

**Decisions to lock:**

1. **Stack** — SD1.5 / SDXL / Flux Schnell / Flux Dev / Qwen / Wan / LTX / AnimateDiff. Pick from [`pipeline-patterns.md`](./pipeline-patterns.md).
2. **Conditioning shape** — single prompt, dual prompt (pos+neg), ControlNet guide, IP-Adapter reference, regional prompts.
3. **Post-chain** — refiner pass? upscale? face detail? frame interp (video)?
4. **Output type** — image / video / audio, resolution, batch size.

**Definition of Done:** Spec concrete enough to instantiate from a template without further user input on basics.

**Watch points:**

- Did the user implicitly require something not in Cloud? (Custom node not in the supported list, model not yet downloaded). Surface before Phase 1.
- Did the user constrain seed, dimensions, or model? Honor over defaults.

## Phase 1 — Template Selection + Parameter Mapping

**Goal:** Produce API-format JSON ready to validate.

**Steps:**

1. Pick template from `templates/` matching the Phase 0 spec.
2. Override parameters from the brief (prompt text, dimensions, seed, model file, LoRA selections).
3. For multi-step chains (refiner, upscale), wire latent passthroughs.
4. Inject `extra_data.api_key_comfy_org` if any Partner Node is in the graph.

**DoD:** API-format JSON exists with all node IDs and link tuples resolved.

## Phase 1.5 — Capability Validation

**Goal:** Catch impossible workflows before they hit the wire.

**Checks:**

- Every `class_type` exists in cached `/api/object_info`.
- Every required input is present and typed correctly.
- Every combo value is in the legal enum for the current Cloud instance.
- Estimated graph fits within concurrency + runtime caps.

**DoD:** Validator returns clean. If not, fix or escalate.

## Phase 2 — Pre-flight

**Goal:** Don't surprise the user with costs or stuck submissions.

**Checks:**

- Cost estimate vs. budget. Surface the math.
- Partner-Node detection → require opt-in if any.
- Concurrency: in-flight count < `tier_limit - 1`?

**DoD:** User has the cost/risk info and either gave a green light or constrained the request.

## Phase 2.5 — Asset Uploads (optional)

**Goal:** For img2img / inpaint / ControlNet, get input assets onto Cloud before submission.

**Steps:**

1. Hash any local input file (Blake3).
2. `HEAD /api/assets/hash/{hash}` — skip upload if already on Cloud.
3. Otherwise `POST /api/upload/image` (or `POST /api/assets` for model files).
4. Replace local file references in the workflow JSON with Cloud `name`s.

**DoD:** All non-Cloud assets are now Cloud-resident, references in the workflow are valid.

## Phase 3 — Submit + Monitor

**Goal:** Get the work done, with live feedback.

**Steps:**

1. `POST /api/prompt` with the validated workflow.
2. On 200, capture `prompt_id`. Check `node_errors` — if non-empty, abort.
3. Open WebSocket to `wss://cloud.comfy.org/ws?clientId=<uuid>&token=<key>`.
4. Filter incoming messages by `prompt_id`.
5. Track `execution_start` → `executing` (per node) → `executed` (per output) → `execution_success` / `execution_error` / `execution_interrupted`.
6. Surface `progress` events as user-visible status.
7. On WS drop: fall back to polling `GET /api/job/{prompt_id}/status` every 1–3s.

**DoD:** Terminal event received (`execution_success` or one of the failure modes).

## Phase 4 — Output Retrieval + Manifest

**Goal:** User gets the file. Skill writes the audit trail.

**Steps:**

1. `GET /api/jobs/{prompt_id}` for canonical outputs.
2. For each output: `GET /api/view?filename=...&type=output`. Follow 302. Drop `X-API-Key` before fetching the signed URL.
3. Save to `outputs/<prompt_id>/<filename>`.
4. Write manifest: `outputs/manifests/{prompt_id}.json` with workflow, params, seed, object_info_hash, system_stats, timestamp, actual GPU time from `execution_meta`.

**DoD:** File on disk, manifest saved, user has the path.

## Phase 5 — Iterate

**Goal:** Efficiently produce variants without re-paying for the parts that didn't change.

**Patterns:**

- **Seed sweep:** identical workflow + new seed each submission. Submit `tier_limit - 1` at a time.
- **Parameter tweak:** change one downstream parameter (steps, cfg, sampler), keep everything upstream identical. Triggers `execution_cached` on the static portion → free time.
- **A/B variant:** two parallel submissions with one structural difference. Document the diff in both manifests.

**Anti-pattern:**

- Restructuring the upstream (different checkpoint, different prompts) on every "minor tweak" — kills the cache, pays full price every time.

**DoD per iteration:** User signs off OR the next iteration is queued.

## Cross-references

- The brief → graph mapping vocabulary: [`pipeline-patterns.md`](./pipeline-patterns.md)
- Validator logic: [`workflow-format.md`](./workflow-format.md)
- Cost / concurrency: [`cost-and-concurrency.md`](./cost-and-concurrency.md)
- Lifecycle protocol: [`websocket-protocol.md`](./websocket-protocol.md)
- Operational rules: [`operational-rules.md`](./operational-rules.md)
