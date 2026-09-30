# Core Workflow

The game workflows use different formats, but the same engineering loop.

| Gate | Required output | Typical failure caught |
| --- | --- | --- |
| G0 Scope and lock | `PROJECT_STATE.md`, `source-lock.json` | wrong build, wrong donor, unauthorized deployment |
| G1 Consumer inventory | target/owner matrix | missing LOD, hidden consumer, wrong archive/slot |
| G2 Source audit | mesh/rig/material/UV report | unweighted vertices, stale shape state, wrong units |
| G3 Authoring contract | source-to-target map and one candidate | mixed bind spaces, palette overflow, accidental topology changes |
| G4 Serialized validation | decoded binary report | compiler accepted malformed or incomplete output |
| G5 Package validation | deterministic manifest and hash | missing companion, stale resource, nondeterministic archive |
| G6 Runtime validation | candidate-bound test report | wrong route, animation deformation, physics, lighting, or conflict |

## Evidence vocabulary

- `reference-inferred`: useful hypothesis from a donor, documentation, or an
  earlier case.
- `offline-accepted`: declared offline gates pass for the named candidate.
- `runtime-load-pass`: the candidate loads in a named scenario; visual and
  animation coverage may still be incomplete.
- `runtime-rejected`: a named candidate has a blocking runtime defect and must
  not be promoted.
- `runtime-confirmed`: the user confirms the named scenario matrix. Unreported
  maps, actions, conflicts, lighting, cold starts, and rollback remain unknown.

## Universal invariants

- Keep source, donor, build, tool and output identity immutable and hash-bound.
- Treat geometry, bind/rest, weights, materials, UV semantics, resource
  references and runtime behavior as separate contracts.
- Use full 3D mirrored and asymmetric poses to expose wrong axes and seams.
- Validate the final serialized data, not only the authoring scene or compiler
  exit code.
- Preserve negative controls and rejected hypotheses as first-class evidence.
- When a runtime failure survives several content changes, test the environment
  before the next content change: a positive control (framework only), a loader
  negative control (vanilla bytes re-installed at their own vanilla path) and a
  previously working reference Mod. If the negative control fails, stop editing
  the Mod (case: `games/monster-hunter-wilds/cases/KARIN_ORIGINAL_CH03_060.md`).
- Bisect along references, not only along files: a file tested alone still
  carries what it points to (an MDF still references its textures). Give each
  isolated file either its referenced assets or vanilla references.
- Hidden or placeholder parts keep the engine joints that the game attaches to
  (weapon mounts, gadget joints). Find them by sampling several vanilla assets
  of the same slot and keeping the names every one of them has.
- Fit for the pose players see most. When a target joint pivot differs from the source joint (Ghost of
  Tsushima: the hero upper-arm pivot sits about 8 cm outside the source character's shoulder joint),
  any T-pose fit moves the mismatch into the idle pose; solve bind positions from that pose instead of
  tuning T-pose offsets.
- A spatial warp driven by bone and skin-radius control points does not control loose cloth far from the
  bone (leg warmers, platform soles). Apply explicit per-region transforms where the scale must change,
  and compare renders with the source model at the same scale, not only with the previous candidate.
