# Case Study: Karin Riptide Replaces Luis

> Status: final offline package snapshot
> Project: `RE4/KarinRiptideReplaceLouis`
> Snapshot date: 2026-08-04
> Game build: Steam `22377325`
> Evidence level: Gates 0-6 offline-accepted; runtime not run by the agent
> Reuse class: case-derived; all routes, offsets, counts, transforms, and tuning values are project-specific

## Scope And Deliverable

This project produced a campaign-and-Mercenaries Luis replacement with static
face, materials, secondary motion, route aliases, current-build control patches,
and a Fluffy-compatible package.

The user explicitly prohibited automatic game testing. The task did not launch
RE4 or the Mod Manager and did not write to the game directory. The final r4
package is:

```text
Output/Karin_Riptide_Replace_Luis_RE4R_build22377325.zip
SHA-256 EF62F5AAD97FBF110039A42C0449D069662EFDB2057F56014CC25C7FAE61B5B0
52 runtime resources / 58 total files
```

This package is `offline-accepted`, not `runtime-confirmed`.

The authoritative source is the project
[`AGENTS.md`](../../../SOURCE_REFERENCES.md#local-only), latest r4 milestone in
[`SOP.md`](../../../SOURCE_REFERENCES.md#local-only), and
[`final-package-verification.json`](../../../SOURCE_REFERENCES.md#local-only).

## Runtime Evidence Timeline

The project contains runtime evidence, but it applies to earlier delivered
trees, not the final r4 package:

| Stage | Evidence | What it establishes |
| --- | --- | --- |
| Earlier package/candidates | User screenshots and observations of stiff/spinning hair, missing tail motion, high-heel/ground issues, missing translucent surfaces, upturned fringe/ribbons, visor overlap, and water-gun/raincoat overlap | These symptoms occurred in the tested earlier tree and motivated isolated offline corrections |
| r3/r4 rebuilds | SHA-bound Mesh, Chain, material, PFB, geometry, determinism, and package reports | The cumulative fixes are internally consistent and deployable offline |
| Final r4 ZIP | `not-run-user-owned` | No claim yet about final in-game appearance, animation, physics, transparency, or route coverage |

Do not erase the earlier user feedback, but do not transfer its runtime evidence
level to a later package whose bytes the user has not tested.

## Luis Consumer Snapshot

The current-build matrix resolved these project routes:

| Role | Runtime consumers |
| --- | --- |
| Body Mesh | campaign `cha300/00`, variant `cha309/00`, Mercenaries `chi100/00`, variant `chi101/00` |
| Body MDF | corresponding `cha300`, `cha309`, `chi100`, `chi101` body aliases and observed variants |
| Static face Mesh | `cha300/10`, `cha300/11`, `chi100/10`, `chi100/11` |
| Static face MDF | those face paths plus observed `cha300/12` material consumer |
| Head/hair Mesh+MDF | `cha300/20`, `chi100/20` |
| Suppressors | `cha300/21`, `chi100/12` |
| Body Chain | `cha300_00`, `chi100_00`, `chi101_00` |
| Head Chain | `cha300_20`, `chi100_20` |
| Character FBXSKEL | `cha3/cha3.fbxskel.5`, `chi1/chi1.fbxskel.5` |

The build did not manufacture missing `cha309`/`chi101` head or Chain aliases.
Reference-only `01/02/50` style paths were not copied without current consumers.

The shared `ch00/ch_male0_joint.fbxskel.5` path was deliberately excluded. It
had a broader blast radius and a different joint set. Character-scoped skeleton
paths were sufficient.

Sources:

- [`consumer-matrix.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`LUIS_CONSUMER_CONTROL_AUDIT.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`native-luis/SOP.md`](../../../SOURCE_REFERENCES.md#local-only)

## Reference And Current-Build Controls

The Hishi reference supplied route clues, a target animation/rest donor, scoped
suppressors, and comparison data. It also contained payloads that were excluded:
weapon/prop, microphone, parfait, environment/test, author texture, and UI data.

Its Mercenaries PFB was an old byte-identical campaign copy that redirected
consumers toward campaign resources. It was specifically rejected as current
Mercenaries authority.

Current native PFBs and current route resources were re-extracted. The final
package patched only three current PFB Bool fields to disable JointConstraints;
JCNS and JMAP remained native and were not packaged. The offsets and single-byte
changes in `patch_luis_joint_constraints.py` are valid only for the locked input
hashes of this build.

## Mesh And Rig Architecture

The source was partitioned by body `00`, static face `10/11`, and head/hair `20`
consumers. The target used an explicit humanoid map, a donor animation skeleton,
required parent-closed current JCNS helpers, and renamed ASCII physical branches.

Case snapshot:

- body: 208 bones, 142 weighted;
- static face: 17 bones, one weighted (`Head` strategy);
- head/hair: 66 bones, 47 weighted, including three zero-weight terminal helpers;
- per-vertex policy: at most four normalized influences, no unweighted vertices;
- visibility/submesh policy: always-visible `Group_0` plus preserved material
  fragments and explicit transparent ordering.

These counts and policies are not generic Luis constants.

The static face does not support blinking, eye tracking, lip sync, or expressions.
Preserving native JMAP did not change that declaration.

## Source Saved-State Audit

The highest-value source lesson was that deleting shape keys without evaluating
saved values discards authored geometry.

Two real defects had this cause:

1. `Body_base:Foot_HighHeel=1.0` was saved but not baked, leaving the foot outside
   the intended shoe pose.
2. `Riptide_SunVisor:Extend_Front=1.0` was saved but not baked, leaving the visor
   interpenetrating the fringe.

The corrected builder recorded requested/applied values and affected vertices
before deleting keys. Blend and FBX agreed on the visor saved state.

The visor shape could not be replaced by one rigid translation: that would move
the rear band and leave a large non-rigid residual. The correct fix was the exact
saved `Extend_Front` deformation.

Sources:

- [`VISOR_FRINGE_CLEARANCE_AUDIT.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`luis-visor-clearance-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`attachment-clearance-acceptance.json`](../../../SOURCE_REFERENCES.md#local-only)

## High-Heel And Ground Correction

The investigation separated foot pose from sole height.

### Rejected variants

- Bake-only corrected the foot shape but left the thick sole underground.
- Foot/Toe weight-driven translation folded many body/shoe triangles and created
  near-zero geometry.
- A below-ankle affine compression passed mechanical geometry gates but reduced
  the shoe's vertical art to about 69.4%; the user rejected the visual change.

### Accepted offline correction

- Bake `Foot_HighHeel=1.0`.
- Rigidly raise both shoes and anklets by `81.975050 mm`.
- Raise body geometry below the ankle by the same amount.
- Linearly reduce body displacement from ankle to zero at the fixed knee.
- Keep all rest bones and geometry above the knee unchanged.

The exact authoring values are project-specific. The reusable pattern is rigid
accessory motion plus a body-only smooth proportional correction that preserves
the accessory artwork and animation skeleton.

The correction required triangle-flip, near-zero-area, edge/area/normal,
shoe-rigidity, matched-floor, determinism, and deformation-pose gates. It still
requires user runtime validation of stance, animation, IK, and ground contact.

Sources:

- [`HIGH_HEEL_AND_GROUND_AUDIT.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`high-heel-lower-leg-shortening-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`high-heel-lower-leg-shortening-comparison.json`](../../../SOURCE_REFERENCES.md#local-only)

## Terminal Dummies For Fringe And Ribbons

Early head Chain candidates produced stiff/upturned fringe and green ribbons.
The source rest directions and exported frame directions were already correct;
blind gravity/quaternion changes would have addressed the wrong layer.

The source optimization had removed VRM terminal bones. A two-node reconstruction
prepended the static parent, leaving the real dynamic root as the Chain terminal.
Because the final node is normally a dummy, the intended deform root was not
simulated correctly.

The final Mesh added collinear, zero-weight, non-deforming helpers:

```text
KRH_034 -> KRH_051    central fringe
KRH_044 -> KRH_052    left green ribbon
KRH_046 -> KRH_053    right green ribbon
```

All campaign/Mercenaries head Chains used these real-root -> dummy paths, with no
static fallback. A helper's reliable binary proof was zero positive weight
assignments after re-import, not Blender `use_deform`.

When terminal helpers cannot be added safely, removing the invalid group and
retaining the correct static source pose is safer than a wrong dynamic chain,
but must be documented as loss of physics.

Sources:

- [`source-vrm-physics-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`karin-riptide-luis-chain-build.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`karin-riptide-luis-chain-frame-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`03_terminal_dummy_dynamic_roots`](../../../SOURCE_REFERENCES.md#local-only)

## VRM-To-Chain Lessons

- The VRM supplied spring/collider topology and semantics, not a one-to-one RE
  parameter map.
- A measured humanoid-anchor fit first proved VRM-to-optimized-rig coordinates.
- Each runtime route retained its own current Chain donor/header.
- Ashley solver settings were transferred only after shared source geometry and
  rest paths were numerically verified, not by list index.
- Long twin tails and tail needed conservative damping/spring/wind tuning, but
  topology and frame checks preceded tuning.
- Branches without source VRM physics definitions remained static.
- Repeated drive, overlapping terminal paths, and ordinary one-node groups were
  rejected.
- Moving water-gun dynamic rest bones forced all affected body Chains to rebuild.

The case used a frame angular error gate below `0.001 rad`; that threshold is a
project acceptance value, not a universal solver limit.

## Water Gun And Raincoat Assembly

The water gun appearing inside the raincoat was initially easy to confuse with
transparent sorting. Source, authoring, and final geometry comparison showed the
authoring assembly was already wrong while export error was sub-micrometre.

Root cause:

- source water gun used a `Spine` anchor mapped to Luis `Spine_0`;
- raincoat back used `Chest` mapped to Luis `Spine_2`;
- independently mapping two related parts changed their relative torso frame.

The final `chest-coherent` correction applied one `Chest -> Spine_2` rigid
transform to all water-gun geometry and the eleven `KRB_070..080` rest bones.
`KRB_070` retained its old parent for that candidate so animation-parent
semantics were not changed at the same time.

The accepted offline audit measured the gun shell fully outside the raincoat,
with minimum/median clearance near `25.96/80.11 mm`. These are case gates. The
reusable rule is to preserve the source assembly with one coherent anchor
transform and move the complete attachment bone package.

Sources:

- [`luis-watergun-clearance-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-feedback-watergun-clearance-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`attachment-clearance-acceptance.json`](../../../SOURCE_REFERENCES.md#local-only)

## Transparency And Draw Order

The raincoat white panels and visor brim disappeared because alpha-test/cutout
materials discarded low-alpha pixels. They required dedicated continuous
transparent materials and opacity textures.

Case-specific final plan:

- raincoat-only ATOC with opacity floor `128/255`;
- visor-only ATOC with opacity floor `96/255`;
- water-gun transparent region retained source continuous alpha;
- water-gun transparent material/submesh serialized before raincoat transparent
  material/submesh.

The ordering addressed transparent composition. It did not solve the geometric
water-gun/raincoat intersection; that required the anchor correction above.

All custom TEX were complete ordinary-path files, with full mips and zero custom
streaming copies. Generated textures were decoded and compared channel by
channel. Exact atlas packing is recorded in the project material report and
must not be copied to another source texture set without re-audit.

Sources: [`material-build-report.json`](../../../SOURCE_REFERENCES.md#local-only)
and [`runtime-feedback-surface-alpha-audit.json`](../../../SOURCE_REFERENCES.md#local-only).

## PFB, JCNS, And Skeleton Result

Current-build PFB semantic patches disabled three JointConstraints Bool fields.
Each output kept size/resource arrays/userdata unchanged, parsed to EOF, and had
exactly the expected byte/semantic change. The byte offsets are tied to this
build's locked PFB hashes.

Thirty-two unweighted current Luis JCNS compatibility helpers completed the body
bone contract, but JCNS itself remained incompatible with the retargeted rest
skeleton and was disabled by the scoped PFB patches. No `.jcns`, `.jmap`, or
global `.skeleton.5` resource entered the package.

The tiny suppressor Meshes hid proven auxiliary consumers without importing
unrelated reference materials or strands.

Sources:

- [`luis-pfb-semantics-current-and-reference.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`pfb-joint-constraints-patch-report.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`final-resource-map.json`](../../../SOURCE_REFERENCES.md#local-only)

## Final Offline Gates

The r4 package gate required:

- two byte-identical Mesh builds and per-slot semantic round-trips;
- high-heel, visor, attachment, and deformation audits;
- five route-specific Chain builds twice plus frame and ancestry audits;
- three MDF plus 17 TEX outputs twice, decoded and with zero streaming;
- three exact current-PFB field patches;
- character-scoped FBXSKEL only;
- a forbidden-resource audit;
- exact 52-runtime-resource map;
- two identical packages and clean ZIP re-extraction equal to expanded output;
- no game/Mod Manager launch and no game-directory write.

The 52-resource snapshot was 12 Mesh, 13 MDF, 17 TEX, five Chain, three PFB, and
two FBXSKEL files. The package gate rejected `.jcns`, `.jmap`, `.skeleton.5`, the shared
`ch_male0_joint`, custom `/streaming/` files, and unrelated reference payloads.
These counts are a final-tree assertion for this project, not a template for
another character.

## Required User Runtime Follow-Up

The delivered test matrix should verify:

- campaign and Mercenaries routes/variants;
- central fringe and green-ribbon rest pose, settling, and rapid turns;
- twin tails and tail stability;
- water-gun clearance during torso motion;
- raincoat, visor, and water-gun transparency/draw order independently;
- high-heel foot containment and sole-ground contact;
- static face limitation and any native remnants;
- cold load, cutscene transitions, and relevant lighting/wetness states.

## Rights Boundary

The source VRM metadata recorded restrictive terms including no redistribution,
no commercial use, and a violence-content restriction that may conflict with an
RE4 use. The technical project does not establish that the user or author has
granted an exception. Do not redistribute or expand the package's use until the
rights holder confirms permission, or the user provides evidence of permission
from the rights holder. A Mod's technical readiness never overrides its source
license.

## Key Evidence

- [`SOP.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`input-lock.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`source-semantic-contract.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`source-rig-contract.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`consumer-matrix.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`final-mesh-numeric-acceptance.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`mesh-build-determinism.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`material-build-report.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`karin-riptide-luis-chain-build.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`karin-riptide-luis-chain-frame-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`attachment-clearance-acceptance.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`pfb-joint-constraints-patch-report.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`final-package-verification.json`](../../../SOURCE_REFERENCES.md#local-only)
