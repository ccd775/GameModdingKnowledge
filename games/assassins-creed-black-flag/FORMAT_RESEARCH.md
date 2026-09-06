# Research and tool provenance

Updated: 2026-08-09

This document records conclusions backed by the current machine-generated
reports. Historical notes that described the reference Forge as LZO1X, or
Forge Injector as the final resource compiler, are superseded by the measured
contracts below.

## Reference and immutable inputs

- Reference publication: Carl Johnson Playable 1.0 by Kamzik123:
  <https://www.nexusmods.com/assassinscreedblackflagresynced/mods/121>
- `karin_D7-E4-04.blend`: 164,833,622 bytes, SHA-256
  `B2C0A711853060C50E0C8CF7BC1935A16794A90FA41060E003CFBF272C920920`.
- `karin_D7-E4-04.fbx`: 146,710,396 bytes, SHA-256
  `354D0F7B58BA339876E53AEB6E8F990C71EE62D20D328FB1A5FC20C100D3EC49`.
- Reference `DataPC_boot_patch_02.forge`: 1,507,328 bytes, SHA-256
  `F3CFD139FFFA82BD2A0BA04F897690D4515229EE161D8E8B8C7B80E49C479637`.

The source checkpoint and reference extraction operate on copies under
`work/`; none of the three immutable inputs has been edited in place.

## Pinned game build

The current authority is the Steam installation at
`<steam-library>\steamapps\common\Assassin's Creed Black Flag Resynced`.
The current BuildID `24424450` authority was revalidated during the 1.5.3
transaction on 2026-08-08. The older BuildID `24326718` fingerprints are
historical and must not be used for current deployment decisions.

| Item | Size | SHA-256 |
|---|---:|---|
| Steam AppID / BuildID / TargetBuildID | `3751950` / `24424450` / `24424450` | n/a |
| `ACBlackFlag.exe` | 478,845,280 | `8D52238155C9491F329C0B78AF2D00EE67AB5E03946EEA83E12B061B64B23140` |
| `DataPC_boot.forge` | 25,640,534,016 | `144D947BD4B84709B891837C1A49893062AA9B79E2CECAF66C15FD884BC70A00` |
| `DataPC_boot_patch_01.forge` | 1,915,453,440 | `D2C0A87FD663C154E837350E8B93A00DF847F6659DC19D4E96BACD84041620D7` |

Steam updated the installation during this project. Re-run the current
fail-closed installer preflight and require these BuildID/static-file hashes,
the exact expected boot state, and no active `patch_02` before any further
installation or rollback.

## Toolchain decision

### Final container authority

The final Forge path is the project-local, fail-closed implementation:

- `scripts/extract_forge_v50_bms.py` parses and validates the v50 container,
  both BMS framing modes, resource envelopes, sizes, checksums, and asset
  boundaries.
- `scripts/rebuild_forge_v50_patch.py` preserves outer object IDs, order,
  resource types, metadata suffixes, and all five untyped sections while
  replacing explicitly named decoded resources only.
- Every release candidate must be independently re-extracted and compared to
  the requested replacement hashes. A successful write is never accepted on
  its own.

### Third-party tools and boundaries

- Blender 4.2.23 LTS, build `d0cbe84903e8`, executable SHA-256
  `E2B4D2CCBFB7A33B0BB1ABB1B7A08EBCA3B5A745E73960D5A2DECC0B9579B715`.
  It is the model preparation, preview, and pose-QA host.
- AnvilToolkit 1.3.6 archive SHA-256
  `0A96A0677E8462A987D88482E2CD8AEF0B8053F5D8C34673AE20E18908E9B505`.
  Its `BlackFlagResynced` Forge deserialize branch is empty, it has no v50
  serializer, and BFR is absent from Mesh, Skeleton, and TextureMap support
  lists. A forced Shadows probe misread 268,761,753 directory slots and failed
  at EOF. It is used only for names, format comparison, glTF preset research,
  and its trusted bundled codec DLLs; it is not a BFR compiler.
- Forge Injector v4-labelled archive SHA-256
  `CB0BECED3F2D83D02D5FA47F494B307D52453549FD8DABF35CBE8BA3AAE4D154`;
  executable SHA-256
  `6D7318B2C66967B86B2EE5F4DFFDC6146EE44D2C728EA512E3A1760C7DC75D1F`.
  It does not convert FBX/GLB/PNG into BFR resources. Its GUI also rejects the
  reference patch's second default-mode BMS as an invalid zero chunk count.
  It is retained as an external behavior comparison, not used as the final
  extractor, resource compiler, or repacker.
- DirectXTex `texconv` 2026.5.8.1 (Microsoft Authenticode valid), SHA-256
  `DCFDEC10244E02CF5037FBA089C55FB7E1326B1C8181742D77D15FA5CB5EEF06`.
- Trusted Oodle libraries are only the AnvilToolkit-bundled v9 and v7 DLLs,
  SHA-256 `D484C81158B4E6EDB593DE75B1573992E304B008C133C62E7D383EACFD3DA995`
  and `02FBF4C1E39DC3CCAA616226F0B6237AD7BCE9FDD8FE29D77BC7ECD9C37C738E`.
  Neither is required by this reference patch. The separately downloaded
  `tools/codec/oo2core-9` binary is untrusted and must not be loaded.

## Measured Forge v50 contract

The reference patch has nine outer entries: four typed resource bundles and
five untyped metadata/index entries. Eight reachable BMS blocks contain 15
decoded assets.

- The stored compression field is `4`, not `8`.
- Compressed records are raw LZ4 blocks. No LZO1X or Oodle chunk occurs in the
  reference patch.
- BMS0 uses TOC mode; BMS1 uses default mode without a TOC chunk-count table.
- The extractor passes 346/346 checks and writes all 15 assets.
- Default-mode compressed records are validated as flag, stored size, decoded
  size, Adler-32 (seed 0), and raw LZ4 payload.

An unchanged decoded-resource rebuild produces
`reference_identity_reencoded.forge`, still 1,507,328 bytes, SHA-256
`44A9C1EFDCC35AA9B9853A2D4EFBC07D0A8B806F2F25BB03D74BD3A3D7D9ABAA`.
Its whole-file hash differs because the typed entries are deterministically
recompressed, but all decoded resources are byte-identical, every untyped
entry is copied exactly, and independent re-extraction passes 322/322 checks.
This is the validated identity baseline for later replacement builds.

## Resource contracts

### Meshes

The reference replaces two Mesh resources sharing material
`0x000000BAC7CA10D9` and an identical 759-entry MeshBone table.

| Resource | Reference vertices / triangles | Used joints |
|---|---:|---:|
| `0x00000081786E922F` | 1,041 / 1,384 | 165 |
| `0x0000009611D6CEAE` | 627 / 948 | 382 |

Format 1 uses 16/12/24-byte static, dynamic, and influence streams, up to
eight influences, unsigned 16-bit global joint indices, and unsigned 16-bit
triangle indices. Parse-to-serialize identity and reference GLB-to-Mesh
identity both pass. The legacy 42-bone palette assumption is invalid here.

The accepted Karin outputs contain 31,548 vertices / 48,030 triangles and
27,820 vertices / 40,482 triangles. The manually accepted
`rigid_hybrid_pivots` authoring GLB has SHA-256
`3E71316DFD7807961140DDA17A39621561F647CB2045BBBA8A809DDACE89D6A4`.
PBR front/three-quarter/back and three pose-stress views pass; strict
parse-to-serialize and the 326-current/433-template MeshBone policy also pass.

BFR uses the opposite triangle front-face convention from the canonical glTF.
The two reference Meshes have mean accumulated geometric-normal dot products of
`-0.90724` and `-0.92922`, while the original Karin compilations measured
`+0.93586` and `+0.91670`. The deterministic derivative
`work/model_pipeline/candidates/karin_target_bound_reversed_winding.glb`,
SHA-256
`ADCF4BAD9A0A48241BFED8010D68123FDED11AE918C86D09A51996D0EA7D6959`,
reverses only triangle index order. Its compiled Mesh SHA-256 values are
`6176833723256B7B57558629EF95235C634AEBC0E28B146A711D114A3E9B4373`
and `5F4A00041D0A74B6F3AAF0D619773A262AE105E1DF4C4AEACDFEFE83F02E7D65`.
Candidate N's solid-magenta runtime control proved that this winding change,
not Material binding, removes the black-surface failure.

### Current-build Skeleton authority

The authoritative Skeleton is patch_01 resource `0x000002242390EC10`,
SHA-256
`804993637C9D57F0F385B20011934D80B6742F2A3016838CCD7EF47539BFF9E6`.
All four Duncan/Walpole top BuildTables resolve through selection table
`0x0000020134EADF32` to this resource. It matches 326/326 current target CRCs
inside the 759-entry reference MeshBone table; position RMS is
`3.75267399e-05`, and the next full-overlap candidate is 90.55 times worse.

The Skeleton resource must remain unchanged. Final Meshes preserve all 759
slots and all metadata, copy current Skeleton inverse-bind matrices into the
326 CRC-matched slots, and preserve the remaining 433 template matrices
byte-for-byte. The authority validator currently passes every one of those
checks.

### Source preparation, atlas, and textures

The prepared source has ten meshes, 47,052 Blender vertices, 88,512 triangles,
and a 243-bone source armature. Four selected appearance shape keys are baked,
269,199 zero-weight assignments are removed, and weights are normalized. The
prepared source render is pixel-identical to the original in three views.

The authoring master is one 4096x4096, 4x4 atlas with 1,024-pixel tiles,
24-pixel gutters, and 11 used material tiles. Candidate R downsamples the
diffuse and normal runtime payloads to 2048x2048 with complete 12-mip chains. A
source-atlas control retains all 88,512 triangles and changes only UV0/UV1. It
proves the required origin conversion:

`v_offset_gltf = 1 - bottom_offset - scale`

The earlier bottom-origin offset sampled wrong rows, including the unused white
tile. The canonical GLB uses the corrected top-origin transform and its final
PBR renders passed manual acceptance. The packaged normal is DirectX `-Y` and
has exactly one green-channel inversion; Blender QA inverts once back to
OpenGL `+Y` before its Normal Map node. The signed DDS encoder performs no
additional green inversion.

Candidate R's three-resource surface bundle passes independent descriptor
parsing, D3D12 footprint reconstruction, zero-padding checks, all 29 mip
comparisons, exact DDS round trips, and signed-channel semantic decoding:

| Role / resource | Format | Size | SHA-256 |
|---|---|---:|---|
| Diffuse `0x000000BAC7CA10DA` | DXGI 78, BC3 sRGB, 2048, 12 mips | 5,596,424 | `88442541C9EB76C6D91CDF1D59EE1DDD1C8D21F11FEF890E2D7663D41ADD8AA5` |
| Flat normal `0x000000BAC7CA10DB` | DXGI 84, `BC5_SNORM`, 2048, 12 mips | 5,596,424 | `C1FD3691AECC64C4F9BE468DC68AC88BF7D8C0C5C3DFE9CFE4D47A0BBF7B4115` |
| Reference specular `0x000000BAC7CA10DC` | DXGI 84, `BC5_SNORM`, 16, 5 mips | 3,336 | `798661D09E4EE1A8F624EAD9560D9B08CF9ECB37AB27AB8A6236410CE1305098` |

Diffuse PNG values are already sRGB. The rejected conversion omitted
`texconv -srgbi` and double-applied the transfer function; the accepted build
uses `-f BC3_UNORM_SRGB -srgbi -srgbo -dx10`. Normal/specular use BFR
pixel-format index 10, gamma 0, and the signed DXGI 84 `BC5_SNORM` contract;
the unsigned DXGI 83 interpretation is rejected.
`build_bfr_signed_bc5_dds.py` converts normal X/Y to signed floats, uses an
`R32G32_FLOAT` intermediate, and emits explicit DX10 BC5 signed DDS.

Each 2048 replacement consumes 21,860 256-byte pages. The 4096 full-mip probe
consumes 87,396 pages and remains runtime-unverified, so 4096 is retained only
as an authoring master. Candidate P used the full authored normal and remained
strongly mottled; Candidate Q reduced tangent-space XY strength to 0.25 and
remained visibly mottled even with the reference specular. Candidate R sets
normal strength to 0.0. This neutralizes a source-normal/BFR-tangent-basis
incompatibility while retaining geometric lighting from the Mesh vertex
normals.

### Material and alpha

`Karin_Alpha` contains authored soft coverage; at threshold 128 only about
2.19% of its rasterized base-mip texels pass. Current-game Material evidence
identifies byte `0x75` as `flags[28] = AlphaTestEnabled`, while byte `0x76`
remains `TwoSided`. Eighteen same-game Materials use the Copy / display-mode 1
/ alpha-test combination.

The alpha-test Material A/B/C variants passed parse-to-serialize and narrow
byte-whitelist checks, but they were not accepted by the runtime candidate
sequence. Candidate R preserves reference Material `0x000000BAC7CA10D9`,
SHA-256
`D3D093F430E0BE2140B8835F45C0FBC55756A4E32F41E2F6305DD3D44D35F9D2`,
byte-for-byte. Its reference specular and all three Material TextureMap IDs are
also unchanged. Authored alpha-test behavior, soft alpha failure, depth,
shadows, and sorting remain a possible future experiment, not part of the
private 1.0 release.

## Runtime evidence and current boundary

The identity-reencoded Forge launched on BuildID `24326718` and reached a
playable ship save without a container-level crash. That validates the identity
repack path, not the Karin resources.

The runtime diagnosis proceeded through controlled candidates. Candidate J
proved that both Meshes resolve directly through the reference Material to the
three TextureMaps. Candidate N combined reversed winding with solid magenta and
rendered broadly solid, proving the winding correction. Candidate O combined
reversed winding with a 512 correct-sRGB diffuse control and rendered in Animus,
gameplay, and motion. Candidate P restored 2048 authored surface maps but showed
strong mottling. Candidate Q retained reference specular and reduced authored
normal strength to 0.25, yet remained visibly mottled. Candidate R retained the
reference specular/Material and used a flat 0.0-strength normal; its surface is
clean.

Candidate R Forge is 3,833,856 bytes, SHA-256
`52355DAC381F1882B3349BDC1E4A40962083265AFE6B79377DE2BD80B7964113`.
It changes four decoded resources: two reversed-winding Meshes, the 2048
correct-sRGB diffuse, and the 2048 flat `BC5_SNORM` normal. Rebuild is `PASS`,
and independent extraction passed 725/725 checks across 8 BMS blocks and 15
assets. The v2 strict payload validator passed 3659/3659 and bound the package
and rebuild report to exactly 4 changed resources, 2 explicitly preserved
targets, and 11 byte-identical decoded resources. It also rehashed 58 source
inputs and proved they remained unchanged.

`candidate_r_animus_ready_02.png` and `candidate_r_gameplay_initial.png` prove
clean Animus and night-gameplay surfaces. `candidate_r_gameplay_after_walk.png`,
`candidate_r_sync_motion_01.png`, and `candidate_r_jump_motion.png` cover back,
walk, synchronization, and jump motion without visible instability.
`candidate_r_camera_arrow_test.png` adds brighter camera rotation, and
`candidate_r_restart_gameplay_loaded.png` proves restart/reload to gameplay.
The release manifest records 8 `OBSERVED_PASS` checks from these captures.

The user then manually closed the session and explicitly stopped further
Candidate R testing. Nine scopes remain `NOT_TESTED`: close front/face,
sustained run/idle, parkour/climb, combat, swimming, ship/rain/wetness,
cutscenes/close facial animation, distance/LOD, and the broad lighting/shadow/
wet-surface matrix. These are not pass claims. They are accepted residual risks
for the authorized private release and remain required for any public or
comprehensive runtime validation.

## Private release and final machine validation

`scripts/build_private_release.py` generated
`dist/Karin_Playable_1.0/` with exactly five files and the deterministic archive
`dist/Karin_Playable_1.0.zip`. Read-only `--verify` reports `VERIFY PASS`. The
archive SHA-256 is
`6F6B72BC6B0DBB0D05CC9B6CA47CC61C9E30CD37A6F32C698D350E013FB3A36C`;
the contained Forge SHA-256 is
`52355DAC381F1882B3349BDC1E4A40962083265AFE6B79377DE2BD80B7964113`.
The release manifest status is `STRUCTURAL_PASS_RUNTIME_PARTIAL`, with 8
`OBSERVED_PASS` and 9 `NOT_TESTED`. Its validation inputs pin strict payload
3659/3659, extraction 725/725, BuildID `24326718`, and game inventory 18/18.

The final machine manifest schema is `karin-bfr-final-model-pipeline/v2`. It
reports status `PASS_CANDIDATE_R_MACHINE_VALIDATION` and packaging status
`PRIVATE_RELEASE_READY_WITH_DOCUMENTED_RUNTIME_SCOPE`. At that historical
checkpoint it also verified that the then-installed
`<steam-library>\steamapps\common\Assassin's Creed Black Flag Resynced\DataPC_boot_patch_02.forge`
is 3,833,856 bytes and has Candidate R SHA-256
`52355DAC381F1882B3349BDC1E4A40962083265AFE6B79377DE2BD80B7964113`.
This is a private personal-use release with explicit runtime limits, not a full
gameplay-certification claim.

## Candidate V material-quality research

Candidate V uses the historical Candidate U SockDiffuse (`68D09380...F09465`) as
its immutable baseline. Earlier Candidate U-labeled exploratory directories are
retained as provenance; all newly generated spec/gloss and WaterFlow Forges are
rebased on SockDiffuse so they do not revert its localized diffuse correction.

The native Duncan audit parsed three Materials with 101 DynamicProperties each,
five TextureSets/slot groups, native streaming TextureMaps, and the relevant
MaterialTemplate dependency. All 18 pinned source resources round-trip
byte-identically. The shader-facing selectors are AlbedoMap, NormalMap,
ZoneMap, and GrungeMap. Structural slot 4 is therefore not an emitted-light
binding. Reconstructed slot-4 images are categorical RGB masks.

Original Duncan high LOD provides the multi-material authority: three local
index partitions with cumulative vertex/index starts and parallel primitive,
instancing, Material, and UV-density arrays. The compact writer/parser now
implements that contract. Final self-tests prove two distinct Material IDs,
byte-identical strict round-trip, invalid-local-index rejection, and 32
primitives totaling 33,312 vertices while each primitive remains below the
signed-Int16 limit. Legacy single-primitive identity remains exact. This proves
the Mesh serialization path, not Forge allocation of new Material resources.

Six spec-map and four `Layer0_SpecGloss` probes were built from SockDiffuse.
Each changes exactly one declared resource, re-extracts at 725/725, and passes
strict payload validation. R/G semantics and scalar response remain runtime
questions; semantic RG and GR atlases are mutually exclusive.

The normal investigation mapped 59,368 source/target vertices and showed BFR
frame pack/reparse mean dot near 0.99999 with zero tangent handedness mismatch.
The material failure appears after UV quantization: 1/2048 UV storage moves
coordinates by at most 0.000244140625 but changes Mikk tangents substantially
on small islands. Hair and ClothB stored-vs-quantized-Mikk p05 dot falls to
about -0.488 and 0.637. The Candidate V mesh therefore quantizes UV first,
recomputes MikkTSpace, and splits discontinuities. Its compiled Meshes have
31,910 and 27,886 vertices and pass strict Mesh/MeshBone validation.

The authored normal was reprojected between the transported and final TBNs.
The bake covers 620,082 triangle samples and 566,034 unique texels; overlap
agreement mean is 0.9999956824 and no sample has negative Z before the positive
hemisphere policy. +Y and -Y BC5_SNORM variants, five constant-axis resources,
and eight SockDiffuse-based Forge probes pass full-mip TextureMap and strict
Forge validation. Runtime must still select the green sign.

Renderer strings prove emissive/GBuffer and global wetness capability. The
bounded local scan covers 202 extracted asset occurrences, five fully parsed
Materials, and one native MaterialTemplate. It finds no feature-named parsed
DynamicProperty or TextureSelector. The template contains two raw
`LightingEmissive` CRC occurrences; without a template/operator parser these
remain leads. Two isolated `NG_WaterFlow_Intensity` probes exist only for the
compact Material and do not prove global wetness behavior.

The aggregate machine gate is
`work/candidate_v_lab/candidate_v_material_lab_handoff.json`, status
`PASS_OFFLINE_LAB_READY_RUNTIME_UNTESTED`. No integrated Candidate V Forge was
built or installed.

## Resynced native mouth/teeth suppression and Candidate AJ

The legacy Black Flag file list identifies
`CHR_Shared_MouthTeethEye_SELECTOR` BuildTable `0x0000000104E53943`, which
resolves to old `CHR_Shared_EyeTeeth` LODSelector `0x000000003EE9A3C0` and
`CHR_Shared_Teeth_Clean` Material `0x00000006C66E6789`. Those IDs do not occur
in the Resynced boot archive and are naming/relationship evidence only.

Scanning every non-empty `VisualPropertyNodeSolver` in the reference mod's
injected BuildTables and extracting all referenced Resynced LODSelectors found
the remapped mouth/teeth selector `0x00000244130CE35A`. Its five LOD Meshes are:

- external `0x00000244130CE35B` and `0x0000024D485A75E8`;
- embedded `0x0000024D485A75F6`, `0x0000024D485A7604`, and
  `0x0000024D485A7612`.

Strict geometry parsing places every vertex in the mouth volume, with one
weighted bone and multiple upper/lower tooth-shaped connected components.
Multiview previews contain no spheres or eye-height geometry. The shared
Material is `0x0000020D6679DD8D`; its TextureSet is
`0x0000020E8A7D3ABD`. A separately extracted bilateral eye candidate remains
outside this chain. The old combined name therefore must not be used to infer
that the Resynced selector contains eyes.

BuildTable `0x00000330557EC362` contains 32 columns and exactly one occurrence
of the selector. It is the `TargetGraphicObject` UInt64 of the final
`VisualPropertyNodeSolver`, at file offset `0x1FFB`. AnvilToolkit source proves
the field is a raw ClassID: mode precedes it, byte `0x1FFA` is reserved, and a
Mask class follows it. Zero is a serializable empty ClassID and is not a
wildcard. Candidate AJ preserves `0x1FFA=00` and changes only the following
eight-byte target window to zero.

The source BuildTable is 9,047 bytes, SHA-256
`BF4313A35AF1473D1A60278C7C2FE21C08FD138603D657F348D485B4A74E04F8`;
the patched BuildTable is the same size with SHA-256
`2797F19426104AB061DB024ABABFE402AACA4D3DF08E7301C8A53894A3C8DA03`.
Candidate AJ is Candidate AI plus this one decoded-resource delta. Its Forge is
4,096,000 bytes, SHA-256
`7F7D3D2EAB98F00F60B784074598A5A88249443B781F34FFC3BB78302EAE2E10`.
Independent extraction passes 725/725; the AJ delta/readback validator passes
62/62. It was historically installed and distributed as Karin Playable 1.5.
Later runtime evidence showed that the null target did not hide the teeth, and
BuildID `24424450` made the old Forge incompatible; Candidate AK supersedes it.

Primary evidence for this stage:

- `work/research/v15_native_mouth_catalog/blackflag_mouth_catalog.json`;
- `work/research/v15_selector_material_match/resynced_eye_teeth_selector_report.md`;
- `work/research/v15_native_mesh_preview/native_mouth_suppression_evidence.md`;
- `work/research/v15_teeth_locator/native_mouth_locator.md`;
- `work/research/v15_teeth_locator/teeth_null_patch_contract.json`;
- `work/reports/candidate_aj_v15/teeth_suppression_patch.json`;
- `work/reports/candidate_aj_v15/candidate_aj_v15_validation.json`;
- `work/reports/candidate_aj_v15/candidate_aj_v15_runtime_release_manifest.json`;
- `work/runtime_backups/2026-07-26_pre_candidate_aj_v15_4CABB898/INSTALLATION_RECORD.json`;
- `dist/Karin_Playable_1.5/release_manifest.json`.

## Primary evidence

- `work/reports/reference_forge_v50_bms_extraction.json`
- `work/reports/forge_v50_patch_identity_rebuild.json`
- `work/reports/forge_v50_patch_identity_reextract.json`
- `work/reports/game_install_inventory.json`
- `work/reports/bfr_target_skeleton_match.json`
- `work/model_pipeline/candidates/compiled_reversed_winding/meshbone_authority_validation.json`
- `work/reports/source_atlas_control_contract.json`
- `work/reports/diagnostics/candidate_k_binding_followup.md`
- `work/reports/diagnostics/candidate_k_mesh_uv_followup.md`
- `work/reports/diagnostics/diffuse_contract_followup.md`
- `work/model_pipeline/candidates/karin_target_bound_reversed_winding_contract.json`
- `work/model_pipeline/compiled_textures_atlas2048_flatnormal_refspec/bfr_texture_writer_contract.json`
- `work/model_pipeline/compiled_textures_atlas2048_flatnormal_refspec/bfr_compiled_texture_verification.json`
- `work/model_pipeline/compiled_material/bfr_alpha_test_material_candidates.json`
- `work/reports/final_model_pipeline_manifest.json`
- `work/reports/final_model_pipeline_manifest.md`
- `work/reports/karin_candidate_q_forge_rebuild.json`
- `work/reports/karin_candidate_r_forge_rebuild.json`
- `work/reports/karin_candidate_r_extraction.json`
- `work/reports/candidate_r_final_forge_payload_validation.json`
- `work/reports/candidate_r_final_forge_payload_validation.md`
- `work/reports/runtime/candidate_r_animus_ready_02.png`
- `work/reports/runtime/candidate_r_gameplay_initial.png`
- `work/reports/runtime/candidate_r_gameplay_after_walk.png`
- `work/reports/runtime/candidate_r_sync_motion_01.png`
- `work/reports/runtime/candidate_r_jump_motion.png`
- `work/reports/runtime/candidate_r_camera_arrow_test.png`
- `work/reports/runtime/candidate_r_restart_gameplay_loaded.png`
- `work/reports/runtime/runtime_navigation_handoff.md`
- `scripts/build_private_release.py`
- `dist/Karin_Playable_1.0/release_manifest.json`
- `dist/Karin_Playable_1.0/RUNTIME_SCOPE.md`
- `dist/Karin_Playable_1.0/INSTALL_AND_ROLLBACK.md`
- `dist/Karin_Playable_1.0/SHA256SUMS.txt`
- `dist/Karin_Playable_1.0.zip`
- `work/candidate_u_native_materials/native_duncan_material_contract.json`
- `work/candidate_u_native_material_contract/native_texture_set_contract.json`
- `work/candidate_u_native_emissive/native_emissive_reconstruction.json`
- `work/mesh_multimaterial_selftest/final_verification/multimaterial_selftest.json`
- `work/candidate_v_material_response/candidate_v_material_response_probes.json`
- `work/candidate_u_normals/SUMMARY.md`
- `work/candidate_u_normals/forge_matrix/forge_probe_matrix.json`
- `work/candidate_v_surface_features/candidate_v_waterflow_probes.json`
- `work/candidate_v_surface_features/local_template_discovery.json`
- `work/candidate_u_surface_features/surface_feature_capability_scan/surface_feature_capability_scan.json`
- `work/candidate_v_lab/candidate_v_material_lab_handoff.json`
- `docs/CANDIDATE_V_MATERIAL_LAB.md`

## Build 24424450 and Candidate AK findings

The August update changed the executable and patch_01 but not boot:

- BuildID `24424450`, depot manifest `4397710407098141927`;
- `ACBlackFlag.exe` is 478,845,280 bytes, SHA-256
  `8D52238155C9491F329C0B78AF2D00EE67AB5E03946EEA83E12B061B64B23140`;
- `DataPC_boot_patch_01.forge` is 1,915,453,440 bytes, SHA-256
  `D2C0A87FD663C154E837350E8B93A00DF847F6659DC19D4E96BACD84041620D7`;
- `DataPC_boot.forge` remains byte-identical at
  `144D947BD4B84709B891837C1A49893062AA9B79E2CECAF66C15FD884BC70A00`.

The old AJ Forge (`7F7D3D2E...E2E10`) repeatedly exited with code 3 on the
new build; with it disabled, the game launched normally. More importantly,
runtime observation proved that zeroing the BuildTable target did not hide the
native teeth. Candidate AK therefore restores Candidate AI's original
BuildTable (`BF4313A3...E04F8`) and does not rely on an empty selector target.

The verified native mouth chain has one selector and five pure-teeth Mesh LODs.
Forge top-level TOC injection is append-and-repoint by selected resource ID, so
embedded-child collision alone is not a sufficient override guarantee.
Candidate AK mirrors the native topology as three explicit top-level entries:
the selector chain with three embedded Meshes and the two external Mesh chains.
The selector class payload is exact. Only each Mesh's clustered index-buffer
window changes, and all 1,212 triangles become `(a,a,a)`. The eye selector and
shared mouth Material are not modified.

The pistol-capacity chest exposure is a skinning-clearance problem rather than
a texture issue. The upper chest garment is approximately 83.39% Spine2 and
16.00% Neck while the hidden skin core was approximately 98.89% Spine2 and
0.94% Neck; local static clearance can be as low as 0.303 mm. Candidate AK
aligns only the covered front Body weights and applies a topology-safe inward
relief. The final accepted maximum is 1.797855563 mm, with 462 changed position
vertices, 176 changed weight vertices, no flipped triangles, and ClothA exact.

Final structural evidence:

- `work/reports/candidate_ak_v151/candidate_ak_v151_release_validation.json`:
  321 PASS, one EXPECTED_DEGENERATE, zero FAIL, 322 total;
- `work/reports/candidate_ak_v151/candidate_ak_final_extraction.json`:
  878/878, 12 entries, 21 assets;
- final Forge: `185FDD4A0957A7DC2A19B59577CA688B09D81FFD42A161A40D284A9B48BF9160`;
- deterministic 1.5.1 ZIP:
  `11EB2C204C20A758F6868B72E25DE863498061B7922246DA9C7D5365CFA35332`.

No automated runtime test is evidence for Candidate AK. Runtime acceptance is
reserved for the user's manual test of teeth LODs, eyes, pistol-upgrade chest
poses, and inherited geometry.

## Candidate AL current-boot container findings

The user's later manual test showed that Candidate AK's structurally valid
standalone `patch_02` also crashes on BuildID `24424450`. This disproves the
narrow hypothesis that AJ's null BuildTable alone caused the new-build crash.
The remaining shared factor is the old reference-derived standalone container
path, so Candidate AL uses the current boot's existing TOC rows instead.

Selected extraction of the current boot proves that the four outfit rows and
three native mouth rows use BMS version 3, field 8, 262144-byte chunks, and TOC
mode for both BMS streams. Compressor calibration is exact: oo2core v9,
compressor 9 (Mermaid), level 7 reproduces all seven original stored payload
chunks byte-for-byte. Kraken/Normal produces valid cross-decodable data but
does not reproduce current native bytes and is not accepted for AL.

Candidate AL stage 1 retains the four Candidate AK decoded bundle indexes,
variable opaque suffixes, asset ordering, and payloads byte-for-byte. Only BMS
storage changes. Its repack report passes 1338/1338; output hashes are:

- `0x24EB3F06DB8`: `CF47D8CE8E0CF655B5195C0B75AB55827213ABA9F074C819F199961B7EC67871`;
- `0x24EB3F01215`: `73ECB260A1950A838311512962F699A6721341073A9581008FD4D329BD88A5D9`;
- `0x24EB3F011DF`: `8F458F283CE39B8E58378CBD0F23728475C4E6E5B7D1698240454C741F587413`;
- `0x24EB3F011FB`: `1F181D11C48C070F352EC68658AAE7B5F00F8742B53B61F3829D8EEBA32A43FC`.

The transaction appends 1,874,517 bytes after the original archive and changes
only offset/size in the four existing TOC rows. Installed boot size/hash are
25,642,408,533 and
`479FCB29C92163A8B830E4294F317FB57B46D76D8766B85FC2C4E11397E80580`.
The full original backup remains exact at `144D947B...70A00`. Stage 1 excludes
all native teeth overrides so user-side startup can isolate the container path.
No automated game launch or test was performed.

## Candidate AM chest-v3 and combined redirect findings

The earlier bounded chest relief excluded already penetrating `gap <= 0`
vertices and gave the underband only sub-millimetre effective retreat. The
opaque cups cover deep Body surfaces by roughly 10-20 mm, so forcing the full
breast surface inward is not a viable deformation fix. Candidate AM instead
degenerates the 1,357 Body triangles whose centroids project at least 6 mm
inside either cup or the underband. A deterministic bipartite keeper assignment
retains all 553 vertices referenced only by those triangles, preserving the
complete 31,548-vertex compiler domain while all selected triangles remain
degenerate.

The still-active boundary is handled separately: 129 position vertices receive
at most 6 mm retreat, 138 Body weight vertices are matched to their covering
garment, and 255 non-seam underband vertices are stabilized. The 55
cup-underband seam vertices preserve position, joint, and weight bytes exactly.
Five Spine2 pitch poses pass the recorded shallow-crossing gates. The final
compiled hashes are Body `F291A428...9EEA4` and ClothA
`77E90EFE...AF2B2`, both with zero dropped vertices.

The current-boot chest-v3 outfit entry is 1,872,845 bytes / SHA-256
`98EC6FE8707DD39496658D9A5F21E52BAC80388CC4D8F1150F6819BFD2F68D09`.
The three mouth entries are 4,967, 7,914, and 4,495 bytes with hashes
`685C26F0...83A0347`, `D6299E36...27F3A10`, and
`BDF466FA...3782D40`. They mirror the native selector topology and preserve the
selector class payload while all five teeth-only Mesh LODs contain 1,212
degenerate triangles. The shared mouth Material and eye selector are untouched.

Candidate AM appends these four entries to exact Candidate AL Stage 1 and
repoints the primary outfit row plus the three existing mouth rows. Python and
independent PowerShell streaming implementations both compute the same virtual
archive: 25,644,298,754 bytes / SHA-256
`1DAC6CB15731EDF877E762430B7257A36117602446B1E23E522BFB79CDEC9C28`.
Installed readback reproduces that value. The immutable original full boot
backup remains `144D947B...70A00`; Candidate AL Stage 1 remains the exact
four-row rollback at `479FCB29...E80580`. No automated game test was performed.

## Candidate AN live oral chains, nipple components, and shadow policy

The user-side 1.5.3 screenshots disproved two remaining assumptions. First,
the previously redirected `0x244130CE35A` chain is teeth geometry but is not
the active Edward facial variant seen in the reported close-up. Current-boot
incoming-reference and Mesh audits identify four parallel oral selectors:

- `0x00000245C69AAABE`;
- `0x00000245C69AAA1A`;
- `0x00000245C69AAADA`;
- `0x00000245C69AAB11`.

Each selector owns one embedded low LOD and references external high and
middle LOD Meshes. Per chain, these contain 640, 298, and 152 triangles;
Candidate AN therefore covers 12 Meshes and 4,360 triangles. Every Mesh uses
the shared oral Material `0x0000020D6679DD8D` and oral bounds. The neighboring
head/face selector `0x245C69AAA0C` is explicitly excluded. The final entries
retain each native bundle index, selector, material references, envelope,
bounds, counts, and Oodle Mermaid/level-7 profile; only clustered index-buffer
windows change to `(a,a,a)`.

Second, the visible nipples are not residual cup-boundary triangles. They are
two independent Body connected components, each 311 vertices / 589 triangles,
outside the chest-v3 mask. Chest-v4 degenerates exactly those 1,178 triangles
and uses a deterministic 622-triangle keeper assignment so the complete
31,548-vertex compiler domain remains referenced. No positions, weights, UVs,
normals, tangents, colors, or non-nipple indices change at this stage.

The earlier Material flag-14 experiment was visually inert, but its historical
assignment to `IsAtlasMaterial` was incorrect. Build 24424450 native descriptor
access values prove `flag[14]` is `IsExcludedFromScreenSpaceShadows` and
`flag[15]` is `IsAtlasMaterial`. Candidate X left the Material opaque-caster and
Mesh caster paths enabled; Candidate AN changed only the compact Mesh
shadow-caster field. Both Body and ClothA serialize `shadow_caster=false`; the
outfit entry decodes to Body
`47805CD7AF3010329707B985DB9DA87371E66CABACCF34B05A60D01B8A628891`
and ClothA
`77E90EFEE673B4544B269BACFC26EB5D9F903AC678266F4E156A620E9ADAF2B2`.
This should remove conventional shadow-map self-shadow between hair, face,
skin, and clothing, but can also reduce the character's ground shadow.

Independent offline validation reports 404/404 custom checks and 1,028/1,028
Oodle decode checks. The 13-entry transaction appends 1,980,025 bytes to exact
Candidate AM 1.5.3 and produces 25,646,278,779 bytes / SHA-256
`1369AE0E5B86880F33E5AB560A606801985501DF838F3681B61805E0B3F3DCE1`.
The installed readback matches. No automated game launch or test was
performed; all visual conclusions remain pending the user's manual runtime
test.

## Candidate AO full dynamic head and combined shadow findings

The user-side 1.5.4 result proves that the four oral selectors above are still
not the sole rendered source. Duncan's embedded visual BuildTable
`0x330557EC362` references both those oral chains and the complete Edward
dynamic-head selector `0x245C69AAA0C`. Its four embedded Mesh LODs cover the
full native head, carry facial bones, and remain active during speech. This is
the only observed chain consistent with animated Edward teeth surviving every
teeth-only redirect.

Candidate AO preserves the full-head selector byte-for-byte and degenerates
only the clustered index windows of its four Meshes: 30,989, 13,041, 6,158,
and 2,895 triangles, 53,083 total. A full scan of Build 24424450 patch_01 finds
no top-level or embedded target-ID collision. The stored replacement is
1,952,061 bytes / `A0C26B47...AEF655D` and passes 713/713 plus 120/120
independent redecode checks.

The current executable's Material descriptor routine at raw `0x036F7720`
pairs field CRCs with member-bit access immediates. Anchoring member bit 14 to
compact flag 0 yields `ShadowCasterOpaque` at flag 12 / `0x65`,
`IsExcludedFromScreenSpaceShadows` at flag 14 / `0x67`, and
`IsAtlasMaterial` at flag 15 / `0x68`. AnvilToolkit 1.3.6 cannot contradict
this map because its Material supported-game list excludes Black Flag
Resynced. AO changes exactly `0x65: 01 -> 00` and `0x67: 00 -> 01`, retaining
AN's Body/Cloth Mesh caster disable. The combined outfit entry is 1,871,812
bytes / `C2E4E47F...A6A8C02B` and passes 1,374/1,374.

Independent validation passes 116/116. The two-entry transaction appends
3,823,873 bytes to exact AN 1.5.4, modifies only two TOC offset/size fields,
and installs 25,650,102,652 bytes / SHA-256
`916594BA6AB3F65BE5EFBFDF85A994509AFF4357F9663A01A0C344BE20906035`.
Installation and full installed readback pass. No automated game launch or
visual test was performed; teeth removal, self-shadow reduction, and possible
loss of the conventional character ground shadow require the user's manual
runtime judgment.
