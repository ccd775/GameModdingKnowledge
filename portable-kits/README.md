# Modding 便携工具包

无需注册 Skill。把整个仓库或导出的单游戏目录交给 agent，先读对应 README，按当前问题选择工具；构建、排障、暂停和复测可以反复进行。

| 游戏 | 实际附带脚本 | 命令与边界 |
| --- | --- | --- |
| MK1 | 图集拼合、hash/差异检查、PSK索引计划、比例/骨盆/颈部算子、三件套预检部署 | [使用](mortal-kombat-1/README.md) |
| 杀手 WOA | PRIM/GLB 校验、roundtrip 比较、六槽 TEXT/TEXD 重建 | [使用](hitman-world-of-assassination/README.md) |
| 看门狗 | XBT/DDS 提取、注入、配对审计、PNG 转 XBT pair | [使用](watch-dogs/README.md) |
| 黑旗记忆重置 | Forge v50 BMS 提取、LZ4 重建、显式资源替换 | [使用](assassins-creed-black-flag/README.md) |
| RE4R | KPKA v4 路径哈希、目录和 payload 提取 | [使用](resident-evil-4-remake/README.md) |
| L4D2 | VPK 提取/回读、VTA 缩放、StudioMDL 运行记录 | [使用](left-4-dead-2/README.md) |
| HD2 | 三件套解析、LUT 行折叠/注入、SDK UV 复制 | [使用](helldivers-2/README.md) |

[公共层](common/README.md) 提供项目初始化、哈希锁、断点、工具预检、确定性 ZIP 和 Blender 审计。

Python 3.10+；大多数脚本只用标准库，Forge 需 lz4，文档检查和导出需 markdown-it-py。Windows 编译器在 Windows 中执行，Blender 审计在 Blender 内执行。仓库根命令：

```powershell
python -m pip install -r requirements.txt
python -B portable-kits/common/modkit.py init ../MyMod --game left-4-dead-2
python -B tests/test_portable_tools.py
python -B tools/check_repository.py
python -B tools/export_kit.py --game left-4-dead-2 --output ../L4D2-Portable
```

导出器带上该游戏文档、实际脚本、公共层和依赖说明，无需父仓库。不会带入私人模型或第三方二进制。

工具补齐格式步骤，不自动决定新角色的骨架、目标资源和外观。迁移来源见 [PROVENANCE.json](PROVENANCE.json)，实测边界见 [VALIDATION.md](VALIDATION.md)。
