# RE4 Modding Shared Knowledge

> Status: active
> Scope: Resident Evil 4 (2023) resource research and character replacement
> Last verified: 2026-08-15
> Build coverage: workflow is general; all concrete build `22377325` values are case snapshots

This directory is the canonical shared entry point for future RE4R Mod tasks in
this workspace. It extracts reusable engineering rules from the Karin Y/Ashley,
Karin Riptide/Luis, Karin Wasakura/Luis, Karin Cloth04/Merchant, Karin
DR03/Merchant, Karin Chrome/Merchant, Karin Nyako/Ada, Karin SSF/Krauser, and
Karin Umbrella/Leon projects without turning any project's routes, versions,
bone counts, hashes, transforms, material names, or tuning values into universal
constants.

The knowledge base is intentionally split into three layers. Its evidence also
includes the accepted DR03/Merchant branch-scoped Chain fallback and the
accepted Chrome/Merchant diagnosis of an unbound source primitive plus a
runtime-only world-contact offset. The accepted Wasakura/Luis sequence adds a
positional UV-stream failure, source-proportion and collider-unit defects,
terminal-helper topology, ground contact, and a bilateral side-skirt fallback.
The Nyako/Ada sequence adds dual-layer PFB binding, zero-file deployment
diagnosis, evaluated-shape visibility, segmented sleeve frames, symmetric
static chest policy, an offline terminal-complete tail candidate whose settling
remains runtime-pending, and a runtime rejection of foot-bone angle as a
flat-sole proxy followed by scoped runtime acceptance of a sole-plane frame.
The Karin SSF/Krauser sequence adds native material-lookup crash forensics,
caller-position/hash progression, the distinction between lookup closure and
cross-array structural closure, and consumer-proven hidden Mesh backing
submeshes for query-only compatibility materials. Its r10-to-r11 continuation
adds crash-window attribution of a Campaign event to a Figure-family consumer,
consumer-scoped material-query sets, complete existing-alias closure, and
scoped runtime acceptance bound to an exact 63/63 installed tree.
The Karin Umbrella/Leon v1-to-v7 sequence adds native-animation translation
versus source-proportion failures, action-specific small-joint pivot audits,
rigid-shell articulation boundaries, all-retained-object shape-state coverage,
final-rest Chain-frame reconstruction, fixed weighted spring anchors,
branch-specific endpoint semantics, deform-chain density, and preservation of
accepted subcontracts through matched negative controls. Its optional voice
add-on adds byte-proven Wwise actor-path aliasing, all-locale sound dependency
closure, missing-path recovery through exact engine hash pairs, and standalone
PAK collision/determinism checks.

1. **Shared contracts** describe how to gather evidence, build, validate, and
   package a Mod.
2. **Project records** remain authoritative for the current state of one Mod.
3. **Case studies** preserve lessons and rejected hypotheses from completed or
   long-running projects.

## Mandatory Reading Order

For a new RE4 task, read in this order:

1. [`AGENTS.md`](AGENTS.md)
2. This index, then the target project's own `AGENTS.md`, full `SOP.md`, input
   lock, consumer matrix, and latest superseding milestone
3. [`EVIDENCE_AND_AUTHORITY.md`](EVIDENCE_AND_AUTHORITY.md)
4. The relevant portions of
   [`CHARACTER_REPLACEMENT_SOP.md`](CHARACTER_REPLACEMENT_SOP.md)
5. [`TECHNICAL_CONTRACTS.md`](TECHNICAL_CONTRACTS.md)
6. A case study only when its problem is genuinely analogous

Before packaging, also read
[`VALIDATION_AND_RELEASE.md`](VALIDATION_AND_RELEASE.md). During diagnosis, use
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md). For a compact start/resume/release
gate, use [`AGENT_CHECKLIST.md`](AGENT_CHECKLIST.md).

## Document Map

| Document | Purpose |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Mandatory behavior and knowledge-maintenance rules |
| [`EVIDENCE_AND_AUTHORITY.md`](EVIDENCE_AND_AUTHORITY.md) | Truth hierarchy, evidence vocabulary, supersession, and report requirements |
| [`CHARACTER_REPLACEMENT_SOP.md`](CHARACTER_REPLACEMENT_SOP.md) | End-to-end, gate-based long-running workflow |
| [`TECHNICAL_CONTRACTS.md`](TECHNICAL_CONTRACTS.md) | Consumer, Mesh, rig, MDF/TEX, Chain, PFB/JCNS, and skeleton contracts |
| [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) | Symptom-led fault isolation and disproven shortcuts |
| [`VALIDATION_AND_RELEASE.md`](VALIDATION_AND_RELEASE.md) | Offline acceptance, deterministic packaging, deployment, and runtime matrices |
| [`AGENT_CHECKLIST.md`](AGENT_CHECKLIST.md) | Short operational checklist for new and resumed tasks |
| [`cases/ASHLEY_KARIN_Y.md`](cases/ASHLEY_KARIN_Y.md) | Ashley replacement case and runtime-isolation lessons |
| [`cases/LUIS_KARIN_RIPTIDE.md`](cases/LUIS_KARIN_RIPTIDE.md) | Luis replacement case and source-state/physics/attachment lessons |
| [`cases/LUIS_KARIN_WASAKURA.md`](cases/LUIS_KARIN_WASAKURA.md) | Runtime-accepted Luis case covering UV streams, collider units, source proportions, ground contact, and mirrored-skirt isolation |
| [`cases/MERCHANT_KARIN_CLOTH04.md`](cases/MERCHANT_KARIN_CLOTH04.md) | Merchant replacement case and bind-space/material/ground-contact lessons |
| [`cases/MERCHANT_KARIN_DR03.md`](cases/MERCHANT_KARIN_DR03.md) | Merchant replacement case and runtime Chain/static-fallback lessons |
| [`cases/MERCHANT_KARIN_CHROME.md`](cases/MERCHANT_KARIN_CHROME.md) | Merchant replacement case and unbound-material/emissive/rigid-ground-correction lessons |
| [`cases/ADA_KARIN_NYAKO.md`](cases/ADA_KARIN_NYAKO.md) | Ada replacement case covering PFB table/RSZ binding, source intent, sleeve frames, deployment proof, Chain terminals, and flat-sole contact frames |
| [`cases/KRAUSER_KARIN_SSF.md`](cases/KRAUSER_KARIN_SSF.md) | Krauser replacement case covering staged load/proportion/crash diagnosis, material lookup progression, MDF-only false closure, hidden Mesh compatibility submeshes, and late Figure/event route attribution |
| [`cases/LEON_KARIN_UMBRELLA.md`](cases/LEON_KARIN_UMBRELLA.md) | Leon replacement case covering animation-rest/proportion separation, finger pivots, rigid shells, saved hair/footwear shape, Chain frames, fixed weighted roots, and tail segment density |
| [`templates/PROJECT_RECORDS.md`](templates/PROJECT_RECORDS.md) | Copyable consumer, candidate, handoff, and test-record templates |

## Truth Hierarchy

Use two related authority orders rather than one ambiguous list.

For scope and state selection:

1. The user's current permissions, exclusions, and acceptance criteria
2. The target project's current `AGENTS.md` and latest non-superseded `SOP.md`
   milestone
3. This shared knowledge base

For concrete paths, counts, hashes, fields, and binary facts within that selected
milestone:

1. SHA-bound machine-readable reports for the exact candidate
2. Resources freshly extracted from the current installed game build
3. The source model for authored appearance and the reference Mod for its stated
   donor/control role
4. Case studies, community guidance, and recollection

Project prose selects the applicable milestone and policy; it does not override
the bytes and measurements in the reports that milestone designates. This
knowledge base teaches the method and never replaces current project evidence.

A newer SHA-bound runtime rejection for the exact candidate is fail-closed even
when project prose has not yet been synchronized. Stop promotion, preserve both
the earlier offline evidence and the runtime report, then update the project
state before planning another candidate.

## Fact Classes

Every important claim should be recognizable as one of these classes:

| Class | Meaning | Reuse rule |
| --- | --- | --- |
| `invariant` | Engineering rule independent of one observed build | Reuse unless contradicted by format/tool evidence |
| `build-sensitive` | Depends on game build, archive priority, schema, or resource version | Re-extract and re-verify after any build/tool change |
| `case-derived` | Worked or failed in a named project/candidate | Use as a hypothesis, not a constant |
| `hypothesis` | Plausible but not yet accepted | Test with a single-variable candidate |
| `rejected` | A specific candidate disproved the stated sufficiency claim | Preserve the rejection and its exact scope |

Routes such as `cha100`, `cha300`, or `chi100`; resource suffixes; PFB offsets;
bone counts; transforms; transparency floors; Chain parameters; and archive
hashes are `build-sensitive` or `case-derived` unless current evidence proves
otherwise.

## Evidence Vocabulary

- `reference-inferred`: inferred from a donor, native resource comparison,
  community source, or earlier case.
- `offline-accepted`: every offline gate declared applicable to the claim scope
  passes. Package/re-extraction gates apply only to package claims. This does not
  prove in-game behavior or later project phases.
- `runtime-load-pass`: a named candidate cold-loads into gameplay, but visual,
  animation, or physics behavior may still be wrong.
- `runtime-rejected`: runtime evidence bound to a named candidate finds a
  blocking defect. The candidate stops promotion, while independently accepted
  offline subcontracts remain historical evidence within their narrow scope.
- `runtime-confirmed`: the user confirms a named candidate for a declared
  scenario matrix or an explicitly scoped package acceptance. Unreported
  routes, actions, lighting, cold-start, conflicts, and rollback remain
  `not-observed`.
- `rejected`: evidence disproves the candidate or the claim that a change alone
  is sufficient.

See [`EVIDENCE_AND_AUTHORITY.md`](EVIDENCE_AND_AUTHORITY.md) for the fields
required before using these labels.

## Current Case Sources

The shared summaries link back to the original project evidence. The most
important source documents are:

- Ashley: [`../KarinYReplaceAshley/AGENT_RE4_MOD_PLAYBOOK.md`](../../SOURCE_REFERENCES.md#local-only),
  [`../KarinYReplaceAshley/AGENTS.md`](../../SOURCE_REFERENCES.md#local-only), and
  [`../KarinYReplaceAshley/SOP.md`](../../SOURCE_REFERENCES.md#local-only)
- Luis: [`../KarinRiptideReplaceLouis/AGENTS.md`](../../SOURCE_REFERENCES.md#local-only)
  and [`../KarinRiptideReplaceLouis/SOP.md`](../../SOURCE_REFERENCES.md#local-only)
- Luis Wasakura: [`../Karin_wasakura_replace_luis/AGENTS.md`](../../SOURCE_REFERENCES.md#local-only),
  [`../Karin_wasakura_replace_luis/SOP.md`](../../SOURCE_REFERENCES.md#local-only),
  the initial UV1
  [`runtime rejection`](../../SOURCE_REFERENCES.md#local-only),
  the r3
  [`geometry`](../../SOURCE_REFERENCES.md#local-only)
  and
  [`physics`](../../SOURCE_REFERENCES.md#local-only)
  audits, the r5
  [`bilateral-skirt contract`](../../SOURCE_REFERENCES.md#local-only),
  and the final
  [`user acceptance`](../../SOURCE_REFERENCES.md#local-only)
- Merchant: [`../KarinCloth04ReplaceMerchant/AGENTS.md`](../../SOURCE_REFERENCES.md#local-only),
  [`../KarinCloth04ReplaceMerchant/SOP.md`](../../SOURCE_REFERENCES.md#local-only),
  runtime reports [`R1`](../../SOURCE_REFERENCES.md#local-only),
  [`R2`](../../SOURCE_REFERENCES.md#local-only),
  [`R3`](../../SOURCE_REFERENCES.md#local-only),
  and [`R4`](../../SOURCE_REFERENCES.md#local-only),
  plus the R2 bind-space
  [`notes`](../../SOURCE_REFERENCES.md#local-only)
  and [`machine report`](../../SOURCE_REFERENCES.md#local-only)
- Merchant DR03: [`../Karin_DR03_replace_merchant/AGENTS.md`](../../SOURCE_REFERENCES.md#local-only),
  [`../Karin_DR03_replace_merchant/SOP.md`](../../SOURCE_REFERENCES.md#local-only),
  the R3 backpack
  [`runtime rejection`](../../SOURCE_REFERENCES.md#local-only),
  the R4
  [`runtime acceptance`](../../SOURCE_REFERENCES.md#local-only),
  and the R4
  [`single-variable contract`](../../SOURCE_REFERENCES.md#local-only)
- Merchant Chrome: [`../Karin_Chrome_Replace_Merchant/AGENTS.md`](../../SOURCE_REFERENCES.md#local-only),
  [`../Karin_Chrome_Replace_Merchant/SOP.md`](../../SOURCE_REFERENCES.md#local-only),
  the source primitive/material
  [`audit`](../../SOURCE_REFERENCES.md#local-only),
  and the R2
  [`runtime acceptance`](../../SOURCE_REFERENCES.md#local-only)
- Ada Nyako: [`../Karin_Nyako_Replace_Ada/AGENTS.md`](../../SOURCE_REFERENCES.md#local-only),
  [`../Karin_Nyako_Replace_Ada/SOP.md`](../../SOURCE_REFERENCES.md#local-only),
  the R2/R3 PFB visibility
  [`runtime sequence`](../../SOURCE_REFERENCES.md#local-only),
  the R5
  [`zero-file deployment report`](../../SOURCE_REFERENCES.md#local-only),
  the R7
  [`sleeve/BodyRope audits`](../../SOURCE_REFERENCES.md#local-only),
  the R8
  [`flat-sole rejection`](../../SOURCE_REFERENCES.md#local-only),
  the R9
  [`sole-plane audit`](../../SOURCE_REFERENCES.md#local-only),
  and the scoped Thin
  [`user acceptance`](../../SOURCE_REFERENCES.md#local-only)
- Krauser SSF: [`../Karin_SSF_Replace_Krauser/AGENTS.md`](../../SOURCE_REFERENCES.md#local-only),
  [`../Karin_SSF_Replace_Krauser/SOP.md`](../../SOURCE_REFERENCES.md#local-only),
  the r9
  [`checkerboard rejection`](../../SOURCE_REFERENCES.md#local-only),
  the
  [`material contract`](../../SOURCE_REFERENCES.md#local-only)
  and
  [`BodyUpdater consumer audit`](../../SOURCE_REFERENCES.md#local-only),
  the r10
  [`Mesh closure`](../../SOURCE_REFERENCES.md#local-only)
  and
  [`single-variable isolation`](../../SOURCE_REFERENCES.md#local-only),
  the r10 Chapter 14
  [`Figure/event rejection`](../../SOURCE_REFERENCES.md#local-only),
  the r11 Figure
  [`Mesh/MDF closure`](../../SOURCE_REFERENCES.md#local-only)
  and
  [`single-variable isolation`](../../SOURCE_REFERENCES.md#local-only),
  and the r11 scoped
  [`user acceptance`](../../SOURCE_REFERENCES.md#local-only)
- Leon Karin Umbrella: [`../Karin_Umbrella_Replace_Leon/AGENTS.md`](../../SOURCE_REFERENCES.md#local-only),
  [`../Karin_Umbrella_Replace_Leon/SOP.md`](../../SOURCE_REFERENCES.md#local-only),
  the v1
  [`initial runtime rejection`](../../SOURCE_REFERENCES.md#local-only)
  and v2
  [`stable runtime rejection`](../../SOURCE_REFERENCES.md#local-only),
  the v4
  [`frame negative control`](../../SOURCE_REFERENCES.md#local-only),
  the v5
  [`deformation root-cause audit`](../../SOURCE_REFERENCES.md#local-only),
  the v6
  [`hair saved-state/root audit`](../../SOURCE_REFERENCES.md#local-only),
  the v7
  [`deformation contract`](../../SOURCE_REFERENCES.md#local-only)
  and
  [`matched stage diff`](../../SOURCE_REFERENCES.md#local-only),
  and the scoped
  [`user acceptance`](../../SOURCE_REFERENCES.md#local-only)

Large JSON reports, extracted native resources, private references, models, and
runtime candidates stay in their project directories. SharedKnowledge stores
the method, a concise result, and links to evidence rather than duplicating
private or fast-changing artifacts.

## Maintenance Rules

- One fact has one canonical home. Other documents link to it instead of
  copying another live parameter table.
- Shared documents describe reusable contracts. Current hashes and candidate
  state stay in project reports or case snapshots.
- A new game build, tool version, add-on version, or PFB schema invalidates the
  corresponding `build-sensitive` conclusions until rechecked.
- Historical failures are never erased. Narrow their claim if later evidence
  shows the original conclusion was too broad.
- New milestones append a date and an explicit `supersedes` statement. Do not
  silently edit an old snapshot into a different result.
- Do not copy private reference-Mod payloads or licensed source models into this
  directory. Record only identity, hash, authorization boundary, and evidence
  links when needed.
