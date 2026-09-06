# 杀手 WOA 便携包

先读 [工具链](../../games/hitman-world-of-assassination/TOOLCHAIN.md) 和 [项目历史](../../games/hitman-world-of-assassination/PROJECT_HISTORY.md) 后段的固定流程。历史早期 S3 男性骨架计划被后来的 235-joint 女性 carrier 取代。

```powershell
python portable-kits/hitman-world-of-assassination/scripts/validate_prim_glb.py ../MyMod/Work/0000000000000001.PRIM.glb --carrier ../MyMod/Ref/carrier.glb --joint-policy exact --json-out ../MyMod/Work/prim-check.json
python portable-kits/hitman-world-of-assassination/scripts/compare_prim_roundtrip.py ../MyMod/Work/source.glb ../MyMod/Work/reexported.glb --json-out ../MyMod/Work/roundtrip.json
python portable-kits/hitman-world-of-assassination/scripts/rebuild_text_resources.py --config ../MyMod/texture-config.json --atlas-dir ../MyMod/Work/atlas --carrier-text-dir ../MyMod/Ref/textures --build-dir ../MyMod/Work/text-build-1 --rpkg-cli $RpkgCLI
```

GLB 校验针对 RPKG 2.34，包括 16HEX.PRIM.glb、sibling metas、accessor、skin 和 carrier；`--skip-meta` 仅诊断使用。roundtrip 比较位置、法线、UV、权重、颜色和命名关节，不证明实体/碰撞依赖。

TEXT builder **限定六槽 carrier**：slots 为 0..5，包含 carrier_mati_hash、carrier_material_id、carrier_dependency_index、texture_hashes 中的 normal/specular/diffuse，以及顶层 atlas_size。MATI/TEXT 的命名模式必须通过脚本内 carrier 校验。示例见 [配置](texture-config.example.json)，ID 均为合成值。输入需要 RPKG 导出的 TGA 及 metas。

RPKG 重建后重新导出比较；SMF 的 content/chunk0 承载当前 QuickEntity TEMP/TBLU 补丁。骨架映射、实体迁移和安装仍由项目脚本/SMF 完成。工具获取见 [来源](../../references/TOOL_SOURCES.md)。
