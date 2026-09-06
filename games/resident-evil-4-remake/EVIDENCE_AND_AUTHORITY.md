# Evidence And Authority

> Status: active
> Scope: reusable evidence model for RE4 Mod projects
> Last verified: 2026-08-07
> Applies to build: all; concrete resource facts remain build-sensitive

## Why This Exists

RE4 character replacement failures often survive because a correct observation
is promoted into an overbroad conclusion. Examples include treating a load pass
as visual confirmation, treating one fixed visibility group as the cause of a
hang, or treating an old donor PFB as current-build authority.

The evidence model keeps observations narrow enough to remain useful.

## Evidence Levels

### `reference-inferred`

Use when a claim comes from:

- a reference Mod;
- a different character or prior project;
- a source VRM/FBX/Blend semantic;
- a community guide or tool description;
- a current native resource whose consumer role has not yet been proven.

Required record: source identity/hash, inferred claim, uncertainty, and the
next test that can promote or reject it.

### `offline-accepted`

First record the `claim_scope`, `artifact_kind`, and `applicable_gates`. Use
`offline-accepted` only when every gate applicable to that scope passes. Typical
resource/candidate gates include:

- correct magic/version and parser acceptance;
- export/re-import semantic comparison;
- numeric geometry, rig, weight, UV, topology, and material checks as applicable;
- Chain/PFB semantic field checks as applicable;
- complete path/size/SHA-256 manifest;
- a relevant reproducibility check, such as two clean deterministic builds or
  an independent extraction/verifier agreement;
- explicit confirmation that no runtime test was performed when that is the
  user's boundary.

Package re-extraction is mandatory only when the claim scope is a deployable
package. A phase-0 inventory or current-native extraction can be
`offline-accepted` after its own declared gates pass even though no Mesh or ZIP
exists. Offline acceptance proves internal consistency within its stated scope;
it does not automatically prove deployability of a later phase, appearance,
animation, IK, physics, lighting, or load behavior.

### `runtime-load-pass`

Use when the user cold-starts a named candidate and reaches gameplay. Record:

- game build and platform;
- candidate ID and archive or payload manifest digest;
- exact route, chapter, costume, and entry point;
- cold-start condition;
- candidate identity proven by resource-hit logs or an equivalent exact
  package/install-tree manifest and hash record;
- whether appearance and physics were evaluated or remain unknown.

A load pass disproves “this exact tested tree always blocks loading” but does not
prove the Mod is visually correct.

### `runtime-rejected`

Use when runtime evidence bound to an exact candidate finds a blocking defect.
Record the same identity and scenario fields as `runtime-load-pass`, plus the
blocking symptom, screenshot/log identity, positive observations that narrow
the fault, and the next single-variable hypothesis if one exists.

Runtime rejection is candidate-level and fail-closed: stop promotion even if
the project SOP still says the candidate is waiting for a test. It does not
erase independently accepted offline resource contracts. It also does not turn
a narrow positive observation into full runtime confirmation. For example, one
shop close-up may show coherent material pages and no skinning explosion while
leaving other animations, routes, lighting, and IK untested.

### `runtime-confirmed`

Use only when user evidence is bound to:

- candidate ID and hashes;
- current build;
- all consumer routes and costumes required by the declared claim scope;
- the actions, poses, cutscenes, lighting, wetness/dirt, and physics states in
  that scope's test matrix;
- a cold start after candidate switching;
- screenshots, logs, or an explicit user observation record.

Confirmation is scoped. “Default costume in chapter 7 looks correct” can confirm
that declared component/scenario but does not confirm an alternate costume,
Mercenaries route, cutscene, full package, or a different build.

When the user explicitly accepts a package immediately after one unique handoff
that named its path and SHA-256, the task context may bind that acceptance even
if the user does not repeat the hash. Record the binding method and the missing
hash repetition as a qualification. This can confirm the explicit package-
acceptance scope, but route, action, cold-start, lighting, conflict, screenshot,
and rollback fields remain `not-observed` unless the user actually reports them.

### `rejected`

Use when evidence disproves either a candidate or a sufficiency claim. State the
narrow proposition that failed:

```text
Rejected: disabling GpuCloth.Enabled alone fixes the Ashley load hang.
Not rejected: GPU Cloth or another component may participate in the full issue.
```

Preserve rejected hypotheses. They prevent future agents from cycling through
the same unproductive candidate.

Use `runtime-rejected` as the candidate's evidence level when the blocker was
observed at runtime. Keep `rejected` on each narrow sufficiency claim so later
work knows exactly what was disproved without overgeneralizing the failure.

## Fact Classification

Evidence level describes how well a claim is tested. Fact class describes how
far it may be reused.

| Class | Typical examples |
| --- | --- |
| `invariant` | Hash all inputs; re-import generated binaries; do not call offline evidence runtime-confirmed |
| `build-sensitive` | Resource suffixes, PFB layout/offset, archive priority, consumer dependency closure |
| `case-derived` | `Group_0` policy for one replacement, one transparency floor, one Chain tuning set |
| `hypothesis` | A proposed attachment anchor or material sort change before acceptance |
| `rejected` | A tested single-variable claim that failed in a named candidate |

A highly tested case value can still be `case-derived`. Runtime confirmation
does not turn a character-specific transform into a universal rule.

## Authority Order

For authorization, scope, stop conditions, and selection of the current
milestone:

1. Current user instructions
2. Current project `AGENTS.md` and latest non-superseded SOP milestone
3. Shared contracts in this directory

For concrete artifact facts within the selected milestone:

1. The exact candidate's SHA-bound machine reports
2. The current installed build's official resources and dependency graph
3. The source model/VRM for authored appearance and saved state
4. The reference Mod within its documented donor/control role
5. Case-study observations, community guidance, and memory

Project prose identifies which milestone and reports are current. Once selected,
the bound report determines its paths, hashes, counts, and measurements. A
reference Mod may connect source and target roles but replaces neither authority.
A newer exact-candidate runtime rejection takes fail-closed precedence over an
older prose status until that status is synchronized.

## Required Evidence Record

For any promoted candidate or important conclusion, record at least:

```yaml
claim_id: stable-project-local-id
date_utc: ISO-8601
claim_scope: inventory | extraction | resource | candidate | package | runtime
artifact_kind: report | mesh | material | chain | pfb | tree | archive | observation
applicable_gates: []
fact_class: invariant | build-sensitive | case-derived | hypothesis | rejected
evidence_level: reference-inferred | offline-accepted | runtime-load-pass | runtime-rejected | runtime-confirmed | rejected
game_build_id: value-or-not-applicable
tool_versions: exact versions and hashes
candidate_id: value-or-not-applicable
candidate_manifest_sha256: value-or-not-applicable
scope:
  routes: []
  costumes: []
  resources: []
  scenarios: []
inputs:
  - path
  - size
  - sha256
outputs:
  - path
  - size
  - sha256
checks:
  - machine-readable check and result
observation: concise result
limitations: what this result does not prove
sources:
  - script/report/screenshot/user-feedback path
supersedes: prior claim id or null
```

Machine reports should be self-describing and bind both the inputs they audited
and the outputs they accepted. A report that merely says `accepted=true` but
does not identify the candidate bytes is not a durable gate.

`accepted=true` is also insufficient when an applicable semantic gate was never
implemented. Record the declared gate set and coverage counts so a report cannot
silently accept zero comparisons or omit source-material, bind-space, or route
closure while still appearing successful.

## Supersession

Project SOPs are often cumulative and preserve old commands or hashes. Apply
these rules:

- New milestones state exactly which earlier fields they supersede.
- Older values remain historical evidence and are not silently rewritten.
- A current-state reader starts at the newest milestone, then follows its
  retained dependencies backward.
- “Current ZIP,” “current candidate,” and install-tree counts live only in the
  target project, not in generic shared contracts.
- If a case summary cites a current value, it includes the date, build, and
  project evidence path.
- A newer exact-candidate runtime rejection appends a superseding state record;
  it does not rewrite or delete the offline reports that describe narrower
  resource/package gates.

## Matched Baselines

A single-variable claim requires two trees that differ only in that variable.
This is especially important for cumulative projects.

If a new high-heel candidate is compared against an old baseline that also lacks
new visor and attachment fixes, the diff is not high-heel-only. The correct
response is to build a matched baseline containing every cumulative change
except the variable under test. A gate should fail when the baseline is stale.

Assert both sides of the diff: the exact changed path set and the complete
unchanged path/size/hash set. This catches incidental rebuild drift even when
the declared variable and its intended outputs are correct. The DR03 Merchant
backpack fix is the reference case: two body-route Chain resources changed while
21 other runtime resources were required to remain byte-identical.

## Runtime Reports And User Feedback

Translate user feedback into a record before changing files:

1. Name the tested package/candidate and hash.
2. Record route, costume, chapter, pose/action, camera view, and cold start.
3. Separate distinct symptoms by layer: static geometry, dynamic physics,
   transparency, draw order, routing, or load behavior.
4. Preserve screenshots and logs under the project evidence directory.
5. Form one or more narrow hypotheses and build isolated candidates.

A runtime-rejected candidate can still contain a newly proven narrow positive
observation. When an exact candidate advances past a former crash boundary but
then exposes a new blocking visual or behavioral defect, preserve the advanced
boundary as positive evidence and reject the candidate for the new blocker.
Do not flatten the sequence into either “the fix failed completely” or “the
candidate passed.” Trace the repaired value into its next consumer; symptom
progression can establish that a prior change was active without proving the
whole dependency closure.

Before treating a native-character screenshot as a payload rejection, record
whether the Mod Manager actually deployed a non-zero file set and whether the
expected target paths/hashes were present. An enabled entry with zero installed
files is a deployment incident. It can reject that installation attempt, but it
does not reject the packaged Mesh, PFB, materials, or Chain.

Keep observation vocabulary separate from implementation identity. A user can
reliably report that a visual side is compressed, inflated, or appears to cross
the body without proving which named mirrored source-bone branch moved. Record
the camera/view wording verbatim, then use explicit branch membership and a
matched candidate before promoting a directional source-branch claim. If later
evidence corrects only that interpretation while preserving the broader causal
layer, supersede the narrow claim rather than discarding the valid diagnosis.

After an explicit acceptance, create the same candidate-bound record and update
the project SOP immediately. Preserve scenario fields the user did not enumerate
as `not-observed`; acceptance is not permission to backfill an idealized test
matrix.

When live-tree inspection is authorized as read-only evidence, persist the
per-path expected/actual size and SHA-256 rows in the feedback report. An
aggregate `N/N` statement is useful corroboration but cannot later prove which
paths were checked after the user-managed tree changes. The snapshot remains
point-in-time evidence and does not authorize installation or removal. This is
an `invariant` recording rule derived from the contrast between the Krauser r9
aggregate observation and the r11
[`acceptance recorder`](../../SOURCE_REFERENCES.md#local-only),
[`machine report`](../../SOURCE_REFERENCES.md#local-only),
and [project snapshot](../../SOURCE_REFERENCES.md#local-only).

If several archives were handed off together, do not silently bind a short
acceptance to all of them. Use the continuous defect/retest context to scope the
binding only when it identifies one variant clearly, document that
qualification, and leave the other archives `not-observed`. Otherwise record
the acceptance with unresolved candidate identity and request clarification
before promotion.

Do not rewrite and repackage the tested archive to embed its new runtime status.
That produces a different hash with no runtime evidence. Runtime reports and SOP
supersession records remain external to the immutable tested package.

Record unobserved cold-start, install-conflict, route, or process state as
`not observed`; do not infer it from a screenshot. A visible blocking defect can
still reject the exact candidate, but positive conclusions must remain scoped
to what the observation actually shows. Likewise, an offline local-geometry
preview can prove foot-to-shoe fit without proving contact against the runtime
world floor.

If the user cannot identify the exact package, classify the observation as
useful runtime feedback with unresolved candidate identity, not as a promoted
runtime-confirmed baseline.

## Licensing And Privacy Evidence

Input locking also records authorization constraints. Keep:

- model/VRM license metadata and permitted use;
- whether redistribution, commercial use, violence, or modification is allowed;
- reference-Mod source and local-only status;
- hashes sufficient to prove which private input was used.

Do not move private payloads into SharedKnowledge. A shared lesson needs only a
description and a link to the authorized project-local evidence.
