# 验证与发布

## 1. 离线闸门

每个构建都要过：

- `n3_validate_g1m.py <built> <template> --layout-changed --physics`：PASS。它用 `g1m_tool.py` 独立读回，不经过写入代码。
- 块差异：和上一个构建比，只有预期的块变了（例：build23 → build24 只有 LLOC、FM1G +96 / +100、ONUN 里两个裙摆条目的碰撞组号）。用 `checks/diff24.py` 或同类脚本。
- 绑定姿势漂移 < 1e-4 cm（`checks/swing.py`）。漂移大说明调色板、逆绑定或权重量化错了。
- 每条链单独绕根部转动时只有它自己的顶点在动（`checks/swing.py`）。
- 三角形总数与预期一致（build22 起丢掉源空间面积为 0 的三角形：46006 → 41272，build23 41298）。
- 每材质计数 = 实际子网格数 / 顶点缓冲数；注册表的 type-4 条目数 = ONUN 里的条目数，顺序一致。
- 贴图：`n3_g1t.py` 解码后与 DDS 逐张一致；新尺寸的贴图过 `n3_g1t_resize.py` 自己的读回比较。
- 共用审计：`ktdata.py usage` 确认被改的贴图没有别的模型在画；被共用的只改槽，不改内容。
- 表情：`checks/facecheck.py` 按姿势渲染；`checks/blinkgap.py` 看满眨眼时眼睑沿目标走到多少、缝多大、左右是否对称。

## 2. 实机闸门

1. 游戏关闭，`n3inject.py install` 后 `verify` 全部一致（本案例 33/33）。
2. 主菜单：角色完整，静止脸正常。**这一步不能判断物理。**
3. 读档进关卡：两种流派（装备界面按 6 切换）都看正面、背面；静止时耳朵、裙摆有没有下垂；跑动、急停后回摆；大动作（前倾下劈）下裙摆和臀部 / 大腿的穿插。
4. 表情：待机眨眼；按喊声键看张嘴（关卡里的表情没有专门测过）。
5. 用户实际玩过、给了反馈才算 `runtime-confirmed`；agent 截图只算 `runtime-load-pass`。
6. 收尾：关游戏，关掉自己打开的窗口，删远端截图和临时文件。

测试机操作要点：每个桌面动作先把游戏窗口切到前台。测试存档的系统设置下，主菜单和对话框要用鼠标按住点击；载入提示页按 E；菜单 Esc 打开、E 确认、Q 返回。

## 3. 发行包

```text
Karin_Nioh3/
  README.md
  install.cmd / verify.cmd / uninstall.cmd   → python karin_install.py <命令> "<游戏目录>"
  karin_install.py
  tools/ktdata.py, g1m_tool.py, n3inject.py
  files/            20 个自制文件：两件上衣、两个物理注册表、两个每材质计数、5 张贴图、9 张贴图表
  collapse.txt      13 个要隐藏的原版模型
  vanilla.json      33 个被替换资源的 v2.0.0.2 原版 sha256
  package.json      装入内容的 sha256
```

- 安装：
  1. 核对游戏没在运行。
  2. 33 个被替换的原版资源逐个和 `vanilla.json` 对 sha256，版本不符就拒绝。原版从 `root.rdb.original` / `root.rdx.original` 读，第一次运行时会先建这两个备份；除此之外什么都不写。
  3. `files/` 复制进 `staging/`；`collapse.txt` 里的 13 个模型从玩家自己的游戏数据提取并塌缩（`g1m_tool.py hide --all`），也放进 `staging/`。所以包里不带原版资源的副本。
  4. `staging/` 逐个和 `package.json` 对 sha256，再 `n3inject.py install`，删除 `staging/`。成功时输出 `records changed: 33 (unexpected: 0)` 和 `install OK`。
- 卸载：备份放回，删除新容器。校验：通过资源表解出每个覆盖，与 `package.json` 比较。
- 便携包里的 `karin_install.py` 就是这个安装器；`.cmd` 只是转调它，本库不收 `.cmd`。
- 测试机实测：从包安装 → verify 33/33 → 卸载（`root.rdb` 与备份相同、容器已删）→ 重装 → verify 33/33。在测试机上从包装出的结果与构建目录逐字节相同。
- README 要写清楚：适配的游戏版本、Python 3.8+（只用标准库）、必须穿哪两件上衣、隐藏了哪些模型（穿别的装备会叠在 Karin 身上，换上衣会看到不完整的角色）、
  已知风险、和其它改 `root.rdb` 的 mod 冲突、游戏更新后怎么办、源模型的版权和使用条款。

## 4. 证据分层与未测场景

| 项 | 证据 |
| --- | --- |
| 忍者模型与材质 | `runtime-confirmed`（build7） |
| 武士流派 | `runtime-load-pass`（build8，agent 实机）；之后用户测物理时两种流派都看过 |
| 表情（眨眼、眉、张嘴） | `runtime-confirmed`（build10） |
| 物理（耳朵、马尾、裙子、尾巴） | `runtime-confirmed`（build21） |
| 袜子里的皮肤 | `runtime-confirmed`（build23） |
| 裙摆臀部碰撞 | `offline-accepted`（build24，已装，待用户） |
| 可再部署包 | 测试机安装 / 校验 / 卸载 / 重装通过；build23 包用户实机 |

未测：过场动画、死亡、隐藏头盔 / 下身的选项、NPC 是否用到被隐藏的模型、穿兄弟模型的 NPC 是否被套上 Karin 的贴图、
忍者上衣的其它染色、和 `0x5c3826bd` 共用计数资源的上衣 `0x1af713a6`、其它游戏版本。
