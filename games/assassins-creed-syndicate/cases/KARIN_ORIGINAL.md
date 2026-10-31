# 案例：Karin_Original → 雅各布 + 伊薇（2026-10-26 至 2026-10-30）

用户要求：两位主角整体替换成 Karin_Original，之后加物理与表情；可以在构建机本机实机测试（测完关游戏、恢复设置）。v3 起用户在同一台机器上自己试玩并反馈。

| 项 | 值 |
| --- | --- |
| 游戏 | PC，`ACS.exe` 链接时间 2016-08-16，forge v27，非商店版副本 |
| 源模型 | Karin_Original 的 Unity FBX（与大革命同一个文件） |
| 交付 | `Karin_ACS_<日期>_s2.zip`（v5，含嵌入式 Python，约 138 MB） |

## 1. 工具链

从大革命项目分出：`acs_forge.py` / `acs_install.py` / `bt_tool.py` / `acs_phys_skel.py` / Blender 脚本是大革命副本的小改，AcuHarness 原样复用；
新写 `glb_names.py`（CRC32 骨名）、`make_meshes.py`（两兄妹一键构建）、两兄妹版 `build_mod.py`。

## 2. 版本轨迹

| 版本 | 改动 | 结果 |
| --- | --- | --- |
| stage 1 | 模型 + 材质：表去掉可视列、头部 LOD 换成 Karin、武器模板材质；318 份副本 | agent 截图：标题画面 Karin 完整 |
| stage 2 | 35 个链根、`Karin_Phys_<twin>`（121 骨、55 BallJoint、裙片碰撞）挂在头部表第 14 列；表情 | agent：过 Logo、伦敦码头实机；用户：「两个角色都被正确替换了，有物理有表情」，耳朵 / 双马尾太硬 |
| v2 | 耳朵、双马尾改 `LocalOwnGravity`（当回弹用） | agent 实机软弧回位；用户：耳朵朝右歪、双马尾持续抖，另报膝盖穿袜、裙褶污渍 |
| v3 | 回到 GlobalGravity rest-on-edge 并放软；耳朵 `upright`；膝盖隐藏带；裙片切法线 | 用户：耳朵好，双马尾整根甩起，污渍减轻 |
| v4 | 双马尾五节都模拟、逐节分级 | 用户：又快速抖 |
| v5 | 双马尾回到 0 / 2 / 4 节并保留分级；耳朵 9°、更软 | 用户：「看起来可以」 |
| 发行 | 自带嵌入式 Python、ASCII `.cmd`；自动找 Steam / Ubisoft Connect / Epic；按内容比对、不锁版本 | 构建机上往返测试通过；其他商店版未测 |

## 3. 关键判断

- 同一个参考（原版饰物用 `LocalOwnGravity`）推出的「骨自己的坐标系」在实机被两只耳朵同向歪斜证伪；之后只用在本作实机稳定过的 GlobalGravity 模型。
- 双马尾的抖动先被归到 `LocalOwnGravity`，v4 证明真正的变量是「相邻链节都模拟」：同一个模型下，五节抖、隔节不抖。
- 用户截图里的四个问题（耳朵、双马尾、膝盖、裙褶）分属物理、源模型形态键、源模型法线三类，各自独立修，v3 一轮同时进实机，因为互不影响。
- 裙褶修后剩下的痕迹用 Cycles 渲染绑定姿势核对：源法线和切开后的法线都干净，判断为运行时光照或蒙皮，没有继续改法线。

## 4. 发行

- 用户要求：用户电脑不需要装 Python，不用 PowerShell；能自动识别 Steam / Ubisoft Connect 版；不依赖具体游戏版本（手上没有其他商店版可测）。
- 结果见 [验证与发布](../VALIDATION_AND_RELEASE.md) §3。
