# 验证与发布

## 1. 离线闸门

- 每份含目标表的原版副本重新编译逐字节相同（全部通过，否则构建停下）。
- 附加骨架和原版逐项对照：深度优先、`Index` = 位置、`ChildBoneCount` = 后代数、自己的骨架键、`LiteRagdoll` / `OrientationBone` 留空、`MirroringTag` /
  `EnablePoseDrivenWrinkles` 写上（[物理](PHYSICS.md) §2）。
- 网格 ≤ 255 骨（175）；新对象 ID 高于原版最大 ID。
- 往返：安装 → 状态 → 卸载，forge 回到原长、索引行回到原值。

## 2. 实机闸门

| 日期 | 构建 | 观察 | 证据级 |
| --- | --- | --- | --- |
| 2026-10-26 | stage 1 | 进入游戏，标题画面 Karin 完整（头发、脸、服装、贴图），没有原版装备 | `runtime-load-pass`（agent 截图） |
| 2026-10-26 | stage 2 | 过 Logo（附加骨架规则成立），标题画面 Karin 完整，视线 / 眼睑随待机动画变化 | `runtime-load-pass`（agent 截图） |
| 2026-10-26 | stage 2 | 读入一个 100 % 进度的存档：伦敦码头上伊薇和雅各布都是 Karin，冲刺时双马尾 / 尾巴摆动，攀爬姿势正常，菜单切换雅各布 | `runtime-load-pass`（agent 截图） |
| 2026-10-27 | stage 2 | 用户：「两个角色都被正确替换了，有物理有表情」；耳朵 / 双马尾太硬 | 替换、物理、表情 `runtime-confirmed`；手感 `runtime-rejected` |
| 2026-10-27 | v2 | agent：冲刺 + 转身 + 急停，双马尾软弧摆动并回位 | `runtime-load-pass`（被 v3 取代） |
| 2026-10-30 | v2 | 用户截图：耳朵朝右歪、双马尾持续抖、膝盖穿袜、裙褶污渍 | `runtime-rejected` |
| 2026-10-30 | v3 | 用户：耳朵好，双马尾整根甩起，裙褶污渍减轻 | 双马尾 `runtime-rejected` |
| 2026-10-30 | v4 | 用户：双马尾又快速抖 | `runtime-rejected` |
| 2026-10-30 | v5 | 用户：「看起来可以」 | `runtime-confirmed` |

全部在构建机那一份副本上。

## 3. 可重新部署的包

`make_release.py <zip> s2=<payload> --python <python-x.y.z-embed-amd64.zip>`：

| 文件 | 内容 |
| --- | --- |
| `payload_<标签>.tar.xz` | solid xz（同一数据文件的各 forge 版本相邻排列，互相压缩；约 870 MB → 125 MB）+ `payload/vanilla.tsv` |
| `install_<标签>.cmd`、`uninstall.cmd`、`status.cmd` | 纯 ASCII 批处理：切到包目录，没有 `python\python.exe` 时提示先解压整个包，再跑 `python\python.exe -I -B acs_install.py …`，最后 `pause` |
| `python\` | python.org 的 Windows 嵌入式 Python（项目 3.14.10，带 vcruntime 和 `_lzma`）；`-I` 隔离模式，不读 PYTHON* 变量和用户 site |
| `acs_install.py`、`README.txt` | 安装器；中文说明（解压、自动找游戏、管理员权限、不锁版本、装了新 DLC 后重装） |

- **不用 PowerShell**（2026-10-30 用户：有的用户电脑不放行 PS 脚本）：`.cmd` 只调嵌入式 Python，安装器只用标准库和 `tasklist`。
- **不锁版本**（2026-10-30 用户：手上没有 Steam / Ubisoft 版可测）：旧做法核对每个要动的 forge 和制作时的原版大小一致，别的版本、少装 DLC、装了别的 mod 都会整个拒装。
  现在 `vanilla.tsv` 记下每份被替换副本（290 个变体 + 28 个 skip 行）在构建机原版里的大小 + SHA-1（装着 mod 时经状态文件读原位置；318 条和构建缓存的哈希全部一致），
  安装器按 ID + 内容匹配（[技术合同](TECHNICAL_CONTRACTS.md) §8）。
- 测试：
  - 合成 forge：总大小不同、缺 `dlc_20`、一份被改过、已知内容出现在新 forge 里、未知内容、没有 `vanilla.tsv` 的旧 payload、全不匹配、forge 版本不对；每次卸载后逐字节还原。
  - 真实游戏：包解压到带空格和中文的路径、PATH 只留 System32，跑 状态 → 卸载 → 安装 → 状态：290 / 290 份与制作源相同，forge 大小与之前一致。
  - 真实游戏上假装没有任何 `dlc_*` 文件夹做只规划不写入的安装：替换 7 个本体 forge 里的 118 份，跳过 172 份 DLC 副本（旧安装器会拒装）。
  - 写保护的 forge：给出「以管理员身份运行」的提示，什么都不改。
- 已知风险：真实的 Steam / Ubisoft Connect / Epic 副本没测；内容不同的副本会被整份换成构建机的版本，若那个版本差别大可能出问题（安装日志会列出是哪几份）。
  装 mod 之后再装的 DLC 不会被替换，需要先卸载再安装。

## 4. 未测场景

- Steam / Ubisoft Connect / Epic 的副本；其他游戏版本。
- 过场（预渲染视频，不会显示 Karin）；开膛手杰克 DLC 的老年雅各布 / 伊薇（未处理）。
- 对话口型、眨眼幅度的单独评价；骑马、驾车、绳索发射器、战斗大动作中的物理。
- 莉迪亚·弗莱在一战记忆里的实机外观。
