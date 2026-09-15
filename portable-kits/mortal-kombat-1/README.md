# Mortal Kombat 1 便携入口

从仓库或独立导出包根目录运行。实现只保留一份，位于 [游戏 scripts](../../games/mortal-kombat-1/scripts/README.md)；导出器会携带整个游戏目录，不需要原作者工作区。

```powershell
python -m pip install -r requirements.txt
python -B portable-kits/common/modkit.py init ../MyMK1Mod --game mortal-kombat-1
python -B games/mortal-kombat-1/scripts/mk1_checks.py --help
python -B games/mortal-kombat-1/scripts/psk_index_plan.py --help
python -B games/mortal-kombat-1/scripts/atlas_quadrants.py --help
python -B -m unittest discover -s games/mortal-kombat-1/scripts -p "test_*.py"
powershell -NoProfile -ExecutionPolicy Bypass -File games/mortal-kombat-1/scripts/test_deploy.ps1
```

先读 [端到端流程](../../games/mortal-kombat-1/PLAYBOOK.md)、[当前证据范围](../../games/mortal-kombat-1/STATUS.md) 和 [工具来源](../../games/mortal-kombat-1/TOOLS.md)。项目初始化仅创建记录框架，详细合同可参考 [MK1模板](../../games/mortal-kombat-1/templates/project.example.json)。

Python 3.10+；图集拼合与其测试使用 Pillow，其余 MK1 Python 工具使用标准库。部署脚本需要 Windows PowerShell，默认只读预检，显式 `-Install` 才安装，游戏运行时拒绝写入。`test_deploy.ps1` 只操作临时合成目录，不触碰游戏。

工具职责与边界：

- `mk1_checks.py`：文件哈希、精确变更白名单、源哈希锁定的render索引退化。
- `psk_index_plan.py`：独立PSK完整索引流匹配，生成计划；不猜LOD或native布局。
- `atlas_quadrants.py`：四页RGBA拼合及矩形清单；不修改模型UV、不Cook。
- `retarget_math.py`、`neck_fit.py`：显式尺度、共同骨盆场、局部头颈算子；不自动选区或绑定。
- `deploy_trio.ps1`：完整三件套哈希预检、备份、部署及失败回滚尝试。

不包含模型、贴图、游戏chunk、密钥、定制UE或第三方二进制。游戏资源由使用者本机合法安装提供；骨架/蓝图/IoStore结构修改仍需目标专属审计，不是通用一键制作器。
