# valtech-radon-comfy-cloud-skill

A Claude Code skill for designing and running ComfyUI pipelines on [Comfy Cloud](https://cloud.comfy.org) from natural-language briefs.

Pairs with the [`comfy-cloud-proxy`](https://github.com/niklazhallberg/comfy-cloud-proxy) MCP server: the proxy is the execution layer; this skill is the design and orchestration brain on top.

## What this is

When Claude Code is given this skill, it gains the knowledge to:

- Translate a creative brief into a working ComfyUI graph
- Pick the right pre-installed nodes and models on Comfy Cloud
- Validate every node and combo value against the live `/api/object_info`
- Pre-flight cost and concurrency before submitting
- Submit, monitor progress, retrieve outputs, and write reproducible manifests
- Iterate efficiently using cache-aware variation patterns

It covers txt2img, img2img, inpainting, ControlNet, LoRA stacks, SDXL refiner chains, multi-pass upscaling, AnimateDiff, Wan 2.2 video, LTX-Video, Flux, Qwen, and more.

## Install

```bash
git clone https://github.com/niklazhallberg/valtech-radon-comfy-cloud-skill.git ~/.claude/skills/comfy-cloud-pipeline-designer
```

Then in Claude Code:

```
/skill enable comfy-cloud-pipeline-designer
```

Verify with:

```
What does the comfy-cloud-pipeline-designer skill do?
```

You also need the `comfy-cloud-proxy` MCP server connected — see https://github.com/niklazhallberg/comfy-cloud-proxy.

## Repository layout

```
valtech-radon-comfy-cloud-skill/
├── SKILL.md              # Skill entry — frontmatter, voice mandate, operational rules, references index
├── README.md             # This file
├── CHANGELOG.md
├── CONTRIBUTING.md
├── references/           # Synthesized working knowledge (loaded by Claude on demand)
│   ├── api-endpoints.md
│   ├── workflow-format.md
│   ├── websocket-protocol.md
│   ├── pipeline-patterns.md
│   ├── pre-installed-nodes.md
│   ├── partner-nodes.md
│   ├── errors-and-limits.md
│   ├── operational-rules.md
│   ├── pipeline-phases.md
│   ├── asset-management.md
│   ├── cost-and-concurrency.md
│   └── mcp-tool-schemas.md
├── research/             # Raw deep-dives that informed the references (source provenance)
│   ├── perplexity-2026-05-21.md
│   ├── gemini-3-5-flash-2026-05-21.md
│   ├── claude-opus-4-7-2026-05-21.md
│   └── openapi-cloud.yaml
├── scripts/              # Helper scripts (validators, sweep launchers, manifest writers)
└── docs/                 # Optional landing pages
```

## Status

**Skill version: 0.1.0** — Initial public structure. SKILL.md is the locked entry point. Reference files are stubs being progressively populated from the research material; see [CHANGELOG.md](./CHANGELOG.md) for what's stabilized.

This skill is part of the Valtech RADON internal AI tooling, published openly so the wider ComfyUI + Claude Code community can build on it.

## Related

- [`comfy-cloud-proxy`](https://github.com/niklazhallberg/comfy-cloud-proxy) — the MCP server this skill operates through
- [Comfy Cloud](https://cloud.comfy.org) — the hosted Comfy execution platform
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — upstream Comfy project
- [Claude Code](https://claude.com/claude-code) — the agent runtime this skill loads into
