# Case Study: Karin Chrome Replaces Merchant

> Status: R1 received task-local runtime regression feedback; exact R2 package
> accepted by the user
> Project: `RE4/Karin_Chrome_Replace_Merchant`
> Snapshot date: 2026-08-06
> Game build: Steam `22377325`
> Evidence level: R2 is `runtime-confirmed` for the user's explicit acceptance
> of the unique delivered package and its two stated regressions; detailed
> route, action, cold-start, and lighting fields were not enumerated
> Reuse class: mixed invariant, case-derived, rejected, and build-sensitive;
> all material constants, transforms, routes, suffixes, and hashes are case data

## Scope And Result

This project replaces Merchant route `cha700` with Karin Chrome. The locked
optimized Blend supplies authored geometry and atlas organization; the sibling
VRM supplies material-binding and physics semantics; a private successful
Merchant replacement supplies route and format evidence only. The build did not
launch RE4, operate Fluffy Mod Manager, install the package, write the game
directory, or modify official PAKs. Deployment and runtime testing were
user-owned.

R1 passed its declared offline gates. User screenshots then showed two narrow
runtime regressions: the long hanging sleeve straps stayed pure white, and the
feet were slightly below the visible world surface. Those screenshots did not
repeat the R1 archive hash, so they remain task-local regression evidence rather
than strict exact-package promotion evidence.

R2 made two scoped corrections:

- assign the previously unbound `ArmBelts` triangles to a dedicated cool-gray,
  non-emissive PBR material and private roughness texture;
- translate the complete character Mesh and rest skeleton upward rigidly,
  without reshaping the feet, ankles, shoes, or lower legs.

The user explicitly stated that acceptance passed immediately after the unique
R2 handoff:

```text
Output/Karin_Chrome_Replace_Merchant_RE4R_build22377325_R2.zip
Size 43,636,382 bytes
SHA-256 ADED05FF3467120DCB6ED27CB8E6C5015D157C289F00DBD8CA033E2379D98FCA
```

The user did not repeat the hash or itemize the runtime matrix. The project
report records the immediate-handoff binding and leaves costume, chapter,
action, lighting, cold-start, process, conflict, and rollback fields as
`not-observed`.

## Evidence Timeline

| Candidate | Runtime result | Narrow conclusion |
| --- | --- | --- |
| R1 task-local feedback | Hanging sleeve straps appeared invariant white; feet appeared slightly below the scene surface | Offline source/material closure and a native-Mesh minimum-Z match did not prove these runtime appearance/contact details |
| R2 `ADED05FF...8FCA` | User explicitly stated acceptance passed | The isolated strap material override plus rigid whole-character lift were sufficient for the accepted handoff scope |

R1 remains an immutable rollback artifact and historical baseline. R2 acceptance
does not turn its exact color, roughness, scale, or translation into reusable
constants.

## Constant-White Material Diagnosis

### Localize the visible surface before editing shaders

`invariant` diagnostic method:

1. Reproduce the camera direction with neutral source renders.
2. Render front, rear, and both sides because narrow hanging parts can overlap
   clothing in one view.
3. Filter source objects or apply temporary diagnostic tints until the visible
   region maps to one source object and triangle set.
4. Remove all diagnostic overrides before building runtime resources.

The left-side isolated render identified the reported straps as `ArmBelts`.
This was more reliable than guessing from the screenshot, object naming, or
atlas color alone. A diagnostic renderer should derive camera framing from the
scoped geometry bounds, create a neutral World when the source scene has none,
and reject blank or clipped output.

### Audit primitive bindings, not only Blender material slots

`invariant` material rule, demonstrated by this case:

For every source glTF/VRM mesh primitive, record either a valid material index
or an explicit unbound state. An importer or optimized Blend may synthesize a
slot such as `Default_Material`; that slot is a fallback representation, not
proof of an authored source material binding.

The Chrome VRM audit found 17 mesh primitives and 11 materials. Exactly one
primitive was unbound: mesh 8, `RETARGETED__ArmBelts.baked`, containing 3,416
triangles. The optimized Blend consequently assigned all of those triangles to
`Default_Material`. A closure report that merely followed this synthesized slot
to an atlas page could look complete while preserving an unintended white
fallback.

Material closure therefore needs two separate assertions:

- structural closure: every final triangle resolves through Mesh material,
  MDF entry, texture set, and runtime render class;
- semantic closure: every source primitive has an authored binding or a
  documented intentional fallback/override.

Unbound primitives must be counted explicitly. Zero unbound primitives is not
always required, but silently treating them as ordinary authored materials is
not acceptable.

### Constant white does not imply missing emissive

`rejected` sufficiency claim:

> A surface that remains white under lighting must be missing its glow or
> emissive setup.

The source VRM had zero emissive materials. The Blend Principled material saved
an emission strength of `1.0`, but its emission color was black and the socket
was not linked into an active emission path. Saved socket values without graph
connectivity do not contribute to the rendered shader.

Before adding emission, audit all of these layers:

- primitive `material` binding in the source container;
- base-color factor and texture;
- emissive factor and emissive texture;
- Blender node links from texture/value sockets through BSDF to output;
- final Mesh material name/index, MDF master material and parameters, and TEX
  paths/channels.

A missing or fallback material commonly renders bright/default white. Adding
emission can amplify the symptom and erase useful lighting response. Diagnose
binding and base PBR first.

### Isolate the override to the proven triangle set

`invariant` candidate-design rule with a `case-derived` implementation:

When the source semantic is missing and runtime evidence identifies one bounded
surface, create a dedicated material class or derived texture only for that
triangle set. Assert that every other source-to-runtime material mapping is
unchanged.

R2 mapped only the 3,416 `ArmBelts` triangles to
`KR_Chrome_ArmBelts_CoolGray`, used `BaseColor=[0.48, 0.58, 0.78, 1.0]`, packed
roughness `0.70`, and disabled emissive. Those values are a runtime-accepted
choice for this character, not a generic strap preset. The reusable lesson is
the isolated ownership and complete MDF/TEX readback, not the constants.

## Ground Contact Diagnosis

### Native geometry minimum is not automatically the world plane

`invariant`, reinforced by both Merchant cases:

A target/native Mesh minimum Z is a geometry measurement. It may include sole
thickness, pose-specific vertices, hidden geometry, or a coordinate convention;
it does not by itself prove the scene's runtime contact plane. Likewise, a
preview floor derived from candidate bounds follows the candidate and cannot
independently expose a contact error.

R1 matched the audited native Merchant minimum at approximately
`-2.771882 mm`, yet the runtime screenshot still showed slight penetration
against the visible scene surface. R2 instead used the reported scene contact as
feedback and moved the character upward by `2.771882 mm`; the final body minimum
was approximately zero within export precision. These measurements are
case-derived. A new project must re-measure its own target and runtime scene.

### Choose rigid whole-character correction only when its invariants hold

`invariant` decision method; R2's displacement is `case-derived`:

Use a common rigid translation when evidence says the authored assembly,
foot-to-shoe fit, proportions, and local deformation are already correct and the
remaining error is a common world-placement offset. Apply the same translation
to every participating Mesh partition and the rest skeleton used to derive bind
and skeleton resources. Do not move only visible shoe vertices while leaving
their pivots behind.

Use a bounded lower-leg/body correction instead when only footwear or a local
region is wrong relative to an otherwise correct character placement. Preserve
the distinction between:

- foot-to-shoe fit;
- shoe-to-world contact;
- complete character-to-world placement.

R2 changed the global Mesh/rest placement and did not warp the shoes, ankles, or
lower legs. Two clean Mesh builds were byte-identical, the Mesh-derived FBXSKEL
was rebuilt twice, and the final minimum-Z gate passed.

### A valid dependency may remain byte-identical

`invariant` validation principle with case evidence:

Invalidate and re-audit every rest-dependent resource after a global transform,
but do not require bytes to change merely to prove that the audit ran. A common
rigid translation preserves local bone directions and relative frames. Chrome
R2 therefore produced new Mesh and FBXSKEL bytes while all three Chain binaries
remained byte-identical to R1 after topology, ancestry, frame, collider, editor
round-trip, and deterministic-build checks passed.

The opposite shortcut is also invalid: unchanged Chain bytes do not by
themselves prove that no Chain impact exists. The semantic impact audit is the
gate.

## Debugging And Validation Pattern

The reusable workflow from this case is:

1. Bind runtime feedback to the candidate when possible and split independent
   symptoms by layer.
2. Map each screenshot region to a source object/triangle set with focused
   multi-view renders.
3. Parse the richer source container with structured glTF/VRM accessors; do not
   infer primitive bindings or emission from imported names alone.
4. Form one narrow correction per symptom and identify its exact owning
   resources.
5. Rebuild every invalidated resource, even when a semantically unaffected
   local resource may reproduce identical bytes.
6. Re-import Mesh/MDF/TEX/FBXSKEL/Chain outputs, close every triangle and bone,
   decode final TEX, and build twice.
7. Assemble from the accepted resource matrix, build the ZIP twice, cleanly
   extract it, and recompute the manifest independently.
8. Preserve the prior archive as rollback and never relabel its bytes.
9. Record acceptance outside the tested ZIP so documentation does not create a
   new untested archive hash.

R2 closed 84,509 unique-character triangles through material semantics and
packaged 27 runtime resources. The exact counts, versions, hashes, and encoder
thresholds are regression guards for this project only.

## Process-State Boundary

`invariant` safety distinction, demonstrated by this project's explicit user
boundary:

- detect and record relevant processes when useful;
- never terminate, control, or repurpose a user-owned RE4, Mod Manager, or
  Blender process;
- allow independent project-local authoring, conversion, staging, and packaging
  to proceed when authorized and when no game-directory or manager write occurs;
- require phase-specific closure and ownership preconditions before install,
  removal, game-tree mutation, manager operation, or runtime testing.

This narrows the older DR03 case policy that treated any active process as a
blanket heavy-build stop. The deciding factor is the mutation and runtime-state
boundary, not the process name alone.

## Rejected Shortcuts

Preserve these narrowly:

- `rejected`: constant white means emission should be added;
- `rejected`: a saved emission strength proves active emission without tracing
  node links and output connectivity;
- `rejected`: an importer-created `Default_Material` is equivalent to an
  authored source primitive binding;
- `rejected`: final Mesh/MDF name alignment alone proves source material
  semantics;
- `rejected`: broad atlas-page changes are the first response to one localized
  material defect;
- `rejected`: native Mesh minimum Z alone proves the runtime world floor;
- `rejected`: a candidate-derived preview floor proves world contact;
- `rejected`: a common world-placement error should first be fixed by locally
  deforming feet, shoes, ankles, or lower legs;
- `rejected`: every invalidated dependency must produce different bytes;
- `rejected`: deterministic packaging proves runtime lighting or ground contact;
- `rejected`: a short user acceptance invents an unreported full runtime test
  matrix.

## Build-Sensitive Snapshot: Do Not Generalize

The following belong only to Karin Chrome Merchant R2 on Steam build
`22377325`: route/suffix paths, four Mesh and four MDF aliases, the 237-bone
FBXSKEL, Chain groups and hashes, the 27-resource package, all PBR constants,
the `1.5166894441905066` scale, both global Z offsets, BC7 thresholds, and all
archive/tree hashes. Re-extract and re-measure them for another source, target,
build, or tool version.

The project used Blender `4.5.12 LTS`, RE Mesh Editor `0.66`, RE Chain Editor
`14.0`, DirectXTex CPU BC7 encoding, and current project-pinned scripts. This is
a reproducible case snapshot, not a permanent tool recommendation.

## Rights And Privacy Boundary

No source Blend/FBX/VRM, texture, private reference Mod, or generated runtime
payload is copied into SharedKnowledge. The source license prohibits
redistribution and restricts several uses. Technical and runtime acceptance does
not expand those rights.

## Key Evidence

- [`SOP.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-chrome-runtime-feedback-r2-accepted.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`chrome-vrm-mesh-material-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-material-build-report-r2.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`mesh-build-report.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`fbxskel-determinism-r2.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-chain-build-report-r2.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-chrome-package-build-r2.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`render_chrome_source_diagnostic.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`audit_chrome_vrm_mesh_materials.py`](../../../SOURCE_REFERENCES.md#local-only)
