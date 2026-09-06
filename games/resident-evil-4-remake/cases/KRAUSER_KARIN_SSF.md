# Case Study: Karin SSF Replaces Krauser

> Status: r1-r9 rejected or superseded; r10 retained a Chapter 11 scoped
> positive result but was rejected at the Chapter 14 Figure/event transition;
> r11 is accepted for normal use in that continuous Chapter 14 retest context
> Project: `RE4/Karin_SSF_Replace_Krauser`
> Snapshot date: 2026-08-07
> Game build: Steam `22377325`
> Evidence level: r11 is `offline-accepted` and `runtime-confirmed` for the
> exact prior Chapter 14 blocker and normal usability in the explicitly bound
> user-test context; detailed visual rows and all unreported routes, actions,
> cold start, lighting, conflicts, and physics remain `not-observed`
> Reuse class: mixed invariant, build-sensitive, case-derived, and rejected;
> every route, resource suffix, PFB offset, material name/hash, count, and
> artifact hash below is a case value unless explicitly classified otherwise

## Scope And Accepted Result

This project replaces the current Krauser Campaign, variant, Figure, and
Mercenaries consumers with Karin SSF. The optimized Blend/FBX supplied authored
geometry and weights, the sibling VRM supplied saved-state and physics
semantics, current build resources supplied consumer and binary authority, and
a private successful Krauser Mod supplied only independently audited structural
examples. The offline build did not launch RE4 or Fluffy Mod Manager, write the
game directory, or modify official PAKs. Runtime testing remained user-owned.

The accepted r11 archive is:

```text
Output/Karin_SSF_Replace_Krauser_RE4R_build22377325.zip
Size 82,771,534 bytes
SHA-256 7EE99608F366B7572BAD124F806E49671F486B38A896BDFA66B9FD2F31D77ACE
63 runtime resources / 69 total entries
```

The earlier r10 archive first received scoped acceptance for Chapter 11
stability and Campaign-body rendering, then failed later at the exact
end-of-Chapter-14 transition. That later
[runtime rejection](../../../SOURCE_REFERENCES.md#local-only)
was bound to an exact 63/63 r10 install and narrowed the new failure to the
`chf700` Figure/event consumer. r11 changed only the Figure body Mesh and its
two existing MDF aliases, retaining the other 60 runtime resources exactly.

After the unique r11 handoff, the user replied `可以正常使用了。`. The
[r11 runtime acceptance report](../../../SOURCE_REFERENCES.md#local-only)
binds that feedback to the archive above, the continuous Chapter 14 retest
context, and a new read-only 63/63 installed-tree size/SHA-256 snapshot. This
confirms that the prior blocking transition no longer prevents normal use in
that context. The user did not repeat the archive hash or enumerate the visual
subchecks, so complete body-material appearance, native mutation-arm
visibility, subsequent fight entry, r11 Chapter 11 regression, model viewer,
Mercenaries, cold start, actions, lighting, physics, conflicts, rollback, and
long-session behavior remain `not-observed`.

This is scoped acceptance, not a fabricated full-game matrix. Campaign body
Chain motion remains intentionally disabled/static. The face and independent
head secondary branches also retain the limitations declared in the project
[SOP](../../../SOURCE_REFERENCES.md#local-only). The tested ZIP was not rebuilt
to embed its later runtime status.

## Candidate And Runtime Timeline

| Candidate | Exact identity and evidence | Runtime result | Narrow durable conclusion |
| --- | --- | --- | --- |
| r1 | `BCD971AEDDF90DB7DB466963175A72CFD0437B9B2830FFB3D838C6D1C4940A28`; [rejected package report](../../../SOURCE_REFERENCES.md#local-only) | Infinite loading before the Chapter 14 encounter and in the model/display interface | Counting packaged TEX files did not prove MDF-to-runtime-path closure; all custom TEX files were under a punctuation-different namespace |
| r2 | [rejected archive](../../../SOURCE_REFERENCES.md#local-only), SHA-256 `70D82713BCD5AEC55E68FB957EC1AE6B49F62E1F49B0BD37C386BAE2D4384222` | Model/display loading succeeded, but the body was severely tall/thin and the tail crossed to the front | The r1 namespace diagnosis was valid; donor-rest warping, independent slot scales, and a reversed tail aim were separately wrong |
| r3 | [rejected archive](../../../SOURCE_REFERENCES.md#local-only), SHA-256 `B358AED56F5F5AF4FB1810B5BC3A6C38B64ACF2117136FB6A18A3DF15E64DE30`; [runtime rejection](../../../SOURCE_REFERENCES.md#local-only) | Source proportions and rearward tail loaded correctly in model/display; Campaign actor creation near the end of Chapter 11 crashed | Rest/proportion repair was valid but did not prove the gameplay-only Campaign consumer graph |
| r4 | [rejected archive](../../../SOURCE_REFERENCES.md#local-only), SHA-256 `BFE05CD4F65FCE9C5F09AC6C41D4EA034AA450B31E8FD7B825F0C2BC34ED9A1E`; [runtime rejection](../../../SOURCE_REFERENCES.md#local-only) | Corrected 100x collider-unit defect and four current-build JointConstraints patches still reached the same native crash stack | Collider reconstruction and PFB hardening were necessary offline corrections, but neither was sufficient for this crash |
| r5 | [rejected archive](../../../SOURCE_REFERENCES.md#local-only), SHA-256 `03F9DF2C4B66F1BEAE61979C1B44DE1F0FF65F2AB5764A2089D86E989CC34667`; [runtime rejection](../../../SOURCE_REFERENCES.md#local-only) | Removing only the loose Campaign Chain and falling back to the native Chain did not change the crash | The custom Campaign Chain asset was not required for the failure, and native Chain fallback alone was insufficient |
| r6 | [rejected archive](../../../SOURCE_REFERENCES.md#local-only), SHA-256 `5D9672E68940E891A1BB941BFEE534AA72A498B5A52965ECCE0ADFCFA23B81E1`; [runtime rejection](../../../SOURCE_REFERENCES.md#local-only) | A reference-structured, 231-bone body-only partition still reached the same native crash path | Eliminating the 256-bone/index-255 risk was sound hardening but not sufficient; install binding for this run is explicitly limited |
| r7 | [rejected archive](../../../SOURCE_REFERENCES.md#local-only), SHA-256 `A8FEBD973C085DC59ACD3E45A9ABDAD9F2DEEAA0D2C815C0E68388BCD65B17CD`; [runtime rejection](../../../SOURCE_REFERENCES.md#local-only) | With an exact 63/63 install binding and Campaign `via.motion.Chain.Enabled=false`, the same crash remained | Chain invocation was neither required nor the next useful variable; the stable dump exposed an unchecked failed material lookup instead |
| r8 | [rejected archive](../../../SOURCE_REFERENCES.md#local-only), SHA-256 `2E32A6799F960684EC662DBFA4BBF6A87065A5607A2ABCA54F2C2F6D6BECCF12`; [runtime rejection](../../../SOURCE_REFERENCES.md#local-only) | Appending complete native `Skin_Mat` advanced the same caller to a missing `Pants_Cloth_Mat`, then crashed | `Skin_Mat` was active and correctly diagnosed, but one material was only the first rung of a fixed five-material lookup sequence |
| r9 | [rejected archive](../../../SOURCE_REFERENCES.md#local-only), SHA-256 `B1D384C6834B91CDBF5A93669140A65F21ACE86FC28939202ED3623392926E5A`; [visual rejection](../../../SOURCE_REFERENCES.md#local-only) | The former Chapter 11 crash stopped, and the independent head rendered normally; the entire Campaign body route rendered brown checkerboard | The five-material/two-property MDF lookup closure fixed the observed crash boundary, but an 18-material MDF paired with a 13-material Mesh was structurally incomplete |
| r10 | [archived rejected candidate](../../../SOURCE_REFERENCES.md#local-only), SHA-256 `6E4B3460E027CDBF1F3215514B752CE01FFC2A0C8485E2FBF0C3620DF4F62F86`; [Chapter 11 acceptance](../../../SOURCE_REFERENCES.md#local-only); [Chapter 14 rejection](../../../SOURCE_REFERENCES.md#local-only) | Chapter 11 Campaign stability/rendering passed, but the exact 63/63 install later crashed when the Chapter 14 transition loaded `chf700` and failed the `R_Arm_Mat` lookup | Campaign Mesh/MDF closure remains valid for its route; an earlier route pass does not confirm a later event consumer, even for the same character |
| r11 | [accepted archive](../../../SOURCE_REFERENCES.md#local-only), SHA-256 `7EE99608F366B7572BAD124F806E49671F486B38A896BDFA66B9FD2F31D77ACE`; [acceptance](../../../SOURCE_REFERENCES.md#local-only) | User reported normal usability in the continuous r11 Chapter 14 retest context; a read-only snapshot matched all 63 installed resources exactly | Closing the separately derived Figure Mesh/two-MDF-alias compatibility set cleared the prior blocker in the accepted scope; unreported visual and route rows remain `not-observed` |

Later candidates do not erase narrow positive results from rejected parents.
For example, r2 validated the TEX namespace repair, r3 validated the proportion
and tail repair, r8 proved lookup progression, r9 proved that the complete MDF
lookup set crossed the former Chapter 11 crash boundary, and r10 validated the
Campaign Mesh/MDF closure before exposing a different Figure/event failure.
Their broader candidate promotion still stopped at each blocking runtime
defect.

## Runtime Resource Paths Must Close Semantically

`invariant`, demonstrated by r1 rejection and r2 load success:

The first package contained every intended custom texture byte, but the MDF
referenced `_Chainsaw/Character/ch/KarinSSFKrauser/...` while the loose files
lived under `_chainsaw/character/ch/karin_ssf_krauser/...`. Case folding cannot
make inserted underscores disappear. REFramework recorded requests for 22
unique resource paths and zero hits in the packaged punctuation-different
namespace.

The failed validator counted TEX files; it did not parse every MDF binding and
resolve the corresponding versioned destination. The corrected verifier had to:

1. parse every final MDF resource path;
2. preserve punctuation while applying only the engine-relevant case policy;
3. resolve every reference to an exact packaged `*.tex.<version>` path;
4. require zero missing destinations;
5. track deliberately unbound outputs separately;
6. prove that the old r1 archive fails the new gate.

The negative control matters. A validator that accepts only the new candidate
without rejecting the known bad archive may still be testing the wrong
property. Texture bytes, DDS/TEX encoding, Mesh, and MDF parameters did not need
to change in r2; only the destination namespace changed.

Evidence and implementation:

- [r1 rejection report](../../../SOURCE_REFERENCES.md#local-only)
- [material builder](../../../SOURCE_REFERENCES.md#local-only)
- [package verifier](../../../SOURCE_REFERENCES.md#local-only)

## Choose The Proportion Contract Before Retargeting

`case-derived` repair supporting an `invariant` authoring rule:

r2 used different body/face/head envelope ratios and warped source bones toward
the larger male donor rest. The mapping could place individual anchors near
their target while still stretching the source's internal torso, legs, and arm
span. r3 instead declared `source-proportions` as the product contract and
applied one route-level similarity transform coherently to source geometry and
physical rest bones. Current-compatible animation/core names and graph
requirements remained separate from source-shape authority.

The tail defect was also a rest-contract failure, not evidence of bad Chain
tuning. Its source aim and target aim pointed in opposite directions, producing
an approximately 180-degree flip. Treating the six tail bones and their mesh as
one rigid source package restored a root behind the Hip and a rearward/downward
chain. Changing gravity, damping, or collision first would have tuned motion
around an already wrong static frame.

Reusable rules:

- choose donor-conforming versus source-proportion rest policy explicitly;
- use one coherent source frame for all visible slots that must match;
- validate source landmark ratios, not only target-anchor distances;
- inspect static root, aim, terminal, and mesh placement before Chain tuning;
- generate and validate Mesh and route-scoped FBXSKEL as a paired rest contract;
- retain four-view evidence and numeric tail direction/continuity checks.

The exact scales, landmarks, ratios, six source bones, and route matrices remain
case-derived. See the
[proportion/tail contract](../../../SOURCE_REFERENCES.md#local-only)
and [proportion audit script](../../../SOURCE_REFERENCES.md#local-only).

## Campaign Crash Diagnosis Must Follow The Stable Fault

### Separate sound corrections from causal sufficiency

`invariant` diagnostic method, demonstrated by r3-r7:

The Chapter 11 Campaign crash appeared only when the gameplay actor was
instantiated, so Chain/PFB/consumer-specific structures were reasonable first
hypotheses. r4 found a real 100x collider offset defect caused by including a
source Armature `0.01` scale in a local inverse. It reconstructed colliders in
world space, then expressed the delta in the final target-bone rotation frame.
It also disabled four current-build JointConstraints components. Those changes
were technically valid, deterministic, and retained later, but the exact native
crash stack remained.

r5 removed only the Campaign Chain override. r6 removed head-physics bridges,
reduced the body from 256 to 231 bones, and moved the last live weighted bone
away from skeleton index 255. r7 then disabled only the serialized Campaign
Chain component while retaining the Chain asset. Each was a defensible isolated
probe; none prevented the stable fault.

The reusable discipline is:

- freeze the dump and all runtime logs before restart or Mod Manager activity;
- bind the installed paths and hashes at the failure instant when possible;
- compare RIP, exception, registers, effective address, caller, and stack
  offsets across candidates;
- make one attributable resource or semantic change against a matched baseline;
- preserve a valid correction when later evidence rejects only its sufficiency;
- stop changing a layer after controlled candidates prove it is not required;
- qualify evidence when the install tree changed before it could be captured.

r6 is the cautionary example for the last rule. Its user attribution and dump
identity survive, but the game restarted and the managed tree changed before a
replayable exact install snapshot was frozen. It remains
`runtime-rejected-install-binding-limited`, not equivalent to r7's exact 63/63
binding.

Key evidence:

- [collider-unit contract](../../../SOURCE_REFERENCES.md#local-only)
- [PFB JointConstraints patch](../../../SOURCE_REFERENCES.md#local-only)
- [r6 successful-reference structure comparison](../../../SOURCE_REFERENCES.md#local-only)
- [r7 one-byte Chain-component patch](../../../SOURCE_REFERENCES.md#local-only)
- [r7 crash disassembly](../../../SOURCE_REFERENCES.md#local-only)

### Decode the failed index instead of guessing the subsystem

`invariant` reverse-engineering method with build-sensitive addresses and
hashes:

At the stable r7 fault, the instruction was `mov rcx, [rax + rdx*8]` and
`RDX=0xFFFFFFFF`. Substituting the dump registers reproduced the recorded
invalid-read address exactly. The caller returned `0xFFFFFFFF` from a 32-bit ID
lookup and consumed it without the not-found check present at another call
site. Executable strings plus RE wide Murmur hashes resolved the active keys to
`Skin_Mat` and `TexBlend_Weight`.

That changed the diagnosis from a broad "Campaign physics crash" to an exact
unchecked material lookup in `Ch1b7z0BodyUpdater`. The current-build PFB also
contained a `via.render.MaterialParam` targeting `Skin_Mat`, while the custom
Campaign body MDF did not contain it.

The strong proof was not merely finding a plausible hash preimage. r8 appended
the complete current-build `Skin_Mat`; the next runtime dump retained the same
lookup helper and property key but advanced the material key to
`Pants_Cloth_Mat`. This simultaneously proved that the r8 material was active
and rejected the claim that restoring only the first lookup was sufficient.

Caller disassembly then established ten lookups arranged as two groups of five:
five material names, each paired with `TexBlend_Weight` and
`TexBlend2_Weight`. The complete case-specific order was:

```text
Skin_Mat
Pants_Cloth_Mat
Shirts_Cloth_01_Mat
PropsA_Cloth_Mat
LowerBody_Metal_Mat
```

r9 restored that entire MDF lookup set and crossed the former crash boundary.
The names, hashes, call offsets, class layout, and five-entry count are
build-sensitive. The reusable method is to combine exact dump arithmetic,
caller/control-flow proof, current resource semantics, and a progressive
single-variable runtime probe.

Evidence and implementation:

- [Campaign crash analyzer](../../../SOURCE_REFERENCES.md#local-only)
- [r8 `Skin_Mat` structured builder](../../../SOURCE_REFERENCES.md#local-only)
- [r8 material-lookup closure audit](../../../SOURCE_REFERENCES.md#local-only)
- [r9 complete MDF closure builder](../../../SOURCE_REFERENCES.md#local-only)
- [r9 body-damage closure report](../../../SOURCE_REFERENCES.md#local-only)

## Mesh And MDF Are One Indexed Runtime Contract

### Why MDF-only repair stopped the crash but produced checkerboard

`invariant` closure principle with `build-sensitive` consumer proof, established
here by r9 rejection, consumer disassembly, and r10 acceptance:

r9 contained the required five materials and two properties in its Campaign
body MDF. The former unchecked lookup no longer returned `0xFFFFFFFF`, so actor
creation passed. The separate head route rendered normally, and same-session
logs showed the Campaign body Mesh/MDF and the custom TEX namespace being read.
The body, limbs, clothing, tail, and wings nevertheless rendered as a brown
checkerboard.

The decisive structural mismatch was:

```text
r9 Campaign body Mesh: 13 ordered materials
r9 Campaign body MDF:  18 ordered materials
MDF-only suffix:       five body-damage compatibility materials
```

`Ch1b7z0BodyUpdater` stores the returned material index at handle offset
`+0x10` and the property index at `+0x14`, caches two five-handle groups, and
later uses the stored material index directly against the Mesh component
material array. Therefore an MDF entry is not merely a named parameter bag. Its
runtime index must be valid on the paired Mesh side.

This case strengthens the shared material contract to:

```text
Mesh material names and order
<-> submesh material indices and backing geometry
<-> MDF material names and order
<-> runtime components that cache or consume material indices
<-> referenced TEX resources
```

Name existence alone is insufficient. Name-set equality alone may also be
insufficient when order/index consumption is proven. A load pass is likewise
insufficient when later render state can still reject the same structure.

Evidence:

- [r9 checkerboard screenshot and runtime rejection](../../../SOURCE_REFERENCES.md#local-only)
- [all-route Mesh/MDF material audit](../../../SOURCE_REFERENCES.md#local-only)
- [BodyUpdater construction/consumption audit](../../../SOURCE_REFERENCES.md#local-only)
- [checkerboard audit script](../../../SOURCE_REFERENCES.md#local-only)
- [material-contract audit script](../../../SOURCE_REFERENCES.md#local-only)
- [BodyUpdater disassembly audit script](../../../SOURCE_REFERENCES.md#local-only)

### Hidden backing submeshes as a compatibility mechanism

`case-derived`, runtime-accepted for the exact r10 candidate:

The successful private reference had a closed Mesh/MDF material-name set and
backed each of the five compatibility materials with a non-degenerate hidden
3-vertex/1-triangle submesh. Its Mesh/MDF order was not identical, so it proved
the existence of valid backing geometry rather than r10's exact index layout.
That was a working structural example, not permission to import its unrelated
textures, skeleton, materials, PFBs, or physics.

r10 retained the exact r9 18-material MDF and changed only
`chb700_00.mesh.221108797`. It appended five backing submeshes at indices
13-17 in exact MDF order. Each triangle:

- has three vertices and one non-degenerate micro-scale face;
- uses the existing `[Position][Normals][UV1][Weight][Color]` layout;
- is weighted 100 percent to the existing `Hip` bone;
- lies around the weighted center of existing Hip-weighted vertices;
- does not expand any of the 141 weighted-bone bounding boxes;
- does not reuse a visible Karin shader as a body-damage compatibility target.

Before editing, the builder performed a no-op export of the locked authoring
Blend and required it to be byte-identical to the r9 baseline Mesh. This catches
tool/profile/export drift before attributing the new bytes to the intended
change. Two fresh r10 builds were byte-identical. The audit then proved all 13
visible submeshes retained exact coordinates, faces, normals, tangents, UVs,
weights, indices, and colors; skeleton names, hierarchy, matrices, weighted
remap, vertex layout, and all bone bounds also remained exact.

The accepted r10 Mesh is 9,275,472 bytes at SHA-256
`2BBD56973F5FEFD27886654FC7313EB8A459416F3E356168F465CBA2297CA529`.
Relative to r9 it adds exactly 15 vertices and five triangles. These counts,
locations, material names, and `Hip` policy are case-specific. A future target
must independently prove whether hidden geometry, an existing native submesh,
or a different consumer contract is appropriate.

Evidence and implementation:

- [r10 Mesh closure builder](../../../SOURCE_REFERENCES.md#local-only)
- [r10 Mesh/MDF semantic audit](../../../SOURCE_REFERENCES.md#local-only)
- [r10 Mesh re-import audit](../../../SOURCE_REFERENCES.md#local-only)
- [r10 master contract](../../../SOURCE_REFERENCES.md#local-only)

## Late Transitions Can Activate A Different Consumer Family

`case-derived`; r10 is `runtime-rejected` and r11 is
`runtime-confirmed` for the exact continuous end-of-Chapter-14 blocker on
Steam build `22377325`:

The Chapter 14 symptom was described as loading mutated Krauser, so `chb701`
was an initially plausible route. It was not the observed route. In the
sub-second crash window, accessed/loose logs recorded `chf700_00.pfb.17`, then
the loose Figure body Mesh and MDF. They did not record a `chb701` loose hit.
The dump failed in the same unchecked material-index helper as r7/r8, with
`RDX=0xFFFFFFFF`; this time the active keys resolved to `R_Arm_Mat` and
`TexBlend_Weight`.

The reusable principle is that a route-family label such as Figure, gallery,
variant, or Campaign does not define every runtime scene that can instantiate
it. Chapter/boss semantics and filename intuition are hypotheses. Attribute a
late transition from time-correlated PFB/Mesh/MDF hits at the fault window,
then update the consumer matrix. An earlier Campaign pass cannot confirm a
later event consumer that happens to reuse the Figure family.

The compatibility namespace was consumer-scoped. The Chapter 11 Campaign
updater required one five-material set, while current native Figure data
identified a different five-material set carrying both queried properties:

```text
R_Arm_Mat
Body00_Mat
Body02_Mat
Belt_Leather_Mat
Pants_Cloth_Mat
```

r11 copied the complete current-native records for those names after the 13
unchanged Karin materials, appended matching hidden non-degenerate backing
submeshes in the same order, and updated both existing Figure body MDF aliases.
It did not copy the Campaign material set into Figure, add a new route, or add
visible native mutation-arm geometry. The exact r10-to-r11 runtime delta was
three Figure resources changed and 60 resources byte-identical.

The user then reported normal usability in the continuous r11 retest context.
At acceptance-record time, every one of the 63 user-managed installed resources
matched the r11 master contract by size and SHA-256. This confirms the prior
blocking transition within that context. It does not convert the offline proof
of hidden `R_Arm_Mat` geometry into a separately observed runtime arm-visibility
result; that and the other unreported matrix rows remain `not-observed`.

Dated supersession, 2026-08-07: r11 supersedes r10 as the current candidate and
supersedes the claim that Chapter 14 remained pending. It does not erase r10's
Chapter 11 positive scope or its later Figure/event rejection.

Evidence and implementation:

- [r10 Chapter 14 rejection and route attribution](../../../SOURCE_REFERENCES.md#local-only)
- [r10 rejection auditor](../../../SOURCE_REFERENCES.md#local-only)
- [r11 Figure MDF builder](../../../SOURCE_REFERENCES.md#local-only)
- [r11 Figure Mesh builder](../../../SOURCE_REFERENCES.md#local-only)
- [r11 Figure Mesh/MDF closure](../../../SOURCE_REFERENCES.md#local-only)
- [r10-to-r11 isolation](../../../SOURCE_REFERENCES.md#local-only)
- [r11 acceptance recorder](../../../SOURCE_REFERENCES.md#local-only)
- [r11 scoped runtime acceptance](../../../SOURCE_REFERENCES.md#local-only)

## Use A Successful Reference As A Probe, Not Authority

`invariant` authority lesson:

The reference Mod was valuable at three different moments:

- it showed a working Campaign body could use fewer body-side physical bones
  and no head-physics bridge;
- it independently contained the route-relevant material names and two blend
  properties found through current native resources and executable analysis;
- it demonstrated valid hidden backing submeshes for both Campaign and Figure
  compatibility materials.

None of those observations made the reference current-build authority. The
consumer routes, resource suffixes, headers, PFB schema, native material
semantics, skeleton pairing, and exact package closure still came from current
build `22377325` evidence. The strongest diagnosis used four independent views:

1. the failing candidate;
2. current native resources and executable behavior;
3. a successful reference structure;
4. the exact runtime symptom or dump.

Agreement across those views justified a narrow reconstruction. It did not
justify copying private payloads wholesale or combining unrelated donor fixes
into one candidate.

## Single-Variable Deltas Preserve Causal Evidence

`invariant`, strongly demonstrated by r4-r11:

Every diagnostic candidate should assert both the intended changed paths and
the complete unchanged set. Merely listing the intended edit cannot detect an
incidental re-export, material rebuild, stale baseline, documentation package,
or route drift.

The decisive r9-to-r10 runtime delta had:

```text
added runtime paths:   0
removed runtime paths: 0
changed runtime paths: 1 (Campaign body Mesh)
unchanged resources:   62 byte-identical
retained Campaign MDF: SHA-256 1CC536F261276B6C4E504DE4421730868AD730EDA47CAB33874286CD0BDF0A2B
```

The ZIP's documentation and manifest changed as expected, but runtime path-set
comparison isolated the body Mesh as the only executable variable. Package
verification separately re-extracted 69 entries, matched all 63 runtime
resources against the master contract, resolved 263 custom MDF texture
occurrences to 22 required paths with zero missing, and recorded one declared
unbound flat-normal output.

The r10-to-r11 delta then isolated a different consumer without rebuilding the
accepted Campaign fix:

```text
added runtime paths:    0
removed runtime paths:  0
changed runtime paths:  3 (Figure Mesh + two existing MDF aliases)
unchanged resources:    60 byte-identical
visible native arm:     not added
```

This made the subsequent scoped acceptance evidence for the Figure closure,
not for an incidental Campaign, texture, rig, Chain, PFB, or Mercenaries
change.

Evidence:

- [r9-to-r10 isolation script](../../../SOURCE_REFERENCES.md#local-only)
- [r9-to-r10 isolation report](../../../SOURCE_REFERENCES.md#local-only)
- [package builder](../../../SOURCE_REFERENCES.md#local-only)
- [r10 package verification](../../../SOURCE_REFERENCES.md#local-only)
- [r10-to-r11 isolation script](../../../SOURCE_REFERENCES.md#local-only)
- [r10-to-r11 isolation report](../../../SOURCE_REFERENCES.md#local-only)

## Runtime Feedback Must Preserve Positive And Negative Scope

`invariant` evidence lesson:

r9 is both a useful load pass and a rejected candidate. The observed session
proved that the former actor-instantiation crash did not recur, the independent
head route rendered, and target loose resources were requested. The body
checkerboard was still blocking, so r9 could not be promoted. Calling it simply
"working" would erase the visual rejection; calling it simply "crashing" would
erase the material-lookup progress.

The r9 report also demonstrates evidence qualification. A point-in-time
read-only observation found all 63 installed resources exact, but its per-file
rows were not persisted before the user-managed tree was removed. The durable
report therefore binds the screenshot, logs, body Mesh/MDF hits, TEX hits, and
archive while treating the earlier 63/63 observation as corroboration rather
than a replayable machine gate. The old remaining dump was r8's and was not
misattributed to the no-crash r9 session.

r10 acceptance used the same precision. It confirmed the exact delivered
package for the continuous Chapter 11 stability/render retest, not every route
or scenario. Its later exact-candidate Chapter 14 rejection did not invalidate
that narrow positive result; it stopped r10 promotion and exposed a separate
consumer.

r11 improves the install-binding record. Its acceptance report persists all 63
per-path expected/actual sizes and hashes rather than retaining only an
aggregate `63/63` observation. The user statement confirms normal usability in
the continuous Chapter 14 retest context, while every unreported visual and
route row remains explicit. In both cases the tested ZIP stays byte-identical:
acceptance lives in an external report and the project record. Repacking an
archive to add an "accepted" label would create new, untested bytes.

## Rejected Shortcuts

Preserve these conclusions narrowly:

- `rejected`: packaged TEX count proves every MDF resource path resolves;
- `rejected`: lowercasing makes punctuation-different resource namespaces
  equivalent;
- `rejected`: independent per-slot scales and donor-directional bone warping
  preserve a source-proportion product;
- `rejected`: a forward tail in static/model display is necessarily a Chain
  tuning problem;
- `rejected`: correcting real collider units and disabling JointConstraints is
  sufficient to fix the Chapter 11 crash;
- `rejected`: the custom Campaign Chain asset is required for the crash;
- `rejected`: native Chain fallback is sufficient to prevent the crash;
- `rejected`: reducing a 256-bone body and removing index-255 risk is sufficient
  to prevent this crash;
- `rejected`: disabling the Campaign Chain component is sufficient to prevent
  this crash;
- `rejected`: restoring only `Skin_Mat` closes the body updater's lookup set;
- `rejected`: a complete MDF lookup set is a structurally complete material
  repair when the paired Mesh still exposes fewer material indices;
- `rejected`: same-session Mesh/MDF/TEX hits rule out a material-index contract
  failure;
- `rejected`: a crash-free actor load is sufficient for visual acceptance;
- `rejected`: a Chapter 11 Campaign pass confirms Krauser's later Chapter 14
  transition;
- `rejected`: a mutation-scene description or `chb701`-like filename proves
  which consumer route is active without crash-window path-hit evidence;
- `rejected`: one consumer's fixed compatibility-material set is a universal
  set that can be transplanted to another consumer family;
- `rejected`: parser, round-trip, determinism, and package extraction prove
  runtime behavior;
- `rejected`: a successful reference Mod authorizes copying its unrelated or
  private resources;
- `rejected`: explicit user acceptance silently confirms every unreported
  route, animation, lighting, physics, conflict, and cold-start state.

The corresponding positive corrections are not rejected merely because they
were insufficient on their own. Resource-path closure, source proportions,
rearward tail rest, collider units, bone-budget hardening, the complete MDF
lookup sets, and deterministic package closure all survive in the accepted r11
line within their measured scopes.

## Reusable Diagnostic Sequence

For a future character replacement that progresses from loading failure to
native crash, checkerboard rendering, or a later-route recurrence:

1. Bind the candidate archive, manifest, installed resource tree, build, route,
   and user observation before editing.
2. Parse MDF paths and resolve exact packaged TEX destinations; use the rejected
   archive as a negative validator test.
3. Separate static source/rest defects from Chain motion. Validate one global
   proportion policy and appendage root/aim/terminal frames.
4. Freeze dumps and logs before restart. Compare the exact native fault across
   isolated candidates rather than restarting the hypothesis from symptoms.
5. Correlate PFB/Mesh/MDF hits in the immediate fault window. Treat chapter,
   boss-form, Figure, gallery, and variant names as hypotheses until the active
   consumer is observed.
6. When the failed index is a sentinel, reproduce its effective address and
   trace both handle construction and later consumption.
7. Resolve hashed keys through executable/current-resource evidence, then use a
   single-variable candidate to prove lookup progression.
8. Audit every required member of a consumer-scoped lookup sequence; do not
   stop at the first missing key or reuse another route's set.
9. Close every existing/requested MDF alias for that consumer, and once lookup
   succeeds but rendering fails, compare route-specific Mesh
   material order, submesh indices, MDF order, consumer index use, and TEX
   closure as one contract.
10. Compare native, failing, and successful-reference structures, but rebuild
   only the smallest current-compatible semantic requirement.
11. Require a baseline-identical no-op export before the changed export, two
    byte-identical builds, exact preservation of visible geometry and rig
    semantics, clean re-import, and package re-extraction.
12. Assert both the exact changed resource set and every unchanged path/hash.
13. Record runtime rejection or acceptance outside the immutable tested ZIP,
    and leave every unreported scenario `not-observed`.

## Build-Sensitive Snapshot: Do Not Generalize

The following belong only to Karin SSF/Krauser r11 on Steam build `22377325`:

- Campaign `chb700`, variant `chb701`, Figure `chf700`, and Mercenaries
  `chi200` routes and all resource suffixes;
- Mesh v221108797, MDF v32, Chain v53, TEX v143221013, and FBXSKEL v5;
- the PFB instance/offsets, executable addresses, hash algorithm use, material
  and property hashes, and `Ch1b7z0BodyUpdater` layout;
- the distinct Campaign and Figure five-material compatibility sets, two
  property names, indices 13-17, 13-to-18 transitions, and hidden-triangle
  policies;
- 231 Campaign body bones, 141 weighted bones, 176,876 vertices, 238,975
  triangles; the matching Figure counts; `Hip` weighting; and every numeric
  bound;
- 63 runtime resources, 69 ZIP entries, the 62 unchanged r9-to-r10 resources,
  the 60 unchanged r10-to-r11 resources, and every
  Mesh, MDF, package, manifest, report, and archive hash;
- disabled/static Campaign Chain motion and enabled Mercenaries Chain policy.

Re-extract current resources, repeat consumer disassembly when relevant, and
re-measure every value for another target, model, game build, executable, tool,
or add-on version. The reusable result is the closure and evidence method, not
these constants.

## Rights And Privacy Boundary

No source Blend/FBX/VRM, source texture, private reference-Mod payload, generated
game binary, runtime dump, or user screenshot is copied into SharedKnowledge.
All such artifacts remain project-local and are referenced only by relative
evidence links. The project input lock and source license metadata remain
authoritative. Technical success and user acceptance do not expand
redistribution rights.

## Key Evidence

Project state and identity:

- [project SOP](../../../SOURCE_REFERENCES.md#local-only)
- [input lock](../../../SOURCE_REFERENCES.md#local-only)
- [consumer matrix](../../../SOURCE_REFERENCES.md#local-only)
- [r10 master contract](../../../SOURCE_REFERENCES.md#local-only)
- [r10 package verification](../../../SOURCE_REFERENCES.md#local-only)
- [r10 runtime acceptance](../../../SOURCE_REFERENCES.md#local-only)
- [r11 master contract](../../../SOURCE_REFERENCES.md#local-only)
- [r11 package verification](../../../SOURCE_REFERENCES.md#local-only)
- [r11 runtime acceptance](../../../SOURCE_REFERENCES.md#local-only)

Runtime rejection chain:

- [r3 runtime rejection](../../../SOURCE_REFERENCES.md#local-only)
- [r4 runtime rejection](../../../SOURCE_REFERENCES.md#local-only)
- [r5 runtime rejection](../../../SOURCE_REFERENCES.md#local-only)
- [r6 runtime rejection](../../../SOURCE_REFERENCES.md#local-only)
- [r7 runtime rejection](../../../SOURCE_REFERENCES.md#local-only)
- [r8 runtime rejection](../../../SOURCE_REFERENCES.md#local-only)
- [r9 visual rejection](../../../SOURCE_REFERENCES.md#local-only)
- [r10 Chapter 14 Figure/event rejection](../../../SOURCE_REFERENCES.md#local-only)

Material lookup and Mesh/MDF closure:

- [r7 crash disassembly](../../../SOURCE_REFERENCES.md#local-only)
- [r8 material-parameter ladder audit](../../../SOURCE_REFERENCES.md#local-only)
- [r8 five-material lookup closure](../../../SOURCE_REFERENCES.md#local-only)
- [r9 body-damage MDF closure](../../../SOURCE_REFERENCES.md#local-only)
- [r9 all-route material comparison](../../../SOURCE_REFERENCES.md#local-only)
- [r9 BodyUpdater consumption proof](../../../SOURCE_REFERENCES.md#local-only)
- [r10 Mesh/MDF closure](../../../SOURCE_REFERENCES.md#local-only)
- [r9-to-r10 exact delta](../../../SOURCE_REFERENCES.md#local-only)
- [r11 Figure MDF closure](../../../SOURCE_REFERENCES.md#local-only)
- [r11 Figure Mesh/MDF closure](../../../SOURCE_REFERENCES.md#local-only)
- [r10-to-r11 exact delta](../../../SOURCE_REFERENCES.md#local-only)

Core builders and auditors:

- [Mesh/rig builder](../../../SOURCE_REFERENCES.md#local-only)
- [Chain builder](../../../SOURCE_REFERENCES.md#local-only)
- [r8 compatibility-material builder](../../../SOURCE_REFERENCES.md#local-only)
- [r9 MDF-closure builder](../../../SOURCE_REFERENCES.md#local-only)
- [r10 hidden-submesh builder](../../../SOURCE_REFERENCES.md#local-only)
- [r10 closure auditor](../../../SOURCE_REFERENCES.md#local-only)
- [r10 master-contract builder](../../../SOURCE_REFERENCES.md#local-only)
- [r11 Figure MDF builder](../../../SOURCE_REFERENCES.md#local-only)
- [r11 Figure Mesh builder](../../../SOURCE_REFERENCES.md#local-only)
- [r11 acceptance recorder](../../../SOURCE_REFERENCES.md#local-only)
- [package verifier](../../../SOURCE_REFERENCES.md#local-only)
