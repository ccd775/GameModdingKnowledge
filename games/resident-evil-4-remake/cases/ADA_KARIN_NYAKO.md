# Case Study: Karin Nyako Replaces Ada

> Status: current R9 package snapshot; Thin runtime confirmed for the scoped
> task context, Normal runtime pending
> Project: `RE4/Karin_Nyako_Replace_Ada`
> Snapshot date: `2026-08-06`
> Game build: Steam `22377325`
> Evidence level: R9 package/resource gates are `offline-accepted`; R9 Thin is
> `runtime-confirmed-scoped` for the user-observed flat-sole task context; R9
> Normal and unreported scenarios remain `not-observed`
> Reuse class: mixed `invariant`, `case-derived`, `build-sensitive`, and
> `rejected`. Every concrete route, slot, field, object value, count, bone or
> group ID, transform, angle, threshold, version, path, and hash in this
> snapshot is both `case-derived` and `build-sensitive` unless explicitly
> classified otherwise. Re-measure and re-extract them for another source,
> target, game build, or toolchain.

## Scope And Current Result

This project built two independent Ada replacements from the supplied Karin
Nyako Normal and Thin authoring sources. The current-build Ada resources own
the Campaign, Figure, and Mercenaries runtime contracts. The optimized Blend
files own visible source geometry and saved shape state; the adjacent VRMs
supply secondary-motion semantics. The private reference Mod was used only as
a route and control probe, never as current-build binary authority.

The current candidate is `R9_FLAT_SOLE_CONTACT`, package version `1.0.8`
(`case-derived`, `build-sensitive`). Both packages passed deterministic build,
semantic re-import, manifest closure, clean ZIP re-extraction, and repeated ZIP
identity. Both remain `offline-accepted` at the package/resource layer; no R9
user report provides a complete route matrix. The later explicit acceptance is
bound by continuous task context to the Thin archive and confirms that the
blocking flat-sole stance was resolved sufficiently for acceptance. It does not
confirm Normal, tail settling, Figure, Mercenaries, cold start, or other
unreported scenarios.

Current project-local archives (`case-derived`, `build-sensitive`):

```text
Output/Karin_Nyako_Normal_Replace_Ada_RE4R_build22377325_R9_FLAT_SOLE_CONTACT.zip
SHA-256 5B196E7BAC25914A6C31FAAF96560A7803DA0053F40A37FE816DFC2E59039C8D

Output/Karin_Nyako_Thin_Replace_Ada_RE4R_build22377325_R9_FLAT_SOLE_CONTACT.zip
SHA-256 A0C8F3439819C796166D5DEFF5A58BD909F42F1F572E19A222E0C917C0766F0B
```

The face is static and does not provide native Ada facial animation. Normal and
Thin are alternatives and must not be enabled together. Authoritative current
state is in the project [`SOP.md`](../../../SOURCE_REFERENCES.md#local-only), not
in this snapshot.

## Candidate And Evidence Timeline

Candidate identifiers and every concrete value in this table are
`case-derived` and `build-sensitive`.

| Candidate | Evidence | Narrow conclusion |
| --- | --- | --- |
| R1 | Both variants `runtime-rejected`: the character was invisible and only a tiny cube-like object was visible | Custom payload access did not prove that the consumed skeleton and route families matched the instantiated PFB |
| R2 | `runtime-rejected` in Figure `00-080`: body, face, and hair stayed invisible while separated prop geometry remained visible | Updating the PFB resource table while leaving RSZ component fields native was insufficient |
| R3 | Normal `runtime-rejected`, but body, face, hair, clothing, and materials became visible | Equal-length dual-layer PFB routing was a positive runtime result; arm twist, chest twitch, unwanted source objects, and floor penetration still rejected the candidate |
| R4 | Offline-superseded before runtime | The candidate predated the clarified clothing intent |
| R5 | Offline-superseded; Thin showed native Ada during a zero-file Fluffy deployment | The screenshot did not establish a binary runtime result because no candidate payload had been deployed |
| R6 | Thin `runtime-rejected`; Normal offline-superseded | Thin `BodyRope` geometry remained present but was baked inside the body; sleeve geometry and physical bones used incoherent rest frames |
| R7 | Thin `runtime-rejected`; Normal offline-superseded | The custom model remained visible, but the idle foot stayed on tiptoe and the tail failed to settle and tangled after lateral motion |
| R8 | Thin `runtime-rejected`; Normal offline-superseded | A scalar `Foot -> Toe` angle was not a valid flat-sole contact contract; the feedback supplied no new tail observation |
| R9 | Thin `runtime-confirmed-scoped`; Normal `offline-accepted-runtime-pending` | Direct authoring audits prove a nearly horizontal fitted sole plane; the later Thin-focused acceptance confirms the blocking flat-sole correction for the task-context scope, while tail solver quality and unreported routes remain not observed |

Evidence must remain component-scoped. R3's visibility repair survives as a
positive route result even though R3 is rejected overall. R5's deployment
diagnosis does not reject its packaged Mesh/PFB bytes. R8's foot rejection does
not reject or confirm its tail change because the user did not observe the tail
in that report.

Evidence:

- [`runtime-feedback-r1.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-r2.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-r3.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-r5-thin-deployment.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-r6-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-r7-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-r8-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-r9-thin-accepted.json`](../../../SOURCE_REFERENCES.md#local-only)

## Consumer And PFB Visibility Contract

`invariant` lesson demonstrated by R2/R3: for a PFB schema that stores resource
paths in both a top-level resource table and instantiated RSZ component fields,
the two layers form one dependency contract. A resource preloaded from the
table is not necessarily the resource instantiated by `via.render.Mesh`,
`via.render.ComputeSkinning`, or `via.motion.Chain`. Validate semantic paths in
both layers and require their dependency sets to agree.

The accepted project snapshot covers three current-build route families and
thirteen PFB consumers per variant (`case-derived`, `build-sensitive`):
Campaign `cha200`, gallery `Figure00_080`, and Mercenaries `cha800`. Current
official PFBs, not reference-PFB copies, are the patch inputs. Campaign PFBs
stay paired with Campaign-authored Mesh/MDF/Chain resources; Mercenaries PFBs
stay paired with Mercenaries-authored resources.

R2 changed only the resource table. Its RSZ fields still requested native Ada
resources, so the custom resources could load without becoming the rendered
character. R3 synchronized full Mesh, MDF, and Chain paths in both layers with
the equal-length aliases `nyakon` and `nyakot`. Those aliases are six
ASCII/UTF-16 code units (`case-derived`, `build-sensitive`), preserving file
size and RSZ absolute alignment for the locked inputs. Alias spelling, length,
field offsets, occurrence counts, route list, and resource suffixes must all be
derived again after a build or schema change.

The final PFB pass separately disables six proven
`via.motion.JointConstraints.v0_Enabled` fields per variant
(`case-derived`, `build-sensitive`). It preserves same-route native JMAP paths
and packages no custom JCNS/JMAP files. The package also deploys the exact
current-native character-scoped FBXSKEL payloads named by the Mesh reports,
instead of a generated skeleton at speculative `.skeleton.5` aliases.

Blocking offline checks require semantic EOF parsing, an exact allowed-field
diff, resource-table/RSZ equality, current-build input hashes, preserved binary
shape/alignment, and an isolated second build. R9 has thirteen deterministic
PFB outputs and twenty-two closed custom PFB dependencies per variant
(`case-derived`, `build-sensitive`). These checks explain visibility routing;
they do not prove runtime animation or appearance.

Evidence:

- [`consumer-matrix.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`pfb-r3-determinism.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r9-pfb-determinism-normal.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r9-pfb-determinism-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`patch_ada_pfbs.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`disable_ada_joint_constraints.py`](../../../SOURCE_REFERENCES.md#local-only)

## Source Object Intent And Saved Shape State

`invariant` lesson: inspect the current canonical authoring file, compare it
with backups, and record a case-sensitive object inventory before building.
An adjacent `.blend1` is a save-state backup, not automatically the intended
source. In this case the old Normal backup reintroduced objects the user had
deleted.

The final object contract is source-specific:

| Variant | Retain | Physically absent | Classification |
| --- | --- | --- | --- |
| Normal | `Top`, `Panty`, `Obi`, `Skirt`, uppercase `Shoe`, uppercase `Sock` | `Fuda`, lowercase `shoes`, lowercase `socks` | `case-derived`, `build-sensitive` |
| Thin | `Fuda`, uppercase `Shoe`, uppercase `Sock` | `Top`, `Panty`, `Obi`, `Skirt`, lowercase `shoes`, lowercase `socks` | `case-derived`, `build-sensitive` |

Object-name case is semantic here. Removing lowercase `shoes`/`socks` must not
remove the intended uppercase `Shoe`/`Sock`. The contract follows the current
canonical Blend bytes and is asserted again against generated Mesh resources
and the final package.

`invariant` saved-state rule: evaluate and record nonzero Shape Key values
before deleting keys. `Basis` does not necessarily represent the appearance
the author saved. Shape-state, object inclusion, foot-to-shoe fit, and
shoe-to-world contact are separate contracts.

Nyako values (`case-derived`, `build-sensitive`):

- both variants bake `Body_base:Foot_HighHeel=1.0` before key removal;
- Normal `BodyRope` bakes `WithSkirt=1`, `WithObi=1`, and
  `Breasts_small=0.75`;
- Thin `BodyRope` bakes only `Breasts_small=0.75`; it must not inherit the
  Normal-only `WithSkirt` or `WithObi` states.

R6 Thin retained all `17,614` `BodyRope` vertices and `35,184` triangles
(`case-derived`, `build-sensitive`). Its missing abdomen rope was therefore not
an accidental topology deletion. The Normal-only shape bake moved the intact
rope inside the skin. R7 corrected the variant-specific evaluation and added a
topology-preservation gate. A hidden source object should not be "fixed" by
deleting vertices until evaluated shape state and skin intersection are
measured.

Evidence:

- [`source-object-deletion-r4.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`source-object-top-removal-r5.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`source-object-intent-r6.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r7-sleeve-bodyrope-thin-campaign.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r7-sleeve-bodyrope-thin-mercenaries.json`](../../../SOURCE_REFERENCES.md#local-only)

## Core Arms And Segmented Sleeve Frames

R3's arms and forearms were severely twisted and appeared reverse-bent. The
current Mesh contract keeps every animation-core bone at the exact current Ada
donor rest, applies one shared body-envelope scale to all visible slots, and
deploys byte-identical current-native FBXSKEL templates. Source geometry and
retained physical rest bones receive the same declared directional transfer.
This `donor-directional` arrangement is `case-derived` and `build-sensitive`;
its offline closure still needs runtime confirmation for R9.

R6 exposed a different but related frame bug. Sleeve physical bones received
directional rest transforms while KNB-weighted sleeve geometry followed
unmatched generated frames. The result was a forearm sleeve nearly
perpendicular to the arm. Correct physical-bone placement alone did not make
the weighted geometry coherent.

R7 partitions the connected sleeves into semantic left/right upper-arm and
forearm segments. Each segment owns one source-to-target frame used for all of
the following:

- the segment's weighted geometry;
- every retained physical-bone rest matrix in the segment;
- the segment-root placement and its target animation anchor.

Vertices spanning the elbow keep their original upper-arm/forearm weighted
blend; the sleeve is not collapsed into one rigid forearm package. The case
snapshot has four semantic segments, with twenty-two retained physical bones
and twenty positive transfers in each forearm segment, and two bones plus one
positive transfer in each upper-arm segment (`case-derived`,
`build-sensitive`). The offline cuff-plane error is about `2.15` degrees
against a `10` degree project gate (`case-derived`, `build-sensitive`). These
counts and thresholds are evidence for this mesh only; the reusable rule is
coherent segment ownership and one frame per connected deformation region.

Evidence:

- [`runtime-feedback-r3.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-r6-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r7-sleeve-bodyrope-normal-campaign.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r7-sleeve-bodyrope-normal-mercenaries.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r7-sleeve-bodyrope-thin-campaign.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r7-sleeve-bodyrope-thin-mercenaries.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`audit_r7_sleeve_bodyrope.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`r9-mesh-audit.json`](../../../SOURCE_REFERENCES.md#local-only)

## Flat Sole Plane, Not Foot-Bone Angle

`invariant` separation demonstrated by R8's rejection:

```text
saved high-heel shape -> foot-to-shoe fit
shoe contact plane   -> footwear orientation
target floor         -> world-height correction
```

None of these contracts proves either of the others. R8 forced the downward
`Foot -> Toe` direction from about `30.9405` degrees to `45.8` degrees,
introducing about `14.8595` degrees of extra pitch and about `58.34 mm` of
front-to-back sole height difference (`case-derived`, `build-sensitive`). The
user's runtime screenshot still showed the flat shoe standing on its toes.
That rejects the proposition that a humanoid foot-bone angle is a sufficient
proxy for this shoe's contact plane.

R9 instead fits the low-contact plane of source object `Shoe`. For each side it
constructs the source frame from the fitted plane normal and the projected
`Foot -> Toe` direction. The target frame uses world vertical and the matching
Ada donor's XY-forward projection. One matrix per side is then applied to both
static weighted geometry and all descendant physical-bone rest placement.

Direct measurements across the four Normal/Thin Campaign/Mercenaries authoring
Blends (`case-derived`, `build-sensitive`) found:

- fitted sole tilt `0.00425-0.00451` degrees;
- maximum front-to-back fitted height delta `5.384e-6 m`;
- maximum plane-fit RMS `2.525e-5 m`;
- maximum absolute animation-donor floor delta `1.183e-4 m`.

The corresponding project gates are `0.25` degrees, `0.001 m`, `0.0005 m`, and
`0.001 m` (`case-derived`, `build-sensitive`). A global-minimum floor gate is
not sufficient: one toe point can touch the floor while the rest of a pitched
sole remains elevated. Measure plane tilt, front/back delta, fit residual, and
floor offset independently.

R9's direct audit is `offline-accepted`. The user's later explicit acceptance,
recorded in `runtime-feedback-r9-thin-accepted.json`, promotes the Thin
flat-sole correction to `runtime-confirmed-scoped` for the continuous task
context. Normal and every unreported route/scenario remain pending or
`not-observed`; the acceptance does not turn the numeric frame/offset values
into shared constants.

Evidence:

- [`runtime-feedback-r8-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-r9-thin-accepted.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r9-flat-sole-tail-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`audit_r9_flat_sole_tail.py`](../../../SOURCE_REFERENCES.md#local-only)

## Ground Correction After Orientation

The sole-plane transform and the vertical floor correction are ordered,
separate operations. After R9 establishes the shoe frame, it applies a
Nyako-specific `knee-fixed-lower-leg-shortening` correction. `Shoe`, `Sock`,
and `ankle_ribbon` move rigidly. `Body_base` and `leg_ribbon` receive a
piecewise-linear displacement from the ankle to zero at the fixed knee.
Geometry above the knee remains fixed.

The final offset is `0.0316411698004231 m`, with the transition measured from
ankle Z `0.1491939276456833 m` to knee Z `0.5272403955459595 m`
(`case-derived`, `build-sensitive`). These are Nyako/Ada measurements. The
method pattern was informed by the Riptide/Luis case, but none of that case's
numeric values were reused.

The reusable principle is to preserve rigid footwear/accessory artwork while
fading body-only compensation to a stable anatomical boundary. Apply the same
bounded correction to dedicated physical rests when their attached geometry
moves. Validate triangle orientation, degeneracy, rigid-part preservation,
target-floor error, and deformation poses. An offline donor floor remains an
offline reference, not proof of collision with every runtime surface.

Evidence:

- [`r9-mesh-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r9-flat-sole-tail-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`build_karin_nyako_ada_meshes.py`](../../../SOURCE_REFERENCES.md#local-only)

## Chest Static Fallback And Tail Terminal

R3 reported continuous twitching in the right-chest dynamic region. The
current case policy makes both symmetric VRM chest spring groups `61` and `62`
static while retaining their Mesh bones (`case-derived`, `build-sensitive`).
Suppressing both sides avoids an asymmetric authored solver policy. It proves
the serialized resources contain no chest Chain solve; it does not prove R9's
runtime chest appearance.

R7 reported that the tail moved only with character motion, failed to settle,
and tangled after short lateral movement. R8/R9 append a collinear,
zero-weight, nondeforming terminal helper after `Tail_005`. The final Chain path
contains `Tail_001` through `Tail_005` plus the helper, for six nodes
(`case-derived`, `build-sensitive`). The complete `VFRPosition` recovery,
damping, reduction, and angle profile stays in the project reports rather than
being copied here as a reusable tuning preset.

`invariant` topology lesson: when optimization removes the source terminal,
prepending a static parent is not equivalent to appending a real terminal
helper. Prove the helper exists in every consuming Mesh, is nondeforming by
zero positive weight assignments after re-import, closes every Chain path, and
uses the final rest geometry. Then validate topology, frames, tuning, and
collision as separate contracts.

R9 Chain outputs are deterministic and semantically re-read offline. R8's
runtime foot screenshot did not observe tail behavior, so the terminal and
solver profile remain runtime-pending.

Evidence:

- [`runtime-feedback-r3.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-r7-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`chain-build-normal.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`chain-build-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`chain-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r9-flat-sole-tail-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`build_karin_nyako_ada_chains.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`audit_karin_nyako_ada_chains.py`](../../../SOURCE_REFERENCES.md#local-only)

## Zero-File Deployment Is Not A Content Rejection

The R5 Thin ZIP imported into Fluffy was byte-identical to the released ZIP,
and its cache enumerated the expected archive contents. During the user's
native-Ada screenshot, however, the matching `installed.ini` section contained
zero `file=` records and all forty-nine expected runtime targets were absent
from the game directory (`case-derived`, `build-sensitive`). Native Ada was
therefore the expected result: the candidate payload had not been deployed.

`invariant` diagnostic order:

1. bind the observation to an exact archive or manifest;
2. verify the Mod Manager's deployment records;
3. verify expected target paths and hashes in the runtime tree;
4. only then diagnose PFB, Mesh, materials, skeleton, or Chain content.

Do not mutate aliases or rebuild content from a screenshot when deployment is
proven empty. Remove or disable stale entries through the Mod Manager's normal
workflow; do not delete the whole `installed.ini` or recursively clear the
game's `natives` tree.

Evidence:

- [`runtime-feedback-r5-thin-deployment.json`](../../../SOURCE_REFERENCES.md#local-only)

## Deterministic Package Closure

Each R9 variant contains fifty-five total files, forty-nine runtime resources,
and twenty-two closed custom PFB references (`case-derived`,
`build-sensitive`). The package gate requires report-listed inputs only, zero
forbidden source/streaming/control resources, exact expanded-folder closure,
clean ZIP re-extraction equality, and an identical second archive hash. The ZIP
root contains `modinfo.ini`, package documentation, the manifest, and
`natives/`, with no extra enclosing directory.

The build did not launch RE4 or Fluffy and did not write the game directory.
Packaging raises only the package claim to `offline-accepted`; it cannot prove
loading, appearance, animation, physics, floor contact, or route coverage.

Evidence:

- [`final-package-normal.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`final-package-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`package-resource-map-normal.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`package-resource-map-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`build_ada_package.py`](../../../SOURCE_REFERENCES.md#local-only)

## Scoped Acceptance With Multiple Delivered Variants

After the R9 handoff, the user replied `验收通过。` The handoff contained both
Normal and Thin archives, so the short message was not automatically evidence
for both packages. Continuous context identified the active retest as Thin: the
preceding runtime defects and screenshots were Thin-focused, and the final
handoff explicitly asked for a Thin R9 retest.

The project therefore records Thin as `runtime-confirmed-scoped` for the
reported task context and leaves Normal, exact route/chapter/costume, Figure,
Mercenaries, cold start, conflict priority, rollback, and tail-specific behavior
as `not-observed`. The qualification is part of the evidence record rather than
an informal assumption.

`invariant` evidence rule: when several archives are delivered together, bind a
short acceptance only if continuous context identifies one candidate clearly;
otherwise retain unresolved candidate identity and request clarification. Keep
the runtime report outside the tested ZIP so the accepted archive hash remains
unchanged.

Evidence:

- [`runtime-feedback-r9-thin-accepted.json`](../../../SOURCE_REFERENCES.md#local-only)

## Rejected Shortcuts

Preserve these conclusions narrowly:

- `rejected`: PFB resource-table replacement alone makes the custom resources
  instantiated by unchanged RSZ component fields;
- `rejected`: deploying a corrected skeleton alias alone fixes a PFB whose
  resource table and RSZ bindings disagree;
- `rejected`: an adjacent `.blend1` is automatically newer authoring intent
  than the current canonical `.blend`;
- `rejected`: a visually missing `BodyRope` proves its vertices were deleted;
- `rejected`: correct sleeve physical-bone rests are sufficient when sleeve
  geometry uses a different coordinate frame;
- `rejected`: one rigid forearm transform is valid for a connected sleeve that
  has meaningful cross-elbow weighting;
- `rejected`: a foot-bone downward angle represents a flat shoe's contact
  plane;
- `rejected`: one global minimum vertex at floor height proves a sole is flat;
- `rejected`: a saved high-heel Shape Key proves world-floor contact;
- `rejected`: an offline-valid Chain proves runtime settling or freedom from
  tangling;
- `rejected`: a native-character screenshot rejects Mod content before
  deployment records and runtime targets are verified;
- `rejected`: deterministic package acceptance is runtime confirmation.

## Reusable Diagnostic Sequence

For a similar character replacement:

1. Lock current official resources, tools, source hashes, and the exact
   candidate before interpreting runtime feedback.
2. Build a current-build consumer matrix and patch PFB table and RSZ fields as
   one semantic dependency contract.
3. Audit canonical source-object intent case-sensitively and evaluate saved
   Shape Keys before deleting them.
4. Separate animation-core donor rests from source-geometry/physical transfers;
   partition connected attachments into coherent semantic frame packages.
5. Separate foot-to-shoe fit, sole-plane orientation, and world-height
   correction; measure a plane rather than one extremal point.
6. Treat Chain topology, terminal completion, settings, and collision as
   independent gates; use a scoped static fallback when the product accepts
   lost secondary motion.
7. Verify deployment before content diagnosis, and preserve zero-file incidents
   as deployment evidence rather than binary rejection.
8. Build one attributable candidate, retain old negative controls, and keep
   positive subcontracts from an otherwise rejected candidate narrowly scoped.
9. Re-import resources, compare a clean second build, re-extract the ZIP, and
   keep runtime status pending until exact-candidate feedback exists.

## Rights And Privacy Boundary

The embedded avatar metadata is restrictive, includes an `OnlyAuthor` use
condition, prohibits redistribution, and restricts violent usage. The supplied
assets are treated only as authorization for this private local technical
build. No Blend, FBX, VRM, texture, private reference-Mod payload, generated
runtime resource, or install-tree copy is stored in SharedKnowledge. Technical
acceptance does not expand the rights holder's license.

## Key Evidence

- [`SOP.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`input-lock.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`consumer-matrix.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`source-object-intent-r6.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r9-mesh-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r9-flat-sole-tail-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`chain-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r9-pfb-determinism-normal.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`r9-pfb-determinism-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`final-package-normal.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`final-package-thin.json`](../../../SOURCE_REFERENCES.md#local-only)
