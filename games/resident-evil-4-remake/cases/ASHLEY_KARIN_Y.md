# Case Study: Karin Y Replaces Ashley

> Status: historical/current-project snapshot
> Project: `RE4/KarinYReplaceAshley`
> Snapshot date: 2026-08-04
> Game build: Steam `22377325`
> Evidence: mixed runtime-confirmed, runtime-load-pass, offline-accepted, and rejected by candidate
> Reuse class: case-derived; no route, count, hash, or parameter is universal

## Scope And Current State

This project replaced Ashley with Karin Y, including body, static face/head,
materials, alternate-costume routing, and secondary motion. It became the main
runtime-isolation laboratory for the workspace.

At this snapshot:

- Candidate 33's default-costume cumulative appearance had user confirmation.
- Candidate 34 added alternate `cha101` routing but did not receive a complete
  alternate-costume regression.
- Candidates 35 and 36 isolated tail-root and neck-length corrections.
- Candidate 37 combined those geometry corrections and was
  `offline-accepted + installed`, not fully `runtime-confirmed`.
- Candidate 37's 62 target files later remained exact while unrelated Luis and
  other files changed the full game tree, so whole-tree acceptance correctly
  became false.
- The user accepted limited right-sleeve droop and some penetration as a known
  limitation; parameter tuning was stopped.

The authoritative live state is the project
[`AGENTS.md`](../../../SOURCE_REFERENCES.md#local-only), full
[`SOP.md`](../../../SOURCE_REFERENCES.md#local-only), and
[`runtime-isolation-candidates.json`](../../../SOURCE_REFERENCES.md#local-only).
This page is a lesson summary.

## Ashley Consumer Snapshot

These roles apply to this Ashley build only:

| Consumer | Observed project role |
| --- | --- |
| `cha100/00` | Default body plus four MDF variants |
| `cha100_00.chain` | Default body, sleeve, skirt, tail, and accessory physics |
| `cha100/10`, `11` | Native face/eye/teeth/faceblend consumers |
| `cha100/20` | Hair consumer; this static-face project also placed visible head/face/accessories here |
| `cha100_20.chain` | Hair, ears, and head-accessory physics |
| `cha100/01` | Independent GPU Cloth/JCNS auxiliary consumer, not a normal body alias |
| `cha100/02`, `21`, `50`, `92`, `93` | Suppression/special consumers; full-body copies are unsafe |
| `cha101/00` | Alternate-costume body/MDF consumer |
| `cha101_00.chain`, `cha101_20.chain` | Alternate-state physics aliases |
| `cha101/01`, `50` | Reference-placeholder semantics preserved |

Candidate 33 looked correct in the default route while an alternate still showed
the donor. This is direct evidence that a visible default replacement does not
prove consumer closure.

Sources:

- [`CURRENT_ASHLEY_PFB_RESOURCE_MAP.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-isolation-candidates.json`](../../../SOURCE_REFERENCES.md#local-only)

## Native, Reference, And Control Lessons

The Satono reference was most valuable as a known-working runtime control and a
path/structure donor. It was not a clean current-build authority.

Important distinctions:

- Costume PFB Mesh components used embedded skeleton data with
  `SharedSkeleton=false`.
- A generic body PFB separately consumed a dummy skeleton.
- Adding an unused skeleton alias did not become a valid fix merely because a
  donor carried an identical file.
- `cha100_01*` PFBs involved GPUC, GPUClothCharacterPart, and JCNS components;
  one enabled flag did not represent the whole dependency graph.
- Candidate 37 retained four default-slot Satono legacy PFB binaries with a
  known stale `Stamp.TestObb` difference. They had scoped compatibility evidence
  in tested scenes, but remain compatibility debt and must never seed a new
  project's PFB plan.

New projects must extract current PFBs and patch supported fields from the
current schema.

## Mesh And Rig Lessons

### Partition and visibility

The original build incorrectly mapped Karin source object enumeration into many
runtime visibility groups. The corrected build used target semantics and an
always-visible `Group_0` policy, with controlled material-based compaction.

Candidate 11 still hung after this correction. Therefore the correction was
structurally valid but not sufficient to solve loading.

### Static face strategy

The project did not implement Ashley facial animation. It retained compatible
eye names where useful but bound the visible eyes to `Head` to avoid bad pivots.
Both cheeks and the mouth-held accessory used the same Head-space transform.
This corrected converging eyes, dirty-looking cheek overlap, and an accessory
embedded in the head without claiming expression support.

### Local rigid packages

Two late geometry corrections established a reusable method:

- Tail root: move the independent tail geometry and `KYB_041..047` rest-bone
  package together by a measured source/target anchor delta.
- Neck length: move the complete visible head package and its dedicated
  `KYH_*` physical bones together while preserving the 11 core animation bones.

The values (`+0.089797616 m` tail and `-0.038076426 m` head in this case) are
project constants only. The reusable lesson is to derive a measured local
transform, move all related geometry/rest bones coherently, freeze unrelated
contracts, and synchronize every consumer alias.

### Offline geometry gates

The final Mesh workflow separated:

- exact topology/material/positive-weight/bone-name/parent checks;
- numeric UV/coordinate/weight quantization checks;
- tighter core-animation matrix tolerances from physical-bone tolerances;
- asymmetric-elbow and crouched-knee deformation tests;
- focused local-package renders and audits.

Case snapshot counts such as body `256/150` total/weighted bones and head
`110/52` belong only to this candidate lineage.

## Material And Texture Lessons

The project established these durable contracts:

- final Mesh material-name order, MDF array order, and submesh material index
  are one contract;
- source Blender Principled parameters can be misleading and require texture/
  donor audit;
- ALBD alpha was not opacity in this packing;
- continuous transparency needed a separate material/submesh rather than only a
  different alpha value;
- all body MDF variants had to be updated together;
- an overly dark metal could be corrected by isolating the dielectric/base-map
  field instead of changing every metal property;
- complete custom TEX used ordinary MDF paths, full mips, deterministic CPU BC7,
  decoded RGBA comparisons, and zero duplicate loose streaming files.

The stocking candidate was independently tested before it entered the
cumulative candidate. This made rollback and attribution possible.

## Chain And Sleeve Investigation

The right long sleeve produced the most important physics lessons.

### Rest orientation came first

A `world-vertical` attempt looked broadly downward in some views but rotated the
sleeve plane about 84 degrees relative to the forearm. The correct
`forearm-coherent` transform applied one `LowerArm.R -> R_Forearm` frame to the
complete sleeve geometry and collapsed strap weights.

Focused gates checked sleeve-cuff and sleeve-root normals relative to the
forearm rather than relying on a beauty render.

### Topology and parameters were separate

- Unlocking internal angle limits did not correct the static shape.
- Splitting overlapping groups restored segmented motion but not full droop.
- Adding a dynamic high-weight root was not sufficient.
- Matching donor gravity was not sufficient.
- Aggressive gravity plus lower spring still produced only slight droop.
- Collision and droop remained independent problems.

The final decision was to preserve a correct rest orientation and accept limited
droop/penetration rather than endlessly stack tuning candidates.

## Runtime Candidate Ladder

The high-signal sequence was:

| Candidate | Single-variable result |
| --- | --- |
| 04 | Unmodified Satono control entered gameplay |
| 13 | Karin head render entered gameplay |
| 14 | Karin body render entered gameplay |
| 15 | Head plus body render entered gameplay |
| 16 | Karin head Chain loaded; hair/ears/accessories moved |
| 17 | Body Chain loaded; sleeve behavior remained wrong |
| 24 | Forearm-coherent sleeve orientation loaded correctly |
| 29 | Corrected head/eyes/cheeks/accessory passed user runtime review |
| 30/31/32 | Hairpin, obi, and stocking isolated changes were accepted |
| 33 | Default-costume cumulative appearance was accepted |
| 34 | Added alternate routing; incomplete runtime regression |
| 35/36 | Tail and neck isolated offline candidates |
| 37 | Tail+neck cumulative, offline-accepted and installed; not fully runtime-confirmed |

Rejected as independently sufficient included:

- Candidate 10: adding JCNS compatibility bones;
- Candidate 11: visibility/group compaction;
- Candidate 12: disabling one GPU Cloth flag;
- Candidate 18: adding sleeve gravity;
- Candidate 22: unlocking internal angle limits;
- Candidates 25-28: topology/root/gravity/spring changes as complete droop fixes.

These results do not say the fields are irrelevant. They say that exact isolated
change did not fully solve the tested symptom.

## Transactional Deployment Lessons

The project exposed two different states that must not be confused:

1. Fluffy completely removed the prior 62-file overlay, leaving the locked empty
   base. The old transaction state was archived and Candidate 37 was installed
   as a fresh transaction.
2. Later unrelated Mods added files outside Candidate 37. Candidate 37 remained
   `62/62 exact`, while the complete tree failed its old-base contract.

A simple state-vs-live Verify could not prove candidate disk or master contract
identity. The correct audit compared master, candidate disk, transaction source,
and live tree. No unexpected files were deleted.

## Stale Documents To Treat Carefully

- `Packaging/README.md` reflects an earlier eight-PFB current-build plan, not the
  Candidate 37 runtime tree.
- `MATERIAL_TEXTURE_PLAN.md` retains an early streaming-pair plan superseded by
  the final ordinary-path-only policy.
- `CANDIDATE18_SLEEVE_CURL_DIAGNOSTIC.md` contains an offline causal hypothesis
  later disproved by Candidate 22 runtime evidence.

This is why current machine reports and latest SOP milestones outrank design
plans.

## Key Evidence

- [`AGENT_RE4_MOD_PLAYBOOK.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`COMMUNITY_RE4_CHARACTER_CONTRACT_RESEARCH.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`SKELETON_JCNS_RUNTIME_CONTRACT_AUDIT.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`CHA100_01_PFB_CONTRACT_AUDIT.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`runtime-isolation-candidates.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`final-mesh-numeric-acceptance.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`tail-neck-source-audit.json`](../../../SOURCE_REFERENCES.md#local-only)
- [`RUNTIME_INSTALL_AUDIT.md`](../../../SOURCE_REFERENCES.md#local-only)
- [`release-candidate-archives.json`](../../../SOURCE_REFERENCES.md#local-only)
