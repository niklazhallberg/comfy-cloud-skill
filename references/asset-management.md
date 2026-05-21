# Asset Management

Comfy Cloud uses **content-addressed storage** — assets are identified by their content hash (Blake3, 64 hex chars), not by filename or folder path.

## Implications

- The same image uploaded twice produces the same hash and the same storage reference. No dupes.
- `subfolder` and `overwrite` fields on upload endpoints are **accepted but ignored**.
- File identity is the hash. Filenames are display metadata.
- Existence check via `HEAD /api/assets/hash/{blake3:...}` is the canonical "do I already have this?" call.

## Upload paths

### Image input (for img2img, inpaint, ControlNet reference)

```
POST /api/upload/image
Content-Type: multipart/form-data
  image: <file>
  type: input
```

Returns `{ name, subfolder, type }` — use `name` to reference in workflow.

Limits:
- Max file size: 50 MB
- Max edge length: 16,384 px
- Max resolution: 64 megapixels

### Mask input (paired with an image)

```
POST /api/upload/mask
Content-Type: multipart/form-data
  image: <mask-file>
  original_ref: <json-string-referencing-image>
```

Returns mask metadata including layer hashes (`mask`, `paint`, `painted`, `painted_masked`).

### Model files (LoRA, checkpoint, VAE, upscaler)

Two paths:

**Direct upload from local disk:**

```
POST /api/assets
Content-Type: multipart/form-data
  file: <safetensors>
  tags: ["models"] or ["loras"] or etc.
```

Returns asset metadata. Returns 200 if hash already cached (no re-upload), 201 if new.

**Background download from HuggingFace or Civitai:**

```
POST /api/assets/download
Content-Type: application/json
  { "url": "https://huggingface.co/...", "tags": ["loras"], "name": "my-lora" }
```

Returns 200 if cached, 202 with `task_id` if downloading. Poll via `GET /api/tasks/{task_id}` to monitor.

Private models on HF/Civitai require the user to save API tokens in Settings → Secrets first.

### Reference an existing hash without re-uploading

```
POST /api/assets/from-hash
Content-Type: application/json
  { "hash": "blake3:abc123...", "name": "...", "tags": [...] }
```

Hash prefix must be `blake3:` or `sha256:`. Useful when the asset is already in storage from a previous run.

## Listing / search

```
GET /api/assets?include_tags=loras&name_contains=brand
```

Filters:
- `include_tags`, `exclude_tags`
- `name_contains`
- `metadata_filter` (JSON)

Sort:
- `name`, `created_at`, `updated_at`, `size`, `last_access_time`

Pagination: standard `limit` + offset / cursor.

## Tagging

Assets can be tagged for organization. Tags are the recommended **registry mechanism** — don't build a parallel database:

```
POST /api/assets/{id}/tags
  { "tags": ["proxy:project=brand-x", "proxy:run=2026-05-21T10:00"] }
```

Then search:

```
GET /api/assets?include_tags=proxy:project=brand-x
```

Use tag histograms via `GET /api/assets/tags/refine` for agent-driven discovery ("show me all tags used in this project").

## Output retrieval

After workflow completion:

1. `GET /api/jobs/{prompt_id}` returns `outputs` with filename + subfolder per output.
2. `GET /api/view?filename=...&type=output` returns **302 redirect** to a signed GCS URL.
3. Follow the redirect. **Do not forward `X-API-Key`** to the signed URL (see [Rule 9 in operational rules](./operational-rules.md)).
4. Download the binary from the redirect target.

For PNG output channel splitting (e.g. RGB vs alpha):

```
GET /api/view?filename=...&channel=rgb
GET /api/view?filename=...&channel=alpha
```

## Best practices for the skill

- **Hash before upload.** Compute Blake3 client-side, then `HEAD /api/assets/hash/{hash}` to skip the upload if already cached. Saves bandwidth and time.
- **Tag every uploaded asset with the run context.** Manifests can then back-reference the assets used per generation.
- **For brand / LoRA libraries: use `POST /api/assets/download` from HF or Civitai instead of local upload.** Faster (server-to-server), better for reproducibility (URLs are stable references).
- **Validate before download.** `GET /api/assets/remote-metadata?url=...` returns content_length, filename, and a `ValidationResult` that rejects unsafe PickleTensor formats. Use before triggering the actual download.

## Cross-references

- HTTP endpoints: [`api-endpoints.md`](./api-endpoints.md)
- Workflow reference to uploaded assets: [`workflow-format.md`](./workflow-format.md)
- Lifecycle of a generation: [`websocket-protocol.md`](./websocket-protocol.md)
