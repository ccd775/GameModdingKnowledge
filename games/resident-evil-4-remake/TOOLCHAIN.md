# RE4R Toolchain And Script Roles

## Tools used in the workspace

| Tool/family | Role | Boundary |
| --- | --- | --- |
| Blender 4.5.12 LTS | source cleanup, shape-key bake, retargeting, material/UV authoring and previews | must be pinned per project; Blender scene validity does not prove RE runtime behavior |
| RE Mesh Editor | Mesh/FBXSKEL import/export and mesh contract inspection | re-import the generated mesh and compare serialized fields |
| RE Chain Editor | Chain topology, terminal, rest-frame and collider authoring | Chain parameters are build- and branch-sensitive |
| RE Asset Library / REasy schema tools | current-build resource inspection and PFB/RSZ field work | derive offsets and schemas from current native files |
| DirectXTex | deterministic BC texture encode/decode and alpha checks | decoded pixels still need material/runtime checks |
| PowerShell/Python | inventories, reports, package assembly, hash and deterministic comparisons | all paths and outputs must be explicit; no wildcard “latest” input |

## Actual project script roles

The workspace projects contain many role-specific scripts. These names are the
stable map an agent should search for or reimplement against the current project:

| Role | Representative scripts | Expected output |
| --- | --- | --- |
| project/input inventory | `New-ProjectInventory.ps1`, `inventory-native-consumers.py`, `extract-native-consumers.ps1` | immutable input and consumer matrix |
| source audit | `inspect_source_mesh.py`, `audit_*_source_semantics.py`, `audit_vrm_physics.py` | mesh/rig/UV/material/shape-key report |
| target/donor audit | `extract_current_merchant.py`, `extract_current_leon.py`, `Extract-SourceDonors.ps1` | current-build target and donor contract |
| retarget/build | `build_*_meshes.py`, `enemy_bridge_retarget_overrides.py`, `build_retargeted_models.py` | derived Blend/mesh plus lineage report |
| materials/textures | `build_*_materials.py`, `audit_*_texture_channels.py`, `build_texture_budget.py` | MDF/TEX/texture budget and channel evidence |
| Chain/physics | `build_*_chains.py`, `audit_*_chain_semantics.py`, `audit_*_chain_frames.py`, `audit_vrm_physics.py` | topology/rest/terminal/collider report |
| PFB/RSZ/controls | `audit_*_pfb_determinism.py`, `audit_*_control_hashes.py`, `Build-GpuClothDisablePatches.py` | semantic field diff and deterministic patch |
| compiled/runtime audit | `audit_*_mesh_reimport.py`, `verify_mesh_roundtrip_semantics.py`, `verify_*_package.py` | serialized closure, package and runtime candidate report |

## Recommended call sequence

```text
New-ProjectInventory.ps1
  -> inventory-native-consumers.py
  -> inspect_source_mesh.py / audit_vrm_physics.py
  -> build explicit consumer and bone maps
  -> build meshes, materials, FBXSKEL and Chain candidates
  -> audit mesh/weights/UV/material/Chain contracts
  -> re-import generated binaries and compare semantic fields
  -> build one-variable PFB/RSZ/JCNS/control candidate when needed
  -> verify deterministic package and exact output manifest
  -> deploy only after authorization and run a candidate-bound runtime matrix
```

Never copy the representative script's bone names, route IDs, offsets, hashes,
or thresholds into a new project. Those values belong to the current-build
reports that the script consumes.

