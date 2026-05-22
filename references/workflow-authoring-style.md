# Workflow Authoring Style — Readability, Groups, Docs, User Manual

**Status: binding for every Comfy Cloud workflow produced by this skill.** These rules apply from v1, not "after optimization in v2". If there's a tradeoff between maximum optimization and maximum understandability for v1, choose understandability — optimize later when the baseline is validated.

## Reader profile

The intended reader is **technically experienced** (comfortable with node-based tools like Weavy, automation platforms, generative AI products) but **new to ComfyUI's specific idioms**. Explain ComfyUI-specific concepts (latents vs. images, conditioning flow, sampler/scheduler distinction, link tuples) — but don't dumb down beyond that.

## The 10 rules

### 1. Simplicity over cleverness

When two solutions are technically equivalent, pick the one a new user can read, debug, and modify fastest. "Smart" tricks (latent re-use shortcuts, conditional flow via SwitchAny, deep helper chains) belong in v2 after the baseline is validated.

### 2. Group nodes into named, color-coded phases on canvas

Every workflow has visible phase boundaries. Standard phase set (use only the ones the workflow actually needs):

- Inputs / Assets
- Masking / Segmentation
- Background Generation / Inpaint
- Compositing
- Relighting
- Upscaling / Finishing
- Save / Export
- Debug / Metrics / Validation

Each group on canvas: rectangle with a clear label and a distinct color. The reader should see the architecture at a glance, without reading JSON.

### 3. Pedagogical names

Group names and node titles describe **purpose**, not just technique. Examples of good vs. tech-only naming:

| Tech-only (avoid) | Pedagogical (prefer) |
|---|---|
| "VAEEncode_1" | "Encode product image to latent" |
| "KSampler" | "Generate background" |
| "ImageCompositeMasked" | "Blend product into scene" |
| "ICLightApplyMaskGrey" | "Relight product to match scene" |
| "UltimateSDUpscale" | "Upscale for final delivery" |
| "LoadImage" | "Load product master" |

Use the node's `title` field in the workflow JSON to override the default class name on canvas.

### 4. First node in every workflow = README Note node

The very first node on canvas (top-left, before any active nodes) is a `Note` (or equivalent) that functions as the workflow's README. Required content:

- **Purpose** — one-line description of what the workflow produces.
- **Output** — file type, default resolution, naming convention.
- **Required inputs** — exactly what files/parameters the user must supply.
- **Easily-swappable parts** — which nodes/values are designed to be changed.
- **Most-important parameters to adjust** — top 3–5, with effect descriptions.
- **Cost drivers / Partner Nodes** — every Partner Node used + its cost-per-call.
- **Known limitations** — what this workflow cannot do, what fails it.
- **Step-by-step "how to use this workflow"** — numbered, ordered list:
  1. Import product image
  2. Import or generate mask
  3. Set environment prompt
  4. Adjust key parameters
  5. Run the workflow
  6. Review output
  7. Iterate or export

Reader should be able to use the workflow purely from the Note node, without external docs.

### 5. Sibling `.md` file next to every workflow JSON

Same base name, `.md` extension. The Note node is the canvas summary; the `.md` is the full manual.

Required sections:

- **Purpose** (one paragraph).
- **Step-by-step explanation of every phase** — what happens in Inputs → Masking → Background Gen → Compositing → Relight → Upscale → Save.
- **Nodes used and why** — table or list mapping each non-trivial node to its role in the pipeline.
- **Parameters the user will likely tune first** — ordered by impact, with effect descriptions (see Rule 7).
- **How each top parameter affects the output** — in plain English, with directional hints ("higher = X, lower = Y").
- **Common failure modes** — symptom + likely cause + fix.
- **Suggested v2 extensions** — what's intentionally simple in v1 and how to extend it later.
- **Full user manual** — the same step-by-step from Rule 4, but with more detail per step. Add advisory copy like:
  - "Note that…"
  - "You can…"
  - "If the result is too sharp/soft, adjust…"
  - "If the product must stay pixel-identical, don't change this part…"

Tone: helpful, direct, no jargon-stacking. Written for the reader profile above.

### 6. Short Note nodes near important individual nodes

Especially in the early phases (Inputs, Masking, first sampler), attach a small Note node next to each non-trivial node. Each inline note covers:

- **What the node does** (one sentence).
- **Why it's in *this* pipeline** (the specific reason, not generic).
- **Top 1–3 parameters** the user might want to adjust.
- **How parameter changes affect output** (effect-based, see Rule 7).

Don't note every node — only the ones a new user would benefit from understanding. Trivial connectors (Reroute, type-cast utilities) don't need notes.

### 7. Document parameters by effect, not internal name

Bad: "denoise: float, range 0.0–1.0".
Good: "denoise (0.0–1.0): higher values change more of the original image, lower values preserve more. For background-swap with product preservation, keep below 0.4 in masked region."

Other examples of effect-based parameter docs:

- "guidance scale: higher = prompt followed more strictly, but result may feel less natural"
- "mask blur (pixels): lower = sharper edge between regions, higher = softer transition"
- "steps: more steps = better quality + more time/cost; diminishing returns past 30 for most models"
- "seed: lock to reproduce identical output; change to get a different variation"

Avoid restating the node's internal parameter name without explaining what it does in practice.

### 8. Clean canvas, left-to-right flow

- Inputs and asset loaders on the left.
- Outputs (SaveImage, VHS_VideoCombine, etc.) on the right.
- Phase groups arranged in a clear flow from inputs to outputs.
- Debug, metrics, and validation nodes in their own group (usually bottom-right or in a separate row).
- Minimize cable crossings — route around groups, not through them.
- Use Reroute nodes only when they materially improve readability, not as cosmetic decoration.

The workflow must be understandable from the canvas alone. If you can't follow the data flow without reading JSON, restructure.

### 9. Reader assumption — technical but new to ComfyUI

When explaining ComfyUI-specific idioms in Note nodes or `.md`:

- Explain **once**, the first time the concept appears in the workflow.
- Use the user's frame of reference (other node-based tools, generative AI products).
- Don't re-explain on every reference — link or back-reference.

Examples of idioms worth explaining once:
- "latent" vs. "image" (and why we encode/decode at boundaries).
- "conditioning" (text-encoder output, threaded through samplers).
- Link tuples in API-format JSON (`[node_id, output_index]`).
- Sampler vs. scheduler distinction.
- Why some nodes take `(model, clip)` and pass `(model, clip)` (the LoRA / patch chaining pattern).

### 10. User-friendly inline guidance

Use direct, advisory phrasing in Note nodes:

- ✅ "Note that the seed lock here is intentional — change it to explore variations."
- ✅ "You can replace this LoadImage with an asset reference once the workflow is wired into the proxy."
- ✅ "If the product edges look unnatural, try increasing the mask blur in the Masking group."
- ✅ "If the product must stay pixel-identical, don't change the composite mask threshold below."

Avoid:

- ❌ Pure technical jargon without context.
- ❌ Conditional/passive constructions ("It may be possible to consider adjusting…").
- ❌ Repeating ComfyUI documentation verbatim — paraphrase with the user's task in mind.

## Required deliverable per workflow — hybrid format

Each workflow ships as **three files** that live together:

1. **`<name>.canvas.json`** — Canvas-format ("workflow") JSON. The **source of truth for humans**. Contains:
   - All phase groups (named, color-coded)
   - README Note node at top-left
   - Inline Note nodes near key active nodes
   - Pedagogical node titles via the `title` field
   - Positions (`pos`) and sizes (`size`) for a clean left-to-right layout
   - All active nodes wired through canvas `links` array

   Loads directly in the Cloud editor (`File → Load`) showing the full visual structure. This is what you edit and iterate on.

2. **`<name>.api.json`** — API-format JSON. The **submit payload**. Generated from the canvas JSON by stripping all visual-only fields (Note nodes, groups, positions, link arrays) and re-keying as `{ node_id: { class_type, inputs } }`. This is what `/api/prompt` consumes.

   **Never hand-author this file.** Generate it from the canvas JSON via `scripts/canvas_to_api.py` (or equivalent in the proxy). Keeping the API JSON in sync with the canvas JSON is a build-time concern, not a manual one.

3. **`<name>.md`** — sibling user manual. All sections from Rule 5. Written for someone who opens the canvas file in the editor and wants the full context.

All three must be committed/saved together. A workflow without its sibling `.md` is incomplete. A workflow's `.api.json` must always be in sync with its `.canvas.json` — if either is missing or stale, the workflow is broken.

## Why canvas + API hybrid

API-format JSON cannot carry `Note` nodes, groups, positions, or color codes (verified: `Note`, `MarkdownNote`, `PrimitiveNode` are not class_types in `/api/object_info`). Those are frontend-only canvas features. So the readability rules in this style guide (Note-node README, inline notes, color-coded phase groups, left-to-right flow) **require canvas-format storage**.

But `/api/prompt` only accepts API-format. So:

- **Humans read and edit the canvas file** — it shows the pipeline structure, groups, and inline docs.
- **The proxy submits the API file** — generated, stripped, never hand-authored.

The conversion is mechanical (drop visual fields, re-key by node ID). Keep both in lockstep via a build script. When you change the canvas file, regenerate the API file. When the user opens a saved workflow, they open the canvas file; the API file is a build artifact.

## Connection to operational rules

This style guide does not replace the [operational rules](./operational-rules.md):

- Rule 4 (manifest per submission) is still binding. The manifest is *machine-readable provenance for a specific run*; the `.md` is *human-readable instruction for the workflow*. Both are required.
- Rule 6 (Partner Node opt-in) — the Note node and `.md` must surface Partner Node usage and per-call cost.
- Rule 8 (cost pre-flight) — the `.md` should document the estimated cost per run, broken out per node.
- Rule 3 (seed discipline) — the Note node should call out that the seed is locked and how to change it intentionally.

## When to deviate

There are no rule exceptions for **v1 workflows**. Every v1 produced by this skill follows the 10 rules.

For experimental scratch workflows produced *during exploration* (not delivered to a user), some rules can be relaxed — but the moment a workflow is delivered or referenced as a working example, it must conform fully.

## Maintaining this rule set

If a delivered workflow surfaces a missing convention (e.g., a new phase type, a new common parameter pattern), update this file to include it. New examples can be added inline; new phases can be added to Rule 2; new parameter effect-descriptions can be added to Rule 7.

This is a living style guide, not a frozen spec.
