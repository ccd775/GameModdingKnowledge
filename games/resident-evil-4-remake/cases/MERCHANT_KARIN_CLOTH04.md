# Case Study: Karin Cloth04 Replaces Merchant

> Status: R1-R4 runtime-rejected; `merchant-build22377325-r5-ground-contact`
> is planned and not built
> Project: `RE4/KarinCloth04ReplaceMerchant`
> Snapshot date: 2026-08-06
> Game build: Steam `22377325`
> Evidence level: R4 passed its declared offline package gates, then failed a
> user-owned Merchant shop runtime test
> Reuse class: mixed invariant, case-derived, rejected, and build-sensitive;
> all routes, counts, transforms, thresholds, and hashes are project-specific

## Scope And Current Result

The project replaces Merchant route `cha700` with Karin Cloth04. The supplied
Blend, sibling VRM, and reference Mod remain private project inputs. No game or
Mod Manager launch, installation, game-directory write, or official PAK change
was performed by the build process.

R4 is not a successful release. It is the first tested candidate in this case
that rendered the complete character with coherent source proportions, saved
high-heel pose, UV layout, and materials without catastrophic skinning
explosion. It was still rejected because the outer sandal soles clipped below
the Merchant floor in the tested shop close-up.

The authoritative latest observation is
[`merchant-runtime-feedback-r4.json`](../../../SOURCE_REFERENCES.md#local-only),
bound to this exact archive:

```text
Output/Karin_Cloth04_Replace_Merchant_RE4R_build22377325_R4_SOURCE_PROPORTIONS.zip
SHA-256 635275F6F4A64C52A1BB506D8A82440CFFA7799C0F06CD0B8981A3FEC1E7AFD9
```

This 2026-08-06 snapshot supersedes the earlier prose state that described R4
as waiting for runtime testing. It does not erase R4's offline evidence or the
positive subsystem observations from the tested shop scenario.

## Runtime Evidence Timeline

| Candidate | Runtime result | Narrow conclusion |
| --- | --- | --- |
| R1 `4955F317...A7C9` | Figure viewer: whole-character explosion and long triangles | The packaged Mesh/skeleton runtime contract was incompatible |
| R2 `06111825...F5A4` | Same catastrophic failure after adding only the reference FBXSKEL | A reference FBXSKEL by itself was not sufficient |
| R3 `39730BF6...F7C` | Explosion removed; texture pages, saved heel pose, and source proportions failed | Static donor-compatible binding narrowed the explosion, but loadable geometry was not visually faithful |
| R4 `635275F6...9FD9` | Coherent model/materials/proportions/footwear fit; outer soles below floor | No explosion was visible in this shop close-up, but world-ground contact remained a release blocker; broader bind/animation behavior was not confirmed |

Sources:

- [`merchant-runtime-feedback-r1.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-runtime-feedback-r2.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-runtime-feedback-r3.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-runtime-feedback-r4.json`](../../../SOURCE_REFERENCES.md#local-only)

## Mesh And Bind-Space Lessons

### Parser validity is not bind-space validity

`invariant`, supported by R2 runtime rejection and offline forensics:

- in-range indices, normalized weights, finite matrices, and
  `world * inverse ~= identity` prove internal structure, not that vertices and
  pivots occupy the same bind space;
- measure vertex-to-pivot distances and absolute posed bounds for every positive
  influence, not only the dominant influence;
- report expected comparison count, actual count, and missing-name sets; an
  empty intersection must fail rather than produce a misleading maximum of
  zero;
- edge-length ratios alone are insufficient because a rigid surface can orbit
  a distant pivot without changing its internal edge lengths.

R2's generated face occupied approximately `Y=0.004..0.135` while its embedded
`Head` pivot was at `Y=1.701`. Generated dominant bind-local maxima reached
roughly `48 m` and `70 m` for two slots, versus sub-meter reference maxima.
These values are case diagnostics, not reusable thresholds.

The source-to-target scale and translation must be applied exactly once. R2
computed an absolute target coordinate and then divided it by the target scale,
which also shrank the translation and separated geometry from skeleton pivots.

Evidence:

- [`MERCHANT_R2_MESH_BIND_SPACE_FORENSICS.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r2-mesh-bind-space-forensics.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`audit_merchant_mesh_fbxskel_runtime_contract.py`](../../../SOURCE_REFERENCES.md#local-only)

### FBXSKEL is a semantic contract

`invariant` method, with an R4 `case-derived` implementation:

An FBXSKEL compatibility check must cover names, order, parent indices,
local/world rest transforms, hash and symmetry tables, segment-scaling data,
pose/export mode, and serialized re-import. Every FBXSKEL bone required by the
slot contract must resolve in the Mesh. Weighted bones must first be classified
as shared-FBXSKEL or proven Mesh-local physical branches; only the shared class
must resolve in FBXSKEL. All relevant Mesh slots sharing one FBXSKEL must agree
on the post-export rest matrices of the declared shared set, which R4 computed
as the intersection of FBXSKEL and the participating Mesh slots.

The validator also needs a known-incompatible negative control. Otherwise a
bug that accepts both compatible and incompatible pairs can masquerade as a
gate. R4 used a native 67-bone skeleton combination as that negative control.

R4's `mesh-matched` FBXSKEL retained the template's name/order/parent and
segment-scaling semantics while deriving rest data from the final Mesh. This is
a case strategy for a deliberately rebuilt source-proportion rest pose, not a
universal instruction to regenerate every target skeleton.

Evidence:

- [`build_karin_cloth04_merchant_fbxskel.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-mesh-fbxskel-runtime-contract.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-fbxskel-determinism.json`](../../../SOURCE_REFERENCES.md#local-only)

### The cumulative static-reference fallback is diagnostic

`case-derived`: when the source dynamic-bone frame/unit relationship was not
proved, R3 used a cumulative strategy: it copied the full donor skeleton,
removed generated KRB/KRH branches, fixed the target-coordinate scale error,
collapsed dynamic source weights deterministically to core animation anchors,
and retained route Chains only as compatibility controls. This combined change
removed the catastrophic explosion and isolated binding from physics, but no
runtime candidate tested the collapse as a single variable. The strategy
intentionally sacrificed secondary motion and must not be described as a
general final-physics solution.

## Proportion And Source-State Lessons

### Select the proportion contract explicitly

`case-derived` strategy distinction:

- donor-animation proportions prioritize the target donor's joint layout;
- source-proportion fidelity establishes one coherent source coordinate frame
  for geometry and mapped anchors, then derives bind data and FBXSKEL from the
  final armature;
- local attachment corrections move a bounded rigid package or use a documented
  taper while leaving unrelated anatomy and rest bones fixed.

R3 mixed a global hip scale with per-region directional transfer. It stopped
the explosion but produced donor-like stretching. The independent R4 audit
measured a maximum landmark error of `0.245882 m` and maximum pair-distance
relative error of `6.45545` for the R3 strategy. R4 used one hip-aligned global
similarity transform for all source geometry and directly mapped core heads,
retained donor axes/hierarchy, placed unmapped bones by a documented solver,
and derived the final bind/FBXSKEL from that armature. It reported zero error
across 159 slot-landmark comparisons (53 source landmarks in each of three
partitions) and 4,134 accumulated pair comparisons. These exact values and the
R4 scale are project-only. R4 runtime evidence covers one shop scenario, not a
complete animation or IK matrix.

### Saved shape state is authored geometry

`invariant`, now supported by both the Luis and Merchant cases:

Audit saved values, mute state, drivers, and actions before deleting shape
keys. Bake only an explicit whitelist into evaluated Basis geometry, record the
value, affected vertex count, and maximum displacement, then remove keys.
Reject unexpected non-zero, driven, or muted saved states rather than silently
baking expressions.

R4 explicitly baked one footwear key and two hair-volume keys. The exact names
and values are source-specific and remain in the project report.

Independent fidelity validation should reopen the hash-locked source, recompute
evaluated shape geometry and the declared global transform, then compare
landmarks, pair distances, and a material-scoped triangle multiset. A triangle
multiset comparison tolerates vertex duplication at UV seams while still
detecting missing or changed geometry.

Evidence:

- [`build_karin_cloth04_merchant_meshes.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`audit_merchant_r4_visual_fidelity.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-visual-fidelity.json`](../../../SOURCE_REFERENCES.md#local-only)

## UV, Material, And Transparency Lessons

### Audit every source representation

`invariant` method; source values are `case-derived`:

The optimized atlas is not automatically the richest source of material
semantics. Cloth04's six optimized atlas images had opaque alpha, while the
locked sibling VRM retained an embedded alpha image with 738,713 zero pixels,
309,863 partially transparent pixels, and no fully opaque pixels. This
distribution established continuous-blend intent. The earlier inference that
opaque optimized atlases meant the character had no transparency was
superseded by that VRM evidence.

When all target triangle corners have a unique one-to-one geometric
correspondence, a lost local UV island can be restored from a richer sibling
container. Global vertex counts need not be identical: the optimized Body had
3,578 vertices while the VRM accessor had 3,580. The recovery must write per
loop rather than per vertex and prove all non-target UV loop hashes are
unchanged. R4 searched 48 signed axis transforms, found one complete target
surface match, and restored 1,224 loops for 408 alpha triangles with zero write
error. This method is invalid when correspondence is ambiguous or the target
triangle surface has no complete match.

Evidence:

- [`source-material-channel-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-material-build-report.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`mesh-build-report.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`build_karin_cloth04_merchant_meshes.py`](../../../SOURCE_REFERENCES.md#local-only)

### Close source material, page, render class, and final triangles

`invariant`: material correctness requires a source-material-to-texture-page
and source-material-to-render-class mapping for every final triangle. A broad
body/face/hair guess is not enough. R3 collapsed materials into broad runtime
classes before proving page closure; its material report still said
`accepted=true`, but the runtime candidate rendered as a patchwork. R4 mapped
ten source materials to pages and nine runtime classes and closed all 95,300
triangles of canonical unique character geometry with zero mapping errors.
`Figure` is a byte-identical Body alias and is not counted as another 75,282
triangles. The counts are case-specific; the closure requirement is reusable.

Surfaces sharing atlas RGB and UVs may still need different PBR-derived texture
variants. Do not flatten metallic, roughness, opacity, or shader class into one
page-level constant. Also do not infer opacity from a filename or assume ALBD.A
is opacity; derive the channel contract from source pixels, material semantics,
and the selected runtime donor.

Continuous alpha and cutout are distinct render classes even if an old source
name contains `Cutout`. A continuous-transparent donor must be copied as a
complete compatible layout, then unrelated eye/glass/oil-film effects must be
neutralized deliberately. Hair cutout remains a separate alpha-test contract.
Specific MMTR names and parameter values are build-sensitive.

Evidence:

- [`merchant-r3-material-build-report.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-material-plan.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`build_karin_cloth04_merchant_materials.py`](../../../SOURCE_REFERENCES.md#local-only)

## Preview And Runtime Boundaries

`invariant`: a fidelity preview should bind the final Mesh/MDF hashes, decode
the generated final TEX files, apply the documented RGBA channel contract, and
render enough views to cover the changed surfaces. R4 required front,
three-quarter, side, back, and feet-side views after all material closure and
readback gates passed.

A solid-color authoring viewport cannot validate texture routing. A final-TEX
Blender preview is stronger, but it still does not prove RE MMTR behavior,
animation deformation, IK, route loading, sorting, lighting, wetness/dirt, or
world collision. Camera focus must be derived from the scoped geometry bounds;
a blank or clipped view is a failed preview, not evidence of absence.

R4's display floor was computed as `candidate_min_z - 0.003`, so it followed
the candidate sole and could not independently reveal a Merchant-floor error.
Candidate-derived planes are suitable for presentation only. A contact gate
must use an independently measured target/native/runtime plane.

Evidence:

- [`render_merchant_r4_textured_preview.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-textured-preview.json`](../../../SOURCE_REFERENCES.md#local-only)

## High Heels Require Two Independent Gates

`invariant`, established by the R4 runtime rejection:

1. **Foot-to-shoe fit:** preserve the authored relationship between foot skin
   and the outer sole after evaluating the saved footwear state. The expected
   skin-to-sole gap is source-specific and is not necessarily zero.
2. **Shoe-to-world contact:** test the outer sole against the target runtime
   floor under relevant animation/IK states. An offline feet-side preview has no
   Merchant world plane and cannot pass this gate.

R4 passed the first gate but failed the second. Its audited skin minima were
approximately `-0.001993 m`; the left/right outer-sole minima were approximately
`-0.021055 m` and `-0.021043 m` against the planned `Z=0` floor. The proposed R5
single variable is a `0.021055 m` rigid rise for footwear/accessories, the same
offset for body vertices below the ankle, and a body-only taper to zero at the
knee while keeping rest bones fixed. This is a `hypothesis`, not an accepted
general correction or a completed candidate.

Evidence:

- [`merchant-runtime-feedback-r4.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-textured-feet_side.png`](../../../SOURCE_REFERENCES.md#local-only)

## Determinism And Packaging Lessons

`invariant` method, R4 evidence scope:

- runtime Mesh binaries must be byte-identical across clean builds;
- an authoring `.blend` may embed its save path and differ bytewise, but each
  copy must be hash-bound and normalized scene/report semantics must match;
- material builds must decode final RGBA channels and repeat byte-identically;
- the master contract must derive its resource count from accepted artifacts
  and bind every resource to an accepting report;
- package verification must cleanly re-extract and exactly reproduce the
  accepted path/size/hash manifest.

R4 met these offline gates. Packaging did not protect it from the later
runtime-only ground-contact failure.

Evidence:

- [`merchant-r4-mesh-build-determinism.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`verify_mesh_build_determinism.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-master-contract.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-package-verification.json`](../../../SOURCE_REFERENCES.md#local-only)

## Rejected Sufficiency Claims

Preserve these narrowly:

- `rejected`: adding the reference FBXSKEL alone fixes the R1 explosion;
- `rejected`: normalized weights, valid indices, and inverse-pair consistency
  alone rule out a bind-space explosion;
- `rejected`: checking only dominant influences or only edge-length ratios is a
  sufficient skinning audit;
- `rejected`: removing the explosion makes R3 visually faithful;
- `rejected`: broad role-based material-page assignment is sufficient;
- `rejected`: a solid authoring viewport proves runtime material or proportion
  fidelity;
- `rejected`: baking the saved high-heel state proves both foot-to-shoe fit and
  world-ground contact;
- `rejected`: an offline feet-side preview proves the Merchant floor contact.

## Build-Sensitive Snapshot: Do Not Generalize

The following belong only to this build/candidate family: Mesh and FBXSKEL bone
counts, `5e-3` rest tolerance, bind-radius thresholds, the approximately
`1.507632` global scale, `Figure` byte aliases, `cha7.fbxskel.5`, resource
suffixes, 26-resource package count, MMTR names, PBR constants, TEX encoder
thresholds, and every R4/R5 offset above. Re-extract and re-measure them for any
new target, build, or tool version.

The project used Blender `4.5.12 LTS`, RE Mesh Editor `0.66`, RE Chain Editor
`14.0`, RE Asset Library `0.25`, locked REasy schemas, and deterministic CPU BC7
settings. This is a working snapshot, not a permanent recommendation.

## Rights And Privacy Boundary

The shared case contains no model, VRM, texture, or reference-Mod payload. Use
the project input lock and original license metadata before redistribution.
Technical acceptance cannot expand the source or donor license.

## Key Evidence

- [`SOP.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`AGENTS.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-visual-fidelity.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-material-build-report.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-mesh-fbxskel-runtime-contract.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-mesh-build-determinism.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-r4-package-verification.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-runtime-feedback-r4.json`](../../../SOURCE_REFERENCES.md#local-only)
