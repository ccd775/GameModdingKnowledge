# HD2 便携包

先读 [快速开始](../../games/helldivers-2/QUICKSTART.md) 和 [资源合同](../../games/helldivers-2/02_HD2_Resource_Contracts.md)。本包有五个实际脚本，其中 stingray_archive.py 是共享库。

```powershell
python portable-kits/helldivers-2/scripts/inspect_patch.py ../MyMod/Ref/example.patch_0 --report ../MyMod/Work/inventory.json --extract-non-streaming-textures ../MyMod/Work/textures
python portable-kits/helldivers-2/scripts/collapse_lut_rows.py --source-dds ../MyMod/Work/native-lut.dds --source-row 3 --output-dds ../MyMod/Work/collapsed.dds --report ../MyMod/Work/lut.json --selection-reason "目标 Piece 行审计"
python portable-kits/helldivers-2/scripts/inject_runtime_lut.py --source-patch ../MyMod/Ref/example.patch_0 --mapping ../MyMod/Work/lut-map.json --output-patch ../MyMod/Work/candidate.patch_0 --dry-run
python portable-kits/helldivers-2/scripts/copy_unit_uv_channels.py --help
```

inspect 要求三件齐全，检查 TOC、类型组、索引、资源键和范围，限定观察到的 AQ 连续布局。可提取非流式 DX10 TextureMap DDS。

collapse 限定 23x8/5 mip/DXGI 10/2076 字节 LUT，保持 header 并逐 mip 选行。行 3 只是示例，新格式需重新审计。

注入 mapping 包含 schema=hd2-runtime-material-lut-map-v1、armor_kit、armor_set_snapshot_sha256、expected_source_hashes、targets；每个 target 提供 native/source DDS、ID 和 ownership 证据。字段与验证见脚本 validate_mapping_identity / validate_source_hashes / main。先 dry-run 再写新三件套。

UV 复制要求 --sdk-dir、输入三件 SHA、material-id 和 source/target UV。复制 UV0 到 UV1/2 只有在 shader 语义匹配时才合理，不能自动修所有 splat。便携测试涵盖纯 Python 归档/LUT，未执行 SDK Unit 编译或游戏任务。[工具来源](../../references/TOOL_SOURCES.md)。
