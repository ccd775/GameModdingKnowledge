# Black Flag Resynced character replacement SOP

Last updated: 2026-08-08

## Goal

Convert the supplied Karin character into a complete private replacement for
Duncan's outfit in `Assassin's Creed Black Flag Resynced`, using the Carl
Johnson mod as the structural reference. Preserve a repeatable path from source
files to a version-matched standalone patch or a transactional boot-Forge
append-and-repoint deployment.

## Non-negotiable rules

1. Never edit the supplied `.blend`, `.fbx`, or reference-mod files in place.
2. Record SHA-256 hashes before and after every binary conversion stage.
3. Keep one canonical Blender working file under `work/blender/` and make a
   checkpoint copy before destructive mesh, UV, material, or armature changes.
4. Treat a successful pack/inject operation as structural validation only. A
   resource can still crash the game because of incompatible vertex layout,
   bone palette, material references, texture format, or prefetch metadata.
5. Do not claim game-level completion until the package has been launched in a
   matching PC build and exercised in gameplay.
6. "Complete model" means every intentionally visible source mesh and material
   region survives unless a rendered and documented comparison proves it is a
   hidden duplicate or internal surface. Unsupported accessory bones are a
   retarget/reweight problem, not permission to delete the affected geometry.

## Pinned toolchain

- AnvilToolkit 1.3.6: structural research, CRC-name dictionary, Blender preset,
  and older/Shadows format comparison only. Its Black Flag Resynced Forge v50
  reader/writer and Mesh support are incomplete; never use it as the final
  compiler for this project.
- Blender 4.2.23 LTS at
  `<steam-library>\steamapps\common\Blender\blender.exe`. This build has loaded
  both supplied source formats successfully. The AnvilToolkit Blender 4.0
  preset passes a controlled glTF round trip after the removed legacy
  `export_colors` property is translated to Blender 4.2's explicit vertex-color
  export properties by `scripts/check_anvil_gltf_preset.py`.
- EncryptedStudios Forge Injector v4: append-and-repoint workflow authority and
  current-boot format cross-check. It is not a model/resource compiler. Its
  complete-stored-entry strategy may append a replacement after the TOC and
  repoint only the selected row. The project's scripted implementation must
  still pin IDs, rows, hashes, process state, full backup, transaction journal,
  and post-write readback; a GUI success alone is not release authority.
- Project-local `scripts/extract_forge_v50_bms.py` and
  `scripts/rebuild_forge_v50_patch.py`: authoritative fail-closed Forge v50
  path for this project. They preserve object order and opaque metadata, decode
  and re-encode raw LZ4 field-4 chunks, reopen every rebuilt typed entry, and
  refuse replacements whose envelope ID/type does not match.
- Jormungandr source checkout: secondary format research and independent binary
  checks only; it is Valhalla-oriented and is not the final compiler.

Exact archives, download URLs, hashes, and license notes belong in
`docs/RESEARCH.md` once downloaded.

## Resume protocol

For every resumed work session:

1. Read `docs/STATUS.md`, then the latest reports in `work/reports/`.
2. Re-hash the immutable source model, FBX, and reference Forge and compare them
   with `docs/RESEARCH.md` before running a converter.
3. Work only from `work/`, write unaccepted candidates to `work/package/`, and
   copy only a runtime-accepted release into `dist/`.
4. Append newly pinned tool versions, download origins, hashes, and format
   discoveries to `docs/RESEARCH.md`; update the current checkpoint in
   `docs/STATUS.md` before stopping.
5. Never promote a stage while an owning tool cannot reopen its output or a
   scripted report cannot be parsed independently.

The baseline resume check is:

```powershell
python scripts\validate_workspace.py
python scripts\check_input_handoff.py
```

## Stage 0 - Inventory and freeze inputs

1. Inventory all files, sizes, timestamps, and SHA-256 hashes.
2. Read the reference README and publication URL.
3. Confirm whether the target PC game is installed and record its build number.
4. Copy source assets to `work/source_copy/` only when a tool requires a writable
   input. Do not rename or normalize originals.

Exit criteria: inventory is recorded and source hashes are stable.

Current result: passed on 2026-07-22. The exact hashes are recorded in
`docs/RESEARCH.md` and the source audit confirms the input stayed unchanged.

Current installed target observed on 2026-07-23: Steam AppID `3751950`,
BuildID/TargetBuildID `24326718`; `ACBlackFlag.exe` SHA-256
`50E53234CA38517CCFB976B63A1FDB93646336C72D19B7EF638A555BE5B7EB4A` and
`DataPC_boot_patch_01.forge` SHA-256
`900F7E07B5961B1FBD67281ABE1ADF1AFEB2CA5490FE5149A61832319FEBCCD7`.
Steam updated this installation during the project, so rerun build inventory
before extracting original resources, injecting a patch, or launching tests.

The immutable Blender checkpoint and packed-image extraction commands are:

```powershell
& '<steam-library>\steamapps\common\Blender\blender.exe' `
  --factory-startup --background --disable-autoexec `
  --python scripts\stage_source_blend.py -- `
  --source karin_D7-E4-04.blend

& '<steam-library>\steamapps\common\Blender\blender.exe' `
  --factory-startup --background --disable-autoexec `
  --python scripts\stage_source_blend.py -- --verify-only
```

The first command creates an atomic, byte-identical checkpoint rather than
resaving the Blender project. It also exports original packed PNG bytes with
full-SHA-256 filenames. The second command reopens and verifies all outputs in
a fresh Blender process.

## Stage 1 - Unpack and identify the reference resources

1. Inventory the reference `DataPC_boot_patch_02.forge`, then decode its BMS
   bundles with `scripts/extract_forge_v50_bms.py`. Require the input to be a
   disposable copy under `work/reference_extraction/`; the script refuses the
   original reference-mod file. Forge Injector output is research context only,
   not an independent authority for this field-4 patch.
2. Export all named resources and a machine-readable inventory containing
   resource ID, type, stored size, decoded size, BMS blocks, and checksum data.
   Do not infer v50 codec meanings from older Forge versions: a layer is
   considered decoded only when its declared output size and structural parser
   checks both pass.
3. Identify Duncan outfit mesh LODs, skeleton/bone palette, materials,
   TextureSets/TextureMaps, EntityBuilder/BuildTable links, and the five boot
   patch metadata resources.
4. Parse target Mesh resources with `scripts/parse_bfr_reference_meshes.py` and
   import the emitted GLB in the pinned Blender build. Export referenced
   textures to lossless editable files plus payload copies retaining GPU format
   metadata. A flat embedded-MeshBone preview is not a Skeleton hierarchy.
5. Repack an unchanged round trip and compare the resource table and decoded
   resources. Byte-identical whole-Forge output is preferred but not required
   if offsets/order legitimately change.

Exit criteria: every reference resource has an ID/type mapping; unchanged
round-trip opens and verifies; target GLB imports in Blender with a valid rig.

Current Mesh result: passed on 2026-07-23. The two resources
`0x00000081786E922F` and `0x0000009611D6CEAE` parse to 1,041/627 vertices and
1,384/948 triangles. They share an identical 759-entry MeshBone table, use
format 1 with 16/12/24-byte static/dynamic/influence streams, eight influences,
16-bit global bone indices, and material `0x000000BAC7CA10D9`. Structural
parse-to-serialize and GLB-to-Mesh rebuilds are byte-identical. See
`work/reference_extraction/mesh_contracts/bfr_reference_mesh_contract.json`
and `work/model_pipeline/bfr_mesh_writer_selftest/bfr_mesh_writer_contract.json`.
The parent hierarchy is still required from the base game.

## Stage 2 - Audit the Karin source model

Capture in `work/reports/source_blend_audit.json`:

- object, mesh, armature, bone, material, image, and animation counts;
- vertex/edge/triangle counts per mesh and UV/color/custom-normal layers;
- active modifiers, shape keys, constraints, non-uniform transforms, and scale;
- material-to-texture graph, image paths, packing state, dimensions, channels,
  color spaces, and missing files;
- vertex group influence counts, unweighted vertices, and maximum influences;
- bounding box, height, forward/up axes, rest pose, and facial/cloth components.

Exit criteria: audit is reproducible in background Blender and all texture data
needed for the visible character is available or explicitly reconstructed.

The verified audit command is:

```powershell
& '<steam-library>\steamapps\common\Blender\blender.exe' `
  --factory-startup --background --disable-autoexec `
  --python scripts\audit_blend.py -- `
  --input karin_D7-E4-04.blend `
  --output work\reports\source_blend_audit.json `
  --markdown work\reports\source_blend_audit.md
```

Current audit result: passed on 2026-07-22. All 24 referenced external image
paths are unavailable, but all 24 image datablocks are packed in the source.
The source has no unweighted vertices and no vertex with more than four
positive weight influences. The four selected appearance shape keys were later
baked into `work/blender/karin_source_baked.blend`; zero weights were removed.
Target mapping and compilation are recorded under Stages 4 and 5.

The source-side bone classification and texture analysis commands are:

```powershell
& '<steam-library>\steamapps\common\Blender\blender.exe' `
  --factory-startup --background --disable-autoexec `
  --python scripts\analyze_source_bones.py

python scripts\analyze_source_textures.py
```

Their reports are `work/reports/source_bone_classification.*` and
`work/reports/source_texture_analysis.*`. Bone categories are preparation
hints only; never use them as an automatic pruning list.

The repeatable source preview command is:

```powershell
& '<steam-library>\steamapps\common\Blender\blender.exe' `
  --factory-startup --background --disable-autoexec `
  --python scripts\render_source_preview.py -- `
  --input karin_D7-E4-04.blend `
  --output-dir work\reports\source_previews
```

Inspect all three rendered views before accepting any later topology,
material, bind, or LOD checkpoint.

## Stage 3 - Prepare topology, materials, and textures

1. Create `work/blender/karin_game_working.blend` from the source.
2. Remove hidden/internal geometry that causes clipping only after a checkpoint.
3. Resolve duplicate surfaces, invalid normals, non-manifold seams, loose
   geometry, degenerate triangles, and unsupported modifiers.
4. Consolidate materials and atlases only when required by the target primitive
   count/material slot layout. Preserve source UVs when compatible.
5. Bake target PBR channels using the reference material conventions. Preserve
   alpha semantics and normal-map handedness/channel packing.
   A material Alpha socket alone is not proof of stored transparency: four
   audited source routes point to RGB PNGs whose implicit alpha is 1.0,
   including the transparent-hair material. Confirm visible intent against the
   source renders before reconstructing or discarding alpha.
6. Produce power-of-two texture dimensions and the exact target BC compression,
   mip count, sRGB/linear flags, and swizzle. Keep the audited 4096-square 16-bit
   RGB atlas as a lossless authoring master, but build the accepted runtime maps
   at 2048 square. Do not use an 8-bit contact-sheet decode as input.

Exit criteria: render/viewport checks show no missing texture, broken alpha,
flipped normal, overlapping duplicate surface, or unsupported node dependency.

## Stage 4 - Fit and bind to the target skeleton

1. Import the reference target GLB into the working scene without altering its
   rest pose, bone names/indices, hierarchy, or scale.
2. Align Karin to the target bind pose and proportions. Apply object transforms
   only after verifying exported coordinates against the reference GLB.
3. Transfer or rebuild weights onto the target deform bones. Limit influences to
   eight, normalize them, and quantize the final eight byte weights to total
   exactly 255. Joint indices are unsigned 16-bit direct indices into the
   immutable 759-entry MeshBone order. Do not apply the legacy 42-bone palette
   rule: these resources contain no per-primitive palette table and the two
   reference primitives already use 165 and 382 distinct global bones.
4. Manually correct shoulders, elbows, wrists/fingers, hips, knees, ankles,
   neck/jaw, coat/skirt-like parts, and equipment contact regions.
5. Test representative extreme poses and compare silhouette, joint volume,
   self-intersection, and weapon/parkour contact points.
6. Keep facial meshes or auxiliary bones only if the target resource supports
   them; otherwise use a deliberate rigid or head-bone binding strategy.

Accessory fallback order when no one-to-one target chain exists:

1. Reuse a semantically matching native target chain when available.
2. Bind rigid head accessories, ears, eyes, and halo parts to the nearest target
   head/neck bone while preserving their source rest-pose transforms.
3. Reweight deformable hair, tail, ribbons, and coat panels to verified target
   head, spine, pelvis, or limb bones with local gradients. Preserve the full
   silhouette even when secondary motion cannot be reproduced.
4. Retain a source auxiliary bone only when the compiled target skeleton accepts
   the added index and an animation test proves stable transforms. Successful
   GLB export alone is not proof.

Before removing shape keys, bake the four active source appearance choices into
the working mesh: `Ahoge_big=1`, `Hair_tail_volume_up=1`, `Foot_OFF=1`, and
`Toe_OFF=1`. Keep a checkpoint with all original shape keys because the ATK
preset deliberately disables morph export.

Exit criteria: no unweighted vertices, invalid bone references, weight overflow,
or material/primitive mismatch; pose tests pass visual review.

Current result: passed on 2026-07-23 with canonical mode
`rigid_hybrid_pivots`. The current base-game Skeleton
`0x000002242390EC10` supplies 326 exact CRC-authorized inverse-bind matrices;
the remaining 433 entries retain the reference Mesh templates byte-for-byte.
The canonical GLB is `work/model_pipeline/karin_target_bound.glb`, SHA-256
`3E71316DFD7807961140DDA17A39621561F647CB2045BBBA8A809DDACE89D6A4`.
Front/three-quarter/back PBR renders and all three shoulder/elbow/hip/knee
stress poses passed manual review. Raw bone-roll copies and the old
translation-only long-neck output remain explicitly marked rejected. See
`work/reports/final_model_pipeline_manifest.json`.

### Candidate T pelvis/thigh correction checkpoint (2026-07-24)

Do not use Candidate S as the UV-optimized runtime candidate. Its
`rigid_hybrid_pivots` conversion maps the fitted root and both UpLeg origins to
nearly the same target height. The source root-to-UpLeg drop is 86.424 mm, so
the weighted result moves root-bound shorts down and leg-bound upper thighs up.
That is the cause of the reported high thigh roots and incomplete pants; no
vertices, triangles, alpha, or Costume partition were missing.

The first runtime comparison candidate is Candidate T mode
`rigid_hybrid_grounded_axial_pelvis`, with no default Hips/UpLeg reweight:

1. Keep the global-fit root and UpLeg origins so the source pelvis separation
   and shorts silhouette remain intact.
2. For each UpLeg-to-knee, knee-to-ankle, and ankle-to-toe segment, use
   `A = R * (I + (s - 1) * u * u^T)`. This maps both segment endpoints, scales
   only along source axis `u`, and preserves transverse thickness.
3. Transform normals with `inverse(transpose(A))`; transform tangents with `A`
   and orthogonalize them against the final normal.
4. Preserve indices, joint order, joint assignments, weights, colors, UV0/UV1,
   and inverse-bind authority. Reverse winding only in the downstream derivative.
5. Pin the resulting GLB SHA-256 to
   `F6576F9D5D07009689C12715A08FC34F48D5014F0C3AF065E9BAC0E9486DE292`.

Offline acceptance thresholds for this checkpoint are:

- root-to-UpLeg source separation retained within 2 mm;
- upper-thigh/transition median offset from the global source no more than 5 mm;
- knee/ankle/toe endpoint error no more than `1e-6` m;
- fixed-world sole minimum within 5 mm of Candidate S;
- robust lower-limb edges (source/rest edge at least 1 mm): static p95 no more
  than 1.10, outliers no more than 150, adjacent displacement-jump p95 no more
  than 5.2 mm;
- normals/tangents finite, unit length within numeric tolerance, and mutually
  orthogonal;
- rest front/three-quarter/back plus knee45, combo, pure hip-flex55 and pure
  hip-abduct55 renders retained for visual comparison.

Candidate T passes these offline thresholds: static robust p95/outliers are
`1.09569/122`; fixed-world sole delta is `-2.124 mm`; robust pose p99 is
`1.4151` for flex55 and `1.2466` for abduct55. Keep all-edge/sub-millimetre
ratios in the report, but do not use them as the pass metric because near-zero
rest edges make ratios unstable. Grounded-rigid is rejected (`1.23459/1530`),
and the five distributed-grounding prototypes are rejected (best 503 outliers).

The abduct55 edge audit does not justify a pre-runtime weight rewrite. All four
candidates have byte-equivalent per-vertex target weights. Candidate T and
grounded-rigid share 99.25% of robust top-1% edges and 97.01% of top-0.1%
edges; the tail is concentrated in source `Body` and `ClothA_Blue` around the
central waist and inner thigh. Candidate T robust p99 remains 1.2466. Treat
the raw imported all-edge p99 of 3.9956 as a recorded sub-millimetre-edge
precision diagnostic, not evidence of an axial-only weight regression.

Offline PASS is not runtime acceptance. Target Hips/UpLeg pivots still differ
from the fitted source by about 44.947/60.027 mm, shin/foot axial scales are
about 1.09345/1.07017, and isolated extreme edges remain. In game, inspect
idle/crouch, walk/run, jump/climb, combat, swimming, hip flexion/abduction,
knee hollows, boot/pant boundaries, shorts openings, and sole clipping. If a
localized reweight is needed, derive it from the axial GLB; never apply an old
hipsfix `motion_guard` GLB to this candidate.

## Stage 5 - LOD and game-resource compilation

1. Match the reference resource's one-primitive layout, complete format-1
   vertex semantics, 16-bit index width, global bone order, culling bounds,
   material ID, resource identity, and triangle front-face convention. BFR's
   reference Meshes use the opposite index winding from the canonical glTF;
   reverse each triangle before runtime compilation without changing vertex
   normals or tangents.
2. Build LOD0 first and compile it with
   `scripts/build_bfr_meshes_from_glb.py`. Generate lower LODs only after
   confirming which resources the Duncan outfit actually loads.
3. Preserve every non-geometry field from the parsed target Mesh template.
   Reject missing `TANGENT`, second UV/color set, second joint/weight set,
   reordered joint CRCs, nonnumeric material names, and geometry outside the
   template culling extents unless expansion has been reviewed explicitly.
4. Preserve the measured binding graph: both Meshes reference Material
   `0x000000BAC7CA10D9`, which directly references the diffuse, normal, and
   specular TextureMaps. Do not invent a top-level TextureSet or new resource
   IDs.
5. Reparse every compiled Mesh/Material/TextureMap with the owning project
   parser, compare semantic reports, and independently decode the final Forge
   after injection. AnvilToolkit reopening is supplementary, not authoritative.

### Texture atlas and TextureMap build

Build the 4x4 atlas first. The manifest is the UV-remap contract: every source
face must use the transform recorded for its material before the two target
Meshes are compiled.

```powershell
python scripts\build_karin_texture_atlas.py

$texconv = 'work\downloads\texconv-may2026.exe'
$runtime = 'work\model_pipeline\textures\runtime_2048'
$dds = "$runtime\dds"
New-Item -ItemType Directory -Force -Path $dds | Out-Null

# The source PNG is already sRGB. Both flags are required; omitting -srgbi
# reproduces the rejected double-sRGB transfer.
& $texconv -f BC3_UNORM_SRGB -m 0 -w 2048 -h 2048 -dx10 `
  -srgbi -srgbo -y -o $dds `
  work\model_pipeline\textures\karin_diffuse_atlas_4096.png

# DirectXTex names this output after the source stem. Normalize only the DX10
# alpha-mode metadata; the script proves the compressed payload is unchanged.
python scripts\normalize_dds_dx10_alpha_mode.py `
  $dds\karin_diffuse_atlas_4096.dds `
  $dds\karin_diffuse_atlas_2048_alpha0.dds `
  --mode 0

# Build the accepted neutral tangent-space normal through an R32G32_FLOAT
# intermediate. The source atlas is already DirectX -Y; do not invert green.
python scripts\build_bfr_signed_bc5_dds.py `
  --normal $runtime\png\karin_normal_atlas_2048.png `
  --specular $runtime\png\karin_specular_atlas_2048.png `
  --normal-strength 0.0 `
  --output-dir $runtime\dds_snorm_flat
```

The accepted replacement DDS inputs are 2048x2048 Texture2D files with complete
12-mip chains. Diffuse is DXGI 78 (`BC3_UNORM_SRGB`); normal is DXGI 84
(`BC5_SNORM`), BFR pixel-format index 10 with gamma 0. The signed builder maps
normal X/Y through an `R32G32_FLOAT` intermediate and invokes `texconv` with
`-f BC5_SNORM -m 0 -dx10 -y`. Candidate R sets XY strength to 0.0 because the
source tangent-space normal is incompatible with BFR's runtime tangent basis.
This yields a neutral tangent-space map; the Mesh vertex normals still provide
geometric lighting. Candidate R retains the exact reference 16x16, 5-mip DXGI
84 specular TextureMap instead of replacing it.

Compile and independently verify the cloned TextureMaps:

```powershell
python scripts\build_bfr_textures_from_dds.py `
  --diffuse work\model_pipeline\textures\runtime_2048\dds\karin_diffuse_atlas_2048_alpha0.dds `
  --normal work\model_pipeline\textures\runtime_2048\dds_snorm_flat\karin_normal_atlas_2048.dds `
  --specular work\model_pipeline\textures\diagnostics\solid_magenta_512\specular_reference_bc5_snorm.dds `
  --output work\model_pipeline\compiled_textures_atlas2048_flatnormal_refspec

python scripts\verify_bfr_compiled_textures.py `
  --compiled-dir work\model_pipeline\compiled_textures_atlas2048_flatnormal_refspec
```

Do not promote the result unless
`bfr_compiled_texture_verification.json` reports `PASS`, all replacement mips
are byte-identical to the normalized inputs, all D3D12 row and placement padding
is zero, extracted DDS files are byte-identical, and signed-channel semantic
checks pass. Each 2048 replacement occupies 21,860 256-byte pages. The 4096
all-inline probe occupies 87,396 pages and remains runtime-unverified; retain it
only as an authoring/structural experiment, not as a release requirement.

### Candidate U localized sock diffuse correction

Use this path when only the two `Body.006 / ClothA_Blue` sock/leg-cover
surfaces must stop receiving the prior emissive-to-diffuse max-merge. Do not
rebuild the UV layout, weights, Meshes, normal, Material, or specular resource.
The selected connected-component IDs are 0 and 2; their provenance is bound to
the immutable SHA-256 of `karin_D7-E4-04_uv_optimized.blend`.

```powershell
& '<steam-library>\steamapps\common\Blender\blender.exe' `
  --background karin_D7-E4-04_uv_optimized.blend `
  --python scripts\audit_sock_texture_regions.py -- `
  --output-root work\reports\candidate_t_v11\diagnostics\sock_texture `
  --object Body.006 --mask-size 512

python scripts\build_sock_diffuse_only_mask.py
python scripts\build_candidate_u_sock_diffuse_atlas.py
python scripts\validate_candidate_u_sock_diffuse_atlas.py
```

The atlas builder starts from Candidate T. It rasterizes the two components at
4x supersampling, uses a hard triangle mask, dilates by 16 authoring pixels / 8
runtime inner-tile pixels, restores RGB from the original packed diffuse, and
copies Candidate T alpha unchanged. Require zero changed RGB pixels outside
the mask, zero alpha changes, and zero overlap between the expanded mask and
other ClothA geometry. At 2048, the accepted atlas changes 32,224 RGB pixels;
both components must remain blue with near-white fraction below the validator's
threshold.

Compile only the new diffuse while reusing Candidate T's flat normal and the
reference specular DDS:

```powershell
$texconv = 'work\downloads\texconv-may2026.exe'
$uTexture = 'work\model_pipeline\candidate_u\downstream\textures'
New-Item -ItemType Directory -Force -Path "$uTexture\diffuse_dds\raw" | Out-Null

& $texconv -f BC3_UNORM_SRGB -m 0 -w 2048 -h 2048 -dx10 `
  -srgbi -srgbo -y -o "$uTexture\diffuse_dds\raw" `
  work\v1_1\candidate_u_sock_diffuse_only\atlas\runtime\karin_candidate_u_sock_diffuse_atlas_2048.png

python scripts\normalize_dds_dx10_alpha_mode.py `
  $uTexture\diffuse_dds\raw\karin_candidate_u_sock_diffuse_atlas_2048.dds `
  $uTexture\diffuse_dds\karin_candidate_u_sock_diffuse_atlas_2048_alpha0.dds `
  --mode 0

python scripts\build_bfr_textures_from_dds.py `
  --output $uTexture\compiled `
  --diffuse $uTexture\diffuse_dds\karin_candidate_u_sock_diffuse_atlas_2048_alpha0.dds `
  --normal work\model_pipeline\candidate_t\downstream\textures\signed_dds_flat\karin_normal_flat_2048.dds `
  --specular work\model_pipeline\textures\diagnostics\solid_magenta_512\specular_reference_bc5_snorm.dds

python scripts\verify_bfr_compiled_textures.py `
  --compiled-dir $uTexture\compiled
python scripts\validate_candidate_u_compiled_diffuse.py
```

The compiled diffuse resource must be
`47644A964570453CB2ABC977703ACD665715EB380E5484FE326E297DBAB151CF`.
The two Mesh resources and normal must remain byte-identical to Candidate T;
Material and specular must remain byte-identical to the reference. Prove this
again with `scripts/validate_candidate_u_delta.py` after rebuilding the Forge.

### Material and alpha strategy

Resolve alpha fields from current-game assets before mutating the compact
reference Material. The exhaustive scan reads only the 2,993 top-level
Material entries selected by the Forge TOC and exports same-game mode-1
examples under `work/`; it never writes to the game archive.

```powershell
python scripts\scan_bfr_alpha_display_materials.py

& '<steam-library>\steamapps\common\Blender\blender.exe' `
  --background --python scripts\render_karin_alpha_thresholds.py -- `
  --input work\blender\karin_source_baked.blend `
  --alpha-audit work\reports\karin_alpha_material_compatibility.json `
  --output-dir work\reports\karin_alpha_threshold_previews

python scripts\build_karin_alpha_threshold_comparison.py
python scripts\build_bfr_alpha_test_material_candidates.py
```

Candidate R does not replace Material `0x000000BAC7CA10D9`; it must remain
byte-identical to the reference, including all three TextureMap IDs. The earlier
Material A/B/C alpha-test variants passed their narrow offline byte-whitelist
checks but were never accepted as release inputs. Preserve those reports as
audit history only. Any future Material change requires a new candidate name,
parse-to-serialize identity, an exact whole-file byte whitelist, and a complete
repeat of the runtime matrix.

### Canonical Mesh result

Build the audited winding derivative from the promoted authoring GLB, compile
that derivative, and then reparse the two outputs:

```powershell
python scripts\build_karin_reversed_winding_variant.py

python scripts\build_bfr_meshes_from_glb.py `
  --input work\model_pipeline\candidates\karin_target_bound_reversed_winding.glb `
  --output-dir work\model_pipeline\candidates\compiled_reversed_winding

python scripts\parse_bfr_reference_meshes.py `
  --inputs `
    work\model_pipeline\candidates\compiled_reversed_winding\asset_009_00000081786E922F.compiled.bin `
    work\model_pipeline\candidates\compiled_reversed_winding\asset_010_0000009611D6CEAE.compiled.bin `
  --output-dir work\model_pipeline\candidates\compiled_reversed_winding\strict_reparse

python scripts\validate_compiled_meshbone_authority.py `
  --compiled `
    work\model_pipeline\candidates\compiled_reversed_winding\strict_inputs\asset_009_00000081786E922F.bin `
    work\model_pipeline\candidates\compiled_reversed_winding\strict_inputs\asset_010_0000009611D6CEAE.bin `
  --report work\model_pipeline\candidates\compiled_reversed_winding\meshbone_authority_validation.json
```

The accepted resources contain 31,548/27,820 vertices and 48,030/40,482
triangles. Their SHA-256 values are respectively
`6176833723256B7B57558629EF95235C634AEBC0E28B146A711D114A3E9B4373`
and
`5F4A00041D0A74B6F3AAF0D619773A262AE105E1DF4C4AEACDFEFE83F02E7D65`.
The winding derivative SHA-256 is
`ADCF4BAD9A0A48241BFED8010D68123FDED11AE918C86D09A51996D0EA7D6959`.
The packaged normal atlas is DirectX `-Y`: its green channel is inverted once
by `build_karin_texture_atlas.py`; Blender QA inverts it once back to OpenGL
`+Y` before the Normal Map node. The signed DDS encoder performs no additional
green inversion.

Exit criteria: compiled resources parse, re-export, have valid references, and
pass scripted vertex/bone/material/texture checks. The winding contract must
report the same negative geometric-normal dot sign as the BFR reference.

## Stage 6 - Package and verify

1. Build a new thin patch Forge in `work/package/`; never overwrite the
   reference archive.
2. Preserve the boot patch chain metadata. For a new highest-numbered patch,
   carry the complete `PrefetchingFileInfos` graph into the corresponding
   `PrefetchInfoOverrides` parent set and update `DeletedFilesManifest`.
3. If deliberately replacing `DataPC_boot_patch_02.forge` as the reference mod
   does, preserve its validated metadata/resources and change only mapped model,
   material, and texture entries.
4. Re-open, extract, and hash every modified resource from the final Forge.
5. Install only into a backed-up matching game build. Always test launch, save
   load, and wardrobe selection of Duncan's outfit, retaining direct evidence.
6. For a public or comprehensive claim, also test cutscenes, traversal, combat,
   swimming, ship gameplay, wetness/lighting, distance LOD transitions, and
   restart. Do not infer a pass from an unrelated screenshot.
7. A private documented-partial release is allowed only when the user explicitly
   stops further testing and accepts the recorded residual risk. Preserve every
   uncovered row as `NOT_TESTED`; never relabel it as `PASS`.

Exit criteria: structural round-trip and strict payload validation pass, and the
runtime scope is represented truthfully as either a complete matrix or an
explicit user-authorized private partial scope.

The repeatable Candidate R four-resource build and independent validation
pattern is:

```powershell
python scripts\rebuild_forge_v50_patch.py `
  --input work\reference_extraction\input\DataPC_boot_patch_02.forge `
  --output work\package\karin_candidate_r_reversed_winding_atlas2048_flatnormal_refspec\DataPC_boot_patch_02.forge `
  --report work\reports\karin_candidate_r_forge_rebuild.json `
  --replace 0x00000081786E922F=<mesh-81786E922F> `
  --replace 0x0000009611D6CEAE=<mesh-9611D6CEAE> `
  --replace 0x000000BAC7CA10DA=<diffuse> `
  --replace 0x000000BAC7CA10DB=<flat-normal>

python scripts\extract_forge_v50_bms.py <disposable-final-forge> `
  --output-root <fresh-final-extraction> `
  --json-output work\reports\karin_candidate_r_extraction.json

python scripts\validate_final_forge_payload.py `
  --final-report work\reports\karin_candidate_r_extraction.json `
  --final-root work\reference_extraction\candidate_r_52355DAC\extracted `
  --package work\package\karin_candidate_r_reversed_winding_atlas2048_flatnormal_refspec\DataPC_boot_patch_02.forge `
  --rebuild-report work\reports\karin_candidate_r_forge_rebuild.json `
  --replacement 0x00000081786E922F=work\model_pipeline\candidates\compiled_reversed_winding\asset_009_00000081786E922F.compiled.bin `
  --replacement 0x0000009611D6CEAE=work\model_pipeline\candidates\compiled_reversed_winding\asset_010_0000009611D6CEAE.compiled.bin `
  --replacement 0x000000BAC7CA10DA=work\model_pipeline\compiled_textures_atlas2048_flatnormal_refspec\resources\asset_007_000000BAC7CA10DA.bin `
  --replacement 0x000000BAC7CA10DB=work\model_pipeline\compiled_textures_atlas2048_flatnormal_refspec\resources\asset_006_000000BAC7CA10DB.bin `
  --preserve 0x000000BAC7CA10D9 `
  --preserve 0x000000BAC7CA10DC `
  --json-output work\reports\candidate_r_final_forge_payload_validation.json `
  --markdown-output work\reports\candidate_r_final_forge_payload_validation.md
```

Current Candidate R result: rebuild `PASS`; Forge SHA-256
`52355DAC381F1882B3349BDC1E4A40962083265AFE6B79377DE2BD80B7964113`.
Independent extraction passed 725/725 checks and recovered 8 BMS blocks and 15
assets. The strict validator passed 3659/3659 and proved 4 changed resources, 2
explicitly preserved targets, and 11 byte-identical decoded resources. It also
proved byte identity between the validated package, staged Forge, rebuild
report, and independently extracted resources.

### Candidate T isolated pelvis-fix build

Candidate T is generated only in its guarded profile. It must not overwrite
Candidate S, Candidate R, `dist/Karin_Playable_1.0`, or the game directory:

```powershell
python scripts\build_v11_downstream.py --candidate-profile t --self-test
python scripts\build_v11_downstream.py --candidate-profile t --plan --through release
python scripts\build_v11_downstream.py --candidate-profile t --execute --through release `
  --release-timestamp 2026-07-24T06:00:00+00:00
```

The 2026-07-24 run passed through release. The final Forge SHA-256 is
`8A6C8764A590E58A6002532216433A21DF5EA6F714AF6D1EFB0DE0D2FE81552E`;
independent extraction passed `725/725`, and strict payload validation passed
`3659/3659` with the same 4 changed / 2 preserved / 11 unchanged partition.
The deterministic structural ZIP is
`work/package/candidate_t_release_staging/Karin_Playable_1.1_UV_Optimized_PelvisFix.zip`,
SHA-256 `20EBBE602BC5F2D8F68450F7604433D3B374E275B8B34996FFC2A5C9140F4133`.
Keep it out of `dist/` until the runtime matrix above is directly observed.

Runtime installation checkpoint (2026-07-24): the game was closed, the prior
Candidate R Forge was copied and hash-verified before overwrite, and Candidate
T was then installed with exact SHA-256
`8A6C8764A590E58A6002532216433A21DF5EA6F714AF6D1EFB0DE0D2FE81552E`.
The rollback Forge is
`work/runtime_backups/2026-07-24_pre_candidate_t_52355DAC/DataPC_boot_patch_02.candidate_r_52355DAC.forge`,
SHA-256 `52355DAC381F1882B3349BDC1E4A40962083265AFE6B79377DE2BD80B7964113`.
The machine-readable record is in the same directory as
`INSTALLATION_RECORD.json`. Installation does not promote Candidate T to
`dist/` and does not count as runtime acceptance.

### Candidate U isolated sock-diffuse build

Candidate U inherits Candidate T's pelvis-fix geometry. Build its Forge from
the immutable reference patch, not by binary-patching the installed T Forge:

```powershell
python scripts\rebuild_forge_v50_patch.py `
  --input work\reference_extraction\input\DataPC_boot_patch_02.forge `
  --output work\package\karin_candidate_u_uv_optimized_pelvisfix_sockdiffuse\DataPC_boot_patch_02.forge `
  --report work\reports\candidate_u_v11\candidate_u_forge_rebuild.json `
  --replace 0x00000081786E922F=work\model_pipeline\candidate_t\downstream\meshes\compiled\asset_009_00000081786E922F.compiled.bin `
  --replace 0x0000009611D6CEAE=work\model_pipeline\candidate_t\downstream\meshes\compiled\asset_010_0000009611D6CEAE.compiled.bin `
  --replace 0x000000BAC7CA10DA=work\model_pipeline\candidate_u\downstream\textures\compiled\resources\asset_007_000000BAC7CA10DA.bin `
  --replace 0x000000BAC7CA10DB=work\model_pipeline\candidate_u\downstream\textures\compiled\resources\asset_006_000000BAC7CA10DB.bin

New-Item -ItemType Directory -Force `
  work\reference_extraction\candidate_u_v11 | Out-Null
Copy-Item `
  work\package\karin_candidate_u_uv_optimized_pelvisfix_sockdiffuse\DataPC_boot_patch_02.forge `
  work\reference_extraction\candidate_u_v11\DataPC_boot_patch_02.forge

python scripts\extract_forge_v50_bms.py `
  work\reference_extraction\candidate_u_v11\DataPC_boot_patch_02.forge `
  --output-root work\reference_extraction\candidate_u_v11\extracted `
  --json-output work\reports\candidate_u_v11\candidate_u_forge_extraction.json

python scripts\validate_final_forge_payload.py `
  --final-report work\reports\candidate_u_v11\candidate_u_forge_extraction.json `
  --final-root work\reference_extraction\candidate_u_v11\extracted `
  --package work\package\karin_candidate_u_uv_optimized_pelvisfix_sockdiffuse\DataPC_boot_patch_02.forge `
  --rebuild-report work\reports\candidate_u_v11\candidate_u_forge_rebuild.json `
  --replacement 0x00000081786E922F=work\model_pipeline\candidate_t\downstream\meshes\compiled\asset_009_00000081786E922F.compiled.bin `
  --replacement 0x0000009611D6CEAE=work\model_pipeline\candidate_t\downstream\meshes\compiled\asset_010_0000009611D6CEAE.compiled.bin `
  --replacement 0x000000BAC7CA10DA=work\model_pipeline\candidate_u\downstream\textures\compiled\resources\asset_007_000000BAC7CA10DA.bin `
  --replacement 0x000000BAC7CA10DB=work\model_pipeline\candidate_u\downstream\textures\compiled\resources\asset_006_000000BAC7CA10DB.bin `
  --preserve 0x000000BAC7CA10D9 `
  --preserve 0x000000BAC7CA10DC `
  --json-output work\reports\candidate_u_v11\candidate_u_final_forge_payload_validation.json `
  --markdown-output work\reports\candidate_u_v11\candidate_u_final_forge_payload_validation.md

python scripts\validate_candidate_u_delta.py
python scripts\build_candidate_u_release.py
python scripts\build_candidate_u_release.py --verify
```

The accepted structural result is Forge
`68D09380FF2DBBFC278319F80579E3469F59F260D2BCFA626E44236058F09465`;
independent extraction is `725/725`, strict payload validation is `3659/3659`,
and the semantic delta from Candidate T is only diffuse
`0x000000BAC7CA10DA`. The deterministic staging ZIP is
`work/package/candidate_u_release_staging/Karin_Playable_1.1_UV_Optimized_PelvisFix_SockDiffuse.zip`,
SHA-256 `FFDFE8D3AF6784E5991D47DA12A014F7D9B5FD8D11740C116E508249F2CB0321`.
Keep it outside `dist/` until U receives its own runtime review.

Historical runtime installation checkpoint (2026-07-24): with the game closed,
the installed Candidate T was copied and hash-verified before overwrite.
Candidate U was installed at exact SHA-256
`68D09380FF2DBBFC278319F80579E3469F59F260D2BCFA626E44236058F09465`.
Rollback uses
`work/runtime_backups/2026-07-24_pre_candidate_u_8A6C8764/DataPC_boot_patch_02.candidate_t_8A6C8764.forge`,
SHA-256 `8A6C8764A590E58A6002532216433A21DF5EA6F714AF6D1EFB0DE0D2FE81552E`.
The same directory contains `INSTALLATION_RECORD.json`. Installation is not
runtime acceptance and does not modify the accepted private 1.0 release.

### Private release build and verification

`scripts/build_private_release.py` binds the Candidate R Forge, strict payload
report, BuildID `24326718` game inventory, and pinned runtime evidence. It is
fail-closed, does not overwrite an existing release directory or ZIP, and
creates a deterministic five-file directory plus archive. On a fresh versioned
target, run the build and then the read-only verification:

```powershell
python scripts\build_private_release.py --self-test
python scripts\build_private_release.py
python scripts\build_private_release.py --verify
```

The directory inventory must be exactly:

- `DataPC_boot_patch_02.forge`
- `INSTALL_AND_ROLLBACK.md`
- `RUNTIME_SCOPE.md`
- `release_manifest.json`
- `SHA256SUMS.txt`

Current result: `BUILD PASS` and `VERIFY PASS` for
`dist/Karin_Playable_1.0/` and `dist/Karin_Playable_1.0.zip`. The ZIP SHA-256 is
`6F6B72BC6B0DBB0D05CC9B6CA47CC61C9E30CD37A6F32C698D350E013FB3A36C`;
the Forge SHA-256 is
`52355DAC381F1882B3349BDC1E4A40962083265AFE6B79377DE2BD80B7964113`.
The release manifest status is `STRUCTURAL_PASS_RUNTIME_PARTIAL` and records 8
`OBSERVED_PASS` plus 9 `NOT_TESTED`. The user explicitly stopped further
Candidate R testing and authorized this private scope. A public or comprehensive
claim still requires direct evidence for all nine untested rows.

When the game runs at High integrity, use only the audited, PID-locked local
bridge `scripts/runtime_input_bridge.ps1` and client
`scripts/send_runtime_key.ps1`. The audited grammar is `KEY`, `CHORD`, `CLOSE`,
and `QUIT`; key/chord values are restricted by a small virtual-key whitelist.
The bridge validates the fixed executable path/window/PID and exposes a
current-user-only local named pipe. It is an automation aid, not part of the
distributed Mod.

## Stage 7 - Candidate V material-quality lab

Candidate V is an isolated research and calibration branch. It must preserve
the installed Candidate U SockDiffuse Forge, its package, and its authoritative
extraction copy at SHA-256
`68D09380FF2DBBFC278319F80579E3469F59F260D2BCFA626E44236058F09465`.
Do not use Candidate T as the Forge input for Candidate V probes; doing so would
silently remove the accepted SockDiffuse correction.

### Resume gate

Before any Candidate V command:

1. Hash the installed, package, and authoritative Candidate U Forge. Require all
   three to equal `68D09380...F09465`.
2. Verify the Candidate T rollback under
   `work/runtime_backups/2026-07-24_pre_candidate_u_8A6C8764/` remains
   `8A6C8764...81552E`.
3. Confirm no game process is running before any later manual installation.
4. Read `docs/CANDIDATE_V_MATERIAL_LAB.md` and the current handoff JSON.
5. Never install more than one unresolved probe variable at a time.

The read-only aggregate gate is:

```powershell
python scripts\build_candidate_v_material_lab_handoff.py
```

It must report `PASS_OFFLINE_LAB_READY_RUNTIME_UNTESTED` and
`baseline_unchanged=true`.

### Native Material and TextureSet boundary

Run the native analyzers only against the pinned existing extraction:

```powershell
python scripts\analyze_bfr_native_duncan_materials.py
python scripts\analyze_bfr_native_texture_sets.py
python scripts\reconstruct_bfr_native_emissive_dds.py
```

Require byte-identical parse/serialize for the audited Material, TextureSet, and
TextureMap resources. The TextureSet has fourteen slots. For the audited Duncan
template, slot 4 is selected by `ZoneMap` and contains categorical RGB zones.
The historical `emissive` filename prefix in reconstruction artifacts is not a
semantic claim. Never bind Karin emissive color to that slot.

Do not apply the compact pixel-format table to native platform-3 resources.
Native Duncan normal index 10 is BC7_UNORM; compact reference normal/spec index
10 is BC5_SNORM.

### Compact multi-material Mesh procedure

The compact writer accepts one or more GLB primitives per BFR Mesh. For every
primitive:

- compile a contiguous local vertex segment;
- remap triangle indices to local zero-based UInt16 values;
- set cumulative `MinIndex` and `StartIndex`;
- keep vertex count at or below 32,767;
- append one matching instancing record, outer Material reference, and positive
  UV-density value in the same order.

Validate legacy and generalized behavior:

```powershell
python scripts\build_bfr_meshes_from_glb.py --expect-identity `
  --output-dir work\mesh_multimaterial_selftest\postchange_identity
python scripts\selftest_bfr_multimaterial_mesh.py `
  --output-dir work\mesh_multimaterial_selftest\final_verification
```

Both must pass. The self-test must also reject an out-of-range local index and
pass the 32-primitive total-over-Int16 case. This writer does not allocate new
Forge resources and must not be used to rewrite native ClusteredMesh data.

### Tangent-space normal procedure

For runtime Mesh UV precision, quantize UV0 and UV1 to 1/2048 before computing
MikkTSpace. Split vertices at tangent/handedness discontinuities, then compile
the Mesh and reproject the authored normal from the transported old TBN into
the final quantized-UV Mikk TBN. Build both +Y and -Y BC5_SNORM variants with a
complete 12-mip chain; do not choose the sign from naming alone.

Runtime order is mandatory:

1. A flat normal-only.
2. A +Y and A -Y normal-only under the same camera/light.
3. A +X/-X only if a swizzle sanity check is needed.
4. B Mikk split + flat, isolating the geometry/TBN change.
5. Exactly one final C +Y or D -Y result.

Every A probe must declare only normal `0x000000BAC7CA10DB` as replacement.
Every B/C/D probe must declare both Meshes plus that normal. All must explicitly
preserve SockDiffuse `0x000000BAC7CA10DA`.

### Specular, SpecGloss, and WaterFlow procedure

Spec R/G semantics are unknown. Observe R-only, G-only, RG, then quadrants.
Only after that may one of the mutually exclusive semantic RG/GR atlases be
selected. Keep the chosen normal fixed while observing SpecGloss 0.0, 0.25,
0.5, and 2.0.

Observe WaterFlow 0.25 and 1.0 only after normal and spec calibration. The
parameter exists in the compact Material but is absent from all audited Duncan
Materials. Its name does not prove rain wetness, roughness darkening, or global
water behavior.

All Candidate V spec/gloss and WaterFlow probes must be derived from
`work/reference_extraction/candidate_u_v11/DataPC_boot_patch_02.forge`, not a
same-hash copy with a different canonical path, because strict validation binds
the input path as well as size and hash.

### Emissive promotion gate

`scripts/scan_local_bfr_feature_templates.py` is bounded to already extracted
resources. Raw ASCII or CRC hits are discovery leads only. The current native
template has two raw `LightingEmissive` CRC occurrences, but no parsed Material
DynamicProperty or TextureSelector binds them. Do not package authored emissive
atlases until a MaterialTemplate/operator schema proves the binding and a
single-variable runtime probe succeeds.

### Promotion rule

Candidate V remains `RUNTIME_UNTESTED` until each selected behavior is directly
observed. Do not combine unresolved normal sign, spec channels, SpecGloss,
WaterFlow, multi-material allocation, or emissive behavior in one initial
Forge. After each observation, restore and rehash Candidate U before moving to
the next unrelated family.

## Stage 8 - Karin Playable 1.2 integrated observation

The user explicitly requested an all-in-one 1.2 installation after the
single-variable Candidate V probes had been built. This is an observation
override, not evidence that the unresolved material semantics are accepted.
Build only from the authoritative Candidate U SockDiffuse Forge, never from the
installed game file:

```powershell
python scripts\build_karin_v12_integrated.py
python scripts\build_karin_v12_integrated.py --verify
```

The fail-closed build requires all new 1.2 output paths to be absent. It creates
a combined compact Material with `Layer0_SpecGloss=1.0` and
`NG_WaterFlow_Intensity=0.25`, then replaces exactly these resources:

- Mesh `0x00000081786E922F`: quantized-UV Mikk split v3;
- Mesh `0x0000009611D6CEAE`: quantized-UV Mikk split v3;
- Material `0x000000BAC7CA10D9`: WaterFlow 0.25, SpecGloss retained at 1.0;
- Normal `0x000000BAC7CA10DB`: reprojected DirectX `-Y` BC5_SNORM;
- Specular `0x000000BAC7CA10DC`: semantic RG (`R=specular`, `G=gloss`).

Diffuse `0x000000BAC7CA10DA` must be declared as the sole preserved pinned
resource and retain SHA-256
`47644A964570453CB2ABC977703ACD665715EB380E5484FE326E297DBAB151CF`.
Do not copy a whole compiled normal/spec directory because its companion
diffuse may be Candidate T and would silently remove SockDiffuse.

Copy the rebuilt Forge into `work/reference_extraction/candidate_v12/`, run the
independent extractor, then bind all five replacement files and the one
preserved ID in `validate_final_forge_payload.py`. The accepted structural
result is extraction `872/872`, strict payload `4872/4872`, five changed, one
preserved, and ten unchanged decoded resources. The build, staged, release,
and installed Forge must all hash to:

`AC2B51294B5463B814DDC51719820ED006CD93A55E699E466899D7945CB28213`

The five-file release directory is
`work/package/candidate_v12_release_staging/Karin_Playable_1.2/`; the ZIP hash
is `269FBC280D9CEA5E0EA7CC2D3F84F39A0B3F7D0CFAAE7EF3DEA5AC7AFF7871EB`.

Install only through:

```powershell
python scripts\build_karin_v12_integrated.py --install
```

The installer verifies the package, requires Candidate U in the game directory,
checks `ACBlackFlag` twice, creates and verifies a new Candidate U backup, stages
a same-directory temporary, and atomically replaces the game Forge. It writes
`work/runtime_backups/2026-07-24_pre_candidate_v12_68D09380/INSTALLATION_RECORD.json`.
Never modify the release package after installation.

Runtime checks must cover fixed-camera day/shadow/night views, dry versus rain
or near-water views, hair and ClothB mottling, highlight balance across skin,
cloth, hair, and metal, both SockDiffuse regions, pelvis/shorts openings,
movement, climbing, swimming, combat, and save/reload. `WaterFlow=0.25` has the
lowest confidence; record whether it is inert, useful, or visibly wrong.

Multi-material runtime resources and authored emissive are not part of 1.2.
The writer supports multiple primitives, but the Forge rebuilder cannot allocate
new Material/Texture resources. The native Duncan slot is `ZoneMap`, so it must
not be replaced by the authored emissive atlas.

## Stage 9 - Candidate W pure-diffuse priority UV release

Candidate W supersedes the localized Candidate U sock correction and the 1.2
material observation branch for the requested 1.1 release. It keeps Candidate
T's `rigid_hybrid_grounded_axial_pelvis` geometry and weights, removes every
emissive-to-diffuse merge, and rebuilds both Mesh resources because the atlas
UV transforms changed.

### Atlas contract

Always build from the immutable packed source diffuse images. Never use a
Candidate T, U, or 1.2 atlas as a source layer. Emissive inputs may be detected
for audit, but the applied count must remain zero.

The final runtime atlas is 2048 square with a 16-pixel gutter. Its 8x8
bottom-left cell layout is:

| Slot | Cell rectangle `[x,y,w,h]` | Cells |
|---|---:|---:|
| Body | `[0,0,4,4]` | 16 |
| ClothB | `[4,0,4,3]` | 12 |
| ClothA | `[4,3,4,2]` | 8 |
| Face | `[4,5,2,3]` | 6 |
| Hair | `[0,4,2,4]` | 8 |
| HairTransparent | `[2,4,2,2]` | 4 |
| Costume | `[6,5,2,2]` | 4 |
| KarinAlpha | `[2,6,2,2]` | 4 |
| KarinCostume | `[6,7,1,1]` | 1 |
| Ruru shared | `[7,7,1,1]` | 1 |

The six primary slots occupy exactly `54/64` cells (84.375%); the four
accessory slots occupy `10/64`. `Costume_1` and `Costume_Metalic` share Ruru
only because their diffuse/alpha pixels are exact and the runtime normal is
flat. Split that slot before any future authored-normal build.

Build and independently validate:

```powershell
python scripts\build_karin_priority_atlas_v11.py
python scripts\validate_karin_priority_atlas_v11.py
```

Required atlas gates are: 11 material contracts, 10 physical slots, 64/64
cells, two emissive sources detected, zero applied, 20 independently rebuilt
resolution tiles exact, both complete atlases exact, and all 59,368 UV samples
below RGB MAE 18 and alpha MAE 4. The pinned generation for the final layout is
`5B2C56BB536F5F8BC38EAB4A44B46426F18590C8BFD44A21388C7C048B79D791`.

### UV-only Mesh rebuild

Retarget the immutable prepared GLB with the Candidate W atlas manifest and
audit, using Candidate T's exact rest mode. Reverse winding and compile both
Mesh resources. Then run:

```powershell
python scripts\validate_candidate_w_uv_only_change.py `
  --candidate-t-glb work\model_pipeline\candidate_t\downstream\retarget\karin_target_bound_uvopt_v11_grounded_axial_pelvis.glb `
  --candidate-w-glb work\model_pipeline\candidate_w\downstream\retarget\karin_target_bound_priorityuv_purediffuse_v11.glb `
  --candidate-t-compiled-dir work\model_pipeline\candidate_t\downstream\meshes\compiled `
  --candidate-w-compiled-dir work\model_pipeline\candidate_w\downstream\meshes\compiled `
  --output work\reports\candidate_w_v11\candidate_w_uv_only_identity_validation.json `
  --markdown work\reports\candidate_w_v11\candidate_w_uv_only_identity_validation.md
```

The release gate permits changes only to `TEXCOORD_0/1`, requires UV0=UV1,
and requires byte identity for positions, normals, tangents, colors, joints,
weights, indices, topology, inverse-bind matrices, dynamic/influence/
precompute/index buffers, and every non-UV static-stream byte.

### Texture and Forge gates

Encode the runtime PNG as `BC3_UNORM_SRGB` with `-srgbi -srgbo`, a complete
12-level mip chain, and DX10 alpha mode 0. Run the final DDS directly through:

```powershell
python scripts\validate_karin_priority_atlas_mip_v11.py `
  --dds work\model_pipeline\candidate_w\downstream\textures\diffuse_dds\karin_priority_purediffuse_v11_2048_alpha0.dds `
  --manifest work\v1_1\weighted_atlas_v2_purediffuse_priority\priority_atlas_manifest.json `
  --build-state work\v1_1\weighted_atlas_v2_purediffuse_priority\priority_atlas_build_state.json `
  --uv-audit work\v1_1\weighted_atlas_v2_purediffuse_priority\priority_atlas_uv_alpha_sampling_audit.json `
  --report work\reports\candidate_w_v11\priority_atlas_mip_bleed_validation.json `
  --markdown work\reports\candidate_w_v11\priority_atlas_mip_bleed_validation.md
```

LOD 5 is the subtexel-gutter boundary, UV footprints can reach adjacent slots
at LOD 6, unavoidable cross-slot aggregation starts at LOD 9, and LOD 11 is the
global texel. These limits must remain explicit rather than being reported as
full-chain isolation.

Compile the diffuse with Candidate T's exact flat-normal DDS. Reuse reference
Material and specular. Rebuild from the immutable reference Forge, extract it,
and require `725/725` extraction plus `3659/3659` payload checks. Run
`validate_candidate_w_forge_delta.py`; W may differ from T/U only in the two
Mesh IDs and diffuse, while normal must equal T/U and Material/specular must
equal the immutable reference. The accepted Forge is:

`67BD74C98B109BFE9EC7EAFC3C10999724BA1E738860FFBC031C1C4C440100A5`

### Package, publish, and install

Build and verify the six-file staging, then publish the exact bytes:

```powershell
python scripts\build_candidate_w_release.py
python scripts\build_candidate_w_release.py --verify
python scripts\publish_candidate_w_v11.py
python scripts\publish_candidate_w_v11.py --verify
```

The deterministic 1.1 ZIP hash is
`0677F944C49625D972D4B3FD30024803D7024775209EB1E030984C248F7721DE`.
The publisher requires the superseded Candidate U 1.1 distribution backup,
allows exactly six release files, and proves that `dist/Karin_Playable_1.0`
did not change.

Install only after `ACBlackFlag.exe` is absent:

```powershell
python scripts\install_candidate_w_v11.py --install
python scripts\install_candidate_w_v11.py --verify-installed
```

At that historical stage the installer required the game Forge to be pinned Candidate U
`68D09380...F09465`, creates a verified external rollback, checks the process
again immediately before replacement, atomically installs the dist Forge, and
writes `INSTALLATION_RECORD.json`. Do not kill a user's active game session to
make this gate pass.

Candidate W later received targeted runtime observation in Duncan Walpole's
Robes. It confirmed the corrected pelvis/shorts and pure-diffuse direction, but
also exposed slight shoe penetration and strong hair/face plus clothing/pants
contact shadows. Candidate X below is the isolated follow-up. Any remaining
unchecked movement, cutscene, save/reload, or distance/LOD rows stay pending;
offline renders and structural validators do not establish runtime acceptance.

## Stage 10 - Candidate X ground and screen-space-shadow trial

Candidate X is a runtime-only derivative of Candidate W. It addresses two
observations independently inside one test Forge: a slight shoe-ground
penetration caused by Candidate T/W's lower rest minimum, and overly strong
hair/face plus clothing/pants contact shadows. Do not publish X or overwrite the
Candidate W distribution until both behaviors are directly observed.

### Local ground correction

Build only from Candidate W's target-bound GLB. The fixed correction is
`groundDelta = 0.002123795449733734 m`, derived from W/T minimum Y
`-82.070983946 mm` versus Candidate R/S `-79.947188497 mm`. Apply it only to
the source ClothA/ClothB segments using:

```text
deltaY = groundDelta
       * smoothstep(0.50, 0.95, FootWeight)
       * (1 - smoothstep(-0.050, 0.030, y))
```

`FootWeight` is the summed Foot/FootThumb influence for the relevant side.
Never move the Skeleton, root, Hips, Foot/Toe pivots, inverse-bind matrices, or
all vertices to solve this issue. Build and validate:

```powershell
python scripts\build_candidate_x_groundfix.py
python scripts\validate_candidate_x_groundfix.py
```

The validator must pass UV, normal, tangent, color, joint, weight, IBM,
topology, and index identity against W. Static non-position bytes and the
influence/precompute/index buffers must remain exact W. The accepted compiled
change affects only quantized position Y in 1,896 and 317 vertices of Mesh
`0x81786E922F` and `0x9611D6CEAE`; the first Mesh minimum code returns from
`-1345` to the R/S value `-1310`. Require robust local edge ratio at least
`0.95`, displacement-neighbor jump at most `1.0 mm`, and maximum face-normal
change below `2 degrees`.

### Screen-space shadow isolation

The diffuse uses original source diffuse only, the normal is flat BC5 SNORM,
and COLOR_0/COLOR_1 contain no spatial AO. Do not brighten diffuse, restore
emissive, or alter SpecGloss to hide the shadows.

The narrow first test is compact Material flag 14,
`IsExcludedFromScreenSpaceShadows=1`. Generate it structurally:

```powershell
python scripts\build_candidate_x_screen_space_shadow_material.py
```

Require the immutable 589-byte Material SHA-256
`D3D093F430E0BE2140B8835F45C0FBC55756A4E32F41E2F6305DD3D44D35F9D2`
as input, a 589-byte output, and exactly one byte delta at absolute offset
`0x67`, `00 -> 01`. The output SHA-256 is
`BC7AA3DCFB6D9E16FCA9CD402526655357BDF4B51BA1FFCD4BC7500E6DD15616`.
Keep `ShadowCasterOpaque=1` so the ground shadow is expected to remain. If flag
14 is inert, build a separate fallback with either Material
`ShadowCasterOpaque=0` or Mesh `ShadowCaster=false`; do not combine either
fallback with X or with each other in the first comparison.

### Forge and installation gate

Rebuild from the immutable reference Forge with exactly five declared
replacements: both X Meshes, the X Material, Candidate W diffuse, and Candidate
W flat normal. Preserve Candidate W/reference specular. Independently extract
and require `725/725`; strict payload validation must pass `3670/3670`. Then
run the W-to-X delta validator:

```powershell
python scripts\validate_candidate_x_forge_delta.py
```

It must prove that X differs from W only in the two Meshes and Material, while
diffuse, normal, specular, and all nine unrelated decoded resources are exact.
The accepted runtime Forge SHA-256 is
`11D1AEDC5AE75365136D82D239A4A679F642B11DB581B38E5F33868707D2730A`.

Install only through the pinned script while the game is closed:

```powershell
python scripts\install_candidate_x_v11.py --install
python scripts\install_candidate_x_v11.py --verify-installed
```

The installer requires Candidate W at `67BD74C9...100A5`, creates a
non-overwritable byte-exact W backup, checks the game process twice, performs a
same-directory atomic replace, and writes an installation record. Candidate X
was installed and verified on 2026-07-25 with runtime status
`PENDING_USER_TEST`.

Runtime comparison must cover both feet at idle, walk/run, slopes, stairs,
jump/landing, and crouch; then compare hair/face and jacket/pants contact shadow
under matched sun and shade. Confirm both that the dirty-looking contact bands
are reduced and that the normal ground shadow remains. A visually inert flag or
a missing ground shadow is a failed hypothesis, not a partial acceptance.

### Candidate X runtime result and postmortem

Candidate X is rejected by direct runtime observation. Its feet still entered
the ground and its hair-to-face shadow remained strong. Preserve its Forge,
reports, installation record, and W rollback as historical evidence, but do not
publish X or reuse its two hypotheses.

The `+2.123795449733734 mm` correction matched Candidate R/S's historical rest
minimum, not the target game's authoritative footwear contact surface. The
measured Candidate W-to-Carl contact difference is approximately 79.69 mm, so
the X correction was insufficient by approximately `77.566745 mm`.

Candidate X's one-field shadow experiment was visually inert, but the former
postmortem assignment of flag 14 to `IsAtlasMaterial` is superseded. Native
Build 24424450 descriptor access values later proved that absolute offset
`0x67` is `IsExcludedFromScreenSpaceShadows`; `IsAtlasMaterial` is at `0x68`.
X changed only the screen-space exclusion flag while the Material opaque-caster
and Mesh caster paths remained enabled, so its runtime result does not isolate
the field identity. Keep X rejected as a runtime candidate, but use the native
descriptor map in Stage 20 for all subsequent BFR Material work.

## Stage 11 - Candidate Y reference foot-fit and selective shadow

Candidate Y starts from clean Candidate W and replaces exactly two Mesh
resources. It reuses W's pure-diffuse TextureMap and flat normal, and preserves
the immutable reference Material and specular. It is an installation/runtime
candidate only; do not overwrite `dist/Karin_Playable_1.1` before direct game
acceptance.

### Reference-calibrated hybrid footwear

Carl's compiled global footwear contact minimum is
`-0.002380443739127781 m`; Candidate W's is
`-0.0820709839463234 m`. Use their exact difference:

```text
groundCorrectionY = +0.07969054020719561 m
```

Classify connected ClothA/ClothB components. A component is rigid footwear when
`maxY <= 0.160 m` and its maximum Foot/FootThumb weight exceeds 0.50. Translate
the complete rigid component by the constant correction so its local shape and
vertex frame remain exact. For other active lower-chain cloth, use:

```text
deltaY = groundCorrectionY
       * smoothstep(0, 0.001, LowerChainWeight)
       * (1 - smoothstep(0.050, 0.650, y))
```

Update falloff normals with the analytic inverse-transpose and tangents with the
forward local Y scale, then re-orthogonalize while preserving handedness. Never
move the Skeleton, rest pivots, inverse-bind matrices, or weights for this fit.

Rebuild and independently validate the non-reversed GLB:

```powershell
python scripts\build_candidate_y_hybrid_footfit.py
python scripts\validate_candidate_y_hybrid_footfit.py
```

The required output is
`work/model_pipeline/candidate_y/footfit/karin_target_bound_priorityuv_purediffuse_v11_hybrid_footfit.glb`,
SHA-256
`1579A87603FE009599EA76DF72240F94ACE08B316F3D46364384C0426E072214`.
The build and independent validation reports are
`work/reports/candidate_y_v11/candidate_y_footfit_build.json` and
`work/reports/candidate_y_v11/candidate_y_footfit_validation.json`. Require a
global minimum of `-2.380444 mm`, no face flips, no unauthorized attribute
changes, and exact rigid-component frame preservation.

Build the game-facing winding variant and its single-primitive baseline:

```powershell
python scripts\build_karin_reversed_winding_variant.py `
  --input work\model_pipeline\candidate_y\footfit\karin_target_bound_priorityuv_purediffuse_v11_hybrid_footfit.glb `
  --output work\model_pipeline\candidate_y\footfit\karin_target_bound_priorityuv_purediffuse_v11_hybrid_footfit_reversed.glb `
  --report work\reports\candidate_y_v11\candidate_y_footfit_winding_contract.json `
  --expected-input-sha256 1579A87603FE009599EA76DF72240F94ACE08B316F3D46364384C0426E072214

python scripts\build_bfr_meshes_from_glb.py `
  --candidate work\model_pipeline\candidate_y\footfit\karin_target_bound_priorityuv_purediffuse_v11_hybrid_footfit_reversed.glb `
  --output-dir work\model_pipeline\candidate_y\footfit\compiled_single `
  --allow-expand-extents
```

The reversed GLB must hash to
`E784436170967255E8FB5731208B8B0D2DE616E8AC688E7E35BEB22D9DA0C8C4`.

### Selective per-primitive caster split

Do not disable casting globally in the Material. Split each target Mesh into
two primitives that repeat Material `0x000000BAC7CA10D9` and UV density 8.0:

- caster `true`: Body, Face, footwear, accessories, and other non-Hair/non-Cloth
  source segments;
- caster `false`: Hair, HairTransparent, and non-footwear ClothA/ClothB
  connected components.

Build the split and patch only the second serialized
`MeshInstancingData.shadow_caster` byte per Mesh:

```powershell
python scripts\build_candidate_y_selective_shadow.py
```

The authoritative report is
`work/reports/candidate_y_v11/candidate_y_selective_shadow_build.json`; require
59,368 exact vertex records, the exact 88,512 oriented-triangle multiset, two
non-empty primitives per Mesh, caster flags `[true, false]`, repeated reference
Material IDs, and no new resources. The final Mesh resources are:

- `work/model_pipeline/candidate_y/selective_shadow/compiled/asset_009_00000081786E922F.compiled.bin`,
  SHA-256 `4900455B671BDF33A82B2219F1FB06D01AD2B982F1778BCB7D329414F75378FB`;
- `work/model_pipeline/candidate_y/selective_shadow/compiled/asset_010_0000009611D6CEAE.compiled.bin`,
  SHA-256 `B0C619425FECE6AF60AFFA29556D219C0EDDF85EDCF2C5C02B5F201F7C1151BE`.

### Offline preview gate

Render the validated non-reversed foot-fit GLB, not the game-winding split GLB.
The exact Blender commands and input hashes are recorded in
`work/reports/candidate_y_v11/offline_preview_workflow_audit.md`. Require:

- `work/reports/candidate_y_v11/offline_preview/manifest.json` to pass the
  two-Mesh, 759-bone, 59,368-vertex, 88,512-triangle import contract and all
  three nonblank views;
- `work/reports/candidate_y_v11/offline_preview_foot_contact/manifest.json` to
  use Carl's fixed `-0.002380443737 m` datum, remain within 0.5 mm, and pass all
  four nonblank foot views.

The fixed preview measured Candidate Y only `-0.000112 mm` from Carl. This is a
static geometry gate, not evidence for animation, terrain, IK, or in-game
shadow behavior.

### Forge rebuild and strict validation

Rebuild from the immutable reference Forge with exactly four replacements: the
two selective-shadow Meshes, Candidate W diffuse, and Candidate W flat normal.
Do not replace Material or specular.

```powershell
python scripts\rebuild_forge_v50_patch.py `
  --input work\reference_extraction\input\DataPC_boot_patch_02.forge `
  --output work\package\karin_candidate_y_v11_footfit_selective_shadow\DataPC_boot_patch_02.forge `
  --report work\reports\candidate_y_v11\candidate_y_forge_rebuild.json `
  --replace 0x00000081786E922F=work\model_pipeline\candidate_y\selective_shadow\compiled\asset_009_00000081786E922F.compiled.bin `
  --replace 0x0000009611D6CEAE=work\model_pipeline\candidate_y\selective_shadow\compiled\asset_010_0000009611D6CEAE.compiled.bin `
  --replace 0x000000BAC7CA10DA=work\model_pipeline\candidate_w\downstream\textures\compiled\resources\asset_007_000000BAC7CA10DA.bin `
  --replace 0x000000BAC7CA10DB=work\model_pipeline\candidate_w\downstream\textures\compiled\resources\asset_006_000000BAC7CA10DB.bin

Copy-Item `
  work\package\karin_candidate_y_v11_footfit_selective_shadow\DataPC_boot_patch_02.forge `
  work\reference_extraction\candidate_y_v11\DataPC_boot_patch_02.forge

python scripts\extract_forge_v50_bms.py `
  work\reference_extraction\candidate_y_v11\DataPC_boot_patch_02.forge `
  --output-root work\reference_extraction\candidate_y_v11\extracted `
  --json-output work\reports\candidate_y_v11\candidate_y_extraction.json `
  --markdown-output work\reports\candidate_y_v11\candidate_y_extraction.md
```

Validate the four replacements while explicitly preserving Material and
specular, then run the pinned semantic delta gate:

```powershell
python scripts\validate_final_forge_payload.py `
  --reference-report work\reports\reference_forge_v50_bms_extraction.json `
  --final-report work\reports\candidate_y_v11\candidate_y_extraction.json `
  --reference-root work\reference_extraction\decoded_bms `
  --final-root work\reference_extraction\candidate_y_v11\extracted `
  --replacement 0x00000081786E922F=work\model_pipeline\candidate_y\selective_shadow\compiled\asset_009_00000081786E922F.compiled.bin `
  --replacement 0x0000009611D6CEAE=work\model_pipeline\candidate_y\selective_shadow\compiled\asset_010_0000009611D6CEAE.compiled.bin `
  --replacement 0x000000BAC7CA10DA=work\model_pipeline\candidate_w\downstream\textures\compiled\resources\asset_007_000000BAC7CA10DA.bin `
  --replacement 0x000000BAC7CA10DB=work\model_pipeline\candidate_w\downstream\textures\compiled\resources\asset_006_000000BAC7CA10DB.bin `
  --preserve 0x000000BAC7CA10D9 `
  --preserve 0x000000BAC7CA10DC `
  --package work\package\karin_candidate_y_v11_footfit_selective_shadow\DataPC_boot_patch_02.forge `
  --rebuild-report work\reports\candidate_y_v11\candidate_y_forge_rebuild.json `
  --json-output work\reports\candidate_y_v11\candidate_y_final_forge_payload_validation.json `
  --markdown-output work\reports\candidate_y_v11\candidate_y_final_forge_payload_validation.md

python scripts\validate_candidate_y_forge_delta.py `
  --candidate-y-forge-sha256 D718883A89C1336610E98798604EA5EB6D9A0DBA03B8620261E634FB921566A1 `
  --candidate-y-mesh-sha256 0x00000081786E922F=4900455B671BDF33A82B2219F1FB06D01AD2B982F1778BCB7D329414F75378FB `
  --candidate-y-mesh-sha256 0x0000009611D6CEAE=B0C619425FECE6AF60AFFA29556D219C0EDDF85EDCF2C5C02B5F201F7C1151BE
```

The final Forge SHA-256 is
`D718883A89C1336610E98798604EA5EB6D9A0DBA03B8620261E634FB921566A1`.
Require extraction `725/725`, payload `3659/3659`, and
`work/reports/candidate_y_v11/candidate_y_forge_delta_validation.json` status
`PASS`. Relative to W, only the two Meshes may differ. Relative to the immutable
reference, exactly the two Meshes, diffuse, and flat normal may differ.

### Installation and runtime gate

Install and verify only through the pinned fail-closed script while
`ACBlackFlag.exe` is absent:

```powershell
python scripts\install_candidate_y_v11.py --preflight-only
python scripts\install_candidate_y_v11.py --install
python scripts\install_candidate_y_v11.py --verify-installed
```

The 2026-07-25 install passed both process checks, created a non-overwritable
byte-exact X backup, performed a same-directory atomic replace, and verified the
installed Forge as `D718883A...566A1`. Its installation record is
`work/runtime_backups/2026-07-25_pre_candidate_y_11D1AEDC/INSTALLATION_RECORD.json`.
This establishes installation integrity only; do not claim visual success from
the install, offline preview, or structural reports.

Runtime acceptance must separately prove: both feet at idle and through
locomotion/terrain transitions; no hover after the larger correction;
hair-to-face and clothing contact-shadow reduction in matched sun/shade views;
and preservation of the character's normal ground shadow. Keep all rows
`NOT_TESTED` until direct evidence exists.

### Candidate Y runtime result and postmortem

Candidate Y is runtime-rejected. The user confirmed that its shoe-ground height
was correct, so retain the hybrid foot-fit GLB and its single-primitive compiled
Meshes. The same runtime screenshot showed severe stretching and corruption in
the hair and cloth surfaces. Preserve the evidence at:

- `work/reports/candidate_y_v11/runtime_rejection/candidate_y_two_primitive_corruption.png`;
- `work/reports/candidate_y_v11/runtime_rejection/candidate_y_runtime_rejection.json`;
- `work/reports/candidate_y_v11/runtime_rejection/candidate_y_runtime_rejection.md`.

The corrupted regions match the second primitive of each Mesh. Those primitives
reset their compact indices to a local zero-based range and depended on
`min_index` as a base vertex. The offline parser reconstructed them with that
base and therefore passed clustered surface checks. The game runtime did not
apply the offline-assumed base vertex. Consequently, the second primitives
indexed unrelated vertices and stretched across the character.

Do not reuse Candidate Y's two-primitive layout, even if the same Material,
triangle multiset, and offline geometry checks pass. This result does not reject
the foot-fit geometry; it rejects the unproven compact Mesh primitive/index
contract. Candidate Y Forge `D718883A...566A1` remains historical evidence only.

## Stage 12 - Candidate Z single-primitive foot-fit and Mesh1 caster trial

Candidate Z preserves Candidate Y's validated foot-fit geometry and returns
both target Mesh resources to exactly one primitive. Mesh0 remains a caster.
Mesh1 disables only its existing `MeshInstancingData.shadow_caster` field. This
is a runtime-only trial and must not replace `dist/Karin_Playable_1.1` before
direct visual acceptance.

### Single-primitive Mesh build

Build from Y's pinned `compiled_single` resources:

```powershell
python scripts\build_candidate_z_mesh1_shadow_hotfix.py
```

Require `work/reports/candidate_z_v11/candidate_z_mesh1_shadow_hotfix_build.json`
status `PASS` and its Markdown companion. The outputs are:

- `work/model_pipeline/candidate_z/mesh_hotfix/compiled/asset_009_00000081786E922F.compiled.bin`,
  SHA-256 `0D6142EBCEADF132E468D24F803F0B6043E89A3D83BE43E696CCEA2336A55028`;
- `work/model_pipeline/candidate_z/mesh_hotfix/compiled/asset_010_0000009611D6CEAE.compiled.bin`,
  SHA-256 `608A3F1E3BC65002B11649C2A6DC9E43B37E16FF984841C2AE63F8ADE0814BFA`.

Mesh0 must be byte-identical to Y's single-primitive foot-fit baseline. Mesh1
must differ from its baseline at exactly offset `0x1AB8BE`, where
`shadow_caster` changes from `1` to `0`. Primitive counts remain one; every
geometry buffer, primitive-table field, Material reference, UV density, bone,
extent, and other parsed field remains exact.

### Forge rebuild and validation

Rebuild from the immutable reference Forge with exactly the two Z Meshes,
Candidate W diffuse, and Candidate W flat normal. Preserve reference Material
and specular:

```powershell
python scripts\rebuild_forge_v50_patch.py `
  --input work\reference_extraction\input\DataPC_boot_patch_02.forge `
  --output work\package\karin_candidate_z_v11_footfit_mesh1_shadow_off\DataPC_boot_patch_02.forge `
  --report work\reports\candidate_z_v11\candidate_z_forge_rebuild.json `
  --replace 0x00000081786E922F=work\model_pipeline\candidate_z\mesh_hotfix\compiled\asset_009_00000081786E922F.compiled.bin `
  --replace 0x0000009611D6CEAE=work\model_pipeline\candidate_z\mesh_hotfix\compiled\asset_010_0000009611D6CEAE.compiled.bin `
  --replace 0x000000BAC7CA10DA=work\model_pipeline\candidate_w\downstream\textures\compiled\resources\asset_007_000000BAC7CA10DA.bin `
  --replace 0x000000BAC7CA10DB=work\model_pipeline\candidate_w\downstream\textures\compiled\resources\asset_006_000000BAC7CA10DB.bin

Copy-Item `
  work\package\karin_candidate_z_v11_footfit_mesh1_shadow_off\DataPC_boot_patch_02.forge `
  work\reference_extraction\candidate_z_v11\DataPC_boot_patch_02.forge

python scripts\extract_forge_v50_bms.py `
  work\reference_extraction\candidate_z_v11\DataPC_boot_patch_02.forge `
  --output-root work\reference_extraction\candidate_z_v11\extracted `
  --json-output work\reports\candidate_z_v11\candidate_z_extraction.json `
  --markdown-output work\reports\candidate_z_v11\candidate_z_extraction.md
```

Run the generic payload gate and the Z-specific semantic delta gate:

```powershell
python scripts\validate_final_forge_payload.py `
  --reference-report work\reports\reference_forge_v50_bms_extraction.json `
  --final-report work\reports\candidate_z_v11\candidate_z_extraction.json `
  --reference-root work\reference_extraction\decoded_bms `
  --final-root work\reference_extraction\candidate_z_v11\extracted `
  --replacement 0x00000081786E922F=work\model_pipeline\candidate_z\mesh_hotfix\compiled\asset_009_00000081786E922F.compiled.bin `
  --replacement 0x0000009611D6CEAE=work\model_pipeline\candidate_z\mesh_hotfix\compiled\asset_010_0000009611D6CEAE.compiled.bin `
  --replacement 0x000000BAC7CA10DA=work\model_pipeline\candidate_w\downstream\textures\compiled\resources\asset_007_000000BAC7CA10DA.bin `
  --replacement 0x000000BAC7CA10DB=work\model_pipeline\candidate_w\downstream\textures\compiled\resources\asset_006_000000BAC7CA10DB.bin `
  --preserve 0x000000BAC7CA10D9 `
  --preserve 0x000000BAC7CA10DC `
  --package work\package\karin_candidate_z_v11_footfit_mesh1_shadow_off\DataPC_boot_patch_02.forge `
  --rebuild-report work\reports\candidate_z_v11\candidate_z_forge_rebuild.json `
  --json-output work\reports\candidate_z_v11\candidate_z_final_forge_payload_validation.json `
  --markdown-output work\reports\candidate_z_v11\candidate_z_final_forge_payload_validation.md

python scripts\validate_candidate_z_forge_delta.py `
  --candidate-z-forge-sha256 4CABB89854EC376AEA1C1E470DDC793D38C64806B4CB8A5CCE6B641AFB0FF942 `
  --candidate-z-mesh-sha256 0x00000081786E922F=0D6142EBCEADF132E468D24F803F0B6043E89A3D83BE43E696CCEA2336A55028 `
  --candidate-z-mesh-sha256 0x0000009611D6CEAE=608A3F1E3BC65002B11649C2A6DC9E43B37E16FF984841C2AE63F8ADE0814BFA
```

The final Forge SHA-256 is
`4CABB89854EC376AEA1C1E470DDC793D38C64806B4CB8A5CCE6B641AFB0FF942`.
Require extraction `725/725`, payload `3659/3659`, and
`work/reports/candidate_z_v11/candidate_z_forge_delta_validation.json` status
`PASS`. The complete report set is under `work/reports/candidate_z_v11/`.

### Installation and runtime gate

Install only through the pinned script while `ACBlackFlag.exe` is absent:

```powershell
python scripts\install_candidate_z_v11.py --preflight-only
python scripts\install_candidate_z_v11.py --install
python scripts\install_candidate_z_v11.py --verify-installed
```

The 2026-07-25 install passed two independent process checks, verified and
backed up the exact Y Forge before replacement, installed Z atomically, and
read back SHA-256 `4CABB898...FF942`. The backup and installation record are:

- `work/runtime_backups/2026-07-25_pre_candidate_z_D718883A/DataPC_boot_patch_02.candidate_y_D718883A.forge`;
- `work/runtime_backups/2026-07-25_pre_candidate_z_D718883A/INSTALLATION_RECORD.json`.

Candidate Z was directly observed in game. It retained Y's correct shoe-ground
height and removed the Y-style whole-character stretching by restoring the
supported one-primitive layout. Later bent-leg poses exposed skin through both
leg assemblies, most clearly at the left short sock. The head also remained
vertically compressed: the neck looked too short and the chin repeatedly
intersected the collar. These runtime observations supersede the earlier
`PENDING_USER_TEST` status. Z remains valid rollback evidence, but it is not the
accepted geometry endpoint. It never replaced `dist/Karin_Playable_1.1`.

## Stage 13 - Candidate AF leg relief and Candidate AI safe head/neck lift

Candidate AF is the offline leg/sock repair authority. Candidate AI inherits
AF byte-for-byte outside its bounded head/collar position field and is the
installed runtime trial. Installation and offline QA do not constitute game
visual acceptance, and neither candidate may replace the Candidate W 1.1
distribution before the runtime matrix below is observed.

### AF and AI geometry authority

Candidate AF's canonical GLB is:

- `work/model_pipeline/candidate_af/sock11218_local_relief/karin_target_bound_priorityuv_purediffuse_v11_sock11218_local_relief.glb`;
- SHA-256 `97E163B5F7EA8380E6B594208674BC3028FCF911235C1E816B93043500FEF233`.

AF repairs the Z-derived bent-leg sock/skin coverage while preserving the
accepted shoe-ground geometry. Its Blender pose QA passes, but AF was never
installed and must never be called a runtime pass.

Build and validate the strict head/collar family from AF with the pinned local
scripts and dependencies:

```powershell
$candidatePy = '<steam-library>\steamapps\common\Blender\4.2\python\bin\python.exe'
& $candidatePy scripts\build_candidate_ah_safe_head_lift.py
& $candidatePy scripts\validate_candidate_ah_safe_head_lift.py
& $candidatePy scripts\build_candidate_ah_safe_head_lift.py `
  --output-root work\model_pipeline\candidate_ai\strict_safe_spatial_head_lift `
  --report work\reports\candidate_ai_v11\candidate_ai_strict_safe_spatial_head_lift_build.json `
  --markdown work\reports\candidate_ai_v11\candidate_ai_strict_safe_spatial_head_lift_build.md
& $candidatePy scripts\summarize_candidate_ai_head_collar_dynamic_qa.py
```

The build reports pin that Blender Python runtime and NumPy 1.24.3. A fresh
rebuild changes timestamped report bytes, so rebuild into a new checkpoint and
re-pin validators/manifests instead of overwriting an accepted evidence set.

The canonical AI output is:

- `work/model_pipeline/candidate_ai/strict_safe_spatial_head_lift/karin_target_bound_priorityuv_purediffuse_v11_headlift_040mm_spatialellipse_collar060.glb`;
- SHA-256 `9EEB1BED16E7CE89324BF3C9C7AFB83AB5B969EA0D3B30CA7CE801625D440B55`.

The strict geometry policy is:

1. translate every complete Head-driven connected component upward by 40 mm;
2. translate the affected collar assembly rigidly by 24 mm, or 0.60 of the
   head lift, leaving a net 16 mm head/collar separation change;
3. blend only the Body neck transition with the pinned spatial ellipse:
   `y_zero=1.470 m`, `y_full=1.560 m`, `xScale=0.080 m`,
   `zScale=0.055 m`, `zCenter=-0.008 m`, radial inner/outer `1.1/2.4`;
4. preserve AF UVs, normals, tangents, colors, joints, weights, indices,
   skeleton/IBMs, leg repair, foot height, and all non-position attributes.

The measured static chin/collar clearance is 13.297139 mm, inside the source
preferred range of 11.9-15.4 mm. Independent builders produced byte-identical
GLBs. No face flips or new degenerate triangles were introduced. Two local
collar-weight variants (`0.35/0.15` and `0.55/0.25`) increased total dynamic
intersections and are rejected; canonical AI retains the accepted weights.

Dynamic collar QA is
`work/reports/candidate_ai_v11/final_head_collar_dynamic_qa/candidate_ai_head_collar_dynamic_qa_summary.json`,
SHA-256 `6C800E0D847EFF43D12E2B3A31756F6C990F6D8282F4E0AEBA0CB5B7ADAD5700`.
Across rest, pitch, combined neck/head, and both yaw directions, total collision
pairs improve from AF to AI: `129->0`, `313->137`, `315->130`, `276->96`,
and `281->105`. Component 87 starts AF rest with 19 static crossings and AI
with zero; the generic own-rest-normalized comparator therefore flags that
component even though absolute pairs improve or do not regress (`19->0`,
`7->4`, `7->5`, `4->4`, `4->4`). This warning is recorded, not waived.

Manual head/neck review passes all seven fixed views in
`work/reports/candidate_ai_v11/candidate_ai_head_neck_visual_acceptance.json`,
SHA-256 `F8836E6126D3E7E6301EA8B83DEE590EF06BD3B95EBABC21610F55C60DC0953C`.
Manual bent-leg review passes both sides with zero critical inside-body samples
and zero ground penetration in
`work/reports/candidate_ai_v11/candidate_ai_bent_leg_visual_acceptance.json`,
SHA-256 `44F07A8E0575A2B3946F4CE2CE58775AEB510903C6AC7BB77B39DCE7323554CA`.
These are Blender acceptances only.

### Runtime Mesh compilation

Reverse triangle winding and compile against Candidate Z's single-primitive
templates. The final compile uses an explicit common position quantization
factor of 2.02 and deliberately omits `--allow-expand-extents`:

```powershell
python scripts\build_bfr_meshes_from_glb.py `
  --candidate work\model_pipeline\candidate_ai\runtime_meshes\karin_candidate_ai_reversed_winding.glb `
  --templates `
    work\model_pipeline\candidate_z\mesh_hotfix\compiled\asset_009_00000081786E922F.compiled.bin `
    work\model_pipeline\candidate_z\mesh_hotfix\compiled\asset_010_0000009611D6CEAE.compiled.bin `
  --output-dir work\model_pipeline\candidate_ai\runtime_meshes\compiled `
  --quantization-factor 2.02

python scripts\validate_candidate_ai_runtime_meshes.py
```

The reversed GLB is
`work/model_pipeline/candidate_ai/runtime_meshes/karin_candidate_ai_reversed_winding.glb`,
SHA-256 `BE505B945F495D2259963E7E3B60423A4697AF88902A3E2D83534B6C56103647`.
The compiled resources are:

- Mesh0 `asset_009_00000081786E922F.compiled.bin`, SHA-256
  `069E8445DD496E43C7C397E8AF46E85140ED064A739FE991F6B106389C2E9A09`;
- Mesh1 `asset_010_0000009611D6CEAE.compiled.bin`, SHA-256
  `7455EC9927E6A638E250B4D0101AB2535D072EF7E4C8E468BDCA76F2BFBC68BE`.

Both Meshes have exactly one primitive. Mesh0 remains a caster and Mesh1
remains non-casting. The 32-byte local extent records are exact Candidate Z
bytes. The 2.02 factor is required because AI exceeds the original 2.0 m
position range; margins are 1.552105 mm and 8.838415 mm, with maximum component
errors of 0.030833368 mm and 0.030822329 mm. The compiler's omitted-option
default remains 2.0 and its identity regression passes.

### Forge rebuild and independent audit

Run the fail-closed Candidate AI pipeline with the compiled artifact pins:

```powershell
python scripts\build_candidate_ai_forge_pipeline.py forge --execute `
  --expected-mesh0-sha256 069E8445DD496E43C7C397E8AF46E85140ED064A739FE991F6B106389C2E9A09 `
  --expected-mesh1-sha256 7455EC9927E6A638E250B4D0101AB2535D072EF7E4C8E468BDCA76F2BFBC68BE `
  --expected-compile-contract-sha256 8147C462E5E0BDB4A2893BD8FECD91D3189A1ABD8DE9C3A9C8261CE5413C5C82
```

The final Forge is
`work/package/karin_candidate_ai_v11_head_neck_legfix/DataPC_boot_patch_02.forge`,
4,096,000 bytes, SHA-256
`09617257D84F030B1A4D6A97404657C262F31FF676D99E38D268F010031579A4`.
Its staged copy under `work/reference_extraction/candidate_ai_v11/` is
byte-identical. Independent extraction passes `725/725`; strict payload
validation passes `3659/3659`; the AI delta gate passes. Relative to Z, only
Mesh0 and Mesh1 change. Relative to the immutable reference, only those two
Meshes, Candidate W pure diffuse, and Candidate W flat normal change. Reference
Material and specular remain exact.

The first Forge attempt also produced the final Forge bytes but invoked the
generic payload validator without explicit reference/final roots, so it emitted
only `3657/3657` and lacked two path-binding checks. It was not install-authorized
and is quarantined under
`work/quarantine/candidate_ai_forge_attempt_2026-07-26_payload3657/` with
`QUARANTINE_REASON.md`. Do not use its incomplete report as release evidence.
The corrected report set and release manifest are under
`work/reports/candidate_ai_v11/runtime_forge/`.

### Installation and runtime gate

Install only when the current game file is exact Candidate Z and the game is
closed:

```powershell
$aiForge = '09617257D84F030B1A4D6A97404657C262F31FF676D99E38D268F010031579A4'
$aiManifest = 'F47E2F5A58A464ADD9EB96537CA3AB8BDB63785F2B94AC98EF4092D793CA3667'
python scripts\install_candidate_ai_v11.py --preflight-only `
  --target-forge-sha256 $aiForge --release-manifest-sha256 $aiManifest
python scripts\install_candidate_ai_v11.py --install --execute-install `
  --target-forge-sha256 $aiForge --release-manifest-sha256 $aiManifest
python scripts\install_candidate_ai_v11.py --verify-installed `
  --target-forge-sha256 $aiForge --release-manifest-sha256 $aiManifest
```

Historical Candidate AI transaction: the 2026-07-26 transaction passed two
game-process checks, verified then-current Z
SHA-256 `4CABB898...FF942`, made a byte-exact backup, installed AI atomically,
and read back SHA-256 `09617257...579A4`. The record and rollback are:

- `work/runtime_backups/2026-07-26_pre_candidate_ai_4CABB898/INSTALLATION_RECORD.json`;
- `work/runtime_backups/2026-07-26_pre_candidate_ai_4CABB898/DataPC_boot_patch_02.candidate_z_4CABB898.forge`.

Historical install status is `PASS`; runtime visual status remained
`PENDING_USER_TEST` before AJ superseded AI. Do not launch the game
automatically. The user test matrix for this inherited payload is:

1. seated, crouched, and deep-knee poses for both sock assemblies and exposed
   skin, especially the left short sock;
2. both shoe soles during idle, locomotion, slopes, stairs, jump, and landing;
3. rest, pitched, and left/right-yawed head poses for neck length,
   chin/collar clearance, shoulder transition, and accessory seams;
4. hair/face and clothing self-shadow, Mesh0 ground-shadow silhouette, and
   Mesh1 hair/cloth stability;
5. near/far camera and LOD/culling behavior after q=2.02 with unchanged extents;
6. walking, running, climbing, combat, swimming, cutscenes, seated animation,
   and save/reload.

Candidate AI remained outside `dist/` at this checkpoint. It later became the
byte-exact payload base for Candidate AJ / version 1.5; never replace only the
Forge inside an existing release directory.

## Rollback and checkpoints

The current rollback is the verified Candidate Z Forge at
`work/runtime_backups/2026-07-26_pre_candidate_aj_v15_4CABB898/DataPC_boot_patch_02.candidate_z_4CABB898.forge`,
SHA-256 `4CABB89854EC376AEA1C1E470DDC793D38C64806B4CB8A5CCE6B641AFB0FF942`.
Close the game before restoring it, verify the exact hash after replacement,
and retain the adjacent `INSTALLATION_RECORD.json` as the Candidate AJ audit
trail.

The next historical rollback is the verified Candidate Y Forge at
`work/runtime_backups/2026-07-25_pre_candidate_z_D718883A/DataPC_boot_patch_02.candidate_y_D718883A.forge`,
SHA-256 `D718883A89C1336610E98798604EA5EB6D9A0DBA03B8620261E634FB921566A1`.
Close the game before restoring it, verify the exact hash after replacement,
and retain the adjacent `INSTALLATION_RECORD.json` as the Candidate Z audit
trail. Candidate Y is runtime-rejected and is a rollback artifact, not a release.

The next rollback is the verified Candidate X Forge at
`work/runtime_backups/2026-07-25_pre_candidate_y_11D1AEDC/DataPC_boot_patch_02.candidate_x_11D1AEDC.forge`,
SHA-256 `11D1AEDC5AE75365136D82D239A4A679F642B11DB581B38E5F33868707D2730A`.
Close the game before restoring it, verify the exact hash after replacement,
and retain the adjacent `INSTALLATION_RECORD.json` as the Candidate Y audit
trail.

The following rollback is the verified Candidate W Forge at
`work/runtime_backups/2026-07-25_pre_candidate_x_67BD74C9/DataPC_boot_patch_02.candidate_w_67BD74C9.forge`,
SHA-256 `67BD74C98B109BFE9EC7EAFC3C10999724BA1E738860FFBC031C1C4C440100A5`.
Close the game before restoring it, verify the exact hash after replacement,
and retain `INSTALLATION_RECORD.json` as the Candidate X audit trail.

The historical 1.2 rollback is the verified Candidate U Forge at
`work/runtime_backups/2026-07-24_pre_candidate_v12_68D09380/DataPC_boot_patch_02.candidate_u_68D09380.forge`,
SHA-256 `68D09380FF2DBBFC278319F80579E3469F59F260D2BCFA626E44236058F09465`.
Close the game before restoring it and require that exact hash after the copy.

Candidate U's next historical rollback is the verified Candidate T Forge at
`work/runtime_backups/2026-07-24_pre_candidate_u_8A6C8764/DataPC_boot_patch_02.candidate_t_8A6C8764.forge`,
SHA-256 `8A6C8764A590E58A6002532216433A21DF5EA6F714AF6D1EFB0DE0D2FE81552E`.
Close the game before restoring it and require that exact hash after the copy.

- `work/checkpoints/00_source_audit/`
- `work/checkpoints/10_reference_extracted/`
- `work/checkpoints/20_topology_materials/`
- `work/checkpoints/30_target_bind/`
- `work/checkpoints/40_game_resources/`
- `work/checkpoints/50_final_forge/`

Each checkpoint contains a `MANIFEST.sha256` generated only after files close
successfully in their owning application.

## Stage 14 - Candidate AJ native mouth/teeth suppression and version 1.5

Use this stage when the target body/head replacement still renders Edward's
native teeth or oral attachment outside the replacement face. Do not infer the
resource from the screenshot alone and do not remove a whole head or eye
selector.

### Locate and classify the native resource

1. Query the Black Flag Full File List and reference map for the legacy
   `CHR_Shared_MouthTeethEye_SELECTOR` chain. Treat legacy IDs only as naming
   evidence because Resynced remaps object IDs.
2. Enumerate every `VisualPropertyNodeSolver.TargetGraphicObject` in the
   injected BuildTables, then extract candidate LODSelectors from the installed
   Resynced `DataPC_boot.forge` with the selected-entry extractor.
3. Parse every LOD Mesh, including external dependencies. Require all bounds,
   components, bones and rendered previews to agree with mouth/teeth geometry.
   Reject a selector if it includes eye-height bilateral spheres or any other
   head geometry.

The verified Resynced chain is:

- mouth/teeth LODSelector: `0x00000244130CE35A`;
- embedded LOD Meshes: `0x0000024D485A75F6`, `0x0000024D485A7604`,
  `0x0000024D485A7612`;
- external LOD Meshes: `0x00000244130CE35B`, `0x0000024D485A75E8`;
- Material: `0x0000020D6679DD8D`;
- TextureSet: `0x0000020E8A7D3ABD`.

All five LODs are teeth-only geometry. The separate eye candidate is excluded.
Evidence is under `work/research/v15_selector_material_match/`,
`work/research/v15_native_mesh_preview/`, and
`work/research/v15_teeth_locator/`.

### Apply the fixed-size BuildTable patch

The target is BuildTable `0x00000330557EC362`, 9,047 bytes, source SHA-256
`BF4313A35AF1473D1A60278C7C2FE21C08FD138603D657F348D485B4A74E04F8`.
Its final GraphicObject column contains a `VisualPropertyNodeSolver` whose
layout is:

- solver hash at `0x1FF2`;
- mode at `0x1FF6..0x1FF9`;
- reserved byte at `0x1FFA`, which must remain `00`;
- `TargetGraphicObject` UInt64 at `0x1FFB..0x2002`.

Change only the target UInt64 from little-endian
`5A E3 0C 13 44 02 00 00` to eight zero bytes. Do not change `0x1FFA`, remove
the column, null the whole BuildTable, or touch the four Duncan outfit
selectors. The expected patched SHA-256 is
`2797F19426104AB061DB024ABABFE402AACA4D3DF08E7301C8A53894A3C8DA03`.
The null ClassID is a valid empty target, not a wildcard.

Build and verify from the pinned Candidate AI base:

```powershell
python scripts\build_candidate_aj_v15_teeth_suppression.py --execute-build
python scripts\build_candidate_aj_v15_teeth_suppression.py --verify
```

The build must fail unless the source hash, unique target offset, wrapper,
column count, solver hash, mode, reserved byte and following Mask class all
match. After repacking, require independent extraction `725/725`, AJ validation
`62/62`, identical object order/metadata, and exactly one changed decoded
resource. Both Karin Meshes, all textures/materials, other BuildTables and the
MaterialTemplate must remain byte-identical to Candidate AI.

The accepted AJ Forge is 4,096,000 bytes with SHA-256
`7F7D3D2EAB98F00F60B784074598A5A88249443B781F34FFC3BB78302EAE2E10`.

### Install, publish and roll back

The installer accepts only the pinned Candidate Z game baseline, requires two
closed-game process checks, creates a non-overwriting backup, stages a temporary
file in the game directory, and uses an atomic replacement:

```powershell
python scripts\install_candidate_aj_v15.py --preflight-only
python scripts\install_candidate_aj_v15.py --install --execute-install
python scripts\install_candidate_aj_v15.py --verify-installed
```

The verified rollback is
`work/runtime_backups/2026-07-26_pre_candidate_aj_v15_4CABB898/DataPC_boot_patch_02.candidate_z_4CABB898.forge`,
SHA-256 `4CABB89854EC376AEA1C1E470DDC793D38C64806B4CB8A5CCE6B641AFB0FF942`.
Never launch or terminate the game from the build/install scripts.

Publish and verify the six-file distribution with:

```powershell
python scripts\build_candidate_aj_v15_release.py --publish
python scripts\build_candidate_aj_v15_release.py --verify
```

The release is `dist/Karin_Playable_1.5/` plus its deterministic ZIP, SHA-256
`149444F1585CEECBD44F7D94CDABCBBFD828693F3B932930CE95EAFB215FE70C`.
Its status remains `STRUCTURAL_PASS_RUNTIME_PENDING` until direct tests cover
rest/talking/cutscenes, blink and eye visibility, locomotion, traversal,
combat, sock/leg coverage, shoe contact, and all inherited AI geometry.

## Stage 15 - Candidate AK / Karin Playable 1.5.1

This stage supersedes AJ for Steam BuildID `24424450`. AJ's null BuildTable
target did not suppress the native teeth and its old Forge is incompatible with
the updated executable/patch_01 loader. Keep AJ disabled and archived; do not
use it as a rebuild base or rollback on the current game build.

### Freeze the updated game authority

Require all of the following before compiling or deploying:

- AppID `3751950`, BuildID and TargetBuildID `24424450`;
- `ACBlackFlag.exe`, 478,845,280 bytes,
  `8D52238155C9491F329C0B78AF2D00EE67AB5E03946EEA83E12B061B64B23140`;
- `DataPC_boot.forge`, 25,640,534,016 bytes,
  `144D947BD4B84709B891837C1A49893062AA9B79E2CECAF66C15FD884BC70A00`;
- `DataPC_boot_patch_01.forge`, 1,915,453,440 bytes,
  `D2C0A87FD663C154E837350E8B93A00DF847F6659DC19D4E96BACD84041620D7`.

The unchanged boot Forge keeps the target Karin and native mouth IDs valid.
The updated patch_01 does not override those top-level IDs. Do not infer
runtime compatibility from that alone; the final release remains runtime
pending until the user tests it manually.

### Apply the hidden-chest repair

Build from the pinned Candidate AI authoring GLB:

```powershell
python scripts\build_candidate_ak_chest_hidden_skin_relief.py
```

Only the front Body connected component beginning at vertex 21580 is eligible.
The protected back component and all ClothA bytes must remain unchanged. The
accepted result changes 462 position vertices and 176 weight vertices, with a
maximum `-Z` relief of 1.797855563 mm. Require zero flipped faces, minimum
old/new normal dot at least 0.80, area ratio within 0.75..1.30, edge ratio
within 0.80..1.30, normalized weights, and unchanged topology, UVs, normals,
tangents, colors, indices, and garment payload.

Reverse winding and compile with the Candidate Z single-primitive templates,
the current Skeleton authority, and explicit quantization factor 2.02. The
accepted Mesh outputs are:

- Body `0x00000081786E922F`: `FF4F12DA3C55AAEE465F46CD5DAF3770239CA680DA31DF64210C054487415018`;
- ClothA `0x0000009611D6CEAE`: `7455EC9927E6A638E250B4D0101AB2535D072EF7E4C8E468BDCA76F2BFBC68BE`.

Rebuild Candidate AI by replacing only Body:

```powershell
python scripts\rebuild_forge_v50_patch.py `
  --input work\package\karin_candidate_ai_v11_head_neck_legfix\DataPC_boot_patch_02.forge `
  --output work\package\karin_candidate_ak_v151_chest_base\DataPC_boot_patch_02.forge `
  --report work\reports\candidate_ak_v151\candidate_ak_chest_base_forge_rebuild.json `
  --replace 0x00000081786E922F=work\model_pipeline\candidate_ak\runtime_meshes\compiled\asset_009_00000081786E922F.compiled.bin
```

### Replace all native teeth LODs without invalid targets

Do not modify BuildTable `0x00000330557EC362`, the shared mouth Material, or
the eye selector. Build five compact Mesh resources in which each clustered
triangle `(a,b,c)` becomes `(a,a,a)` and every other byte stays exact:

```powershell
python scripts\build_candidate_ak_native_teeth_degenerate_lods.py
```

Mirror the native resolution topology in the patch layer:

1. top-level selector `0x00000244130CE35A`, type `0x51DC6B80`, with its
   original selector class payload and embedded Meshes `...75F6`, `...7604`,
   and `...7612`;
2. top-level Mesh `0x00000244130CE35B`, type `0x415D9568`;
3. top-level Mesh `0x0000024D485A75E8`, type `0x415D9568`.

```powershell
python scripts\build_candidate_ak_teeth_forge_entries.py `
  --input work\package\karin_candidate_ak_v151_chest_base\DataPC_boot_patch_02.forge `
  --output work\package\karin_candidate_ak_v151_build24424450\DataPC_boot_patch_02.forge `
  --report work\reports\candidate_ak_v151\candidate_ak_final_forge_entries.json
```

The final Forge must be 4,128,768 bytes with SHA-256
`185FDD4A0957A7DC2A19B59577CA688B09D81FFD42A161A40D284A9B48BF9160`.
It contains 12 outer entries, seven typed entries, 21 decoded assets, and 1,212
degenerate teeth triangles across five LODs.

### Release, deployment, and runtime boundary

Run the offline gates and deterministic publisher:

```powershell
python scripts\validate_candidate_ak_v151_release.py
python scripts\build_candidate_ak_v151_release.py --verify
```

The dedicated validator must report exactly 321 `PASS`, one
`EXPECTED_DEGENERATE`, zero `FAIL`, and 322 total. The expected item is the
generic Mesh auditor deliberately rejecting degenerate triangles; it is valid
only when all five fixed Mesh IDs, exact index windows, hashes, and 1,212
triangle triples match. Any other generic-audit error is fatal.

Deployment is file-only and fail-closed:

```powershell
python scripts\install_candidate_ak_v151.py --preflight-only
python scripts\install_candidate_ak_v151.py --install --execute-install
python scripts\install_candidate_ak_v151.py --verify-installed
```

The installer may query whether `ACBlackFlag` is running, hash files, create a
non-overwriting backup, stage a temporary Forge, atomically rename it, and read
it back. It must never start, control, send input to, or terminate the game.
The old 1.5 Forge remains disabled and is copied into the installation evidence
directory, but is explicitly not a rollback for BuildID `24424450`.

Publish only `dist/Karin_Playable_1.5.1/` and its deterministic ZIP. ZIP
SHA-256 is
`11EB2C204C20A758F6868B72E25DE863498061B7922246DA9C7D5365CFA35332`.
Status stays `STRUCTURAL_PASS_RUNTIME_PENDING` until the user manually checks
all five distance LODs, facial animation and eyes, every pistol-capacity tier,
chest deformation poses, and the inherited model regression matrix.

## Stage 16 - Candidate AL / Build 24424450 boot compatibility

Candidate AK's standalone `patch_02` passes offline structure but still exits
during the user's manual startup. Do not reactivate AK or infer that another
standalone Forge rebuilt from the old reference container will be compatible.
For the current build, stage replacements through the existing
`DataPC_boot.forge` rows using the Injector's append-and-repoint contract.

### Extract and calibrate the current boot

Stream-read only the Forge header, FAT/TOC, and these seven current top-level
IDs: the four Duncan outfit BuildTables plus selector `0x244130CE35A` and
external Meshes `0x244130CE35B` and `0x24D485A75E8`. Pin the original boot at
25,640,534,016 bytes and SHA-256
`144D947BD4B84709B891837C1A49893062AA9B79E2CECAF66C15FD884BC70A00`.

The current entries use BMS version 3, field 8, 262144-byte chunks, and TOC
mode for both streams. Their exact native encoder profile is oo2core v9,
compressor 9 (Mermaid), level 7. Before processing a candidate, require that
this profile re-encodes all selected original entries byte-for-byte. Do not use
Kraken/Normal merely because both Oodle DLLs can decode it.

Build the outfit-only compatibility entries:

```powershell
python scripts\build_candidate_al_boot_injection_entries.py
```

Require `1338/1338 PASS`. Preserve every decoded Candidate AK bundle byte,
including the variable 104-byte opaque record suffixes, plus asset order and
payload. Only the BMS container changes. Accepted entry hashes are:

- `0x24EB3F06DB8`: `CF47D8CE8E0CF655B5195C0B75AB55827213ABA9F074C819F199961B7EC67871`;
- `0x24EB3F01215`: `73ECB260A1950A838311512962F699A6721341073A9581008FD4D329BD88A5D9`;
- `0x24EB3F011DF`: `8F458F283CE39B8E58378CBD0F23728475C4E6E5B7D1698240454C741F587413`;
- `0x24EB3F011FB`: `1F181D11C48C070F352EC68658AAE7B5F00F8742B53B61F3829D8EEBA32A43FC`.

### Transactional deployment

Close the game, Steam and its web helpers, Ubisoft Connect and all
`UplayWebCore`, Forge Injector, and AnvilToolkit processes. Require no active
`DataPC_boot_patch_02.forge`. Then:

```powershell
python scripts\install_candidate_al_boot_redirect.py --preflight-only
python scripts\install_candidate_al_boot_redirect.py --install --execute-install
python scripts\install_candidate_al_boot_redirect.py --verify-installed
```

The installer must create and hash a complete non-overwriting backup, preserve
the four original TOC rows, append and fsync all four entries before changing
any row, update only offset/size while retaining ID/type, fsync again, read back
each installed entry, and hash the full archive. Any failure after mutation
must restore the four rows and truncate to the original size. Roll back with:

```powershell
python scripts\install_candidate_al_boot_redirect.py --rollback --execute-rollback
```

The accepted stage-1 installed boot is 25,642,408,533 bytes with SHA-256
`479FCB29C92163A8B830E4294F317FB57B46D76D8766B85FC2C4E11397E80580`.
The verified full original backup is
`DataPC_boot.forge.karin_pre_v152_build24424450.full.bak` beside the archive.
Installation evidence belongs under
`work/runtime_backups/candidate_al_v152_boot_redirect_build24424450/`.

This stage deliberately excludes the three mouth/teeth overrides. The user
must first perform the startup check manually. If startup still crashes, roll
back AL and investigate Candidate bundle semantics; do not add more resources.
If startup succeeds, rebuild the three native mouth chains with the same
measured Mermaid/level-7 profile and deploy them as a separately reviewable
stage. No automation may launch or test the game.

### Prepare the stage-2 native teeth chains

Repack Candidate AK outer entries 4-6 only after stage 1 is exact. The first
entry is mouth selector `0x00000244130CE35A` with three embedded Mesh LODs;
the other two are external Mesh entries `0x00000244130CE35B` and
`0x0000024D485A75E8`. Keep the decoded Candidate AK bundle and payload bytes
exact, including all five degenerate teeth-only Meshes and 1212 degenerate
triangles. Re-encode only the BMS containers with the measured native profile:

```powershell
python scripts\build_candidate_al_stage2_teeth_entries.py
```

Require `329/329 PASS`, exact reproduction of all three original native
containers, and these output entries:

- selector chain: 4,967 bytes,
  `685C26F042E226C406436E7E182B943E49BE36D995A5A86A4AB1C8A4D83A0347`;
- external Mesh `0x00000244130CE35B`: 7,914 bytes,
  `D6299E365228EE15952AC0052424677F2311B87DD14E1DB3FE675959127F3A10`;
- external Mesh `0x0000024D485A75E8`: 4,495 bytes,
  `BDF466FA0363EC96C145FA4DD03CF0A37889895B3216736A3574B273C3782D40`.

The teeth-only append is 17,376 bytes. A read-only virtual build from the
exact stage-1 boot yields 25,642,425,909 bytes and SHA-256
`C2A9E1E07C72ABA42FDD6FEC79320C8A79DD3CDFCB063B390A1024A9C38B393E`.
The virtual hash calculation must also reproduce the stage-1 input hash
`479FCB29...E80580` and observe an unchanged file identity across the read.

Use `scripts/install_candidate_al_stage2_teeth_redirect.py` for preflight,
installation structure, verification, and rollback-to-stage-1 behavior. It
shares the stage-1 Windows transaction mutex, holds a share-deny boot handle,
requires the exact BuildID/static files/original full backup/no active
`patch_02`, validates all four stage-1 outfit rows plus all three native teeth
rows, appends and fsyncs before committing only the three teeth row
offset/size fields, then checks the fixed full stage-2 hash. It preserves the
original full backup and rolls back only to exact stage 1.

Interrupted installs without a final installation record may be recovered
only when the durable journal and inline native rows are exact, every target
row is a complete native or planned row, the tail is an exact prefix of the
three replacement entries, and normalizing the three rows reproduces the full
stage-1 hash. Unknown or torn TOC rows fail closed.

The current script deliberately sets
`COMBINED_STAGE2_TRANSACTION_READY=False`. Do not enable it and do not run
`--install --execute-install` until the chest-v2 entry, its row authority, and
the resulting combined full-boot hash are integrated into the same atomic
transaction. A JSON approval cannot bypass this code-level gate. Read-only
preflight remains:

```powershell
python scripts\install_candidate_al_stage2_teeth_redirect.py --preflight-only
```

No automated process may start, control, or test the game for this stage.

## Stage 17 - Candidate AM chest v3 offline candidate

Chest v3 supersedes the underband-only experimental direction without
overwriting Candidate AM v2. It starts from the fixed Candidate AK GLB and
uses three independently gated operations: a full deep Body mask under both
cups and the underband, a maximum 6 mm active boundary retreat with covering
garment weight matching, and seam-gated underband stabilization.

Build the canonical GLB:

```powershell
python scripts\build_candidate_am_chest_v3.py
```

Require canonical SHA-256
`D614582FB75FA52E89D760BFED4379B1A8B0EE1BB099C6F736FFDA9FEC2D7C7D`.
The exact deep mask contains 1,357 triangles and 860 vertices. Its 553
exclusive hidden vertices are assigned to 553 distinct degenerate keeper
triangles by deterministic bipartite matching. The required mask, exclusive
vertex, keeper-triangle, and keeper-assignment hashes are pinned in the build
script. All 1,357 triangles remain degenerate while every one of the 31,548
Body vertices remains referenced.

The five-pose Spine2 X stress sweep must leave zero shallow underband
crossings. Each cup may contain only its three fixed 6 mm-capped boundary
vertices, never more than three per pose and never deeper than 2.1 mm under
the explicitly recorded projected-gap definition. No active triangle may
flip; all rest and posed edge-ratio gates must pass. The 55 cup-underband seam
vertices remain byte-exact.

Reverse winding and compile both runtime Meshes:

```powershell
python scripts\build_karin_reversed_winding_variant.py `
  --input work\model_pipeline\candidate_am\chest_v3\karin_target_bound_priorityuv_purediffuse_v153_chest_v3.glb `
  --expected-input-sha256 D614582FB75FA52E89D760BFED4379B1A8B0EE1BB099C6F736FFDA9FEC2D7C7D `
  --output work\model_pipeline\candidate_am\chest_v3\karin_target_bound_priorityuv_purediffuse_v153_chest_v3_reversed.glb `
  --report work\reports\candidate_am_v153\chest_v3_reversed_winding.json

python scripts\compile_candidate_am_chest_v3_meshes.py
```

The reversed GLB hash is
`DC5BD83071C8F468E4232B6315361F88292AF501F127587DFB77DB4E1764418C`.
Use only the accepted Candidate Z runtime templates, quantization factor
`2.02`, and unchanged template extents. Required compiled resources are:

- Body: 1,990,539 bytes, 31,548/31,548 vertices, zero dropped,
  `F291A428BAFADED84318E65B176769BA42A26589B3D0A6EE5EF78E8F4AD9EEA4`;
- ClothA: 1,751,395 bytes, 27,820/27,820 vertices, zero dropped,
  `77E90EFEE673B4544B269BACFC26EB5D9F903AC678266F4E156A620E9ADAF2B2`.

Rebuild the standalone validation Forge from Candidate AI v11, replacing
only these two Mesh resources:

```powershell
python scripts\rebuild_forge_v50_patch.py `
  --input work\package\karin_candidate_ai_v11_head_neck_legfix\DataPC_boot_patch_02.forge `
  --output work\package\karin_candidate_am_v153_chest_v3\DataPC_boot_patch_02.forge `
  --report work\reports\candidate_am_v153\candidate_am_chest_v3_forge_rebuild.json `
  --replace 0x00000081786E922F=work\model_pipeline\candidate_am\chest_v3\runtime_meshes\compiled\asset_009_00000081786E922F.compiled.bin `
  --replace 0x0000009611D6CEAE=work\model_pipeline\candidate_am\chest_v3\runtime_meshes\compiled\asset_010_0000009611D6CEAE.compiled.bin
```

The output must remain 4,096,000 bytes with SHA-256
`3D631D636A68E163AB95166B56125C0F7C699CBE2DB2CFA2E896C57A35EB44D9`.
This Forge is only an offline decoded-content authority; do not deploy it to
Build 24424450.

Encode the current-boot outfit entry and run the complete cross-layer audit:

```powershell
python scripts\build_candidate_am_chest_v3_outfit_entry.py
python scripts\validate_candidate_am_chest_v3_release.py
```

The entry must be 1,872,845 bytes with SHA-256
`98EC6FE8707DD39496658D9A5F21E52BAC80388CC4D8F1150F6819BFD2F68D09`.
Both BMS streams must use version 3, field 8, 262,144-byte TOC blocks, and
oo2core v9 Mermaid/level 7. Decoding the entry must reproduce the v3 Forge
bundle and payload exactly; embedded Body and ClothA must be byte-identical to
the compiled files, and every other outfit asset must remain byte-identical to
Candidate AI v11.

The release validator requires `1272/1272 PASS`. Its only parser waiver is the
generic blanket ban on the exact 1,357 planned Body degenerate triangles; all
other Mesh assertions stay enabled. The pinned report records
`NOT_DEPLOYED_OFFLINE_ONLY` because it is the pre-integration content authority.
Do not regenerate it after installer pinning. Stage 18 records the later parent
review, combined transaction, and installed-state evidence. Never deploy the
standalone validation Forge or start/automate the game from this build stage.

## Stage 18 - Candidate AM 1.5.3 combined transactional deployment

Candidate AM integrates the accepted chest-v3 outfit entry with all three
native-profile teeth chains in one transaction. Never deploy the standalone
chest-v3 validation Forge. The exact Stage 1 input is Candidate AL at
25,642,408,533 bytes / SHA-256
`479FCB29C92163A8B830E4294F317FB57B46D76D8766B85FC2C4E11397E80580`.

Generate the read-only virtual plan before installation:

```powershell
python scripts\plan_candidate_am_v153_combined_redirect.py
```

Require `PASS`, Stage 1 hash `479FCB29...E80580`, append order outfit, selector,
external Mesh 35B, external Mesh 75E8, and final size/hash
25,644,298,754 / `1DAC6CB15731EDF877E762430B7257A36117602446B1E23E522BFB79CDEC9C28`.
The plan must pin chest-v3 release validation `1272/1272`, outfit entry
validation `1029/1029`, and teeth validation `329/329`. Independently reproduce
the virtual hash when installer constants or any replacement byte changes.

Before deployment, close `ACBlackFlag`, Steam and all `steamwebhelper`, Ubisoft
Connect and all `UplayWebCore`, AnvilToolkit, and Forge Injector processes.
Require no active `DataPC_boot_patch_02.forge`. Then run:

```powershell
python scripts\install_candidate_am_v153_combined_redirect.py --preflight-only
python scripts\install_candidate_am_v153_combined_redirect.py --install --execute-install
python scripts\install_candidate_am_v153_combined_redirect.py --verify-installed
```

The installer must hold the shared Windows transaction mutex and exclusive
boot handle, validate BuildID `24424450` and its static files, validate the
immutable original full backup, preserve all four exact Stage 1 target rows,
append and fsync all four replacement entries, and only then repoint four
existing TOC rows. Object IDs and resource types never change. A failure after
mutation restores the four Stage 1 rows and truncates to exact Stage 1 before
returning an error.

Accepted installed state:

- `DataPC_boot.forge`: 25,644,298,754 bytes,
  `1DAC6CB15731EDF877E762430B7257A36117602446B1E23E522BFB79CDEC9C28`;
- active `DataPC_boot_patch_02.forge`: absent;
- installation evidence:
  `work/runtime_backups/candidate_am_v153_combined_redirect_build24424450/`;
- immutable original full backup: 25,640,534,016 bytes,
  `144D947BD4B84709B891837C1A49893062AA9B79E2CECAF66C15FD884BC70A00`.

Rollback to exact Candidate AL Stage 1 only with all relevant processes closed:

```powershell
python scripts\install_candidate_am_v153_combined_redirect.py --rollback --execute-rollback
```

Rollback restores the four preserved rows and truncates the combined tail,
requiring final hash `479FCB29...E80580`. It does not consume or replace the
full original backup. Keep launchers closed after deployment or rollback. No
automation may start, control, or test the game; runtime acceptance belongs to
the user's manual test of startup, all teeth LODs, upgraded-pistol chest poses,
blue-underband deformation, and inherited geometry.

## Stage 19 - Candidate AN 1.5.4 nipple, self-shadow, and live teeth repair

Candidate AN starts only from exact installed Candidate AM 1.5.3:
25,644,298,754 bytes / SHA-256
`1DAC6CB15731EDF877E762430B7257A36117602446B1E23E522BFB79CDEC9C28`.
Do not use the original boot, Candidate AL, or any standalone `patch_02` as
this stage's transaction input.

Build the nipple-suppressed chest-v4 GLB and reversed-winding derivative:

```powershell
python scripts\build_candidate_an_nipple_suppression.py

python scripts\build_karin_reversed_winding_variant.py `
  --input work\model_pipeline\candidate_an\chest_v4\karin_target_bound_priorityuv_purediffuse_v154_chest_v4.glb `
  --expected-input-sha256 ED6A20F569121272B5A22CE3674C485E4806D8DD7769E54DF2C066CD345621F2 `
  --output work\model_pipeline\candidate_an\chest_v4\karin_target_bound_priorityuv_purediffuse_v154_chest_v4_reversed.glb `
  --report work\reports\candidate_an_v154\chest_v4_reversed_winding.json
```

Require the canonical/reversed GLB hashes
`ED6A20F5...5621F2` and `EBF92D1C...F4B3B0`. Exactly two nipple
components, 622 vertices / 1,178 triangles, are newly selected. All selected
triangles are degenerate and every one of the 31,548 Body vertices remains
referenced. The keeper-triangle and assignment hashes are
`77B81FDD...3BD43C` and `1183FE24...70414`.

Compile the two one-primitive runtime Meshes and build the current-boot outfit
entry:

```powershell
python scripts\compile_candidate_an_v154_meshes.py
python scripts\build_candidate_an_v154_outfit_entry.py
```

Both compact Mesh resources must serialize `shadow_caster=false`. Required
hashes are Body `47805CD7...A628891`, ClothA
`77E90EFE...EADAF2B2`, and outfit entry `64A226DB...A70CE`
(1,871,807 bytes). The outfit builder must pass 1,029/1,029. Disabling both
casters is the accepted strong self-shadow mitigation; record the expected
ground-shadow reduction instead of silently treating it as a regression.

Build the four actual Edward facial oral chains:

```powershell
python scripts\build_candidate_an_v154_runtime_teeth_entries.py
```

The authority is selectors `0x245C69AAABE`, `0x245C69AAA1A`,
`0x245C69AAADA`, and `0x245C69AAB11`, each with high/middle/low Mesh LODs.
Require 12 entries, 12 Meshes, and 4,360 triangles. Every Mesh triangle must be
`(a,a,a)` and only its clustered index window may differ. Selector/non-Mesh,
eye, head/face skin, and shared Material bytes remain exact. The builder must
pass 863/863.

Run the independent offline gate before deployment:

```powershell
python scripts\validate_candidate_an_v154_independent.py
```

Require 404/404 custom checks and 1,028/1,028 Oodle checks. The validator must
independently recompile Body and ClothA, decode the outfit entry, decode all 12
teeth entries, and confirm the exact 1.5.3 authority. It must not read or write
the game directory.

With the game, Steam and all `steamwebhelper`, Ubisoft Connect and all
`UplayWebCore`, AnvilToolkit, and Forge Injector closed, and with no active
`DataPC_boot_patch_02.forge`, plan and deploy:

```powershell
python scripts\install_candidate_an_v154_combined_redirect.py --plan
python scripts\install_candidate_an_v154_combined_redirect.py --install --execute-install
python scripts\install_candidate_an_v154_combined_redirect.py --verify-installed
```

The read-only plan must append exactly 13 entries / 1,980,025 bytes and report
`PASS_PINNED`. Accepted installed state is 25,646,278,779 bytes / SHA-256
`1369AE0E5B86880F33E5AB560A606801985501DF838F3681B61805E0B3F3DCE1`.
The transaction preserves 13 exact Candidate AM TOC-row sidecars under
`work/runtime_backups/candidate_an_v154_combined_redirect_build24424450/`,
appends and fsyncs the entire tail, then commits only offset/size in those 13
rows. Object IDs and resource types never change.

Rollback to exact Candidate AM 1.5.3 only with all relevant processes closed:

```powershell
python scripts\install_candidate_an_v154_combined_redirect.py --rollback --execute-rollback
```

Rollback restores the 13 preserved rows and truncates the Candidate AN tail,
requiring 25,644,298,754 bytes / `1DAC6CB1...DEC9C28`. Keep launchers closed
after deployment or rollback. Do not automate game launch, input, or visual
testing. Manual acceptance must cover close-up/cutscene teeth at multiple
distances, both nipples in pistol-upgrade poses, face/clothing brightness in
day and night lighting, and the documented ground-shadow tradeoff.

## Stage 20 - Candidate AO 1.5.5 full native head and combined shadow suppression

Candidate AO starts only from the exact installed Candidate AN 1.5.4 boot:
25,646,278,779 bytes / SHA-256
`1369AE0E5B86880F33E5AB560A606801985501DF838F3681B61805E0B3F3DCE1`.
AN remains the exact AO rollback baseline. Do not use a standalone
`DataPC_boot_patch_02.forge`.

The four AN oral selector chains were real and successfully redirected, but the
Duncan visual BuildTable `0x330557EC362` also references the complete Edward
dynamic-head selector `0x245C69AAA0C`. That selector contains four embedded
full-head Mesh LODs and remains animated by the facial/speech system, which is
why teeth survived AN. Build the replacement with:

```powershell
python scripts\build_candidate_ao_v155_native_head_entry.py
```

Keep the 575-byte selector byte-exact and degenerate only the four clustered
16-bit index windows. Require 30,989 + 13,041 + 6,158 + 2,895 = 53,083
triangles, all `(a,a,a)`. The stored entry is 1,952,061 bytes / SHA-256
`A0C26B47CA3663F4A5B9AA4449080CCD7A2ABFC00CC9FBB71D459DE62AEF655D`.
The builder must pass 713/713 plus 120/120 independent redecode checks. The
Build 24424450 patch_01 full scan must show no top-level or embedded collision
for the target IDs.

Do not derive BFR compact Material names from AnvilToolkit 1.3.6 legacy game
branches: `Game.BlackFlagResynced` is absent from that Material serializer. The
current executable's native descriptor access values lock the relevant map:

```text
flag[12] / 0x65 = ShadowCasterOpaque
flag[14] / 0x67 = IsExcludedFromScreenSpaceShadows
flag[15] / 0x68 = IsAtlasMaterial
```

The authority report is
`work/reports/candidate_ao_v155/bfr_material_native_descriptor_mapping.md`,
status `PASS_NATIVE_DESCRIPTOR_LOCK`, SHA-256
`2E35DC4A9A2196663D052D8C9ABA2AE03E683687B6572F02CBDFDDD94D788B49`.
It pairs field CRC descriptors with member-bit access immediates rather than
assuming registration order.

Build the combined Material and outfit entry:

```powershell
python scripts\build_candidate_ao_v155_combined_shadow_material.py
python scripts\build_candidate_ao_v155_combined_outfit_entry.py
```

Relative to AN, the 589-byte Material may change exactly `0x65: 01 -> 00` and
`0x67: 00 -> 01`. This disables the traditional opaque-caster path and excludes
the Material from screen-space shadows while retaining AN's Body/Cloth
`shadow_caster=false`. All other Material bytes and all other outfit assets
must remain exact. The Material hash is `E145E617...E004D85`; the stored outfit
entry is 1,871,812 bytes / `C2E4E47F...A6A8C02B` and passes 1,374/1,374.
This intentionally strong mitigation may remove or reduce the character's
ground shadow.

Run the independent gate:

```powershell
python scripts\validate_candidate_ao_v155_combined_independent.py
```

Require `STRUCTURAL_PASS_RUNTIME_PENDING`, 116/116 checks, exact AN Body/Cloth,
the two-byte Material delta, all four full-head LOD windows, and the pinned
two-row transaction. Then close the game, Steam, Ubisoft Connect, AnvilToolkit,
and Forge Injector and deploy only through:

```powershell
python scripts\install_candidate_ao_v155_dual_redirect.py --plan
python scripts\install_candidate_ao_v155_dual_redirect.py --install --execute-install
python scripts\install_candidate_ao_v155_dual_redirect.py --verify-installed
```

The transaction appends exactly two entries / 3,823,873 bytes, preserves two
AN TOC rows under
`work/runtime_backups/candidate_ao_v155_dual_redirect_build24424450/`, and
changes only their offset and size. The accepted installed boot is
25,650,102,652 bytes / SHA-256
`916594BA6AB3F65BE5EFBFDF85A994509AFF4357F9663A01A0C344BE20906035`.
Installation and installed readback must both report PASS.

Rollback restores exact AN 1.5.4 and truncates only the AO tail:

```powershell
python scripts\install_candidate_ao_v155_dual_redirect.py --rollback --execute-rollback
```

Do not automate game launch or visual testing. The user must manually verify
speech/cutscene teeth at all distances, self-shadow in mixed lighting, and the
expected ground-shadow tradeoff.

## Stage 21 - Candidate AP / Karin 1.5.6 live oral chain and cloth-layer AO repair

Candidate AP starts only from the exact installed Candidate AO 1.5.5 state:

- `DataPC_boot.forge`: 25,650,102,652 bytes / SHA-256
  `916594BA6AB3F65BE5EFBFDF85A994509AFF4357F9663A01A0C344BE20906035`;
- `DataPC_boot_patch_01.forge`: 1,915,453,440 bytes / SHA-256
  `D2C0A87FD663C154E837350E8B93A00DF847F6659DC19D4E96BACD84041620D7`.

The user's 1.5.5 runtime test rejects both of that stage's hypotheses. Edward's
animated teeth remain visible, and disabling the outfit caster paths damages
the character's conventional cast shadow. Do not reuse the AO full-head entry
as a teeth authority and do not retain the AO `Mesh0=false`, Material
`flag12=0/flag14=1` shadow policy.

The Build 24424450 player-root reference closure identifies two different live
oral selectors: `0x259BBD9F22D` (five LOD Meshes) and `0x23ACC3BE642`
(four LOD Meshes). Together they contain exactly nine oral Meshes / 4,060
triangles. Build their replacements with:

```powershell
python scripts\build_candidate_ap_v156_live_oral_entries.py
```

Each replacement may change only its native clustered UInt16 index window;
every triangle becomes `(a,a,a)`. Selector, material, skeleton, bounds, and all
non-Mesh assets remain exact. Five stored entries belong to
`DataPC_boot.forge`. Resource `0x24BBCF837FF` has a different, higher-priority
same-ID row at TOC index 1216 in `DataPC_boot_patch_01.forge`, so its patch_01
entry is mandatory. A boot-only replacement is incomplete. Require the builder
report at 455/455 and independent live-oral validation at 67/67. Never disable
shared Material `0x22752155CA7`: two additional non-player Mesh consumers use
it outside the player-root closure.

No safe per-Karin AO-strength property exists in the current Material. Preserve
normal shadow behavior and reduce only the measured cloth-to-cloth proximity.
Candidate AT is the outfit component of AP. It translates exactly two complete,
disconnected back-torso outer cloth components by 6 mm without changing their
internal topology:

```powershell
python scripts\build_candidate_at_v156_rigid_outer_clearance.py
python scripts\build_candidate_at_v156_outfit_entry.py
```

Require exactly 1,673 POSITION vertices to change and no changes to topology,
normals, tangents, UVs, colors, joints, weights, materials, Body skin, Hair, or
Face. The proxy gate is:

- ClothB `<5 mm`: 290 -> 20; median gap 6.939 -> 10.776 mm;
- ClothA `<5 mm`: 199 -> 60; median gap 4.807 -> 7.633 mm;
- zero flipped triangles and rigid component edge/area preservation.

Restore the accepted AI/AM shadow contract exactly: Mesh
`0x81786E922F` `shadow_caster=true`, Mesh `0x9611D6CEAE`
`shadow_caster=false`, Material `flag12=1` (`ShadowCasterOpaque`) and
`flag14=0` (`IsExcludedFromScreenSpaceShadows`). The stored outfit entry must
be 1,870,932 bytes / SHA-256
`4727FA90FFC143BB17A1E40957F92C2B5D5EC75D44F306497745F701E67FB13A`
and its repack report must pass 882/882.

Plan and deploy both archives only through the fail-closed transaction:

```powershell
python scripts\install_candidate_ap_v156_dual_archive.py --plan
python scripts\install_candidate_ap_v156_dual_archive.py --install --execute-install
python scripts\install_candidate_ap_v156_dual_archive.py --verify-installed
```

Before installation, close `ACBlackFlag`, Steam and every `steamwebhelper`,
Ubisoft Connect / `upc` and every `UplayWebCore`, AnvilToolkit, and Forge
Injector. The installer preserves seven exact 24-byte TOC rows plus the exact
size/hash of both baseline archives. It appends and fsyncs both archive tails,
read-verifies them, and only then commits six boot rows and one patch_01 row.
Any failure restores all seven rows and truncates both archives to their exact
1.5.5 baselines.

The pinned installed state is:

- `DataPC_boot.forge`: 25,652,038,192 bytes / SHA-256
  `8D5AA29D6F93B4214A5C664855E08F70CAFA926178380906076942E484C29EBF`;
- `DataPC_boot_patch_01.forge`: 1,915,465,325 bytes / SHA-256
  `65B150481E408EDF29D025854D33E141201B5746B0488A1E58EED92BD00F9CD5`;
- active `DataPC_boot_patch_02.forge`: absent.

Rollback restores both exact 1.5.5 archives, not Candidate AN:

```powershell
python scripts\install_candidate_ap_v156_dual_archive.py --rollback --execute-rollback
```

Do not automate game launch, input, or visual testing after deployment. Manual
acceptance must cover speech/cutscene teeth and their face shadow at close,
medium, and far LODs; conventional ground/cast shadow restoration; back-torso
cloth-layer AO in bright and dark scenes; silhouette or seam changes from the
6 mm outer-layer clearance; and all inherited chest, socks, feet, neck, UV, and
weapon checks.

## Stage 22 - Candidate AU / Karin 1.5.7 facial attachment and waist-belt recovery

Candidate AU starts only from the exact installed Candidate AP 1.5.6 state:

- `DataPC_boot.forge`: 25,652,038,192 bytes / SHA-256
  `8D5AA29D6F93B4214A5C664855E08F70CAFA926178380906076942E484C29EBF`;
- `DataPC_boot_patch_01.forge`: 1,915,465,325 bytes / SHA-256
  `65B150481E408EDF29D025854D33E141201B5746B0488A1E58EED92BD00F9CD5`.

The user's 1.5.6 runtime result proves that the nine Stage 21 oral Meshes were
not the remaining visible object. Their removal did eliminate its face shadow,
but a pointed native facial attachment remained. Do not invent a second index
path inside those nine Meshes: each has one clustered triangle index buffer,
its five non-clustered MeshData buffers are empty, and its precompute buffer is
skinning data rather than another triangle stream.

The remaining discrete attachment is selector `0x219100E82CE`. Its exact
player closure is:

```text
0x227F7B5EC6C -> 0x22ED455CD30 -> 0x22A5CFBC1C5
  -> 0x1FAFE239799 -> 0x1FE860BC624 -> 0x219100E82CE
```

The last BuildTable row is a parsed `GraphicObject / Handle`, not adjacent-ID
inference. The selector owns five LOD Meshes, ten primitives, and 2,763
triangles. It is an open, planar, pointed player facial attachment rather than
a complete face, eye, or collar. Its retail semantic name is not proven; call
it the observed facial attachment rather than claiming that either Material
name literally means teeth.

Build its patch_01 replacements with:

```powershell
python scripts\build_candidate_au_v157_player_facial_attachment.py
python scripts\validate_candidate_au_v157_independent.py
```

All three top-level IDs have different same-ID boot copies and authoritative
patch_01 overrides. Redirect only these patch_01 rows:

- TOC 1361, selector `0x219100E82CE`, including three embedded low LODs;
- TOC 1362, external high LOD `0x219100E82CF`;
- TOC 1363, external middle LOD `0x21D0DA0E887`.

Preserve the selector, Materials `0x21910093390` and `0x22DB3D2B109`, vertex
data, skinning, blend shapes, bounds, and every non-index byte. Degenerate only
the two exact clustered UInt16 primitive index windows in each of the five
Meshes. Require 5/10/2,763 complete coverage and 93/93 independent checks. The
three stored entry hashes are `49C988B7...C4FA04`,
`C6B52FB0...92876D`, and `FE6D4FA0...E8006E`. Selector
`0x256BC0F5ABD` is excluded because its elongated vertical-shell silhouette
does not match the runtime object and it is absent from the exact player
closure.

Stage 21 also misclassified the black waist belt as a rear ClothA AO layer.
The affected `ClothA_Blue` connected component is component 29,
minimum vertex 15,188, with 342 vertices / 560 triangles. AT translated it by
6 mm, causing the belt to fall behind the white shorts in the game pose. Build
the exact recovery with:

```powershell
python scripts\build_candidate_au_v157_belt_restore.py
python scripts\build_candidate_au_v157_outfit_entry.py
```

Restore only those 342 POSITION elements to Candidate AN bytes. Their UVs,
weights, indices, normals, tangents, colors, triangle membership, and atlas
remain exact. Mesh1 becomes byte-exact Candidate AN; Mesh0 remains byte-exact
Candidate AT, retaining the legitimate 1,331-vertex ClothB rear-layer shift and
its `<5 mm` proxy improvement from 290 to 20. Withdraw the invalid ClothA
199-to-60 AO claim; after belt restoration that pair is correctly 199 to 199.
Retain the normal shadow contract Mesh0=true, Mesh1=false, Material
flag12=1/flag14=0. The outfit entry is 1,870,931 bytes / SHA-256
`CEBF0D05A7A462614B870DC101BF4E2ABF57187FDD04CC3CEE461316F423F29C`
and must pass 882/882.

Before deployment, require the combined independent gate at 409/409 and the
21-artifact manifest SHA-256
`05E69FE01C45BC89F427C3B506EE7772715E0B3CF22DD59C98BD13585F621AA4`.
Close the game, Steam and every `steamwebhelper`, Ubisoft Connect / `upc` and
every `UplayWebCore`, AnvilToolkit, and Forge Injector. Then run only:

```powershell
python scripts\install_candidate_au_v157_dual_archive.py --plan
python scripts\install_candidate_au_v157_dual_archive.py --install --execute-install
python scripts\install_candidate_au_v157_dual_archive.py --verify-installed
```

The transaction preserves four exact 1.5.6 TOC rows, four corresponding
payload sidecars, and both archive baseline identities. It appends and fsyncs
both tails, verifies them, and only then commits one boot row and three
patch_01 rows. Any failure restores all four rows and truncates both archives
to exact 1.5.6.

The pinned Candidate AU installed state is:

- `DataPC_boot.forge`: 25,653,909,123 bytes / SHA-256
  `BAF0767B58D5F30F0C33817D77DAFA0BAD735B7F43A26583C4662A0668F17DFB`;
- `DataPC_boot_patch_01.forge`: 1,915,532,455 bytes / SHA-256
  `D2983CDE9D5F4B4F6AF38826B6A7DF2586F65BCFCAFDCC3C3181D89187181362`;
- active `DataPC_boot_patch_02.forge`: absent.

Rollback restores exact Candidate AP 1.5.6 across both archives:

```powershell
python scripts\install_candidate_au_v157_dual_archive.py --rollback --execute-rollback
```

Do not automate game launch, input, or visual testing. Manual acceptance must
verify the pointed face object during speech and cutscenes at every LOD, the
black waist belt in rest and animated poses, the retained ClothB AO reduction,
normal cast shadow, and all inherited chest, socks, feet, neck, UV, weapon, and
startup checks.

## Stage 23 - Candidate AV / Karin 1.5.8 native head-subtable suppression

The user's manual 1.5.7 result rejects `0x219100E82CE` as the remaining
teeth/gingiva authority: its five LOD Meshes were removed without changing the
visible native mouth object. Do not select another leaf solely from geometry
similarity or broad graph reachability. The complete player-facial closure
from root `0x227F7B5EC6C` expands through every serialized customization
alternative: 2,663 BuildTables, 49,149 contextual edges, and 1,459 referenced
geometry entries. That closure is an offline possibility graph, not the
runtime-selected row state.

Build the audited BFR BuildTable harness and parse the player facial root:

```powershell
& .\tools\BfrBuildTableHarness\build.ps1
dotnet .\tools\BfrBuildTableHarness\bin\manual\BfrBuildTableHarness.dll parse `
  work\research\v158_active_face_selection\root_buildtable_parse.json `
  work\research\v157_visible_teeth_trace\player_facial_closure\extracted\DataPC_boot\entry_009163_00000227F7B5EC6C\asset_000_00000227F7B5EC6C.bin
```

The parser must consume the 1,434-byte resource to EOF and expose eight row
components in authoring order `1,3,5,4,2,8,9,11`. Numeric sorting is not a
valid row invariant. Row key 1 contains the unique BuildTable reference to
native head master `0x227F7B610C3` at byte offset 1,348. Generate the bounded
replacement only with:

```powershell
dotnet .\tools\BfrBuildTableHarness\bin\manual\BfrBuildTableHarness.dll `
  null-build-table-reference `
  work\reports\candidate_av_v158\candidate_av_v158_head_subtable_patch.json `
  work\research\v157_visible_teeth_trace\player_facial_closure\extracted\DataPC_boot\entry_009163_00000227F7B5EC6C\asset_000_00000227F7B5EC6C.bin `
  work\candidate_av_v158_head_subtable_suppression\assets\asset_000_00000227F7B5EC6C.bin `
  --resource-id 0x00000227F7B610C3
```

The only allowed window is the nine-byte reference at 1,348. Replace marker 1
and ID `0x227F7B610C3` with marker 3 and a zero ID. Preserve byte length, root
ID, row metadata, and the other seven peer references. The patched asset must
be 1,434 bytes / SHA-256
`E3DA35A6D338E8BE4705A168341B5F4D042E62380F0F80D07CD6E48399711C42`.

The branch boundary must prove that the suppressed family includes the known
oral/full-head selectors `0x259BBD9F22D`, `0x23ACC3BE642`, and
`0x245C69AAA0C`, while excluding all four Karin/Duncan replacement BuildTables
and Karin Meshes `0x81786E922F` / `0x9611D6CEAE`. Build and independently
validate the stored entry with:

```powershell
python scripts\build_candidate_av_v158_head_subtable_suppression.py
python scripts\validate_candidate_av_v158_independent.py
```

Require 71/71 builder checks and 36/36 independent checks. The replacement
stored entry is 489 bytes / SHA-256
`2D1C292D6A35A9C67F1F753E433E61EDF46EBCDB9A38EA26FFBCDAA02D3F09EF`.
It must decode to the exact original bundle index plus the patched root asset,
and reproduce byte-exactly with the Build 24424450 Mermaid 9 / level 7 BMS
profile.

Candidate AV starts only from exact installed Candidate AU 1.5.7:

- boot: 25,653,909,123 bytes /
  `BAF0767B58D5F30F0C33817D77DAFA0BAD735B7F43A26583C4662A0668F17DFB`;
- patch_01: 1,915,532,455 bytes /
  `D2983CDE9D5F4B4F6AF38826B6A7DF2586F65BCFCAFDCC3C3181D89187181362`;
- active patch_02: absent.

Deploy through the single-row transaction only:

```powershell
python scripts\install_candidate_av_v158_boot.py preflight
python scripts\install_candidate_av_v158_boot.py install
python scripts\install_candidate_av_v158_boot.py verify
```

The installer backs up the exact 1.5.7 TOC row and 492-byte source entry,
appends the 489-byte replacement, fsyncs it, and redirects only boot TOC index
9,163. Any failure after writing restores the original row and truncates boot
to the exact baseline size. The committed installed state is:

- boot: 25,653,909,612 bytes / SHA-256
  `24FBECF3E4205AE0FFC747A4A3258F091D0F669D67747AB76745B404048A9E0D`;
- patch_01: unchanged from 1.5.7;
- active patch_02: absent.

Rollback to exact 1.5.7 with:

```powershell
python scripts\install_candidate_av_v158_boot.py rollback
```

Do not automate game launch, input, or visual testing. Manual acceptance must
check the native teeth and gingiva with the mouth closed and during speech,
from front/profile/low angles and at multiple LOD distances. Also confirm the
Karin face, eyes, hair, outfit, waist belt, weapons, body animation, cast
shadow, startup, and all inherited chest/leg/foot/neck fixes remain intact.

Candidate AV's manual runtime result is rejected. It removed the native teeth
and gingiva, but both Karin eyes left their sockets and appeared on the chest.
Do not deploy AV as an accepted release and never again null the whole head
master `0x227F7B610C3`. The runtime rejection record is
`work/reports/candidate_av_v158/runtime_rejection_eye_transform_20260830.json`,
SHA-256 `A1CD0193C8297A293A6835C8CB18FA332C7BF1A254AB0277E803F55370D3DB32`.

## Stage 24 - Candidate AW / Karin 1.5.9 eye-rig restoration and leaf geometry suppression

AV proved that the native head master owns more than oral geometry. Karin Mesh
`0x9611D6CEAE` has 822 eye vertices, 411 per eye. They use Head slot 162 plus
`FB_EyeRoot_L` slot 210 or `FB_EyeRoot_R` slot 212. The general body Skeleton
does not contain those eye-root CRCs. Their runtime selection context is:

```text
0x227F7B5EC6C -> 0x227F7B610C3 -> 0x227F7B963FC
  -> 0x228EA92F0B2 -> runtime-selected facial Skeleton
```

The separate dynamic-head geometry path is:

```text
0x227F7B610C3 -> 0x246B97967AB -> 0x22A5CF92912
```

The eye-rig subtree contains 182 candidate Skeletons with both Karin eye-root
CRCs. The dynamic-head subtree contains 192 Skeletons and none has that pair.
Therefore restore the exact Candidate AU root row and preserve the complete eye
branch. Suppress geometry only at row-level `GraphicObject / Handle` leaves;
do not null a parent BuildTable, Skeleton, selector, tag, dependency, or
Material reference.

Build the candidate with:

```powershell
python scripts\build_candidate_aw_v159_leaf_graphics.py
python scripts\validate_candidate_aw_v159_independent.py
```

The strict inventory contains 149 dynamic-head BuildTables. Exactly 103 parse
to EOF; 46 complex routing/property tables remain fail-closed and byte-exact.
Clear the eight-byte ClassID of each of the 97 unique parsed GraphicObject
Handles while retaining its zero marker and serialized length. Route 91
replacement entries to boot and six to patch_01. The patched table set must
have zero intersection with the eye-rig subtree. All four proven oral/full-head
targets must be included: `0x245C69AAA0C`, `0x259BBD9F22D`,
`0x23ACC3BE642`, and `0x244130CE35A`.

The hardened build report is
`work/reports/candidate_aw_v159/candidate_aw_v159_leaf_graphics_build.json`,
SHA-256 `386C7541D493BCC5AD29EB3BFAADA8B4E314F9E39366BC37CEE64E6378615D52`.
Require 5,831/5,831 build checks. The independent report is
`work/reports/candidate_aw_v159/candidate_aw_v159_independent_validation.json`,
SHA-256 `71B771A62996BC9F489A2AEEC666376DC214E8C6D78E461134AC661391F07BCC`.
Require 5,027/5,027 structural checks and 5,891/5,891 Oodle/BMS checks. All 97
stored entries must re-encode byte-exactly; all non-target assets and bytes
must match their source. The observed 581 changed nonzero bytes must remain
inside the 97 Handle-ID windows.

Candidate AW starts only from exact installed Candidate AV 1.5.8:

- boot: 25,653,909,612 bytes /
  `24FBECF3E4205AE0FFC747A4A3258F091D0F669D67747AB76745B404048A9E0D`;
- patch_01: 1,915,532,455 bytes /
  `D2983CDE9D5F4B4F6AF38826B6A7DF2586F65BCFCAFDCC3C3181D89187181362`;
- active patch_02: absent.

Deploy and verify only through the dual-archive transaction:

```powershell
python scripts\install_candidate_aw_v159_dual_archive.py preflight
python scripts\install_candidate_aw_v159_dual_archive.py install
python scripts\install_candidate_aw_v159_dual_archive.py verify
```

The installer preserves 98 exact AV TOC rows and 97 AW payload sidecars before
the first game write. It appends and fsyncs both complete tails, verifies every
payload, commits the six patch_01 leaf rows, commits the 91 boot leaf rows, and
restores root row 9,163 last. Any exception restores all 98 rows and truncates
both archives to exact AV lengths. The installed identities are:

- boot: 25,653,946,455 bytes /
  `B1924B3FE09888465BF25FB0B0B06E773C083155D76B236F83F1A19E1986B1E2`;
- patch_01: 1,915,534,766 bytes /
  `5FC332B3BF55E68B00DD79DB8CB00590DF605A3A8F603E7163072CEAEC440D48`;
- active patch_02: absent.

The transaction is `COMMITTED` and the installed verification report is
`work/reports/candidate_aw_v159/candidate_aw_v159_installed_verification.json`,
SHA-256 `B5595F7FD2ECDAB2AE5003BF1E2ED46151A593CB5AB84EB339CC196B8C9B3AFE`.
Recovery evidence is under
`work/runtime_backups/candidate_aw_v159_dual_archive_build24424450/`. Roll back
to exact AV with:

```powershell
python scripts\install_candidate_aw_v159_dual_archive.py rollback
```

Do not automate game launch, input, or visual testing. Manual acceptance must
verify both eyes stay in their sockets during blinking, gaze, head motion,
speech, cutscenes, and LOD changes; no eye fragment appears on the chest;
native teeth and gingiva remain absent from front/profile/low angles; and the
waist belt, chest, socks, feet, neck, hair, clothing, weapons, UVs, colors, AO,
and conventional cast shadows retain their inherited behavior.

Candidate AW's manual runtime result is rejected. It restored Karin's eyes to
their sockets, but the native teeth and oral geometry returned. The runtime
record is
`work/reports/candidate_aw_v159/runtime_rejection_oral_return_20260830.json`,
SHA-256 `ECC45A505D2DDB3589AE80EB074ACABD7726C3B2C7E2148CB134C6D9116E0805`.
The 46 fail-closed key4 tables contain no GraphicObject metadata, so the
remaining native head does not come from an omitted key4 leaf.

## Stage 25 - Candidate AX / Karin 1.6.0 paired facial GraphicObject suppression

Rejected by the user on 2026-09-05: NPC heads disappeared while Karin's mouth
remained. The tables described in this stage are shared NPC assets. Do not
repeat this deployment or treat its offline checks as proof of player-only
scope. Stage 26 restores these changes and corrects the outfit-local cause.

The remaining native head authority is below the preserved eye-Skeleton root
`0x228EA92F0B2`. Its root contains no direct GraphicObject or Skeleton value.
All 91 child leaf BuildTables parse to EOF and contain exactly two rows each.
Every one of the 182 rows has one native `GraphicObject / Handle` and one
separate `Skeleton / Handle`; all 182 paired Skeletons are unique and contain
both `FB_EyeRoot_L` and `FB_EyeRoot_R` CRCs.

The 182 GraphicObject values resolve to 93 unique LODSelectors. Every selector
uses the same complete native dynamic-head family:

- Meshes `0x21600C18186`, `0x21600C1818D`, and `0x21600C18194`;
- Material `0x1F613012A06`.

The middle LOD has 1,968 vertices, 3,676 triangles, 30 bones, and full-head
bounds. It is not a mouth-only attachment. Therefore clear all 182 row-level
GraphicObject Handle IDs while preserving their marker bytes. Preserve each
same-row Skeleton, SkeletonStateModifier, other Handle, PropertyPath, default
selection trailer, BuildTable reference, and every other asset byte. Never
null key2 or the `0x228` root.

The peer boundary report is
`work/research/v160_head_master_peer_branches/head_master_peer_branch_audit.json`,
SHA-256 `A028970E15E6907E68C0EFE5BA775695E5EF135C69E25AE738706301226FDDB7`.
Build and validate with:

```powershell
python scripts\build_candidate_ax_v160_eye_skeleton_graphics.py
python scripts\validate_candidate_ax_v160_independent.py
```

The build report is
`work/reports/candidate_ax_v160/candidate_ax_v160_build.json`, SHA-256
`2530E1A2BF61DD072D32C954F85DFABD88E1B3929BF26AF4CA13C1ADF8EDE946`.
Require 6,017/6,017 checks, 91 boot entries, 182 Handle clears, zero overlap
with AW's 97 key4 tables, and 1,092 changed nonzero decoded bytes confined to
the 182 ID windows. The independent report is
`work/reports/candidate_ax_v160/candidate_ax_v160_independent_validation.json`,
SHA-256 `2BF6FC3BA228BEA1C0FE0BB7F0E19A3614A8CA9E7EE2640873A3BA0BF8BFDA56`.
Require 9,310/9,310 structural checks and 5,471/5,471 Oodle/BMS checks,
including 182 exact Skeleton peers, 455 exact PropertyPath column regions, 91
exact opaque trailers, all non-target assets, strict Mermaid 9 / level 7
re-encoding, and five unchanged control roots.

Candidate AX starts only from exact installed Candidate AW 1.5.9:

- boot: 25,653,946,455 bytes /
  `B1924B3FE09888465BF25FB0B0B06E773C083155D76B236F83F1A19E1986B1E2`;
- patch_01: 1,915,534,766 bytes /
  `5FC332B3BF55E68B00DD79DB8CB00590DF605A3A8F603E7163072CEAEC440D48`;
- active patch_02: absent.

Deploy only with the hardened boot transaction:

```powershell
python scripts\install_candidate_ax_v160_boot.py preflight
python scripts\install_candidate_ax_v160_boot.py install
python scripts\install_candidate_ax_v160_boot.py verify
```

The installer pins a fixed 91-target mapping, build/independent/synthetic
report SHAs, and five control roots. Before the first boot write it preserves
91 AW row sidecars, 91 AX payload sidecars, a baseline manifest, and journal.
It holds share-mode-zero handles on boot and patch_01, appends and fsyncs the
59,136-byte tail, verifies every payload, commits and fsyncs 91 TOC rows, then
checks the complete boot SHA, patch_01 SHA, patch_02 absence, BuildID, EXE, and
control roots. Any `BaseException` restores all rows and truncates to exact AW.
The synthetic test injects a torn 38th row after 37 commits and proves complete
recovery.

The installed identities are:

- boot: 25,654,005,591 bytes /
  `E96BB739589E3797375CD7B63D51AC6A1CC70836D0637BC01964D7CB4797C729`;
- patch_01: unchanged from AW;
- active patch_02: absent.

The transaction is `COMMITTED`. Installed verification is
`work/reports/candidate_ax_v160/candidate_ax_v160_installed_verification.json`,
SHA-256 `A8C739940174FF93B8F321EABF658DFFDF2B5EBACAC8C710B4984CF43589DA86`.
Recovery evidence is under
`work/runtime_backups/candidate_ax_v160_boot_build24424450/`. Roll back to
exact AW with:

```powershell
python scripts\install_candidate_ax_v160_boot.py rollback
```

Do not automate game launch, input, or visual testing. Manual acceptance must
confirm that both Karin eyes remain correctly positioned and animated while
all native teeth, gingiva, and full-head geometry remain absent during speech,
cutscenes, close/profile/low views, and LOD changes. Recheck the waist belt,
chest, socks, feet, neck, hair, clothing, weapons, UVs, colors, AO, and cast
shadows for inherited regressions.

## Stage 26 - Candidate AY / Karin 1.6.1 shared-head recovery and local mouth switch

The AX runtime feedback establishes a scope failure: globally clearing facial
BuildTable GraphicObject values removed NPC heads without hiding Karin's mouth.
Neither a large count of passing binary assertions nor a generic facial
reference closure proves that the edited resources belong only to the player.
All future character-specific visibility work must start at the outfit's
instance property overrides. Shared head tables and native geometry stay intact.

The September update is BuildID `24833802`. The boot was still exact AX,
but patch_01 and the EXE were updated. Do not disable older installers' version
guards or overwrite these updated files. The dedicated recovery script pins
the new identities and the two historical backup manifests, restores 182
AW/AX boot rows, and truncates only the backed-up append tail. The resulting
boot is exact AU, 25,653,909,123 bytes /
`BAF0767B58D5F30F0C33817D77DAFA0BAD735B7F43A26583C4662A0668F17DFB`.

```powershell
python scripts\recover_shared_heads_build24833802.py apply
```

This recovery already ran successfully. Its recovery rows and 96,468-byte
removed tail are under
`work/runtime_backups/shared_head_recovery_build24833802/`.
The removed tail is recoverable and contains only superseded mod payloads.

Inspect the Karin outfit entry `0x24EB3F06DB8` before following shared facial
tables. Its embedded visual BuildTable `0x330557EC362` has 31 instance
visibility rules. `VisualPropertyNodeSolver` (`0x1D6F0AE7`) is 50 bytes in
these compact resources. The second PropertyPath node targets `Active`, hash
`0x4CB2F934`, verified against the local Anvil hash dictionary. Column 20004
targets `0x256689B49E2` and its row Bool at resource byte 8,990 is `true`.
This is the original native mouth still explicitly enabled by the mod.

The enabled selector was extracted from the updated patch_01. Its mouth LOD
`0x256689B9806` has 827 vertices, 707 triangles, 75 facial bones and compact
mouth bounds. The other enabled selector `0x1F4353D91FE` has a 218-vertex,
380-triangle, two-bone pair of native eyeballs and is left unchanged. Offline
shape evidence is in
`work/research/v161_head_ownership/enabled_visual_meshes/enabled_visuals.png`.

AY changes only the mouth Bool from `1` to `0`. The 9,047-byte resource size,
all column/target IDs, Skeleton dependencies, eye weights, original 30 other
rules, bundle index and other 11 outfit assets remain exact. The broad
1,109-rule visibility-list research draft was not deployed and is marked
`DISCARDED_NOT_DEPLOYED`.

```powershell
python scripts\build_candidate_ay_v161_local_mouth_switch.py
python scripts\install_candidate_ay_v161_local_mouth.py plan
python scripts\install_candidate_ay_v161_local_mouth.py install
python scripts\install_candidate_ay_v161_local_mouth.py verify
```

The final installer also restores 21 older shared Mesh/LODSelector rows from
the immutable original boot. Only the four known Karin outfit rows may differ
from the original TOC. After normalizing those four rows, the entire original
boot prefix must hash to vanilla SHA
`144D947BD4B84709B891837C1A49893062AA9B79E2CECAF66C15FD884BC70A00`.
This checks every shared boot resource byte, not merely a selected head list.

Installed identities:

- boot: 25,655,780,054 bytes /
  `746A4FF0E038D226929443BE542B8B6F3D3FC76D38653CE323C6AC6D9F8A39FF`;
- updated patch_01: 2,058,878,976 bytes /
  `E68D7B8CDD5206C13FDE6E2CD481CCBCD21C36475F6547D51FFA9D43309F7F63`;
- updated EXE: `614DAB4A20A5D5C6256792E1DAA6D05669C97A751079B10DF1725D6965AD766D`;
- active patch_02: absent.

AY output entry is 1,870,931 bytes /
`86B62A89826ADFB06361348DA463B48FE5DFF0B8A097C51DE3F10AFC4230CEC0`.
The local visual output is
`513297CA0A7693C1B388CF43637921AA49BF5E61FB412663AA772DB2DBB2B078`.
The independent decoder verifies the single payload delta at 11,792
(local asset byte 8,990), unchanged other assets and exact re-encoding.
The installer preserves 22 baseline rows plus the candidate payload before
appending, fsyncs/readbacks before committing, and holds both archive locks.
The current patch_01, EXE and BuildID are checked before and after installation.

Evidence: `work/reports/candidate_ay_v161/`.
Backup: `work/runtime_backups/candidate_ay_v161_build24833802/`.
Rollback to the recovered AU state using:

```powershell
python scripts\install_candidate_ay_v161_local_mouth.py rollback
```

Do not launch or control the game for automatic testing. User verification
must confirm complete NPC heads, no native mouth through Karin's face during
speech or low-angle views, correct Karin eyes, and the retained clothing,
waist belt, leg and foot fixes. Record runtime results separately from file
verification. Do not call AY runtime-accepted before the user's confirmation.
