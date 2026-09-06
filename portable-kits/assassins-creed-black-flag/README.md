# 黑旗记忆重置便携包

先读 [格式研究](../../games/assassins-creed-black-flag/FORMAT_RESEARCH.md) 和 [完整项目历史](../../games/assassins-creed-black-flag/PROJECT_HISTORY.md)。末段是 AY / 1.6.1；用户于 2026-09-06 在知识库整理会话确认最后修复实机无问题，优先于历史 9 月 5 日的 pending。没有新增全动作/地图验收声明。

```powershell
python portable-kits/assassins-creed-black-flag/scripts/extract_forge_v50_bms.py ../MyMod/Ref/patch.forge --output-root ../MyMod/Work/extract-1 --json-output ../MyMod/Work/extract-1.json --markdown-output ../MyMod/Work/extract-1.md
python portable-kits/assassins-creed-black-flag/scripts/rebuild_forge_v50_patch.py --input ../MyMod/Ref/patch.forge --output ../MyMod/Work/identity.forge --report ../MyMod/Work/identity.json --reencode-all
python portable-kits/assassins-creed-black-flag/scripts/rebuild_forge_v50_patch.py --input ../MyMod/Ref/patch.forge --output ../MyMod/Work/replaced.forge --report ../MyMod/Work/replaced.json --replace "0xRESOURCE_ID=../MyMod/Work/replacement.bin"
```

替换 RESOURCE_ID 为提取出的实际 ID。rebuild 保留 TOC、非类型化区块和 resource envelope，支持观察到的连续布局 field-4 LZ4 patch，**不是完整 boot 的通用重建器**。

extract 支持 TOC/default BMS。LZ4 仅依赖 lz4 包；遇到 field 8 才需 --oodle-libs 指向另行获取的 AnvilToolkit 1.3.6 v7/v9 DLL，保持原 SHA 验证。未分发 DLL，便携测试未执行 Oodle 分支。

完整历史包含 Mesh 格式、MeshBone/CRC、winding、atlas、材质探针和最终口腔 ownership。新角色的 Mesh writer 要按当前合同适配。历史直接写 boot 的候选安装器不作为通用部署器；角色显示开关从 outfit 实例属性定位，不能清空 NPC 共用表。
