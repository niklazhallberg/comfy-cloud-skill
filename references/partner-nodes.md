# Partner Nodes

Partner Nodes are workflow nodes that internally call **external third-party APIs** (not Comfy Cloud's own GPU). They appear in `/api/object_info` like any other node but have distinct behavior:

- They bill separately from base GPU time (often dramatically more per call)
- They require `extra_data.api_key_comfy_org` in the submission payload
- Their outputs come from external services with their own latency and reliability characteristics

## Known Partner-Node providers (71 packages in upstream)

The full catalog from upstream `comfy_api_nodes/` — verify each is exposed on Cloud by checking `/api/object_info` at runtime.

**Video generation:**
- Kling (Kuaishou)
- Luma (Dream Machine)
- Runway
- Sora 2 / Sora 2 Pro (OpenAI — note: some Sora nodes carry a deprecation notice in upstream code)
- Vidu (ShengShu)
- Veo / Veo2 (Google DeepMind)
- Pixverse
- Wavespeed
- LTXv (Lightricks — also available as open model)
- WAN / Wan 2.x (Alibaba — also available as open model)
- Minimax (Hailuo)
- ByteDance video — Seedance (image-to-video), ByteDance 2 (newer text-to-video, first-last-frame, reference variants)

**Image generation:**
- Bria
- Recraft
- Stability (SDXL, Stable Diffusion 3)
- Ideogram
- Magnific (upscaling)
- Topaz (upscaling)
- HitPaw
- Reve
- Nano Banana (Google's Imagen 3)
- Flux Pro (Black Forest Labs hosted; distinct from open Flux Schnell/Dev)
- ByteDance image — Seedream v1 & v2

**3D:**
- Rodin
- Tripo
- Meshy
- Hunyuan 3D (Tencent)
- Sonilo

**LLM / VLM:**
- Grok (xAI)
- Claude (Anthropic)
- Gemini (Google)
- OpenAI (GPT family)
- OpenRouter (multi-provider routing)
- ByteDance (Doubao LLM)

**Audio / voice:**
- ElevenLabs (TTS, voice cloning)

**ByteDance asset creation:**
- `ByteDanceCreateImageAsset`, `ByteDanceCreateVideoAsset` — for creating ByteDance-side asset references for downstream nodes

Source: `comfy_api_nodes/nodes_*.py` (71 files) in upstream ComfyUI. Cloud installs a subset — confirm by checking `/api/object_info` for the relevant `class_type`s before exposing.

**For runtime discovery:** filter `/api/object_info` for nodes whose `python_module` starts with `comfy_api_nodes.` or whose `category` indicates partner status, then maintain that as the curated list.

## Required submission shape

A workflow containing any Partner Node must include `extra_data.api_key_comfy_org`:

```json
{
  "prompt": { /* workflow with Partner Node */ },
  "extra_data": {
    "api_key_comfy_org": "<your-cloud-api-key>"
  }
}
```

This is the **same** API key used in the `X-API-Key` header. The browser sets it automatically; API clients must set it manually.

## Skill policy

Per [Rule 6 in operational rules](./operational-rules.md):

1. **Detect at validation time.** Maintain a `class_type → partner_node` map. On workflow validation, scan for any Partner Node `class_type`.
2. **Surface estimated cost.** Partner Nodes often charge per output (image, second of video, etc.) at rates 10–100× GPU-second cost. Use the provider's published rate sheet to estimate, then surface to the user.
3. **Require explicit opt-in.** Default to refusing submission. The user must pass `--partner-ok` (or equivalent skill signal) to proceed.
4. **Log Partner-Node usage in the manifest.** Mark the manifest with `partner_nodes_used: [<class_type>, ...]` so cost retrospectives can identify high-spend runs.

## Why this is high-risk

A single Kling 5-second video can cost ~$0.40. A single Flux Pro 1024² image can cost ~$0.05. A typical txt2img on the base GPU is ~$0.001. An agent that submits 20 Kling videos "to explore variations" can burn through credits in seconds.

The skill should treat Partner Nodes as a different cost class entirely, never as drop-in replacements for base-GPU equivalents.

## Cross-references

- Workflow format and `extra_data`: [`workflow-format.md`](./workflow-format.md)
- Cost math: [`cost-and-concurrency.md`](./cost-and-concurrency.md)
- Operational Rule 6: [`operational-rules.md`](./operational-rules.md)
