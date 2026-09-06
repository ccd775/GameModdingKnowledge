# Karin Watch Dogs production pipeline

Last updated: 2026-08-05

## Current release contract

The active release is `Karin Default Outfit Replacer 1.3.0`. It completely replaces only Aiden's default Vigilante outfit. Shop skins, DLC outfits, the prisoner/intro model, and story-forced models are out of scope.

Published artifacts:

- Directory: `dist/karin_replacer_v1_3_0/`
- ZIP: `dist/karin_replacer_v1_3_0.zip`
- ZIP size: 5,752,682 bytes
- ZIP SHA-256: `5B2BE5A472F5AFCA0B0F42BF3BA80B89FE24481701E72C846DA00B86041701FB`
- Freeze: `.work/release_freezes/karin_replacer_v1_3_0/RELEASE_FREEZE.json`
- Status: tool gates passed, ModManager payload matched, user accepted in game on 2026-08-05
- Accepted limitation: minor residual finger deformation in some gun and pocket animations

The release and freeze files are read-only. Do not rebuild into or overwrite the `1.3.0` paths. Any changed asset requires a new version and release directory.

## Authoritative chain

```text
karin_D7-E4-04_uv_optimized.blend
  -> cleaned immutable source
  -> fix_karin_v13_final_issues.py
  -> 35_candidate_v1_3_hole_exact.blend
  -> ponytail / pose / collar audits
  -> diffuse-only atlas and dual LOD build
  -> orientation-fixed FBX
  -> ZModeler double bind and clean L0/L1 Compound
  -> raw char01.xbg
  -> GPU-buffer audit and fresh-process reimport
  -> private neutral-hair material table patch
  -> 22-item Living City-compatible workspace
  -> FAT/DAT pack, unpack comparison, deterministic ZIP
  -> ModManager install and in-game acceptance
  -> immutable 1.3.0 freeze
```

Authoritative assets:

- Blender: `.work/v13/35_candidate_v1_3_hole_exact.blend`
  - SHA-256 `0D60FE536B742A35CEBD870A39A95069C34A6C4A856C2624441DCF5DBE5D085F`
- Dual LOD: `.work/module_build/karin_v13_hole_exact_final/karin_modules_lod_karin_v13_hole_exact_final.blend`
  - LOD0: 45,003 vertices / 84,586 triangles
  - LOD1: 15,828 vertices / 28,488 triangles
- FBX: `.work/fbx_handoff/karin_v13_hole_exact_final_orientation/karin_char01_scale001_orientation_fixed.fbx`
  - SHA-256 `98FE401213627B4E630D64D29CDA37F43BDB1E86CE339A20261472C1C6237126`
- Z3D: `.work/zmodeler_production/karin_char01_v13_hole_exact_final/project/char01_karin_v13_final_compound_checkpoint.z3d`
  - SHA-256 `CD8E70ACFF29A0BF6921707374FB49556DB67700B52FBC27197CAB2E45F13F30`
- Raw XBG: `.work/zmodeler_production/karin_char01_v13_hole_exact_final/output/graphics/characters/char/char01/char01.xbg`
  - SHA-256 `D77BA08F1630CA1E58E103A2BAE8878C7165917C55BD657D16B13DA2CC7E73F7`
- Runtime neutral-patched XBG:
  - SHA-256 `719307B4957F155A49AB09D37BE4627A6CB9AE936EDD5F693899BBE740CFE203`

## Production scripts

Current authority:

- `fix_karin_v13_final_issues.py`: final hand, ponytail-root, and collar changes.
- `audit_karin_ponytail_hole_alignment.py`: two-sided hair-band-hole gate.
- `diagnose_karin_v13_hand_collapses.py`: hand stress diagnostics.
- `audit_karin_v13_components.py`: final component checks.
- `apply_karin_atlas_uv.py`: apply the frozen diffuse-only atlas UV layout.
- `build_karin_modules_lod.py`: build LOD0 and LOD1.
- `build_karin_char01_fbx_handoff.py`: create the binary FBX handoff.
- `audit_karin_char01_fbx_handoff.py`: FBX structure and payload gate.
- `audit_karin_xbg_mesh_buffers.py`: required XBG GPU-buffer gate.
- `build_karin_runtime_v13.py`: neutral material patch, 22-item workspace, FAT/DAT, unpack verification, and release ZIP.
- `build_graphickit_default_all_redirect.py`: rebuild the complete Living City-compatible model database when the effective database owner changes.
- `xbt_tool.py` and `build_xbt_pair.py`: donor-header-preserving XBT processing.

Older `v4`, `v5`, `v6`, `v11`, native-scale probe, and donor-additive scripts are retained only as diagnostics or provenance. They are not current production authority.

## Geometry and XBG gates

The final ZModeler scene must contain exactly two roots:

```text
char01.skel
char01.mesh   (Compound states: L0, L1)
```

An independent `Pelvis`, `LOD*_REBUILT` root, donor branch, third state, radial shards, or empty LOD is a failure.

`audit_karin_xbg_mesh_buffers.py` must return `PASS_CLEAN_TARGET` with:

- LOD0: exactly 84,586 triangles
- LOD1: exactly 28,488 triangles
- exact descriptor index coverage
- every index inside its declared local stream
- no donor submesh sequence, donor faces, or excess faces

Header/string inspection alone is not sufficient. A completely fresh ZModeler Build 1244 process must also reimport the XBG and display complete Karin geometry in both L0 and L1. The validation scene is closed without saving.

Frozen evidence is under `.work/release_freezes/karin_replacer_v1_3_0/evidence/`.

## Texture and material contract

Use the model's original diffuse RGB. Never bake or composite emission, glow, or bloom masks into diffuse. Watch Dogs does not need those masks for this release; compositing them caused glowing regions to become white.

The runtime includes 19 frozen XBT files. Low and `_high` streamed textures are processed separately while preserving the donor XBT header and virtual filename. Do not use `xbt_tool.py --force` for a release.

The private neutral hair material is:

`graphics/_materials/droylouo-m-20260729190000-v6a.material.bin`

- 1,136 bytes
- SHA-256 `28576B7F3A0A9724CF068A28A4BBA52ACED6E6DB768DB1B7514233B4E818DAB9`

The runtime patch changes only the XBG material-table path for the hair slot. The mesh and skeleton payload remains byte-identical.

## Runtime geometry selection

Living City changes `A_MainCharacters.char01_Aiden` from the vanilla single `All` component to modular head, torso, legs, and head-accessory components. A package containing only `char01.xbg` can therefore replace all textures while the game still draws Aiden geometry.

The release includes the complete, identity-audited Living City-compatible `graphickit_models.lib` with only that model's component list restored to the existing vanilla `All` part. Do not replace it with a vanilla database, a one-record delta, or ad hoc binary edits.

- Database SHA-256: `CEA69043A894D5659795E41348364AC740507FAD68CBB9D6BB0DF6FA14A6686E`
- Karin must load above `Living_City` in ModManager.
- No replacement `items.lib`, `graphickit_parts.lib`, or modular outfit XBGs are required.

## Runtime package contract

The internal workspace must contain exactly 22 files:

- 1 `char01.xbg`
- 19 frozen XBT textures
- 1 private neutral-hair material
- 1 complete Living City-compatible `graphickit_models.lib`

The outer ModManager ZIP must contain exactly:

| File | Bytes | SHA-256 |
|---|---:|---|
| `karin_replacer.dat` | 25,585,024 | `6D3D30F1F71869FF1B97F005D4451850AB8292A3230C367DEDB0CFF490830FB6` |
| `karin_replacer.fat` | 372 | `22EC1FCF1E9CFDE573E2CDC8137E87E3CF90AC1CFCEC71A58B3D0FFA4AAC2831` |
| `modconfig.json` | 658 | `110D00641FF3ACD251A6E8E0F784822A790D0586542532715711CEA32A9EF631` |

Do not add source BLEND/FBX/Z3D files, PNG previews, ZModeler sidecars, skeleton exports, emissive textures, unrelated databases, or other outfits.

## Runtime builder

Staging command used before acceptance:

```powershell
python pipeline\build_karin_runtime_v13.py `
  --raw-xbg .work\zmodeler_production\karin_char01_v13_hole_exact_final\output\graphics\characters\char\char01\char01.xbg `
  --expected-raw-xbg-sha256 D77BA08F1630CA1E58E103A2BAE8878C7165917C55BD657D16B13DA2CC7E73F7 `
  --staging-only
```

Publishing command used after acceptance:

```powershell
python pipeline\build_karin_runtime_v13.py `
  --raw-xbg .work\zmodeler_production\karin_char01_v13_hole_exact_final\output\graphics\characters\char\char01\char01.xbg `
  --expected-raw-xbg-sha256 D77BA08F1630CA1E58E103A2BAE8878C7165917C55BD657D16B13DA2CC7E73F7 `
  --publish --replace-staging
```

The builder rejects an unexpected raw-XBG hash, payload count drift, unknown files, failed XBG audits, pack/unpack mismatch, and an existing release path. The frozen `1.3.0` command must not be rerun against the current `dist` paths.

The builder still inherits the 19 frozen diffuse-only textures, private material, and database from:

`.work/runtime_probe_build/karin_replacer_v1_1_0_v3j/workspace/`

Do not delete that directory while this version-specific builder remains the recovery path.

## Release and rollback

The authoritative build report is:

`.work/release_freezes/karin_replacer_v1_3_0/evidence/build_validation_published.json`

- Status: `PASS`
- Mode: `published`
- SHA-256 `F05116E4F5F0B4AEEE0DA054521CF1D1AB9E74F5386DBBEBDCC41A87108E6172`

The package copy and clean ZIP extraction are frozen separately under `package/` and `zip_roundtrip/`; both manifests match the release files byte-for-byte.

For runtime rollback, reinstall `dist/karin_replacer_v1_2_0.zip` using the same `friendlyId`, and keep it above Living City. Do not alter original game FAT/DAT archives or unrelated user mods.
