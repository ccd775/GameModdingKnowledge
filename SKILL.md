---
name: game-modding-shared-knowledge
description: Use this skill when creating, repairing, auditing, packaging, or validating a game character or resource Mod for the six supported games in this repository.
metadata:
  short-description: Reproducible game Modding workflows and evidence contracts
---

# Game Modding Shared Knowledge Dispatcher

This is a compact dispatcher for systems that recognize `SKILL.md`. For a
multi-session project, use [`PLAYBOOK.md`](PLAYBOOK.md) as the primary guide;
it allows staged progress, pauses and resumption instead of forcing a single
rigid checklist. This folder contains no game binaries or private models.

## First Routing Step

Before editing anything, read:

1. [`references/AGENT_START.md`](references/AGENT_START.md)
2. The target game's [`README.md`](games/)
3. [`references/CORE_WORKFLOW.md`](references/CORE_WORKFLOW.md)
4. [`references/TOOLCHAIN_AND_SCRIPTS.md`](references/TOOLCHAIN_AND_SCRIPTS.md)
5. [`PLAYBOOK.md`](PLAYBOOK.md)
6. The target game's detailed SOP, validation and troubleshooting documents

Copy [`templates/PROJECT_STATE.md`](templates/PROJECT_STATE.md) and
[`templates/source-lock.json`](templates/source-lock.json) into the new project
before authoring. Never use this root document as a live candidate state file.

## Routing

- Hitman: World of Assassination -> `games/hitman-world-of-assassination/`
- Watch Dogs -> `games/watch-dogs/`
- Assassin's Creed IV: Black Flag Resynced -> `games/assassins-creed-black-flag/`
- Resident Evil 4 Remake -> `games/resident-evil-4-remake/`
- Left 4 Dead 2 -> `games/left-4-dead-2/`
- Helldivers 2 -> `games/helldivers-2/`

Use a game's detailed documents only after routing. Do not transfer a resource
path, bone count, threshold, archive index, material ID, or transform from one
game or build to another without fresh evidence.

## Minimum Invariants

- Record user scope, current build, tools, source/reference identity and hashes
  before any irreversible transformation.
- Keep geometry, bind/rest, weights, materials, resource references, packaging
  and runtime behavior distinguishable in the project state.
- Prefer attributable candidates and preserve rejected evidence.
- Re-import/decode outputs before release and state evidence as
  `reference-inferred`, `offline-accepted`, `runtime-load-pass`,
  `runtime-rejected`, or `runtime-confirmed`.
- Do not publish private models, reference Mod payloads, game assets, absolute
  paths, credentials, or a release ZIP. Run the public-tree validator before a
  commit.

## Tools

Use [`references/TOOLCHAIN_AND_SCRIPTS.md`](references/TOOLCHAIN_AND_SCRIPTS.md)
to choose tools by game and responsibility. Use the included scripts for
project initialization, hashes, and publication checks. Game-specific converters
and GUI tools must be installed or supplied by the user; this skill does not
pretend that a generic script can replace them.

Read [`references/CAPABILITY_GAPS.md`](references/CAPABILITY_GAPS.md) before
claiming that a task is buildable or runtime-ready.
