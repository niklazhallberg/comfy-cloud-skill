# Pipeline Patterns

Recipes for the major workflow classes you can build on Comfy Cloud. Each section gives the node sequence, key parameters, and common variations.

## txt2img (SD1.5 / SDXL / Flux / Qwen)

The canonical chain:

```
CheckpointLoaderSimple
    → CLIPTextEncode (positive)  ─┐
    → CLIPTextEncode (negative)  ─┤
    → EmptyLatentImage          ─┤
                                  ▼
                            KSampler
                                  │
                            VAEDecode
                                  │
                            SaveImage
```

Key parameters: `seed`, `steps`, `cfg`, `sampler_name`, `scheduler`, `denoise=1.0`.

Stack-specific: Flux Schnell uses 4 steps + cfg=1.0; Flux Dev uses ~20 steps + cfg=3.5; SDXL base uses ~25 steps + cfg=7.

## img2img

```
LoadImage (or asset reference)
    → VAEEncode
    → KSampler (denoise < 1.0)    // typically 0.5–0.8
    → VAEDecode
    → SaveImage
```

The `denoise` value controls how much of the input is preserved (0 = identical, 1 = ignore input).

## Inpainting

```
LoadImage
    → InpaintModelConditioning  ←  LoadImageMask
    → KSampler
    → VAEDecode
    → SaveImage
```

Alternatives: Impact Pack detailers for face-region-only inpaint; RMBG / SAM masking for background replacement.

## ControlNet (single guide)

```
LoadImage (reference)
    → preprocessor (e.g. Canny, DepthAnything, OpenPose)
    → ControlNetApply  ←  ControlNetLoader  ←  conditioning_positive
    → KSampler
```

Stacking: chain multiple `ControlNetApply` nodes — each takes a conditioning input and outputs new conditioning.

Advanced: `ComfyUI-Advanced-ControlNet` for per-step weighting and reference modes.

## LoRA stack

```
CheckpointLoaderSimple
    → LoraLoader (lora_1, strength_model=1.0, strength_clip=0.8)
    → LoraLoader (lora_2, ...)
    → LoraLoader (lora_3, ...)
    → CLIPTextEncode
    → KSampler
```

Each `LoraLoader` takes `(model, clip)` and outputs `(model, clip)`. Just chain.

Tip: keep upstream loaders identical between runs ([Rule 4 in operational rules](./operational-rules.md)) for cache-aware variation.

## SDXL base + refiner

```
CheckpointLoaderSimple (SDXL base)
    → KSampler (denoise=1.0, ~20 steps)
    → KSampler (model=refiner, denoise=0.2–0.25, ~10 steps, same latent)
    → VAEDecode (with base VAE)
    → SaveImage
```

The refiner pass takes the base's latent directly (no decode/encode round-trip). Mismatched UNet types will surface as `ValidationError`.

## Multi-pass upscale

```
... → VAEDecode → IMAGE
    → UltimateSDUpscale (model: 4x_NMKD-Siax_200k, denoise 0.2)
    → SaveImage
```

For face-specific detail recovery, add Impact Pack `FaceDetailer` between decode and upscale.

## AnimateDiff

```
CheckpointLoaderSimple (SD1.5)
    → AnimateDiffLoaderGen1 (motion model)
    → CLIPTextEncode (per-frame OR scheduled prompts)
    → KSampler
    → VAEDecode
    → VHS_VideoCombine (output .mp4)
```

## Wan 2.2 (i2v)

```
WanImageToVideoSampler  (image input, prompt, motion settings)
    → VHS_VideoCombine
```

Wan 2.2 templates on Cloud are tuned for 4-step sampling — fast but specific. See `ComfyUI-WanVideoWrapper` for advanced controls (TeaCache, MagCache, MultiTalk).

## LTX-Video

```
LTXVPipelineLoader
    → LTXVBaseSampler  (or LTXVInContextSampler, LTXVLoopingSampler)
    → VHS_VideoCombine
```

## Cross-references

- Workflow JSON shape: [`workflow-format.md`](./workflow-format.md)
- Which nodes exist on Cloud right now: [`pre-installed-nodes.md`](./pre-installed-nodes.md)
- Partner-Node workflows (Kling, Luma, etc.): [`partner-nodes.md`](./partner-nodes.md)
- Cost per pattern: [`cost-and-concurrency.md`](./cost-and-concurrency.md)

---

*This file is a working pattern catalog, not exhaustive. New patterns can be promoted from working `templates/*.json` files. See [CONTRIBUTING.md](../CONTRIBUTING.md).*
