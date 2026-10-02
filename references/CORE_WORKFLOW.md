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
- When an importer only swaps vertex buffers, look for per-asset values derived from the vanilla vertex count
  (Horizon Forbidden West: the `VertexComputeNbtCount` of GPU normal-regeneration SkinInfo parts). A stale count
  hangs the game on load; diff a working reference Mod's metadata against vanilla before guessing.
- Pick the material of a replaced part by its shader, not by free texture-page space: a face-skin shader's
  subsurface scattering tinted hair red-brown in shadow, which no offline render showed.
- Confirm which asset the game actually loads before editing it. God of War Ragnarök ships a complete Freya in
  `r_freya00.wad` that nothing references; the companion loads `r_freyavalkyrie00.wad`. Search the game's
  dependency manifest for who references the asset instead of trusting the file name.
- Validate serialized skinning per vertex (joint set and weights against the source), not by index range. A
  joint layout chosen from the wrong component combination (u16 slots written as packed 11-bit indices) passed
  a range check and bound a whole mesh to the wrong bones in game.
- Bind only to bones that carry skin in the vanilla meshes. Rigs can stack non-deforming FK controls on the same
  joints, and a position-based role or mirror search will happily pick them (the skirt and tail then flip).
- Shared source model: since 2026-10-02 Karin_Original's FBX and VRM have body_2's `kisekae_Knee` shape key baked
  into the base mesh (key zeroed, name kept; originals beside them as `*.orig`; VRM `971a150d…` → `8f930404…`,
  FBX `0b6e268d…` → `18f00e1a…`). Projects built before that date used the unbaked source. The first copy into
  the synced folder came out with a 384 KiB zero block in each file (VRM `32dd84b5…`, FBX `c8b90bc2…`; replaced
  the same day): re-hash files after copying them into a sync drive. Pipelines that drop shape keys lose these
  "dressing" keys that pull skin in under clothing; bake the needed key at the source
  (`portable-kits/god-of-war-ragnarok`, `bake_knee.py`) rather than adding per-game culls, and use the
  `.orig` files for outfits that expose the knee.
