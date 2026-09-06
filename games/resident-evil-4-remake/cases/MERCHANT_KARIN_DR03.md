# Case Study: Karin DR03 Replaces Merchant

> Status: R3 runtime-rejected; R4 backpack-static package accepted by the user
> Project: `RE4/Karin_DR03_replace_merchant`
> Snapshot date: 2026-08-06
> Game build: Steam `22377325`
> Evidence level: R4 is `runtime-confirmed` for the user's explicit acceptance
> of the exact delivered package; individual route, action, cold-start, and
> lighting results were not enumerated
> Reuse class: mixed invariant, case-derived, rejected, and build-sensitive;
> all bone names, group counts, hashes, routes, and transforms are case values

## Scope And Result

This project replaces Merchant route `cha700` with Karin DR03 using a locked
optimized Blend/FBX, a sibling VRM for saved-state and physics semantics, and a
private Merchant Mod as a route/format reference. The build process did not
launch the game, operate Fluffy Mod Manager, install the package, write the game
directory, or modify official PAKs. Runtime testing and final acceptance were
user-owned.

R3 passed its declared offline Mesh, MDF/TEX, FBXSKEL, Chain, preview,
determinism, and package gates. At runtime, however, the backpack rotated and
lifted onto the shoulder. R4 changed only the campaign-body and Figure Chain
resources: it removed every backpack dynamic group while retaining the Mesh,
weights, physical bones, FBXSKEL hierarchy, materials, ground placement, head
Chain, and all other body physics. The user then explicitly reported that
acceptance passed.

The accepted archive is:

```text
Output/Karin_DR03_Replace_Merchant_RE4R_build22377325_R4.zip
Size 24,229,026 bytes
SHA-256 E8B6AFBFD75725219BA688BD41EB00222CC05FE21DF1F17648C937556ABF0C0D
```

The user did not repeat the hash in the acceptance message. Candidate binding
is based on the explicit acceptance arriving immediately after the unique R4
handoff containing that path and hash. The project report records this
qualification instead of inventing missing scenario details.

## Evidence Timeline

| Candidate | Runtime result | Narrow conclusion |
| --- | --- | --- |
| R3 `C0CDD5CC...90129` | Screenshot: backpack skewed and lifted onto shoulder | Parser/round-trip/deterministic Chain acceptance did not prove stable runtime motion; the generated backpack solve was blocking |
| R4 `E8B6AFBF...0C0D` | User explicitly stated acceptance passed | Removing only the backpack Chain solve while preserving its FBX hierarchy was sufficient for the accepted scope |

R3 remains useful as the matched offline baseline. Its runtime rejection does
not invalidate its independently accepted Mesh, material, skeleton, ground, or
package-integrity reports.

## Runtime-Only Physics Diagnosis

### Compare rest placement, hierarchy, and runtime motion separately

`invariant` method, supported by this case:

1. Confirm whether the source/authoring/final-binary rest geometry is correctly
   placed.
2. Confirm the generated dynamic root has the intended static parent and full
   hierarchy closure.
3. Confirm whether the defect appears only after the runtime solver becomes
   active.
4. Change the smallest layer that first diverges.

In this case the offline textured rest views placed the backpack correctly. The
source root `VRC_DR_03_BAG_1` was parented to source chest bone `Chest__4`, and
the generated runtime root `KRB_000` was correctly parented to `Spine_2`.
Therefore reauthoring vertices, collapsing weights, or moving the anchor would
have changed already-correct contracts. The first observed divergence was the
runtime Chain solve.

A correct parent proves only the static inheritance path. It does not prove
that RE Chain node roles, frames, limits, collision, or source-to-solver
calibration will keep that branch in place.

## Static FBX-Hierarchy Fallback

### Remove the solver, not the whole deformation contract

`case-derived`, runtime-accepted for this exact R4 candidate:

- keep the backpack geometry and original skin weights;
- keep the physical bones and their rest hierarchy in Mesh and FBXSKEL;
- suppress every Chain group that can drive the rejected branch;
- verify the dynamic root still inherits a stable animated core parent;
- leave unrelated physics routes unchanged;
- declare that the branch no longer has independent secondary motion.

With no Chain override, the extra bones retain their serialized local rest
transforms and inherit the animated parent hierarchy. This can preserve the
authored shape more faithfully than collapsing every branch weight into one
core bone, especially when straps or accessories also carry shoulder, arm, or
torso weights.

This is not a universal instruction to keep every failed physical branch as
uncontrolled extra bones. Before using the fallback, prove:

1. all retained bones serialize in every required Mesh/FBXSKEL consumer;
2. the root parent is correct and stable;
3. no PFB, JCNS, collider, or other runtime component requires that branch to
   remain Chain-driven;
4. every Chain path touching the branch is removed from every route;
5. static posed/deformation checks remain valid;
6. the loss of independent motion is an accepted limitation;
7. the exact package receives runtime validation.

If static inheritance is not supported or the retained local transforms are
wrong, a deterministic weight collapse to a proven anchor may be a separate
diagnostic candidate. Do not combine the two strategies and call the result a
single-variable test.

## Branch Filtering After Chain Segmentation

`invariant` implementation lesson; names and counts below are `case-derived`:

Do not identify a rejected branch only by checking whether a final Chain path
starts at its original source root. Merge and overlap segmentation can trim a
shared prefix. Several R3 backpack groups therefore began at descendant bones
such as left/right strap branches rather than at `VRC_DR_03_BAG_1`.

A robust suppressor should match every source node in the path against an
explicit branch membership set or a validated source-name prefix. Then assert:

- exact suppressed group count;
- exact contributing source spring-group set;
- exact retained static-bone closure;
- expected remaining group count per route;
- zero rejected-branch nodes in every final group;
- the same result in every deterministic run.

R4 expected seven suppressed groups per body route, source VRM0 groups `54`,
`55`, and `56`, 17 retained static runtime bones, and 20 remaining groups for
both campaign body and Figure. These numbers are regression guards for this
case, not reusable constants.

## Matched-Baseline Resource Delta

`invariant` method, strongly demonstrated by this case:

A physics fix is not attributable merely because the author intended to touch
one branch. Compare complete accepted trees and make the build fail unless the
actual path/size/hash delta matches the declared variable.

R4 used the accepted R3 staged resource report as its baseline and required:

- changed: `cha700_00.chain.53`;
- changed: `cha700_00_figure.chain.53`;
- unchanged: the head Chain and all 20 non-Chain runtime resources;
- total closure: 23 runtime resources;
- actual result: exactly two changed and 21 byte-identical resources.

This gate protected the already-accepted model, materials, ground offset,
FBXSKEL, and head/hair physics from incidental rebuild drift. It is stronger
than comparing source parameters or trusting a changelog.

The R4 policy validator also used the unchanged R3 Chain report as a negative
control. It rejected R3 because the required branch fallback was absent. A new
validator should prove that the old failing candidate cannot pass under a new
label; acceptance of only the positive candidate is insufficient coverage.

## Offline Chain Gates And Runtime Boundaries

`rejected` sufficiency claim:

> A Chain that parses, survives editor round-trip, has valid ancestry and
> frames, and builds twice byte-identically is therefore runtime-stable.

R3 disproved that claim. Those checks remain necessary and preserve valuable
structural evidence, but source VRM spring values are semantic inputs rather
than a proven one-to-one RE solver calibration. Runtime can still reveal branch
rotation, lift, divergence, collision, or pose-specific instability.

When a structurally valid branch fails at runtime, first decide whether the
desired product truly requires motion on that branch. A stable static fallback
may be the right product decision for a rigid backpack or similar attachment.
If motion is required, continue with isolated topology/frame/parameter/collider
candidates instead of changing Mesh, weights, materials, and physics together.

## Ground Contact And Physics Must Stay Independent

`invariant` candidate-design lesson:

R3 used an independently measured whole-character ground offset and matched the
current native Merchant floor within its declared offline tolerance. The R4
backpack fix reused those exact Mesh bytes. Keeping ground, geometry, and
physics independent prevented a solved floor issue from being reopened while
diagnosing an upper-body accessory.

Do not let a runtime physics complaint trigger a new global transform unless
evidence shows the static geometry or world-contact contract is also wrong.

## Process Guards And Release Automation

### User processes are never build targets

`case-derived` release policy with an `invariant` non-interference rule:

Before Blender, binary conversion, staging, or packaging, detect RE4 and Mod
Manager processes. Never terminate them automatically. Continue read-only
forensics and script preparation while they are active, then resume the heavy
phase only after the user closes them.

This case paused the R4 build while `re4.exe` and later `Modmanager.exe` were
active. The guard prevented concurrent authoring/staging against a user-owned
runtime session.

**Superseded scope note, 2026-08-06:** Chrome Merchant and Wasakura/Luis later
established that process presence is not a universal stop condition for fully
project-local, process-independent offline authoring and packaging when the
user permits it. The reusable rule is to never control user processes and to
block phases whose mutation/runtime boundary actually conflicts. DR03's broad
pause remains its historical project policy, not a requirement for every
offline build.

### Nested PowerShell wrappers must return control

`invariant` automation lesson:

A project Blender wrapper that ends with a bare `exit $LASTEXITCODE` can
terminate an outer release orchestrator immediately after Blender finishes,
skipping staging, contract generation, packaging, or verification. For wrappers
that may be called by another script, run the native tool, throw on a non-zero
exit code, and return normally on success. The outer orchestrator then owns
phase sequencing and final failure handling.

Every long-running release script should also:

- compile/parse its scripts before the heavy phase;
- run the process guard itself;
- stop on the first non-zero phase;
- revalidate output reports rather than trusting console success;
- build archives twice and cleanly re-extract them.

## Runtime Feedback Precision

`invariant` evidence lesson:

- A screenshot can reject a candidate even when cold-start, process, and route
  details are missing; record those fields as `not-observed` and keep positive
  claims narrow.
- If the user does not restate a package hash, record how task context binds the
  report to the delivered candidate and state that qualification.
- An explicit user acceptance can confirm that exact package for the declared
  acceptance scope, but it does not manufacture an itemized route/action/
  lighting matrix that the user did not report.
- Preserve the tested archive bytes. Record feedback in a package-external
  project report and update the SOP; rebuilding the ZIP merely to embed an accepted
  status creates a new, untested candidate hash.
- Update the project SOP immediately after both rejection and acceptance.

## Rejected Shortcuts

Preserve these narrowly:

- `rejected`: structurally accepted offline Chain data proves stable runtime
  motion;
- `rejected`: a correct dynamic-root parent proves the solver will preserve the
  attachment's authored position;
- `rejected`: filtering only paths that start at the original branch root removes
  every group after merge/overlap segmentation;
- `rejected`: a solver-only runtime defect should first be fixed by changing
  Mesh geometry, weights, or FBXSKEL;
- `rejected`: copying VRM stiffness, drag, gravity, and colliders constitutes a
  proven RE Chain calibration;
- `rejected`: package determinism and clean re-extraction prove runtime physics;
- `rejected`: a bare child-script `exit` is harmless inside a multi-phase
  PowerShell release orchestrator;
- `rejected`: explicit user acceptance without itemized scenarios proves every
  possible route, animation, lighting, or conflict state.

## Build-Sensitive Snapshot: Do Not Generalize

The following belong only to DR03 Merchant R4 on Steam build `22377325`:

- runtime root `KRB_000` and static parent `Spine_2`;
- retained backpack bones `KRB_000..KRB_016`;
- source VRM0 groups `54..56` and seven suppressed Chain groups per body route;
- 20 body, 20 Figure, and three head Chain groups;
- 23 runtime resources and 29 package files;
- the exact Mesh, MDF2, TEX, FBXSKEL, Chain, package, and manifest hashes;
- the `0.006787755293771625 m` project ground offset;
- every source-specific atlas, shape-key, material, and bone mapping.

Re-extract and re-measure these for another model, target, build, or tool
version. The reusable result is the evidence method and static-fallback decision
process, not these constants.

## Rights And Privacy Boundary

No source Blend/FBX/VRM, texture, reference Mod payload, or generated game
resource is copied into SharedKnowledge. The project-local input lock and source
license metadata remain authoritative. Technical/runtime acceptance does not
expand redistribution rights.

## Key Evidence

- [`SOP.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-runtime-feedback-r3-backpack.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-runtime-feedback-r4-accepted.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-chain-build-report-r4.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-dr03-runtime-assets-r4.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-dr03-master-contract-r4.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-dr03-package-build-r4.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`merchant-dr03-package-verification-r4.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`build_karin_dr03_merchant_chains.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`stage_merchant_dr03_runtime_assets.py`](../../../SOURCE_REFERENCES.md#local-only)
- [`Build-DR03MerchantRelease.ps1`](../../../SOURCE_REFERENCES.md#local-only)
