# 公共运行层

从交接包根运行，项目输出与知识库分开。`modkit.py` 使用标准库，不部署或启动游戏。

```powershell
python -B portable-kits/common/modkit.py init ../MyMod --game watch-dogs
python -B portable-kits/common/modkit.py inventory ../MyMod/Ref --output ../MyMod/Work/input-files.json
python -B portable-kits/common/modkit.py verify ../MyMod/Ref --manifest ../MyMod/Work/input-files.json
python -B portable-kits/common/modkit.py doctor ../MyMod/project.json
python -B portable-kits/common/modkit.py checkpoint ../MyMod source-1 --status research --note "已审计源，下一步提取目标骨架" --report Work/input-files.json
python -B portable-kits/common/modkit.py inventory ../MyMod/Output/stage --output ../MyMod/Work/stage-files.json
python -B portable-kits/common/modkit.py package ../MyMod/Output/stage --manifest ../MyMod/Work/stage-files.json --output ../MyMod/Output/candidate-1.zip
```

`init` 只接受新目录；`verify` 比较完整集合、大小与 SHA-256，新增文件也失败。manifest 写在输入树之外。`checkpoint` 追加命名记录，不根据状态文字伪造验收。`package` 精确装包，固定时间戳和顺序并逐成员回读，不能代替游戏资源编译器。

在 project.json 的 tools 中写目标机器配置：
```json
{"blender": {"path": "tools/blender/blender.exe", "sha256": "填写实测64位SHA256"}}
```
`doctor` 检查路径和哈希，不执行外部工具，也不推断格式兼容。

## Blender 源审计

`scripts/audit_blend_source.py` 来自 L4D2 项目，读取 mesh、armature、材质、UV、shape keys、权重和纹理信息，不修改或保存源文件。先加载源文件，再执行脚本：

```powershell
& $Blender --factory-startup --background --disable-autoexec --python-exit-code 1 ../MyMod/Ref/source.blend --python portable-kits/common/scripts/audit_blend_source.py -- --output ../MyMod/Work/reports/source.json
```
