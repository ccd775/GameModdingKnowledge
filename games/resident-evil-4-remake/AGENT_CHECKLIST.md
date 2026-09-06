# Agent Checklist

> Status: active
> Scope: compact start, build, release, and resume gate
> Last verified: 2026-08-07

Use this checklist after reading the relevant detailed documents. A checked box
means there is evidence, not merely that the step was considered.

## New Task

- [ ] Read SharedKnowledge entry, then the project `AGENTS.md` and full project
  `SOP.md`, newest exact-candidate runtime reports, then the evidence model and
  relevant shared topic pages.
- [ ] Record the user's target, inclusions, exclusions, quality bar, and whether
  game launch/install is authorized.
- [ ] Inspect license/privacy metadata and redistribution constraints.
- [ ] Lock source FBX/Blend/VRM/textures, reference Mod, executable, manifest,
  PAK set/indexes, path dictionary, tools, add-ons, and schemas.
- [ ] Detect current build and process state; do not assume an earlier snapshot.
- [ ] Create project workspace and keep all inputs read-only.

## Discovery

- [ ] Merge current official archives in discovered load priority.
- [ ] Extract and verify current target Mesh/MDF/TEX/Chain/PFB/JCNS/JMAP/
  FBXSKEL/skeleton resources.
- [ ] Parse current PFB dependencies and record missing probes explicitly.
- [ ] Build a consumer matrix for default, alternate, cutscene, mode, face,
  hair, auxiliary, and suppressor consumers.
- [ ] Treat chapter/Figure/variant naming as provisional; update ownership from
  time-correlated PFB/Mesh/MDF runtime hits when a late transition exposes a
  different consumer.
- [ ] Exclude unrelated reference payloads.
- [ ] Prove a known-good donor/control when runtime work is authorized.
- [ ] Run import/export/re-import identity tests with pinned tools.

## Source And Rig

- [ ] Inventory objects, topology, UV layer names/positional order and material
  intent, materials, bones, parents, matrices, weights, shape keys, saved
  values, VRM groups, and colliders.
- [ ] Saved-state coverage names every retained object and exact non-Basis
  key/value set; affected vertices, maximum displacement, bake result, and a
  known omitted-bake negative control are recorded when a nonzero bake is
  required.
- [ ] Count valid and unbound source primitive material indices; record actual
  base/emissive factors, textures, and shader-node connectivity.
- [ ] Audit every source representation; record where optimized Blend/FBX/VRM
  semantics differ and which source is authoritative for each field.
- [ ] Record exact case-sensitive object membership and variant-specific
  keep/delete intent; equal topology does not replace evaluated visibility and
  body-clearance checks.
- [ ] Partition by target consumer.
- [ ] Record explicit core-bone map and all collapse rules.
- [ ] Select source-proportion, donor-proportion, or bounded-local-correction
  strategy and apply each scale/translation exactly once.
- [ ] Representative target-native translation poses preserve the declared
  proportion contract; a correct static pose alone is not accepted.
- [ ] Clear unintended Armature object parents and stale
  `matrix_parent_inverse`; retain one intended modifier and verify normalized
  object/world placement independently of final binary equality.
- [ ] Preserve full parent closure for weights, Chain, colliders, JCNS, and
  control bones.
- [ ] Enforce project influence limit, normalization, and no unweighted vertices.
- [ ] Bake required saved shape-key state before deleting keys.
- [ ] Move each attachment/local correction as a coherent geometry/rest-bone
  package.
- [ ] Short articulated chains pass per-joint geometry-to-animation-pivot audits
  and target-specific action poses; bounded prefits leave target rest bones and
  unrelated geometry frozen.
- [ ] For connected clothing spanning multiple limbs, declare semantic segments
  and prove each segment's static transfers, physical rest bones, and target
  parents use the intended frame while cross-segment weights remain normalized.
- [ ] Separate saved foot shape, foot-to-shoe fit, sole/rest-package
  orientation, and shoe-to-floor placement; do not use foot-bone angle as a
  sole-plane proxy.
- [ ] Rigid shoe/cuff/strap/accessory shells use proved compatible pivots or one
  coherent rigid bind with explicit lost articulation; no unrelated many-to-one
  bone collapse is hidden as a motion feature.
- [ ] Keep core animation bones and unrelated variables frozen unless explicitly
  changed.

## Mesh

- [ ] Visibility groups come from target semantics, not source object order.
- [ ] Group/submesh strategy respects vertex/index and visibility limits.
- [ ] Final Mesh material table/order is canonical for MDF construction.
- [ ] Re-import verifies topology, material triangles, UV, weights, bone
  names/parents/matrices, bounds, and versions.
- [ ] Source material UV intent closes through authoring positional layer order
  to the serialized runtime-sampled stream; generated-Mesh self-round-trip is
  not the only UV proof.
- [ ] Every positive influence passes absolute vertex-to-pivot and posed-bounds
  checks; comparison coverage is non-empty and complete.
- [ ] Weighted shared-FBXSKEL and proven Mesh-local bones are classified; shared
  slots close on the declared FBXSKEL set and a negative control fails.
- [ ] Dependent FBXSKEL is generated twice from final Mesh state; bytes and
  serialized semantics match, or a current-native byte-copy is explicitly
  proven by exact shared-core closure and Mesh-local extra classification;
  later shared Mesh rest/order changes invalidate either decision.
- [ ] Independent source fidelity audit recomputes saved-state geometry from
  locked inputs; triangle multisets are required only for topology-preserving
  work, with declared surface/silhouette gates for retopology.
- [ ] Neutral, extreme, and consumer-specific exposing poses pass, including
  weapon grips for finger work and native translation poses for proportion work.
- [ ] Focused geometry gates cover feet, neck/tail, visor/hair, attachments, or
  other reported issues.
- [ ] Flat-footwear gates measure the actual exported low-contact plane tilt,
  front/back height delta, fit residual/coverage, and per-side independent floor
  residual; one minimum-Z contact point is insufficient.
- [ ] Two clean builds are byte-identical.

## Materials

- [ ] Packed channel semantics are documented from source evidence.
- [ ] MDF array exactly matches the final Mesh material table, or a current-
  build explicit name/index remap is proved and recorded.
- [ ] Every submesh material index resolves correctly.
- [ ] PFB/RSZ gameplay material/property queries are inventoried, including
  names with no visible source triangles.
- [ ] Query sets are derived per consumer rather than copied from a passing
  route, and every existing/requested MDF alias closes with the paired Mesh.
- [ ] Any material index reused across Mesh/MDF/renderer arrays resolves to the
  same intended material; count/set equality alone is not accepted.
- [ ] Query-only compatibility materials have consumer-proven non-degenerate
  hidden backing submeshes when required, and visible submeshes, vertex layout,
  rig/remap, and per-bone bounds remain unchanged.
- [ ] Every source primitive has an authored material or an explicit intentional
  fallback/override; importer-created default slots are not accepted silently.
- [ ] Every final triangle closes from source material through texture page and
  render class.
- [ ] UV provenance is recorded; any sibling-source recovery is unique,
  per-loop, and leaves non-target UV hashes unchanged.
- [ ] Cutout and continuous transparency are separated where necessary.
- [ ] Geometry clearance and transparent draw order are tested separately.
- [ ] TEX dimensions, mips, formats, and sRGB/linear semantics are correct.
- [ ] Every generated TEX decodes and passes all-channel comparison.
- [ ] No unexpected custom complete TEX exists in loose streaming.
- [ ] Two material builds are byte-identical.

## Preview

- [ ] Preview binds final Mesh/MDF/TEX hashes and decodes final TEX channels.
- [ ] Required overview and focused views are in frame and materially valid.
- [ ] Clearance/contact planes come from independent target or scene evidence,
  not candidate minimum bounds.
- [ ] Offline preview claims exclude animation, IK, engine rendering, routing,
  and world-ground contact.

## Physics

- [ ] VRM/source physics is treated as semantic input, not direct parameter copy.
- [ ] Fixed weighted attachment anchors, actual dynamic roots, weighted
  endpoints, and terminal/dummy nodes are classified per branch from source and
  final-Mesh evidence.
- [ ] Ordered unique positive target count preserves the declared source deform
  intervals; every many-to-one collapse and unsupported visible span is audited.
- [ ] No missing terminal/collider/ancestor or repeated driven path.
- [ ] Collider units/transforms are explicit; every serialized local offset is
  scale-plausible and reconstructs the intended final world center, and a known
  unit-defective control fails.
- [ ] Frames are rebuilt from final rest directions and pass angular checks; an
  inherited-frame negative control fails when rest directions changed.
- [ ] Topology/frame issues are solved before parameter tuning.
- [ ] Gravity/droop and collision are separate candidates.
- [ ] Every route uses its verified current Chain donor/header.
- [ ] All Chains re-import, semantic-diff, frame-audit, and build twice.
- [ ] Any runtime-rejected static branch fallback matches every path node after
  segmentation, leaves zero branch survivors in every route, preserves proven
  Mesh/FBXSKEL hierarchy, and declares lost motion.

## PFB And Controls

- [ ] PFB/RSZ patch starts from the current build and locked schema.
- [ ] Input/output parse to EOF.
- [ ] Byte diff and semantic diff contain only declared fields.
- [ ] Redirected dependencies match across PFB resource-table strings and RSZ
  component fields with exact occurrence counts and package closure.
- [ ] Related JCNS/GPUC/GPU Cloth components are audited independently.
- [ ] Shared skeleton blast radius is resolved; character-scoped paths preferred.
- [ ] Static face limitations are explicit; incompatible JMAP/JCNS not copied.
- [ ] Suppressors are minimal and consumer-scoped.

## Candidate And Offline Acceptance

- [ ] Candidate is a complete tree with one declared semantic variable.
- [ ] Parent is a matched cumulative baseline.
- [ ] Exact path/size/hash diff matches the declaration.
- [ ] Every path outside the declared variable is asserted byte-identical to a
  matched accepted baseline.
- [ ] The superseded/rejected parent is a negative control and fails the new
  candidate-specific policy gate.
- [ ] Rejected hypotheses are recorded narrowly and retained.
- [ ] Cumulative candidate is rebuilt from canonical source, not layered from
  stale candidates.
- [ ] All binary reports bind to actual artifact hashes.
- [ ] Resource map covers every path and forbidden resources are absent.
- [ ] Two full candidate builds match.

## Package

- [ ] Canonical release entry point enforces the selected mutation boundary:
  project-local offline work may proceed when authorized, while install,
  game-tree, manager, and runtime phases block conflicting processes; it never
  terminates user processes.
- [ ] Nested tool wrappers throw on native failure and return normally on
  success; a child `exit` cannot skip downstream release phases.
- [ ] Package is built from the accepted manifest.
- [ ] Root contains `modinfo.ini`, documentation, manifest, and `natives/`
  without an accidental wrapper directory.
- [ ] Entry path/order/timestamp/compression policy is deterministic.
- [ ] Two package builds are byte-identical or payload authority is explicitly
  documented.
- [ ] Clean re-extraction exactly matches staging.
- [ ] Build support, routes, conflicts, limitations, license, and evidence level
  are documented.
- [ ] Mutually exclusive Normal/Thin or other same-path variants are documented
  and cannot be enabled together.
- [ ] Package creation did not upgrade offline evidence to runtime evidence.

## Runtime, Only If Authorized

- [ ] Deployment owner is explicit: external script with game/Fluffy closed, or
  Fluffy as the sole writer with game closed and no concurrent external writes.
- [ ] Fluffy is closed before independent post-operation tree audit and game
  launch.
- [ ] The enabled entry owns the expected non-zero deployed-file set and sampled
  live target hashes match; an enabled zero-file entry is not payload evidence.
- [ ] External-script preflight has no same-path conflict, or the Fluffy-managed
  conflict/priority decision is explicit before Fluffy rebuilds its tree.
- [ ] Install transaction owns only paths it created.
- [ ] Every candidate switch uses a cold start.
- [ ] Logs and user feedback bind to candidate/build/route/costume/scenario.
- [ ] A crash-fix regression verifies both the former fault boundary and the
  first fully rendered state; “no crash” is not recorded as a visual pass.
- [ ] If one blocker becomes another, preserve the earlier positive observation,
  reject the candidate for the new blocker, and trace repaired outputs into the
  next consumer before changing unrelated resources.
- [ ] Visual left/right or cross-body wording remains an observation until an
  explicit source-branch membership test establishes directional identity.
- [ ] A short explicit acceptance records its task-context package binding and
  leaves unreported matrix fields as `not-observed`.
- [ ] Foot-to-shoe fit and shoe-to-world contact are tested as separate gates.
- [ ] Default and alternate consumers are tested separately.
- [ ] Late cutscene/boss/event phase transitions have independent rows and
  route-hit evidence; an earlier encounter pass is not reused as their result.
- [ ] Any read-only installed-tree acceptance snapshot persists per-path
  expected/actual sizes and hashes, not only an aggregate exact-count claim.
- [ ] Rollback preserves non-candidate files and passes four-way audit.

## Pause Or Handoff

- [ ] Project SOP contains the latest superseding milestone.
- [ ] A newer SHA-bound runtime rejection is reflected immediately; no rejected
  archive remains described as current, accepted, or merely pending.
- [ ] A newer candidate-bound runtime acceptance is reflected immediately; the
  accepted package is no longer described as untested, and its scope is not
  broadened beyond reported scenarios.
- [ ] Runtime reports stay outside the immutable tested archive; documentation
  updates do not silently create a new untested ZIP hash.
- [ ] Current evidence level, candidate, manifest, completed gates, rejected
  hypotheses, limitations, next variable, and resume commands are explicit.
- [ ] Runtime state is recorded as exact transaction evidence or `not installed`.
- [ ] SharedKnowledge receives only genuinely reusable lessons, with case values
  left in the case study/project.
