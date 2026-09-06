# RE4R Character Replacement SOP

> Status: active
> Scope: long-running full-character replacement projects
> Last verified: 2026-08-07
> Evidence basis: Ashley/Karin Y, Luis/Karin Riptide, Merchant/Karin Cloth04,
> and Merchant/Karin DR03

This SOP is a reusable execution order. A project copies the relevant gates
into its own `SOP.md`, adds its own routes and thresholds, and keeps live state
there. Project evidence may tighten these gates but should not silently weaken
them.

## Definition Of Done

A deployable character replacement is complete only when:

- all intended gameplay, costume, alternate-mode, cutscene, and auxiliary
  consumers are explicitly resolved or explicitly excluded;
- source/license, game build, native resources, references, and tools are locked;
- generated Mesh, MDF/TEX, Chain, PFB/RSZ, and skeleton resources satisfy their
  binary and semantic contracts;
- every runtime file has a consumer, source, size, and SHA-256 record;
- two clean builds are deterministic;
- the package re-extracts exactly to the accepted payload;
- the evidence level is stated honestly;
- install, conflict, test, and rollback instructions match the user's boundary.

Runtime confirmation is a separate user-owned gate unless the user explicitly
authorizes the agent to launch and test the game.

## Recommended Workspace

```text
Project/
  AGENTS.md
  SOP.md
  ref/                         # immutable donor/reference Mod
  Scripts/                     # reproducible inventory/build/audit/package code
  Tools/                       # pinned tools or exact references to them
  Work/
    inventory/                 # hashes and environment snapshots
    native-target/             # current-build extracted resources
    reports/                   # canonical machine evidence
    blender/                   # authoring and clean-build roots
    candidates/                # isolated and cumulative complete trees
    runtime-test/              # only when runtime work is authorized
    staging-final/             # package payload assembled from accepted artifacts
  Output/                      # promoted deployable package only
```

Keep source/reference directories read-only. Never write generated files beside
the source FBX/Blend/VRM or into installed game archives.

## Gate 0: Scope, Rights, And Input Lock

Record before technical work:

- exact game, platform, game build, target character, and target modes;
- whether the goal includes body, face, expressions, hair, physics, materials,
  costumes, Mercenaries/alternate modes, cutscenes, or accessories;
- explicit exclusions and accepted limitations;
- whether the task is research-only, package-only, install-authorized, or
  runtime-test-authorized;
- which phases are project-local and process-independent versus which phases
  write the game tree, operate Mod Manager, or require stable runtime state;
- source model and texture identity;
- source VRM/FBX/Blend saved state and license metadata;
- reference Mod identity and redistribution boundary;
- game executable, manifest, official PAK set, path dictionary, and load order;
- tools, Blender version, add-ons, schemas, converters, and scripts.

Generate `Work/reports/input-lock.json` with paths, sizes, timestamps where
useful, SHA-256 hashes, and license/scope notes. Hash small inputs fully. For very
large official archives, record a deliberate identity policy such as full hash,
decrypted-index hash plus size/time, or another documented equivalent.

Stop when the source license conflicts with the requested use. Technical success
does not grant redistribution rights.

Relevant process detection is evidence, not an automatic global lock. When the
user authorizes a package-only workflow whose writes stay inside the project,
active RE4 or Mod Manager processes need not block independent authoring,
conversion, staging, or packaging. Never control those processes. Apply strict
closure/ownership guards before installation, removal, game-directory writes,
manager operation, or runtime testing.

## Gate 1: Current-Build Extraction

Do not begin with reference-Mod bytes. Establish the current native contract:

1. Discover the actual base and patch PAK set and effective priority.
2. Hash/decrypt indexes and merge them in load order.
3. Build target probes from known paths, path hashes, PFB strings, reference
   paths, and character-family seeds.
4. Extract only exact resolved hits into an isolated workspace.
5. Parse current Mesh, MDF, Chain, PFB, JCNS/JMAP, FBXSKEL/skeleton, and any
   related control resources.
6. Preserve every probe that is absent as an explicit missing record.
7. Verify extraction twice or run an independent verifier over the same index
   and output set.

The number and names of patch archives are build-sensitive. Discover them; do
not copy a prior project's `base -> patch_004` assumption.

When the game updates, all build-sensitive extracted resources and downstream
PFB/RSZ conclusions return to pending until rebuilt.

## Gate 2: Consumer Matrix

Build `Work/reports/consumer-matrix.json` before authoring. Each row should
contain:

```text
route family
runtime path and suffix
resource type
role: body / face / head / hair / physics / suppressor / control / unknown
default / alternate / cutscene / mode ownership
current native source and priority
reference evidence
PFB or other dependency evidence
planned action: replace / alias / patch / preserve / suppress / exclude
reason and evidence level
```

Rules:

- One visible default slot does not prove alternate costumes or modes are
  covered.
- Treat chapter, boss-form, Figure/gallery, variant, and filename semantics as
  provisional ownership only. If a later failure's time-correlated runtime
  path hits prove another consumer family, append that evidence to the matrix
  and retain the earlier route result within its narrower scope.
- A suffix such as `00`, `10`, `20`, or `50` has no universal meaning. Derive
  its role from the current character's consumers.
- Do not copy the complete body into auxiliary, GPU Cloth, expression,
  placeholder, or suppressor slots.
- Do not invent a missing native alias because the reference Mod carries one.
- Audit every reference payload and explicitly exclude unrelated weapon, prop,
  UI, sound, environment, or author-specific resources.
- Record shared paths separately from character-scoped paths. Shared skeletons
  and broad aliases require a blast-radius audit.

Gate 2 is accepted when every package path has a known consumer or a documented
reason for uncertainty, and every intended route is covered or excluded.

## Gate 3: Source, Donor, And Tool Contracts

### Source audit

Inventory:

- objects, material slots, triangles, UV layer names and positional order,
  active/render markers, each material's intended UV set, vertex colors, and
  normals;
- each glTF/VRM mesh primitive's material index or explicit unbound state,
  source base/emissive factors and textures, and actual shader-node links;
- armatures, bone names, parents, rest matrices, weighted assignments;
- shape keys and their saved values on every retained object in Blend, FBX, and
  any sibling source that preserves authored state;
- exact case-sensitive object membership and variant-specific keep/delete
  intent, distinguishing an authored object such as `Shoe` from an obsolete or
  unrelated similarly named object;
- VRM version, spring groups, node paths, colliders, and metadata;
- source object-to-bone and attachment relationships;
- texture atlas channel documentation and actual pixel statistics.

Audit every locked source representation, not only the optimized authoring
Blend. A sibling VRM/FBX may retain saved alpha, UV, material, shape, or physics
semantics that an optimized atlas or export discarded. Record which
representation is authoritative for each recovered semantic.

Do not assume all shape-key values are zero or that Basis is the delivered
appearance. Record `requested`, `saved_value`, `applied`, `affected_vertices`,
maximum displacement, and `removed_without_bake` for every deleted key. Require
an exact retained-object/key/value inventory; a footwear-only or face-only audit
does not cover hair, clothing, accessories, or other retained objects.

Use an explicit bake whitelist. Stop on unexpected non-zero values, animation,
drivers, or ambiguous muted state so a facial expression or diagnostic key is
not silently made permanent.

Topology counts are not enough for a visibility claim. Independently evaluate
the saved source state and compare positions/clearance for clothing, ropes, and
attachments that may be moved inside the body by a hidden-state shape key while
retaining every vertex and triangle.

### Donor audit

For each target slot, inventory native and reference Mesh/MDF/Chain/PFB
contracts. Distinguish:

- animation base skeleton;
- required compatibility bones;
- physical branches;
- material order and submesh layout;
- visibility semantics;
- Chain header/settings/colliders;
- PFB component and resource dependencies.

### Tool identity test

Before trusting the authoring pipeline:

1. Import a known-good target/reference resource.
2. Export it without intended semantic edits.
3. Re-import the result.
4. Compare topology, materials, UV layer-to-serialized-stream mapping, bone
   names/parents/matrices, weights, Chain structure, versions, and parse-to-EOF
   behavior.

Pin the exact working tool versions. “Latest” is not a reproducible version.

## Gate 4: Mesh And Rig Authoring

### Partition by consumer

Create body, static face, head/hair, and auxiliary partitions according to the
consumer matrix. The source model's object layout is only input organization.

### Build the rig contract

- Map core humanoid bones explicitly.
- Preserve target animation bone names, parents, roll/orientation, and rest
  transforms according to the selected target/donor contract.
- Append only required physical or attachment bones.
- Preserve the full parent closure for every weighted, Chain, collider, JCNS,
  or control bone.
- Make every source-bone collapse explicit and deterministic.
- Select a project influence limit supported by the target/tool contract;
  normalize after truncation and reject unweighted vertices.
- Select and record the proportion contract: preserve source proportions,
  conform to donor animation proportions, or apply a bounded local correction.
- Exercise representative target animation translations before moving core rest
  landmarks. A source-proportional static pose does not prove that target-native
  translation deltas will preserve the same torso or limb intervals.
- Normalize object-level binding: clear unintended Armature parents and stale
  `matrix_parent_inverse`, apply the declared object/world transform once, and
  keep only the intended Armature modifier.
- Audit every positive influence against its bind pivot, not only the dominant
  group.
- For short articulated chains such as fingers and toes, measure source-geometry
  to final animation-pivot residuals per joint and validate the target-specific
  action that exposes them. If using a bounded geometry prefit, freeze target
  rest bones and constrain the correction to the declared weighted region.
- Keep compatibility helper bones unweighted unless their actual consumer
  contract requires deformation.
- For connected clothing spanning multiple animation segments, declare the
  upper/lower or left/right semantic packages explicitly. Use the same matrix
  for each segment's static transfers and physical rest placement while
  preserving normalized cross-segment vertex weights.
- For footwear, record evaluated foot shape, foot-to-shoe fit, sole/rest-package
  orientation, and shoe-to-floor placement as separate contracts. Never treat
  a foot-bone direction as a sole-plane normal without independent geometric
  proof.
- For rigid shells such as sneakers, cuffs, straps, or hard accessories, prove
  every intended articulation pivot. When the source part has no compatible
  target articulation, bind it as one coherent rigid package and declare the
  lost local motion instead of collapsing it onto unrelated bones.

### Retarget geometry

Use measured anchor transforms, not visual nudges. Preserve the relative
assembly of related geometry and bones. For a local rigid package:

```text
desired_feature = target_anchor + build_scale * (source_feature - source_anchor)
delta = desired_feature - current_feature
```

Apply the same rigid transform to the complete geometry package and its
dedicated rest-bone subtree. Freeze unrelated core animation bones, topology,
UV, weights, material order, and other resources so the candidate remains
attributable.

Apply each measured source-to-target scale and translation exactly once. Never
rescale a coordinate after it has already been placed in absolute target space.
For source-proportion mode, use one source coordinate frame for geometry and
directly mapped anchors. Solve unmapped rest bones with a documented method,
retain or rebuild axes/hierarchy deliberately, and derive bind data and any
skeleton resource from the final armature rather than blindly transforming an
entire donor skeleton.

For a correction that must fade across a limb, define the displacement function
explicitly. A typical lower-leg form is:

```text
z <= ankle:                 displacement = full_offset
ankle < z < knee:           displacement = full_offset * (knee-z)/(knee-ankle)
z >= knee:                  displacement = 0
```

Rigidly move shoes/accessories that must retain their art proportions. Validate
the transition geometry and do not move rest bones unless the animation
contract intentionally changes.

For a planar flat sole, fit the independently identified low-contact surface
instead of targeting a scalar `Foot -> Toe` angle. Complete the source frame
with foot-forward projected into the sole plane; complete the target frame with
the independently justified floor normal and donor horizontal foot-forward.
Apply one frame transform per side to the complete intended static/physical foot
package, then remeasure any ground offset. A lowest vertex touching the floor is
not sufficient because the heel can remain raised.

### Visibility and submeshes

Derive visibility groups from the target consumer contract. Never map source
object enumeration directly to runtime groups. `Group_0` has Ashley runtime
evidence and Riptide/Luis r4 offline acceptance, but no Riptide/Luis
final-package runtime confirmation. It remains a case-derived starting point,
not proof for every character.

Preserve or compact material fragments only under explicit vertex/index limits
and after proving identical topology, material triangle sets, UV, weights, and
material indices.

### Export and acceptance

Immediately re-import each Mesh and verify:

- magic/version and expected consumer suffix;
- object/group/submesh/material contracts;
- triangle counts and material-triangle sets;
- finite coordinates, bounds, normals, UVs, and permitted quantization error;
- source material UV intent -> authoring positional layer -> serialized runtime
  UV stream closure per loop/corner; active/render markers alone do not pass;
- bone names, order if required, parents, matrices, and parent closure;
- positive weight groups, influence limit, normalization, and no unweighted
  vertices;
- packed positive palette indices resolve through `remapCount` and the final
  remap list to intended Mesh bones;
- absolute vertex-to-pivot distances for every positive influence and bounded
  absolute posed geometry, not only edge-ratio checks;
- Mesh-bone local/world translations, neutral target-space bounds, critical
  feature-to-anchor distances, and absolute Mesh/FBXSKEL rest residuals;
- expected versus actual Mesh/FBXSKEL comparison counts, with empty or missing
  intersections treated as failures;
- FBXSKEL order, parents, local/world rest, auxiliary tables, segment scaling,
  export mode, and serialized re-import semantics;
- explicit classification of weighted shared-FBXSKEL versus proven Mesh-local
  physical bones;
- post-export rest closure over the declared shared-FBXSKEL set across every
  relevant Mesh slot, plus a known-incompatible negative control;
- every Chain/JCNS/collider/attachment reference exists;
- each declared segment-coherent attachment has exact physical/static matrix
  membership, correct target parents, and focused pose/cuff continuity gates;
- footwear claims measure the actual exported sole-plane tilt, front/back
  contact height delta, plane-fit residual/coverage, and per-side independent
  floor residual rather than only transform parameters or global minimum Z;
- targeted static-clearance and deformation-pose audits.

Independently reopen the locked source and recompute evaluated saved-state
geometry, transforms, landmarks, and pair distances. For topology-preserving
work, also compare material-scoped triangle multisets. For intentional
retopology or LOD changes, use a declared surface, silhouette, landmark,
material-region, and error contract instead. Do not accept source fidelity only
because the builder reports that its own output matches.

Export the final Mesh first. Then execute the declared FBXSKEL strategy: either
generate the dependent resource twice in clean roots, or prove an exact
current-native template byte-copy against the declared shared animation-core
set while classifying all extras as Mesh-local. Use the consumer-proven runtime
path/suffix, require serialized semantic equality, and run the joint
Mesh/FBXSKEL audit. Any later participating Mesh bone order/rest/classification
change invalidates the prior FBXSKEL evidence.

## Gate 5: MDF And TEX

1. Read the final Mesh material-name table in its actual serialized order.
2. Build every MDF array to match that table exactly unless current-build
   consumer evidence proves an explicit name/index remap.
3. Confirm every submesh `materialIndex` resolves to the intended material.
4. Inventory material and property names queried by PFB/RSZ gameplay
   components, even when no visible source triangle uses them. Current-build
   disassembly or schema-backed component semantics must define the lookup and
   downstream consumer; a reference Mod alone is not sufficient authority.
5. Determine whether any returned material index crosses MDF, Mesh, or renderer
   array boundaries. Require index-isomorphic bindings unless an explicit
   current-build name-to-index remap is proved; matching counts or name sets
   alone are insufficient.
6. For a proven query-only compatibility material, do not append MDF alone. If
   the addressable Mesh material table is constructed from submeshes, provide a
   minimal non-degenerate hidden backing submesh and prove that export/re-import
   retains it without changing visible geometry, vertex layout, rig/remap, or
   per-bone bounds.
7. Prove that the runtime-sampled UV stream equals each source material's
   intended UV set. A generated-Mesh self-round-trip is not source-intent proof.
8. Count every source primitive with a missing/out-of-range material binding.
   Treat importer-created default slots as fallbacks until an authored semantic
   or explicit override is documented.
9. Prove source object/material -> texture page -> runtime render class closure
   for every final triangle; report expected, matched, ambiguous, and failed
   counts.
10. For apparent glow or invariant-white defects, trace active base/emissive
   factors, textures, node links, MDF parameters, and final TEX. Do not infer
   emission from a saved but disconnected socket value.
11. If a richer sibling source restores a local UV island, require a unique
   one-to-one correspondence for all target triangle corners, write per loop,
   document coordinate conversion, and prove non-target UV hashes are unchanged.
12. Derive packed texture channels from source documentation plus pixel audit,
   not filenames or Blender preview alone.
13. Separate alpha-test/cutout surfaces from continuous transparency when their
   render contracts differ.
14. Give continuous transparent surfaces dedicated materials and opacity
   textures when necessary; ensure no ordinary material shares those semantics.
15. Decide transparent draw order explicitly, but diagnose it separately from
   static geometry intersection.
16. Encode correct dimensions, mip chain, GPU format, and sRGB/linear semantics.
17. Decode every generated TEX and compare all channels to its intended source.
18. Re-parse every MDF and verify only intended semantic fields changed.

Material/property query inventories are consumer-scoped. Derive the complete
set separately for each observed body, event, Figure, alternate, or mode
consumer; do not copy a passing route's fixed set into another family. Close
every existing/requested MDF alias for that consumer together with the paired
Mesh-side material slots. This is an `invariant` workflow rule supported by the
`case-derived`, scoped runtime-confirmed
[`Krauser r11 sequence`](cases/KRAUSER_KARIN_SSF.md#late-transitions-can-activate-a-different-consumer-family)
and its project
[`Figure closure report`](../../SOURCE_REFERENCES.md#local-only).

The Ashley, Luis, and Merchant projects accepted complete custom
high-resolution TEX at ordinary MDF-referenced paths and rejected duplicate complete files in loose
`natives/STM/streaming`. This is a strong local default, not a claim that native
streaming pairs can never be valid. A future streaming layout needs an explicit
current-build contract and separate validation.

## Gate 6: Chain Physics

Treat source VRM dynamics as semantic input, not a direct binary conversion.

1. Map VRM/FBX nodes and colliders into the final target rig using measured
   anchors. Record units and scale factors, derive collider-local offsets from
   final target transforms without stale source armature scale, and reconstruct
   every serialized collider back to its intended world center.
2. Select current target Chain resources as route-specific structural donors.
3. Build linear groups from the final parent graph and document branch splits.
4. Verify the fixed attachment anchor, true dynamic root, weighted endpoint,
   and terminal/dummy semantics independently for each branch. A weighted first
   segment may intentionally remain outside the simulated path.
5. Compare source weighted deform intervals with ordered unique positive target
   bones; reject unapproved many-to-one collapse that removes visible curve
   resolution.
6. Rebuild angle-limit frames from final rest directions. Do not retain donor
   frame quaternions after rest directions or successor relationships change.
7. Transfer/tune spring, damping, gravity, wind, hardness, angle limits, and
   collision only after topology and frames are correct.
8. Reject repeated driven paths, accidental overlapping groups, missing
   terminal bones, missing collider bones, and unproven one-node groups.
9. Keep source branches without physics semantics static unless the project
   deliberately introduces and tests new behavior.
10. When dynamic rest bones move, invalidate the old Chain acceptance and audit
   every affected route. A proven common rigid translation may retain identical
   Chain bytes if directions/local relationships and frame/collider semantics
   remain unchanged; otherwise rebuild.
11. Export, re-import, semantic-diff, frame-audit, and build twice.

If runtime rejects one secondary branch while source/authoring/exported rest
placement and the static root parent are already correct, isolate the solver
before changing Mesh or weights. A static-hierarchy candidate may suppress all
Chain paths touching that branch while preserving its Mesh/FBXSKEL bones and
weights. Match every path node, not only the original root: overlap segmentation
can trim the root and leave descendant-starting groups. Require zero surviving
branch members in every route, unchanged unrelated resources, an explicit loss-
of-motion limitation, and exact-package runtime validation. See the
[`DR03 Merchant case`](cases/MERCHANT_KARIN_DR03.md).

Treat screenshot-side labels as observations rather than source-branch proof.
For mirrored cloth, a one-side suppression may be a diagnostic candidate. If it
normalizes that side while the opposite active side shows the same failure
class, a bilateral side-branch fallback can be the next coherent variable while
stable center/back branches remain dynamic. See the
[`Wasakura/Luis case`](cases/LUIS_KARIN_WASAKURA.md).

Do not copy Chain settings by list index across rigs. Match semantic bone paths,
rest geometry, node roles, and topology first.

## Gate 7: PFB, JCNS, GPU Cloth, And Skeleton Control

- Start from current-build PFB/RSZ bytes and a locked schema.
- Parse to EOF and inventory resources, components, enabled flags, userdata,
  skeleton mode, JCNS, and GPU Cloth/GPUC dependencies.
- Treat resource-table strings and RSZ component fields as separate binding
  layers. For every redirected Mesh/MDF/Chain dependency, prove all required
  occurrences were patched and the final table/component paths resolve to the
  same packaged resource.
- Patch only fields whose semantics and offsets are derived from that exact
  input. Require input hash, output hash, fixed size unless intentionally
  changed, exact byte diff, and exact semantic diff.
- Disabling one component does not prove related components or resource
  dependencies are detached.
- Keep JCNS/JMAP native when the replacement does not implement their behavior;
  document missing facial motion rather than copying incompatible resources.
- Prefer character-scoped skeleton aliases. A shared skeleton path requires a
  current-build consumer audit and a focused candidate.
- Use tiny suppressor/placeholder Meshes only where the consumer requires them;
  preserve their scoped role and do not copy unrelated body material payloads.

## Gate 8: Candidate Design

Create complete installable trees, not loose overlay fragments. Each diagnostic
candidate changes one resource or one coherent semantic package.

Recommended progression when load behavior is uncertain:

1. unmodified reference control;
2. head render only;
3. body render only;
4. head plus body render;
5. head Chain;
6. body Chain;
7. aliases and alternate routes;
8. PFB/control resources;
9. isolated visual/material/geometry corrections;
10. deterministic cumulative rebuild.

Each candidate records:

- parent/baseline candidate;
- declared variable;
- complete path/size/SHA-256 tree;
- exact diff from the parent;
- an asserted unchanged-resource set, not only a list of intended changes;
- required build/routes;
- offline checks;
- runtime result or `not-run`;
- rollback target.

Do not construct the final cumulative candidate by repeatedly overlaying stale
intermediate binaries. Rebuild it once from canonical source parameters, then
prove that its diff is the intended union of accepted isolated changes.

## Gate 9: Offline Acceptance

Apply [`VALIDATION_AND_RELEASE.md`](VALIDATION_AND_RELEASE.md) in full. At a
minimum:

- build all changed binaries twice in clean output roots;
- compare bytes and semantic reports;
- re-import Mesh and Chain;
- re-parse MDF and PFB;
- decode TEX;
- run deformation and focused geometry audits;
- include action-specific poses for small joints and native-translation poses for
  any proportion contract that retains target animation;
- render scoped previews from the decoded final TEX and final MDF bindings;
- validate camera/focus against the scoped geometry bounds and reject blank,
  clipped, or out-of-scope views;
- for clearance/contact claims, use an independently measured target or scene
  reference plane; a plane derived from candidate bounds is display-only;
- generate a forbidden-path/resource audit;
- bind every report to actual artifact hashes;
- produce an exact resource map and package manifest.

Promote only an `offline-accepted` cumulative candidate to staging.

## Gate 10: Package

Build the deployable package from the accepted manifest, never from an
untracked working directory.

The common Fluffy layout is:

```text
modinfo.ini
README.md
manifest.sha256
natives/
```

Do not add an unnecessary outer candidate directory inside the ZIP. Use fixed
entry order, path normalization, compression settings, and timestamps when
byte-identical archives are required. Re-open and extract the archive to a new
directory, then compare every path, size, and SHA-256 with staging.

The package inherits the candidate's evidence level. Packaging is not runtime
validation.

Set process guards from the operation boundary. A workspace-only build from
locked inputs may proceed while RE4 or Mod Manager is active when it only
records that state and performs no process control, deployed-tree authority
read, installation, candidate switch, or game-directory write. Deployment and
runtime operations still follow Gate 11 and the transactional process rules.

## Gate 11: User Runtime Validation

If the user retained runtime testing, deliver:

- candidate/package name and SHA-256;
- supported game build and routes;
- install, conflict, remove, and cold-start instructions;
- instructions to confirm the enabled entry actually deployed files and that
  no mutually exclusive variant owns the same runtime paths;
- a scenario matrix covering default and alternate consumers;
- independent rows for late cutscene/boss/event phase transitions, with the
  active route verified from runtime hits rather than scene naming;
- focused checks for static geometry, deformation, transparency, physics,
  cutscenes, wetness/dirt, and lighting;
- separate foot-to-shoe and shoe-to-world contact checks when footwear is in
  scope; the latter must use the actual target floor and relevant IK/animations;
- known limitations and rollback candidate.

When runtime work is explicitly authorized for the agent, follow the
transactional deployment rules in
[`VALIDATION_AND_RELEASE.md`](VALIDATION_AND_RELEASE.md). RE4 must be closed for
every switch. An external script must not switch while Fluffy is running;
Fluffy-managed enable/disable is allowed only with Fluffy as the sole writer,
followed by closing Fluffy and performing the independent tree audit.

## Gate 12: Feedback Loop

For each user report, including a short explicit acceptance:

1. Bind the observation to candidate/build/route/cold-start evidence.
2. Split mixed symptoms into their technical layers.
   A native-character screenshot is deployment evidence only after the actual
   installed file set is known; an enabled zero-file entry does not reject the
   packaged PFB/Mesh. Likewise, a tiny placeholder requires consumer/PFB
   binding evidence before it is labeled a scale defect.
3. Compare source, authoring, exported binary, and runtime observation.
4. Form the smallest testable hypothesis.
5. Build a matched-baseline isolated candidate.
6. Preserve rejected sufficiency claims.
7. Rebuild the cumulative candidate only after isolated acceptance.
8. Update the project SOP and handoff block.

Keep visible orientation and source identity separate. A report such as
“right side crossed left” proves an abnormal silhouette in that view; it does
not by itself prove which named source branch migrated. Use explicit membership
and matched candidates to establish that claim.

If the user accepts a uniquely identified delivered package without restating
its hash, record the task-context binding and that qualification. Promote only
the stated acceptance scope; keep unreported route, action, cold-start,
lighting, process, conflict, and attachment fields as `not-observed` rather
than inferring a complete matrix.

When one blocker disappears but the same candidate exposes a new blocking
layer, preserve both facts. For example, an actor-instantiation crash can become
a material fallback after a lookup fix. Record the crash-path pass as a narrow
positive observation, reject the candidate for the new visual blocker, and
trace the output of the repaired lookup into its next consumer before changing
unrelated resources. A symptom transition is often stronger causal evidence
than another all-or-nothing rebuild.

A newer SHA-bound runtime rejection is fail-closed even if the prose still says
the candidate is awaiting testing. Synchronize the project state immediately,
preserve narrower offline passes and positive observations, and leave the next
candidate as a hypothesis until it is separately built and accepted.

When a later transition fails after an earlier route passed, reopen consumer
attribution before editing the earlier route. Bind the fault timestamp, inspect
the immediate PFB/Mesh/MDF accessed and loose-hit window, and derive the new
consumer's material/property and alias closure from current-build evidence.
The `case-derived` Krauser r10/r11 evidence is the
[`route-attribution rejection`](../../SOURCE_REFERENCES.md#local-only)
followed by the
[`scoped acceptance`](../../SOURCE_REFERENCES.md#local-only).

## Long-Running Handoff Block

At every pause, update this block in the project SOP:

```text
Objective:
User authorization boundary:
Current evidence level:
Current game build/platform:
Immutable inputs and input-lock digest:
Pinned tools/schemas:
Current consumer matrix digest:
Current canonical candidate:
Candidate file count and manifest digest:
Exact changes from prior accepted baseline:
Completed offline gates:
Completed runtime scenarios:
Latest exact-candidate runtime feedback:
Runtime positive-observation scope:
Rejected hypotheses:
Known limitations:
Current install state or not-installed boundary:
Next single variable:
Exact resume commands:
Evidence directory:
Rollback procedure:
Supersedes:
```

The next agent should be able to resume from this block without trusting memory
or re-running completed destructive/runtime steps.
