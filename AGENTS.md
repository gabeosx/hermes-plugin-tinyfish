# Codex Project Shim

Some repositories use `.agents/` as the canonical home for agent instructions
and skills. This repository does.

## Canonical instruction source

The authoritative project instructions live at:

- `.agents/AGENTS.md`

Read that file before doing substantive work in this repository.

If this file and `.agents/AGENTS.md` appear to conflict, treat
`.agents/AGENTS.md` as the source of truth for project-specific policy,
workflow, conventions, and routing.

## Skill routing policy

This repository stores reusable project skills under:

- `.agents/skills/`

When a task appears to match a skill-based workflow, do not improvise from
scratch if a relevant skill exists. Instead:

1. Inspect the available skills under `.agents/skills/`.
2. Identify the best matching skill based on its folder name and `SKILL.md`
   metadata.
3. Read that skill's `SKILL.md`.
4. Follow the workflow, constraints, and deliverable format defined there.

Prefer the most specific matching skill over a general one.

If no skill is relevant, proceed normally using `.agents/AGENTS.md` and
repository conventions.
