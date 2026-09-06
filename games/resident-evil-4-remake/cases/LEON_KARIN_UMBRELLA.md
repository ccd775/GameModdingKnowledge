# Case Study: Karin Umbrella Replaces Leon

> Status: v7 accepted by the user for the delivered task scope
> Project: `RE4/Karin_Umbrella_Replace_Leon`
> Snapshot date: 2026-08-07
> Game build: Steam `22377325`
> Evidence level: offline gates accepted; the exact v7 PAK is
> `runtime-confirmed` for the stated user-acceptance scope
> Reuse class: mixed invariant, case-derived, rejected, and build-sensitive;
> every route, bone name, mapping, count, parameter, and hash below is a case
> value unless explicitly classified otherwise

## Scope And Accepted Result

This project replaced Leon in the declared campaign and Mercenaries consumers
with the supplied optimized Karin Umbrella Blend. Its sibling VRM supplied
VRChat spring hierarchy and collider semantics. A private Leon replacement Mod
was a path, structure, and known-loading reference only; current build resources
and project-local reports remained the authority for consumer and binary facts.

The accepted package is:

```text
Dist/Karin_Umbrella_Replace_Leon_Private_v7_HAIR_FIX.pak
Size 410,582,905 bytes
SHA-256 D8B6D7BA200EBA4AA5624C3D343F7D47DDFF52CD4B738E6F9341BD834FA38648
112 entries
Stage-manifest SHA-256 89254845A8BEDC5F63DE57F8718A2AD4F453005C185F5BE7F0C1CE230B2C08AF
```

The user's final statement, immediately following the unique v7 handoff, was
recorded as scoped task acceptance. It confirms the reported central-bang and
twin-tail authored-shape repairs and carries forward the explicitly confirmed
v6 finger, twin-tail-root, and tail-curvature repairs. It does not invent a
route, chapter, costume, cold-start, pose, lighting, conflict, long-session, or
installed-tree matrix. Those fields remain `not-observed`.

The tested PAK was not repacked after acceptance. Runtime status lives in an
external report so the exact tested bytes remain immutable.

Authoritative state and evidence:

- [`SOP.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`release-v7-hair-fix.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v7-runtime-acceptance-20260807.json`](../../../SOURCE_REFERENCES.md#local-only)

## Candidate And Runtime Timeline

| Candidate | Exact observed result | Durable conclusion |
| --- | --- | --- |
| v1 | Eyes converged; central fringe pointed upward; upper body stretched; tail twisted upward; both twin tails twisted along their length; feet appeared on tiptoe | Per-bone donor-directional conformance, incompatible active face pivots, and collapsed physical paths could all be wrong while files still parsed |
| v2 stable | A cuff strap segment stood upward; the shoe toe looked split; the abdomen still stretched; hair, ears, and tail were rigid | Moving target core rest landmarks to the source did not preserve proportions under native animation; unrelated chain collapse and blanket static fallbacks traded deformation for lost motion |
| v3 motion | Offline-only and superseded before runtime | An untested intermediate is not runtime evidence and should not replace the last tested negative control |
| v4 motion | Hair flew rapidly above the head; ears embedded into the head; sneaker silhouette remained wrong | Reconstructed rest bones with inherited Chain node frames were invalid; endpoint policy and saved footwear state also needed independent audits |
| v5 controlled motion | Weapon-grip fingers twisted severely; twin-tail attachment segments kinked upward; tail showed stepped corners | Neutral-pose success did not prove small-joint pivot compatibility; the first weighted attachment segment was not necessarily a dynamic root; deform-chain density mattered before tuning |
| v6 deformation fix | The user confirmed the finger, twin-tail-root, and tail-curvature defects were solved; central fringe still pointed upward and twin-tail authored shape looked unbaked | Preserve accepted subcontracts from a rejected cumulative candidate; inspect retained-object saved state and the central-fringe root separately |
| v7 hair fix | User accepted the task | Baking the locked hair saved state and correcting the central-fringe fixed-root topology completed the reported scope |

Every rejection is a scoped negative control, not disposable history. In
particular, v6 remained the negative control for the v7 hair bake and central
fringe topology while its finger, twin-tail-root, and tail repairs remained
positive evidence.

Evidence:

- [`v1-runtime-rejection-20260806.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v2-runtime-rejection-20260806.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v4-runtime-rejection-20260806.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v5-runtime-rejection-20260807.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v6-runtime-feedback-20260807.json`](../../../SOURCE_REFERENCES.md#local-only)

## Geometry Proportions Versus Animation Rest

`case-derived` repair supporting an `invariant` separation rule:

Source silhouette and target animation compatibility are separate contracts.
v1 projected source geometry through per-bone donor directions. That made local
anchors individually plausible but visibly stretched the authored torso and
appendages. v2 moved Leon core rest heads toward source landmarks. Static
placement improved, but Leon animation translations were authored for Leon's
rest intervals and re-extended the shorter Karin abdomen at runtime.

The accepted line used a hybrid contract:

1. retain exact Leon core-animation rest transforms;
2. place the visible source geometry through one measured global source frame;
3. keep physical and attachment rest branches coherent with that geometry;
4. introduce a bounded local geometry prefit only where a measured animation
   pivot mismatch requires it;
5. freeze the target animation skeleton during that local correction.

This is not a universal instruction to always preserve the donor rest. It is a
reusable decision framework: choose which side owns animation rest, which side
owns visible proportions, and where an explicit local compatibility layer is
allowed. Test runtime translation as well as rotation. A static T-pose cannot
prove that native animation deltas will preserve source body lengths.

## Small-Joint Pivots Need Action-Specific Proof

`invariant` validation lesson with case-derived measurements:

The v5 hands looked plausible in neutral previews but failed during firearm
grips. Across 30 mapped phalanges, source geometry pivots differed from the
preserved Leon pivots by a mean of about `41.03 mm` and a maximum of about
`58.92 mm`. Rotations around those remote pivots twisted fingers even though
weights were normalized and the Leon rest skeleton itself was exact.

v6 retained the Leon finger bones and prefitted only vertices weighted to each
finger through deterministic per-phalanx rest transforms. Representative
weapon-hand poses then became the relevant gate. The values and exact transform
implementation belong to this case; the reusable method is:

- audit every positive small-joint influence against the pivot that will
  actually animate it;
- report coverage, mean/max residual, and a known-bad predecessor;
- preserve the animation skeleton when it is the compatibility authority;
- correct only the bounded weighted geometry when a local prefit is selected;
- validate the actions that expose the joint, such as aim, grip, trigger, and
  support-hand poses, not only neutral or generic extreme poses.

Evidence:

- [`v5-runtime-deformation-audit-20260807.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`deformation-contract-v6-deformation.json`](../../../SOURCE_REFERENCES.md#local-only)

## Static Face Is A Product Contract

`case-derived` product decision:

The source did not provide a proved Leon-compatible eye, expression, look-at,
lip-sync, JMAP, or JCNS contract. Keeping incompatible active eye pivots caused
the v1 converged-eye result. The project therefore transferred the visible face
and eyes through one static Head-space contract and retained only compatibility
structure required by the consumer.

This avoided incompatible eye rotations, but it does not create blinking,
look-at, lip sync, or expressions. Static face transfer is a deliberate feature
boundary, not a complete facial-animation solution. It must be disclosed and
tested for overlap, normals, and head-space coherence.

## Rigid Shells, Saved Shape, And Ground Contact Are Different

The v2 cuff mapped 11 source strap bones into five unrelated target Cloth
targets. The compressed branch could not preserve the strap's authored local
shape and one segment lifted away. The shoe toe was similarly allowed to follow
Leon Toe pivots that did not match the source sneaker shell, so animation split
the front of the rigid shoe.

The stable repairs rigidized those art packages under coherent parent anchors
instead of forcing unsupported articulation. This knowingly removes independent
strap or toe motion. It does not solve two other footwear contracts:

- the source sneaker's saved shape must be evaluated and baked;
- the resulting rigid sole must still be fitted to the foot and checked against
  runtime world contact.

These three defects can look similar in a screenshot but require different
evidence. Do not use shape-key baking to explain a pivot split, do not move the
whole foot skeleton to fix a rigid shell, and do not treat one lowest shoe
vertex as proof of a flat planted sole.

## Audit Saved Shape On Every Retained Object

`invariant` source-state contract demonstrated by two independent negatives:

v4 found ten nonzero saved sneaker keys whose requested bake set was empty; the
keys had been removed while Basis geometry survived. v6 later repeated the same
failure class on hair because the earlier audit had focused on footwear. The
locked `Hair_Main` saved:

| Key | Saved value | Affected vertices | Maximum local displacement |
| --- | ---: | ---: | ---: |
| `Ahoge_big` | `1.0` | 50 | `0.02093079` |
| `Hair_tail_volume_up` | `1.0` | 2,042 | `0.05287128` |

v7 baked both values before deleting keys. v6, with an empty hair bake, remained
the matched negative control. The user then accepted the twin-tail authored
shape.

The reusable rule is broader than footwear or face: enumerate every retained
object and every non-Basis key from each locked source representation. Record
the exact key/value set, affected vertices, displacement, `applied`, and
`removed_without_bake`. Fail on unexpected nonzero, animated, driven, or muted
states. Independently reopen the locked source and compare evaluated geometry;
do not accept only the builder's own bake report.

Evidence:

- [`sneaker-shape-bake-v5-controlled-motion.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v6-hair-root-cause-20260807.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`hair-shape-and-central-bang-v7-hair.json`](../../../SOURCE_REFERENCES.md#local-only)

## Rebuild Chain Frames From The Final Rest Rig

`invariant` physics contract:

v4 reconstructed physical rest bones but inherited reference angle-limit frame
quaternions. The final successor directions no longer matched those frames. The
offline audit measured maximum frame errors near `180 degrees` for the head and
`173.79 degrees` for the body. At runtime, hair flew rapidly above the head and
ears folded inward.

Rebuild node frames after the final rest hierarchy and successor directions are
known. Compare a declared frame axis with the final successor/rest-tail vector
and fail above a project threshold. Do this before adjusting gravity, spring,
damping, wind, hardness, or quaternion signs. A parseable Chain and a plausible
single-view rest silhouette do not prove valid solver frames.

Evidence:

- [`chain-frame-audit-v4-runtime-rejected.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`chain-frame-audit-v7-hair.json`](../../../SOURCE_REFERENCES.md#local-only)

## Fixed Weighted Roots And Branch-Specific Terminals

`invariant` topology method with case-derived branch choices:

A visible weighted attachment segment is not automatically a simulated root.
The source VRM twin-tail springs began at the child after the attachment
segment. v5 simulated the first mapped weighted segment, so the roots kinked
upward. v6 left each first twin-tail segment weighted and parent-following but
outside the Chain path, then simulated the descendants. The user confirmed the
root repair.

The central fringe required the same reasoning in v7. The source
`Hair_front_001` spring began below `Hair_front_2`; the final topology used a
fixed weighted first segment, a simulated second segment, and a zero-weight
terminal helper. The fixed anchor remained visible and deforming without being
solver-driven.

Terminal policy was also branch-specific. Some source/reference twin-tail end
segments carried positive weights and had to remain deforming; separate bang,
tail, ear, or breast endpoints used zero-weight terminal semantics. Do not
blanket-zero the last source bone, collapse every endpoint, or assume that the
first visible segment is the spring root. Derive all three roles independently:

```text
weighted fixed attachment anchor
-> first simulated node and complete driven path
-> weighted endpoint or zero-weight terminal, as proved for that branch
```

Evidence:

- [`filtered-chain-build-v7-hair.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`deformation-contract-v7-hair.json`](../../../SOURCE_REFERENCES.md#local-only)

## Preserve Deform-Chain Density Before Tuning

`case-derived` repair supporting an `invariant` topology gate:

The source tail had six weighted deform intervals, but v5 collapsed them to
four unique positive targets; two source segments shared one final target. The
runtime tail therefore changed direction in visible steps. v6 preserved six
unique weighted targets, kept the first as a fixed anchor, simulated the next
five, and appended a zero-weight terminal. The user confirmed that the reported
segmented corners were gone.

Solver tuning cannot recreate spatial degrees of freedom removed by bone
collapse. Before changing spring or damping, report:

- source weighted deform intervals;
- final unique positive-weight targets in order;
- every many-to-one collapse;
- fixed-anchor, simulated-node, weighted-endpoint, and terminal roles;
- maximum unsupported span relative to the visible curve.

The accepted count of six and every `Cloth_F_*`/`KRB_*` mapping are case values,
not a universal minimum.

## Matched Diffs Preserve Causal Evidence

v7 changed only three head/hair Mesh consumer paths and two head Chain consumer
paths relative to v6. The other 107 staged paths were byte-identical. The
candidate therefore isolated the hair saved-state bake and central-fringe
topology while preserving the already accepted v6 finger, twin-tail-root, and
tail contracts.

This is an `invariant` candidate-design lesson: when a rejected cumulative
candidate contains accepted subcontracts, freeze those outputs and build the
next candidate as the smallest coherent semantic delta. Assert the complete
unchanged set, not only the intended changed paths. Keep the predecessor as the
negative control and rebuild from canonical parameters rather than overlaying
untracked intermediate files.

Evidence:

- [`stage-diff-v6-to-v7-hair.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`stage-determinism-v7-hair.json`](../../../SOURCE_REFERENCES.md#local-only)

## Rejected Shortcuts

Preserve these claims narrowly:

- `rejected`: per-bone donor-directional source projection preserves the
  authored silhouette because individual mapped anchors look plausible;
- `rejected`: moving donor core rest heads to source landmarks is sufficient to
  preserve proportions under native target animations;
- `rejected`: a neutral-pose hand proves firearm-grip finger compatibility;
- `rejected`: normalized weights prove that small-joint pivots are compatible;
- `rejected`: collapsing a rigid strap or shoe shell onto unrelated target
  articulation preserves its form;
- `rejected`: removing shape keys while retaining Basis preserves the delivered
  appearance when saved values are nonzero;
- `rejected`: auditing shoe shape keys is sufficient source-state coverage for
  hair and every other retained object;
- `rejected`: inherited Chain frame quaternions remain valid after physical rest
  directions are reconstructed;
- `rejected`: the first visible weighted segment must be the simulated root;
- `rejected`: every last source/reference branch bone should be converted to a
  zero-weight terminal;
- `rejected`: collapsing six visible tail intervals to four solver targets can
  be repaired solely by spring, damping, or gravity tuning;
- `rejected`: a candidate rejected for one new defect erases its independently
  observed positive subcontracts;
- `rejected`: scoped task acceptance permits inventing an unreported runtime
  scenario matrix or repacking the tested PAK.

## Reusable Diagnostic Sequence

For a VRM-derived replacement with deformation and physics defects:

1. Bind every screenshot or statement to the exact package and preserve the
   previous candidate as a negative control.
2. Audit the delivered saved state of every retained source object before
   diagnosing animation or physics.
3. Compare source proportions, target rest intervals, and representative native
   animation translations; do not stop at a static pose.
4. For rigid parts, separate shell articulation, saved shape, foot/body fit, and
   world contact into independent contracts.
5. For hands and other short joints, measure all positive vertex-to-pivot
   relationships and render the target-specific action that exposes them.
6. Read source spring roots and hierarchy to identify any fixed weighted
   attachment segment before creating the target Chain path.
7. Classify each branch endpoint as weighted deform, simulated node, or
   zero-weight terminal from evidence instead of a global rule.
8. Preserve sufficient unique deform targets for the authored curve before
   tuning solver parameters.
9. Rebuild node frames from final rest directions, then audit overlap,
   colliders, and parameters in that order.
10. Carry accepted subcontracts forward with a matched cumulative diff, build
    twice, and record runtime acceptance outside the immutable package.

## Build-Sensitive Snapshot: Do Not Generalize

The following belong only to this Karin Umbrella/Leon v7 snapshot on Steam
build `22377325`:

- all campaign/Mercenaries paths, resource suffixes, aliases, and consumer
  counts;
- all Leon rest matrices and every source-to-target bone mapping;
- the 30 finger-prefit bones and their measured pivot residuals;
- the six tail targets, two twin-tail fixed roots, central-fringe bone names,
  terminal IDs, Chain headers, groups, node frames, and tuning values;
- the two `Hair_Main` key names, saved values, vertex counts, and displacement
  values;
- every material/TEX/PFB/FBXSKEL choice and all package/report hashes;
- 112 PAK entries, the five-path v6-to-v7 diff, and 107 unchanged paths.

Re-extract and re-measure these values for another model, target, build, or tool
version.

## Rights And Privacy Boundary

No private model, texture, reference Mod payload, generated game binary, or
runtime screenshot is copied into SharedKnowledge. Project-local input locks
and reports retain hashes and authorized evidence. Technical success and user
acceptance do not expand redistribution rights; the accepted package remains
private and non-redistributable.

## Key Evidence

- [`input-lock.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`leon-consumer-matrix.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v1-runtime-rejection-20260806.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v2-runtime-rejection-20260806.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`chain-frame-audit-v4-runtime-rejected.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v5-runtime-deformation-audit-20260807.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v6-runtime-feedback-20260807.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v6-hair-root-cause-20260807.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`hair-shape-and-central-bang-v7-hair.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`deformation-contract-v7-hair.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`stage-diff-v6-to-v7-hair.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`release-v7-hair-fix.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`v7-runtime-acceptance-20260807.json`](../../../SOURCE_REFERENCES.md#local-only)
