# 构建流水线

命令和环境变量见 [便携工具](../../portable-kits/zelda-tears-of-the-kingdom/README.md)。这里说明每一步的输入、输出和离线门槛。

## 1. 工具

| 工具 | 版本 | 用途 |
| --- | --- | --- |
| Switch Toolbox | 2026-10-31 版的 DLL | BFRES 读写，由 TotkMdl（net48，x64，WinForms）无界面驱动。TotkMdl 给加载器一个隐藏的 MDI 窗体，把 `TotkGamePath` 指向 `romfs_st` |
| Blender | 5.0 | FBX 导出、预览渲染。项目里旧的 4.2.23 副本缺 DLL，没用 |
| PhysicsTool | 2.2.0 | 只读 bphcl（探针） |
| LibHac | 0.19.0 | 解 XCI / NCA |
| Python | 3.14 | numpy、scipy、zstandard、Pillow、astc-encoder-py、etcpak、texture2ddecoder |

## 2. 步骤

| 步骤 | 输入 | 输出 | 门槛 |
| --- | --- | --- | --- |
| 原版文件 | 基础版 XCI + 1.2.0 更新 NCA + 密钥 | `romfs/`（模型、pack、ZsDic、RESTBL、Link 皮肤贴图、图标）、`romfs_anim/` | 文件能被 `totkfs` / `mc` / TotkMdl 打开 |
| 基础模型 | `03_kalin` 的三件 1061（Switch Toolbox 另存过的） | `work/build/base_*.json`（`TotkMdl info`） | 骨骼名与原版一致 |
| 源模型 | Karin_Original FBX | `src/karin_dump.npz`（按 (位置, 法线, UV, 物体) 去重的顶点，游戏空间）、`src/karin_shapekeys.npz`（同一索引的形态键位移）、`src/tex/*.png` | 物体和骨骼清单（`inv_karin.py`） |
| 面部骨架 | `Player_Animation.Skeleton.bfres.mc` | `work/anim_skel.json` | — |
| 构建 | 以上全部 | `work/build/out/*.bfres.mc`、`edit_*.json`、`report.json`、`karin_bones_game.json`、`face_fit.npz`、`blink_fit.npz` | TotkMdl 重新读回成功；report 里的眨眼闭合和其他姿势偏差 |
| 贴图 | `src/tex/*.png`、原版 Link 皮肤贴图（头模板） | `work/build/tex/KarinOri_*.txtg` | `txtg.py` 读回头信息 |
| 图标 | 渲染的 `icon_*.png`、原版图标 | `work/build/icons/UI/Tex/Icon/*.bntx.zs`（12 个） | 尺寸、格式不变 |
| 头盔 pack | `03_kalin` 的 4 个 Head pack | `work/build/packs/Pack/Actor/` | 四个等级的 ArmorParam 差异相同 |
| 打包 | 以上 + 原版 RESTBL + 其他 mod 的 RESTBL | `00_Karin_Original/romfs/`（26 个文件） | `restbl_changes.json` 列出每个改动的条目 |
| 离线检查 | `TotkMdl export` 的 JSON | 姿势、面部、摆动的 JSON 和三视图渲染 | 见 §3 |
| 发行 | mod 文件夹 + 用户的相关 mod | Full / Lite 文件夹和 ZIP | 见 [存档与发行](SAVE_AND_RELEASE.md) |

`build_karin.py` 内部的顺序：

1. 读取 Karin 的网格和骨骼，用基础模型的骨架算出 Link 的世界绑定矩阵。Link 缺的右手指骨用左手镜像补上。
2. 生成每根人形骨的相似变换（头部单独缩放 / 下沉，腿部 `radial`），线性混合，写出 `karin_bones_game.json`。见 [重定向与比例](RETARGET_AND_PROPORTIONS.md)。
3. 在绑定姿势里压扁肩部。
4. 迁移权重：人形骨对到 Link 的骨，双马尾 / 裙摆 / 兽尾对到布料骨骼，再限制每个顶点的骨骼数并归一化。
5. 借用布料骨骼（`APPENDAGES`），见 [物理](PHYSICS.md) §3。
6. 面部拟合和眨眼拟合，见 [面部](FACE.md)。
7. 生成编辑 JSON 并调用 TotkMdl `replace`，编辑包括：
   - 删掉原套装的形状；
   - 复制皮肤材质并改名，避开染色动画；
   - 换采样器贴图；
   - `smoothBones`；
   - 新形状；
   - 头部和头发用浮点权重。

## 3. 离线检查

- **姿势**：`pose_test.py` 的测试姿势，看裙子和腿、肩的穿插。没有布料，是最坏情况。
  - 默认姿势：放下双臂并弯肘、抬左大腿屈膝、转头、前裙掀起 40°、后发摆开。
  - 也可以把 `*.pose.json` 作为第一个参数传入，项目的跑步姿势和图标姿势就是这样给的。
- **面部**：`face_preview.py` 用游戏的面部动画帧给 Head 摆姿势，再用 Blender 三视图看眨眼、口型、喊叫时的眼部变形。
  - 预览相机放在脸前：`blender_preview.py --cam 0 1.56 0.3`。
- **摆动**：`swing_test.py` 按真实铰链轴转动借用骨骼，看耳朵伸长和刘海的方向，见 [物理](PHYSICS.md) §6。
- **比例**：手臂下垂（70°）时的外轮廓半宽，以及下巴到肩关节连线的距离，都与「Karin 原比例 × 实际高度倍率」比较。
- **贴图的 UV 约定**：用 `03_kalin` 自己的图集渲染它的头部来核对。

## 4. 等价性（便携包）

便携版脚本在项目工作目录上重跑（2026-11-07），结果与 v7c 逐字节相同：

- 三个模型：头 `04e074eb…`、下装 `9c712ec1…`、上衣 `31304250…`；
- 6 张贴图、12 个图标；
- 打包出的 26 个文件，含 RESTBL。

详见 `portable-kits/VALIDATION.md`。
