# Growth protocol — pointer

This skill follows the shared **radon-skill-growth v1.0** protocol: a lightweight process for turning what is learned in real sessions into durable, reviewed skill knowledge. The shared protocol lives in a private repository; the same mechanic is documented publicly in [touch-designer-skill → `references/skill-growth-protocol.md`](https://github.com/niklazhallberg/touch-designer-skill/blob/main/references/skill-growth-protocol.md).

In short:

1. **Trigger** — a non-trivial problem got solved (several probe→fix cycles, reality contradicted the model, a non-obvious workaround).
2. **Generalize** — strip client names, project names and one-off numbers. If it can't be stated generically, it is project knowledge, not skill knowledge.
3. **Grade the source** — own empirical test (high confidence) vs. external source ("verify before relying") vs. both.
4. **Ask in flow** — propose the entry to the human; nothing is written without approval.
5. **Write + log** — the entry goes into the relevant `references/*.md` file and is prepended to `CHANGELOG.md` in the same commit.
6. **Consolidate** — periodically merge and prune entries (`scripts/session-sync-hook.sh` flags when it's time).

Candidates saved for later land in `SKILL-DISCOVERIES.md` at the repo root. Domain-specific examples and gotchas stay in this skill's own `references/` and `CHANGELOG.md`.
