# Contributing

This skill is part of the Valtech RADON internal AI tooling, published openly. Contributions are welcome, especially in these areas:

- New `references/*.md` entries synthesized from real ComfyUI / Comfy Cloud experience
- Additional `templates/*.json` API-format workflows, validated against a live `/api/object_info`
- `scripts/` helpers for validation, sweeps, manifests, and asset management
- Evals in `evals/` (we need at least three; current count: 0)

## Skill conventions

Inherited from the [`valtech-radon-lens-studio-skill`](https://github.com/niklazhallberg/valtech-radon-lens-studio-skill) precedent and Anthropic's official skill-authoring best practices:

- `SKILL.md` body ≤ 500 lines. If a section is growing, split into `references/`.
- `description` field ≤ 1024 chars. `description + when_to_use` ≤ 1536 chars (truncation point in the skill listing).
- File references in SKILL.md are **one level deep** — link to `references/foo.md`, never `references/foo/bar.md`.
- Forward slashes only in paths.
- Reference files are a **parts-bin**, not a menu. Compose across multiple files when a brief calls for it.
- Third-person, gerund-or-noun-phrase voice in frontmatter ("Designs", "Validates", "Runs", not "I" or "You").

## Workflow templates

Every `templates/*.json` must:

1. Be in **API format** (flat dict, string node IDs, `class_type` + `inputs` per node).
2. Validate against a recent `/api/object_info` snapshot.
3. Include a header comment block explaining the intended use case and which parameters are designed to be swapped.
4. Use placeholder values that are valid (not `null` or `__PLACEHOLDER__`) so the template is runnable as-is.

## Research preservation

The `research/` directory is **append-only**. Don't edit the original AI deep-dives — preserve them verbatim with their date stamps. Add new research as new files, dated. Synthesis happens in `references/`, never by mutating `research/`.

## Pull requests

- One concept per PR.
- Reference an issue or describe the gap being filled.
- Run any local validators in `scripts/` before submitting.

## Sources of truth

Two OpenAPI specs are pinned in `research/`:

- [`research/openapi-cloud.yaml`](research/openapi-cloud.yaml) — Cloud's documented public surface (from docs.comfy.org).
- [`research/openapi-oss-upstream.yaml`](research/openapi-oss-upstream.yaml) — the upstream ComfyUI repo's full OpenAPI (Comfy-Org/ComfyUI). A superset including OSS-only and Cloud-only endpoints.

When the two conflict or when researchers report findings, the precedence is:

1. **Docs `openapi-cloud.yaml`** for what Comfy publicly promises on Cloud
2. **Upstream `openapi-oss-upstream.yaml`** for the implemented superset (helpful for understanding behavior, but not all endpoints are exposed on Cloud)
3. **Community sources / AI research** for context, but flag conflicts explicitly in [`references/conflicts-and-limitations.md`](references/conflicts-and-limitations.md)

When something appears only in upstream, the skill probes before relying on it. Reference files should mark such items "OSS upstream — Cloud-status unverified" until confirmed.
