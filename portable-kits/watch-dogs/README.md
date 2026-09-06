# 看门狗便携包

先读 [游戏知识](../../games/watch-dogs/README.md) 和 [ZModeler 操作](../../games/watch-dogs/ZMODELER_OPERATOR_CHECKLIST.md)。以下从交接包根执行：

```powershell
python portable-kits/watch-dogs/scripts/xbt_tool.py inspect ../MyMod/Ref/low.xbt
python portable-kits/watch-dogs/scripts/xbt_tool.py extract ../MyMod/Ref/low.xbt ../MyMod/Work/low.dds
python portable-kits/watch-dogs/scripts/xbt_tool.py inject ../MyMod/Ref/low.xbt ../MyMod/Work/replacement.dds ../MyMod/Work/new.xbt
python portable-kits/watch-dogs/scripts/audit_xbt_templates.py ../MyMod/Ref/textures ../MyMod/Work/xbt-audit
python portable-kits/watch-dogs/scripts/build_xbt_pair.py ../MyMod/Ref/source.png ../MyMod/Ref/low.xbt ../MyMod/Ref/low_high.xbt ../MyMod/Work/pair --texconv $Texconv --expected-texconv-sha256 $TexconvSHA256
```

注入保留 donor header，拒绝 DDS 尺寸/mip/格式不一致及已有输出。`--force` 只用于格式实验。pair builder 限定 XBT 123 + legacy DXT1/DXT5，low 完整 mip/high 单 mip。模板审计搜索同一目录，不递归猜测配对。

Blender 制作派生 FBX 后，在 ZModeler 分别绑定两个 LOD 并建立新 Compound；导出 XBG 后验证 GPU buffer 与新进程回读，再接入 XBT 和 FAT/DAT。专属 XBG 审计器仍需按当前 donor 的实际索引范围编写，不能沿用旧 423 骨与面数。ZModeler/NexusTools 不随包提供。见 [工具来源](../../references/TOOL_SOURCES.md)。
