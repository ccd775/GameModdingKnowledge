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
- Read the cooked or packed asset back before tuning its look. Sifu: UE editor Python hands out struct copies, so
  material slots edited through them stayed `null` in the cooked mesh; four in-game tests chased dark lighting until a
  CUE4Parse read-back of the pak showed the empty slots.
- Re-posing a source model (T to A) also rotates the pieces hanging from the limb (sleeves, strings): they end up in
  the legs at rest. Turn their hang bones back to their source world direction after aligning the limb.
- Tune joint drives from the source model's own physics parameters and the engine's drive formula, not by trial.
  PhysX body angular damping acts only on the inertia about the centre of mass, a small fraction of a slender chain's
  inertia about its root, so it barely damps a pendulum swing. UE 4.26 PhysX drives are acceleration drives: for a
  sub-chain of inertia I_sub about the joint and mode frequency w, stiffness = w^2 * I_sub / I_com and damping =
  2 * zeta * w * I_sub / I_com (`games/sifu/PHYSICS.md`).
- Reproduce a cloth clipping report offline with the game's own animation of that move before changing parameters.
  A coarse time-stepped stand-in is enough to rank candidates when only conclusions that hold at two solver settings
  are trusted (Sifu `skirt_sim.py`).
- Read the skeleton's translation retargeting mode before deciding where proportions change. Palworld's human
  skeleton uses `Skeleton` mode for almost every bone, so the mesh's own bind pose sets the proportions (only bone
  orientations must match vanilla); Stellar Blade uses `Animation` mode, so proportions can only change in a
  post-process AnimBP.
- Replace the narrowest runtime hook the game already links. Palworld links each outfit's physics through an anim
  layer interface (`ALI_HumanCloth` / `ClothLayer`) chosen by a data table; a new implementation blueprint at the
  vanilla path runs on the replaced mesh without touching the player AnimBP.
- Turn "too stiff" into a measurement. Port the engine's secondary-physics step offline and drive it with the game's
  locomotion animation (Palworld `kawaii_sim.py`, KawaiiPhysics 1.17.1). Chains that sit at their angle limit most of
  the time read as stiff: steady-state lag is about (1 - WorldDampingLocation) x per-frame travel / Stiffness, and in
  KawaiiPhysics the angle limit runs after collisions, so a tight limit also drags cloth back into a lifted thigh.
- Check for a built-in cosmetic override before building a workaround for gear that hides a replaced outfit.
  Palworld's dresser (since v0.5.0) can show the starting outfit over any armour.
- When secondary physics only moves for about a second after a reset (outfit change, menu close, pause), stop
  tuning parameters and find the engine's per-frame gate. In Marvel's Spider-Man 2 the AnimDynamics job skips an
  instance whose model has no owner actor with an animation controller, or whose runtime bounding sphere (rebuilt every
  frame from the per-joint spheres, not from the built header) is too small for the camera distance; outfit parts
  built by the skin manager have no owner, so no data change could keep their chains alive
  (`games/marvels-spider-man-2/PHYSICS.md`).
- Host physics on an object the engine already spawns for every target outfit and drives on its own. Spider-Man 2's
  masked suits all spawn the same placeholder head actor; moving the chains there (never-cull on, joint spheres
  enlarged, hip joints added to the head-to-body joint map) gave continuous physics on 91 suits, where adding one
  more attachment component per suit failed because the engine keeps only the first component of a type.
- Before editing a container format, make the codec re-encode every shipped file byte-exactly (Spider-Man 2: all
  11,477 actors) and regenerate vanilla physics sections word for word; compare denormal-looking words bit by bit,
  because small integer pairs read as floats compare equal and hid a wrong field for two in-game rounds.
- Shared source model: since 2026-10-02 Karin_Original's FBX and VRM have body_2's `kisekae_Knee` shape key baked
  into the base mesh (key zeroed, name kept; originals beside them as `*.orig`; VRM `971a150d…` → `8f930404…`,
  FBX `0b6e268d…` → `18f00e1a…`). Projects built before that date used the unbaked source. The first copy into
  the synced folder came out with a 384 KiB zero block in each file (VRM `32dd84b5…`, FBX `c8b90bc2…`; replaced
  the same day): re-hash files after copying them into a sync drive. Pipelines that drop shape keys lose these
  "dressing" keys that pull skin in under clothing; bake the needed key at the source
  (`portable-kits/god-of-war-ragnarok`, `bake_knee.py`) rather than adding per-game culls, and use the
  `.orig` files for outfits that expose the knee.
- When a rig or physics mechanism shows no visible effect, run a binary probe (a constant 15 cm bone offset, a locked
  joint) before tuning parameters. Days Gone spent eight builds tuning PhysX constraints on extra player-mesh bodies
  that the engine ignored; one constant-offset probe ruled out BoneDrivenController in a single round
  (`games/days-gone/PHYSICS.md`, `games/days-gone/FACE_AND_LIPSYNC.md`).
- Nearest-surface weight transfer from a realistic face misses narrow features: Karin's eyelids and both lips landed on
  the same side of Deacon's 0.1-0.7 cm lip seam, so blinks moved only the brows and dialogue barely opened the mouth.
  Simulate the game's own face animation (decoded, with its additive rules) on the build before shipping, and solve
  per-vertex weights (non-negative, sum 1, influence cap) so the game's poses reproduce the source model's own shape keys.
- Small realistic joint deltas can drive anime-scale deformation through mesh-only bones: give a parent bone a cooked
  ref-pose rotation and non-uniform scale (UE rebuilds inverse bind matrices at load) and copy the source joint's local
  translation onto the child with a CopyBone node (Days Gone: 0.8 cm lid travel -> 3.9 cm VRM blink).
- Adding nodes to a cooked UE4 AnimBlueprint: pose LinkIDs index AnimNodeProperties forward while the root, state
  machines and ubergraph calls index it from the end. Insert new node properties at the head of the class field chain
  and add M to every pose link, including those inside BlendPose arrays (`games/days-gone/TECHNICAL_CONTRACTS.md` §8).
- A secondary-physics node with no gravity barely returns inside its allowed deviation: it rests wherever motion left
  it, so the resting error is the cap, and neighbours resting off in different directions fold or twist the chain.
  Raising stiffness or mass did not fix it in The Witcher 3; small caps plus rigid skip links at the bind length did.
  Apply the fix to every shape-keeping chain at once, not only the one the user named (the twin tails needed another
  round after only the tail was fixed) (`games/the-witcher-3/PHYSICS.md` §5).
- Judge a resting shape from the side and from the user's camera, next to an offline render of the target pose with
  every node on its stiffness target. Front and back shots hid a twisted tail for two rounds, and the agent once read a
  tail sticking out in a burst as its modelled shape (`games/the-witcher-3/cases/KARIN_ORIGINAL.md`).
- In offline clipping checks, propagate aim constraints: a pinned segment that looks at a drifting simulated node turns
  with it. The Witcher 3 skirt poke only reproduced once the waist segment turned with the drifted hip ring. On pleated
  cloth use ray casts along the skin normal, not nearest-face signed distances (`games/the-witcher-3/PHYSICS.md` §7).
- Do not fit fingers with a body-wide spatial warp. Control points on neighbouring finger segments fight each other,
  and in Horizon Forbidden West they pushed Karin's fingers up to 0.94 cm off Beta's finger axes, always toward the
  neighbouring finger. Running looked fine, but cutscene finger curls crossed the middle and ring fingers. Map the hand
  per bone instead and blend the maps by the source's own skin weights: align the whole palm frame including its roll,
  then turn each segment onto its target axis. Gate the result offline on the segment-centre offset from the bone axis
  and on an interpenetration count with every finger curled into a fist
  (`games/horizon-forbidden-west/BUILD_PIPELINE.md` §3).
- Rig an anime face to a joint-driven realistic face with guards on top of the nearest-surface transfer:
  - Split the lips by topology. Karin's mouth slit rims are 0.04 cm apart, so take each rim vertex's side from the
    direction its triangles extend in, not from its height.
  - Average the weights of coincident vertices (mirror centre line, UV seams), or the face cracks open when it moves.
  - Leave out joints whose travel cannot cover the source feature: lids that travel 1 cm against a 4.6 cm anime eye
    only twitch.

  Before concluding that expressions do not work, look in a scene that reliably drives the face: HFW photo mode
  expressions did, plain gameplay showed almost none (`games/horizon-forbidden-west/BUILD_PIPELINE.md` §6).
- When the tools cannot author new physics, borrow the target's own simulated particles: HFW Beta's PBD particle
  bones kept simulating with her cloth meshes collapsed. Spread a long part along one particle chain (root to tip
  levels, adjacent levels blended) rather than hanging it on one or two particles. One particle swings the whole part
  as a rigid lever, which the user called "too uniform" (`games/horizon-forbidden-west/BUILD_PIPELINE.md` §4).
- When a tool chain round-trips binary resources through JSON, check whether a field silently changes encoding or
  disappears: WolvenKit 7 drops `SSkeletonBone.name` on read and writes it as `StringAnsi`, which made every mesh skinned
  to the dangle skeleton invisible. Round-trip one vanilla file and diff it before trusting a converter
  (`games/the-witcher-3/TECHNICAL_CONTRACTS.md` §3).
