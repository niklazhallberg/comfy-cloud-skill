# Changelog

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
