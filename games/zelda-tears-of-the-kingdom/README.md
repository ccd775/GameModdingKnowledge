# 塞尔达传说：王国之泪（The Legend of Zelda: Tears of the Kingdom）

## 范围

这里整理《王国之泪》1.2.0（title `0100F2C0115B6000`，yuzu 系模拟器）一次角色替换的可复用合同。替换对象是 Link 的防具套装 **Armor_1061**（火焰头饰 / 火焰服 / 火焰裤子，1062–1064 升级档共用同一模型），来自 2026-11-02 → 11-03 的一个交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin_Original v1–v7c | 从 FBX 构建的头、上衣、下装三个模型：<br>- 按段重定向到 Link 的 T 姿势骨架；<br>- 借用套装 Havok cloth 驱动的骨骼做物理（双马尾、24 根裙骨、兽尾、面颊发、刘海、狐耳）；<br>- 嘴型拟合到 Link 的面部骨骼；<br>- 带符号、可大于 1 的浮点蒙皮权重做眨眼；<br>- 合并的 RESTBL、背包图标；<br>- 可再部署的安装包和存档工具 | `runtime-confirmed`（用户本机实机）：<br>- 贴图修复（v2）、裙摆（v3）；<br>- 眨眼（v5，「眼睛会眨眼了」）；<br>- 狐耳不再被拉长（v6b）；<br>- v6d 后用户说「可以了」。<br><br>`offline-accepted`：<br>- 头身比例、脖子、肩膀、腿（v7–v7c）；<br>- 安装包。 |

**快照范围**
- 只对游戏 1.2.0（RESTBL `Product.120`）和 yuzu EA 4176 有效。
- **`build-sensitive`**：文件名、骨骼名、哈希、存档偏移。
- **`case-derived`**：比例 1.38 / 1.40、权重增益、渐入高度。
- 实机证据都来自用户本机：游戏由用户启动和游玩，agent 只在模拟器关闭时安装文件。

**本作的主要贡献**
- **不改 Havok cloth，也能有物理**：把 Karin 的可动部件蒙皮到原套装中由布料驱动的骨骼上。
  - 先用 PhysicsTool.Core 读出每根布料骨骼由哪个粒子三角形驱动，固定粒子的数量和排布决定它是铰链还是万向节。
  - 再按部件挑骨骼。直立的狐耳用负权重。
  - 记录了负权重线性蒙皮的拉伸公式，以及哪些骨骼一定会把耳朵拉长（[物理](PHYSICS.md)）。
- **浮点 / 负蒙皮权重在实机生效**：原版权重是 `8_8_8_8_UNorm`，脸部网格改成 `Format_32_32_32_32_Single` 后，用户实机确认眨眼生效。
  - 本库仁王3（`games/nioh-3/FACE.md`）用过同样的「权重 > 1 / < 0、Head 吃剩余」方案。
  - TotkMdl 绕过了 Switch Toolbox 把权重按 8 位截断的问题（[面部](FACE.md)）。
- **染色动画按材质名换贴图**：套装的染色动画绑定材质名，会把 Karin 的身体换成别的贴图。给材质改名就能避开（[技术合同](TECHNICAL_CONTRACTS.md) §3）。
- **骨架比例的硬限制**：Link 的手臂关节固定在 ±18.3 cm，动画绕它转。肩宽只能靠压扁肩头、把方肩改溜肩来缓解（[重定向与比例](RETARGET_AND_PROPORTIONS.md)）。
- **存档里发装备**：按 progress.sav 的哈希表找到防具包数组，只写空格子，并置「已获得」标记（[存档与发行](SAVE_AND_RELEASE.md)）。

与其它目录的关系：
- 本作没有引擎编辑器可用。网格写入靠 Switch Toolbox 的 BFRES 代码，由 TotkMdl 无界面驱动。
- 物理不新建，只借用游戏已有的布料骨骼。
- 面部同仁王3一样，用骨骼权重近似形态键。

## 核心方法

1. 用 NxExtract（LibHac）从基础版 XCI 和 1.2.0 更新 NCA 解出需要的原版文件：模型、pack、贴图、RESTBL、动画、图标。
2. 用 TotkMdl `info` / `export` 读骨架、平滑矩阵表、形状和材质，用 `bphcl_probe` 读布料驱动关系，再定映射方案。
3. 改动按类别分版本，一版只让一类改动进实机反馈：几何、材质、物理增益、面部、比例。用户实机看到的问题先离线复现，用 `pose_test` / `swing_test` / `face_preview` 加 Blender 预览。
4. 打包时 RESTBL 合并原版、其他启用的 mod 和本 mod 的条目，文件夹名用 `00_` 开头抢先生效。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。实机证据来自用户的口头反馈和截图。未测场景见 [案例](cases/KARIN_ORIGINAL.md) 的「未测」一节。

## 阅读入口

| 文档 | 内容 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | 接手前的检查和硬性规矩 |
| [技术合同](TECHNICAL_CONTRACTS.md) | LayeredFS 与 RESTBL、`.bfres.mc` 与 mesh codec、TexToGo、pack、图标、动画、romfs 解包 |
| [构建流水线](BUILD_PIPELINE.md) | 从 FBX 到 mod 文件夹的每一步、输入输出、离线门槛 |
| [重定向与比例](RETARGET_AND_PROPORTIONS.md) | 按段相似变换、头部缩放与下沉、肩部压扁、腿部加粗、裙摆权重 |
| [物理](PHYSICS.md) | 借用布料骨骼：cloth 清单、三角形类型、负权重拉伸、被否决的方案 |
| [面部](FACE.md) | 面部动画读取、嘴型 NNLS 拟合、带符号权重的眨眼、浮点权重格式 |
| [存档与发行](SAVE_AND_RELEASE.md) | 安装包、安装器、progress.sav 结构、存档工具 |
| [排障](TROUBLESHOOTING.md) | 症状 → 原因 → 处理 |
| [案例：Karin_Original](cases/KARIN_ORIGINAL.md) | v1–v7c 的时间线、用户反馈和未测项 |
| [便携工具](../../portable-kits/zelda-tears-of-the-kingdom/README.md) | 脚本、C# 工具、安装脚本的用法 |
