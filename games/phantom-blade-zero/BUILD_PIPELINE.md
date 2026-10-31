# 构建流水线

命令行和参数见 [便携工具包](../../portable-kits/phantom-blade-zero/README.md)。下面是顺序、每步的输入输出和要核对的东西。

## 0. 工作目录约定

| 变量 | 内容 |
| --- | --- |
| `PBZ_WORK` | 原版 dump：`ue/Hun_Invs.uemodel`、`ue/Hun_Young_Skeleton.uemodel`、`ue/Hun_Hat_Skeleton.uemodel`；`c/`（`Hun_Skin_Skeleton`、`Hun_Body_Simple`、`Hun_Head_New` 等的 `.skel.json`）、`g/Hun_Invs.Hun_Invs.skel.json`、`y/`（少年魂） |
| `PBZ_SOURCE_VRM` / `PBZ_SOURCE_BLEND` | 源模型（Karin_Original 的 VRM；PicodraTech 的 `Karin_PT_Unified_Atlas.blend`，旁边要有 `textures/`） |
| `PBZ_ROOT` | UE 那一侧的工作根：`UE\ProjectPBZ`（内容工程）、`logs\`、`out\`、`tools\`（PbzExport、usmap、Oodle DLL、AES 文本） |
| `UE_ROOT` | UE 5.7 安装目录（含 `Engine\`） |
| `PBZ_GAME_DIR` | 含 `ProjectPBZ` 的游戏目录 |

## 1. 提取

1. `pbzx_run.ps1 <子目录> list <正则>` 找资产；`json` 看属性（`PBZX_SCRIPT=1` 时连蓝图字节码一起读）；`export uemodel` 导出骨架和网格给 Blender；
   `skel` 写精确的参考骨架 / 形变 / section（`.skel.json`：每根骨 `name`、`parent`、`t`、`q`、`s`，骨架还带 `retarget`）。
2. 需要的 dump：`Hun_Invs`（uemodel + skel）、`Hun_Skin_Skeleton`（skel，带重定向模式）、`Hun_Body_Simple`（skel，**身体骨名的来源**）、`Hun_Head_New`、
   `Hun_Hat_Skeleton`；少年魂的 `Hun_Young_Skeleton`、`Hun_Young_Body`、`Hun_Young_Head`。

## 2. Blender 构建（`build_pbz.py` / `build_pt.py`）

`blender --background --factory-startup --python build_pbz.py -- <run> --scale 1.30 --variant adult`，再跑一次 `--variant young`（比例 1.32）。
PicodraTech 用 `build_pt.py`（默认比例 1.37 = 1.30 × 眼高比 1.0994 / 1.0415）。

做的事：

- 导入原版骨架（`Hun_Invs.uemodel` 的 1130 根骨），**把原版身体有、这副骨架没有的骨补到父骨上**（`EXTRA`，断言是单位变换；
  `report.json` 的 `body_bones_added`）。领导者网格仍只用原版的 1130 根。
- 按重定向合同摆关节（[技术合同](TECHNICAL_CONTRACTS.md) §5），网格按区域刚体变换摆上去，权重从 Karin 的骨映射到游戏骨。
- 布料分段：每段一个材质槽（`MI_Karin_Skirt`、`MI_Karin_HairTail` …），写 `cloth.json`（每段的掩码、最大距离、参数）和 `cloth_collision.json`（碰撞体）。
- 面部：43 个 `CTRL_expressions_*` 形变 + 34 个 `head_*` ARKit 别名（成年头还有 `KarinFaceShow`），写进头 / 睫毛片的 FBX。
- 输出：`Karin_Leader.fbx` → `Hun_Invs`，`Karin_Body.fbx` → `Hun_Body_Simple`，`Karin_Head.fbx` → `Hun_Head_New`，`Karin_Face.fbx` → `Hun_BrowLashCard`，
  `Empty.fbx` / `Hat_Empty.fbx`（隐藏占位），少年魂的 `*_Young.fbx`，`textures/`，`report.json`，`build.blend`。

核对：`report.json` 的 `missing_face_keys` 为空、`slots_unmapped` 为空、`bones.body` 等于原版身体骨数（264）、布料段的面数和固定点数合理。

## 3. UE 内容工程（UE 5.7）

工程 `ProjectPBZ`（便携包 `ue/ProjectPBZ`）：空插件 `HuaShira`（让资产落在 `/HuaShira/...`）+ 编辑器插件 `PBZModTools`（先用 `build_plugin.ps1` 编译）。
`run_all.ps1 -Run <run>` 依次跑（每步 `ue_run.ps1`，日志里出现标记才算过）：

| 步骤 | 脚本 | 标记 | 内容 |
| --- | --- | --- | --- |
| imp | `ue_import_pbz.py` | `IMPORT_OK` | 第一次导入领导者时生成骨架占位并移到游戏路径；导入身体、头、睫毛片、隐藏占位；占位物理资产和后处理动画蓝图；贴图（VT）和材质实例 |
| young | `ue_import_young.py` | `IMPORT_YOUNG_OK` | 少年魂的身体、头、隐藏件 |
| fixmats | `ue_fixmats.py` | `FIXMATS_OK` | 材质实例重设：第 0 层贴图、湿润参数清零、布料段的槽指向同一材质 |
| bright | `ue_brightness.py` | `BRIGHTNESS_OK` | 贴图亮度系数 |
| clotha / clothy | `ue_cloth.py <run> adult / young` | `CLOTH_OK adult` / `CLOTH_OK young` | 每段布料（插件 `CreateClothFromSlot`）、碰撞物理资产、求解器、关阴影；成年身体复制成 `Hun_Body_Climax` |
| blink | `ue_blink.py` | `BLINK_OK` | 重建 `Hun_CopyPose` / `Hun_CopyPose_Head`（复制姿势 + 眨眼 / FaceShow 叠加，按角色类名门控），并在编辑器里自测 |
| morph1 | `ue_morphdump.py` | `MORPHDUMP_OK` | 形变名单与法线检查 |

然后 `cook.ps1`（带版本号的 cook；按 `Success - 0 error(s)` 判断）和 `mkcontainer.ps1`（容器 + 伴随 pak）。成年 + 少年一次全流程约 2.5 分钟。

PicodraTech 用 `-Mod pt`：导入、少年导入、材质、亮度、布料五步换成 `scripts/ue/pt/` 里的分支（读 `materials.json`），容器名 `z_KarinPT_P`；
项目给它单独复制了一份 UE 工程（`-Root` 指向那份）。

## 4. 读回

`PBZX_EXTRA=<out 目录>` 时 PbzExport 先读 mod 容器。每版至少核对：`Hun_Body_Simple` / `Hun_Body_Climax` 的骨数和 `*_child` 骨、
材质槽名（`MI_Karin_*`）、`Hun_Head_New` 的形变数（78）和材质（槽 0 `MI_Karin_Skin`、槽 1 `MI_Karin_Face`）、布料资产数（每个身体 PicodraTech 7 段）、
`Hun_CopyPose` 的节点和门控。读到 `Blinn_Hero_Hun_*` 这类原版槽名说明读的是原版（`PBZX_EXTRA` 没生效）。

## 5. 安装

游戏关闭时把三个文件放进 `~mods`。发行包的 `install.ps1` 会找 Steam 库、核对 buildid 和包内哈希、拒绝在游戏运行时安装，
并删除另一套 Karin 包（[验证与发布](VALIDATION_AND_RELEASE.md) §3）。
