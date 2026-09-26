# research/

Raw source material the `references/` files were synthesized from. Kept for provenance, so any claim in the skill can be traced back to where it came from.

| File | What it is |
|---|---|
| `openapi-cloud.yaml` | Comfy Cloud's public OpenAPI spec (docs.comfy.org). **Highest precedence** for what Cloud promises |
| `openapi-oss-upstream.yaml` | Upstream ComfyUI OpenAPI spec — a superset incl. OSS-only endpoints. Used to understand behaviour; Cloud status must be verified |
| `*-2026-05-21.md` | Four independent AI deep-research reports (ChatGPT, Claude, Gemini, Perplexity) on the same brief, run in parallel to cross-check each other |

**Rules** (see [CONTRIBUTING.md](../CONTRIBUTING.md)):

- **Append-only.** Files are never edited after they're added; new research goes in new, dated files.
- **Not loaded by the skill.** Claude reads `references/`, never `research/`.
- Where sources disagree, the conflict and its resolution are recorded in [`references/conflicts-and-limitations.md`](../references/conflicts-and-limitations.md).
