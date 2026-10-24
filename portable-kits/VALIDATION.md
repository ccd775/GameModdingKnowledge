# 迁移验证记录

## 2026-10-24：新增刺客信条：大革命便携包

- **迁入内容：** 18 个文件，放在 `portable-kits/assassins-creed-unity/`。
  - `scripts/` 下 11 个 Python，来自项目 `scripts/`：`acu_forge.py`、`scan_objs.py`、`objs_to_tsv.py`、`acu_install.py`、`bt_tool.py`、`build_mod.py`、`acu_phys_skel.py`、
    `make_release.py`、`head_bones.py`、`glb_rotate.py`、`glb_info.py`；
  - `scripts/blender/` 下 5 个 Blender 脚本，来自项目 `scripts/`：`prep_karin_original.py`、`fit_karin.py`、`face_rig.py`、`export_karin_lods.py`、`render_compare.py`；
  - `acuharness/` 下 AcuHarness 的 `Program.cs`、`build.ps1`，来自项目 `tools/AcuHarness/`：项目原创的 C# 驱动（奥德赛 AcoHarness 的分支），引用用户自备的
    AnvilToolkit 1.3.6，不带 AnvilToolkit、`Unity.gfl` 或 .NET 的任何文件；
  - PROVENANCE 每个文件一行（18 行），全部有项目原件；
  - 新增 `README.md`、`toolchain.json`、`requirements.txt`（numpy）。公共层 `modkit.py` 的游戏列表加上 `assassins-creed-unity`，导出器和导出测试因此覆盖它。
- **没有迁入：** 本机实机测试的窗口 / 按键辅助脚本 `gsnap.py`、`game_input.ahk`（绑定本机的窗口桥、AutoHotkey 路径和前台锁，做法写在
  `games/assassins-creed-unity/DEV_TOOLING.md` §5）；发行包里的 `.cmd`（由 `make_release.py` 生成，仓库不收 `.cmd`）；崩溃转储的一次性分析脚本和
  原版 BallJoint 的统计脚本（方法写在 `DEV_TOOLING.md` §4 和 `PHYSICS.md` §2、§4）；反编译的 AnvilToolkit；全部工作数据（索引、副本清单、提取的数据文件、
  XML、blend、GLB、payload、发行 zip、截图、崩溃报告）。
- **便携改动**在 12 个文件：
  - 写死的本机路径改成环境变量或参数，缺了先报错并说出变量名，什么都不写：
    - `acu_install.py`：模块级的游戏目录默认值原来是一个固定路径 → 空（`ACU_GAME_DIR` 或 `find_game()` 的 Steam 库查找；`find_game()` 原样保留）；
    - `build_mod.py`：工程的 `work`、`cache`、harness，共享工具目录里的 dotnet、texconv → `ACU_DOTNET`、`ACU_HARNESS`、`ACU_TEXCONV`、`ACU_SRC_TEX`、`ACU_TEMPLATES`、
      `ACU_CACHE`，在 `main()` 开头、删输出目录之前一起检查；游戏目录原来来自 `acu_install` 的固定默认值 → `--game` / `ACU_GAME_DIR` / Steam 库；
    - `scan_objs.py`：dotnet、harness、`cache` 和游戏目录 → `ACU_DOTNET`、`ACU_HARNESS`、`ACU_CACHE`、`--game` / `ACU_GAME_DIR` / Steam 库；
    - `acuharness/build.ps1`：共享工具目录、写死的运行时版本目录、工程的 `anvil_runtime\Lists` 和 `bin\` 输出 → `-AtkDir` / `ACU_ATK_DIR`、`-DotnetRoot` / `ACU_DOTNET_ROOT`、
      `-ListsDir` / `ACU_ATK_LISTS`、`-OutDir` / `ACU_HARNESS` 所在目录，`-RuntimeVersion` 默认 9.0.18；
  - 没有 argparse 的命令补上了 argparse（`acu_forge.py`、`objs_to_tsv.py`、`acu_install.py`、`bt_tool.py`、`build_mod.py`、`acu_phys_skel.py`、`make_release.py`、`head_bones.py`、
    `scan_objs.py`），位置参数和选项不变；原来 `--help` 会以非 0 退出，`objs_to_tsv.py --help` 和 `make_release.py --help` 甚至会把 `--help` 当输出文件名。
    `acu_phys_skel.py` 的 `--no-collide` 原来在 `params()` 里查 `sys.argv`，改成 `main()` 设置的模块变量（第一次改时 argparse 的结果和函数里后面的局部变量 `a` 重名，
    被等价性核对抓到，已改名）；
  - `glb_rotate.py`、`glb_info.py` 与奥德赛便携包的同名文件相同（项目原件也和奥德赛的项目原件相同）；
  - 换行：每个迁入文件保留原来的换行（`build_mod.py`、`fit_karin.py`、`face_rig.py`、`Program.cs` 是 CRLF，其余 LF）。

  其余 6 个文件与原文件逐字节相同：`prep_karin_original.py`、`fit_karin.py`、`face_rig.py`、`export_karin_lods.py`、`render_compare.py`、`Program.cs`。处理逻辑没有改。
- **等价性验证（本机，2026-10-24）：**
  - **条件：** Windows 10 19044；Python 3.14.0 + numpy 2.5.2、Pillow 12.3.0；游戏（Steam build 21970519，原版）、AnvilToolkit 1.3.6、.NET 9.0.18 运行时、texconv 在本机。
  - 原脚本和便携脚本在同一份输入上运行，输出逐字节比较，31 项全部相同：
    - 合成数据：`acu_forge.py index` / `extract`（3 个合成的 v27 forge，两张链接的索引表、`dlc_1\` 下一个）；`acu_install.py` 的 install → status → uninstall
      （游戏目录带空格；通用 payload、forge 专用版本、`skip.tsv`、`vanilla_sizes.tsv`；`--game` 与 `ACU_GAME_DIR` 两种方式；`.tar.xz` payload；forge 大小不符时的拒绝信息），
      卸载后游戏目录与安装前逐字节相同；`make_release.py`（两个标签）：zip 里除 `acu_install.py`（便携包打进便携版，按设计不同）外每个成员相同，便携包打的包能用
      包里的安装器装上再卸掉；
    - 本机真实数据：`bt_tool.py` 的 `edit`（`--drop` + `--clear-dynres`、带路径的 `--set`）/ `lodsel` / `show`（亚诺的原版表和 LODSelector）；`acu_phys_skel.py` 四种参数
      （v7、v7x 的 `--capsule-scale 2`、`--no-collide`、不给 `--id`）：骨架、`BallJointCommonData`、`LiteRagdoll` 和报告相同，且 v7 / v7x 的输出与项目里实际发行用的
      XML 逐字节相同；`objs_to_tsv.py`（项目的两份扫描日志）；`head_bones.py`、`glb_info.py`、`glb_rotate.py +90`（Karin 的 LOD0 GLB）；
  - `acu_forge.py index` 跑全部 63 个 forge（180 245 行），与项目的 `cache/index.tsv` 逐字节相同；
  - `acuharness/build.ps1` 用上面的变量编译出 AcuHarness；便携的 `build_mod.py`（经 Steam 库自动找到游戏）用它重建 v7：457 个数据文件、`skip.tsv` 与发行的 v7 同名，
    `skip.tsv` 逐字节相同；数据文件容器的字节每次打包都不同，两边都用 harness 的 `unpack-data` 解开后，14 585 个对象全部逐字节相同；
  - 便携的 `make_release.py` 打包发行的 v7 payload：`payload_v7.tar.xz`（44 232 152 字节）、三个 `.cmd`、`README.txt` 与发行包逐字节相同，只有 `acu_install.py` 不同；
  - 缺变量：`build_mod.py`（一次列出 6 个变量，输出目录没有被创建）、`scan_objs.py`（3 个）、`build.ps1` 都在动手之前报出变量名。
  - **没有重跑的部分：** `scan_objs.py` 的实际扫描（只核对了缺变量的报错；它调用的 `scan-objs` 在构建里间接用到的副本清单与项目相同）；5 个 Blender 脚本；在游戏里装便携版
    重建的 payload（与发行的 v7 内容相同）。实机结论来自项目用原脚本构建的 v1–v7。
- **合成数据测试：** `AssassinsCreedUnityTools` 6 项：PROVENANCE / 便携性（每个文件一行，哈希、字节数、修改标记、`bundled_scripts` 一致；没有盘符路径、用户目录、
  写死的 `sys.path`、窗口辅助脚本和 `.cmd`）；合成 forge 上的安装（通用 / 专用版本、`skip.tsv`、状态、重复安装拒绝、逐字节卸载、`.tar.xz` 与 `ACU_GAME_DIR`、大小不符和缺 payload 的拒绝）；
  发行 zip 的成员、`vanilla_sizes.tsv` 和用包里的安装器往返；附加骨架的 v3 规则（深度优先、`Index`、`ChildBoneCount` = 后代数、自己的键、BallJoint 引用为空）、
  重力补偿的方向（下垂的裙片朝外、水平的尾巴朝上）、碰撞对象和 `--no-collide` / `--capsule-scale`；`objs_to_tsv.py`；缺变量的报错。`--help` 测试覆盖 `scripts/` 下全部 11 个脚本；
  没装 numpy / Pillow 时，要它们的项跳过。上面的等价性核对是本机手工跑的，没有写进测试套件。
- **未验证：**
  - 便携版没有装进游戏测试（重建出的 payload 内容与用户接受的 v7 相同）；
  - 测试套件对 Blender 脚本只做语法检查，`Program.cs` 没有在测试里编译；
  - 非 Windows 系统（安装器用 `tasklist` 判断游戏是否在运行、用注册表找 Steam）、其它游戏版本 / 平台；
  - 新模型的案例常量。

## 2026-10-24：奥德赛便携包更新（第二个模型 Karin_PicodraTech）

- **变更内容：**
  - 更新 4 个文件：`build_mod.py`（`--model original|pt`：`MODELS` 表、图集自带的法线贴图 `normal_png`）、`aco_phys_skel.py`（`--attach`）、
    `blender/export_karin_lods.py`（导出配置 `aco_pt`）、`blender/pose_preview.py`（状态里的 `rot`：按骨 ID 直接转，子骨跟着转）；
  - 新增 2 个文件：`normal_curl.py`（法线贴图 G 约定的旋度测试）、`make_dist.py`（写 `BUILD_INFO.json` / `MANIFEST.sha256` 并打 zip；上次没迁入的打包步骤，
    这次在项目里写成了脚本）。两个新脚本在项目里就改成了 argparse，`--help` 检查不需要另做便携改动；改完后用 `make_dist.py` 在副本上重做了 PicodraTech 包，
    `BUILD_INFO.json` 和 `MANIFEST.sha256` 与原包逐字节相同。
  - 便携改动：项目原件的改动按原样移植进便携版，原有的路径参数化不变；`build_mod.py` 的贴图目录变量按模型检查（`--model original` 要 `ACO_SRC_TEX`，
    `--model pt` 要新的 `ACO_PT_TEX`），`aco_phys_skel.py` 的 `--attach` 进了 argparse。`export_karin_lods.py`、`normal_curl.py`、`make_dist.py` 与项目原件逐字节相同。
  - PROVENANCE 更新 4 行（`original_sha256` 换成新的项目原件），新增 2 行；`toolchain.json` 的 `bundled_scripts` 加 2 个脚本。
- **等价性验证（本机，项目的真实输入）：**
  - **条件：** Windows 10 19044；Python 3.14.0 + numpy 2.5.2、Pillow 12.3.0；AcoHarness（项目编译的那一份）、texconv；没有 Blender 参与。
  - `aco_phys_skel.py`：PicodraTech 的 LOD0 GLB 和拟合报告，`--params` + `--attach`（190 根骨、107 条记录）和全部默认（134 条）两种；原脚本、`ACO_WORK`、
    `--template` / `--base` 的骨架 XML 和报告逐字节相同，`--params` + `--attach` 的输出也与 PicodraTech v1 包里用的骨架 XML 相同。
  - `build_mod.py`：本包脚本重建 `--model pt`（PicodraTech v1）和 `--model original`（Karin_Original v8）的 payload，用 AcoHarness `unpack-data` 解开每个 `.data`
    逐个比内部文件：PicodraTech 的 7 个数据文件（LOD0 里 18 个对象）与项目构建相同，v8 的 7 个（LOD0 里 15 个）与 v8 包相同；`skip.tsv` 相同。
    `.data` 容器本身每次构建的字节都不同，所以不比它的哈希。
  - 复审后 `aco_phys_skel.py` 只改了参数表上方的注释（按键合并的说明），项目原件和便携版一起改，重跑上面的骨架比较仍逐字节相同。
  - 项目原件的回归（改共用脚本之前的版本 → 改之后）：用改过的项目脚本重建 v8，骨架 XML 逐字节相同，24 个内部文件与 v8 包逐个相同。
- **合成测试新增 2 项：**
  - `normal_curl.py`：按「绿色朝图像上方」烘出的高度场法线相关系数 < −0.5，翻转 G 后 > 0.5；图里另有一块近黑（各通道 < 10）、约定相反的高频图案，
    只有跳过近黑像素时符号才对（去掉跳过那一行后这一项失败）；
  - `build_mod.normal_png`：空白先填平（填平的区域保持平、UV 岛边缘没有被黑色拉歪的像素 —— 去掉填平那一行后这一项失败），按要求翻转 G，B = 0、A = 光泽度。

  `ACO_DEPS` 里 `build_mod` 加 numpy、新增 `normal_curl`。
- **实机证据：** 没有。PicodraTech v1 按用户要求没有安装（「暂不进行自主测试」），只有离线核对（`games/assassins-creed-odyssey/cases/KARIN_PICODRATECH.md` §3）。
- **未验证：** 2 个 Blender 脚本（`export_karin_lods.py` 与原件相同、`pose_preview.py`）没有用本包重跑，项目里用原件跑过；`--model pt` 的贴图、物理参数、`--attach` 在游戏里的效果。

## 2026-10-24：看门狗面部表情、Windy City II 私有头部、City Noir 构建器扩展

- **变更内容：**
  - 更新 10 个文件，同步为项目 kit（`.work/karin_citynoir/kit/scripts/`）的当前版本：
    - `build_from_vrm.py`、`vrm_fit.py`、`vrm_model.py`、`vrm_textures.py`、`vrm_physics.py`、`xbg_physics.py`、`xbt_encode.py`：City Noir 的悬挂、权重改挂、UV 岛重排、加大漫反射、披肩布料选项，以及 `face` 段和 `--facial-definition`；
    - `package_mod.py`、`repack_fat8.py`、`char01_paths.py`：`transform=` 钩子、可增删条目的 `write()`、dpdx 路径。
  - 新增 5 个文件：
    - `dpdx_format.py`、`vrm_face.py`、`xbg_face.py`、`private_head.py`：与项目原件逐字节相同；
    - `face_preview.py`：只把导入路径改成脚本自身目录。
  - 新增 2 个配置样板：`karin_original_face.json`、`karin_pt_face.json`。
  - PROVENANCE 更新 14 行（只改 portable 哈希，原始取证值不变），新增 5 行。
  - 公开版之前只有旧版代码，没有便携改动，所以直接以 kit 原件覆盖。行尾统一为 LF。
- **本次修正：** `xbg_face.py` 原来用 scipy 的 KD 树做最近邻。改成纯 numpy 后，输出的 XBG 变了。
  - 原因：VRM 接缝处同一位置有几个顶点，其中 4 个在 blink 键下会分开，两种实现对并列的处理不同。
  - 改为在重合顶点里取网格邻点与 XBG 顶点的邻点重合的那个，改后与 KD 树起点得到的结果相同。
  - 项目里的蓝白 Karin 1.7.0-test 已按此重建。
- **等价性验证：**
  - **条件：** Python 3.14.0、numpy 2.5.2、Pillow 12.3.0，全部用本包脚本。
  - **结果：**
    - `profiles/karin_original.json`：ZIP 与 Karin_Original 0.1.2 逐字节相同（`20D92DD7…`）；
    - `profiles/karin_original_1_0_0.json` + char10 碰撞体：XBG 与 1.0.0 相同（`609B07FC…`）；
    - `profiles/karin_original_face.json`：XBG `52159161…`、dpdx `70B4CDF6…`，与 Karin_Original 1.1.1-test 的构建相同；
    - `xbg_face.py` 加在蓝白 Karin 1.6.0 的 XBG（`338CB93E…`）上：XBG `EFE581FE…`、dpdx `271CBE64…`，与 1.7.0-test 的构建相同。
- **离线闸门：**
  - `face_preview.py`：静止位移 0，眨眼控制最多移动 46–50 mm；
  - 眨眼相对残差约 0.07，眼睑边缘到位 99.5% 以上；
  - `xbg_face.py` 对齐：中位误差 0.04 mm，最大 0.09 mm，3,254 个顶点全部对上；
  - 改动范围：骨架只改眼骨和下巴的局部平移，29 个逆绑定（都在这三根骨的子孙上）；网格只改两个 LOD 脸的权重。
- **实机证据：**
  - Karin_Original 1.1.0-test：游戏读取包里的 dpdx，嘴会动，眨眼闭不严，眼珠几乎看不出在动；
  - 私有头部：Karin_Original 1.0.1-test 在装与不装 WC2 1.1.2 时脸都正常（2026-10-10）；
  - City Noir 0.1.0–0.1.2 的结果见 `games/watch-dogs/PHYSICS.md` §7。
- **合成测试新增 `WatchDogsFace` 5 项：**
  - dpdx：四元数编解码；无旋转码；纯平移增量；旋转缩放；写出与读取的往返；截断文件报错；
  - 平移眼睑：两方向锥的拟合，份额非负且和不超过 1；单骨主方向；带上限的非负最小二乘；
  - dpdx 改写：父空间平移、跟随比例、去掉睁大方向和其他轴的控制、无旋转码、挪动骨骼的静止平移，以及不一致时报错；
  - 对齐：相似变换复原、分块最近邻，接缝两侧各取自己一侧的顶点；
  - FAT：`write()` 增删条目、16 字节对齐、拒绝异常尾部。
- **未验证：**
  - 平移眼睑、视线 ×2 未经实机；
  - `xbg_face.py` 只用在蓝白 Karin 1.6.0 上；
  - `face` 段和 `private_head.py` 没有端到端的合成测试，只用真实数据核对过；
  - City Noir 的选项只有部分实机结论（0.1.3 起的结果未知）。

## 2026-10-24：西之绝境构建器更新（手部、表情、借用物理）

- **变更内容：**
  - 更新 2 个文件：`build_hfw.py`、`fit_hfw.py`；
  - 新增 3 个文件：`face_hfw.py`（面部绑定模块）、`hand_pose.py`（握拳测试）、`face_pose.py`（面部测试姿势）。
  - 5 个文件都与项目原件逐字节相同。两个测试脚本在项目里就改成了 argparse，所以 `--help` 检查不需要另做便携改动。
  - PROVENANCE 更新 2 行，新增 3 行。
- **新开关：** `--hands rigid|tps`、`--face rig|rigid`、`--physics pbd|none`。做法见 `games/horizon-forbidden-west/BUILD_PIPELINE.md`。
- **等价性验证：**
  - **条件：** build `14835813`，环境同 2026-10-02。h2 导出是从重建的干净根目录重新导出的，用旧脚本重建出的 v4，33 个 mod 文件与实机版逐字节相同。
  - **结果：** 用本包脚本复核：
    - `--hands tps --face rigid --physics none`：30 个构建输出与 v4 相同；
    - 全部默认：30 个构建输出与 1.1.0 相同；
    - `--face rigid --physics none`（项目脚本）：25 个 ascii 与 1.0.1 相同。
  - **mod 文件：** 1.0.1 与 v4 相比有 3 个文件不同，1.1.0 与 1.0.1 相比有 11 个不同。两版的发布 zip 解压后，都与实机测试时安装的文件逐字节相同。
- **离线闸门：**
  - 握拳测试中插进相邻手指的顶点数：v4 为 69，1.0.1 和 1.1.0 为 0，与原版 Beta 相同；
  - 面部测试姿势：Karin 与 Beta 跟随同样的骨骼，眨眼时 Karin 不动；
  - 重合顶点中权重不一致的组：v6 为 92 组，1.1.0 为 0。
- **实机证据：**
  - **1.0.1：** 用户在过场动画里确认手指已修好。
  - **1.1.0：** 用户认可裙摆、双马尾、尾巴的摆动；agent 在照片模式里确认表情生效。对话中的口型没有专门检查。
- **合成测试新增 3 项：**
  - 三角形最近点（与密集网格暴力比对）、重心插值采样（槽位和稠密两种权重一致）、RBF 命中标记点；
  - 粒子链沿长度的分配和根部渐变；
  - 手掌坐标系是右手正交系，旋转后由两组坐标系能复原出旋转。

  根测试共 87 项，全部通过。

## 2026-10-23：新增刺客信条：奥德赛便携包

- **迁入内容：** 18 个文件，放在 `portable-kits/assassins-creed-odyssey/`。
  - `scripts/` 下 11 个 Python，来自项目 `scripts/`：`aco_forge.py`、`aco_locate.py`、`aco_gfl.py`、`aco_install.py`、`bt_tool.py`、`build_mod.py`、
    `build_atlas.py`、`aco_phys_skel.py`、`aco_pose_sim.py`、`glb_rotate.py`、`glb_info.py`；
  - `scripts/blender/` 下 5 个 Blender 脚本，来自项目 `scripts/`：`fit_karin.py`、`face_rig.py`、`export_karin_lods.py`、`pose_preview.py`、`aco_pack_atlas.py`；
  - `acoharness/` 下 AcoHarness 的 `Program.cs`、`build.ps1`，来自项目 `tools/AcoHarness/`：项目原创的 C# 驱动，引用用户自备的 AnvilToolkit 1.3.6，
    不带 AnvilToolkit、`Odyssey.gfl` 或 .NET 的任何文件；
  - PROVENANCE 每个文件一行（18 行），全部有项目原件；
  - 新增 `README.md`、`toolchain.json`、`requirements.txt`（numpy）。公共层 `modkit.py` 的游戏列表加上 `assassins-creed-odyssey`，导出器和导出测试因此覆盖它。
- **没有迁入：** `rshot.sh`、`rshots.sh`、`shrink_shot.ps1`（测试机远程截图 / 缩图的私有辅助脚本，绑定本机的远程桌面工具链；做法写在
  `games/assassins-creed-odyssey/DEV_TOOLING.md` §4）；可重新部署包的 `_env.cmd`、`install.cmd`（和包里的 `uninstall.cmd`、`status.cmd`）：仓库不收 `.cmd`，
  做法写在 `games/assassins-creed-odyssey/VALIDATION_AND_RELEASE.md` §3；生成 `BUILD_INFO.json` / `MANIFEST.sha256` 的打包脚本（不在交来的项目原件里）；
  影项目的 `skirt_follow.py`、`acsh_forge.py`、链根表、规范化的源 blend 和贴图；全部工作数据（提取的数据文件、XML、blend、GLB、payload、包 zip、录像、截图）。
- **便携改动**在 13 个文件：
  - 写死的本机路径改成环境变量或参数，缺了先报错并说出变量名，什么都不写：
    - `aco_locate.py`：索引目录原来默认脚本目录旁的 `cache`，游戏目录原来默认一个固定路径 → `ACO_CACHE` / `--cache`、`ACO_GAME_DIR` / `--game`（只有 `extract` 要）；
    - `aco_install.py`：游戏目录原来默认同一个固定路径 → `ACO_GAME_DIR` / `--game`，新增 `set_game()`；`install` / `uninstall` / `status` 的位置参数不变，
      包里 `install.cmd` 的调用方式照常可用；
    - `build_mod.py`：工程的 `work`、harness，影项目的 dotnet、texconv、源贴图 → `ACO_WORK`、`ACO_HARNESS`、`ACO_DOTNET`、`ACO_TEXCONV`、`ACO_SRC_TEX`，
      在 `main()` 开头、删输出目录之前一起检查；
    - `build_atlas.py`：影项目的 texconv → `ACO_TEXCONV` / `--texconv`；
    - `aco_phys_skel.py`：工程 `work` 下的两个模板 XML → `ACO_WORK`，新增 `--template` / `--base`；
    - `aco_pose_sim.py`：同步盘上的 `sys.path` 和头部骨架 XML → 脚本自己的目录、`ACO_HEAD_SKELETON_XML` / `ACO_WORK`；`Skel()` 的默认参数改为 `None`，缺了报错；
    - `aco_gfl.py`：影项目的脚本目录和工程的 GFL → `ACO_ACSH_SCRIPTS` / `--acsh-scripts`、`ACO_GFL` / `--gfl`，`acsh_forge` 改为检查参数之后才导入；
    - `acoharness/build.ps1`：影项目的工具目录、写死的运行时版本目录、工程的 `anvil_runtime\Lists` 和 `bin\` 输出 → `-AtkDir` / `ACO_ATK_DIR`、
      `-DotnetRoot` / `ACO_DOTNET_ROOT`、`-ListsDir` / `ACO_ATK_LISTS`、`-OutDir` / `ACO_HARNESS` 所在目录，`-RuntimeVersion` 默认 9.0.18；
  - 没有 argparse 的命令补上了 argparse（10 个：`aco_forge.py`、`aco_locate.py`、`aco_gfl.py`、`aco_install.py`、`bt_tool.py`、`build_mod.py`、`build_atlas.py`、
    `aco_phys_skel.py`、`glb_rotate.py`、`glb_info.py`），位置参数和选项不变；原来 `--help` 会以非 0 退出（打印说明后 `sys.exit` 或下标越界）。
    不认识的子命令现在由 argparse 报错（原来打印说明后退出 1）；`aco_install.py install` 缺 payload 目录时报用法错误（原来下标越界）；
  - `blender/pose_preview.py`：按上一级的 `scripts/` 找 `aco_pose_sim`；加了 `--head-xml <xml>`，传给 `sim.Skel(...)`（不给时照旧用
    `ACO_HEAD_SKELETON_XML` / `ACO_WORK`）；说明里补了这三种来源、一次性计划任务不继承会话环境变量、需要 OpenGL 的提示；
  - 换行：每个迁入文件保留原来的换行，CRLF 的 `aco_install.py`、`bt_tool.py`、`build.ps1` 改动处也用 CRLF（`face_rig.py`、`Program.cs` 是 CRLF、未改）；其余 LF。

  其余 5 个文件与原文件逐字节相同：`fit_karin.py`、`face_rig.py`、`export_karin_lods.py`、`aco_pack_atlas.py`、`Program.cs`。处理逻辑没有改。
- **等价性验证（离线，本机，合成数据）：**
  - **条件：** Windows 10 19044；Python 3.12.10 的独立虚拟环境 + numpy 2.5.4、Pillow 12.3.0；没有游戏、AnvilToolkit、.NET、texconv 或 Blender 参与。
  - 原脚本和便携脚本在同一份合成数据上运行，输出逐字节比较，全部相同：
    - `aco_forge.py index` / `extract`（3 个合成的 v28 forge：根目录 2 个、`dlc_58` 下 1 个）；
    - `aco_locate.py find`（名字、16 位 ID、`/正则/`）/ `extract`；
    - `aco_install.py install` → `status` → `uninstall`（游戏目录带空格，2 个 payload，`skip.tsv` 跳过一份 DLC 副本）：安装后的全部 forge 和状态输出相同；
      卸载后游戏目录与安装前逐字节相同；`--game` 与 `ACO_GAME_DIR` 结果相同；
    - `bt_tool.py edit`（`--drop`、带反斜杠路径的 `--set`、`--clear-dynres`）/ `lodsel` / `show`；
    - `glb_rotate.py`（−90°，再转回 +90°）、`glb_info.py --joints`；
    - `aco_phys_skel.py`（合成的 2 骨模板 + 3 骨基础骨架 + 4 节 KP 链）：原脚本、`ACO_WORK`、`--template` / `--base` 三种方式的骨架 XML 和报告相同
      （6 根骨、2 条物理记录）；
    - `aco_pose_sim.Skel`：合成头部骨架 + 一个姿势，0.5 权重下各骨的全局变换相同。
  - 缺变量：`build_mod.py`（一次列出 5 个变量，输出目录没有被创建）、`build_atlas.py`、`aco_phys_skel.py`、`aco_gfl.py`、`aco_pose_sim.Skel()`、`aco_locate.py`、
    `aco_install.py`、`build.ps1`（4 个变量）都在动手之前报出变量名；`build.ps1` 用 PowerShell 解析器解析没有错误。
  - **没有重跑的部分：** `build_mod.py`、`build_atlas.py`、`aco_gfl.py` 的实际运行（要 AnvilToolkit / AcoHarness / texconv / 影项目的 `acsh_forge`）；5 个 Blender 脚本；
    AcoHarness 的编译和运行；在测试机上安装便携版。实机结论来自项目用原脚本构建的 v1–v8 和 v8 包的重新部署。
- **合成数据测试：** `AssassinsCreedOdysseyTools` 1 项：PROVENANCE 每个文件一行，哈希、字节数、修改标记、`bundled_scripts` 一致；本包文件里没有盘符路径和用户目录，
  每个文件一种换行，`sys.path` 里没有写死的路径，没有远程截图脚本和 `.cmd`。`--help` 测试覆盖 `scripts/` 下全部 11 个脚本；没装 numpy / Pillow 时，
  要它们的脚本跳过。上面的等价性核对是本机手工跑的，没有写进测试套件。
- **未验证：**
  - 便携版没有装进游戏测试；
  - 测试套件对 Blender 脚本只做语法检查，`Program.cs` 没有编译；
  - 非 Windows 系统（安装器用 `tasklist` 判断游戏是否在运行）、其它游戏版本 / 平台；
  - 新模型的案例常量。

## 2026-10-23：新增巫师3 次世代版便携包

- **迁入内容：** 27 个文件，放在 `portable-kits/the-witcher-3/`。
  - `scripts/` 下 14 个 Python：项目 `Tools/scripts/` 的 13 个（`w3bundle.py`、`w3metadata.py`、`w3metadata_write.py`、`build_mod.py`、`fix_cr2w_skeleton_names.py`、
    `make_empty_item_template.py`、`make_mesh_item_template.py`、`make_dangle_item_template.py`、`make_head_item_template.py`、`make_dyng.py`、`make_w3fac.py`、
    `face_pose_map.py`、`karin_face.py`），新写的 `w3paths.py`；
  - `scripts/blender/` 下 3 个 Blender 脚本，来自项目 `Tools/scripts/`：`karin_build.py`、`make_stub_mesh.py`、`karin_preview.py`；
  - `scripts/checks/` 下 7 个离线检查：会话里写的 `rule_check.py`、`idle_view.py`、`idle_head.py`、`skirt_walk_sink.py`、`face_geom.py`，工作目录 `scratch/` 的
    `regen_compare.py`（改名为 `regen_metadata_compare.py`），新写的 `cmp_w2mesh.py`；
  - `tools/` 下 3 个 PowerShell 7 脚本，来自项目 `Tools/scripts/`：`prepare.ps1`、`pipeline.ps1`、`wk.ps1`；
  - PROVENANCE 每个文件一行；两个新文件的 `original_sha256` 为空；
  - 新增 `README.md`、`toolchain.json`、`requirements.txt`（numpy）。公共层 `modkit.py` 的游戏列表加上 `the-witcher-3`，导出器和导出测试因此覆盖它。
- **没有迁入：** 实机测试的按键 / 截图 / 读档脚本（AutoHotkey、窗口桥、威伦测试流程：坐标、存档位置和本机路径都是这台机器的，方法写在
  `games/the-witcher-3/DEV_TOOLING.md` §4）；会话里的一次性分析脚本（姿势网格、碰撞链接、原版扭转统计、滚转模拟渲染等）；源模型、游戏提取物、
  WolvenKit、插件、构建产物和发行 zip。
- **便携改动**在 21 个文件（19 个迁入文件和 2 个新文件）：
  - 写死的本机路径（工作目录、游戏目录、源 FBX、WolvenKit、Blender、插件偏好）改由新文件 `w3paths.py` 从 `W3_GAME_DIR` / `W3_WORK` / `W3_SOURCE_FBX` 拼出，
    没设时报错并说出变量名；`karin_build.py` 的 `CFG` 里这些键默认 `None`，JSON 参数没给时才从环境变量取（新增 `png_dir` 键，原来写死）；
    插件模块名可用 `W3_ADDON_MODULE` 改；
  - `build_mod.py`：bundle 清单原来写死，改为 `--listing`（默认 `<W3_WORK>/scratch/all_bundles.tsv`），按 `utf-8-sig` 读；
  - 没有 argparse 的命令补上了 argparse（6 个：`w3metadata.py`、`fix_cr2w_skeleton_names.py`、`make_empty_item_template.py`、`make_mesh_item_template.py`、
    `make_dyng.py`、`make_w3fac.py`），位置参数不变；
  - `w3metadata.py`（调试读取器）原来按 v6 布局读：FileEntry 20 字节、BundleInfo 6 个 u32，读 v7 的 store 会错位；改为 v7 时 FileEntry 24 字节、BundleInfo 以 u64
    数据块长开头（与写出器、`regen_metadata_compare.py` 一致），打印时表不足 5 行不再越界。改后读原版 store 和 v0.4.4 的 store 都正好读到文件末尾；
  - Blender 脚本移到 `scripts/blender/`，按上一级的 `scripts/` 找 `w3paths`、`karin_face`、`face_pose_map`；`karin_build.py` 两处注释里的 scratchpad 脚本名改指便携包路径；
  - 检查脚本：路径改由 `w3paths` 拼出，补了用法说明；`regen_metadata_compare.py` 的游戏目录改为参数（默认 `W3_GAME_DIR`），重建的 store 只在给了 `--out` 时写出；
  - PowerShell：`prepare.ps1` / `pipeline.ps1` / `wk.ps1` 的工作目录、游戏目录、Blender、WolvenKit 改为 `-WorkRoot` / `-GameDir` / `-Blender` / `-WolvenKitDir` / `-Exe`
    参数，默认取 `W3_*` 变量，缺了先报错再做事；脚本目录改为 `tools/` 旁边的 `scripts/`；`make_stub_mesh.py` 的 JSON 参数改用 `ConvertTo-Json` 生成；
  - 换行：`w3metadata_write.py` 原文件是 CRLF，逐字节未改；其余都是 LF。

  其余 6 个文件与原文件逐字节相同：`w3bundle.py`、`w3metadata_write.py`、`make_dangle_item_template.py`、`make_head_item_template.py`、`face_pose_map.py`、
  `karin_face.py`。处理逻辑除 `w3metadata.py` 的 v7 读法外没有改。
- **等价性验证（离线，本机）：**
  - **条件：** Windows 10 19044；Python 3.14；Blender 5.0 + Witcher3-Blender-Tools v1.1.0；WolvenKit 7 nightly 2026-10-14；游戏 5.0.1048522；
    一个全新的工作目录（项目工作目录只读）；
  - **`prepare.ps1` + `pipeline.ps1`（含 Blender，不部署）：** 约 16 秒 + 40 秒。829 个打包文件中 822 个与 v0.4.4 逐字节相同（817 个物品模板、dyng、w3fac、
    脸部网格、两个存根）。身体 `karin_body.w2mesh` 只有顶点顺序不同：`cmp_w2mesh.py` 比较顶点（位置 + 按骨名的权重）、面、UV 的多重集合和骨组全部相同；
    同一个便携包连跑两次顶点顺序也不同（插件导出器的行为）。6 张 xbm 写着源 PNG 的绝对路径，路径归一化后每张只差 22 个字节（CR2W 头部的文件长、偏移、CRC）。
    所以 bundle / store 的哈希与 v0.4.4 不同、长度相同；
  - **打包：** 便携包生成的三个物品模板加上项目构建 v0.4.4 时的 depot，经便携包的 `build_mod.py` + `w3metadata_write.py` 打出的 `blob0.bundle` 和 `metadata.store`
    与 v0.4.4 逐字节相同（`597794E9…`、`177B780A…`）；补 argparse 之后用 `-SkipBlender` 重跑，模板、dyng / w3fac JSON 和打包结果不变；
  - **检查脚本：** `rule_check.py`（91 个 look-at 节点，0°）、`skirt_walk_sink.py`（40 帧：全刚性 1 个顶点 0.7 cm，current / snug 0）、`face_geom.py`
    （最佳中心 (0.02, −0.02) 13.5°）与项目会话里原脚本的输出一致；`idle_view.py`、`idle_head.py`、`karin_preview.py` 正常出图；`regen_metadata_compare.py`
    重建原版 store：FileInfo / FileEntry / Buffer / Hash 表一致，BundleInfo 只有 `buffers.bundle`（7.6 GB，原版记 0）不同，目录表顺序不同；
  - **没有重跑的部分：** `-Deploy` 和游戏内测试（实机结论来自项目用原脚本构建的版本）。
- **合成数据测试：** `TheWitcher3Tools` 共 11 项，不需要游戏、Blender 或 WolvenKit：
  - v5 bundle：头部字段、按小写路径排序、4096 对齐、CRC32 / MD5、只在变小时 zlib；v3 TOC 往返；命令行 `pack` / `list -v` / `extract`；
  - v7 store：FNV-1a 64 已知值、VLQ 往返（含负数）；两个 bundle 里的同名文件按 bundle 顺序链接、buffer 归属、目录树和 FileInit、按哈希排序的哈希表；读取器读到末尾；
  - CR2W 骨名修复：合成的 WolvenKit 形式 CSkeleton（含 72 字符的名字，两字节 VLQ 长度），名字表原地改名与 FNV-1a32、各表与导出 CRC、头 CRC、后续导出的偏移、尾部 buffer 不变；
    没有 CSkeleton 时拒绝；
  - 物品模板：发型物品（毛发组件与附着删除、约束属性顺序、wind / gravity / dampening、包围盒、导入表、嵌套的 `flatCompiledData` 同样改）、`--fur stub`、
    空物品、单网格物品（负数包围盒作位置参数）、头部物品（法线混合组件 / 附着 / 材质删除、眼睛换存根）；
  - dyng 与 w3fac JSON：节点 / 链接 / 三角形数组、碰撞记录、骨的 `name` String、rig 数据；placer / kf 骨对、映射、`POSE_GAIN`、空变换、锚点顺序不符时拒绝；
  - `build_mod.py stage` / `pack`：按清单分类（含 DLC 路径、去重、跳过剑鞘和别的角色）、`--extra`、缺 `W3_WORK` 时报错；
  - 表情求解（numpy）：`side_mask`、`nnls`、权重行和 = 活动份额、每顶点最多 4 根骨、阶跃位移场的重建误差、带种子的 k-means 可复现；
  - look-at 滚转检查（numpy）：按规则建的骨 0°，绕 X 转 90° 的骨 90°；
  - 路径与 PowerShell（要 pwsh 7 和 Windows，否则后半跳过）：`w3paths` 缺变量时报出变量名；3 个工具都能解析，缺变量时报出 `W3_GAME_DIR` / `W3_WORK` /
    `W3_WOLVENKIT_DIR` / `W3_BLENDER`；`wk.ps1` 用假 CLI 转换成功、输出含 ERROR 时失败；
  - PROVENANCE：每个文件一行，哈希、字节数、修改标记、`bundled_scripts` 一致；没有盘符路径和用户目录，每个文件一种换行，`sys.path` 里没有写死的路径。
- **未验证：**
  - 便携版没有装进游戏测试；
  - 测试套件对 Blender 脚本只做语法检查（上面的等价性验证是本机手工跑的）；
  - 非 Windows 系统（xbm 写出调用 texconv / WIC）、其它 Blender / 插件 / WolvenKit / 游戏版本；
  - 新模型的案例常量。

## 2026-10-16：新增往日不再便携包

- **迁入内容：** 45 个文件，放在 `portable-kits/days-gone/`。
  - `scripts/` 下 21 个 Python：项目工具目录 `ModTools/DaysGone/pytools/` 的 17 个（`abp_springs.py`、`anim_pertrack.py`、`blink_amp.py`、`fix_root_pose.py`、`pakextract.py`、`paklist.py`、`pakwrite.py`、`physchain.py`、`refskel.py`、`retarget_imports.py`、`retarget_inplace.py`、`shader_skips.py`、`skel_retarget.py`、`skelmesh_normals.py`、`skelmesh_positions.py`、`uhdr.py`、`upkg.py`），项目 `Scripts/` 的 `make_pak.py`、`patch_looks.py`，新写的 `lid_calib.py`、`dgpaths.py`；
  - `scripts/blender/` 下 13 个 Blender 脚本，来自项目 `Scripts/`：`build_body.py`、`face_rig.py`、`blink_rig.py`、`blink_sim.py`、`mouth_rig.py`、`viseme_sim.py`、`shape_sheet.py`、`fbx_common.py`、`dump_loop_normals.py`、`export_dummy_skeleton.py`、`skirt_body_shrink.py`、`fit_colliders.py`、`render_preview.py`；
  - `configs/` 下 3 个案例配置：`runs/t31/springs.json`、`runs/t30/mouth_map.json`、`runs/t28/lid_calib.json`，改名为 `springs_t31.json`、`mouth_map_t30.json`、`lid_calib_t28.json`，字节未改；
  - `dgexport/` 下 DgExport 的 `Program.cs`、`DgExport.csproj`；
  - `tools/` 下 6 个 PowerShell 7 脚本，由构建机 `DGModding/tools/` 的 `dgx_run.ps1`、`cook.bat`、`ue411.bat`、`swap.ps1`、`setres.ps1`、`watchgame.ps1` 改写为 `dgx_run.ps1`、`cook.ps1`、`ue_editor.ps1`、`install_pak.ps1`、`set_resolution.ps1`、`watch_launch.ps1`；
  - PROVENANCE 每个文件一行，记录原始和公开版的 SHA-256；两个新文件的 `original_sha256` 为空；
  - 新增 `README.md`、`toolchain.json`、`requirements.txt`（numpy）。公共层 `modkit.py` 的游戏列表加上 `days-gone`，导出器和导出测试因此覆盖它。
- **依赖闭包：** 按各脚本的 import 补齐了 `retarget_imports.py`、`fix_root_pose.py`、`shader_skips.py`、`patch_looks.py`（`make_pak.py` 用）。`fit_colliders.py` 导入 `physchain.py` 的胶囊函数，所以 `physchain.py` 也收进来了，尽管它的路线已放弃。
- **没有迁入：**
  - `physchain_v1.py`、`physasset_edit.py`：给玩家物理资产加链刚体的路线，玩家网格上额外刚体的 PhysX 约束在游戏里没有效果（t12–t19：限位、锁定和驱动都看不出作用），已放弃；
  - `abp_dynamics.py`：把游戏原有的 3 个 AnimDynamics 节点改到 Karin 的链上（t20），已被 `abp_springs.py` 取代；
  - 构建机的 `rungame.bat`（`setres.ps1 1920 1080` 后从 Steam 启动，拆成 README 第 6 步的两行）和 `swap_karin.bat`（`swap.ps1` 的批处理版，由 `install_pak.ps1` 代替）；
  - 源模型、参考 mod、游戏数据、DgExport 的输出、cook 结果、`runs/` 下的 blend / FBX / npz / pak。
- **便携改动**在 30 个文件（28 个迁入文件和 2 个新文件）：
  - 写死的本机 `pytools` 目录：`abp_springs.py`、`blink_amp.py`、`fix_root_pose.py`、`physchain.py`、`refskel.py`、`retarget_imports.py`、`skel_retarget.py`、`patch_looks.py` 改为脚本自己的目录，`make_pak.py` 的 `TOOLS` 同样；Blender 的 `blink_sim.py`、`mouth_rig.py`、`fit_colliders.py` 改为上一级的 `scripts/`；
  - 写死的缓存和源模型路径改由新文件 `dgpaths.py` 从 `DG_CACHE` / `DG_MODELS_DIR` 拼出，没设时报错并说出变量名：`make_pak.py`（游戏材质实例和外观，在 `main()` 开头、删暂存目录之前取）、`build_body.py`（`--target` 的默认值和源 VRM）、`face_rig.py`、`blink_rig.py`、`mouth_rig.py`、`viseme_sim.py`；
  - 没有 argparse 的命令补上了 argparse（15 个：`abp_springs.py`、`anim_pertrack.py`、`blink_amp.py`、`fix_root_pose.py`、`pakextract.py`、`paklist.py`、`pakwrite.py`、`physchain.py`、`refskel.py`、`retarget_imports.py`、`skel_retarget.py`、`uhdr.py`、`upkg.py`、`make_pak.py`、`patch_looks.py`），位置参数和选项不变。`pakwrite.py` 只用 argparse 检查参数，仍把原参数列表交给 `main()`（`make_pak.py` 直接调用它）；`uhdr.py` 多给任何参数仍是打印全部名字；`upkg.py` 的命令限定为 `dump` / `props`（原来别的命令什么也不做）；
  - PowerShell：`dgx_run.ps1` 的 DgExport、pak 目录和输出目录改为 `-Exe`、`DG_GAME_DIR`、`DG_WORK_ROOT`；`cook.ps1` 的 UE 和工程改为 `DG_UE_ROOT`、`DG_PROJECT`（默认 `<DG_WORK_ROOT>\U411\BendGame`），先建日志目录，按 `findstr` 的区分大小写方式筛 `Success - ` / `Failure - `；`ue_editor.ps1` 同上；`install_pak.ps1` 的 `~mods`、暂存和备份目录改为 `DG_GAME_DIR` / `DG_WORK_ROOT`，pak 名改为 `-Name`（默认 `zz_Karin_P`），没有暂存的 pak 时先拒绝（原脚本会先把已装的 pak 移走再失败），缺的目录自动建；`set_resolution.ps1` 的模式列表原来写到用户目录下的固定文件，改为只在给了 `-ModesFile` 时写，结果行总是打印；`watch_launch.ps1` 的输出目录原来写死，改为 `-OutDir`（默认 `<DG_WORK_ROOT>\out`），其余照旧；
  - 换行：每个迁入文件保留原来的换行，CRLF 的 9 个（`abp_springs.py`、`anim_pertrack.py`、`fix_root_pose.py`、`physchain.py`、`upkg.py`、`make_pak.py`、`build_body.py`、`face_rig.py`、`mouth_rig.py`）改动处也用 CRLF；新写的文件和 PowerShell 改写是 LF。

  其余 15 个文件与原文件逐字节相同：`retarget_inplace.py`、`shader_skips.py`、`skelmesh_normals.py`、`skelmesh_positions.py`、`shape_sheet.py`、`fbx_common.py`、`dump_loop_normals.py`、`export_dummy_skeleton.py`、`skirt_body_shrink.py`、`render_preview.py`、3 个配置、`Program.cs`、`DgExport.csproj`。处理逻辑没有改。
- **`--help`：** `scripts/` 下 21 个脚本在没设任何 `DG_*` 时都以 0 退出。不要 numpy 的 12 个：`paklist`、`pakextract`、`pakwrite`、`uhdr`、`upkg`、`retarget_imports`、`retarget_inplace`、`shader_skips`、`fix_root_pose`、`patch_looks`、`make_pak`、`dgpaths`。
- **等价性验证（离线，本机）：**
  - **条件：** Windows 10 19044；Python 3.14.0 + numpy 2.5.2（zlib-ng 1.3.1）；项目私有 Blender 4.2.23 LTS（UEFormat 0.10.0 在 `addons_core`）及其 Python 3.11.7 + numpy 1.24.3（zlib 1.2.13）；项目缓存经 `DG_CACHE`、源 VRM 经 `DG_MODELS_DIR`；项目的 `runs/` 只读，`build.blend` 先复制到临时目录，输出都写在临时目录；
  - **`make_pak.py`：** t31 的参数（`runs/t31/cooked_all`、`--normals t11`、`--positions t27`、`--skeleton t10`、`--extra` t31 的动画蓝图）用 Blender 的 Python 运行：pak 与 `runs/t31/zz_Karin_P.pak` 逐字节相同（`87576aec…`），`.report.json` 和暂存目录（79 个文件）也相同。用 Python 3.14 运行：暂存目录仍逐字节相同，pak 因 zlib-ng 压缩不同而字节不同，`pakextract.py` 解开后与 t31 的暂存目录相同；报告里法线统计的浮点数末位不同（numpy 版本）；
  - **`abp_springs.py`：** 游戏的 `Deacon_VimBlueprint`、t30 的 cook 网格和 `configs/springs_t31.json`，两种 Python 写出的动画蓝图都与 `runs/t31/Deacon_VimBlueprint.uasset` 逐字节相同（`352e10fd…`，加 101 个节点、核对 2479 个姿势链接）；`springs_report.json` 用 Blender 的 Python 时逐字节相同，用 numpy 2.5.2 时有些浮点数末位不同；
  - **`blink_amp.py`：** t30 的 `cooked_raw.uasset`、t29 的 `blink_rig.json`、`configs/lid_calib_t28.json`：网格与 t30 `cooked_all` 里的逐字节相同（`e827a26c…`），报告与 `runs/t30/blink_amp.json` 相同，两种 Python 一样；
  - **`skel_retarget.py`：** 游戏骨架加 `^face_=AnimationRelative`，280 根骨，与 `runs/t10/deacon_master_Skeleton.uasset` 逐字节相同；
  - **`lid_calib.py`：** 默认参数下与 `runs/t28/lid_calib.json` 逐字节相同（`31d835c4…`），两种 Python 一样；
  - **其他命令：** `pakextract.py` 解 t31 pak 得到的文件与 t31 暂存目录相同；`paklist.py`、`upkg.py dump`、`refskel.py`、`anim_pertrack.py` 正常输出。`uhdr.py` 读游戏格式的包（500 / licensee 34）会在名字表处出错，原脚本也一样（它只在 FileVersionUE4 ≥ 504 时跳过名字哈希），读原版 4.11 的包正常；
  - **Blender 脚本：** `build_body.py --variant B`（`--factory-startup`）的 `report.json` 和 5 张贴图与 t7 逐字节相同；`face_rig.py --check`（在 t7 的 `build.blend` 副本上）的 `face_rig.json` 与 t11 相同，4 张渲染像素相同（PNG 元数据里的日期和 `.blend` 路径不同）；`blink_rig.py`（t11 的 `build.blend` 和 cook 网格）的 `blink_rig.json` 与 t29 相同；`mouth_rig.py --render`（t29 的 `build.blend`、t29 的 cook 网格、`configs/mouth_map_t30.json`）的 `mouth_rig.json` 和 `mouth_sheet.png` 与 t30 相同；FBX 的字节因创建时间和源路径不同，没有逐项比较。`viseme_sim.py` 正常运行，没设 `DG_CACHE` 时报错并说出变量名；
  - **`fit_colliders.py`：** 和现在的 `physchain.py` 一起运行时在头部胶囊处报 `ValueError: min() arg is an empty sequence`（`physchain.DEFAULT` 里已没有和 `head` 碰撞的链）。用原脚本和原 `pytools` 运行结果相同，是项目的现状，没有改；它只服务于已放弃的 PhysX 路线；
  - **没有重跑的部分：** UE 4.11 的编辑器导入和 cook、DgExport（C#）、在测试机上安装和实机；与原文件逐字节相同的 Blender 脚本（`render_preview.py`、`shape_sheet.py`、`dump_loop_normals.py`、`skirt_body_shrink.py`、`export_dummy_skeleton.py`）；`make_pak.py --phys`、`patch_looks.py` 单独的命令行（`make_pak.py` 调用它的 `patch()`）、`physchain.py`。
- **合成数据测试：** `DaysGoneTools` 共 9 项，不需要游戏、Blender 或 UE：
  - pak v3：`pakwrite.py` 写出（zlib 多块、空文件、`--store`、`--mount`），页脚和索引 SHA-1，`paklist.py` 的列表，`pakextract.py` 解出后逐字节相同；
  - 合成的 Bend 格式包（版本 500、licensee 34、名字带哈希）：`upkg.py` 解析导入路径和类，`refskel.py` 的局部 / 组件空间矩阵，`retarget_imports.py` 改骨架导入后包头按新名字变长、导出数据不变，`fix_root_pose.py` 改写两份 `[Armature, Align]` 姿势而 `Align` 以下的组件空间姿势不变，找不到时报错；
  - `blink_amp.py`：放大骨的旋转和缩放、眼睑骨的静止平移、眼睑骨组件空间位置不变、闭眼位移等于幅度，两份姿势数组都改写；
  - `skelmesh_normals.py` / `skelmesh_positions.py`：合成的 32 字节顶点缓冲，按 UV 选角、双面角按旧法线选边、切线重新正交、W 字节保留，位移只动匹配的顶点、缓冲外的同值副本只计数不改，找不到缓冲时报错；
  - `abp_springs.py`：`quat_from_matrix()` 的往返（含 180° 旋转的分支），`node_specs()` 的弹簧常数 `I · omega²`、阻尼 `1 − exp(−drag)`、盒子、角度限制和径向平面，FName 的实例编号（`face_1544` 存成 `face` #1545）；
  - `anim_pertrack.py`：Float96NoW（全部分量 / 只存 X、Z）、带帧表的 IntervalFixed32NoW 旋转和 Fixed48NoW 旋转的轨道解码与下一条轨道的偏移；
  - `lid_calib.py`：中位数和最低帧，命令行在 `--cache` 下按 DgExport 的布局找输入、输出缩进 1 的 JSON；`dgpaths.py` 缺变量时报错；`lid_calib.py`、`make_pak.py` 没有 `DG_CACHE` 时在写任何文件之前失败；
  - PowerShell 工具（要 pwsh 7 和 Windows，否则跳过）：6 个都能解析；5 个在缺变量时报出变量名（`set_resolution.ps1` 只解析，运行会改本机分辨率）；`dgx_run.ps1` 的参数转发；`install_pak.ps1` 的哈希不符拒绝、安装并保留旧 pak、没有暂存时拒绝；
  - PROVENANCE：每个文件一行，哈希和字节数对得上，修改标记与哈希一致，与 `toolchain.json` 的 `bundled_scripts` 相同；本包文件里没有盘符路径和用户目录，每个文件只有一种换行，`sys.path` 里没有写死的路径，没有收已放弃的工具。

  `--help` 测试覆盖 `scripts/` 下全部 21 个脚本；没装 numpy 时，要 numpy 的测试和 `--help` 跳过。
- **未验证：**
  - 便携版没有装进游戏测试，也没有在构建机上跑 UE 4.11 一侧；实机结论来自项目用原脚本构建的 t5–t31；
  - 测试套件对 Blender 脚本只做语法检查；
  - 非 Windows 系统、其他 Blender / UE / 游戏版本；
  - 新模型的案例常量。

## 2026-10-14：新增漫威蜘蛛侠2便携包

- **迁入内容：** 38 个 Python 文件，放在 `portable-kits/marvels-spider-man-2/scripts/`，来源是项目的 `Work/tools/`。
  - 容器与格式 14 个：`sm2_common.py`、`sm2_dat1.py`、`crc64_table.py`、`sm2_stage.py`、`sm2_install.py`、`i30_model.py`、`i30_build.py`、`i30_writer.py`、`i30_texture.py`、`i30_joints.py`、`i30_dynamics.py`、`i30_actor.py`、`i30_actor_edit.py`、`bcdec.py`；
  - 流水线 16 个：`sm2_index.py`、`sm2_find.py`、`sm2_extract.py`、`suit_models.py`、`survey_targets.py`、`sm2_karin_geo.py`、`sm2_fit.py`、`vrm.py`、`render.py`、`sm2_build_model.py`、`sm2_assets.py`、`sm2_batch.py`、`sm2_dyn.py`、`sm2_face.py`、`sm2_prop_test.py`、`sm2_head_carrier.py`；
  - 验收 7 个：`sm2_verify_stage.py`、`sm2_verify_face.py`、`test_dyn_model.py`、`test_dyn_roundtrip.py`、`test_actor_roundtrip.py`、`sm2_pose_check.py`、`sm2_preview.py`；
  - 依赖补入 1 个：`survey_dyn2.py`。`test_dyn_roundtrip.py` 在模块顶层导入它的 `get()`，`test_dyn_model.py` 又导入 `test_dyn_roundtrip.py`，缺了它这两个脚本连 `--help` 都跑不了；
  - PROVENANCE 每个文件一行，记录原始和公开版的 SHA-256。`vrm.py`、`render.py` 与本库对马岛便携包的同名文件逐字节相同，`sm2_fit.py` 是对马岛 `fit.py` 加了 `set_mapping()`（项目当时就这样复制过来的）；
  - 新增 `README.md`、`toolchain.json`、`requirements.txt`（numpy、Pillow、scipy、etcpak：scipy 给拟合和 `sm2_pose_check.py`，etcpak 给 `sm2_assets.py` 压贴图）。公共层 `modkit.py` 的游戏列表加上 `marvels-spider-man-2`，导出器和导出测试因此覆盖它。
- **没有迁入：**
  - `sm2_package.py`：旧打包器（T3–T4b，只换两套默认战衣），已被 `sm2_batch.py` 取代；
  - `sm2_hsa_test.py`：T18 的多条 HeroSuitAddition 试验，路线已否决；
  - 一次性调查：`survey_align.py`、`survey_dyn.py`、`survey_flags.py`、`survey_fmt1_graphs.py`、`survey_joint_order.py`、`survey_materials.py`、`survey_models.py`、`find_materials.py`、`tex_inspect.py`，源 VRM 审计 `vrm_audit.py`、`vrm_read.py`；
  - ALERT、Overstrike、InsomniacTools 的源码（第三方，项目放在 `Work/ext/`）；
  - 游戏数据、解出的资产、`asset_index.json`、`reports/` 下的 JSON（`suit_models.json`、`targets.json`、`masked_suits.json`）、拟合结果、`.stage`、发行包和其中的 `install.bat` / `uninstall.bat`、源 VRM。`masked_suits.json`（v2 的 91 个战衣）是项目从全战衣 loadout 表整理的，没有对应脚本，README 写明了格式和 `--suit` 的替代用法。
- **便携改动**在 17 个文件：
  - `sm2_common.py`：游戏目录原先默认写死的本机路径，改为只读 `SM2_GAME`，没设时由 `game_dir()` 报错；工作目录（`native/`、`reports/`、`build_*`）改为 `SM2_WORK`，默认仍是 `scripts/` 的上一级；ALERT 位置改为 `SM2_ALERT`，默认仍是 `<上一级>/ext/ALERT`；`dat1lib` 原先在模块顶层导入，改为 `alert()` 里按需导入（`load_toc()`、`asset_id()` 调用），找不到时报错并给出仓库地址；
  - `sm2_karin_geo.py`：源 VRM 的默认路径原先指向项目外的私有模型目录，改为 `SM2_VRM`；`--vrm` 和 `SM2_VRM` 都没有时用 argparse 报错；新增 `vrm_path()` 给其他脚本用；`WORK` 与 `sm2_common.py` 同样读 `SM2_WORK`（`build_sig*`、`native/` 经它定位）；
  - `sm2_batch.py`：`--author` 默认值原先是项目作者名，改为空；游戏目录改用 `game_dir()`，源 VRM 改用 `vrm_path()`；
  - `sm2_face.py`、`sm2_pose_check.py`：源 VRM 改用 `vrm_path()`；`sm2_pose_check.py` 的 `scipy.spatial.cKDTree` 改为在用到的地方导入；
  - `sm2_assets.py`：`etcpak` 改为在 `compress()` 里导入；
  - `i30_actor.py`、`i30_joints.py`：`dat1lib.crc32` / `crc64` 原先在模块顶层导入，改为在 `crc32()`、`crc64()`、`joint_hash()` 里导入；加进 `sys.path` 的 ALERT 目录先看 `SM2_ALERT`，默认不变；
  - `sm2_build_model.py`：`set_materials()` 原先把 `<WORK>/ext/ALERT` 加进 `sys.path`，改为 `sm2_common.ALERT`（`SM2_WORK` 改了也不影响 ALERT 的位置）；
  - `sm2_index.py`、`suit_models.py`、`survey_targets.py`：没有参数，一导入就干活；补了只带说明的 argparse（在任何读取之前），`sm2_index.py` 的 `dagstr` 改用 `game_dir()`；
  - `test_actor_roundtrip.py`（`'--all' in sys.argv`）、`test_dyn_roundtrip.py`、`survey_dyn2.py`（`sys.argv[1:]` 作模型名）、`test_dyn_model.py`（`sys.argv[1]` 作 stage）：改用 argparse，参数不变；
  - `sm2_install.py`：只把用法里的示例游戏目录换成 `<game folder>`；
  - 换行：上面 17 个里有 12 个原文件是 CRLF，一并改为 LF；另有 14 个文件只把 CRLF 改为 LF：`sm2_dat1.py`、`crc64_table.py`、`i30_model.py`、`i30_build.py`、`i30_writer.py`、`i30_texture.py`、`i30_dynamics.py`、`i30_actor_edit.py`、`sm2_fit.py`、`sm2_dyn.py`、`sm2_prop_test.py`、`sm2_head_carrier.py`、`sm2_verify_stage.py`、`sm2_preview.py`。

  其余 7 个文件与原文件逐字节相同：`sm2_stage.py`、`bcdec.py`、`sm2_find.py`、`sm2_extract.py`、`vrm.py`、`render.py`、`sm2_verify_face.py`。处理逻辑没有改。
- **`--help`：** 38 个脚本在没有 ALERT、没设任何 `SM2_*` 时都以 0 退出；再把 scipy、etcpak、`dat1lib` 屏蔽掉（只剩标准库、numpy、Pillow）也都以 0 退出。只导入标准库的 14 个：`sm2_common`、`sm2_dat1`、`crc64_table`、`sm2_stage`、`sm2_install`、`i30_build`、`i30_texture`、`i30_actor`、`i30_actor_edit`、`sm2_index`、`sm2_find`、`sm2_extract`、`suit_models`、`test_actor_roundtrip`。纯库模块没有加命令行，和其他便携包一样，运行时只做定义、以 0 退出。
- **等价性验证（离线，本机）：**
  - **条件：** Windows 10 19044；Python 3.14.0、numpy 2.5.2、Pillow 12.3.0、scipy 1.18.0、etcpak 0.9.15；本机游戏（启动器 v1.130.1.0，toc SHA-1 `318f4345f3a1`）；ALERT `bc90ed9b` 的 `dat1lib`；源 VRM（SHA-256 `8f930404…2d87`）；项目的 `asset_index.json`、`targets.json`、`suit_models.json`、`masked_suits.json` 的副本。原脚本复制到临时目录运行（它的工作目录和 ALERT 也在临时目录里），本包脚本经 `SM2_*` 指向另一个临时工作目录，项目目录只读；
  - **安装器：** 两边各在原版 toc 的副本上装 v2 发行包（124 个资产）：装后 toc SHA-1 都是 `69ce1233d4fe`（与项目记录的远端实测一致），`--report` 逐字节相同，`status` 输出相同，卸载后都回到 `318f4345f3a1`；
  - **读游戏：** `sm2_index.py` 重建的 `asset_index.json` 与原脚本的、项目里的逐字节相同（420,968 个名字，解出 420,966 个）；`suit_models.py`、`survey_targets.py` 写出的 `suit_models.json`、`targets.json` 也与两者逐字节相同（108 个目标，7 种骨架签名）。`test_actor_roundtrip.py`（5 个英雄 actor，bad 0）、`test_dyn_roundtrip.py`、`sm2_find.py`、`sm2_extract.py` 的输出与原脚本相同，解出的 `hero_spiderman_advanced.model` 与项目 `native/` 里的逐字节相同。`test_dyn_roundtrip.py` 两边都报 `total mismatching words 17`，全部来自 `npc_lidemon_antivenom_34x.model` 的 T6 表，其余 15 个模型为 0：这是原脚本在这个 build 上的现状，不是迁移造成的；
  - **对 v2 发行包的离线验收：** `test_dyn_model.py`（110 个模型）、`sm2_verify_stage.py`（108 个）、`sm2_verify_face.py`（111 个）的输出与原脚本逐行相同，都是 0 bad；
  - **构建（只重跑一个目标模型 `hero_spiderman_advanced`）：** `sm2_batch.py` 不带参数、带 `--dyn`、带 `--dyn --face` 三种，`.stage` 的 11 个资产两边逐字节相同，`.stage.json` 报告相同，`info.json` 只差作者（原脚本写项目作者名，本包默认空）；三种骨架签名的拟合 `karin_geo.npz` 逐数组相同。以 `--dyn --face` 的包为 base，`sm2_prop_test.py`（完整包 13 个资产、`--delta` 2 个）和 `sm2_head_carrier.py --suit <advanced> --never-cull --joint-bsphere 1.0 --map-body --blank-prop`（完整包 17 个、`--delta` 7 个）两边逐资产相同，载体包的 `test_dyn_model.py` 输出相同；
  - **其他：** `sm2_karin_geo.py --target peter` 的 `karin_geo.npz` / `.json`、`sm2_build_model.py --target peter` 的 `.model`、`sm2_face.py --family peter --render` 的 `face.npz` 和 `poses.png`、`sm2_pose_check.py` 的输出和 PNG（蹲 1.8%、栖 2.1%、坐 0.7%、跨步 0%，与项目 T9 记录一致）、`sm2_preview.py` 的 PNG 都与原脚本逐字节相同；
  - **没有重跑的部分：** 全量 v1 / v2 构建（108 个模型、91 套战衣去链）没有用本包重跑；`test_actor_roundtrip.py --all`、`sm2_head_carrier.py --masked`、`--cat-actor`、`sm2_batch.py --dyn-base` / `--dyn-ab` 没有跑。
- **合成数据测试：** `MarvelsSpiderMan2Tools` 共 3 项，只用标准库，不需要游戏、ALERT 或模型：
  - `.stage`：`crc64_path()` 与独立实现的位运算 CRC-64（反射 ECMA-182，初值为多项式，`>> 2 | 1 << 63`）一致，含大小写、反斜杠、重复分隔符和非 ASCII 路径；两套默认战衣的路径算出游戏 toc 里的 id `A6D53AE572ACCADC`、`841353C2023080D8`；写入读回保留顺序、span、id、资产头、贴图 meta 和数据，STG 包装的偏移和 16 字节对齐；按路径命名的条目、非 span 目录；
  - 安装器：合成 toc（两个 span、两个归档、贴图 meta、变长资产头），未改动的 toc 重存逐字节相同；一个包同时覆盖等长资产头原地改写、新资产插入两个 span、更长资产头追加、贴图 meta 替换和有序插入；旧的 `mod7` 被删；`status`；两个包按顺序成为 mod0、mod1 且后者生效；再装一次从 `toc.BAK` 重来、结果与第一次相同；卸载还原 toc 并删掉 `mod*`；
  - `.actor`：手写的序列化对象（bool、u32、f32、数组、空数组、id64、带存储哈希的字符串、嵌套对象、null）经 `Writer` → `Reader` 往返，值不对齐打包；坏的对象头报错；组件容器（字符串块、ActorPriusBuilt、16 字节对齐的组件数据、无数据组件）保存、解析、再保存逐字节相同；全程没有导入 `dat1lib`。

  `--help` 测试覆盖 `scripts/` 下全部 38 个脚本；没装 numpy 或 Pillow 时，除上面 14 个以外的脚本跳过。
- **未验证：**
  - 便携版没有装进游戏测试；实机结论来自项目用原脚本构建的 v1、v2；
  - 其他游戏版本、ALERT 的其他提交、非 Windows 系统；
  - 新模型的案例常量。

## 2026-10-13：新增幻兽帕鲁便携包

- **迁入内容：** 27 个文件，放在 `portable-kits/palworld/`。
  - `scripts/` 下 1 个 Python 命令 `gen_ue_config.py` 和调参文件 `physics_tune.json`；
  - `scripts/blender/` 下 7 个 Blender 脚本：`build_pal.py`、`palcommon.py`、`kawaii_sim.py`、`probe_run_pose.py`、`render_preview.py`、`render_views.py`、`render_keys.py`；
  - `scripts/ue/` 下 2 个 UE 编辑器 Python：`ue_import.py`、`ue_build_abp.py`；
  - `tools/` 下 5 个 PowerShell：`palx_run.ps1`、`run_py.ps1`、`cook_and_pack.ps1`、`verify_paks.ps1`、`build_plugin.ps1`；
  - `palexport/` 下 PalExport 的 `Program.cs`、`PalExport.csproj`；`ue/PalModTools/` 下编辑器插件的 5 个文件（`.uplugin`、`Build.cs`、`PalGraphLib.h`、`PalGraphLib.cpp`、`PalModToolsModule.cpp`）；`ue/PalProj/` 下内容工程模板（`Pal.uproject` 和 3 个 `Config/*.ini`）；
  - 来源是本机工具目录 `ModTools/Palworld/`（`scripts/`、`ue/`、`ue/project/`、`src/PalExport/`），`palx_run.ps1` 来自构建机的 `PalModding/tools/`。构建机上的 UE 脚本副本与本机的逐字节相同。PROVENANCE 每个文件一行，记录原始和公开版的 SHA-256；
  - 新增 `README.md`、`toolchain.json`、`requirements.txt`（numpy，只给 `gen_ue_config.py` 用）。公共层 `modkit.py` 的游戏列表加上 `palworld`，导出器和导出测试因此覆盖它。
- **没有迁入：**
  - KawaiiPhysics 1.17.1 插件源码（pafuhana1213/KawaiiPhysics，MIT，第三方）：README 说明自己取来放进工程的 `Plugins\KawaiiPhysics\`；
  - `probe_frames.py`：一次性探针，打印原版和 Karin 骨架的骨朝向，用来定骨架合同；没有参数，结论已在 `build_pal.py` 的注释和技术合同里；
  - `ue_debug_mat.py`：一次性探针，查占位母材质和 MI 的参数；查到的「UE 5.1 设贴图参数成功也返回 False」已写在 `ue_import.py` 的注释里；
  - 源模型、参考 mod、游戏数据、提取出的 JSON / uemodel / ueanim、usmap、Oodle DLL、生成的贴图、FBX、blend、pak 和发行包；项目构建目录里的 `ue_config.json`、`physics_r4.json`（后者含本机路径）。
- **便携改动**在 13 个文件：
  - `blender/palcommon.py`：UEFormat 插件目录、PalExport 缓存目录和源 VRM 原先写死，改为环境变量 `PAL_BLENDER_ADDONS`、`PAL_CACHE`（脚本在后面拼上 `Pal\Content\Pal\Model\Character\Player`）、`PAL_SOURCE_VRM`；没设时路径里是 `<PAL_…>`，载入会报找不到文件；
  - `blender/kawaii_sim.py`：默认参数文件原先是脚本同目录的 `physics_tune.json`，改为本包的 `scripts/physics_tune.json`（脚本的上一级目录，绝对路径）；CRLF 改为 LF；
  - `gen_ue_config.py`：改用 argparse，两个位置参数不变（`--help` 在导入 numpy 之前处理）；
  - `ue/ue_import.py`、`ue/ue_build_abp.py`：只改了用法注释里的构建机路径（换成 `<PAL_WORK_ROOT>`，并补一行 `run_py.ps1` 的写法）；CRLF 改为 LF；
  - `tools/palx_run.ps1`：PalExport、游戏 pak 目录、usmap、Oodle DLL 和输出目录原先写死，改为 `-Exe`、`PAL_GAME_DIR`、`PAL_USMAP`、`PAL_OODLE`、`PAL_WORK_ROOT`（都有同名参数；后三个的默认值在 `<PAL_WORK_ROOT>\tools\`）；
  - `tools/verify_paks.ps1`：同上，pak 目录和输出目录改为 `<PAL_WORK_ROOT>\out\<tag>`、`<PAL_WORK_ROOT>\extract\verify_<tag>`；
  - `tools/run_py.ps1`、`tools/build_plugin.ps1`：UE 安装和工程目录改为 `PAL_UE_ROOT`、`PAL_PROJECT`（默认 `<PAL_WORK_ROOT>\UEProject\Pal`）；`build_plugin.ps1` 的编译器开关改为 `-Compiler`，默认仍是 `VisualStudio2019`；
  - `tools/cook_and_pack.ps1`：UE、工程、repak、工作目录和 `~mods` 改为 `PAL_UE_ROOT`、`PAL_PROJECT`、`-Repak`、`PAL_WORK_ROOT`、`PAL_GAME_DIR`；工作目录和工程目录先解析成完整路径（暂存时按长度截取相对路径）；`-Install` 缺游戏目录时在动手前报错；注释里的构建机名删掉；
  - 位置参数改用显式 `Position`，新参数只能按名字给；
  - 只把 CRLF 改为 LF：`physics_tune.json`、`blender/build_pal.py`、插件的 `PalGraphLib.cpp`。

  其余 14 个文件与原文件逐字节相同：`probe_run_pose.py`、`render_preview.py`、`render_views.py`、`render_keys.py`、`Program.cs`、`PalExport.csproj`、插件的 `.uplugin`、`Build.cs`、`PalGraphLib.h`、`PalModToolsModule.cpp`，`Pal.uproject` 和 3 个 `.ini`。处理逻辑没有改。
- **等价性验证（离线，本机）：**
  - **条件：** Windows 10 19044；项目的私有 Blender 4.2.23 LTS（UEFormat 在 `addons_core` 里）；Python 3.14.0、numpy 2.5.2、Pillow 12.3.0；项目缓存的 OldCloth001 `.uemodel`（经 `PAL_CACHE`）、源 VRM（经 `PAL_SOURCE_VRM`）、冲刺和慢跑 `.ueanim`、项目的玩家资产列表。项目 r3 构建目录（`build.blend`、`physics.json`、`report.json`、`physics_r4.json`）先复制到临时目录，原脚本也复制到临时目录运行，源目录只读；
  - **`kawaii_sim.py`：** 在 r3 的副本上用冲刺动画、本包的 `physics_tune.json`、`export=` 运行（项目原用法，不加 `--factory-startup`）：导出文件除 `tune` 那一行外与项目的 `physics_r4.json` 逐字节相同，`groups` 与原脚本这次导出的也相同。同一输入下原脚本和本包脚本的 `NODE`、`skirt verts`、`RESULT`、`FLARE` 行相同：冲刺 `mean skirt verts inside thigh 13.8 (>1cm 11.3), worst 16 verts depth 5.95 cm at step 83, max flare front 65.0 back 56.4 deg`（与项目记录的 r4 值 13.8 一致）；慢跑动画（同样默认 700 cm/s）两边都是 `8.6 (>1cm 5.7)`、最差 8 个顶点 5.94 cm。本包脚本加 `--factory-startup` 再跑冲刺，导出文件与不加时逐字节相同，`RESULT` 相同；
  - **`build_pal.py`：** 原脚本和本包脚本各构建一次（`--factory-startup`，默认缩放 1.30）：`physics.json`、`report.json` 和 5 张贴图逐字节相同，也与项目 r3 的相同。FBX 和 `build.blend` 的字节因输出路径而不同；在 Blender 里导入三个 FBX、打开 blend，逐对象比较网格顶点、面、角法线、UV、材质槽、顶点组权重、形态键、修改器和骨架（头、尾、矩阵、父骨），原脚本、本包脚本和项目 r3 三者相同（189 根骨，身体 32 232 个顶点，头 3 375 个顶点和 12 个形态键含 Basis，隐藏网格 3 个顶点）；
  - **`gen_ue_config.py`：** 用项目的玩家资产列表，原脚本和本包脚本的 `ue_config.json` 和 6 张辅助贴图逐字节相同，也与项目 r3 的相同（26 个女性脸型、37 个发型）；
  - **PowerShell 工具：** 5 个都过了 PowerShell 7 解析器；缺环境变量时都在动手前报错。用假的 PalExport（回显参数的 `.cmd`）和假的 repak（把暂存目录列进 pak 文件）在带空格的临时路径里跑了 `palx_run.ps1`、`verify_paks.ps1`、`cook_and_pack.ps1 -SkipCook -Install`：参数顺序和默认路径与原脚本相同，三个包只收白名单内的文件（占位骨架、`ALI_HumanCloth`、其他 MI、男性脸型被排除），装进 `<游戏目录>\Pal\Content\Paks\~mods`；
  - **没有重跑的部分：** UE 一侧（`run_py.ps1`、`build_plugin.ps1`、真实的 cook 和 repak、`scripts/ue/*.py`）、插件（C++）和 PalExport（C#）要用构建机上的 UE 5.1 和游戏，本次只核对了改动；`render_preview.py`、`render_views.py`、`render_keys.py`、`probe_run_pose.py` 与原文件逐字节相同，没有重跑，`kawaii_sim.py` 的 `render=1` 分支也没有跑。
- **合成数据测试：** `PalworldTools` 共 5 项：
  - `kawaii_sim.py` 的 `merged()` 和 `curve()`（从源码里单独编译，脚本本身要 bpy）：参数只覆盖给出的键、未知键忽略、显式胶囊替换派生胶囊、按骨改半径、附加胶囊、输入不被修改、组缺参数时报 `KeyError`；曲线的线性插值、两端截断、没有曲线时为 1；
  - `physics_tune.json`：组名与 `build_pal.py` 写进 `physics.json` 的 7 个组相同；每个键都是 `merged()` 认的；取值范围、曲线递增、胶囊字段；合并后的数值键都是 `ue_build_abp.py` 读的；
  - `gen_ue_config.py`：合成资产列表（混入 `.uexp`、男性脸型、MI、带后缀的发型、PalExport 的 stderr 行）得到排好序的脸型和发型路径；辅助贴图的尺寸和颜色、材质实例引用的贴图都已定义、插槽偏移；缺参数时失败；
  - PowerShell 工具（要 pwsh 7 和 Windows，否则跳过）：解析、缺环境变量时报出变量名、`palx_run.ps1` / `verify_paks.ps1` 的参数转发和默认路径、`cook_and_pack.ps1` 的白名单分包和安装、`-Install` 缺游戏目录时不写文件；
  - PROVENANCE：每个迁入文件一行，哈希和字节数对得上，修改标记与哈希一致，与 `toolchain.json` 的 `bundled_scripts` 相同；本包文件里没有盘符路径和用户目录、只有 LF、不含 KawaiiPhysics 源码。

  `--help` 测试覆盖 `scripts/gen_ue_config.py`（在导入 numpy 之前退出）；`gen_ue_config.py` 的测试缺 numpy 或 Pillow 时跳过。
- **未验证：**
  - 便携版没有装进游戏测试，也没有在构建机上跑 UE 一侧；实机结论来自项目用原脚本构建的 r3 / r4；
  - 测试套件对 Blender 脚本只做语法检查和上面两个函数，UE 脚本只做语法检查；
  - 非 Windows 系统、其他 Blender / UE / 游戏版本、以扩展方式安装的 UEFormat；
  - 新模型的案例常量。

## 2026-10-13：新增 Sifu 便携包

- **迁入内容：** 37 个文件，放在 `portable-kits/sifu/`。
  - `scripts/` 下 4 个 Python 命令：`dyn_tuning.py`、`make_textures.py`、`package_release.py`、`frames_to_gif.py`；
  - `scripts/blender/` 下 14 个 Blender 脚本：`build_karin.py`、`source_prep.py`、`profiles.py`、`sifu_common.py`、`face_stage.py`、`cloth_stage.py`、`dyn_stage.py`、`torso_weights.py`、`bake_ao.py`、`preview_model.py`、`pose_preview.py`、`preview_face.py`、`skirt_sim.py`、`make_skeleton_fbx.py`；
  - `scripts/ue/` 下 4 个 UE 编辑器 Python：`ue_build_mesh.py`、`ue_import_skeleton.py`、`verify_mesh.py`、`scripts_smoke.py`；
  - `tools/` 下 5 个 PowerShell：`sfx_run.ps1`、`ue_run.ps1`、`cook_pak.ps1`、`build_plugin.ps1`、`burst.ps1`；
  - `sifuexport/` 下 SifuExport 的 `Program.cs`、`SifuExport.csproj`；`ue/SifuModTools/` 下编辑器插件的 4 个文件（`.uplugin`、`Build.cs`、`.h`、`.cpp`）；`ue/SifuProj/` 下内容工程模板（`Sifu.uproject` 和 3 个 `Config/*.ini`）；
  - 来源是项目的 `Karin_Original_W/Scripts/`（Blender 脚本、Python 命令、两个 UE 脚本）和本机工具目录 `ModTools/SIFU/`（PowerShell、抓屏、SifuExport、插件、工程模板、`verify_mesh.py`、`scripts_smoke.py`）。两处的副本与构建机上的相同。PROVENANCE 每个文件一行，记录原始和公开版的 SHA-256；
  - 新增 `README.md`、`toolchain.json`、`requirements.txt`（numpy，只给 `make_textures.py` 用）。仓库检查允许的文件类型加上了 `.h`、`.cpp`、`.uplugin`、`.uproject`、`.ini`。
- **没有迁入：**
  - 一次性探针：`analyze_weights.py`、`face_probe.py`、`inspect_sources.py`、`measure_w_head.py`、`pdbgrep*.py`、构建目录里的 `fbxcheck.py`、`normcheck.py`、`uvcheck.py`、`vcol.py`、`tagwalk.py`；
  - `patch_rigidbody.py`：给插件源码追加 `SetupRigidBodyPostProcess` 的一次性脚本，改动已在随包的插件源码里；
  - `preview.py`、`preview_proxies.py`：早期快速预览，已被 `preview_model.py`、`pose_preview.py` 取代；
  - `build_model.sh`、`ship_model.sh`：整理成 README 里的分步命令。它们写死了本机目录和 ssh 别名，`.sh` 也不是仓库允许的类型；
  - 游戏 AES 密钥（项目日志和本机 `sfx_run.ps1` 里有）；
  - 源模型、游戏数据、提取出的 JSON / glTF / 动画、生成的贴图、FBX、blend、pak 和发行包；各 `build_cfg.json` 和 Original 手写的 `ue_build.json`（含绝对路径）。
- **便携改动**在 17 个文件：
  - `blender/profiles.py`：源模型根目录原先写死，改为环境变量 `SIFU_MODELS_DIR`；没设时路径里是 `<SIFU_MODELS_DIR>`，载入会报找不到文件；
  - `blender/sifu_common.py`：`Base_skeleton` JSON 的默认路径原先写死，改为环境变量 `SIFU_BASE_SKEL`；build_cfg 的 `base_skel` 照旧优先，两个都没有时报错；
  - `blender/build_karin.py`：把上一级目录加进 `sys.path`，因为 `dyn_tuning.py` 放在 `scripts/` 下；
  - `blender/skirt_sim.py`：`pose_preview.py` 和 `sifu_common.py` 原先从写死的项目目录读，改为脚本自己所在的目录（换成正斜杠，因为它被拼进 `exec` 的字符串字面量）；
  - `make_textures.py`：改用 argparse，位置参数不变；平法线 `T_Karin_Flat_N.png`（64×64，RGB 128/128/255）和黑遮罩 `T_Karin_Black.png`（16×16）原先从本机目录复制，现在默认直接生成，字节与原文件相同；`--flat-dir` 保留复制的做法；`profiles.py` 从 `scripts/blender/` 导入；
  - `package_release.py`：pak 来源目录和发行目录原先写死（后者按脚本位置推算），改为必填的 `--out-root`、`--release-dir`；安装说明里的示例游戏目录原先写死，改为 `--game-dir`（默认 `SIFU_GAME_DIR`，都没有时是占位文字）；profile 只接受有发行文字的四个变体，原先 `karin_original` 会在中途报 `KeyError`；
  - `dyn_tuning.py`、`frames_to_gif.py`：改用 argparse，参数不变；
  - `ue/ue_build_mesh.py`、`ue/ue_import_skeleton.py`、`ue/verify_mesh.py`：`py_args.json` 原先是写死的路径，改为读环境变量 `SIFU_PY_ARGS`（由 `ue_run.ps1` 设置）；
  - `ue/scripts_smoke.py`：输出路径原先写死，改为 `py_args.json` 里的第一个参数；
  - `tools/sfx_run.ps1`：删掉写死的 AES 密钥，改从 `SIFU_AES` / `-Aes` 读，没有就报错；SifuExport、游戏和缓存目录改为 `-Exe`、`SIFU_GAME_DIR`、`SIFU_WORK_ROOT`；
  - `tools/ue_run.ps1`、`tools/cook_pak.ps1`、`tools/build_plugin.ps1`：UE 安装、工程、工作目录和游戏目录改为 `SIFU_UE_ROOT`、`SIFU_PROJECT`、`SIFU_WORK_ROOT`、`SIFU_GAME_DIR`（都有同名参数）。位置参数改用显式 `Position`，新参数只能按名字给；`cook_pak.ps1` 把工程目录解析成完整路径后再截取相对路径；`build_plugin.ps1` 会先建日志目录；
  - `tools/burst.ps1`：抓图目录原先写死，改为 `-Dir`，默认 `<SIFU_WORK_ROOT>\cap`；
  - 只把 CRLF 改为 LF：7 个 Blender 脚本（`face_stage.py`、`cloth_stage.py`、`dyn_stage.py`、`torso_weights.py`、`bake_ao.py`、`pose_preview.py`、`make_skeleton_fbx.py`），`Program.cs`，以及插件的 `Build.cs`、`.h`、`.cpp`。

  其余 9 个文件与原文件逐字节相同：`source_prep.py`、`preview_model.py`、`preview_face.py`、`SifuExport.csproj`、`.uplugin`、`Sifu.uproject` 和 3 个 `.ini`。处理逻辑没有改。
- **等价性验证（离线，本机）：**
  - **条件：** Windows 10 19044；Blender 4.2.23 LTS（`-b --factory-startup`）；Python 3.14.0、numpy 2.5.2、Pillow 12.3.0；项目缓存的 W 骨架 JSON、W glTF、面部姿势 JSON 和 `Base_skeleton` JSON（经 `SIFU_BASE_SKEL`）；源模型经 `SIFU_MODELS_DIR`；输出写到临时目录，build_cfg 只改了 4 个输出路径。参照是项目用同一版脚本做的构建：Original 为 `work/regress/`（其 `cloth.json` 与 v6 发行时的相同），变体为 `work/y/`；
  - **`karin_original`：** `cloth.json` 与 v6 逐字节相同；`build_report.json` 除 `config` 里 4 个输出路径外相同；构建日志除时间和 FBX 路径外相同；
  - **`y`（用到 `drop_meshes`、`hang`、`mesh_materials`）：** `cloth.json` 逐字节相同；`build_report.json` 除 4 个输出路径外相同（`source_prep.src` 也相同，因为 `SIFU_MODELS_DIR` 给的是同一个目录）；
  - **FBX：** 两个 profile 的字节都不同。按 FBX 二进制节点树解码比较（数组解压后比较）：Blender 每次运行随机生成对象 ID（来自 Python 的随机化 `hash()`），把 ID 换成对象名后，Original 的 41 050 个节点（13 029 个数组）和 `y` 的 122 823 个节点（42 547 个数组）只差创建时间戳、SceneInfo 里的源 `.blend` 路径，以及 Original 的贴图 / 视频节点里的输出目录。几何、法线、UV、顶点色、权重、绑定姿势和连接都相同；
  - **`.blend`：** 字节不同（Blender 文件里有内存指针和路径）。在 Blender 里逐数据块比较：网格的顶点坐标、面、UV、颜色和其他属性、材质、形状键，物体的父子关系、变换和修改器，顶点组权重，骨架的骨（头、尾、矩阵、父骨）全部相同（Original 11 个网格 34 398 个顶点，`y` 35 个网格 192 793 个顶点）；
  - **`y` 的贴图：** 本包的 `bake_ao.py` 在本包构建的 blend 上烘焙，5 张 `AO_<页>.png` 与项目的逐字节相同；接着 `make_textures.py` 写出的 13 张 PNG 和 `ue_build.json`（第三个参数给项目当时用的构建机目录）都与项目的逐字节相同。单独用项目的 AO 跑 `make_textures.py`，结果也逐字节相同；
  - **`package_release.py`：** 用项目取回的 `y` pak 重做 v1（`--game-dir` 给项目说明里的目录），发行文件夹里的 pak、sig、`安装说明.txt` 与发行包逐字节相同；zip 的成员名、顺序和内容相同，zip 文件本身只差 `安装说明.txt` 成员的修改时间（脚本运行时写的）；
  - **没有重跑的部分：** UE 一侧（`ue_run.ps1`、`cook_pak.ps1`、`build_plugin.ps1`、`sfx_run.ps1`、`burst.ps1`、`scripts/ue/*.py`）、插件（C++）和 SifuExport（C#）要用构建机上的 UE 4.26 和游戏，本次只核对了改动：PowerShell 脚本过了 PowerShell 解析器，缺环境变量时 4 个工具都在动手前报错；`frames_to_gif.py`、`skirt_sim.py`、`preview_model.py`、`pose_preview.py`、`preview_face.py`、`make_skeleton_fbx.py` 没有在真实数据上重跑。
- **合成数据测试：** `SifuTools` 共 4 项：
  - `dyn_tuning.py`：两条链加两个运动学碰撞体。每个关节的驱动刚度与阻尼与按平行轴定理独立算的子链惯量一致，驱动作用在 I_com 上时给出的正好是设定的模态频率；没有 `tune` 的链用模块里的 `CHAINS`；碰撞过滤只放行链自己的碰撞体，静止时重叠的对加入禁用表，链与链之间全部禁用；命令行就地改写 `cloth.json`，其他段落不变；
  - `make_textures.py`：合成图集页和 AO 页（profile `y`），检查平法线和黑遮罩、BaseColor 的 alpha（皮肤 255、布料 0）、ComboMap 四个通道（各 kind 的粗糙度、金属 0、按强度换算的 AO、alpha 230 / 255）、`ue_build.json` 的路径、父材质和贴图引用；`--flat-dir`；没设 `SIFU_MODELS_DIR` 时失败；
  - `package_release.py`：发行文件夹、CRLF 说明文字、MD5、zip 成员；示例目录取 `--game-dir`、`SIFU_GAME_DIR` 或占位文字；`karin_original` 和缺 `--release-dir` 时报错且不写文件；
  - `frames_to_gif.py`：帧数、帧时长（GIF 以 10 ms 为单位）、默认 6 列的联系表、裁剪和列数参数。

  `--help` 测试覆盖 `scripts/` 下全部 4 个脚本；`make_textures.py` 缺 numpy 或 Pillow、`frames_to_gif.py` 缺 Pillow 时跳过。
- **未验证：**
  - 便携版没有装进游戏测试，也没有在构建机上跑 UE 一侧；实机结论来自项目用原脚本构建的发行包（Original v6 由用户在游戏里确认，四个变体只做了离线检查）；
  - `opt`、`pt`、`umb` 三个变体的构建没有用本包重跑；
  - 测试套件对 Blender 和 UE 脚本只做语法检查；
  - 非 Windows 系统、其他 Blender / UE / 游戏版本下的结果；
  - 新模型的案例常量。

## 2026-10-12：浪人崛起（KT 引擎格式工具与腿部权重）

- **迁入内容：** 5 个 Python 文件，放在 `portable-kits/rise-of-the-ronin/scripts/`。来源是项目的 `tools/`、`original/tools/` 和 `repair/20261004/tools/`，按职责合并改写（每个来源各占 PROVENANCE 一行）：
  - `g1m_tool.py`：合并 `lib_g1m_sections.py`、`collapse_hidden_triangles.py`、`ko_hide_face.py`，以及 `ko_common.py` 的块读写；
  - `g1t_tool.py`：来自 `g1t_layout.py`，以及 `ko_fix_textures.py` 的常量块；
  - `ktdata.py`：来自 `build_current_g1t_usage_map.py`、`dump_ktid_slots.py`；
  - `leg_weights.py`：来自 `ko_leg_ref.py`、`ko_conform.py` 的 `leg_distributions`、`pico_legs.py`、`pico_legs_check.py`；
  - `shader_dump.py`：来自 `read_skin_shader.py`。
- **通用化改动：**
  - 去掉本机路径、模板路径和 Karin 专用的文件表，改为命令行参数；所有写文件的命令都拒绝覆盖。
  - G1M 解析不再依赖 gust_stuff 和 pyquaternion（只用标准库）。调色板骨号到骨架存储序号的映射改为显式处理：项目脚本按 gust 的命名间接用对了，但没有写明。
  - 腿部权重改为原地写入 G1M（只改混合字节、调色板、MM1G 和 FM1G 计数），不再经过 gust 导出 / 导入。原版参考也直接从 G1M 读出。
  - G1T 常量填充增加 R32_FLOAT / RGBA8；读回时能识别 BC1 / BC4 / BC5 / BC7（mode 6）/ 浮点的单一颜色。
  - 共用贴图审计（`ktdata.py usage`）把项目里的一次性扫描脚本做成了命令。
- **等价性验证：**
  - **条件：** Python 3.14.0、numpy 2.5.2、scipy 1.18.0。输入是项目留下的 Picodra 20260916a 模板、三个原版腿部模型、10-04 发布的成品，以及原版 G1T。
  - **腿部参考：** 59097 个参考顶点，作为集合与项目的 `leg_ref.npz` 逐值相同。
  - **651 sub6：** 原地重做后，每个顶点的有效权重、调色板和追加的 12 个绑定都与发布的 20261004a 相同。回读得到静止姿态偏移 0.00198、弯脚踝时脚的平均位移 0 → 5.53。
  - **8DC sub7：** 有 2 个顶点相差一个 2^-11 量化步长，原因是骨架世界矩阵的浮点误差；调色板和 8 个绑定相同；静止姿态偏移 0.0065。
  - **贴图：** 5 张常量修复与发布包逐字节相同。对原版 `0x1E76FD2D` 写入 0.0，得到的正是上游 mod 的错误版本（只差 +0x3A / +0x3B）。85 张原版 G1T 全部能解析，其中 76 张是 tile 存储，抽查 3 张 tile 往返一致。
  - **G1H：** 能列出捏脸头 G1H 的 41 个嵌入模型；在 hidehead 包里，最大模型的 38 个子网格全部识别为已隐藏。
- **合成数据测试：** `RiseOfTheRoninTools` 共 5 项：
  - G1M 解析、隐藏（含 G1H 容器）、追加绑定；
  - G1T tile 往返、DDS 还原 tile、各格式常量填充与读回、比较与 mip；
  - 资源表的存储和两种 zlib 分块、两种 RDB 尾部、kidsobjdb、KTID、槽表与共用贴图审计；
  - shader 包拆分；
  - 腿部：从「膝下全绑膝骨」重分后，弯脚骨时脚会跟着动；缺失的骨被追加原生绑定；量化后权重之和为 1。
- **未验证：**
  - 便携版的 `ktdata.py` 没有在游戏数据上重跑：整理时游戏未安装。它沿用的解析逻辑在项目里用真实数据跑过。
  - 20261004a 的成品本身没有实机测试。
  - 从源模型构建的脚本没有迁入。

## 2026-10-12：新增龙之信条2便携包

- **迁入内容：** 32 个文件，放在 `portable-kits/dragons-dogma-2/`。
  - `scripts/` 下 7 个 Python：`devcmd.py`、`make_chain_spec.py`、`patch_mesh_header.py`、`build_karin_textures.py`、`make_original_lua.py`、`clsp_dump.py`、`clear_cet_flag.py`；
  - `scripts/blender/` 下 3 个 Blender 脚本：`build_karin_body.py`、`re_common.py`、`prepare_karin_original.py`；
  - `reframework/` 下 4 个 Lua：`karin_replacer.lua`、`karin_dev.lua`、`karin_probe_dump.lua`、`karin_pipeline_probe.lua`；
  - `devqueries/` 下 12 个 Lua 查询；
  - `dd2tool/` 下 DD2Tool 的 5 个 C# 源文件和 `DD2Tool.csproj`；
  - 来源是项目的 `Scripts/`、`Scripts/blender/`、`Scripts/reframework/`、`Scripts/devqueries/` 和 `Tools/src/DD2Tool/`。PROVENANCE 每个文件一行，记录原始和公开版的 SHA-256；
  - 新增 `requirements.txt`（numpy，只给贴图脚本用）。仓库检查允许的文件类型加上了 `.lua`、`.cs`、`.csproj`。
- **没有迁入：**
  - `karin_replacer_original.lua`：由 `make_original_lua.py` 生成；
  - 驱动游戏窗口的脚本：`dd2_reload.py`、`dd2_reset_scripts.py`、`ui_find.py`、`ref_menu_find.py`、`fglock.py`、AHK 和 `.sh`。它们依赖本机的窗口布局、截图模板和前台锁；
  - `build_all.sh`：整理成 README 里的分步命令；
  - `probe_karin.py`、`probe_body_roundtrip.py`：一次性诊断；
  - 生成的规格 JSON（含绝对路径）、发行 PAK、RE-Engine-Lib 源码、游戏和模型数据。
- **便携改动**在 10 个文件：
  - `devcmd.py`：游戏目录原先写死，改为 `--game-dir` 或环境变量 `DD2_GAME_DIR`。没给目录、或目录下没有 `reframework/` 时报错，不创建文件；
  - `make_chain_spec.py`：
    - 原生链模板原先在项目的 `work/native`，改为 `--native-dir` 或 `DD2_NATIVE_DIR`，规格里仍写解析后的绝对路径；
    - 骨骼表原先按 profile 写死在项目的 `work/` 下，改为 `--inventory`；
    - 手写的参数解析改为 argparse，位置参数不变，`--profile=original` 的写法照样可用；
  - `build_karin_textures.py`：源图（PicodraTech 原先是绝对路径）、临时目录和清单、原生模板贴图、texconv、DD2Tool 原先都写死，改为 `--src`、`--work-dir`、`--manifest`、`--native-dir`、`--texconv`、`--dd2tool`（后三个也可用环境变量）；
  - `make_original_lua.py`：输入默认为本包的 `reframework/karin_replacer.lua`，输出改为必填的 `--out`，`--check` 改用 argparse。生成的文本没有变；
  - `clsp_dump.py`：改用 argparse，参数不变；
  - `clear_cet_flag.py`：加说明和 argparse，CRLF 改为 LF；
  - `blender/build_karin_body.py`：源 blend（PicodraTech 原先是绝对路径）和原生身体网格改为必填的 `--source-blend`、`--dd2-body`。这两个参数也会出现在 `build_report.json` 的 `args` 里；
  - `blender/re_common.py`：RE Mesh Editor 的插件目录原先写死为另一个项目的路径，改为可选的环境变量 `DD2_BLENDER_ADDONS`；
  - `blender/prepare_karin_original.py`：FBX 路径原先写死，改为 `--` 之后的第二个参数，SHA-256 检查不变；
  - `DD2Tool.csproj`：RE-Engine-Lib 位置提成属性 `ReeLibDir`，默认值仍是同级的 `../RE-Engine-Lib`；
  - 只把 CRLF 改为 LF：`MdfTools.cs`，以及 `audit_foreign_refs.lua`、`audit_joints.lua`、`container_joints.lua`、`native_refs.lua`、`skirt_rec.lua`。

  其余 16 个文件与原文件逐字节相同，包括 `patch_mesh_header.py`、4 个 `reframework/` 脚本和另外 4 个 C# 源文件。处理逻辑没有改。
- **等价性验证（离线）：**
  - **条件：**
    - build `25290080` 的原生文件；
    - Python 3.14.0、numpy 2.5.2、Pillow 12.3.0；
    - Blender 4.5.12 LTS、RE Mesh Editor 0.66，插件经 `DD2_BLENDER_ADDONS` 加载；
    - texconv 2026.5.8.1；
    - DD2Tool 由本包源码编译：放在 RE-Engine-Lib（`bf0e5e5`）旁边，用 .NET SDK 10.0.401 编译通过，在 .NET 8 运行时上运行。
  - **DD2Tool：** 对同一个 mesh 的 `meshinfo` 输出，与项目里的 DD2Tool 相同，只有记录的输入路径不同。
  - **PicodraTech v1.3.0：** 依次运行本包的 Blender 脚本、DD2Tool `meshconv` / `meshreorder`、`patch_mesh_header.py`、`meshinfo`、贴图脚本、`mdfbuild`、`make_chain_spec.py` + `chainbuild`、`pack`：
    - `mdfbuild` 用的是项目的 MDF 规格，路径改到临时目录；
    - `.240423143` 和 `.260421070` 网格都与项目的构建相同，12 张贴图与项目缓存相同；
    - PAK 与发行包逐字节相同（`2E8E9EFE…`）。
  - **Original v1.0.1：** 从项目当时的 Blender 输出（`.240423143`）开始，走同样的流程：
    - 15 张贴图相同；
    - PAK 与发行包逐字节相同（`4FE56A2D…`）。
  - **Original 的 Blender 这一步：**
    - 用本包脚本重跑，网格与项目的相差约 11 字节（共 3.56 MB）；两次重跑之间也差这么多，固定 `PYTHONHASHSEED` 也一样；
    - 两次的 `build_report.json` 除路径外相同；
    - 这一步本身不是逐字节稳定的。这个差异对游戏有没有影响，没有测试；
    - PicodraTech 那一步重跑逐字节相同。
  - **Original 的源模型转换：** `prepare_karin_original.py` 用脚本里记了 SHA-256 的那个 FBX 重跑：`inventory.json` 和 5 张图片与项目的逐字节相同，blend 文件不同（Blender 文件里有路径等信息）。共享模型目录里现在那个 FBX 是 2026-10-02 为战神项目烘焙过膝盖的版本，脚本按 SHA-256 拒绝了它。
  - **链规格：**
    - `make_chain_spec.py` 的 PicodraTech F、child、Original O 三种输出，与项目原脚本逐字节相同；
    - F 和 O 也与两个发行版当时用的规格相同；
    - 用 README 里的 Blender 片段从源 blend 导出的骨骼表，得到的 F 规格也相同。
  - **Lua：**
    - 本包的 `karin_replacer.lua` 与 PicodraTech v1.3.0 发行脚本相同（`E6947AAD…`）；
    - `make_original_lua.py` 用它生成的脚本，与 Original v1.0.1 发行脚本逐字节相同（`3A2AD3FB…`）；
    - 对项目里的生成文件，`--check` 输出 `up to date`。
  - **`clsp_dump.py`：** 对原生 `body_female.clsp.3` 打印的内容和写出的 JSON，都与项目原脚本相同。
- **合成数据测试：** `DragonsDogma2Tools` 4 项。
  - 链规格的四元数：`swing_from_x` 把 +X 精确转到 7 个方向（含 ±X），是单位四元数，没有绕 X 的扭转。`tilt_outward` 用的是合成的裙子骨架：4 个根围着一根偏离原点的竖轴，父骨坐标系都转过。检查每个节点的锥轴与静止方向的夹角正好是 0.25 rad，锥轴落在静止方向和外向量所在的平面里，并且朝外转；别的 setting 的组不变；
  - `patch_mesh_header.py`：只改偏移 22 的 2 个字节，`--flags` 有效，旧版本（240423143）报错且文件不变；
  - `clsp_dump.py`：MurmurHash3 的公开测试向量，`L_Breast` 的哈希与 DD2Tool（REE-Lib）打印的值相同，胶囊和球两种预设的解析，命令行写 JSON；
  - `devcmd.py`：没有游戏目录时报错；目录下没有 `reframework/` 时报错，也不创建目录；用假的游戏目录走一遍命令文件和结果文件。

  `--help` 测试覆盖 `scripts/` 下全部 7 个脚本；`build_karin_textures.py` 在缺 numpy 或 Pillow 时跳过。根测试共 46 项，全部通过。
- **未验证：**
  - 便携版没有装进游戏测试，实机结论来自项目用原脚本构建的发行包；
  - DD2Tool（C#）和 Lua 不在 Python 测试里，只用在上面的离线重建中；
  - `devcmd.py` 和 `karin_dev.lua` 没有连游戏测试；
  - 测试套件对 Blender 脚本只做语法检查；
  - 非 Windows 系统、其他 build、其他工具版本下的逐字节一致性；
  - 新模型的案例常量。

## 2026-10-06：看门狗物理（链、大衣布料、VRM 构建器的物理段）

- **迁入内容：** 3 个 Python 文件和 1 个配置样板，放在 `portable-kits/watch-dogs/`。
  - 来自项目的 `.work/physics/`：
    - `smu_format.py`（原名同）；
    - `xbg_physics.py`：合并自 `rig_physics.py`、`vanilla_skeleton.py`，以及 `build_coat_cloth_k15.py`、`build_k15_combined.py`、`build_ko_combined.py` 中的通用部分；
    - `vrm_physics.py`：来自 `build_ko_combined.py`。
  - `build_from_vrm.py` 新增可选的 `physics` 段和 `--colliders`。
  - `profiles/karin_original_1_0_0.json`：Karin_Original 1.0.0 的链、裙子布料和背面设置。
  - PROVENANCE 记录每个来源文件的原始 SHA-256；同一个公开文件合并了几个来源时，每个来源各占一行。
- **通用化改动：**
  - 保留的原版对象数原先写死为 16，改为"到大衣布料为止"；表的全局粒子分界原先写死为 161，改为按保留对象的节点数计算。对 Aiden 的模板，两种算法结果一致（16 和 161）。
  - 碰撞体：原先直接读 Nicky 的 char10.xbg。现在改为读 `xbg_physics.py export-colliders` 导出的 JSON，缺省时退回由骨架推出的胶囊。仓库不收录游戏数据。
  - 链、布料、背面的参数全部移到配置文件；项目里按模型写死的流程（蓝白 Karin 从源 BLEND 找回链权重）只写进文档，不迁入。
  - 没有 `physics` 段时，构建路径与此前完全相同。
- **等价性验证：**
  - **条件：** Python 3.14.0、numpy 2.5.2、Pillow 12.3.0；输入为 Karin_Original 的 VRM，Karin 1.3.0 运行包作底包。
  - **有物理：** `profiles/karin_original_1_0_0.json` 配合从 char10.xbg 导出的碰撞体，输出 `READBACK PASS`，char01.xbg 与用户实机验收的 Karin_Original 1.0.0 逐字节相同（`609B07FC…`）。
  - **无物理：** `profiles/karin_original.json` 仍逐字节重建 0.1.2 的 char01.xbg（`CDE17BB0…`）。
  - **不给碰撞体文件：** 用骨架推出的胶囊，构建通过，各链静止时都在碰撞体外。
- **合成数据测试：** `WatchDogsPhysics` 3 项。
  - SMU 对象写出与解析的往返：不同起始偏移下矩阵都按文件偏移 16 字节对齐；名字哈希错误时报错；
  - 在合成模板上搭链：节点位置、父节点、+Y 朝向、逆绑定、保留对象逐字节不变、只有一个挂点时自由节点的挂点序号为 0、LOD 不变；`move()` 能移动和改挂节点；`export-colliders` 导出且拒绝覆盖；
  - VRM 端到端：合成的 jiggle、大衣布料、领子链和表。检查：
    - 保留和去掉的对象、表项分界；
    - 布料参数和大腿胶囊半径；
    - 改挂的粒子（仍固定的那个保持固定）；
    - 链的挂点和 flags、碰撞组（碰撞体文件和骨架推出两种来源）；
    - 裙子和头发的权重、背面副本。
- **未验证：**
  - 实机只有 Karin 1.6.0（FBX 路线，本包不含其流程）和 Karin_Original 1.0.0；
  - 骨架推出的胶囊、其他模型、带不同物理块的模板都没有实机测试；
  - 游戏的链做不到运动跟随，这是引擎限制，不是本包的缺陷。

## 2026-10-03：看门狗 VRM 构建器整理成通用版

- **迁入内容：** 8 个 Python 文件和 1 个配置样板，放在 `portable-kits/watch-dogs/`。
  - 来自项目的 `.work/karin_original/`，按职责改名：`vrm_model.py`（原名同）、`vrm_fit.py`（原 `karin_fit.py`）、`vrm_weights.py`（原 `weights_map.py`）、`vrm_assemble.py`（原 `assemble.py`）、`vrm_textures.py`（原 `build_textures.py`）、`build_from_vrm.py`（原 `build_karin_original.py`）、`package_mod.py`（原 `package_karin_original.py`）、`char01_paths.py`（原 `fat_paths.py`）；
  - `profiles/karin_original.json`：Karin_Original 0.1.2 的材质分槽和次级骨链规则，从原脚本里写死的常量整理而来；
  - PROVENANCE 记录每个文件的原始 SHA-256 和公开版 SHA-256。
- **通用化改动：**
  - 模型相关的常量移到配置文件：VRM 材质到 4 个槽位的映射、高光类别、头发和裙子的链规则（`match`/`under`/`to` 或 `to_side`/`shares`/`side_width`）；
  - 链级原先取节点名的数字后缀，改为向上数到分叉节点或人形骨骼的步数。对 Karin_Original，两种算法在所有带权重的节点上结果一致；
  - 贴图：同一槽位多张 base color 时按配置顺序上下拼或拼成网格，加复制边缘的缝隙；睫毛槽裁到实际用到的 UV 区域；合成尺寸取底包 donor 的实际尺寸，原先写死为 Karin 1.3.0 的尺寸；
  - 拟合：根据左右大腿判断朝向，VRM 0.x（朝 −Z）先转 180°；VRM 0.x 的拇指改用 1.0 命名；可选人形骨骼和模板骨骼缺失时跳过对应步骤；
  - 权重：除 0.1.2 已有的眼骨外，下巴也并入 `Head`；模板里缺少的 char01 骨骼退回最近的已映射祖先；
  - 构建入口直接读底包 FAT/DAT，取出模板 XBG 和 donor XBT，不再依赖项目目录；新增 `build_report.json`；
  - 打包：底包、pack 名、friendlyId、版本、描述和 ZIP 时间戳都由参数给出；modconfig.json 保持 CRLF；输出目录非空时默认拒绝写入；
  - `repack_fat8.py` 拆出 `entry_hash` 和 `rebuild` 供打包调用，命令行行为不变。
- **没有迁入：** `twist_profile.py`（扭转骨比例已作为常量写进 `vrm_weights.py`）、`eye_check.py`、`preview_*.py`、`inspect_*.py`、`pose_test.py`：只服务于本项目的诊断。VRM、贴图、底包和产物都不收录。
- **等价性验证：**
  - **条件：** Python 3.14.0、numpy 2.5.2、Pillow 12.3.0。输入为 Karin_Original 的 VRM（VRM 1.0）、`profiles/karin_original.json`、Karin 1.3.0 运行包作底包，modconfig 取自 0.1.2 包。
  - **结果：** `build_from_vrm.py --package` 输出 `READBACK PASS`。char01.xbg（`CDE17BB0…`）、15 个 XBT、FAT、DAT、modconfig.json 和 ZIP（`20D92DD7…`）都与用户实机认可的 Karin_Original 0.1.2 逐字节相同。
- **合成数据测试：** `WatchDogsVrmBuilder` 3 项。
  - 用合成 VRM 1.0 和合成底包端到端构建并打包：回读通过；缩放、躯干保留与四肢关节移动；前臂摆姿势方向；眼睛权重并入 `Head`、头发链分给 `Spine2`、裙摆按左右分给两侧大腿；两张外套贴图上下拼、睫毛裁剪；新包只改动预期条目；输出目录非空时拒绝写入；
  - VRM 0.x 的朝向判断和拇指改名：同一模型的 0.x 与 1.0 版本拟合结果一致；
  - 配置漏列材质时报错；三张贴图拼成 2×2 网格。
- **未验证：** 除 Karin_Original 外的任何模型都没有实机测试；VRM 0.x、缺失可选骨骼、多贴图拼图集只有合成数据测试。

## 2026-10-03：新增看门狗 XBG 写出器

- **迁入内容：** 11 个 Python 文件，放在 `portable-kits/watch-dogs/scripts/`。
  - 写出器，来自项目的 `.work/xbg_writer/`：`xbg_model.py`、`xbg_codec.py`、`fbx_reader.py`、`fbx_mesh.py`、`fbx_to_xbg.py`，入口是 `build_xbg_from_fbx.py`；
  - FAT v8，同一来源：`extract_fat8.py`、`repack_fat8.py`；
  - 骨架：`xbg_skeleton.py` 来自 `.work/karin_v14/skeleton.py`，`xbg_skeleton_patch.py` 来自 `.work/karin_original/skeleton_patch.py`；
  - 贴图：`xbt_encode.py`，来自 `.work/karin_original/`；
  - PROVENANCE 分别记录每个文件的原始 SHA-256 和公开版 SHA-256。
- **没有迁入：**
  - `make_test_package.py`、`fat_paths.py`、`package_karin_original.py`：写死了本项目的发布目录和条目清单。打包改用 `repack_fat8.py` 和使用说明里的步骤；
  - Karin_Original 的 VRM 构建脚本（`vrm_model.py`、`karin_fit.py`、`weights_map.py`、`assemble.py`、`build_karin_original.py`、`build_textures.py`）：与该模型的材质名、部件名绑定；
  - 格式反推和对照工具（`roundtrip_test.py`、`compare_xbg_*.py`、`fit_*.py`），以及 1.4、1.5 的修复脚本：只服务于本项目的旧 FBX；
  - 模板 XBG、样本、FBX 和贴图：它们来自游戏或模型。
- **便携改动**在 6 个文件：
  - `build_xbg_from_fbx.py`：新增 `--force`，默认拒绝覆盖已有的输出和报告；
  - `extract_fat8.py`、`repack_fat8.py`：
    - 改用 argparse。原来直接读 `sys.argv`，运行 `--help` 会出错；
    - 默认拒绝覆盖已有输出；
    - `repack_fat8.py` 新增 `path_hash`，替换键可以直接写游戏路径；
  - `xbg_skeleton.py`：
    - 改名，原名 `skeleton.py` 太泛；
    - 从同目录导入 `xbg_model`；
    - 命令行改为 argparse 的通用残差检查，去掉了 Karin 专用的关节打印；
  - `xbg_skeleton_patch.py`：
    - 改名；
    - 新增 `rigid_world`，未列出的关节随父骨刚性移动；
    - 新增带写后验证的命令行；
    - 文档字符串里的逆绑定数量更正为 382；
  - `xbt_encode.py`：
    - 改为从同目录导入本包的 `xbt_tool.py`；
    - 新增 argparse 命令行，默认拒绝覆盖；
    - PSNR 改为输出普通浮点数。

  其余 5 个文件与原文件逐字节相同，编解码和转换逻辑都没有改。
- **等价性验证：**
  - **条件：** Python 3.14.0、numpy 2.5.2、Pillow 12.3.0。全部用本包的脚本运行，输入是项目已有的文件。
  - **写出器：** 输入为 v1.3 的 FBX 交接文件和 1.3.0 模板。`build_xbg_from_fbx.py` 输出 `READBACK PASS`，结果与项目写出器先前的输出逐字节相同（`4502953c…`）。
  - **骨架：** 在 1.3.0 模板上把两侧上臂沿锁骨方向内移 4 cm。`xbg_skeleton_patch.py` 移动了 82 个节点，上臂间距从 0.3726 m 变为 0.2931 m，与实机认可的 1.5 一致，残差没有变大。
  - **贴图：** `xbt_encode.py` 生成的头发和睫毛 XBT，与 Karin_Original 0.1.2 包内的文件逐字节相同。
  - **FAT：** 不替换任何条目时，`repack_fat8.py` 重打 1.3.0 包，FAT 和 DAT 都与原文件逐字节相同；`extract_fat8.py` 解出 22 个条目。
  - **合成测试：** `tests/test_portable_tools.py` 新增 5 项（`test_wd_*`）。把对齐测试换回旧的"照抄补零"写法时，4 个子用例全部失败；用修复后的写法全部通过。

## 2026-10-02：新增战神：诸神黄昏构建器

- **迁入内容：** 29 个 Python 文件。
  - `scripts/` 下 26 个：两个角色的构建入口、回读校验、屈膝模拟、两个贴图包入口、骨架角色表、VRM 贴图导出、源模型形态键烘焙，以及 17 个模块；
  - `scripts/blender/` 下 3 个 Blender 脚本。放在子目录里，是为了不让 `--help` 检查去跑它们；
  - 来源是项目工具目录 `Tools_GoWR` 的 `gowr/`、`source_fix/`、`blender/`。`knee_sim.py` 来自 agent 会话的临时目录，项目目录里没有它。`gamedir.py` 是新写的；
  - PROVENANCE 分别记录每个文件的原始 SHA-256 和公开版 SHA-256。
- **没有迁入：**
  - `build_freya_final.py`：它改的是 `r_freya00.wad`，游戏不加载这个文件，是被否决的路线；
  - `lodpack.py`：没有脚本引用它；
  - `launch_test.sh`：仓库不收 `.sh` 文件；
  - `data/` 里的角色表、骨骼表、贴图计划和原版 boot-options，`work/` 里的拟合结果和原版 wad。它们来自游戏或模型。
- **便携改动**在 12 个文件，另加新文件 `gamedir.py`：
  - 游戏目录只在 `gamedir.py` 一处设置：`--game` 或环境变量 `GOWR_GAME`，都没有时明确报错。`build_mesh.py`、`build_textures.py`、`agctex.py` 原来写死的路径改为调用它；
  - `agctex.py` 改为第一次用到时才加载 DLL，所以任何模块在任何系统上都能导入；
  - 入口脚本改用 argparse，底板 wad、拟合目录、骨骼表、角色表和输出都从参数传入。涉及 `build_kratos_final.py`、`build_valk_final.py`、`verify_build.py`、`knee_sim.py`、`build_textures.py`（新增 main，用奎托斯的默认规则）、`build_valk_textures.py`、`rigspec.py`、`extract_vrm_textures.py`、`bake_knee.py`、`wad.py`；
  - `verify_build.py` 不再从构建脚本导入 `BASE_WAD`，也不再切换到自己所在的目录；
  - `rigspec.py` 的骨骼表改成常量 `SPECS`，去掉了 `r_freya00` 那一份；
  - `knee_sim.py` 的骨骼号、槽位号和膝盖高度提成顶部常量，CRLF 换行改为 LF；
  - `wad.py` 直接运行时会先列出全部条目。

  其余 16 个文件与原文件逐字节相同，包括 3 个 Blender 脚本。处理逻辑没有改。
- **等价性验证：**
  - **条件：** build `18979360`；Python 3.14.0、numpy 2.5.2、scipy 1.18.0、Pillow 12.3.0、lz4 4.4.5、etcpak 0.9.15、texture2ddecoder 1.0.6。全部用本包的脚本运行。输入是项目已有的拟合结果（来自已修正膝盖的源模型）、骨骼表、两个角色表，以及从 VRM 导出的贴图源 PNG。
  - **奎托斯：** 底板是 KarinPicodraTech_Kratos 的 wad。`r_heroa00.wad`（`c8b43fc4…`）、`KarinOriginal.lodpack`（`a483890f…`）及其 `.toc`、`KarinOriginal.texpack`（`b37d5ca5…`）及其 `.toc`，与已发布的 5 个文件逐字节相同。
  - **芙蕾雅：** 底板是原版 `r_freyavalkyrie00.wad`（LZ4）。`r_freyavalkyrie00.wad`（`f003da61…`）、`KarinOriginalFreya.lodpack`（`408cc758…`）及其 `.toc`、`KarinOriginalFreya.texpack`（`20d321c0…`）及其 `.toc`，与已发布的 5 个文件逐字节相同。
  - **报告：** 两个角色的 `mesh_report.json` 和贴图 `.plan.json`，也与项目里的记录逐字节相同。
  - **回读：** `verify_build.py` 两个角色都是 `BAD 0`（奎托斯 10 个槽位，芙蕾雅 19 个槽位，位置误差都是 0）。
  - **屈膝：** `knee_sim.py` 在 0、30、60、90 度时，`outside_knee` 都是 0。会话里的原脚本对同一份输出给出的结果逐行相同。
  - **角色表：** `rigspec.py` 重新生成的两个角色表，与项目使用的逐字节相同。奎托斯的骨架和项目当时一样，是从 KarinPicodraTech_Kratos 的 wad 读的。
  - **形态键烘焙：** `bake_knee.py` 从 `.orig` 原件烘焙出的 FBX（`18f00e1a…`）和 VRM（`8f930404…`），与项目当时在会话里烘焙的副本逐字节相同。
    - 这次比对发现，共享模型目录里的两个烘焙文件与之不同：各有一段 384 KiB（0x60000）、按 4 KiB 对齐的全零块，VRM 在 0xC0000，FBX 在 0xE0000，块以外逐字节相同。结果是那个 FBX 无法解析，那个 VRM 里脸部网格 `Body` 有 70 个形态键的数据变成了 0；
    - 这是复制进同步盘时发生的存储损坏，不是脚本差异。`.orig` 原件没有这种全零块；
    - 2026-10-02 当天已用会话里的烘焙副本替换，替换后两个文件的哈希与本包输出一致，FBX 能解析，VRM 脸部全零形态键的数量与原件相同（474 个里 218 个，原本就是空的）。复制进同步盘的文件要在复制后重新核对哈希。
  - **其他：** `scripts/` 下 26 个脚本都能用 `--help` 运行。
- **合成测试**新增 7 项：
  - 三种骨骼权重布局的编码、解码往返：(9,2,4)+(10,2,3)、(9,2,4)+(10,2,2)、(9,4,4)+(10,3,1)。第二种检查 8 个 u16 骨骼槽（用 7 个，第 8 个为 0），骨骼号大于 2047 也不丢；超出容量的影响数按 10 / 7 / 4 截断；
  - 单组多成员 lodpack 的写入，以及从 lodpack、`.toc`、LZ4 压缩的 `.toc` 回读；
  - 槽位规划：先取共同档位再按顺序升级，索引容量也算；副槽连最低档都放不下时，部件交给主槽；主槽放不下时从末尾丢部件；什么都放不下时报错；
  - 二进制 FBX：16 种长度下原样写回逐字节相同（覆盖"已对齐时填充 16 字节"）；改动 zlib 压缩的数组后重写，其他属性不变，尾部填充仍按 16 字节对齐；
  - VRM 形态键烘焙：`body_2` 的稀疏 `kisekae_Knee` 加到基础网格上，该形态键清零（索引保留），包围盒更新；另一个形态键和另一个网格不变；
  - 骨架镜像：同一关节上叠两根骨时按父骨选择，`left_override` 只替换指定的角色；
  - 游戏目录：没设置时报错；导入 `agctex.py` 不需要 DLL，第一次真正使用时才去找它。

  根测试共 31 项，全部通过。十个游戏的独立导出测试也全部通过，其中战神的测试在导出包里确实执行了，没有被跳过。
- **依赖：** 本包的额外依赖放在 `portable-kits/god-of-war-ragnarok/requirements.txt`：numpy 2.5.2、scipy 1.18.0、etcpak 0.9.15、texture2ddecoder 1.0.6（需要 Python 3.12+）。
  - Pillow 和 lz4 来自根 `requirements.txt`；
  - 贴图那一步要在 Windows 上调用游戏自带的 `libSceAgcTextureTool.dll`；
  - Blender 5.0.1 只用于拟合、减面和骨骼表。
- **未执行：**
  - Blender 的三步（骨骼表、拟合、减面）没有重跑，等价性验证用的是项目已有的拟合结果和骨骼表；
  - 用原版 `r_heroa00.wad` 做奎托斯底板；
  - 新模型的案例常量；其他 build；其他库版本下的逐字节一致性；
  - 在非 Windows 系统上跑网格步骤；
  - 本次没有部署或启动游戏，实机证据仍是此前 agent 的自测。

## 2026-10-02：新增西之绝境构建器

- **迁入内容：** 9 个 Python 文件，`build_hfw.py`、`make_mod.py`、`patch_bounds.py` 和 6 个模块或工具脚本。PROVENANCE 分别记录每个文件的原始 SHA-256 和公开版 SHA-256。
- **便携改动**只在 4 个文件：`make_mod.py`、`patch_bounds.py`、`pose_preview.py`、`gamekey.py`。
  - 4 个文件的位置参数都改用 argparse，有了 `--help`，测试也就能统一检查各脚本的帮助输出；
  - `make_mod.py` 在缺少 h2 工具、`.pristine` core、texconv 或 `jobs.json` 时直接报错；
  - `gamekey.py` 在非 Windows 系统上也能导入。

  其余 5 个文件与原文件逐字节相同。其中 `vrm.py` 与对马岛便携包中的同名文件逐字节相同。
- **等价性验证：**
  - **条件：** build `14835813`；Python 3.14.0、numpy 2.5.2、scipy 1.18.0、Pillow 12.2.0；texconv 2024.6.5.1（SHA-256 `9450ba6c…`）；h2_pc_mi_091 0.9.1（SHA-256 `871331ef…`）；同一 VRM 和同一组 h2 导出。
  - **构建：** `build_hfw.py` 的 30 个输出与 v4 构建逐字节相同，包括 25 个 ascii、4 张页和 `jobs.json`。
  - **导入和补丁：** `make_mod.py` 和 `patch_bounds.py` 产出的 33 个 mod 文件，与 agent 实机测试过的 v4 逐字节相同。便携改动前后各跑了一次，两次都相同。
  - **其他：** `pose_preview.py` 产出 15 个 OBJ；`make_mod.py` 在工具目录缺失时以退出码 2 拒绝运行。
- **合成测试**新增 5 项：
  - ascii 读写往返：骨架、多 UV 层、8 个权重槽、LF 换行，且不写出 `nan`；
  - core 补丁：常量从脚本源码中读取，检查 4 个包围盒和 6 个 SkinInfo 部件；类型不是 7 时拒绝修改，文件保持不变；
  - 权重量化，以及射线锥遮挡判定（立方体内外各一个点，另测距离不足的情况）；
  - 掩码合并：两个包围盒重叠但足迹分离的岛分成两块，镜像的岛合成一块；
  - 姿势 FK：转轴不动，子骨跟随，蒙皮按权重混合。

  根测试共 24 项，全部通过。九个游戏的独立导出测试也全部通过，其中西之绝境的测试在导出包里确实执行了，没有被跳过。
- **依赖：** 本包的额外依赖放在 `portable-kits/horizon-forbidden-west/requirements.txt`：numpy 2.5.2、scipy 1.18.0（需要 Python 3.12+）。
  - Pillow 来自根 `requirements.txt`；
  - `gamekey.py` 另需 pywinauto，只在 Windows 上做实机测试时使用。
- **未执行：**
  - 新模型的案例常量；
  - 其他 build；
  - 其他库版本或 texconv 版本下的逐字节一致性。

  实机证据仍是 v4 的 agent 自测，用户尚未单独确认。

## 2026-10-01：新增对马岛构建器

- **迁入内容：** 9 个 Python 文件，`build_karin.py`、`verify.py` 和 7 个模块。PROVENANCE 分别记录每个文件的原始 SHA-256 和公开版 SHA-256。
- **便携改动**只在 `build_karin.py` 和 `verify.py` 两个文件：
  - 去掉写死的本机游戏目录和 VRM 路径，改为 `--game`（或 `GOT_GAME_DIR`）和必填的 `--vrm`；
  - texconv 改为可选的 `--texconv`，可用 `--expected-texconv-sha256` 校验；不提供时用 etcpak；
  - 两个文件的 CRLF 换行统一为 LF。

  其余 7 个文件与原文件逐字节相同。
- **等价性验证**（build `23879181`；环境为 Python 3.14.0、numpy 2.5.2、scipy 1.18.0、Pillow 12.2.0、etcpak 0.9.15）：用 PROVENANCE 里记录的便携脚本、同一 VRM 和 texconv 2025.10.28.1（SHA-256 `2cb5703c…`）重建两个 profile，输出与项目构建逐字节相同：
  - Original：md5 `a30f3ac17122e2ab1702bc74dffa2ec0`；
  - PicodraTech：md5 `bf0a6e15a6c7786dd48a91210e31fc82`。

  两个 profile 不带 texconv 的 etcpak 构建都通过 `verify.py`（PROBLEMS none，使用 76 根骨骼）。
- **合成测试**新增 6 项：
  - PSARC 数据原样存储且按 8192 对齐（用非零载荷检查）；
  - 权重和法线打包；
  - 减面时边界锁定、面朝向不翻；
  - 拼页像素与 UV 一致，缩小比例下也一致，透明标记不丢色；
  - 下垂姿势反解；
  - 5 种错误输入被拒绝：缺 VRM、缺游戏目录、只给哈希不给 texconv、texconv 路径不存在、哈希不符。

  根测试共 19 项，全部通过；八个游戏的独立导出测试通过，其中对马岛测试在导出包里确实执行，没有被跳过。
- **依赖：** 本包的额外依赖放在 `portable-kits/ghost-of-tsushima/requirements.txt`：numpy 2.5.2、scipy 1.18.0、etcpak 0.9.15、texture2ddecoder 1.0.6。
  - 这些版本需要 Python 3.12+。
  - 根 `requirements.txt` 不变，其他工具包仍支持 Python 3.10。
  - 没装这些依赖时，对马岛测试会跳过并提示安装命令。
  - 本机的 Pillow 是 12.2.0、markdown-it-py 是 4.2.0，与根文件里的 12.3.0 / 4.0.0 不同。
- **未执行：**
  - 新模型的 profile；
  - 本次没有新的实机部署；
  - VRM 读入只在两个项目模型上验证过；
  - 没有在其他库版本上核对逐字节一致性。

## 2026-09-15：新增 MK1 公开工具与第七游戏导出

- 迁入MK1流程、8份案例、当前状态、模板及11个源码/测试文件（6个工具、5个测试文件），没有游戏/模型payload或专用二进制。公开脚本只规范LF换行；原始和公开字节hash分别保存在PROVENANCE。
- 根组件测试13项通过，其中MK1入口执行18项合成测试及3个CLI帮助检查；Windows PowerShell合成部署测试通过，4项hash/路径拒绝生效，不操作真实游戏。
- 七个游戏的独立导出测试通过：目录含空格，使用导出包自己的代码和测试；MK1工具在导出包中实际执行，未选择游戏显式跳过。
- 公开边界、链接、JSON、Python语法和源码provenance检查通过。Python3.12，markdown-it-py4.0.0、lz4 4.4.5、Pillow12.3.0。
- 当前T1000 v8材质复发与Umbrella柯南武器候选未安装均单独说明；此次迁入没有重新Cook、部署或实测游戏，也没有更新旧v0.1.0 Release附件。

以下为六游戏首次迁入的历史记录。

整理日期：2026-09-06。状态：便携脚本组件测试，不是六款游戏新 Mod 的端到端验收。

测试环境：Python 3.12.10、lz4 4.4.5、markdown-it-py 4.0.0；requirements.txt 与实际测试版本一致。

## 实际迁入

19 个原项目 Python 文件；每项在 PROVENANCE.json 中记录源相对位置、原始大小与 SHA-256。保留的是作者在工作区编写的算法/包装器，未复制参考 Mod、模型、纹理、原游戏文件或第三方 DLL。

迁移改动包括：显式输入/输出路径；XBT/PAK 输出防覆盖；VTA 的原 126 骨/31 帧参数化；Forge 的 LZ4 独立于本机 Oodle 路径、field 8 才按需加载已固定 DLL；StudioMDL 新输出检查；RE4 table/payload bounds 检查。格式专属限制仍保留，不将其变成全格式支持声明。

新公共 modkit 提供 init、inventory、verify、doctor、checkpoint、package。旧 PowerShell helper 只保留兼容入口，不再复制到 common 子目录。

## 合成回归

运行 `python -B tests/test_portable_tools.py`：12 项测试通过，使用运行时创建的合成 fixture，没有读取游戏或私人模型。

- 新项目创建、追加断点、重复写入拒绝。
- 完整文件集合/hash 校验、额外文件拒绝、两份 ZIP 字节相等。
- 空输入、越界路径拒绝。
- XBT 提取/注入字节相等、DDS 格式不匹配与覆盖拒绝。
- PRIM/GLB 相同数据通过、顶点改变失败、损坏 GLB 失败。
- 合成 Forge 替换、重复构建相等、独立 extractor 回读；LZ4 不加载 Oodle。
- VTA 使用 1 骨/2 帧的非旧角色合同缩放，保留法线，重复输出拒绝。
- VPK payload CRC 正向/反向和路径隔离。
- KPKA DEFLATE 提取与表/负索引反例。
- HD2 三件套与错误范围检查；LUT header/行内容检查。
- 所有命令行脚本的 --help 启动检查。

未执行：RPKG 实际 TEXT 编译、StudioMDL 实际角色编译、用户 HD2SDK UV 编译、Oodle DLL 分支、六款游戏部署与新运行时测试。原项目的实机验收记录保留为历史证据。

另在 Blender 4.2.23 上创建并保存合成三角网格/UV/材质/shape-key 场景，实际运行迁入的源审计器并核对 JSON。命令使用 --python-exit-code 1，避免脚本异常被 Blender 默认退出码掩盖。合成 Blend 和报告在包外生成，不作为用户模型分发。

## 继续维护

`tests/test_export_portability.py` 另外执行一次覆盖六份导出目录的隔离测试：路径含空格，不使用父仓库代码，逐项检查实际脚本存在，并运行导出包自身的组件测试。未选择游戏的测试显式跳过，所选游戏和公共层通过；六份均通过本地链接、JSON、脚本 provenance 哈希与 Python 语法检查。

修改脚本后重新运行相关测试，更新迁移后的 hash，并检查 standalone 导出。新 build 导致格式失败时记录错误和精确输入身份，修正当前分支，不静默删除检查或复制旧角色常量。
