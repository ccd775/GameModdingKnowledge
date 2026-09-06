# Project Record Templates

> Status: active
> Scope: copyable structures for project-local SOPs and reports
> Last verified: 2026-08-06

These are human-readable templates. Projects should also emit machine-readable
JSON/CSV where automated gates consume the data.

## Project Header

```markdown
# <Project Name> SOP

## Objective

<One measurable outcome.>

## User Boundary

- Game launch: authorized / prohibited
- Mod Manager operation: authorized / prohibited
- Game-directory writes: authorized / prohibited
- Mutable deployed tree used as build authority: authorized / prohibited
- Process guard boundary: workspace-only / deployment / runtime
- Required deliverable: research / assets / package / installed candidate

## Evidence Vocabulary

- reference-inferred
- offline-accepted
- runtime-load-pass
- runtime-rejected
- runtime-confirmed
- rejected

## Immutable Inputs

| Role | Path | Size | SHA-256 | License/scope |
| --- | --- | ---: | --- | --- |

## Build And Tools

| Item | Version/build | SHA-256/provenance | Status |
| --- | --- | --- | --- |

## Explicit Exclusions

- <unsupported route, facial animation, unrelated reference payload, etc.>
```

## Consumer Matrix

```markdown
| Route/mode | Runtime path | Type/version | Consumer role | Current source | Reference evidence | Planned action | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| campaign/default | ... | mesh/... | body | patch PAK hit | donor path | replace | offline-accepted |
| alternate | ... | chain/... | absent probe | missing | reference only | preserve absent | reference-inferred |
```

Machine-readable rows should also contain:

```json
{
  "route_family": "campaign-default",
  "runtime_path": "natives/STM/...",
  "resource_type": "mesh",
  "resource_version": "derive-current-build",
  "role": "body",
  "current_archive": "resolved archive identity",
  "current_sha256": "...",
  "reference_sha256": "... or null",
  "consumer_evidence": ["pfb path", "runtime log", "native dependency"],
  "action": "replace",
  "canonical_artifact": "project-relative generated path",
  "evidence_level": "offline-accepted",
  "notes": ""
}
```

## Source-To-Runtime Semantic Records

For every material UV contract, record positional routing rather than only the
authoring active layer:

```yaml
source_material: <name>
source_intended_uv: <layer/semantic>
authoring_layers_in_order: []
authoring_active_layer: <name>
exporter_identity: <version/hash>
serialized_runtime_stream: <UV1/UV2/etc>
runtime_material_sample: <stream/field>
loop_corner_coverage: <matched/expected>
locked_source_comparison: pass | fail
self_roundtrip_only: false
```

For every gameplay component that queries material parameters outside ordinary
visible-submesh traversal, record the complete index flow:

```yaml
consumer_component: <PFB/RSZ type and instance>
consumer_resource: <current-build path/hash>
query_material_name: <name>
query_material_hash: <hash>
query_property_names_and_hashes: []
lookup_array: <MDF/Mesh/component table>
returned_material_index: <value or runtime-derived>
downstream_index_consumers:
  - <array/component and disassembly/schema evidence>
mesh_material_index: <value>
mdf_material_index: <value>
index_equivalence_proof: exact-order | explicit-name-remap | unresolved
visible_triangle_count: <n>
backing_submesh_required: true | false | unresolved
backing_submesh:
  vertices: <n>
  triangles: <n>
  nondegenerate: true | false
  serialized_reimport: pass | fail
  vertex_layout_unchanged: true | false
  rig_remap_and_bone_bounds_unchanged: true | false
visible_submesh_semantics_unchanged: true | false
evidence_paths: []
```

For each converted collider, keep enough data to detect unit and stale-transform
errors:

```yaml
source_collider: <id>
source_units: <value>
source_center: []
final_world_center: []
target_owner_bone: <name>
serialized_local_offset: []
local_offset_magnitude: <value>
reconstructed_world_center: []
world_reconstruction_error: <value>
scale_relative_bound: <value>
negative_control: <report/id>
```

For clothing or attachments spanning animation segments, keep static and
physical transfer ownership explicit:

```yaml
segment_id: <left-forearm-sleeve/etc>
source_anchor: <bone>
target_anchor: <bone>
source_roots: []
static_positive_groups: []
physical_bones: []
transform_matrix: []
static_physical_max_matrix_delta: <value>
target_parent_checks: []
focused_pose_checks: []
```

For footwear, do not collapse foot shape, fit, orientation, and floor placement
into one height value:

```yaml
side: left | right
saved_foot_shape: <keys/values/report>
foot_to_shoe_fit: <measurement/report>
sole_source_object: <name>
contact_surface_coverage: <faces/vertices or declared surface selector>
sole_plane_normal: []
sole_plane_rms: <value>
sole_tilt_to_target_plane_degrees: <value>
front_back_height_delta: <value>
independent_floor_reference: <source/report>
floor_residual: <value>
static_physical_shared_matrix: true | false
runtime_ik_contact: pass | fail | not-observed
```

## Candidate Record

```yaml
candidate_id: 03_terminal_dummy_dynamic_roots
parent_candidate: 02_static_fallback
game_build_id: <build>
claim_scope: candidate
artifact_kind: tree
applicable_gates: [mesh, chain, manifest, deterministic-build]
fact_class: case-derived
declared_variable: <one resource or coherent semantic package>
expected_diff:
  paths_added: []
  paths_removed: []
  paths_changed: []
expected_unchanged:
  path_count: <n>
  manifest_or_report: <path/hash>
matched_baseline: <path/id>
build_parameters: []
manifest_sha256: <sha256>
offline_checks:
  parser_roundtrip: pass
  semantic_diff: pass
  deterministic_build: pass
  package_reextract: pass-or-not-applicable
runtime_status: not-run | load-pass | runtime-rejected | confirmed
runtime_scope:
  routes: []
  costumes: []
  scenarios: []
limitations: []
evidence_paths: []
rollback_candidate: <id>
```

## Rejected Hypothesis

```markdown
### <Hypothesis ID>: <Narrow claim>

- Candidate: `<id>`
- Baseline: `<matched id>`
- Exact variable: `<field/resource>`
- Test scope: `<build/route/chapter/cold start>`
- Observation: `<what happened>`
- Rejected statement: `<what this result disproves>`
- Not disproved: `<nearby broader possibilities still open>`
- Evidence: `<reports/logs/screenshots>`
```

## Runtime Feedback Record

```yaml
date_utc: <ISO-8601>
reporter: user
candidate_id: <id>
archive_sha256: <sha256>
package_binding:
  method: hash-repeated | unique-immediate-handoff | context-scoped-multiple-handoff | install-tree-manifest | unresolved
  qualification: <none or exact limitation>
game_build_id: <build>
cold_start: true | false | not-observed
route: <campaign/mercenaries/etc>
costume: <name/id>
chapter_or_entry: <location>
action_pose: <idle/run/aim/etc>
camera_and_lighting: <view/condition>
observations:
  - layer: static-geometry | physics | transparency | routing | loading
    result: <description>
    visual_orientation: <verbatim left/right/cross-body wording or not-applicable>
    source_branch_identity: <verified name/set or unresolved>
    identity_evidence: <matched candidate/report or none>
blocking_symptoms: []
positive_observations: []
process_state_at_capture: <observed state or not-observed>
deployment_evidence:
  manager_entry_enabled: true | false | not-observed
  deployed_file_count: <n or not-observed>
  sampled_target_hashes: []
attachments:
  - <screenshot/log path>
evidence_level_after_record: runtime-load-pass | runtime-rejected | runtime-confirmed | rejected
untested_scope: []
scope_limitations: []
```

## Release Record

```markdown
## Release Candidate

- Package: `<path>`
- Size: `<bytes>`
- SHA-256: `<sha256>`
- Manifest digest: `<sha256>`
- Supported build/platform: `<value>`
- Runtime resources / total files: `<n> / <n>`
- Routes covered: `<list>`
- Mutually exclusive variants / same-path conflicts: `<list>`
- Evidence level: `<value>`
- Runtime validation: `<scope or not-run-user-owned>`
- Operation/process boundary: `<workspace-only or deployment/runtime guard>`
- Known limitations: `<list>`
- Forbidden-resource audit: `pass`
- Two-build determinism: `pass`
- Clean re-extraction: `pass`
- Install/conflict/remove instructions: `<path>`
- Source/license restriction: `<summary>`
```

## Resume/Handoff Block

```text
Objective:
User authorization boundary:
Current evidence level:
Immutable inputs and hashes:
Game build/platform:
Pinned tools/schemas:
Current consumer matrix:
Current candidate:
Candidate file count / manifest digest:
Exact differences from prior accepted baseline:
Canonical install state or not-installed boundary:
Processes at last audit:
Offline checks completed:
Runtime scenarios completed:
Latest exact-candidate runtime feedback:
Runtime positive-observation scope:
Rejected hypotheses:
Known limitations:
Next single variable:
Exact resume commands:
Evidence directory:
Rollback procedure:
Supersedes:
```
