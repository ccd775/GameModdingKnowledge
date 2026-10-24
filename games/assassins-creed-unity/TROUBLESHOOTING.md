# 排障手册

除标注外均为本项目实测（Steam build 21970519）。

## 1. 安装与加载

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| Karin 的网格和贴图对，但亚诺的整套装备（兜帽盖脸、外套、腰带、裤子、靴子）和牙齿还在 | 只改了 `CN_P_Arno` 里的表；同样的表还嵌在 `DataAI_UIDataRoot` 和旧时代服装文件里 | `scan_objs.py` 找全副本，每一份都改（[技术合同](TECHNICAL_CONTRACTS.md) §3） |
| 游戏在 Logo 处闪退（`ACU.exe+0x95240`） | 附加骨架和原版规则不符。v3 同时有三处：`ChildBoneCount` 写成了直接子骨数、键沿用了别的骨架、BallJoint 指向了 `LiteRagdoll`；三处一起改后解决，单独哪一处致命没有分开测 | 按 [物理](PHYSICS.md) §2 的三条核对，和原版骨架逐项比 |
| `install` 报 `no payload for these copies` | 某个 ID 的某份副本既没有通用 payload、也没有这个 forge 的专用版本、也不在 `skip.tsv` 里 | 补 forge 专用版本，或者那份确实不用改时写进 `skip.tsv` |
| `install` 报 `these forges differ from the vanilla game the payload was built for` | 游戏版本不同，或者 forge 已被别的 mod 改过 | Steam「验证游戏文件完整性」恢复原版；版本不同时要用这个版本重建 |
| `install` 报 `forge variants that match no index row` | payload 里有某 forge 的专用版本，但那个 forge 里没有这个 ID | 版本或索引不对：重建索引和副本清单 |
| `already installed; uninstall first` | 状态文件存在 | 先 `uninstall`；换版本前总是先卸载 |
| 游戏更新或校验文件后 mod 失效 / 异常 | 更新替换了 forge，状态文件里的旧行不再对应 | **不要卸载**：删 `<游戏目录>\.karin_acu_state.json`，Steam 校验文件，重新安装 |
| `close the game first` | `ACU.exe` 还在运行 | 退出游戏 |
| 安装器找不到游戏 | 不在 Steam 库里，或注册表 / `libraryfolders.vdf` 读不到 | `--game "<含 ACU.exe 的目录>"` 或设 `ACU_GAME_DIR` |
| 康纳的旧时代服装没有物理 | 康纳的附加骨架表里没有可占用的布料单元格 | 已知限制（[物理](PHYSICS.md) §1） |

## 2. 物理

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 双马尾、尾巴直垂，裙片压进大腿 / 臀部 | BallJoint 没有弹簧，锥中心在静止姿势上时重力把链拉到锥边（v4） | 锥中心逆着下垂方向偏一个锥角（`rest_offsets`，[物理](PHYSICS.md) §4） |
| 保住了形状但几乎不动、太硬 | 锥角太小（v5 的 3–5°） | 有了重力补偿后再放大锥角、降低摩擦（v6） |
| 跑动时大腿穿出裙子 | 没有碰撞（v5），或胶囊太小 / 太短（v6 每腿一个、半径 = 裸皮） | 每条大腿两个胶囊，比皮肤粗约 3 cm，覆盖到髋关节（v7，[物理](PHYSICS.md) §6） |
| 不确定碰撞有没有生效 | — | 诊断构建：胶囊半径 ×2（`--capsule-scale 2`），站着时裙子应明显撑开 |
| 手上丝带的偏移是几千度 | 分叉根的子骨不在局部 X 方向上，最小二乘退化 | `rest_offsets` 对 `tl[0] < 0.7` 不偏 |
| 侧发往脸上摆 | 侧发本来朝里挂，「向外」对它就是朝脸 | 锥角保持小（5°） |

## 3. 工具链

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 构建很慢（一个数据文件 30 s 以上） | 中间产物写在同步盘里，或每条 harness 命令单独起进程 | `ACU_SCRATCH` 放本地目录；用 `batch` |
| 构建停在 `vanilla XML does not recompile byte-identical` | 这份副本的 XML 往返不精确（工具版本或对象类型变了） | 不要跳过：先查是哪个字段，确认往返精确后再改 |
| `tables … not found in the XML export` | 副本清单里的表在这份数据文件的导出里找不到 | 重建副本清单；检查 `export-xml-dir` 是否导出了 BuildTable |
| harness 说找不到文件 | 不带斜杠的参数按 harness 所在目录解析 | 写成 `./文件` 或绝对路径 |
| 读贴图时卡住 | 读顶层 mip 时等 GUI 文件对话框 | 结束进程；只用内联 mip 的贴图做模板 |
| `import-glb`：骨数 > 255 | v2 顶点格式没有宽索引 | 导出时裁骨，减少 KP 骨 |
| 比较两次构建的 `.data`，每个都不同 | 容器每次打包字节都不同 | 解包后比内部对象（[技术合同](TECHNICAL_CONTRACTS.md) §2） |
| Blender 输出跑到 C 盘根 | 相对路径按 Blender 的当前目录解析 | 参数全写绝对路径 |
| 改 `ACU.ini` 后换行变了 | Git Bash 的 `sed` 去掉了 CRLF | 用 Python 按字节改，先备份 |
| 本机测试卡在 Ubisoft Connect 登录框 | Steam 版经 Ubisoft Connect 启动 | 请用户自己登录；agent 不代填凭据 |
