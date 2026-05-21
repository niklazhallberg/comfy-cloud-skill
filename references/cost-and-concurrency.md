# Cost & Concurrency

## Credit math

Comfy Cloud bills per-second of **active GPU time**. Idle (UI editing, queueing, planning) is free.

| Tier | Credits/mo | Effective USD/credit | Approx GPU-seconds/credit |
|---|---|---|---|
| Creator | 7,400 @ $35 | $0.0047 | 1 second of standard GPU ≈ 1 credit |
| Pro | 21,100 @ $100 | $0.0047 | same |

(Per-second rate is the same; tiers differ in monthly allocation + concurrency.)

## Per-pipeline rough estimates (base GPU)

These are ballpark — verify with actuals from `execution_meta` in `/api/jobs/{id}` for your specific Cloud configuration.

| Pipeline | Typical GPU-seconds |
|---|---|
| SD1.5 txt2img, 512², 20 steps | 5–10s |
| SDXL txt2img, 1024², 25 steps | 15–25s |
| SDXL base + refiner, 1024² | 25–40s |
| Flux Schnell, 1024², 4 steps | 8–15s |
| Flux Dev, 1024², 20 steps | 25–45s |
| Qwen-Image, 1024² | 20–40s |
| Img2img (same stack as base) | 0.5–0.8× the txt2img time (denoise-dependent) |
| ControlNet pass | +30–50% over base |
| UltimateSDUpscale 4× | 60–120s (the upscale itself dominates) |
| AnimateDiff, 16 frames | 60–120s |
| Wan 2.2 i2v, 4-step, 720p, 4s | 90–180s |
| LTX-Video, ~5s clip | 60–120s |

## Partner Node costs (very different cost class)

Partner Nodes don't burn GPU-seconds — they bill flat per-call or per-output. **See [`partner-nodes.md`](./partner-nodes.md)** for the catalog. A few illustrative figures (provider-published, subject to change):

- Kling video, 5s: ~$0.40
- Flux Pro image, 1024²: ~$0.05
- Ideogram image: ~$0.08
- Nano Banana (Imagen 3): ~$0.04

A Partner Node burst can outpace a month's base-GPU spend in minutes. Hence Rule 6 ([operational-rules.md](./operational-rules.md)).

## Concurrency budgeting

Hard limits:

- Creator: **3** parallel jobs
- Pro: **5** parallel jobs
- Queue depth: 100 pending

Skill policy (Rule 7): default to **`tier_limit - 1`** for skill-driven submissions so the user can still use the UI in parallel.

For parameter sweeps:

1. Determine `effective_cap = tier_limit - 1`
2. Submit up to `effective_cap` at once
3. Wait for any one to finish before submitting next
4. Track in-flight via `prompt_id` set; remove on `execution_success` / `execution_error` / `execution_interrupted`

## Cost-aware pipeline design

The Cloud caches outputs for unchanged nodes (`execution_cached` event). Design templates so:

- **Upstream nodes (checkpoint, conditioning, base sampler) stay identical between runs.**
- **Variation happens downstream** (sampler params, post-chain, seed only when the goal is variation).

When the upstream is stable, repeated submissions trigger `execution_cached` for the upstream nodes — the skipped time is **free**. Hours of agent iteration become minutes of paid GPU.

## Pre-flight check (Rule 8)

```
# Pseudo-code
total_seconds = sum(estimate_per_node(class_type, params) for node in workflow)
estimated_cost = total_seconds * cost_per_second
budget = env("COMFY_BUDGET_SECONDS", default=180)

if total_seconds > budget:
    surface_breakdown(workflow, total_seconds, budget)
    require_user_confirmation()

if any_partner_node(workflow):
    estimated_partner_cost = sum(partner_cost(class_type) for node in workflow if is_partner(node))
    surface_partner_cost(estimated_partner_cost)
    require_explicit_opt_in()
```

After execution, log actuals from `execution_meta` for budget calibration.

## When the user is OK with the cost

- For a one-off "make this hero image": auto-approve up to ~60 GPU-seconds.
- For a documented sweep ("generate 20 variants"): require an explicit budget approval covering the full sweep.
- For Partner Nodes: always require explicit per-call or per-batch approval.

The skill should make cost **visible**, not block work the user clearly wants.

## Cross-references

- HTTP 402/429 handling: [`errors-and-limits.md`](./errors-and-limits.md)
- Partner-Node detection: [`partner-nodes.md`](./partner-nodes.md)
- Operational rules 6, 7, 8: [`operational-rules.md`](./operational-rules.md)
