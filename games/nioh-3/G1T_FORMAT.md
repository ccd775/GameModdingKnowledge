# Nioh 3 G1T, version 0066, storage type 3 (zlib + DX12 64 KB tiles)

Tools: [`n3_g1t.py`](../../portable-kits/nioh-3/README.md) (decode / encode / constant) and `n3_g1t_resize.py` (new size) in the portable kit. Established from 8 vanilla v2.0.0.2 samples: `0xad4f6a70` (BC7 256, 7 mips,
16-layer array), `0x1306ac15` (BC7 256, 7 mips, 2-layer array), `0x8b541440` / `0xe0739e0c` / `0x15f4a3b5`
(BC7 2048, 10 mips), `0x7f1eb597` (BC1 2048, 10 mips), `0x122d6017` (BC1 512, 8 mips), `0xbbc1ade7`
(R32G32B32A32_FLOAT 1x1, 1 mip, plane array of 1). All of them are single-texture files. The reference parser is
MrIkso RDBExplorer 22e72d8 `G1TParser.cs`. "Verified" below means it holds for every sample and the round trip
(decode, then re-encode onto an all-zero buffer) reproduces the vanilla decompressed bytes exactly.

## Container header (little endian)

| off | size | value in samples | meaning |
|---|---|---|---|
| 0 | 4 | `GT1G` | magic |
| 4 | 4 | `6600` | version (ASCII) |
| 8 | 4 | = file length | file size, verified |
| 12 | 4 | 32 | offset of the texture offset table |
| 16 | 4 | 1 | texture count |
| 20 | 4 | 10 | platform (reference: WinDX12) |
| 24 | 4 | 0 | global metadata size |
| 28 | 4 x count | 0, 3 or 4 | per-texture "normal map flags" (reference name). 3 on the NORMAL map, 4 on both arrays, 0 elsewhere. **Meaning unknown**, so it is preserved. |
| table | 4 x count | 4 | texture header offset, relative to the table |

## Texture header (8 bytes, at table + offset)

`b0`: mip count in the high nibble, load type in the low nibble (0 PLANAR, 3 PLANE_ARRAY in the samples). `b1`:
format (0x59 BC1, 0x5F BC7, 0x04 R32G32B32A32_FLOAT here; 0x5C BC4 and 0x5D BC5 come from the reference).
`b2`: log2 width in the low nibble, log2 height in the high nibble. `b3`: log2 depth (0). `b4..b6` = `00 10 21`
in every sample (**unknown**). `b7` = 0x12: extra header version.

## Extra header (12 bytes)

`u32 size` (12), `f32 z_scale` (-1.0), `u16 ex_info` (low nibble = faces, 0 in every sample; the rest = array
count: 16 / 2 / 1 for the arrays, 0 for planar), `u8 storage` (= 3 in every sample), `u8 byte11`.
`byte11` is 1 in `0x8b541440` (COLOR), `0x15f4a3b5` and `0x122d6017`, and 0 in the others. It may be an sRGB flag
(**unverified**). It is preserved, and DDS output is always written as UNORM.

Slices per mip: `S = depth * layers * max(1, faces)`. This is the reference parser's meta stride, and the table
sizes confirm it (for example, 16 slices x 7 meta rows x 16 B gives the 1964-byte table of `0xad4f6a70`).

## zlib block (directly after the extra header)

Header, 9 x int32: `magic "0000"`, `table_size`, `unk_0c` (128 in every sample, **unknown**), `window` (65536),
`meta1_count`, `chunk_count`, `meta2_count`, `has_tail` (1), `tail_size`. After that come:
`meta1[meta1_count * S]`, `meta2[meta2_count * S]` (16 B each), `chunk_count x (u32 offset, u32 size)`, and, if
`has_tail`, `(u32 offset, u32 size)`. The header and these tables together take exactly `table_size` bytes
(verified).

* `meta1_count + meta2_count == mip count` (verified). Mips `0 .. meta1_count-1` are tiled; the rest are in the tail.
* Both tables are **mip-major, slice-minor**: entry `mip * S + slice`. In `0xad4f6a70`, meta2 entries 0-15 are all
  `(128, 16384)` and entries 16-31 are all `(64, 4096)`.
* **meta1 entry** = `(tiles_x, tiles_y, unk, first_tile)`. `tiles_x/y = ceil(elements / tile shape)`, for example
  BC7 2048: (8,8), (4,4), (2,2), (1,1) at first tiles 0, 64, 80 and 84, giving 85 = chunk_count; BC1 2048: (4,8),
  (2,4), (1,2) at 0, 32 and 40, giving 42. In the arrays it is `(1,1,0,slice)`. `unk` is 0 everywhere (**unknown**).
* **meta2 entry** = `(row_bytes, size, 0xBAADBAAD, 0xBAADBAAD)`. `size` is the linear byte size of the mip.
  `row_bytes` is one pixel row in bytes (width x bits per pixel / 8). That equals the block-row pitch / 4 for BC: BC7
  128 px gives 128, BC1 256 px gives 128, RGBA32F 1 px gives 16. The tool checks it, but its use by the game is
  unknown. The two `BAADBAAD` words look like unfilled debug padding.
* **Chunk table**: `offset` is an absolute offset in the file. That is verified only for single-texture files,
  where file start and container start are the same, so the base for multi-texture files is unverified. `size`
  counts the 4-byte prefix. At `offset` sits a `u32` deflated size (`size - 4`) followed by a zlib stream (header
  `78 9C`). Every chunk inflates to exactly `window` bytes, so one chunk is one 64 KB tile. Chunks follow each
  other with no gaps from `data_start` (the end of the table) onwards. Vanilla streams are not byte-identical to
  Python zlib at any level (tested 0-9, memLevel 8/9); only trivially compressible chunks match level 6. The
  compressed bytes therefore differ from vanilla, while the inflated bytes are identical.
* **Tail**: `offset` = the end of the last chunk, `size = tail_size`, and the file ends at the end of the tail
  (verified). The tail is **raw (not compressed), linear, mip-major then slice**: every meta2 image back to back,
  with no padding. `tail_size` equals the sum of the meta2 sizes (for example 21840 = 16384+4096+1024+256+64+16).
  The 1x1 float texture has no chunks: meta1_count 0 and the whole image (16 B) is in the tail.

## Tiling (the chunk stream = all inflated chunks concatenated; tile t = bytes t*65536 .. +65536)

A tiled mip occupies tiles `first_tile .. first_tile + tiles_x*tiles_y - 1`, **row-major** (tile index
`first_tile + ty*tiles_x + tx`). Inside a tile the data is **plain linear rows**: `tile_h` rows of
`tile_w * bytes_per_element` (= 1024) bytes. There is no swizzle inside the tile. Tile shape in elements (4x4 blocks
for BC) follows the D3D12 standard 64 KB shape: 64x64 for 16 B elements (BC7/BC5), 128x64 for 8 B (BC1/BC4).
This agrees with the reference `DeswizzleD3D12_64KB_BC` and with the Ronin storage-1 layout. A mip is tiled
exactly when it fills at least one whole tile; in the samples, a mip under 64 KB goes to the tail. Array slices of
the same mip take consecutive tile ranges, each given by its own meta1 entry.

Evidence (project scratch report `verify_report.json`, not shipped):

* Mean |diff| at tile boundaries divided by the same measure elsewhere is at most 1.6 for every tiled mip. Reading
  the same data with tiles in column-major order gives 11.2 / 13.3 (0x8b541440) and 2.7 / 2.1 (0x7f1eb597).
  The low end of the observed range is 0.13; values under 1 come from flat regions at the boundaries.
* Mip n, decoded independently, against mip n-1 downscaled 2x: mean |diff| 0.2-4.3 / 255 across tiled→tiled and
  tiled→tail transitions on every planar sample. The column-major misreading gives 22.5 / 12.6.
* No duplicated halves: mean |left half − right half| is 8.9-39.8 on the planar maps (a duplicated layout gives ~0).
  The 0.0 values occur only on uniform array layers.
* Tail order: for the arrays, a mip-major tail gives mip1-vs-mip0 diff 0-10.9 per layer. Reading it slice-major
  gives 41-167. Layers 1, 5, 7, 9, 13 and 15 of `0xad4f6a70` (and layer 1 of `0x1306ac15`) are single-colour
  placeholders. They are the 161-byte chunks, and their tail mips are uniform too.
* Visual check: texconv PNGs of all mips and layers show a normal map, colour atlases, a shading map and a
  detail-normal array with clean UV islands.

## Writing (what `encode` / `constant` change)

They change only the chunk bytes, the `(offset, size)` of each chunk, the tail entry offset, and the file size
at +8. Everything else is copied from the template: headers, extra header, zlib header (counts and tail_size
too), meta1 and meta2. The new pixel data is written into the template's inflated stream and tail, so tile padding
(none in the samples) would stay vanilla. The DDS must match the format family, width, height, mip count and
layer count exactly. Only single-texture, planar or plane-array, depth-1 files are accepted.
**Not covered by any sample**: cube or volume textures, faces > 1, partial tiles, non-square tiled mips,
uncompressed tiled mips (their shape comes from the D3D12 table), multi-texture files, and in-game loading of the
output.
