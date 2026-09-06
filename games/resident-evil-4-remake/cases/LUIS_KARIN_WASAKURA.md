# Case Study: Karin Wasakura Replaces Luis

> Status: r5 accepted by the user for the delivered task scope
> Project: `RE4/Karin_wasakura_replace_luis`
> Snapshot date: 2026-08-06
> Game build: Steam `22377325`
> Evidence level: offline gates accepted; exact r5 package is
> `runtime-confirmed` for the stated user-acceptance scope
> Reuse class: mixed invariant, case-derived, rejected, and build-sensitive;
> every route, count, transform, bone ID, Chain group, and hash below is a case
> value unless explicitly classified otherwise

## Scope And Accepted Result

This project replaced Luis in campaign and Mercenaries consumers with the
supplied optimized Karin Wasakura Blend/FBX. A sibling VRM supplied saved-state,
spring, collider, material, and license semantics. A private Merchant Mod was
useful for atlas/material/package examples, but it was not Luis route, skeleton,
Chain, or PFB authority. Current build resources and the independently extracted
consumer matrix supplied those contracts.

The accepted package is:

```text
Output/Karin_Wasakura_Replace_Luis_RE4R_build22377325.zip
Size 96,328,944 bytes
SHA-256 078C83A7592D9422B013C781DD8565D1723C8D819F18E6D3845504D87770488A
47 runtime resources / 54 total files
```

The exact tested bytes are also preserved under `Work/accepted-candidates`.
The user first reported that the r5 skirt appearance was normal, then explicitly
stated that task acceptance passed. The final acceptance is bound by task
context to the unique r5 archive above. It confirms the user-observed Atlas,
fringe/ribbon, body-proportion, shoe-floor, and skirt-silhouette scopes. It does
not invent an itemized campaign/Mercenaries, costume, chapter, cutscene,
animation, lighting, conflict, cold-start, or long-session matrix.

Authoritative state and evidence:

- [`SOP.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-20260806-r5-task-accepted.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`final-package-verification.json`](../../../SOURCE_REFERENCES.md#local-only)

## Candidate And Runtime Timeline

| Candidate | Exact runtime result | Durable conclusion |
| --- | --- | --- |
| Initial UV1 package `886DAFFC...C7D4` | Atlas images loaded, but face, hair, skin, and clothing sampled unrelated regions | A self-consistent Mesh round-trip did not prove that runtime UV1 carried the source material's intended UV set |
| r2 `3B5E711E...D079` | Textures were corrected; fringe and green ribbons stayed lifted, one skirt side collapsed, torso looked stretched, and soles entered the floor | The UV repair was valid, but packaging/offline closure did not prove physics, proportions, or runtime ground contact |
| r3 `CDEE0D11...3D1D` | Fringe, ribbons, proportions, and shoe-floor appearance were corrected; one skirt side remained abnormally compressed/displaced | Terminal, collider, proportion, and lower-leg fixes were positive runtime observations; the remaining failure was branch-local |
| r4 `E9DF731F...977` | The suppressed side became normal while the still-dynamic opposite side bulged outward | The screenshot's earlier directional interpretation was unreliable, but the controlled Chain-only delta still isolated the active solver as causal |
| r5 `078C83A7...88A` | Both skirt sides had a normal silhouette; user then accepted the task | Bilateral side-panel static hierarchy was accepted; center/back skirt physics remained active |

Every rejected archive was preserved as a negative control. A newer candidate
did not erase narrower accepted subcontracts from its parent: for example, the
r2 runtime rejection did not invalidate the source-to-runtime UV repair.

## Source, Build, And Bone-Budget Contract

The optimized Blend snapshot contained 16 Mesh objects, 63,213 vertices,
112,861 triangles, 277 bones, and 264 weighted bones. Five nonzero saved shape
states were evaluated and baked exactly once. The sibling VRM supplied 33 spring
groups, 67 spring roots, 13 collider groups, and 32 colliders. These counts and
saved values are case-derived, not Karin or Luis constants.

The source representations had separate authority:

- Blend geometry and weights were the authored visual source;
- VRM spring/collider metadata supplied physical semantics;
- current Luis resources supplied consumer, route, version, header, control,
  and target animation contracts;
- the private Merchant reference supplied only the material/package roles that
  were independently applicable.

The body Mesh reached 240 bones by retaining 77 current-Luis base bones and 163
Wasakura physical bones. Adding 32 unweighted compatibility helpers from an
earlier Luis case would have exceeded the 256-bone project limit. The project
therefore omitted those helpers, patched exactly three current-build PFB
`JointConstraints` Boolean fields, and left native JCNS/JMAP out of the package.
The reusable lesson is to solve bone budget and control strategy together before
authoring; the counts and PFB fields are build-sensitive.

## Runtime UV Routing, Not Blender Active State

`invariant` contract demonstrated by a runtime rejection and accepted repair:

A UV layer's name or Blender active/render flag does not prove which serialized
runtime UV stream the exporter will write. The contract must close all four
links:

```text
source material intent
-> authoring UV layer and positional index
-> serialized Mesh UV stream
-> runtime material/MMTR sample
```

All four Wasakura source materials used `UV_Atlas`. The rejected authoring
objects ordered layers as `[UV_Source, UV_Atlas]`. For the pinned RE Mesh
exporter, `uv_layers[0]` became runtime UV1 and `uv_layers[1]` became runtime
UV2, irrespective of the Blender active/render markers. The game therefore
sampled Atlas textures with `UV_Source`.

The first validator re-exported and re-imported the already-wrong Mesh. It
proved byte/semantic stability around the wrong mapping and could not prove
source intent. The repair promoted `UV_Atlas` to layer zero, retained
`UV_Source` as runtime UV2, and required:

- fixed runtime UV1 to equal rejected runtime UV2 exactly;
- exact source UV coverage on every source Mesh;
- unchanged topology, material slots, coordinates, weights, hierarchy, and
  rest matrices across all 17 exported submeshes;
- refreshed downstream Mesh-dependent reports and a deterministic package.

When a complete Atlas loads but islands appear globally scrambled, inspect UV
stream provenance before repainting textures, changing MDF parameters, or
blaming TEX encoding.

Evidence:

- [`runtime-feedback-20260806-uv1.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-uv-channel-fix.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-r3-uv-preservation.json`](../../../SOURCE_REFERENCES.md#local-only)

## Authoring Parenting And Evaluated Source State

`invariant` validation lesson:

An authoring object can retain a stale Armature parent transform or
`matrix_parent_inverse` after collection cleanup. In early builds this created
a 100x/axis authoring-space defect even though the serialized Mesh happened to
match a later output. Matching runtime bytes did not retroactively make the
authoring container a trustworthy source of truth.

The builder cleared unintended object parenting and parent inverse before
attaching the one intended Armature modifier. Independent binding audits then
required identity-scale object/world placement and expected bounds in two clean
roots. This is separate from the saved-shape audit: evaluated nonzero shape keys
must be baked from a whitelist before deletion, exactly once.

Do not use a final binary hash alone to bless a broken authoring scene. Validate
both the delivery binary and the normalized scene semantics that will be used
for the next edit.

## Preserving Source Proportions

`case-derived` repair supporting a reusable transform rule:

The rejected rig used per-bone donor-directional placement. It stretched the
source `Spine`-to-`Chest` interval across a longer Luis donor interval, making
the upper torso look elongated. R3 instead used one Hip-anchored global
similarity transform for visible vertices and source physical rest bones while
preserving native Luis core-animation rest matrices exactly.

The exact scale `1.463541989263906` and landmarks belong only to this source,
target, and build. The reusable rule is to choose the proportion mode before
retargeting and apply one coherent source frame. Per-anchor donor conformance
and source-proportion preservation are different products; mixing them
silently can stretch anatomy even when each individual mapped point looks
plausible.

Evidence:

- [`runtime-feedback-20260806-r2-physics-proportion-ground.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-r3-geometry-audit.json`](../../../SOURCE_REFERENCES.md#local-only)

## Shoe Art, Lower-Leg Transition, And Floor

The source-proportion candidate placed the shoe minimum at
`-0.03591229021549225 m`. R3 rigidly raised the shoe art by the opposite amount
and applied a knee-fixed taper to the lower-leg body, socks, and ankle ribbon.
The corresponding ankle-ribbon physical rest bones received the same bounded
correction. The final offline shoe minimum was exactly `0.0 m`, with no triangle
flips or new near-zero triangles, and the user later observed that the soles no
longer appeared below the floor.

The exact offset and ankle/knee heights are case-derived. Reusable rules:

- preserve rigid shoe/accessory art rather than compressing it to fit;
- fade body-only compensation to zero at a stable anatomical boundary;
- move dedicated physical rest bones coherently with corrected geometry;
- keep foot-to-shoe fit and shoe-to-world contact as separate gates;
- treat an offline plane as runtime-ground evidence only when it comes from an
  independent target/native measurement.

## VRM Collider Units And Coordinate Reconstruction

`invariant` transform/validation method, with case-derived measurements:

VRM collider centers must travel through the same final source-to-target
coordinate contract as the physical rest rig. Do not compute Chain-local
collider offsets through a stale source armature inverse containing an
authoring scale.

The rejected conversion included the source `0.01` scale in an armature inverse
and produced a maximum local collider offset of about `33.27 m`; the skirt
effectively had no useful body collision. R3 instead mapped the source collider
center into final world target space, subtracted the final target bone position,
converted the difference with only the target-bone rotation required by the
serialized convention, and validated the inverse reconstruction.

The corrected maximum local offset was about `0.316 m`, and maximum reconstructed
world-center error was about `3.34e-8 m`. Those thresholds are case values. A
new project should establish scale-relative bounds, reconstruct every final
collider back into world space, and retain the previous unit-defective result
as a negative control.

Collision correctness still does not prove droop, spring response, or runtime
stability. Keep topology, frames, parameters, and collision as separate
variables.

Evidence:

- [`runtime-r3-physics-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`chain-build-report-r3.json`](../../../SOURCE_REFERENCES.md#local-only)

## Visible Roots Need Real Terminal Helpers

The rejected head groups inserted a visible bone's parent before the visible
branch. That made the intended visible root the final/terminal node instead of
the simulated segment. Stronger gravity would not fix the topology.

R3 used three Wasakura-specific, collinear, zero-weight helpers for the front
fringe and green ribbons. The final paths were visible deform root -> terminal
helper, with no parent proxy prepended. Re-import proved zero positive weight
assignments on the helpers. The user then observed that the fringe and ribbons
no longer stayed lifted.

This independently corroborates the terminal-helper method from the Riptide
Luis case. It does not make either project's helper indices reusable. Always
derive the visible root, parent, tail direction, appended bone identity, and
route closure from the current final Mesh.

## Diagnosing Mirrored Skirt Failures

### Separate observation from source-branch identity

`invariant` evidence rule:

A screenshot can reliably show an abnormal silhouette without reliably proving
which named source branch crossed the body. Camera mirroring, character facing,
bone naming conventions, overlapping cloth, and the deformation itself can all
make visual left/right labels ambiguous.

R3 offline evidence already showed mirrored left/right skirt bone-head rest
positions below one micrometre and reconstructed mirrored hip/upper-leg
colliders. The runtime screenshot suggested that one side had been pushed
across the body, but this was an observation, not proof of source-bone migration.

R4 changed only the three body Chain resources and suppressed the source
`skirt_R_*` paths while keeping Mesh, weights, rest bones, materials, TEX, PFB,
FBXSKEL, and head Chains unchanged. The suppressed visual side became normal;
the still-dynamic opposite side then remained inflated. This corrected the
directional story while strengthening the causal result: the active side-skirt
Chain solve, not static Mesh placement, drove the bad silhouette.

### Bilateral static side-panel fallback

R5 suppressed both mirrored side-panel branch sets across every body route. It
retained all 72 side-skirt bones as deforming, weighted children in the FBX
hierarchy, so they followed the animated hip without an RE Chain override.
Center and back skirt groups remained dynamic.

The complete r4-to-r5 candidate diff contained exactly three changed body Chain
resources, 44 byte-identical runtime resources, and no path additions/removals.
All side-branch nodes had zero Chain survivors; retained center/back groups and
collisions remained semantically unchanged apart from deterministic setting-ID
renumbering. The package built twice identically and received user acceptance.

Reusable decisions:

- one-sided suppression can be a diagnostic candidate rather than a final fix;
- if both mirrored active branches show the same class of instability, a
  bilateral coherent fallback can be the next single semantic variable;
- retain geometry, weights, physical bones, parents, and static rest placement;
- remove every Chain group touching the rejected membership set in every route;
- assert both exact changed paths and the complete unchanged resource set;
- keep stable independent branches dynamic when the product allows it;
- disclose the exact lost motion and require runtime acceptance.

The accepted limitation here is explicit: left and right side panels have no
independent secondary sway, while center and back skirt panels retain physics.

Evidence:

- [`runtime-feedback-20260806-r3-right-skirt.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-20260806-r4-left-skirt-bulge.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-r5-bilateral-skirt-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-r5-candidate-diff.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-20260806-r5-skirt-accepted.json`](../../../SOURCE_REFERENCES.md#local-only)

## Offline Packaging Versus Runtime Process Guards

`invariant` authorization/safety rule refined by this project:

Guard the operation that can mutate or depend on live runtime state, not the
mere existence of a process.

This task was explicitly limited to a workspace-local deployable package. The
packager neither installed files nor read a mutable deployed candidate as a
build input. Under the user's clarification, active RE4/Fluffy processes were
recorded but did not block deterministic authoring, staging, ZIP creation, or
verification. The build never controlled those processes or wrote the game
directory.

By contrast, candidate switching, Fluffy-managed enable/disable, external loose
deployment, live-tree verification, or any game-directory write still requires
the deployment-owner and process rules in `VALIDATION_AND_RELEASE.md`.

Likewise, a Steam appmanifest can change non-build state after runtime use. For
this release, the stable identity gate was build ID plus locked executable and
official resource inputs, not byte equality of mutable manifest text. A project
must declare which manifest fields are identity authority and which are dynamic;
it must not silently waive a changed build ID, executable, PAK, or archive
priority.

## Immutable Accepted Archives

The r5 ZIP was not rebuilt to embed the later runtime status. Its accepted copy
was archived byte-for-byte, and user feedback was written to external JSON and
the project SOP. This preserves the evidence-to-artifact binding.

Repacking documentation after a runtime test creates a different archive hash
with no runtime evidence. Package-internal wording can remain historically
offline-only; the project record selects the newer external acceptance state.

## Rejected Shortcuts

Preserve these claims narrowly:

- `rejected`: Blender active/render UV state proves the runtime UV stream;
- `rejected`: re-importing a wrong Mesh and comparing it to itself proves source
  material intent;
- `rejected`: globally scrambled Atlas placement should first be fixed by
  repainting textures or changing all MDF parameters;
- `rejected`: per-bone donor-directional placement preserves a source-proportion
  product merely because mapped anchors individually look plausible;
- `rejected`: a collider-local transform containing stale source armature scale
  is acceptable if the Chain file parses;
- `rejected`: adding the visible bone's parent before a missing terminal is an
  equivalent substitute for a real zero-weight terminal helper;
- `rejected`: a visual left/right screenshot label proves the identity and
  cross-body path of a named source-bone branch;
- `rejected`: one mirrored side becoming normal proves the opposite active side
  is already stable;
- `rejected`: making a branch static requires deleting its bones or collapsing
  all of its weights;
- `rejected`: offline structural Chain acceptance proves runtime skirt motion;
- `rejected`: active RE4 or Fluffy processes alone must block a strictly
  workspace-local package build that performs no deployment or live-tree write;
- `rejected`: user acceptance permits rewriting the tested ZIP to add an
  accepted label without creating a new candidate.

## Reusable Diagnostic Sequence

For a future VRM-derived replacement with mixed visual defects:

1. Bind feedback to the exact package hash and preserve the screenshot.
2. Split Atlas, static geometry, proportions, contact, topology, collision, and
   runtime solver symptoms into separate contracts.
3. For global Atlas scrambling, close source UV intent to serialized runtime UV
   index before touching texture pixels or MDF tuning.
4. For stretched anatomy, compare the declared proportion strategy against
   source and donor landmark intervals.
5. For floor clipping, measure rigid shoe art separately from body transition
   geometry and actual runtime floor evidence.
6. For upturned one-segment appendages, inspect true root/terminal roles before
   changing gravity.
7. Reconstruct every collider into world space and reject unit-scale outliers.
8. For a runtime-only branch displacement with correct static placement, build
   a Chain-only matched candidate and assert the entire unchanged resource set.
9. Treat a one-sided mirrored fallback as diagnostic evidence; let the result
   determine whether the smallest coherent final variable is unilateral or
   bilateral.
10. Build binaries and packages twice, keep rejected archives, and store runtime
    status outside the immutable tested ZIP.

## Build-Sensitive Snapshot: Do Not Generalize

The following belong only to this Wasakura/Luis r5 snapshot on Steam build
`22377325`:

- campaign/Mercenaries route paths and resource suffixes;
- the 240-body/71-head/17-face bone contracts and all `KRB_*`/`KRH_*` IDs;
- the `1.463541989263906` source scale and `0.03591229021549225 m` shoe offset;
- all collider thresholds, Chain groups, route headers, terminal lengths, and
  suppressed skirt memberships;
- the three PFB fields, FBXSKEL aliases, material parameters, and TEX packing;
- 47 runtime resources, 54 ZIP entries, and every artifact hash.

Re-extract current resources and re-measure all of them for another model,
target, game build, or tool version.

## Rights And Privacy Boundary

No private model, texture, reference Mod, or generated game binary is copied
into SharedKnowledge. The project-local input lock records source hashes and
the VRM metadata used during the authorized task. Technical and runtime
acceptance do not expand redistribution rights.

## Key Evidence

- [`input-lock.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`consumer-matrix.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`source-semantic-contract.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`source-vrm-semantic-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`mesh-build-determinism-r3.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-r3-geometry-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-r3-physics-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`chain-build-report-r5.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-r5-bilateral-skirt-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-r5-candidate-diff.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`independent-package-verification.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-20260806-r5-task-accepted.json`](../../../SOURCE_REFERENCES.md#local-only)
