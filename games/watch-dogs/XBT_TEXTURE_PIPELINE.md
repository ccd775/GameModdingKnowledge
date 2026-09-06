# Watch Dogs XBT texture pipeline

## Audit donor containers

```powershell
python pipeline/audit_xbt_templates.py `
  .work/vanilla_char01/graphics/characters/char/char01 `
  .work/texture_audit
```

The audit writes `template_matrix.csv` for quick selection and
`template_matrix.json` for complete per-file metadata, hashes, stream pairs,
and validation issues. A nonzero exit indicates a missing stream, orphan high
file, or an unexpected pair layout.

## Build one streamed pair

```powershell
python pipeline/build_xbt_pair.py `
  source.png `
  donor/char01_head_v2_d2.xbt `
  donor/char01_head_v2_d2_high.xbt `
  output/directory
```

The builder converts the PNG twice: once to the low donor's dimensions and mip
chain, and once to the high donor's dimensions and single top mip. It then
preserves each donor XBT header byte-for-byte and injects the corresponding DDS.
Output filenames remain the donor filenames because the low header embeds the
high stream's virtual path. Existing files are refused unless `--overwrite` is
explicitly supplied.

For alpha-tested textures, review the source and material first. The optional
`--separate-alpha` and `--alpha-threshold 0.5` flags are available, but must be
validated visually in game.

## Validation

```powershell
python pipeline/test_xbt_pair_pipeline.py
```

The smoke matrix covers all eight paired signatures found in the vanilla
`char01` donor set. It verifies both DXT1 and DXT5, square and rectangular
textures, every donor resolution tier, DirectXTex parsing, exact donor-header
preservation, exact DDS metadata and byte lengths, byte-identical
`xbt_tool.py` extraction/reinjection, and rejection of a mismatched high DDS.

## Limits

- The builder accepts paired XBT version 123 donors with legacy DXT1 or DXT5
  DDS payloads. It intentionally rejects standalone XBTs and unknown formats.
- It does not assign materials, edit XBG files, create UV atlases, or infer
  which character texture belongs in which material slot.
- It does not reinterpret normal-map channels, choose color-space transforms,
  or guarantee acceptable BC compression quality. Prepare those source images
  before conversion and inspect the final result in engine.
- The bundled `texconv.exe` hash is pinned. A different trusted executable must
  be supplied together with its expected SHA256.
- A passing structural test is not a substitute for an in-game render test.
