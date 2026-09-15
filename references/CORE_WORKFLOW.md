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
