# 开发工具

## 1. 外部工具

| 工具 | 版本 | 用途 |
| --- | --- | --- |
| Blender | 5.0 | 全部几何、权重、dyng 规格、表情求解（用 Blender 自带的 Python 和 numpy） |
| Witcher3-Blender-Tools（dingdio） | v1.1.0（`witcher3_tools.zip`，SHA-256 `cc422fb0…ba76700ac`），作为 Blender 4.2+ 扩展装在 `user_default` 仓库 | 读 w2rig / w2mesh / w2anims（`dc_anims.load_bin_anims_single(..., rigPath=man_base.w2rig)` 导入原版动画）、原生写 w2mesh、写 xbm（调用 texconv）。脚本按模块名 `bl_ext.user_default.witcher3_tools` 启用它（`W3_ADDON_MODULE` 可改） |
| WolvenKit 7 nightly | `7.2.0-nightly.2026-10-14`（zip SHA-256 `97f99d9c…cacecab5018734`） | 只用 CLI 的 `--cr2w2json` / `--json2cr2w`；`.exe.config` 的 sku 降到 .NET 4.8 |
| Python | 3.10+，标准库 | 自写的 bundle / store / CR2W 工具和 JSON 生成器 |
| PowerShell | 7 | `prepare.ps1`、`pipeline.ps1`、`wk.ps1` |

插件的偏好里要填游戏目录、uncook 目录（工作目录的 `uncook\`，脚本把 depot 路径直接拼在后面，所以带结尾分隔符）和 WolvenKit CLI 的路径，
构建脚本每次启动时自己设。

## 2. 自写工具（便携包 `scripts/`）

- `w3bundle.py`：v5 bundle 列表 / 提取 / 打包；`w3metadata.py`：读 store（调试用）；`w3metadata_write.py`：写 v7 store。
- `fix_cr2w_skeleton_names.py`：WolvenKit 写出的骨架名改回原版编码（[技术合同](TECHNICAL_CONTRACTS.md) §3）。
- 模板 / 资源生成器：`make_empty_item_template.py`、`make_mesh_item_template.py`、`make_dangle_item_template.py`、`make_head_item_template.py`、
  `make_dyng.py`、`make_w3fac.py`（读 `face_pose_map.POSE_GAIN`）。都在 WolvenKit 的 JSON 上做最小修改。
- `build_mod.py`：按 bundle 清单铺满全部 `geralt_items` 模板并打包。
- Blender：`karin_build.py`、`make_stub_mesh.py`、`karin_preview.py`；求解库 `karin_face.py`（numpy），映射表 `face_pose_map.py`。

## 3. 离线检查（便携包 `scripts/checks/`）

| 检查 | 回答什么问题 |
| --- | --- |
| `blender/idle_view.py`、`blender/idle_head.py` | 目标形状：待机姿势里每个 dyng 节点都在刚度目标上（全刚性）时是什么样；全身从右侧到背后 5 个角度（看尾巴、双马尾），头部特写 6 个角度（看刘海、侧发）；绑定姿势同角度对照。拿来和游戏截图比，判断「停下后的形状对不对」 |
| `blender/skirt_walk_sink.py` | 走 / 跑 / 冲刺帧里裙子会不会穿：三种模式（全刚性、按当前碰撞上限往里推、髋圈保持 98 %），带 look-at 传递，沿皮肤法线射线检查 |
| `blender/face_geom.py` | 刘海 / 侧发离脸多远、头部碰撞中心放哪（网格搜索头发 − 中心方向与脸部法线的夹角） |
| `rule_check.py` | 每个 look-at 节点的绑定滚转和游戏规则差多少度（目标 0°） |
| `regen_metadata_compare.py` | 用原版 bundle 重建原版 store，逐表比较（换游戏版本后先跑它） |
| `blender/cmp_w2mesh.py` | 两个 w2mesh 内容是否相同（忽略顶点顺序） |

项目里还用过、没有随包的一次性脚本（思路值得复用）：原版动画的姿势网格渲染（待机、跑、冲刺、持剑待机、举过头顶的攻击，查肩部缺口）；
待机姿势里检查有没有被违反的碰撞链接；原版 dyng 的扭转 / look-at 统计（原版链 98.7 % 相邻骨扭转 < 30°、look-at 节点 |Z · 父 Z| 中位数 0.98）；
按游戏滚转规则重建骨后渲染，和游戏截图对照。

## 4. 实机测试自动化

测试和用户在同一台 Windows 机器上，游戏是 DX12 版 `bin\x64_dx12\witcher3.exe`，窗口标题 `The Witcher 3`。

- 窗口：pywinauto 找窗口句柄，mss 截客户区（截图前确认窗口在前台、没被遮挡），AutoHotkey v2 发送按键，每次发送前后都核对前台句柄。
- 按键脚本：按住某键若干毫秒、可以串多组（`键 毫秒 键 毫秒 …`、`sleep 毫秒`）；冲刺 = 按住 W，300 ms 后加左 Shift。**冲刺脚本不松键，后面必须跟一次松键**；
  测试前先结束残留的按键脚本进程（一个卡住的进程让菜单按键错位，进了世界地图）。
- 启动循环：反复按空格跳过片头，直到主菜单的 logo 区域和参考截图匹配；Enter（继续）；如果弹出 CDPR 账号二维码就按 Esc；等加载转圈图标消失、
  画面不再全黑（连续两次）才算进游戏。读档后用小地图区域的亮度判断加载完成。
- 一轮标准测试（威伦的测试存档）：主菜单「继续」读最新存档 → 游戏里 Esc → 「读取游戏」→ 选威伦的快速存档 → 等加载 → 转镜头拍正面、背面、侧面待机
  → 冲刺 2 秒急停 → 每 0.5 秒一张连拍 10 秒左右（看链甩出去后能不能回到原形）→ 拼成对比图。看急停要在附近的溺尸过来之前做。
- 眨眼：约 12 fps 的连拍（mss 循环截图）。
- 存档：用户说测试存档可以随便用。新游戏测试会留下序章的检查点存档，它们会变成「最新」，主菜单「继续」会读到它们；用户自己玩也会产生新存档。
  每次自动化前看存档目录，按「读取游戏」列表里的位置选档。
- 显示：截图和连拍都按客户区坐标裁剪；全分辨率连拍用于看裙摆和膝盖。

## 5. 工作目录

- 工作目录放在同步盘之外（提取物、构建、截图、WolvenKit 副本都在里面，体积大、文件多）。项目目录只放脚本、状态文件和发行包。
- `prepare.ps1` 可以随时在一个新的工作目录里重建全部准备数据（2026-10-23 实测约 16 秒，含 WolvenKit 复制）；`pipeline.ps1` 一次完整构建约 40 秒
  （含 Blender）。
