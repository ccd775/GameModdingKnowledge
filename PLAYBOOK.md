# Long-Running Modding Playbook

Use this document as the main operating model for multi-day or multi-week Mod
projects. It is deliberately less rigid than a normal Skill: the agent records
the current phase, chooses the next useful action, pauses when an external
dependency or user test is needed, and resumes from project state later.

## Operating loop

```text
understand request
  -> inventory files/tools/build
  -> write project state and source lock
  -> select target consumer and reference contract
  -> make a small candidate
  -> audit and compare
  -> package or pause
  -> request/record runtime feedback
  -> revise the next single variable
```

The arrows are a preferred rhythm, not a requirement to finish every phase in
one session. A pause is successful when another agent can read `PROJECT_STATE.md`
and continue without reconstructing hidden context.

## Decisions the agent should make explicitly

- What is known from current files, what is inferred from a reference, and what
  is still a hypothesis?
- Which tool or script owns the next transformation?
- Which inputs must remain immutable?
- What is the smallest candidate that can distinguish two competing causes?
- Is the next action offline, deployment, or runtime, and is that action
  authorized?
- What evidence will promote, reject, or defer the candidate?

## State writing

At the end of each meaningful stage update:

- `PROJECT_STATE.md`: current phase, candidate, accepted/rejected gates, next
  action and known limits;
- `source-lock.json`: inputs/tools and hashes;
- `Work/reports/`: machine-readable reports and logs;
- `Output/`: only candidates that passed their declared offline gates;
- `reports/runtime/`: user observations bound to installed hashes.

Do not turn old prose into a new result silently. Append a dated milestone and
link the report that supersedes it.

## When to pause

Pause and explain the missing dependency when the target build is unknown, a
required tool is unavailable, a private asset lacks redistribution permission,
the user has not authorized deployment/runtime testing, or a runtime failure
cannot be isolated to a responsible contract. Continue with read-only
inventory, documentation, and synthetic tests while waiting when possible.

## Game routing

Use the selected `games/*/AGENTS.md` for the relevant reading order. The root
`SKILL.md` is only a compact dispatcher for systems that recognize Skill files;
the Playbook is the preferred guide for long-running work.

Historical project instructions describe their original context. Current user
requirements and permissions take precedence; do not re-request authorization
already given in the conversation. A copied mandatory checklist is not a reason
to stop unrelated useful work or to restart every phase on each resume.
