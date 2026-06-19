# Canvas render — final delivery on cloud.comfy.org

**Binding rule.** The final deliverable for any Comfy workflow this skill
designs is the **live canvas in the user's Comfy Cloud browser**. JSON files
in `output/`, manifests, and screenshots are intermediate artifacts. The user
runs Comfy Cloud in Chrome and wants the graph dropped onto their canvas
ready to edit and re-run. Phase 6 of the pipeline (see `pipeline-phases.md`)
codifies this.

## The flow

1. **Build canvas-format JSON.** Apply `workflow-authoring-style.md` (groups,
   Note nodes, sibling `.md` manual). Save to `output/<name>.canvas.json`.
2. **Push to userdata** with `mcp__comfy-cloud-proxy__upload_workflow_to_userdata`
   for persistence across sessions:
   ```
   upload_workflow_to_userdata(
     localPath="output/<name>.canvas.json",
     remotePath="<name>.json"  # root — subfolders don't auto-create
   )
   ```
3. **Open a new tab via Playwright MCP** on `https://cloud.comfy.org/`:
   ```
   mcp__playwright__browser_tabs(action="new", url="https://cloud.comfy.org/")
   ```
   Playwright's profile (`.playwright-profile/`) shares JWT auth with the
   user's Chrome session — the new tab lands logged in on the user's actual
   account, and the Playwright Chrome window is visible to them.
4. **Wait for app init.** Confirm `window.app`, `window.app.graph`, and
   `window.LiteGraph` are all defined. Body class is
   `litegraph grid dark-theme`. Usually 2–3 s after navigate.
5. **Inline the canvas JSON** into a `mcp__playwright__browser_evaluate`
   function body. Do NOT try to `fetch('/api/userdata/<name>.json')` from the
   browser — that endpoint accepts only `bearer_jwt` and `x_api_key`, returns
   403 `auth_type_not_allowed` on cookie auth.
6. **Load via the canonical API:**
   ```js
   await window.app.loadGraphData(data, true, true, '<name>');
   //                                   │     │     └─ workflow_name (becomes tab title)
   //                                   │     └────── restore_view (use extra.ds)
   //                                   └──────────── clean (replace existing canvas)
   ```
   Side effects: URL hash flips to a new workflow ID, page title becomes
   `*<name>` (asterisk = unsaved).
7. **Center the view manually.** `app.canvas.fitView()` does NOT exist on
   the Cloud build. Set:
   ```js
   app.canvas.ds.scale = 0.55;        // ~0.55 fits a 5-group graph
   app.canvas.ds.offset = [200, 200];  // tune to graph extents
   app.canvas.setDirty(true, true);    // force redraw
   ```
8. **Screenshot to verify** with `mcp__playwright__browser_take_screenshot`.
   Confirm group colors, node positions, edge wiring. If anything is off,
   fix the JSON and re-run `loadGraphData`.
9. **Tell the user** the canvas is live in the Playwright Chrome window and
   they need to hit **Save** in the top toolbar to persist as a named
   workflow (otherwise the `*` prefix stays and a refresh loses it).

## Why a separate Playwright Chrome is correct

Playwright runs in its own Chrome process. It cannot reach into the user's
already-open Chrome window — those tabs are inaccessible. However, the
Playwright window:
- Is visible to the user (not headless).
- Shares JWT auth via the persistent profile directory.
- Lands on the user's real Comfy Cloud account, so anything saved persists
  to their userdata and shows up in their original Chrome's Workflows panel
  on next refresh.

The user sees a new Chrome window opened by Playwright. That is the
intended behavior, not a bug.

## Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| `window.app` undefined | Page still loading | Wait 2–3 s after navigate, re-probe |
| `loadGraphData` not a function | Stale page (pre-app load, or old Comfy version) | Hard-reload tab, re-probe |
| 403 on `/api/userdata/...` from fetch | Cookie auth not accepted | Inline JSON in `browser_evaluate` body instead |
| Nodes load but no edges | Link tuple format wrong | Each link is `[id, from_node, from_slot, to_node, to_slot, type]` — ints + string |
| Notes don't render | Wrong type string | Use `"Note"` (not `"MarkdownNote"`) for plain text notes |
| Graph off-screen after load | `extra.ds` mismatch with canvas size | Set `canvas.ds.scale` + `ds.offset` manually + `setDirty(true, true)` |
| User says "no new tab opened" | Tab was opened in Playwright's own window, not their Chrome | Confirm Playwright Chrome window is foregrounded; explain it's a separate process sharing auth |

## When to skip Phase 6

- The user explicitly says "just the JSON" or "don't open my browser".
- The workflow is a one-off API submission with no expectation of further
  editing (rare — most Comfy Cloud work involves iteration).
- The Playwright MCP is unavailable. In that case, fall back to telling the
  user to open the Workflows panel in their own Chrome and load the
  userdata file pushed in step 2.
