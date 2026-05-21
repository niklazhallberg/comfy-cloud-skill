# Pre-Installed Nodes on Comfy Cloud

The authoritative live list is at https://comfy.org/cloud/supported-nodes/. Discover at runtime via `GET /api/object_info`.

This file is a **curated highlight reel**, not a complete enumeration. For exhaustive lookup, use the live API.

## Model folder categories (28 total)

When discovering installed models, query `/api/experiment/models/{folder}` for each category. From `folder_paths.py:14-63` in the upstream ComfyUI repo:

**Core generation:**
- `checkpoints` — Full diffusion checkpoints (SD1.5, SDXL, Flux, etc.)
- `loras` — LoRA / LoCon / LyCORIS adapters
- `vae` — Variational autoencoders
- `vae_approx` — Lightweight approximate VAEs for previews (TAESD)
- `embeddings` — Textual inversions
- `text_encoders` — CLIP / T5 / Gemma text encoders for new architectures
- `diffusion_models` — Unet-only / DiT-only weights (separated from full checkpoints)
- `clip_vision` — Image encoders for IP-Adapter etc.

**Conditioning:**
- `controlnet` — ControlNet weights
- `style_models` — Style adapter weights
- `gligen` — GLIGEN grounding weights
- `hypernetworks` — Legacy hypernet weights
- `photomaker` — PhotoMaker character-consistency weights
- `classifiers` — Classification model weights
- `model_patches` — Patch-style fine-tunes

**Image post-processing:**
- `upscale_models` — Pixel-space upscalers (ESRGAN, RealESRGAN, NMKD, UltraSharp, etc.)
- `latent_upscale_models` — Latent-space upscalers
- `background_removal` — RMBG / BiRefNet weights
- `detection` — Object detection weights (YOLO etc.)

**Video / motion:**
- `frame_interpolation` — RIFE etc.
- `optical_flow` — Optical flow estimation weights
- `geometry_estimation` — Depth / normal weights (DepthAnything, Lotus)

**Audio:**
- `audio_encoders` — Audio embedding models

**Infrastructure:**
- `configs` — Model config files
- `diffusers` — HF diffusers-format model directories
- `custom_nodes` — Custom node packages (Cloud-curated, not user-installable)

When the skill needs to know what's available, iterate these categories — don't assume "loras" is the only path for adapter-style weights.

## Foundational utility

- `ComfyUI_essentials`
- `ComfyUI-Logic`
- `Basic data handling` (258 nodes — booleans, math, regex, type casting, tensor ops)
- `KJNodes` (41 nodes — assorted samplers, scheduling, math)
- `WAS Node Suite` (40 nodes — general-purpose)
- `ComfyUI_SchemaNodes` (Schema Boolean/Float/Int/String/Image Parameter — **explicitly designed for external parameterization**)

## Detailing & masking

- `ComfyUI Impact Pack` (39 nodes — SAMLoader, detailers, regional samplers)
- `comfyui_face_parsing`
- `ComfyUI-RMBG` (BiRefNet, RMBG-2.0, SAM/SAM2/SAM3, GroundingDINO)
- `ComfyUI-SAM3`

## ControlNet & conditioning

- `ComfyUI-Advanced-ControlNet` (scheduling, weighting, reference modes)
- `ComfyUI_IPAdapter_plus`

## Upscaling

- `ComfyUI_UltimateSDUpscale`
- `ComfyUI-Upscaler-Tensorrt`
- `ComfyUI_Steudio` (Divide-and-Conquer upscaling)

## Video & animation

- `ComfyUI-VideoHelperSuite`
- `ComfyUI-AnimateDiff-Evolved`
- `ComfyUI-WanVideoWrapper` (51 nodes — Wan 2.1/2.2, TeaCache, MagCache, MultiTalk, FantasyTalking)
- `ComfyUI-LTXVideo` (Base Sampler, In-Context Sampler, Looping Sampler)
- `ComfyUI-CogVideoXWrapper`
- `ComfyUI-Frame-Interpolation` (RIFE)
- `DynamiCrafterWrapper`
- `LivePortraitKJ`
- `ComfyUI-FlashVSR_Ultra_Fast`
- `ComfyUI-WanVaceAdvanced`, `ComfyUI-WanAnimatePreprocess`, `ComfyUI-SCAIL-Pose`

## Photoshop-style layers / compositing

- `ComfyUI_LayerStyle` + `ComfyUI_LayerStyle_Advance`
- `ComfyUI-enricos-nodes` (visual compositor V3)

## Flux-specific

- `ComfyUI-Fluxtapoz` (RF-Inversion etc.)
- `ControlAltAI-Nodes` (Flux Resolution Calc, Region Mask Generator)

## Samplers & schedulers

- `RES4LYF` (86 nodes — 40 sampler types, 20 noise types, advanced sigma manipulation)

## 3D

- `ComfyUI-Sharp` (Apple SHARP)
- `comfyui-PlyPreview`

## Audio

- `ComfyUI_AudioTools`
- `ComfyUI-MelBandRoFormer`
- `ComfyUI-Qwen-TTS`

## Vision / VLM

- `ComfyUI-QwenVL` (Qwen2.5-VL / Qwen3-VL)
- `ComfyUI-DepthAnythingV2`
- `ComfyUI-Lotus`

## Color & filters

- `radiance` (24 nodes — 32-bit HDR support)
- `ComfyUI-Image-Filters`

## Prompting

- `OneButtonPrompt`
- `ComfyUI-Prompt-Combinator`
- `ComfyUI_Fill-Nodes` (audio-reactive, prompt utilities)

## What's NOT installable

- Arbitrary custom node packs via Git or ComfyUI Manager. Only the curated list above. Request additions at https://comfy.org/cloud/supported-nodes/ → "Submit new request".
- Self-managed model files via filesystem. Use `POST /api/assets` or `POST /api/assets/download` instead (see [`asset-management.md`](./asset-management.md)).

## Discovery in skill code

```
# Pseudo-code
cache = get_or_fetch_object_info()
if "DesiredNodeClass" not in cache:
    raise NodeNotAvailableError(...)
combo_values = cache["DesiredNodeClass"]["input"]["required"]["sampler_name"][0]
```

Never hardcode a list in workflow templates without validating against this discovery step.
