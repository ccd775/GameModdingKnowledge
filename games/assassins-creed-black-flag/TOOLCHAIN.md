# Black Flag Resynced Toolchain And Script Roles

## Actual tool decisions

| Tool | Version/status | Role |
| --- | --- | --- |
| Blender | 4.2.23 LTS | source Blend/FBX audit, model staging and preview |
| Project Forge v50 parser/rebuilder | project scripts | final container authority; parses BMS0/BMS1 and raw LZ4, replaces named decoded resources |
| AnvilToolkit | 1.3.6, research only | names, format comparison, glTF preset research and bundled codec comparison; not a BFR compiler |
| Forge Injector | v4-labelled archive, research only | external behavior comparison; not an FBX/GLB/PNG compiler |
| DirectXTex `texconv` | pinned build | texture conversion where a target resource contract requires it |

## Scripts used in the project

| Script | Role |
| --- | --- |
| `scripts/audit_blend.py` | source mesh/armature/material/shape-key/weight audit |
| `scripts/extract_forge_v50_bms.py` | parse Forge v50 outer table, BMS framing, raw LZ4 and checksums |
| `scripts/rebuild_forge_v50_patch.py` | preserve outer IDs/order/untyped sections while replacing explicitly named decoded resources |
| `scripts/build_candidate_ay_v161_local_mouth_switch.py` | create the one-Bool Karin outfit-local mouth candidate |
| `scripts/install_candidate_ay_v161_local_mouth.py` | plan/install/verify/rollback with build/hash guards |
| `scripts/recover_shared_heads_build24833802.py` | restore shared NPC head rows after the rejected broad edit |
| `scripts/runtime_input_bridge.ps1` | manual runtime handoff; only use when the user authorizes input control |
| `scripts/send_runtime_key.ps1` | send a single controlled test input to the authorized game window |

## 1.6.1 verified sequence

The current local-mouth candidate changed one Bool from `1` to `0` inside the
Karin outfit resource. The installer restored 21 historical shared Mesh/
LODSelector rows, then verified that only four Karin outfit TOC rows differed
from the original boot. Independent decoding passed 873 checks; shared native
head data was restored; the user subsequently confirmed the result in game.

## Full replacement boundary

The local mouth repair does not remove the need for a full target-resource
inventory when building a new character replacement. The matching game build,
boot Forge, target Skeleton/Mesh/Material resources and tool versions remain
mandatory inputs for any new replacement.

