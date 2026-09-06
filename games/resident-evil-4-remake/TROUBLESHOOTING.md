# Troubleshooting Playbook

> Status: active
> Scope: symptom-led diagnosis for RE4R character replacement
> Last verified: 2026-08-07

## Diagnostic Order

Do not start with parameter tuning. Check layers in this order:

1. **Identity and routing:** exact candidate, build, consumer, alias, and actual
   requested path.
2. **Binary contract:** resource version, parse, material index, bone closure,
   PFB dependencies, and runtime-tree conflicts.
3. **Source saved state:** retained-object shape keys, object transforms, source
   attachment frames, and intended transparency.
4. **Authoring geometry/rig:** source-to-target transform, weights, rest bones,
   clearance, visibility groups, and export comparison.
5. **Chain structure:** true root, terminal/dummy, overlap, frames, and colliders.
6. **Chain parameters:** spring, damping, gravity, wind, hardness, and limits.
7. **Rendering:** alpha mode, opacity channel, MMTR, material/submesh order.
8. **Runtime-only behavior:** animation, IK, cutscene state, GPU Cloth, lighting,
   wetness/dirt, and engine-specific sorting.

At each layer compare source -> authoring -> exported binary -> runtime. The
first stage where the result diverges is the best fault boundary.

## Symptom Matrix

| Symptom | First evidence to collect | Likely layers | Avoid as first move |
| --- | --- | --- | --- |
| Loading stalls near the end | Named control candidate, accessed/loose logs, exact tree manifest | routing, PFB/JCNS/GPUC, Chain, aliases, texture layout, conflict | rebuilding the whole model or changing many resources |
| Actor creation crashes at one repeatable native instruction with an invalid material index | exact ZIP/install binding, dump registers and stack, caller return, material/property hash, Mesh/MDF/PFB parse | unchecked runtime material/property lookup and cross-array index consumption | changing Chain, Motion, PFB, or one guessed material without resolving the full caller matrix |
| An earlier encounter passes but a later boss/event transition crashes in the same character | exact late-transition timestamp, sub-second PFB/Mesh/MDF accessed and loose-hit window, dump key/index, route-scoped native MDF properties | a different event/Figure/alternate consumer with its own material-query and alias closure | assuming the chapter description or mutation filename identifies the active route, or copying the earlier route's material set |
| `Files encountered` keeps rising | timestamped accessed/loose logs and candidate path hits | repeated resource construction/request loop | interpreting it as loose-file count or directory recursion |
| Default costume works, alternate shows donor/native | consumer matrix and path-hit logs | missing alias/alternate route | changing geometry/materials |
| Mod Manager says enabled but the native character remains | enabled entry plus actual deployed-file list, target-path hashes, and request logs | zero-file/stale installation, conflict priority, wrong package root | changing Mesh/PFB before proving any candidate bytes were deployed |
| Character is invisible or only a tiny placeholder appears | current PFB resource-table paths, RSZ component fields, occurrence counts, and runtime path hits | table/component path mismatch, missing dependency, scoped suppressor/fallback | changing model scale or rebuilding materials first |
| Part disappears entirely | source alpha stats, decoded ATOC, MDF alpha-test flags, submesh material | opacity/cutout contract, visibility, missing TEX | moving geometry |
| Part topology is intact but the surface is absent | evaluated source/build positions, saved shape keys, body clearance, affected-vertex displacement | hidden-state shape-key bake or geometry moved inside another surface | concluding that vertices were deleted from equal topology counts |
| Semi-transparent part becomes a hard hole | dedicated material and opacity-channel audit | alpha test discarding low alpha | raising material alpha without separating the surface |
| Transparent object draws through another | source/authoring/final clearance plus material order | draw order if geometry is correct; retarget if geometry intersects | treating ordering and placement as one problem |
| Attachment sits inside clothing | source vs authoring anchor frames and final export error | incoherent retarget anchors/rest package | material reordering alone |
| Both forearms look reverse-bent or severely twisted | source/target upper-arm, forearm, and hand rest directions plus roll/frame matrices | wrong limb rest-frame mapping or donor/core mismatch | retuning weights or Chain parameters first |
| Torso or abdomen is plausible at rest but elongates in motion | source/target rest intervals plus native animation translation deltas and runtime pose | moved target core rest under animation authored for target lengths; mixed proportion contracts | further moving core rest landmarks from a static screenshot |
| Fingers twist mainly while aiming or gripping a weapon | per-phalange positive weights, source geometry pivots, final animation pivots, and exact grip pose | small-joint pivot mismatch despite normalized weights and correct neutral pose | repainting hands, changing Chain, or accepting a neutral preview |
| Whole character explodes into long triangles | exact Mesh/FBXSKEL pair, all-positive vertex-to-pivot distances, absolute posed bounds | bind-space transform, bone order/parents/rest, cross-slot skeleton mismatch | assuming normalized weights or a parsable Mesh proves compatibility |
| Rigid cuff strap or hard accessory has one segment standing away from the body | source branch intervals, target collapse map, rigid-component membership, and runtime parent motion | source rigid shell compressed onto unrelated articulation or remote pivots | adding stronger gravity or mapping every source segment to any available Cloth bone |
| Sneaker front splits or looks shattered only in motion | saved shoe state, Toe/Foot pivots, shoe-weight regions, and toe-rotation pose | rigid shoe shell bound to incompatible target Toe articulation | baking shape keys alone or moving the whole foot skeleton |
| Texture islands show unrelated skin/clothing pages | source material UV intent -> authoring layer index -> serialized runtime UV stream, plus per-triangle page closure | wrong positional UV stream, guessed page/class, lost local UV island | repainting the atlas or changing all MDF parameters |
| One isolated strap/part stays pure white under changing light | source primitive material index, importer fallback slot, base/emissive factors, actual node links, final MDF/TEX binding | unbound primitive, default material, wrong base PBR class/path | adding emissive or changing a whole atlas page |
| Hair/ribbon points upward at rest | source saved pose, actual Chain path, terminal identity | missing terminal dummy, wrong dynamic root, frame | stronger gravity or quaternion reversal |
| Hair is static, then spins violently | Chain topology, repeat drive, frames, solver type, wind | terminal/root semantics, overlapping groups, parameter mismatch | copying another chain by list index |
| Hair continuously flies above the head or ears fold inward after rest-bone reconstruction | final successor directions, inherited vs rebuilt node-frame axes, angular-error report | stale donor angle-limit frames on changed rest directions | spring/gravity tuning before frame rebuild |
| Twin-tail or fringe first segment kinks upward while the remaining chain moves | source spring root and parent, weighted first segment, final first simulated node | fixed weighted attachment anchor incorrectly included as dynamic root | making the anchor unweighted or reversing gravity |
| Tail or long hair bends in visible steps | source deform intervals, ordered unique final weight targets, many-to-one collapse map | insufficient deform-chain density before solver tuning | changing damping/spring to recreate removed spatial degrees of freedom |
| Twin-tail volume or other authored hair silhouette is wrong even when motion is stable | all retained hair-object saved keys, values, evaluated displacements, and prior bake report | nonzero saved state removed without bake | changing Chain parameters or sculpting Basis before source-state audit |
| Rigid accessory is correct offline but flies, rotates, or lifts at runtime | exact candidate screenshot, final rest placement, root parent, and every Chain path containing branch members | runtime Chain topology/frame/calibration or collision | moving geometry, collapsing weights, or changing FBXSKEL before isolating the solver |
| Tail has no physics | runtime path hits, Chain group/terminal, Mesh bone closure | missing route/alias, missing group, absent terminal | adding arbitrary gravity |
| Tail moves only after locomotion, does not settle, or tangles after lateral steps | complete node path, zero-weight terminal helper, repeated drive, rest frames, return/damping profile | missing terminal semantics, overlap, or no stable rest return | increasing gravity before topology/frame proof |
| Sleeve looks curled/rotated | sleeve plane normal relative to forearm in several views | wrong rest transform/frame | gravity-only tuning |
| Sleeve points across or perpendicular to the forearm | per-segment upper-arm/forearm membership, static-transfer matrices, physical-rest matrices, and root parents | one connected sleeve forced through the wrong limb frame | assigning one matrix to the whole connected component |
| Sleeve moves but does not droop | topology segmentation, dynamic root, then solver parameters | geometry/rest silhouette plus solver | assuming one gravity value is sufficient |
| Cloth penetrates body | collision groups/colliders after motion is otherwise correct | collision, geometry clearance | mixing collision and droop changes |
| One mirrored skirt side collapses or bulges only when physics runs | exact package, mirrored static rest/collider audit, explicit branch membership, Chain-only matched candidate | runtime Chain solve, terminal/frame/collider calibration | assuming visual left/right proves the named source branch or editing Mesh first |
| High-heel foot outside shoe | saved source shape keys and source foot-to-sole relationship | source-state loss or wrong footwear fit | translating the whole foot skeleton |
| Foot fits shoe but sole is underground | outer-sole min-Z against the runtime floor, animation/IK state | world-ground contact and lower-leg geometry | treating an offline feet-side preview as floor evidence |
| Flat shoe touches at one point but remains on tiptoe | fitted low-contact plane, sole tilt, front/back height delta, and per-side floor residual | shoe/rest-package orientation; stale post-rotation floor offset | forcing a scalar `Foot -> Toe` angle or accepting one minimum-Z vertex |
| Focused preview is blank or clipped | scoped geometry bounds, camera target, clipping planes, rendered pixel coverage | camera/focus setup rather than missing geometry | accepting the image as proof the part is absent |
| One surface has checkerboard/missing texture | MDF path, actual ordinary TEX, version/mips | path/version/packaging | duplicating complete TEX into streaming |
| Body route becomes checkerboard while an independent head route is correct, especially after a material-lookup crash fix | exact body Mesh/MDF name/count/index tables, PFB material-query target, downstream use of returned indices | Mesh/MDF material-array closure or missing backing submeshes before TEX | changing all textures or assuming “no crash” proves the material repair is complete |
| Metallic part is nearly black | decoded ALBD/dielectric map and light response | BaseDielectricMap/base color | changing all metallic/roughness fields together |
| Eyes converge or face looks dirty | eye pivots/weights and unified Head transfer | rig/overlap/normals | repainting textures first |
| Candidate Verify fails but its files match | four-way master/disk/state/runtime audit | unrelated base drift | deleting unexpected files |
| Multi-phase release stops after Blender succeeds | child wrapper source and outer phase log | nested PowerShell `exit`, stale `$LASTEXITCODE`, or missing throw/return contract | manually running later phases while leaving the orchestrator broken |

## Loading Stall Isolation

### Establish a control

Use an unmodified known-working reference Mod as a control when licensing and
scope allow. A control that reaches gameplay proves the game build, loader, and
basic deployment channel for that exact test, then narrows the fault to the
replacement payload.

### Build an additive ladder

The Ashley project isolated a load issue with:

```text
reference control
head render
body render
head + body render
head Chain
body Chain
remaining aliases/PFB/control resources
```

Each candidate was a full tree with one declared delta. This provided more
information than repeatedly rebuilding the full package.

### Read loader counters correctly

In the observed LooseFileLoader behavior, `Files encountered` incremented for
each non-empty resource request before cache handling. A rising number indicated
repeated construction/request attempts, not the number of files on disk.

This is case evidence tied to the observed loader version; recheck source/log
behavior when the loader changes.

### Preserve rejected sufficiency claims

Ashley runtime candidates showed that the following changes alone did not fix
the load stall:

- adding inferred JCNS compatibility bones;
- correcting visibility groups/submesh compaction;
- disabling one GPU Cloth Bool;
- removing duplicate loose streaming TEX.

Several were still valid structural corrections. The rejection is that each was
not sufficient alone.

## Actor-Instantiation Crash, Checkerboard, Or Later-Route Recurrence

Treat a repeatable native crash and the visual state after removing it as two
successive consumer boundaries, not as one binary pass/fail result.

1. Freeze the exact candidate archive, installed-tree identity when available,
   crash dump, accessed/loose logs, and timestamps before restarting the game or
   changing the Mod Manager state. An old dump that predates the current
   session is not evidence for the new symptom.
2. Confirm which body/head/variant route was requested. A separately correct
   head proves that route and some shared texture namespace can load; it does
   not prove the body Mesh/MDF contract.
3. Bind the fault to the current executable. Record RIP, invalid effective
   address, index register, lookup-name/property hashes, and the immediate
   caller return. Resolve hashes from executable strings, current schemas, and
   parsed native/reference resources rather than memory alone.
4. If a candidate keeps the same fault instruction but advances to the next
   caller position or next material hash, preserve that as positive evidence:
   the earlier lookup fix was active. The candidate is still runtime-rejected,
   and the result does not prove the whole lookup set is closed.
5. Once caller control flow proves a fixed lookup matrix, enumerate the complete
   name/property set and compare current native, successful reference, target
   PFB/RSZ parameters, candidate MDF, and candidate Mesh. A coherent full-matrix
   candidate is more informative than continuing one-name-at-a-time after the
   matrix is proven.
6. Do not stop at “the crash disappeared.” Trace how the returned indices are
   cached and consumed. If a material index later addresses a Mesh-side or
   renderer-side array, validate index equivalence across the full Mesh/MDF
   binding graph.
7. When a queried compatibility material has no visible source geometry, use a
   consumer-proven minimal hidden backing submesh that survives serialization.
   Require a non-degenerate triangle, valid vertex layout/weights, unchanged
   visible submesh semantics, and unchanged skeleton/remap/bounding boxes.
8. Build the post-crash visual correction against the exact crash-free parent.
   Assert the one declared changed resource and the byte-identical remainder,
   then retest both stability and rendering at the same checkpoint.
9. If the same character fails only at a later transition, restart consumer
   attribution. Inspect the immediate pre-crash PFB/Mesh/MDF hits instead of
   assigning ownership from chapter, boss-form, Figure/gallery, or variant
   naming. A previously passing route is a control, not proof that the later
   scene uses it.
10. Derive the complete material/property query set for the newly observed
    consumer from current-native records and caller/component evidence. Do not
    reuse the earlier route's fixed set merely because one name overlaps.
11. Close every existing/requested MDF alias plus the paired Mesh-side slots,
    then retest the exact later transition. Record crash clearance, first
    rendered state, special-part visibility, and subsequent scene entry as
    separate rows.

Interpret the common symptom progression narrowly:

```text
missing material lookup -> invalid sentinel index -> native crash
MDF-only lookup closure -> actor instantiates -> later Mesh/material-array mismatch
Mesh/MDF backing closure -> candidate eligible for the same stability + render retest
later transition -> re-attribute consumer -> derive route-local query/alias closure
```

This sequence is `case-derived`, not a universal RE Engine state machine. The
Krauser/Karin SSF case confirmed it for one current-build body updater, then
showed that a Chapter 11 Campaign pass did not cover the Chapter 14
Figure/event consumer. See
[`KRAUSER_KARIN_SSF.md`](cases/KRAUSER_KARIN_SSF.md) and the canonical material
contract in [`TECHNICAL_CONTRACTS.md`](TECHNICAL_CONTRACTS.md#41-material-indexing-is-one-contract).
Generating evidence is preserved in the project
[`r10 route-attribution rejection`](../../SOURCE_REFERENCES.md#local-only),
[`r11 Figure closure`](../../SOURCE_REFERENCES.md#local-only),
[`r11 scoped acceptance`](../../SOURCE_REFERENCES.md#local-only),
and [SOP snapshot](../../SOURCE_REFERENCES.md#local-only).

Preserve these rejected sufficiency claims:

- `rejected`: disabling Chain, JointConstraints, or swapping Chain bytes alone
  fixes a proven material-index crash;
- `rejected`: restoring the first missing material proves the caller's complete
  lookup matrix is satisfied;
- `rejected`: adding every queried name to MDF is structurally complete when a
  later consumer uses the returned index against Mesh-side state;
- `rejected`: disappearance of the crash promotes the candidate even when the
  body renders with a blocking fallback material;
- `rejected`: a body-wide checkerboard necessarily means the custom TEX files
  are absent when an independent head route using them renders correctly;
- `rejected`: a passing early encounter confirms every later consumer for the
  same character;
- `rejected`: mutation/variant naming identifies the active crash route without
  time-correlated path hits;
- `rejected`: a compatibility-material set derived for one updater is a
  universal per-character set.

## Invisible Character, Tiny Placeholder, Or Native Fallback

Separate deployment from resource binding before touching geometry:

1. Confirm the exact candidate archive and inspect the Mod Manager's actual
   deployed-file records. An enabled entry with zero copied files is a
   deployment incident, not evidence that the packaged Mesh or PFB failed.
2. Hash the intended target paths in the live tree when runtime inspection is
   authorized. Record missing, same, and conflicting files.
3. Resolve the current consumer. Some special slots intentionally use tiny
   suppressors; a small cube/triangle can mean the wrong scoped consumer was
   replaced or the primary body dependency never bound.
4. Parse the current PFB resource table and every relevant RSZ component field.
   A custom path in the table is insufficient if `via.render.Mesh`,
   `via.render.ComputeSkinning`, `via.motion.Chain`, or a related instance still
   names the native or placeholder path.
5. Patch both required binding layers from the locked current input, assert
   expected occurrence counts, parse to EOF, and require table/component path
   equality plus complete package closure.
6. Rebuild every consumer route twice and compare an isolated repeat tree.

Do not infer a scale defect from invisibility until path hits prove that the
custom Mesh was requested. Do not infer a binary/PFB rejection from a native
character screenshot until candidate files are proven deployed. The Nyako/Ada
case contains three separate negative examples: R2 table/component divergence
left body, face, and hair invisible while independent prop geometry remained
visible; R1's earlier tiny cube occurred under a route/FBXSKEL mismatch and is
not specific evidence of PFB-layer divergence; a later native-Ada screenshot
came from a zero-file Fluffy installation. See
[`ADA_KARIN_NYAKO.md`](cases/ADA_KARIN_NYAKO.md).

## Whole-Character Explosion And Long Triangles

First verify the exact installed candidate, runtime route, Mesh/FBXSKEL pair,
and resource versions. Then audit bind-space semantics before tuning weights or
physics:

1. Re-import the final Mesh and FBXSKEL and compare names, serialized order,
   parents, local/world rest matrices, auxiliary tables, segment scaling, and
   export mode.
2. Prove each packed positive palette index is below `remapCount` and resolves
   through the serialized remap list to the intended Mesh bone.
3. For every positive influence on every vertex, measure the absolute distance
   from the vertex to its bind pivot. Do not stop at the dominant influence.
4. Compare bone local/world translations, neutral target-space bounds, critical
   feature-to-anchor distances, and absolute Mesh/FBXSKEL rest residuals.
5. Pose representative bones and cap absolute vertex displacement and posed
   bounds. Internal edge ratios cannot detect a rigid patch orbiting a remote
   pivot.
6. Report expected versus actual comparisons and missing-name sets. Empty
   intersections fail; they never imply zero error.
7. Classify weighted bones as shared-FBXSKEL or proven Mesh-local physical
   branches. If several slots share one FBXSKEL, require the declared shared set
   of post-export rest matrices to close across those slots.
8. Run a known-incompatible negative control and require the validator to reject
   it.

The Merchant R2 case disproved three shortcuts: adding the reference FBXSKEL
alone, checking normalized weights/valid indices/inverse pairs alone, and using
edge ratios alone. Its generated geometry and pivots were each internally
finite but occupied incompatible absolute spaces. See
[`MERCHANT_R2_MESH_BIND_SPACE_FORENSICS.md`](../../SOURCE_REFERENCES.md#local-only)
and the
[`Merchant case`](cases/MERCHANT_KARIN_CLOTH04.md).

## Atlas Loads But Uses Wrong Islands

When the correct Atlas image is visibly present but facial, hair, skin, and
clothing features appear on unrelated regions, separate texture identity from
UV-stream identity:

1. Identify the UV set intended by each locked source material.
2. Record every authoring UV layer name, positional index, and active/render
   marker.
3. Prove how the pinned exporter maps layer positions into serialized runtime
   UV streams.
4. Re-import the final Mesh and compare the stream sampled by the runtime
   material against source UVs per loop/corner.
5. Build a candidate that changes only UV stream assignment/order and assert
   topology, materials, coordinates, normals, weights, bones, and matrices are
   unchanged.
6. Require the fixed runtime stream to equal the previously serialized intended
   stream exactly when topology permits that comparison.

Do not accept a Mesh round-trip that only compares the generated file to a
re-export of itself. That can be perfectly stable around the wrong mapping. In
the Wasakura/Luis rejection, Blender's active `UV_Atlas` marker did not override
the exporter's positional rule; layer zero became runtime UV1. See
[`LUIS_KARIN_WASAKURA.md`](cases/LUIS_KARIN_WASAKURA.md).

## Twisted Limbs And Perpendicular Sleeves

First separate the core animation limb from attached deform/physics branches.
Severe bilateral reverse bending usually points to the upper-arm/forearm/hand
rest contract, while a sleeve rotated across an otherwise correct arm points to
an attachment-segment frame.

1. Compare source and target upper-arm, forearm, and hand heads/tails, roll, and
   full rest matrices. Verify that the selected donor really owns the target
   animation contract.
2. Re-import the final Mesh and prove core bone names, parents, directions, and
   FBXSKEL closure before changing weights.
3. Inventory every positive sleeve influence and physical root. A single
   connected sleeve can contain both upper-arm and forearm semantic regions.
4. Build one rest-frame transform per declared limb segment. Require each
   physical rest record and static weight transfer in that segment to serialize
   the same matrix and parent to the matching donor anchor.
5. Preserve normalized cross-segment weights at the elbow instead of making the
   entire connected component rigid.
6. Measure the cuff plane against the target forearm and test a representative
   bent-elbow pose for gaps, inversion, and discontinuity.
7. Only after the static/rest result is correct should Chain topology or solver
   parameters enter the diagnosis.

The Ashley case established focused cuff-frame checks. The Nyako/Ada case adds
the negative example where upper-arm and forearm semantics were mixed across a
connected sleeve, producing an approximately perpendicular result. Exact source
roots, transfer counts, matrices, and angular thresholds are `case-derived`.

## Runtime Translation, Small Pivots, And Rigid Shells

When a proportion defect appears only in motion, compare target-native animation
translations with both the original and modified target rest intervals. Moving a
target core skeleton to shorter source landmarks can make the static body look
right while native translation curves re-extend it at runtime. Freeze Chain and
materials during this test. Decide explicitly whether target animation rest or
source anatomical rest is authoritative instead of alternating between the two.

For a short joint that fails only in a specific action:

1. isolate the exact action and candidate;
2. enumerate every positively weighted vertex and mapped joint;
3. compare source geometry pivots with final animation pivots per joint;
4. preserve the target rest skeleton when it is the animation authority;
5. if selected, prefit only the bounded joint-weighted geometry through a
   deterministic rest transform;
6. retest neutral continuity and the exposing action.

For a hard shoe, cuff, plate, or strap, first decide whether it is authored as a
rigid shell. Do not force its source segments through unrelated target pivots
merely to retain nominal articulation. A coherent rigid bind with an explicit
loss-of-motion limitation is safer than a many-to-one articulated collapse.
Shape-state baking, rigid-shell binding, body fit, and world contact remain four
separate gates.

The Leon/Karin Umbrella sequence is the matched negative/accepted case for all
three patterns. See
[`LEON_KARIN_UMBRELLA.md`](cases/LEON_KARIN_UMBRELLA.md).

## Static Geometry Versus Rendering

For an overlap report, calculate and render:

1. source relationship;
2. authoring relationship;
3. exported Mesh relationship;
4. transparent material order.

Interpretation:

- Source correct, authoring wrong: retarget, shape-state, or attachment-anchor
  problem.
- Authoring correct, exported wrong: serialization/export problem.
- Source/authoring/export correct, runtime wrong: animation, route, visibility,
  or render/runtime problem.
- Geometry intersects in authoring: draw-order changes cannot be the full fix.

The Luis water gun failed because the gun and raincoat were independently
mapped through different torso frames. The visor failed because a saved shape
key was discarded. Both initially resembled rendering problems.

## Shape-Key Loss

Diagnostic pattern:

- source screenshot differs from built static geometry;
- exported Mesh exactly matches authoring, so export is not the cause;
- authoring exactly matches source Basis;
- source file saves a non-zero shape-key value.

Correct response:

1. Enumerate every retained object and verify every saved value in every supplied
   source representation; do not scope the audit only to the currently reported
   footwear, face, or hair object.
2. Bake only the intended key/value before deletion.
3. Compare the baked geometry directly with the evaluated source state.
4. Report affected vertex count and max error.
5. Keep rigid translation as a rejected alternative when it changes unrelated
   regions or leaves a large residual.

Keep the immediately preceding empty-bake or Basis-only candidate as a negative
control. The Leon/Karin Umbrella project repaired footwear keys first but later
found two independently nonzero hair keys, demonstrating that object-local audit
success is not source-wide coverage.

## High Heels And Ground Contact

Use two independent acceptance gates:

1. **Foot-to-shoe fit:** evaluate the intended saved high-heel state and compare
   skin to the source outer sole. Preserve the authored gap; it need not be zero.
2. **Shoe-to-world contact:** compare the outer sole to the target runtime floor
   in relevant animation/IK states. An offline preview without that world plane
   cannot pass this gate.

The contact plane must come from independent target/native/runtime evidence. A
preview floor defined as `candidate_min_z - epsilon` will follow the defect and
is suitable only for presentation, never for a contact or clearance gate.
The minimum vertex of a native target Mesh is also only geometry evidence; it
does not automatically equal the runtime scene plane. Chrome Merchant R1
matched the native minimum but still received task-local penetration feedback.

For a flat shoe, do not use a scalar `Foot -> Toe` bone angle as the sole
orientation target. Bone direction and contact-plane normal encode different
things. Do not accept one minimum-Z point either: a toe can touch the floor
while the heel remains visibly raised.

Instead:

1. fit the source shoe's intended low-contact surface and record coverage and
   plane-fit residual;
2. project source foot-forward into that plane to complete the source frame;
3. build the target frame from an independently justified floor normal and the
   donor's horizontal foot-forward direction;
4. apply one transform per side to the complete static/physical foot package;
5. recalibrate ground placement after the rotation;
6. reopen the exported authoring/binary result and measure sole tilt,
   front-to-back height delta, plane RMS/thickness, and each side's floor
   residual.

Nyako/Ada R8 is the rejected example: a scalar bone-angle target tilted an
originally flat sole and still passed a lowest-point gate. R9 replaced it with
a sole-plane frame and received scoped user acceptance. The numeric angles,
offsets, face counts, and thresholds from that case are not reusable constants.

Then choose a correction according to the failed gate:

- Bake the intended high-heel foot shape first.
- Audit the shoe sole and skin independently.
- Avoid weight-proportional translation when it folds triangles.
- Avoid affine shoe compression when preserving shoe art is required.
- Consider a rigid shoe/accessory translation plus a smooth body-only lower-leg
  displacement that reaches zero at the knee.
- When the complete authored assembly is locally correct and evidence instead
  indicates one common world-placement error, consider a rigid translation of
  every participating Mesh and its rest skeleton. Do not move vertices without
  their pivots.
- Keep animation/rest bones fixed when the goal is geometry-only compensation,
  then test pose deformation and IK in user runtime validation.

Acceptance needs triangle-flip, near-zero-area, edge-ratio, area-ratio,
normal-dot, shoe-rigidity, knee/upper-body invariance, and matched-floor checks.
The Merchant R4 candidate passed foot-to-shoe fit but was runtime-rejected for
outer-sole floor clipping. Therefore saved-shape baking is not sufficient proof
of world contact.

## Chain Fault Tree

For stiff, unstable, or upturned dynamics:

1. Does the runtime route request the intended Chain?
2. Does the final Mesh contain every node/terminal/collider and parent?
3. Is there a weighted attachment anchor that should remain fixed outside the
   simulated path, and does the source spring actually begin at its child?
4. Is the visible deform root actually simulated, or has it become terminal?
5. Is the endpoint a weighted deform segment or a zero-weight terminal for this
   specific branch?
6. Did source optimization remove `_end`/dummy bones?
7. Are groups overlapping or driving a bone more than once?
8. Does the final path preserve enough ordered unique positive targets for the
   source's visible deform intervals?
9. Does each rebuilt frame axis align with the final successor/rest direction?
10. Do source collider centers map through the final rig transform, remain
   scale-plausible, and reconstruct from serialized local offsets back to the
   intended world positions?
11. Does the static source rest pose already point the correct way after all
    saved shape state is evaluated?
12. Only then compare solver type, angle limits, spring/damping, gravity, wind,
   and collision.

For hair that flies continuously upward or ears that fold into the head after a
rest-rig rebuild, compare inherited frame quaternions to the final successor
directions before touching parameters. For an upward kink confined to the first
segment, inspect fixed-anchor versus dynamic-root role. For stepped curvature,
inspect many-to-one bone collapse. These are distinct failure layers even when
all three are described as bad physics.

For a tail that moves only after locomotion, fails to return to a natural rest,
or tangles after a few lateral steps, explicitly verify the complete path ends
in a real zero-weight terminal helper, no node is driven by overlapping groups,
and the selected solver profile includes a stable rest-return/damping contract.
Do not tune against an incomplete path.

For a one-sided chest or other mirrored twitch, audit both source branches and
all route groups before changing only the visible side. A symmetric static
policy can be a coherent safety candidate when that motion is nonessential, but
it must retain the required Mesh bones, remove every affected Chain driver on
both sides, preserve unrelated groups, declare the lost motion, and receive
runtime evidence. The Nyako/Ada project used this policy for its chest branches;
the group numbers and settings are `case-derived`.

If a proper terminal cannot be added safely, removing the invalid group and
retaining the correct static source rest pose is a defensible fallback. It loses
secondary motion but avoids simulating the wrong node. Record that limitation.

For a rigid accessory that is correct in source, authoring, and exported rest
pose but moves incorrectly only at runtime:

1. Prove the static root parent and local hierarchy are correct.
2. Record the visual symptom separately from source-branch identity. Camera
   orientation and deformation can make `left`/`right` or cross-body migration
   ambiguous.
3. Enumerate every final Chain path containing any branch node. Do not search
   only for paths that start at the original root; overlap segmentation may
   have trimmed it.
4. Build a complete matched candidate that removes only those groups while
   retaining geometry, weights, bones, and FBXSKEL.
5. Assert exact changed paths and exact unchanged hashes against the accepted
   baseline.
6. Re-import, semantic-diff, build twice, package twice, and request a focused
   exact-package runtime retest.

The DR03 Merchant R3 backpack had correct offline placement and a correct
generated root parent, but seven body/Figure groups drove the branch upward at
runtime. R4 removed only the two body-route Chain resources' backpack groups,
kept 21 other runtime resources byte-identical, and received user acceptance.
This supports the method, not its project-specific anchor or group numbers. See
[`MERCHANT_KARIN_DR03.md`](cases/MERCHANT_KARIN_DR03.md).

The Wasakura/Luis skirt sequence adds a mirrored-branch warning. Suppressing one
side normalized that side but exposed the same failure class on the opposite
still-dynamic side. The accepted next candidate suppressed both side panels
while retaining center/back physics. A unilateral fallback can therefore be a
diagnostic result rather than the final product decision. See
[`LUIS_KARIN_WASAKURA.md`](cases/LUIS_KARIN_WASAKURA.md).

## Release Orchestrator Stops After A Successful Tool

When an outer PowerShell release script invokes a child `.ps1` wrapper, a bare
`exit $LASTEXITCODE` in the child can terminate the outer script before staging,
contract generation, packaging, or verification. The tool may have succeeded,
so logs misleadingly end on a successful Blender message.

For wrappers intended for both direct and nested use:

1. run the native executable;
2. capture/check its exit code immediately;
3. throw on non-zero;
4. return normally on success;
5. let the outer orchestrator own phase sequencing and its final exit status.

Parse/compile the wrapper and outer script before the heavy phase. Keep an
operation-appropriate process guard in the canonical release entry point, and
validate the final machine report so console completion cannot substitute for
downstream evidence. A workspace-only build and a deployment transaction do not
have the same process preconditions; see `VALIDATION_AND_RELEASE.md`.

## Transparency Fault Tree

1. Close every final triangle from source object/material through texture page
   and runtime render class; reject role-level page guesses.
2. Inspect all source representations for richer alpha or UV semantics.
3. If restoring a local UV island from a sibling container, require a unique
   one-to-one match for all target triangle corners, write per loop, and prove
   non-target UVs unchanged.
4. Parse final Mesh material index and MDF material array.
5. Decode ALBD/NRMR/ATOC and inspect the actual controlling opacity channel.
6. Determine cutout versus continuous-blend intent per surface.
7. Split the continuous region into an exclusive submesh/material if needed.
8. Set the correct transparent master material and disable alpha test where
   appropriate.
9. Neutralize unrelated effects inherited from a transparent donor layout.
10. Apply a documented opacity transformation only to the intended surface.
11. Verify material/submesh draw order for overlapping transparent pieces.
12. Recheck source/authoring/final geometry clearance independently.

Do not apply one opacity floor to every material sharing an atlas. The Luis
raincoat and visor needed separate surfaces and separate case-specific floors.

## Constant-White Surface Fault Tree

1. Bind the observation to a candidate when possible and determine whether the
   whiteness is invariant under lighting or camera changes.
2. Reproduce the view with neutral front/rear/side source renders; isolate
   objects or apply temporary tints until the visible triangles are known.
3. Parse the source glTF/VRM primitive `material` field. Count valid, missing,
   and out-of-range bindings instead of trusting imported material-slot names.
4. Trace base-color factor/texture and emissive factor/texture in the source.
5. Inspect actual shader-node links. A saved strength/value on a disconnected
   socket is not an active effect.
6. Parse the final Mesh material table/submesh indices and MDF master,
   parameters, and TEX paths; decode the bound TEX channels.
7. If source intent is absent, create a documented surface-scoped fallback and
   assert every unrelated material mapping remains unchanged.
8. Re-import, decode, build twice, and require runtime validation under relevant
   lighting.

Do not add emission merely because the result is white. The
[`Chrome Merchant case`](cases/MERCHANT_KARIN_CHROME.md) found one unbound
primitive, zero source emissive materials, and an inactive unlinked Blend
emission socket. A dedicated non-emissive PBR override fixed the accepted
scope.

## Consumer And Costume Fault Tree

When one route is wrong:

- verify its PFB dependencies and logs;
- for late transitions, correlate the dump timestamp with the immediate
  PFB/Mesh/MDF accessed and loose-hit window before assigning route ownership;
- compare path/hash aliases with the accepted default artifact;
- include Mesh, MDF, Chain, and control resources separately;
- derive gameplay material/property queries per consumer and close every
  existing/requested MDF alias rather than copying the default route's set;
- preserve special placeholders instead of replacing them with body geometry;
- do not add current-missing aliases without a requesting consumer;
- test each route/costume after a cold start.

Default-route visual success says nothing about alternate consumers that were
never requested during that test.

## Runtime Tree Drift

Use a four-way comparison:

```text
master candidate contract
candidate files on disk
transaction state source
actual game tree
```

Classify target paths as `missing`, `same`, or `conflicting`. A candidate subset
can be exact while the complete tree fails because another Mod added unrelated
files. That is non-candidate base drift, not proof that the candidate is corrupt.

Never delete unexpected files merely to make a count match. Preserve external
changes and refresh the baseline when the tree becomes stable.
