# Hitman Toolchain And Script Roles

## Pinned tools used by the project

| Tool | Version | Role |
| --- | --- | --- |
| RPKG Tool CLI/GUI | 2.34.0 | RPKG extraction, GLB/TGA export, PRIM/TEXT/TEXD rebuild and inspection |
| Simple Mod Framework | 2.33.40 | manifest, packagedefinition patching, install, load order and rollback |
| GlacierKit | 1.12.15 | resource search, entity/path/hash checks |
| Blender | 4.2.23 LTS | source normalization, retargeting, weights, UV/material work, GLB export and preview |
| io_scene_glacier | project audit copy | read-only PRIM/BORG/material contract inspection |

Never substitute `latest` for a pinned tool without a new import/export and
roundtrip test.

## Project script roles

The original project used these scripts; their role is portable, while paths,
resource IDs and target constants are project-specific:

| Script | Role |
| --- | --- |
| `scripts/build_texture_atlases.py` | Build deterministic texture atlas candidates |
| `scripts/validate_prim_glb.py` | Validate GLB/PRIM geometry, joints, materials and bounds |
| `scripts/compare_prim_roundtrip.py` | Re-export/re-import comparison for PRIM identity |
| `scripts/rebuild_text_resources.py` | Rebuild TEXT/TEXD payloads from approved images |
| `scripts/deployment_preflight.ps1` | Verify game version, backups, target paths and rollback safety |
| `work/entity-migration/build_entity_migration.py` | Build and validate current TBLU/TEMP entity patch |
| `tools/download_github_asset.ps1` | Download a pinned tool asset for the local tool lock |

## Build order

1. Extract the reference and current Runtime resources; inventory hash, type,
   dependency and owner.
2. Audit the Blend/FBX, bake only deliberate shape-key state, and produce a
   target-skeleton mapping.
3. Export GLB with the carrier's axis, node names and complete influences.
4. Rebuild PRIM/TEXT/TEXD, decode the result, and compare geometry/material/
   skeleton/bounds to the contract.
5. Build the SMF source Mod, deploy only through SMF, and verify generated
   patch resources by independent extraction.
6. Test one explicit outfit/mission matrix; record untested actions instead of
   inferring them from static load success.

