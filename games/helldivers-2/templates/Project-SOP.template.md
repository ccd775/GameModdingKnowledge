# <Character> -> HD2 <Target Slot> Mod SOP

## 1. Objective And Current State

- Objective:
- Current status: `inventoried`
- Last runtime-accepted baseline: none
- Current authoring candidate: none
- Current final triplet: none
- Current package: none
- Deployment authorized: no
- Game launch authorized: no

## 2. Immutable Inputs

| Asset | Path | Bytes | SHA-256 | Role |
| --- | --- | ---: | --- | --- |
| Source model |  |  |  | read-only |
| Reference Mod |  |  |  | read-only |
| Donor source |  |  |  | read-only |
| Donor triplet |  |  |  | read-only |

Rule: recalculate these hashes before and after every write-producing stage.

- Exact user-selected reference directory:
- Reference authoring Blend + compiled triplet identity:
- Reference source-character identity:
- Forbidden/superseded reference lineages:
- Saved nonzero source shape-key map:

## 3. Environment

| Tool | Version/commit | Path | SHA-256 | Notes |
| --- | --- | --- | --- | --- |
| Game |  |  |  | |
| Blender |  |  |  | |
| AQ Modified |  |  |  | |
| HD2SDK CE |  |  |  | |
| FileDiver |  |  |  | |
| texconv |  |  |  | |

## 4. Directory Contract

```text
Ref/                 immutable references
Work/Reference/      read-only imported studies
Work/scripts/        project scripts
Work/tools/          pinned tools
Work/contracts/      machine contracts
Work/reports/        build and gate reports
Work/audits/         diagnostics and rejected evidence
Work/candidates/     immutable versioned candidates
Output/              accepted delivery only
```

## 5. Target Resource Map

| Equipment role | Body type/profile | Target FileID | Complete carrier FileID | Archive | Compile/clone policy | Visible/suppression | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 6. Donor Contract

- Unit version:
- Vertex stride:
- UV count and semantics:
- Skeleton/palette:
- `LegacyWeightNames`:
- Armature Modifier:
- Mesh-local coordinate proof:
- TransformInfo/BoneInfo/inverse-bind provenance:
- Source-to-compiled residual gate:
- Source longitudinal axis -> target chain-axis contract:
- Segment endpoint closure and terminal inheritance policy:
- Source/target shoulder semantic cardinality and many-to-one policy:
- Carrier-per-role lineage and locked triplet hashes:
- Expected compile count and whole-Unit clone targets:
- Declared seam topology and torso/hip/leg ownership graph:
- Natural final-lineage seam-weight error before any post edit:
- Per-seam post-partition edits, rationale, changed vertices, and before/after error:
- Targeted pose moving/excluded bones and measured coverage:

## 7. Material Contract

| Role | Private Material ID | Parent | Texture IDs | Color space | Alpha mode |
| --- | --- | --- | --- | --- | --- |

- Namespace string:
- Full-ID collision gate:
- High32/ShortID collision gate:
- Draw sections by LOD:
- Aggregate private TextureMap base-level budget:
- Semantic texture-area subtotals:
- Namespace reuse policy (`new_namespace` or `exact_lineage_replacement`):

## 8. Frozen Domains And Allowed Delta

### Last Accepted Baseline

- Path/hash:
- User-confirmed behavior:

### Current Iteration

- Problem screenshot/hash:
- Root-cause hypothesis:
- Allowed changes:
- Must remain byte/float identical:
- Targeted differential pose:

## 9. Gate Status

| Gate | Report | SHA-256 | Result | Limits |
| --- | --- | --- | --- | --- |
| Input immutability |  |  | pending | |
| Source/reference audit |  |  | pending | |
| Authoring static |  |  | pending | |
| Standard poses |  |  | pending | |
| Targeted poses |  |  | pending | |
| Shoulder semantic cardinality/partition/seam/frame/axis/mirror/closure |  |  | pending | |
| Natural seam weights before edits / justified per-seam post edits / no artificial transition rings |  |  | pending | |
| Pelvis ownership graph/seams/no direct bypass |  |  | pending | |
| Saved shape-key bake |  |  | pending | |
| Visible compile |  |  | pending | |
| Carrier bind preservation/whole-Unit clone identity |  |  | pending | |
| Suppression geometry and slot ownership |  |  | pending | |
| Compiled postflight |  |  | pending | |
| Material/namespace |  |  | pending | |
| Final integration |  |  | pending | |
| Independent rebuild |  |  | pending | |
| Package |  |  | pending | |
| Deployment |  |  | not_authorized | |
| Runtime |  |  | not_tested | |

## 10. Accepted Artifacts

| Artifact | Path | Bytes | SHA-256 | Status |
| --- | --- | ---: | --- | --- |

## 11. Rejected/Superseded Artifacts

| Version | Path | SHA-256 | Reason | Evidence |
| --- | --- | --- | --- | --- |

## 12. Recovery And Reproduction

```powershell
# Exact commands. Always use new output/report paths.
```

## 13. Deployment And Rollback

- Deployment mode (`new_slot` or `exact_lineage_replacement`):
- Replaced live triplet hashes, if applicable:
- Old/new coexistence prohibited and checked:
- Deployment report:
- Installed paths/hashes:
- Runtime hash binding:
- Exact rollback paths/hashes:

## 14. Known Limits

- LOD:
- gibs:
- splat/dirt/blood/gunk/acid:
- transparency:
- untested equipment/animations:

## 15. Work Log

- YYYY-MM-DD:
