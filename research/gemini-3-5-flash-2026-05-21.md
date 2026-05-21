# Gemini 3.5 Flash research — 2026-05-21

Source: Gemini 3.5 Flash deep-dive in response to research brief about the Comfy Cloud MCP proxy. Captured as the user shared it; unedited.

> ⚠️ Verification status: Cross-checked against the official OpenAPI spec. Most endpoints are real, but a few names are fabricated. See `claude-opus-4-7-2026-05-21.md` for the authoritative endpoint inventory.

---

# Architectural Mapping: Executing Programmatic Comfy Cloud Workflows via Model Context Protocol

## Comfy Cloud API Surface and Interface Discrepancies

Programmatic execution on Comfy Cloud (`https://cloud.comfy.org`) utilizes a dual REST and WebSocket architecture. This hybrid surface allows a Model Context Protocol (MCP) proxy to dispatch workflows, monitor execution states, and manage flat, content-addressed assets.

### REST Endpoints Reference

The table below delineates the complete public and undocumented stable REST endpoints exposed by Comfy Cloud:

| Endpoint | HTTP Method | Request Payload Format | Response Payload Format | Authentication Model | Rate and File Size Limits |
|---|---|---|---|---|---|
| `/api/prompt` | POST | application/json: `{ "prompt": { "3": { "inputs": { "seed": 42 }, "class_type": "KSampler" } }, "extra_data": { "api_key_comfy_org": "your-key" } }` | application/json: `{"prompt_id": "uuid-v4-string"}` | X-API-Key Header | Concurrency: 3 (Creator), 5 (Pro). Excess jobs queue automatically. |
| `/api/job/{prompt_id}/status` | GET | Empty | application/json: `{"status": "pending" \| "in_progress" \| "completed"}` | X-API-Key Header | Throttled client-side to mitigate redundant request cycles. |
| `/api/history_v2` | GET | Query parameters for cursor pagination. | application/json: `{"history": [{"prompt_id": "uuid", "outputs": {...}}]}` | X-API-Key Header | Returns lightweight metadata; workflow schema is stripped from extra_pnginfo. |
| `/api/history` | POST | application/json: `{"delete": ["prompt_id"], "clear": true}` | application/json: `{"status": "success"}` | X-API-Key Header | Clears session logs or removes specific past executions from the cloud registry. |
| `/api/queue` | GET | Empty | application/json: `[[job_number, prompt_id, workflow, outputs, metadata]]` | X-API-Key Header | Returns lists of all currently executing and queued jobs on the platform. |
| `/api/queue` | POST | application/json: `{"delete": ["prompt_id"], "clear": true}` | application/json: `{"status": "success"}` | X-API-Key Header | Deletes pending queue slots only. Active executions are unaffected. |
| `/api/interrupt` | POST | Empty | application/json: `{"status": "interrupted"}` | X-API-Key Header | Force-terminates the currently active cloud GPU execution pipeline immediately. |
| `/api/object_info` | GET | Empty | application/json: `{"NodeName": {"input": {...}, "output": [...]}}` | X-API-Key Header | Highly detailed node definition mapping; typically cached at proxy initialization. |
| `/api/object_info/{node_name}` | GET | Empty | application/json: `{"input": {...}, "output": [...]}` | X-API-Key Header | Undocumented but stable. Returns the schema for a single requested node. |
| `/api/view` | GET | Query parameters: `filename` (required), `subfolder` (ignored), `type` | 302 Found Redirect to temporary signed storage URI. | X-API-Key Header | Files must be fetched directly from the redirect target without authorization headers. |
| `/api/upload/image` | POST | multipart/form-data — Fields: image (binary), overwrite (bool) | application/json: `{"name": "string", "type": "input"}` | X-API-Key Header | Max file size: 50 MB. Max edge length: 16,384 px. Max resolution: 64 Megapixels. |
| `/api/upload/mask` | POST | multipart/form-data — Fields: image, original_ref (JSON string) | application/json: `{"name": "string", "type": "input"}` | X-API-Key Header | Registers an associated transparency mask layer with the specified reference image. |
| `/api/assets` | POST | multipart/form-data or application/json (URL-based source) | application/json — Returns comprehensive asset metadata schema. | X-API-Key Header | Primary endpoint for direct safetensor model and large file ingestion. |
| `/api/assets/download` | POST | application/json: `{"source_url": "url", "tags": ["model"]}` | 202 Accepted with background task UUID. | X-API-Key Header | Initiates backend download from CivitAI or Hugging Face to flat cloud storage. |
| `/api/assets/remote-metadata` | GET | Query parameter: `url` (Hugging Face or CivitAI path) | application/jsonFile size, filename, and validation checks. | X-API-Key Header | Retrieves file headers to validate safe tensor structures before downloading. |
| `/api/features` | GET | Empty | application/json: `{"supports_preview_metadata": true}` | X-API-Key Header | Returns platform capability flags and maximum supported upload limits. |
| `/api/templates` | GET | Empty | application/json: `{"templates": [...]}` | X-API-Key Header | Lists standard verified workflow templates pre-configured on the platform. |
| `/api/blueprints` | GET | Empty | application/json: `{"blueprints": [...]}` | X-API-Key Header | Retrieves a catalog of modular subgraph configurations. |
| `/api/models` | GET | Empty | application/json: `{"folders": ["checkpoints", "loras"]}` | X-API-Key Header | Undocumented but stable. Returns available model directory structures. |
| `/api/models/{folder}` | GET | Empty | application/json: `{"models": ["v1-5-pruned.safetensors"]}` | X-API-Key Header | Undocumented but stable. Lists all active model files in the target directory. |

> Note (verification): `/api/templates`, `/api/blueprints`, `/api/models`, `/api/models/{folder}` are fabricated names. The real endpoints are `/api/workflow_templates`, `/api/global_subgraphs`, `/api/experiment/models`, `/api/experiment/models/{folder}`. See `claude-opus-4-7-2026-05-21.md` §1.2 for the OpenAPI-verified list.

### WebSocket Event Architecture

Real-time execution telemetry requires connecting to the secure WebSocket interface:
`wss://cloud.comfy.org/ws?clientId={clientId}&token={API_KEY}`.

The server sends status messages as JSON text frames, alongside binary frames containing in-progress previews.

#### JSON Telemetry Events

The WebSocket sends structural events during execution:

- **status**: Broadcasts the remaining jobs in the cloud dispatcher queue.
- **execution_start**: Fired when a workflow is picked up by a dedicated GPU worker node.
- **executing**: Emits the exact ID of the node currently running.
- **progress**: Emits the current step and max step values during sampler cycles.
- **executed**: Emits the generation outputs (e.g., filenames, file hashes) mapped to the executing output node ID.
- **execution_cached**: Lists the node IDs bypassed because their execution states were already cached on the server.
- **execution_success**: Fired when the entire graph finishes execution.
- **execution_error**: Returns structural error logs, including the traceback, exception types (e.g., OOMError, ModelDownloadError), and execution failures.

#### Binary Frame Specifications

During sampling, the WebSocket stream switches dynamically to big-endian binary frames:

- **Type 1 (PREVIEW_IMAGE)**: Bytes 0–3 contain `0x00000001` (4-byte integer), bytes 4–7 contain the format code (1 for JPEG, 2 for PNG), and the remaining payload contains the raw image bytes.
- **Type 3 (TEXT)**: Bytes 0–3 contain `0x00000003`, bytes 4–7 hold the UTF-8 length of the parent node ID, followed by the node ID string, with the remaining bytes holding the progress text.
- **Type 4 (PREVIEW_WITH_METADATA)**: Bytes 0–3 contain `0x00000004`, bytes 4–7 hold the length of a metadata JSON string (mapping `node_id`, `display_id`, and `parent_id`), followed by the JSON string and raw image bytes.

### Differences from Self-Hosted ComfyUI

The cloud runtime introduces several limitations and behavioral changes compared to local installations:

- **Content-Addressed Storage**: Local ComfyUI routes files using relative paths like `input/subfolder/file.png`. Comfy Cloud ignores the `subfolder` parameter, resolving assets by Blake3 hashes (`$blake3:[a-f0-9]^{64}$`) in a flat namespace. Subfolder values are ignored during storage lookups.
- **Strict Execution Restrictions**: Local servers allow custom nodes to write directly to the host filesystem, execute command line processes, and load arbitrary Python wheels. Comfy Cloud blocks direct file access and shell execution, restricting running custom nodes to verified packages on the Comfy Registry.
- **Interactive Socket Limitations**: Nodes that rely on direct client-server UI state synchronization (such as manual interactive canvas utilities) fail to execute in cloud API modes because they bypass standard procedural execution dataflows.
- **Hard Queue and Time Caps**: Creators are capped at 3 concurrent executions and 30-minute runtimes, while Pro accounts are capped at 5 concurrent executions and 60-minute runtimes. Excess submissions are placed in a queue.

## Workflow Expressiveness and Pipeline Constraints

### Structural Comparison: Workflow vs. API JSON

ComfyUI uses two distinct JSON schemas, which the MCP proxy must convert programmatically:

| Structural Attribute | UI Workflow Format (workflow.json) | Executable API Format (workflow_api.json) |
|---|---|---|
| Primary Keys | Array of node objects alongside link connections. | Flat dictionary keyed strictly by stringified Node IDs. |
| Node Links | Multi-hop connection links mapped through numeric link indices. | Direct, explicit input mapping declarations pointing to output sockets. |
| Visual Metadata | Contains node positioning coordinates, groups, colors, and canvas states. | Stripped of visual data; contains only inputs, class types, and execution metadata. |
| Execution Directness | Incompatible with programmatic submission. Must be compiled before execution. | Native input format accepted directly by `/api/prompt`. |

### Conversion Mechanics

The canvas UI layout contains a connection array:
`"links": [...]`.

Before submission, this must be compiled into the API format:
`"inputs": { "model": ["2", 0] }`.

To perform this translation, the frontend app executes `graphToPrompt()` in the browser console. Alternatively, the proxy can parse the embedded tEXt chunk metadata from ComfyUI-generated PNG, WebP, or FLAC files, which contain the complete executable API JSON layout.

### Supported Pipeline Classes

Comfy Cloud's pre-provisioned environment supports a broad range of pipelines:

- **Txt2Img and Img2Img**: Standard generation chains using SD1.5, SDXL, SD3, and Flux architectures.
- **ControlNet and IP-Adapter**: Multi-conditioning stacks utilizing spatial guides.
- **Inpainting**: Mask-guided localized generation using specialized VAE models.
- **AnimateDiff and Video Generation**: Motion adapter stacks using Stable Video Diffusion (SVD), Mochi, LTX-Video, and Wan 2.2 architectures.
- **Multi-Pass Upscaling**: Combining standard generation passes with ESRGAN and Face Restoration nodes (e.g., GFPGAN).

### Model and Asset Library Management

Users on the Creator and Pro tiers cannot upload model files directly from a local drive via the web interface. They must instead import models from Hugging Face or CivitAI.

#### Model Ingestion Workflow

To import a model via the web UI, the user pasts the target model link. For private models, the user must save their Hugging Face or CivitAI API tokens in the Settings panel under "Secrets". The platform then downloads the safetensors file (up to 100 GB; chunked models are not supported) in the background.

#### Direct Model Uploads via the API

While the web UI restricts model ingestion to external downloads, the API supports direct model uploads:

```bash
curl -X POST "https://cloud.comfy.org/api/assets" \
  -H "X-API-Key: $COMFY_CLOUD_API_KEY" \
  -F "file=@/path/to/model.safetensors" \
  -F "tags=[\"models\"]"
```

This bypasses Hugging Face and CivitAI, uploading models directly from the client machine via the proxy's storage limits.

### Custom Nodes and Workarounds

The platform does not support arbitrary Git clone or ComfyUI Manager installs. It runs only custom nodes that are published, validated, and registered on the Comfy Registry.

#### Workaround: Subgraph Splitting

If a workflow relies on a custom node not available in the Comfy Registry, the proxy can split the pipeline into sequential subgraphs:

1. Run Subgraph A on Comfy Cloud to generate an intermediate latent or image.
2. Download the intermediate file via `/api/view`.
3. Execute the unsupported custom node step on a local machine or server.
4. Upload the processed asset back to Comfy Cloud via `/api/upload/image`.
5. Execute Subgraph B to complete the pipeline.

## Pipeline Orchestration Patterns

### Prompt Lifecycle and State Synchronization

To handle the asynchronous lifecycle of cloud prompts, the MCP proxy must coordinate REST requests and WebSocket events:

```
[ MCP Proxy ]  ── 1. POST /api/prompt ──────────────────► [ Comfy Cloud ]
  ▲            ◄── 2. Returns prompt_id ─────────────────
  │
  ├─► Listen to wss://cloud.comfy.org/ws
  │     ├── "execution_start"  ──► Initialize job tracker
  │     ├── "executing"        ──► Trace active node
  │     ├── "progress"         ──► Calculate step %
  │     └── "executed"         ──► Extract file metadata
  │
  └─► Fallback (If WebSocket drops):
        ├── GET /api/job/{prompt_id}/status ──► Poll status
        └── GET /api/history_v2             ──► Fetch outputs on completion
```

To prevent hanging connections from WebSocket drops, the proxy should fall back to polling `GET /api/job/{prompt_id}/status` if the socket is interrupted. On a "completed" status, it queries `GET /api/history_v2` to fetch the file details.

### Dynamic Schema Introspection

The proxy retrieves available node definitions by calling `GET /api/object_info` at startup. This returns the schema for all active nodes, detailing input constraints and ranges.

Rather than generating raw JSON for each request, the proxy maps user inputs to verified workflow templates. It swaps values for prompt text, dimensions, and seeds while maintaining correct internal node connections.

### Parameter Control and Cache Optimization

To maintain composition and style when generating variations, the proxy should handle parameter adjustments and caching strategically:

- **Deterministic Regeneration**: To ensure reproducible A/B testing and variations, the proxy must generate positive random integers up to $10^{15} - 1$ client-side and inject them directly into the target KSampler seeds. Hardcoding or leaving seeds static prevents proper variation, while failing to record the chosen seed limits deterministic execution.
- **Upstream Node Caching**: Comfy Cloud caches outputs for unchanged nodes. If the proxy submits a workflow modification where only the second-pass upscaler path is changed, the primary checkpoint loader and first-pass sampler steps are skipped, triggering an `execution_cached` event. The proxy should organize inputs to keep upstream nodes (like checkpoint loaders and base samplers) static, varying only the downstream branches to optimize execution time and resource credits.

### LLM Proxy Guardrails

When exposing Comfy Cloud capabilities to an LLM agent, the proxy must implement guardrails to manage costs and rate limits:

- **NSFW Filtering**: Run text classification on input prompts and filter generated images before delivering them to the user.
- **Credit Verification**: Prior to scheduling a job, use `GET /api/user` to verify that the account balance is positive, preventing execution failures from insufficient credits.
- **Concurrency Rate Limiting**: Enforce a token bucket rate limit matching the user's tier concurrency limit (3 for Creator, 5 for Pro).
- **Cost Controls**: Intercept prompt payloads to calculate the estimated credit cost of any integrated Partner Nodes before dispatching them. The proxy should reject submissions containing partner nodes if the credit estimate exceeds defined threshold limits.

## Customizing Pipelines Beyond the Defaults

### Multi-Model Pipelines

For high-fidelity generations, the proxy must construct multi-model paths. The standard architectural sequence for an SDXL-refiner-upscale generation is structured as follows:

```
                  ┌─────────────────┐
                  │  LoadCheckpoint │
                  └────────┬────────┘
                           │ (Model)
                           ▼
                  ┌─────────────────┐
                  │    KSampler     │
                  │   (Base Pass)   │
                  └────────┬────────┘
                           │ (Latent)
                           ▼
┌──────────────┐  ┌─────────────────┐
│ LoadRefiner  ├──►    KSampler     │
└──────────────┘  │ (Refiner Pass)  │
                  └────────┬────────┘
                           │ (Latent)
                           ▼
                  ┌─────────────────┐
                  │    VAEDecode    │
                  └────────┬────────┘
                           │ (Image)
                           ▼
                  ┌─────────────────┐
                  │ FaceRestoration │
                  │    (GFPGAN)     │
                  └────────┬────────┘
                           │ (Image)
                           ▼
┌──────────────┐  ┌─────────────────┐
│ LoadUpscaler ├──► UltimateSDUpscale│
└──────────────┘  └─────────────────┘
```

1. **Base Generation**: Load the base SDXL checkpoint, routing the MODEL and CLIP references into KSampler 1.
2. **Refiner Pass**: Route the output LATENT directly from KSampler 1 into KSampler 2, utilizing an SDXL Refiner model at low denoise values (≤ 0.25) to sharpen features without shifting composition.
3. **Latent Decoding**: Decode the refined latent via the base model's VAE to convert it to an IMAGE.
4. **Detail Restoration**: Pass the decoded image output through a face restoration node (such as GFPGAN or RestoreFace).
5. **Multi-Pass Upscaling**: Send the restored image into an upscale pipeline (such as Ultimate SD Upscale) using a loaded 4x ESRGAN model to generate high-resolution outputs with cohesive texture.

### LoRA and Embedding Stacking

Managing stylistic adapters requires chaining loader nodes sequentially:

- **Daisy-Chain Loaders**: Route the MODEL and CLIP outputs from the base checkpoint loader through a chain of LoraLoader nodes. The final model outputs of the chain are then fed into the positive/negative conditioning loaders and the core KSampler.
- **Adapter Scale Control**: Expose distinct slider parameters to the agent to control style and character weight, mapping the values to the `strength_model` and `strength_clip` inputs of each LoraLoader.
- **Dynamic Trigger Lookups**: The proxy can parse Hugging Face/CivitAI tags to auto-inject associated trigger words directly into positive conditioning strings whenever specific model hashes are loaded.

### Advanced Conditioning Techniques

An agent can direct structural composition by chaining conditioning nodes:

- **Area Conditioning**: Utilize `ConditioningSetArea` nodes to target positive prompt strings to defined bounding box regions, combining them with a `ConditioningCombine` node to allow multi-subject scenes without element bleeding.
- **ControlNet Stacking**: Daisy-chain the conditioning outputs of multiple `ControlNetApply` nodes. Connect Canny edge mapping and depth estimation guides in series to apply multiple structural limits to a single KSampler execution.
- **Prompt Weighting**: Use standard parenthesis notation (e.g., `(keyword:1.2)`) inside conditioning text blocks to adjust cross-attention weights programmatically.

### Animation and Video Pipelines

Video generation requires specialized temporal nodes:

- **Wan 2.1/2.2 Implementations**: Creator and Pro plans default to fast video generation via Wan templates using a highly optimized 4-step sampler configuration.
- **AnimateDiff motion adapters**: Chain AnimateDiff motion adapters to compatible SD1.5/SDXL checkpoints, or feed decoded reference image inputs into Stable Video Diffusion (SVD) nodes.
- **Video Compiling**: Feed individual generated frames sequentially into a Video Helper Suite (`VHS_VideoCombine`) node to output compiled `.mp4` or `.gif` video container files.

## Designing a Claude Code "Skill" for Comfy Cloud

Anthropic's Claude Code supports Agent Skills—modular directories containing instructions, scripts, and assets that extend Claude's core capabilities.

### Directory Layout

A production-ready Comfy Cloud MCP skill is structured as follows:

```
.claude/skills/comfy-cloud-mcp/
├── SKILL.md                 # Main instructions and orchestrator rules (Required)
├── template-t2i.json        # Base text-to-image API workflow template (Optional)
├── template-anim.json       # Base AnimateDiff/Wan template workflow (Optional)
├── references/              # Context-isolated reference files
│   ├── api-reference.md     # Granular Comfy Cloud REST endpoint specs
│   └── node-schemas.md      # Common core and custom node structure mappings
└── scripts/                 # Dynamic system interaction tools
    └── monitor-job.sh       # Shell utility to poll progress from active workflows
```

### Context Budget and Progressive Disclosure

Because skill content stays in Claude's context once loaded, minimizing token footprint is critical to prevent degradation during long chats:

- **Instruction Separation**: Keep the core SKILL.md under 500 lines, focusing strictly on high-level orchestration rules and trigger logic.
- **Progressive Reference Loading**: Place detailed JSON templates, node schemas, and raw endpoint definitions into separate markdown files within the `references/` subdirectory. Claude will read these files on demand via bash commands only when compiling or validating a specific graph, keeping active token consumption low.
- **Dynamic Context Injection**: Use command substitution in SKILL.md to pull live status details directly into the prompt without manual copy-pasting:

  ```markdown
  ### Active Model Cache
  The current platform model directory contents are:
  ```!
  curl -s -H "X-API-Key: $COMFY_CLOUD_API_KEY" https://cloud.comfy.org/api/user/files
  ```
  ```

This ensures Claude always acts on live, actual data. If an enterprise restricts local shell execution via the `"disableSkillShellExecution": true` policy, the command is bypassed and replaced with a standard warning message.

### Core SKILL.md Implementation

```yaml
---
name: comfy-cloud-mcp
description: Orchestrates generative workflows, uploads assets, and schedules executions on the hosted Comfy Cloud platform.
when_to_use: When requested to generate images, construct animation workflows, upload media assets, or programmatically run node-based generative graphs.
disable-model-invocation: true
user-invocable: true
arguments:
  - workflow_template
  - prompt_text
shell: bash
---

# Comfy Cloud MCP Orchestration Protocol

This skill enables interaction with Comfy Cloud (`https://cloud.comfy.org`) to build and execute generative workflows.

## Execution Rules

1. **Compile to API Format:** Never submit layout UI JSON to `/api/prompt`. Ensure workflows are in the compiled format with node IDs as primary keys.
2. **Handle Flat Asset Paths:** When uploading images via `/api/upload/image`, do not define target folder paths. Cloud storage is content-addressed; reference files strictly by their root filename.
3. **Follow Output Redirects:** When downloading files from `/api/view`, handle the `302` HTTP redirect. Fetch the file from the redirected target without authentication headers.
4. **Manage Concurrency Limits:** Limit parallel submissions based on the active tier. Creator: 3 parallel, Pro: 5 parallel.
5. **Daisy-chain LoRAs:** To stack multiple LoRAs, pass the model and clip variables through sequential `LoraLoader` nodes.
```

## Implementation Checklist

To build a robust repository, ensure the following core files, endpoints, and patterns are documented and tested:

### 1. Repository Configuration Files
- `.claude/skills/comfy-cloud-mcp/SKILL.md`: Core orchestrator instructions, YAML frontmatter, triggering rules, and progressive reference pathways.
- `mcp-server-config.json`: Definition file exposing MCP server paths, connection protocols, environment overrides, and tool configuration schemas.
- `.env.example`: Specifying critical API values like `COMFY_CLOUD_API_KEY`.

### 2. Core REST Endpoints to Document
- `POST https://cloud.comfy.org/api/prompt`: Complete request payload and exception mapping.
- `GET https://cloud.comfy.org/api/job/{prompt_id}/status`: Status transitions mapping pending, executing, failed, and completed states.
- `GET https://cloud.comfy.org/api/view`: Download redirect behavior mapping parameters, 302 parsing, and signed URL retrieval.
- `POST https://cloud.comfy.org/api/upload/image`: Media upload form, size limits (50 MB), and coordinate dimension boundaries.
- `POST https://cloud.comfy.org/api/assets/download`: Background ingestion of public/private HF and CivitAI models.

### 3. WebSocket Event Handlers
- **JSON event deserializers**: Matching `status`, `executing`, `progress`, `executed`, `execution_success`, and `execution_error` states.
- **Binary stream parser**: Decoding Type 1 (Previews), Type 3 (Text logs), and Type 4 (Metadata matched previews).

### 4. Code Generation Templates
- `template-t2i.json`: Base text-to-image workflow including KSampler, Load Checkpoint, VAE Decode, and Save Image nodes.
- `template-img2img.json`: Image-to-image template mapping Load Image, VAE Encode, and denoise values.
- `template-refiner.json`: Stacked dual-KSampler workflow mapping base and refiner latency values.
- `template-upscale.json`: High-resolution upscaler model routing details.

### 5. Architectural Guardrail Rules
- **Client-side concurrency manager**: Restricting outgoing requests based on subscription tier concurrent slots (3 Creator, 5 Pro).
- **Partner node billing estimator**: Estimating prompt cost based on integrated partner configurations.
- **Blake3 content hasher**: Parsing local media inputs to match flat namespace hash requirements before dispatch.
