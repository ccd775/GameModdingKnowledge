# L4D2 便携包

读 [端到端制作](../../games/left-4-dead-2/10-end-to-end-sop.md) 和 [项目脚本职责](../../games/left-4-dead-2/12-automation-script-catalog.md)。下面四个脚本已实际附带，其余角色脚本按新模型实现。

```powershell
python portable-kits/left-4-dead-2/scripts/extract_vpk_entries.py --vpk-exe $VpkExe --dir-vpk ../MyMod/Ref/pak01_dir.vpk --output ../MyMod/Work/native --entry models/survivors/survivor_teenangst.mdl --report ../MyMod/Work/extract.json
python portable-kits/left-4-dead-2/scripts/rescale_vta.py --input ../MyMod/Work/source.vta --reference-smd ../MyMod/Work/scaled.smd --output ../MyMod/Work/scaled.vta --input-units-per-meter 1 --output-units-per-meter 39.37007874 --expected-nodes 1 --expected-frames 2 --report ../MyMod/Work/vta.json
python portable-kits/left-4-dead-2/scripts/run_studiomdl.py --studiomdl $StudioMDL --game ../MyMod/Work/compile_sandbox --qc ../MyMod/Work/model.qc --log ../MyMod/Work/compile.log --report ../MyMod/Work/compile.json
python portable-kits/left-4-dead-2/scripts/validate_vpk_tree.py --vpk-exe $VpkExe --vpk ../MyMod/Output/addon.vpk --loose ../MyMod/Output/stage --report ../MyMod/Work/vpk.json
```

VTA 的单位/骨数/帧数取自输入，1/2 是合成示例；工具只缩放 position、保留 normals，检查 frame-0 bounds 与 scaled SMD 一致。VPK 提取支持无 preload 的分卷/embedded；包回读限定无 preload 的单体 VPK。

StudioMDL 记录器要求新日志和新模型输出，只证明编译 exit/伴随文件存在，不替代二进制深审计。隔离 sandbox/gameinfo.txt 需挂载游戏编译依赖，world/light/arms 分别有 QC。用 Valve vpk 装包后执行 payload 检查。不会自动安装或操作 HLMV/游戏。[工具来源](../../references/TOOL_SOURCES.md)。
