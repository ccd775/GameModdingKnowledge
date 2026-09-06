# Technical Contracts

> Status: active
> Scope: reusable RE4R character-resource contracts
> Last verified: 2026-08-15
> Evidence level: mixed invariant and case-derived; project values require re-verification
> Evidence basis: Ashley/Karin Y, Luis/Karin Riptide, Luis/Karin Wasakura,
> Merchant/Karin Cloth04, Merchant/Karin DR03, Merchant/Karin Chrome,
> Ada/Karin Nyako, Krauser/Karin SSF, and Leon/Karin Umbrella

## 1. Consumer And Path Contracts

The runtime consumer, not the source asset, determines packaging.

For every path answer:

- Which PFB/component/route requests it?
- Is it default, alternate costume, cutscene, Mercenaries/other mode, figure,
  expression, GPU Cloth, suppressor, or shared control data?
- Does the path exist in the current build?
- Which official PAK occurrence wins by priority?
- Is it replaced, aliased, patched, preserved, or intentionally absent?
- Which exact generated artifact supplies it?

Do not infer that equal-looking filenames are aliases. Prove aliases by current
dependency data, runtime logs, or reference/control evidence. Do not synthesize
missing aliases without a consumer.

`invariant` method with `case-derived` runtime evidence: do not infer the active
consumer from chapter, boss-form, Figure/gallery, variant, or filename
semantics. A Campaign event may instantiate a resource family normally
associated with another surface. When a failure appears only at a late
transition, bind the dump timestamp and correlate PFB/Mesh/MDF accessed and
loose-hit records in the immediate fault window. Append the observed ownership
to the consumer matrix and retain the earlier route pass within its narrower
scope. The r10 Krauser rejection and r11 acceptance demonstrate this method;
the `chf700` case value itself is not reusable. See the
[`Krauser case`](cases/KRAUSER_KARIN_SSF.md#late-transitions-can-activate-a-different-consumer-family)
and its project-local
[`route-attribution report`](../../SOURCE_REFERENCES.md#local-only).

Keep a canonical artifact separate from its runtime aliases. Build once, then
copy byte-identical outputs to the exact verified consumers. The manifest should
record both the canonical source and each consumer path.

## 2. Reference Mod And Native Roles

Use current native resources for:

- resource versions and binary schemas;
- current PFB/RSZ structure;
- actual dependency paths;
- route-specific Chain headers/settings donors;
- JCNS/JMAP/FBXSKEL and shared-resource behavior;
- archive priority and absence evidence.

Use a reference Mod for:

- target-path discovery;
- a known-good loading control;
- donor skeleton/rest pose when current native extraction is insufficient and
  compatibility is separately proved;
- examples of suppressors/placeholders;
- visual intent and hypotheses.

Never inherit unrelated reference props, weapons, sound, UI, test objects, or
environment assets merely because they are present in the donor tree.

A successful reference can prove that a structural technique is viable, such
as a valid hidden submesh backing a query-only material. It does not prove that
the reference's material names, record bytes, ordering, aliases, or query set
belong to the current consumer. Derive those values from the current native
route and executable/component behavior, then use the reference only as an
independent structural control. This is an `invariant` authority rule; the
runtime-confirmed case-derived example is the
[`Krauser r11 Figure closure`](cases/KRAUSER_KARIN_SSF.md#late-transitions-can-activate-a-different-consumer-family).

## 3. Mesh And Rig

### 3.1 Partitioning

Partition by target consumer slot. A common replacement may need separate body,
static face, and head/hair Meshes plus scoped suppressors, but the actual split
is character-specific.

Do not clone the full replacement into special `01`, `02`, `21`, `50`, or other
slots based only on naming patterns. In the Ashley case, several such slots had
GPU Cloth, suppressor, or attachment semantics.

### 3.2 Bone classes

Classify bones before building:

| Class | Contract |
| --- | --- |
| Core animation | Target names/parents/rest orientation follow the animation base donor |
| Weighted physical/attachment | Full parent closure; geometry and rest transforms move coherently |
| Chain terminal/helper | Present in Mesh; correct parent/order/hash; normally zero weighted assignments |
| JCNS/control compatibility | Present only when a current consumer requires it; usually unweighted |
| Unused source | Collapse by an explicit deterministic mapping or remove with proof |

Every weighted bone and every Chain/JCNS/collider reference requires complete
parent closure up to an accepted root.

### 3.3 Weights

Choose the maximum influences from the verified target/tool contract. The
current case projects enforced four influences even though some tooling can
represent more; four is a project precedent, not a universal format law.

After truncation:

- remove invalid groups;
- renormalize positive weights;
- reject any unweighted vertex;
- record maximum sum error and quantization tolerance;
- distinguish true deform weights from zero-weight compatibility bones;
- compare positive-weight group sets after Mesh re-import.

Audit every positive influence, not only the dominant influence. A small weight
assigned to a remote or incompatible pivot can still stretch triangles at
runtime even when sums are normalized and dominant-bone checks pass.

Neutral-pose checks are insufficient for short articulated chains. Finger and
toe vertices may look correct at rest yet orbit incompatible target pivots under
a weapon grip, trigger pose, or toe rotation. Measure per-joint source geometry
and final animation-pivot residuals for every positive influence, then validate
the target-specific action that exposes the joint. When the target animation
skeleton is immutable, a bounded per-joint geometry prefit can be a valid local
compatibility layer, but it must freeze the target rest bones, affect only the
declared weighted geometry, and pass continuity and posed-bounds gates. This is
the `case-derived` repair used for the Leon/Karin Umbrella fingers; its bone set
and transforms are not reusable. See
[`LEON_KARIN_UMBRELLA.md`](cases/LEON_KARIN_UMBRELLA.md#small-joint-pivots-need-action-specific-proof).

### 3.4 Rest transforms

Match both position and direction. Moving bone heads/tails without preserving
roll or rest-frame orientation can produce correct-looking static geometry and
wrong animation/physics.

Select the intended proportion contract before transforming geometry:

| Strategy | Coherence requirement | Main tradeoff |
| --- | --- | --- |
| Preserve source proportions | Establish one measured source coordinate frame for geometry and directly mapped anchors; solve unmapped rest data explicitly, then derive bind and skeleton resources from the final armature | Animation/IK compatibility still needs runtime proof |
| Conform to donor animation proportions | Use explicit per-anchor or per-limb mappings against the donor skeleton | Source limb and body proportions may change visibly |
| Correct a local attachment | Move one bounded rigid package or use a documented taper while freezing unrelated anatomy/rest data | Transition and pose deformation require focused gates |

Target animation translations can encode the target's authored rest intervals.
Moving core rest heads to source landmarks may therefore look proportionally
correct offline but re-extend or compress the source body at runtime. Conversely,
per-bone donor-directional conformance can preserve animation compatibility
while visibly changing the source silhouette. Audit both rotation and
translation in representative target animations before accepting a proportion
strategy.

One coherent hybrid is exact target core-animation rest plus one measured global
source-geometry frame, with physical branches placed coherently and only
explicit bounded local prefits. This worked for Leon/Karin Umbrella after both
per-bone donor conformance and moved-core-rest candidates failed. It is a
`case-derived` option, not a universal default; the `invariant` requirement is
to declare which rig owns animation rest, which geometry owns proportions, and
where local exceptions are permitted.

Apply scale and translation exactly once. If a point is already in absolute
target space, do not divide or multiply it again by the scale: doing so also
changes the translated component and can separate vertices from their pivots.
Never mix cached exporter rest-matrix properties from one rig state with newly
rebuilt rest transforms. The property names and cache behavior are
tool-version-sensitive and require an import/export/re-import identity test.

Normalize object-level binding before export. Remove unintended Armature object
parents and stale `matrix_parent_inverse`, apply the declared object/world
transform exactly once, and retain only the intended Armature modifier. Validate
this normalized scene contract independently in clean authoring roots. A final
runtime binary can coincidentally match while the editable scene still contains
a 100x/axis defect; binary equality does not make that scene a trustworthy next
authoring baseline. The Wasakura/Luis case provides the negative example.

For a rigid local package, move:

- every vertex belonging to the visual attachment/part;
- all dedicated physical rest bones;
- any collider/rest data derived from those bones;
- all runtime aliases of the same Mesh.

Any moved dynamic rest bone invalidates the prior Chain acceptance. Re-run
frame, collider, ancestry, topology, and route audits. A common rigid
translation that preserves all directions and relevant local relationships may
retain byte-identical Chain files when the audit proves no serialized semantic
change, as in the Ashley tail/head package. Rotation, nonuniform transform,
changed local frames, or uncertain semantics requires rebuilding every affected
Chain, as in the Luis water-gun package.

#### Segment-coherent deform and physics packages

One connected source object is not necessarily one rigid semantic package. A
long sleeve, skirt panel, rope, or layered accessory can span two animation
segments while also carrying physical branches. Assign transforms from source
anchor semantics, not from object membership or connected-component identity.

For each declared segment:

- name the source and target anchors, source physical roots, and expected parent
  target;
- compute one source-to-target rest-frame matrix;
- apply that exact matrix to the segment's static weight transfers and physical
  rest-bone placement;
- retain the original normalized weight blend for vertices influenced by more
  than one segment;
- parent each transferred physical root to the matching target segment instead
  of forcing every branch into one forearm, upper-arm, or torso space;
- verify segment membership, matrix equality, parent closure, and positive
  influence coverage after Mesh re-import.

For a sleeve crossing the elbow, upper-arm-weighted vertices may legitimately
use an upper-arm frame while forearm-weighted vertices use a forearm frame. The
blocking gates are continuity under representative elbow poses and a cuff plane
aligned with the target forearm, not the claim that the entire connected sleeve
uses one matrix. The Nyako/Ada case is the reference for the four-segment
upper-arm/forearm pattern; its source bone names, counts, and matrices remain
`case-derived`.

#### Footwear contact frames

Treat these as separate contracts:

1. evaluated source foot shape, including saved shape keys;
2. foot-to-shoe fit;
3. shoe/rest-package orientation;
4. shoe-to-target-floor placement under animation and IK.

A `Foot -> Toe` bone direction is not a sole normal. The Nyako/Ada R8 runtime
rejection showed that forcing a flat shoe to a scalar foot-bone angle could
tilt an originally horizontal sole while every minimum-Z floor check still
passed. That proxy is `rejected` for flat-sole orientation.

For a planar or near-planar sole, fit an independently identified low-contact
surface and construct a complete orthonormal source frame from its normal plus
the source `Foot -> Toe` vector projected into the plane. Construct the target
frame from the independently justified target-floor normal plus the target
animation donor's horizontal foot-forward projection. The frame mapping is:

```text
R = target_frame * transpose(source_frame)
```

Apply one matrix per side to every intended rigid/static shoe attachment and to
all physical rest descendants in that foot package. Recalibrate any later
ground offset after this rotation; an offset measured for an earlier frame is
stale.

Validate the actual exported shoe, not only the requested transform:

- fitted sole-normal tilt against the declared target plane;
- front-to-back contact-surface height delta;
- plane-fit RMS/thickness and sufficient contact-surface coverage;
- left and right floor residuals against independent target/donor evidence;
- exact static-transfer and physical-rest matrix equality per side;
- unchanged topology, material assignment, weights, and unrelated rest data.

Project thresholds, contact-face counts, offsets, source saved key values, and
the decision to use world vertical are `case-derived` or `build-sensitive`.
Runtime stance, IK, and scene-floor contact still require candidate-bound user
evidence. See [`ADA_KARIN_NYAKO.md`](cases/ADA_KARIN_NYAKO.md).

### 3.5 Bind space and shared FBXSKEL

A parsable Mesh is not necessarily in a compatible bind space. Normalized
weights, valid indices, finite matrices, and small world/inverse residuals are
necessary but not sufficient.

For each runtime Mesh/FBXSKEL combination:

- prove every packed positive palette index is below `remapCount` and resolves
  through the serialized remap list to the intended Mesh bone;
- measure absolute vertex-to-pivot distance for every positive influence and
  absolute posed bounds under diagnostic rotations;
- compare Mesh-bone local/world translations, neutral target-space bounds,
  critical feature-to-anchor distances, and absolute Mesh-versus-FBXSKEL rest
  residuals;
- report expected comparisons, actual comparisons, and every missing Mesh,
  FBXSKEL, weighted, or parent name; an empty comparison set is a failure;
- validate bone names, serialized order, parent indices, local/world rest
  transforms, hashes/symmetry data, segment scaling, and pose/export mode;
- re-import the serialized FBXSKEL and compare its semantic state;
- classify each weighted Mesh bone as shared-FBXSKEL or proven Mesh-local. The
  shared class must resolve in FBXSKEL; a Mesh-local physical branch instead
  needs its own parent/rest/remap/Chain/export proof;
- require every FBXSKEL bone expected by a slot to exist in that Mesh;
- for all slots sharing one FBXSKEL, compare post-export rest matrices only for
  the declared shared set, normally the intersection of the FBXSKEL and the
  relevant Mesh slots, and reject disagreement;
- run a known-incompatible negative control and require the validator to reject
  it.

Treat FBXSKEL as dependent on the final Mesh armature contract. Generate it
twice from clean roots, require byte/semantic determinism, and invalidate its
acceptance whenever participating Mesh bone order or rest data changes.

Generation is not always the correct deployment action. When the final Mesh
proves exact closure on the current native animation-core set and every added
weighted physical branch is independently proven Mesh-local, a byte-identical
current-native FBXSKEL copy can be the narrower contract. Conversely, a changed
shared rest/order requires a generated compatible resource. In both cases, take
the runtime path and suffix from current consumer evidence; do not rename a
verified `.fbxskel` payload to a speculative `.skeleton` alias because the
contents appear related. The Nyako/Ada case demonstrates the native-template
strategy; its paths, shared set, and counts are `case-derived`.

Thresholds, allowed Mesh-local extras, skeleton generation strategy, and
consumer path are build- and project-sensitive. See the
[`Merchant/Karin Cloth04 case`](cases/MERCHANT_KARIN_CLOTH04.md) for the failure
that established these gates.

### 3.6 Shape keys and authored saved state

Before deleting shape keys, audit current values in all supplied source forms.
Blend and FBX can save a non-Basis state. Required report fields:

```text
object
shape key
saved value in each source
requested bake value
affected vertex count
maximum displacement
applied true/false
removed_without_bake true/false
```

The Luis case lost both a high-heel foot pose and the visor extension because a
builder deleted keys and retained Basis. This failure mode applies to any source
model, not just VRChat exports.

The Merchant case independently confirmed the same class of failure. Use an
explicit bake whitelist and fail on unexpected non-zero, animated, driven, or
muted saved states. Reopen the locked source independently and compare evaluated
geometry rather than trusting only the builder's own bake report.

The audit scope is every retained object, not only face or footwear. The
Leon/Karin Umbrella sequence first found ten missing sneaker bakes, then later
found two nonzero `Hair_Main` states after a footwear-focused repair. Require an
exact retained-object/key/value inventory, affected-vertex count, maximum
displacement, and, for every required nonzero bake, a matched negative control
that fails when the bake is omitted.
This is an `invariant` coverage rule; the key names, values, and displacement
numbers are case-derived. See
[`LEON_KARIN_UMBRELLA.md`](cases/LEON_KARIN_UMBRELLA.md#audit-saved-shape-on-every-retained-object).

Topology preservation does not prove visibility preservation. A saved key can
move an intact clothing or rope mesh inside the body while vertex and triangle
counts remain exactly unchanged. For a reported missing part, compare evaluated
source and built positions, affected-vertex counts, displacement directions,
and clearance to the body before concluding that vertices were deleted. The
Nyako/Ada Thin `BodyRope` failure is the reference negative case.

### 3.7 Visibility, fragments, and submeshes

Visibility groups are runtime semantics. Source object numbering is not a valid
group map. `Group_0` is a useful always-visible starting policy: Ashley had
runtime-observed loading/visibility evidence for it, while Riptide/Luis r4 is
only offline-accepted and still needs user runtime validation. Re-audit every
new target's hide/show behavior.

Submesh compaction is permitted only when:

- index/vertex limits remain valid;
- triangle sets by material are unchanged;
- material-name order and indices remain valid;
- UVs, normals, weights, and bounds remain within tolerances;
- required runtime visibility granularity is preserved.

Keeping fragments can be safer when transparent draw order or isolated
materials need explicit control.

### 3.8 UV layer routing

UV identity is positional at the serialization boundary unless the pinned
exporter proves otherwise. A layer name, Blender active/render flag, or correct
source preview does not establish which runtime UV stream receives that data.

Record and verify this chain for every material-bearing surface:

```text
source material's intended UV set
-> authoring layer name and positional index
-> serialized Mesh UV stream/index
-> runtime material/MMTR sample
```

Re-import the final Mesh and compare the runtime-sampled stream to the locked
source intent per loop/corner. A Mesh -> export -> re-import comparison against
itself proves serialization stability around the current mapping; it cannot
detect a consistently wrong source-to-runtime assignment.

When diagnosing a UV-index candidate, freeze topology, material slots,
coordinates, normals, weights, bone hierarchy, and rest matrices. Assert the
exact old-stream/new-stream relationship and require complete surface coverage.
The Wasakura/Luis case is the runtime-confirmed reference for a pinned exporter
that serialized `uv_layers[0]` as runtime UV1 regardless of Blender's active
marker. That exact index behavior remains tool-version-sensitive. See
[`LUIS_KARIN_WASAKURA.md`](cases/LUIS_KARIN_WASAKURA.md).

### 3.9 Face and eyes

A replacement without expressions should say so explicitly. Static strategies
may bind eye, cheek, and facial accessories to `Head`, while retaining necessary
compatibility bone names. This avoids bad pivots but does not provide blinking,
look-at, lip sync, or expression support.

All static facial pieces should use the same head-space transfer. Apparent dirty
cheeks or dark patches may be geometry overlap, normals, or mismatched transfer,
not a texture problem.

## 4. MDF, Materials, And TEX

### 4.1 Material indexing is one contract

Treat these structures as one closed binding graph:

1. final Mesh material-name table and order;
2. MDF material array and order;
3. every submesh `materialIndex`.

Submesh traversal order is not automatically MDF order. Always parse the final
Mesh and construct/validate MDF against it.

Do not reduce this gate to visible triangles. A PFB/RSZ gameplay component may
query a material by name, cache the returned material and property indices, and
later use the material index against another runtime array. For every such
consumer, prove all of the following:

- every queried material name exists exactly once in every array the consumer
  can address;
- every queried property exists with the required hash and value shape;
- the index returned by the lookup resolves to the same intended material in
  each later consumer array;
- the Mesh has a valid serialized material slot and backing submesh when the
  exporter or runtime constructs its addressable material array from submeshes;
- all non-query materials and visible submeshes retain their declared mapping.

Literal Mesh/MDF order equality is the conservative default when an index
crosses array boundaries. A different order is acceptable only when current-
build disassembly or a semantic runtime mapping proves an explicit name-to-
index remap. Equal name sets alone do not prove index equivalence, while equal
counts alone prove neither names nor semantics.

Some compatibility materials are queried by gameplay but have no visible
source surface. Do not append them to MDF alone and stop after the crash
disappears. When current consumer or successful-reference evidence proves a
backing Mesh slot is required, create a minimal valid hidden submesh for each
name. The geometry must survive export/re-import and therefore should be
non-degenerate rather than an empty slot or zero-area triangle. Keep it within
the existing vertex layout and influence policy, place/weight it so it does not
expand visible bounds or per-bone bounding boxes, and assert that every visible
submesh remains semantically unchanged.

Treat the compatibility query namespace as consumer-scoped and alias-complete.
Do not transplant a fixed name/property set from a passing default body to a
later event, Figure, alternate, or mode route. Derive each consumer's complete
set from current-native material properties plus caller/component evidence. If
that consumer already has multiple requested MDF aliases, close every one and
require byte-identical or explicitly mapped semantics; fixing only the primary
MDF leaves the other alias boundary unproven. This is an `invariant` closure rule
supported by `case-derived`, scoped runtime confirmation in Krauser r11. The
consumer-specific names and counts remain build-sensitive. See the
[`r11 Figure closure report`](../../SOURCE_REFERENCES.md#local-only)
and the project [SOP](../../SOURCE_REFERENCES.md#local-only).

The Krauser/Karin SSF sequence is the runtime-confirmed case-derived example:
an MDF-only compatibility closure removed an unchecked missing-index crash but
left the body Mesh material table shorter, producing checkerboard rendering.
Adding only the missing hidden Mesh backing submeshes closed the runtime
contract. The material names, counts, micro-geometry dimensions, call offsets,
and updater behavior are build- and case-sensitive; reuse the proof method, not
those values. See [`KRAUSER_KARIN_SSF.md`](cases/KRAUSER_KARIN_SSF.md).

Also close source semantics through the final triangles. For every final
triangle, prove its source object/material, texture page, and runtime render
class. Report expected triangle count, matched count, ambiguous mappings, and
errors. A role-level guess such as body/face/hair, or matching only the final
material names, cannot detect a wrong atlas page or shader class.

### 4.2 Primitive bindings and shader connectivity

For every source glTF/VRM mesh primitive, record either its valid material
index or an explicit unbound state. An importer or optimized authoring file may
synthesize a slot such as `Default_Material`; this is fallback representation,
not proof of authored material intent. Source-to-runtime triangle closure is
incomplete when it silently treats that fallback as an ordinary authored
binding. Count unbound primitives and triangles, then document the deliberate
fallback or override for each one.

Do not diagnose a constant-white surface as missing emissive from appearance
alone. Trace source base-color and emissive factors/textures, Blender node links
through BSDF/output, and final Mesh/MDF/TEX semantics. A saved emission strength
on an unlinked or black socket contributes nothing. Missing material or base
PBR fallback can render bright white; adding emission may amplify the defect.

When one bounded surface needs a correction, assign a dedicated runtime class
or derived TEX only to its proven triangle set and assert all unrelated
material mappings are unchanged. See the
[`Chrome Merchant case`](cases/MERCHANT_KARIN_CHROME.md).

### 4.3 Packed channels

Do not infer channel semantics from a filename. Audit source documentation,
source pixels, donor material properties, and generated output. Inspect every
locked source representation: an optimized Blend/atlas may have discarded an
alpha mask, UV island, or material scalar that remains in a sibling VRM/FBX.

Record for every TEX:

- semantic role by channel;
- dimensions and mip count;
- GPU format;
- sRGB or linear interpretation;
- source image/channel;
- transform such as inversion, normal-Y flip, threshold, or floor;
- decoded comparison metrics.

Round-trip all RGBA channels, not only a previewed RGB image.

Surfaces that share atlas RGB and UVs can still require separate derived TEX or
MDF variants for metallic, roughness, opacity, or render-class semantics. Do
not replace those distinctions with one page-level constant.

When the target triangle corners have a unique one-to-one geometric
correspondence, a missing local UV island may be restored from a richer sibling
source container even if global vertex indexing or a small number of unused
vertices differs. Require complete target-surface coverage, write UVs per loop
so seams survive, state any coordinate conversion, and prove every non-target
loop hash is unchanged. Ambiguous correspondence or incompatible target
triangulation rejects this recovery method.

### 4.4 Transparency layers

Separate three questions:

1. **Geometry:** are the surfaces physically on the intended side of each other?
2. **Opacity contract:** is the material cutout/alpha-test or continuous blend,
   and which channel controls opacity?
3. **Draw order:** in what material/submesh order do overlapping transparent
   surfaces render?

Changing draw order cannot move an attachment outside clothing. Moving geometry
cannot restore pixels discarded by alpha test.

Continuous transparent regions often require:

- their own submesh/material;
- an appropriate transparent MMTR/master material;
- alpha test disabled;
- an explicit opacity texture/channel;
- no accidental sharing with an opaque/cutout material;
- a deliberate material/submesh ordering relative to other transparent parts.

Choose continuous blend versus cutout from actual source alpha distribution and
render intent, not an inherited material name. When borrowing a continuous
transparent donor, preserve its complete compatible parameter/texture layout
and explicitly neutralize unrelated eye, glass, oil-film, reflection, or effect
features. Copying only the master-material path can leave hidden donor effects
active.

ALBD alpha is not generically opacity. In the Ashley packing it carried a
dielectric/metal semantic, while opacity was in ATOC.R. Re-audit each source
packing instead of applying that mapping globally.

### 4.5 Streaming policy

The stable local pattern is one complete custom TEX at its ordinary
MDF-referenced path and no duplicate complete custom TEX under loose
`natives/STM/streaming`.

This rejects the specific dangerous “ordinary low-resolution plus duplicate
complete streaming copy” layout seen in early Ashley work. It does not prohibit
a proven native low/high streaming pair required by a future target. Such a pair
must have current-format/tool support, a consumer contract, and separate
runtime evidence.

### 4.6 Deterministic encoding

Pin encoder, flags, format, colorspace, mip generation, and CPU/GPU path. The
current projects used deterministic CPU BC7 settings because GPU encoding could
vary. Decode generated TEX and compare with documented thresholds appropriate to
the chosen lossy format.

## 5. Chain Physics

### 5.1 Source physics is semantic evidence

VRM spring definitions provide useful roots, paths, drag/stiffness/gravity, and
collider semantics. They do not map one-to-one to RE Chain solver fields.

First prove the coordinate mapping from the source VRM to the optimized rig.
Then map only paths present in the final Mesh.

Read the source spring root together with its parent hierarchy. A visible first
segment may remain weighted and follow its animated parent while intentionally
staying outside the simulated path. Do not infer the dynamic root from the first
visible bone, the first mapped target, or a list position.

### 5.2 Terminal/dummy semantics

The last node of a normal RE Chain group is commonly a terminal/dummy and may
not behave as a deforming simulated segment. Therefore:

- do not copy terminal settings to every internal node;
- do not let an optimized-away end bone turn the real dynamic root into the
  terminal;
- when needed, append a collinear, zero-weight, non-deforming terminal helper at
  the real root's tail;
- verify the helper by zero positive weight assignments after binary re-import,
  not only Blender's `use_deform` flag;
- avoid unproven one-node normal groups.

The Luis fringe/ribbon correction is the reference case for this pattern.

Terminal semantics are branch-specific. A source/reference endpoint may be a
positive-weight deform segment that must remain weighted, while another branch
needs a new zero-weight terminal helper. Likewise, a positive-weight attachment
anchor can remain fixed outside the Chain path while its child is the true
dynamic root. Prove fixed anchor, first simulated node, endpoint, and terminal
roles independently; do not blanket-zero or collapse every last bone. The
Leon/Karin Umbrella twin tails, tail, and central fringe provide the matched
negative and accepted examples.

### 5.3 Group topology

Audit:

- dynamic root and complete node path;
- terminal identity/hash;
- repeated driven bones across groups;
- shared/overlapping branches;
- missing or duplicated terminals;
- parent closure in Mesh;
- collider ownership and local transform.

Overlapping groups can repeatedly drive one bone. Splitting them may restore
segmented response, but it does not by itself create natural static droop.

Also compare source weighted deform intervals with ordered unique positive
targets in the final Mesh. Many-to-one collapse removes spatial degrees of
freedom and can produce stepped tail or hair curvature that parameter tuning
cannot restore. Report every collapse, fixed-anchor span, simulated span, and
terminal role before adjusting spring or damping. The accepted number of tail
targets in the Leon/Karin Umbrella case is case-derived; preservation of
adequate authored curve resolution is the reusable gate.

### 5.4 Rest frames before parameters

Recompute node frames from final rest geometry and validate an axis against the
successor/rest-tail direction. A wrong rest frame can rotate a sleeve or other
part roughly 90 degrees even when the outline looks plausible from one view.

Reconstructed or redirected rest bones invalidate inherited reference
angle-limit quaternions even when names and node counts remain valid. Near
opposite frame/successor directions can send hair continuously upward or fold
ears inward. Rebuild frames from the final hierarchy first and retain the
rejected inherited-frame candidate as a negative control. The Leon/Karin
Umbrella v4 frame audit measured this failure before v7 acceptance; its exact
angles are case values.

Only after topology and frames pass should tuning change:

- `springCalcType`;
- spring force and damping/damping power;
- gravity direction/magnitude and per-node coefficients;
- angle limits and hardness;
- wind coefficients;
- collision shapes and collider groups.

Do not react to “stiff when still, spins when moved” by blindly reversing
gravity or quaternion signs. First prove node role, terminal structure, frame
direction, repeated paths, and source rest pose.

### 5.5 Collision is a separate variable

Gravity/droop and collision/penetration are different hypotheses. A chain can
move naturally and still intersect the body, or collide without developing the
desired rest silhouette. Isolate collision candidates from parameter candidates.

Map source collider centers through the same final source-to-target transform
used by the physical rest rig. Then derive the serialized target-bone-local
offset with the target rotation convention and reconstruct every result back to
world space. Record:

- source and final collider centers;
- source/authoring units and all applied scale factors;
- target owner bone and its final rest transform;
- serialized local offset magnitude;
- reconstructed world-center error;
- scale-relative bounds and a known unit-defective negative control.

Do not pass a collider through a stale armature inverse containing an authoring
scale. The Wasakura/Luis failure converted a source `0.01` scale into offsets of
tens of metres while all files still parsed. Exact values are case-derived; the
world reconstruction and unit-sanity method is invariant.

### 5.6 Chain acceptance

For every runtime route:

- use the correct current route donor/header;
- build twice byte-identically;
- re-import with the pinned Chain editor;
- compare groups, settings, nodes, terminals, colliders, wind, and intended
  semantic diffs;
- prove all hashes/names resolve to Mesh bones;
- audit frame angular error against a project threshold;
- prove no unintended static fallback or repeated drive;
- invalidate prior acceptance when a participating rest bone changes, run the
  impact audit, and rebuild unless a common rigid translation is proven to
  preserve all relevant directions, local relationships, and serialized
  semantics.

### 5.7 Runtime-rejected branch fallback

A branch-scoped isolation method is an `invariant`; the decision that a
particular branch may remain static and every anchor/count used to implement it
are `case-derived`.

A branch can satisfy every offline structural Chain gate and still rotate,
lift, diverge, or collide incorrectly at runtime. When the static source,
authoring, and exported rest placement are correct and the generated root has
the correct parent, treat the runtime solver as the first failing layer. Do not
broaden the candidate to Mesh geometry, weights, FBXSKEL, and tuning at once.

A branch-scoped static fallback may retain geometry, weights, physical bones,
and FBXSKEL local hierarchy while removing every Chain group that can drive the
branch. It is valid only when:

- the retained root has a proven animated parent and complete serialized
  closure;
- no other PFB, JCNS, collider, or control consumer requires a Chain-driven
  branch;
- every route is audited and contains zero rejected-branch path members;
- unrelated Chain groups and all non-Chain runtime resources remain identical
  to a matched accepted baseline;
- static pose/deformation checks pass;
- loss of secondary motion is explicit;
- the exact package receives runtime evidence.

Do not filter only paths whose first node equals the original branch root.
Merge or overlap segmentation can trim a shared prefix and leave groups that
start at descendants. Match every node against an explicit branch-membership
set or a validated source-name prefix, then assert the exact suppressed group
set, retained static-bone closure, expected remaining groups, and zero survivors
in every deterministic run.

Keep runtime observation labels separate from source-branch identity. A
screenshot can prove that a visual side is collapsed, inflated, or displaced
without proving that geometry migrated across the body or that the named
`left`/`right` source branch is the one visible on that side. Use a one-branch
matched candidate to establish causality. If the suppressed side normalizes
while the opposite still-dynamic mirrored branch shows the same failure class,
a bilateral suppression can be the next single coherent variable. Retain any
independent center/back or unrelated branches that remain stable.

The runtime-accepted DR03 Merchant backpack fallback is the reference case for
this pattern. Its anchor, bone range, spring-group numbers, and group counts are
case-derived and must not be copied. See
[`MERCHANT_KARIN_DR03.md`](cases/MERCHANT_KARIN_DR03.md). The
[`Wasakura/Luis case`](cases/LUIS_KARIN_WASAKURA.md) extends the evidence to a
mirrored cloth system where both side panels became static while center/back
physics remained active.

## 6. PFB, RSZ, JCNS, GPU Cloth, And Skeletons

### 6.1 PFB is build-sensitive

Never patch a PFB from a remembered offset. Derive the offset from a locked
current input and schema, then require:

- input hash match;
- parse to EOF before and after;
- intended resource arrays and userdata unchanged;
- expected file size behavior;
- exact byte diff count;
- exact semantic field diff;
- second build identical.

Treat the PFB resource table and RSZ component fields as separate path-binding
layers. A replacement path present in the table does not prove that
`via.render.Mesh`, `via.render.ComputeSkinning`, `via.motion.Chain`, or another
component instance references it. For every changed dependency:

- identify all table and component occurrences from the current parsed input;
- patch both layers when the consumer contract requires both;
- require the final table path and component path to resolve to the same
  packaged resource;
- preserve or deliberately rebuild RSZ alignment when string lengths change;
- assert expected occurrence counts, exact semantic diffs, and dependency
  closure for every consumer route.

A PFB may parse and load while a component still requests the native path,
leaving the intended custom body absent. A tiny placeholder has broader causes,
including a wrong scoped consumer, suppressor, route family, or skeleton
contract. Keep those observations separate: Nyako/Ada R2 tied resource-table/
RSZ divergence to an invisible body while independent prop geometry remained
visible; its earlier R1 tiny cube did not specifically prove that divergence.
The case's equal-length aliases and occurrence counts are `case-derived`, not a
general format requirement.

An old reference PFB may load in one tested scenario and still contain stale or
unknown fields. That is scoped compatibility evidence, not current authority.

### 6.2 Independent components

JCNS, GPU Cloth, GPUC resources, GPUClothCharacterPart, dummy skeletons, and
other components may have independent enabled flags and dependencies. Disabling
one Bool is not proof that all related construction paths are disabled.

Audit component arrays and current PFB dependencies as a graph.

### 6.3 JCNS and JMAP

Required JCNS bones form a compatibility contract even if they are unweighted.
Build their parent closure and stay within format/tool bone limits. Passing the
bone set is necessary structure, not proof that JCNS will work with a retargeted
rest skeleton.

If the replacement intentionally uses a static face, preserve native JMAP/JCNS
where appropriate and declare that expressions are unsupported. Copying an old
JMAP does not create expression compatibility.

### 6.4 Skeleton blast radius

Prefer character-scoped FBXSKEL/skeleton paths. Before touching a shared
skeleton:

- resolve every current consumer;
- compare bone sets and control joints;
- identify extra joints such as lights or weapon anchors;
- build a single-variable runtime candidate;
- provide a rollback that does not disturb other characters/Mods.

## 7. Suppressors And Placeholders

Some native consumers must remain structurally present while their visible
payload is hidden. A tiny scoped suppressor can be correct when proven by a
reference/control and current consumer audit.

Requirements:

- valid target Mesh version and re-import;
- minimal geometry within format limits;
- exact consumer path;
- no unrelated MDF/TEX/strand dependencies;
- no use as a universal replacement for unknown slots;
- explicit entry in the consumer matrix and forbidden-resource audit.

## 8. Resource Versions

Resource suffixes and schemas are build-sensitive. The current case work on
Steam build `22377325` observed Mesh `221108797`, MDF2 `32`, TEX `143221013`,
Chain `53`, PFB `17`, and other project-specific versions. These values belong
to those case snapshots. A new task must read magic/version from current native
resources and verify its installed tool support before authoring.

## 9. Known Working Toolchain Snapshot

The Ashley, Luis, and Merchant case projects converged on this local snapshot:

- Blender `4.5.12 LTS` through a project-pinned background wrapper;
- RE Mesh Editor `0.66`;
- RE Chain Editor `14.0`;
- RE Asset Library `0.25` where needed;
- a project-locked REasy schema for PFB/RSZ inspection and field patches;
- DirectXTex CPU BC7 with fixed options for deterministic texture encoding.

This is evidence that the versions worked for the locked build and assets, not
a permanent recommendation. Record add-on hashes and run an import/export/
re-import identity test in every new project, especially after Blender, game,
or schema updates.

## 10. Wwise Voice Path Aliases

Voice replacement can be a path-alias operation rather than audio authoring.
If a reference places one actor's byte-identical Wwise payload under another
actor's runtime path, prove that identity before attempting conversion, event
editing, or bank reconstruction. A matching filename pattern alone is not
proof; compare complete payload hashes against current official resources in
archive-priority order.

Treat the voice feature as a dependency closure, not a collection of obvious
media files. Audit all applicable layers:

- Wwise sound banks and media banks;
- language-specific banks for every supported locale;
- streamed/package containers such as SPCK where present;
- USER banklist, container, package, and trigger resources;
- mode-specific aliases such as Mercenaries paths.

Do not assume that a `voice_emo`-named subset is independently loadable merely
because the requested symptom is breathing or damage reactions. General,
`voice`, and `voice_emo` banks can be joined through metadata and event routing.
Promote a smaller subset only after its dependency graph and an exact runtime
candidate pass. Otherwise preserve the proven reference closure and document
that its behavioral scope may be broader than the user's example vocalizations.

Current path dictionaries can omit paths present in an older or custom PAK.
For an unresolved entry, generate a narrow set of semantically justified path
candidates, compute the engine's lower/upper path hashes, and require an exact
hash-pair match. Payload duplication can support the alias hypothesis but does
not recover a logical path by itself. Never drop an unresolved USER entry just
because its bytes duplicate another resource.

For a standalone voice add-on, require:

- an explicit logical-path whitelist and expected entry count;
- source/reference/tool hashes and a stated archive-priority snapshot;
- magic checks appropriate to the selected resources (observed examples:
  USER `USR\0`, SBNK `BKHD`, SPCK `AKPK`);
- all-locale coverage or an explicit locale restriction;
- two byte-identical stages and two byte-identical PAK builds;
- independent decompression and payload comparison for every PAK entry;
- filename-hash intersection checks against the companion model package;
- runtime status kept separate from offline package acceptance.

The Karin Umbrella/Leon voice add-on is the case-derived snapshot behind this
contract: 55 campaign paths were byte-identical to current official Ashley
counterparts and different from native Leon, while 8 Mercenaries USER aliases
duplicated the campaign metadata, for 63 packaged entries total. Those actor
IDs, paths, counts, languages, bytes, and hashes are not universal constants.
See the project
[`SOP`](../../SOURCE_REFERENCES.md#local-only)
and machine report
[`ashley-voice-addon-v1.json`](../../SOURCE_REFERENCES.md#local-only).
