# Validation, Deployment, And Release

> Status: active
> Scope: offline gates, deterministic packaging, and authorized runtime handling
> Last verified: 2026-08-07

## Validation Principle

Validate both bytes and meaning. A parser accepting a file is weaker than a
semantic round-trip; a semantic round-trip is weaker than user-owned runtime
confirmation. Reports must bind to the exact candidate artifacts by SHA-256.

## Clean-Build Determinism

For each promoted candidate:

1. Start from the locked inputs and canonical parameters.
2. Build into clean output root A.
3. Build independently into clean output root B.
4. Compare path set, size, SHA-256, and semantic reports.
5. Fail on any unapproved nondeterminism.

Do this for Mesh, FBXSKEL, Chain, MDF/TEX, PFB patches, candidate assembly, and
the final archive. If a format contains unavoidable timestamps or ordering, normalize them
or define a payload-manifest authority and document why the outer bytes differ.

Distinguish delivery binaries from authoring containers. Runtime Mesh/TEX/MDF
bytes should match when the format permits it. An authoring `.blend` may embed
its save path and differ bytewise across clean roots; in that case bind each copy
to its own hash and require normalized scene content and complete report
semantics to match. Do not waive runtime-binary determinism merely because the
authoring container has an explained difference.

## Release Orchestration Safety

Classify process safety by the phase's mutation boundary. A fully project-local
offline build may run Blender, conversion, staging, and packaging while RE4 or
Mod Manager is active when the user's boundary permits it and the workflow does
not write the game tree, operate the manager, or depend on mutable runtime
state. Record relevant process state, but never terminate or control user
processes.

Installation, removal, game-directory mutation, Mod Manager operation, and
runtime testing require their own process preconditions. Stop those phases when
RE4 or the designated deployment owner would conflict. A process guard should
enforce the selected boundary, not turn unrelated project-local computation
into a universal stop condition. Chrome Merchant is the reference case for
authorized project-local packaging while user processes were independent; the
Wasakura/Luis package independently followed the same operation-scoped rule.

When an outer PowerShell release script calls a child tool wrapper, the child
must return control on success. Avoid a bare `exit $LASTEXITCODE` in a wrapper
that can be nested, because it can terminate the outer pipeline after a
successful tool run and silently skip downstream phases. Check the native exit
code immediately, throw on non-zero, and return normally on success. The outer
script owns phase order and validates each phase's machine report.

Before a heavy release run:

- parse/compile every participating script;
- verify all locked inputs and prerequisite reports exist;
- run the phase-appropriate process/write-boundary guard;
- stop at the first failed phase;
- require the final verification report, not console completion, before
  promotion.

## Mesh Gates

Required per runtime slot:

- expected magic/version and successful re-import;
- exact or intentionally transformed topology and material-triangle sets;
- valid groups/submeshes and material indices;
- finite coordinates, normals, UVs, and bounds;
- every source material's intended UV set closes through authoring positional
  layer order to the serialized runtime-sampled UV stream per loop/corner;
- a self-round-trip of the generated Mesh is supplemented by an independent
  locked-source UV-intent comparison;
- no unweighted vertices;
- influence count and normalized-weight policy;
- every packed positive palette index resolves through `remapCount` and the
  serialized remap list;
- all-positive-influence vertex-to-pivot distance checks, not dominant-only;
- Mesh-bone local/world translations, neutral target-space bounds, critical
  feature-to-anchor distances, and absolute Mesh/FBXSKEL rest residuals;
- bone names/parents/closure and project-specific matrix tolerances;
- expected and actual Mesh/FBXSKEL comparison counts, with explicit missing
  Mesh, FBXSKEL, weighted, and parent sets; empty intersections fail;
- FBXSKEL names/order/parents/local and world rest/auxiliary tables/segment
  scaling/export mode survive serialized re-import;
- weighted bones are classified as shared-FBXSKEL or proven Mesh-local physical
  branches, with the appropriate closure for each class;
- every slot sharing one FBXSKEL closes on the declared shared set of
  post-export rest matrices;
- the declared FBXSKEL strategy is proven: generated resources are
  byte/semantic deterministic, while a native-template byte-copy requires exact
  shared-core closure, Mesh-local classification for extras, and the
  consumer-proven path/suffix;
- a known-incompatible negative control is rejected by the same validator;
- terminal/collider/JCNS/control references present;
- shape-key bake record covers every retained object and exact saved key/value
  set, reports affected vertices and displacement, contains no unintended
  `removed_without_bake`, and, when a nonzero bake is required, rejects a known
  omitted-bake predecessor;
- short articulated chains report per-joint source-geometry to final-animation
  pivot residuals for every positive influence and pass consumer-specific poses;
- any rigid shoe/cuff/strap/accessory shell either proves compatible articulation
  pivots or uses one coherent rigid bind with explicit lost local motion;
- every declared segment-coherent attachment has exact source-root membership,
  physical/static transform equality, correct target parents, and focused
  continuity under representative limb poses;
- flat-footwear claims validate the actual exported low-contact plane: normal
  tilt, front/back height delta, plane-fit residual/coverage, and left/right
  independent floor residuals; one minimum-Z point and a scalar foot-bone angle
  do not satisfy this gate;
- targeted geometry-clearance checks;
- at least neutral and extreme asymmetric/crouched deformation poses, plus
  target-specific grips and native-translation poses for affected contracts;
- no non-finite vertices, triangle flips introduced by a local correction, new
  near-zero triangles, or extreme edge expansion beyond the project gate.

For a source-fidelity claim, use an independent verifier that reopens the
hash-locked source and evaluates declared saved shape state and transforms. A
topology-preserving contract may compare landmarks, pair distances, and
material-scoped triangle multisets without requiring raw vertex-array identity
where UV seams duplicate vertices. Intentional retopology/LOD work instead needs
a declared surface, silhouette, landmark, material-region, and error contract.
Do not accept only the builder's own self-report.

Keep structural Chain equality and Mesh quantization tolerance as separate
checks. Do not require byte equality where the format legitimately quantizes
geometry, but do require a stated numeric threshold.

## MDF And TEX Gates

- Mesh material-name table and MDF material array close under the declared
  binding: exact order by default, or an explicit current-build name/index remap
  with consumer proof.
- Every submesh material index is valid and intended.
- Every material/property name queried by a gameplay component is present and
  unique in every array that component can address, including query-only names
  with no visible source surface.
- When a returned material index is reused across Mesh/MDF/renderer arrays,
  index equivalence is proved from current-build consumer semantics. Equal
  counts or unordered name sets do not satisfy this gate.
- Every required compatibility-only Mesh slot has a serialized backing submesh
  when the exporter/runtime derives addressable material slots from submeshes.
  Hidden backing geometry is non-degenerate, survives re-import, obeys the
  existing vertex layout and weight policy, and does not expand visible or
  per-bone bounds.
- Adding compatibility slots preserves exact semantics for all previously
  visible submeshes and leaves unrelated runtime resources byte-identical to a
  matched baseline.
- Every source primitive has a valid authored material binding or a counted,
  documented fallback/override; importer-created default slots do not silently
  satisfy this gate.
- Every final triangle closes from source object/material through the declared
  texture page and runtime render class; expected, matched, ambiguous, and error
  counts are explicit.
- The runtime-sampled UV stream equals the source material's intended UV set;
  authoring active/render markers are evidence only after exporter mapping is
  proved.
- UV provenance is recorded per surface. Any local recovery from a sibling
  source proves unique one-to-one correspondence for all target triangle
  corners, per-loop writes, and unchanged non-target UV hashes.
- Re-parse MDF and allow only declared semantic changes.
- TEX magic/version, dimensions, mip count, format, and color space are correct.
- Decode every mip or at least every full-resolution channel plus verified mip
  structure according to the project policy.
- Compare all RGBA channels against the documented source transform.
- Base/emissive factors, textures, and shader-node connectivity are audited for
  surfaces with glow or invariant-white symptoms; disconnected saved values are
  not treated as active shader behavior.
- Transparent/cutout materials are exclusive to the intended geometry.
- Transparent material/submesh order is asserted where relevant.
- No unexpected custom TEX appears under `natives/STM/streaming` under the local
  ordinary-path policy.
- Two complete material builds are byte-identical.

## Preview Gates

Preview is an offline diagnostic gate, not runtime confirmation:

- bind the preview to final Mesh, MDF, and TEX hashes;
- decode the generated final TEX rather than reading only source PNGs;
- apply the documented RGBA/PBR/opacity channel contract;
- render views that cover every changed surface, including focused footwear or
  attachment views when relevant;
- derive camera target and clipping range from the scoped geometry bounds;
- reject blank, clipped, out-of-frame, or materially unbound images;
- use an independently measured target/native/runtime plane for clearance or
  contact claims; a plane computed from candidate minimum bounds is only a
  display aid and cannot pass that gate;
- state explicitly that the preview does not prove engine MMTR behavior,
  animation, IK, sorting, lighting, routes, or world-ground contact.

## Chain Gates

For every packaged Chain route:

- expected magic/version and editor round-trip;
- exact group/settings/node/terminal/collider/wind inventory;
- all referenced bones and full ancestry in the corresponding Mesh;
- no unapproved overlapping/repeated driven paths;
- fixed weighted attachment anchors, first simulated nodes, weighted endpoints,
  and zero-weight terminals are classified per branch; no missing terminals or
  unproven one-node normal groups;
- source weighted deform intervals close onto an approved ordered set of unique
  positive target bones; every many-to-one collapse is explicit and passes the
  declared visible-curve-resolution gate;
- rebuilt frame axes meet the project angular threshold, and inherited donor
  frames are not reused after direction/successor changes without equivalent
  proof;
- source collider units and transforms are explicit; serialized local offsets
  are scale-plausible and reconstruct every intended final world center within
  a declared tolerance, with a unit-defective negative control;
- any moved dynamic rest bones trigger a fresh Chain impact audit; direction or
  local-frame changes require rebuilt Chains, while a proven common rigid
  translation may retain identical bytes only after frame/collider/ancestry
  revalidation;
- semantic diff is limited to intended changes;
- two builds are byte-identical.
- for a runtime-rejected static fallback, every path node is checked against the
  rejected branch membership after merge/segmentation, every affected route has
  zero survivors, retained bones/parents close in Mesh/FBXSKEL, and loss of
  motion is explicit;
- the complete candidate diff proves only the intended Chain resources changed
  and every unrelated runtime resource remained byte-identical to a matched
  accepted baseline.

## PFB And Control Gates

- current-build input hash and schema lock;
- parse to EOF before and after;
- exact expected byte offsets derived from the input, not hardcoded from another
  build;
- exact byte-diff count and semantic field diff;
- every redirected dependency closes across both PFB resource-table strings and
  the relevant RSZ component fields, with expected occurrence counts and final
  table/component path equality;
- unchanged size/resource arrays/userdata unless explicitly intended;
- current consumer matrix contains every patched PFB;
- JCNS/JMAP/skeleton packaging matches the declared support level;
- no broad shared skeleton without a dependency/blast-radius audit;
- two builds are byte-identical.

## Resource-Map Gate

For every runtime entry record:

```text
runtime path
resource type and version
canonical source artifact
consumer and route
action: generated / alias / current patch / suppressor
size
SHA-256
evidence level
```

Also assert forbidden resources and namespaces. Typical project-specific
forbidden sets include unrelated reference props/UI, unexpected JCNS/JMAP,
shared skeleton aliases, and custom streaming duplicates.

Derive the expected resource count from accepted artifacts rather than a stale
handwritten constant. Bind every master-contract resource to the report that
accepted its exact hash, and fail if a report accepts bytes that are no longer
present in staging.

## Candidate Gate

A diagnostic candidate must be a complete tree and have:

- stable ID and parent/baseline;
- one declared semantic variable;
- exact tree manifest;
- an automatically computed diff against the parent;
- an automatically asserted unchanged-resource set; an intended-diff list alone
  cannot detect incidental rebuild drift;
- a negative control using the superseded/rejected parent report or tree, which
  must fail the new policy gate rather than being relabeled as the new candidate;
- a matched baseline containing all other cumulative fixes;
- offline acceptance appropriate to the changed resources;
- user runtime status or explicit `not-run`;
- a rollback candidate.

An isolated pair can be promoted into a cumulative candidate only when the
cumulative diff equals the intended union and is rebuilt from canonical source.

## Package Gate

A Fluffy-compatible package normally has `modinfo.ini`, documentation,
`manifest.sha256`, and `natives/` at its root. Verify:

- no nested candidate wrapper directory;
- normalized safe relative paths;
- exact staging path set and no extras;
- fixed entry order, timestamp, and compression when byte determinism is
  required;
- archive built twice byte-identically;
- every entry streams back with expected CRC/size/hash;
- archive extracted to a clean directory;
- extracted filesystem tree exactly matches staging and manifest;
- install/remove instructions name conflicts and supported build;
- mutually exclusive variants that own the same runtime paths are documented
  and cannot be enabled together;
- evidence level remains unchanged by packaging;
- active process state is recorded but does not reject a workspace-only package
  unless the declared release boundary depends on or mutates live runtime state.

## Runtime Test Matrix

When the user tests, tailor the matrix to the consumer map. A character
replacement commonly needs:

| Area | Examples |
| --- | --- |
| Routes | campaign default/variant, alternate costumes, Mercenaries/other modes |
| Entry | model viewer, chapter entry, save load, cutscene transition, late boss/event phase transition |
| Pose | idle, walk/run, crouch, asymmetric elbows, aim, melee, grab, ladder/vault |
| Rig | shoulder, elbow, wrist, hip, knee, ankle, neck, eyes/face if supported |
| Physics | still settling, small movement, rapid turn, wind, collision, tail/hair/cloth/accessory |
| Rendering | front/back/side, close-up, dark/bright light, wetness, dirt/blood, transparency |
| Geometry | foot-to-shoe fit and shoe-to-world contact as separate checks, attachment-clothing, visor-hair, tail root, neck/shoulder |
| Stability | cold start, route switch, retry/death, cutscene return |

Bind each observation to candidate/build/route/cold-start. A screenshot without
candidate identity is diagnostic input, not a promotion record.

For a candidate that repairs an actor-instantiation or material-lookup crash,
the focused regression must cover both the former crash boundary and the first
fully rendered state after it. Record route-local results separately: a correct
head does not confirm an independently consumed body, and “no crash” does not
confirm textures, material switching, damage-state parameters, or later scene
transitions. If the crash disappears but a blocking checkerboard appears, keep
the no-crash result as a narrow positive observation while classifying the
candidate as runtime-rejected for rendering.

`invariant` test-design rule with `case-derived` runtime evidence: test late
event/phase transitions as independent consumer rows even when an earlier
encounter for the same character passes. Bind route ownership from runtime path
hits at that transition; do not infer it from chapter or mutation semantics.
The Krauser r10 Chapter 11 pass did not cover the Chapter 14 `chf700`
Figure/event path, while r11 closed and cleared that separate blocker. See the
[`r10 rejection`](../../SOURCE_REFERENCES.md#local-only),
[`r11 acceptance`](../../SOURCE_REFERENCES.md#local-only),
and [case snapshot](cases/KRAUSER_KARIN_SSF.md#late-transitions-can-activate-a-different-consumer-family).

A blocking defect can reject an exact candidate even when process state or some
positive-test fields were not observed. Record those fields as `not observed`
and keep all positive conclusions limited to the visible scenario.

Record visual orientation separately from source-bone identity. A screenshot
can establish collapse, inflation, or cross-body appearance without proving
which named mirrored branch moved. Promote a directional/branch claim only
after an explicit-membership matched candidate or equivalent runtime evidence.

An explicit user acceptance immediately following one uniquely identified
package handoff can confirm that package for the stated acceptance scope even
when the user does not repeat the hash. Record the task-context binding and its
qualification. Do not infer an itemized route, action, cold-start, lighting,
conflict, or rollback matrix that the user did not report; keep those fields as
`not observed` and avoid broader compatibility claims.

When a read-only live-tree snapshot is available at feedback-record time,
persist every destination's expected/actual size and SHA-256, not only an
aggregate `N/N` count. This strengthens candidate binding but remains a
point-in-time observation; it neither proves earlier deployment steps nor
authorizes later tree mutation. The
[`r11 acceptance recorder`](../../SOURCE_REFERENCES.md#local-only)
and its [report](../../SOURCE_REFERENCES.md#local-only)
are the case-derived example.

Keep runtime feedback outside the tested archive. Updating package-internal
documentation or evidence after the test changes the archive hash and creates a
new candidate that has not been runtime-confirmed. Append a project report and
update the project SOP while preserving the accepted ZIP bytes.

## Authorized Runtime Deployment

Only perform these steps when the user's current request authorizes installation
or runtime testing.

Choose exactly one deployment owner:

- **External loose-tree script:** RE4 and Fluffy Mod Manager are both closed.
  The script uses the manifest-bound transaction below.
- **Fluffy-managed install:** RE4 is closed while Fluffy is the sole writer.
  Do not run an external installer concurrently. Finish the enable/disable or
  import/remove operation, close Fluffy, then perform the independent tree audit
  before launching RE4.

Rules common to both modes:

- Never recursively clear `natives`.
- Snapshot process state and the current tree first.
- After a managed enable/import, verify that the entry owns the expected
  non-zero deployed-file set and that representative target hashes match before
  launching. An enabled label with zero deployed files is not a payload runtime
  test and must not be used to reject Mesh/PFB/material binaries.
- An external script must reject every same-path/different-hash target. A
  Fluffy-managed install must instead make same-path Mod conflicts and priority
  explicit in Fluffy, then let Fluffy alone rebuild its managed tree; never use
  an external copy to bypass that conflict decision.
- For an external script, write transaction state as `installing` before
  copying, copy only `missing` paths, record but do not own `same` paths, verify,
  and then mark `installed`.
- For an external-script rollback, remove only paths created by that transaction
  and only when current hashes still match the installed candidate.
- For a Fluffy-managed operation, treat Fluffy's rebuilt tree as external state;
  take a new post-operation snapshot instead of claiming external-script
  ownership of its files.
- Prove all non-candidate paths are unchanged.

## Four-Way Runtime Audit

A simple Verify that compares an old transaction state with the live tree is not
enough. The authoritative audit compares:

1. master candidate manifest;
2. current candidate files on disk;
3. transaction state's recorded source bytes;
4. actual game tree.

This catches candidate-disk drift and distinguishes complete external removal
from unrelated base drift.

If all created candidate paths disappear and the live tree equals the locked
base, archive the stale state and treat any reinstall as a new transaction. Do
not fake a successful remove.

If candidate paths remain exact but unrelated files were added, the candidate
subset may be valid while the whole-tree acceptance is false. Preserve those
external files and stop until a safe fresh baseline can be established.

## Game Update Procedure

After an update:

1. stop using old build-sensitive conclusions;
2. lock the new executable, manifest, PAK set, and indexes;
3. rebuild the current native consumer matrix;
4. re-extract and compare every replaced resource and dependency;
5. re-derive PFB/RSZ offsets and schemas;
6. re-run tool identity tests for changed versions;
7. rebuild all binaries and packages;
8. require a new runtime matrix before claiming compatibility.

Do not relabel an old package as supporting a new build because paths or version
suffixes appear unchanged.

## Release Record

The final handoff should state:

- package path, size, SHA-256, and manifest digest;
- supported build/platform;
- runtime resource and total file counts;
- routes covered and explicitly unsupported behavior;
- completed offline gates;
- runtime evidence level and scenarios actually tested;
- known limitations;
- install/conflict/remove procedure;
- source/license restrictions;
- canonical project reports and exact resume point.
