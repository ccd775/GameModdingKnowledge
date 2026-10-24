# 构建流水线

命令和环境变量见 [便携包](../../portable-kits/assassins-creed-odyssey/README.md)。这里讲每一步做什么、产物是什么、怎么判断它成功了。

```text
一次性                                    每一版
 aco_forge.py index → 索引 TSV             fit_karin.py（Blender）─► fit.blend + fit_fit.json（KP 物理骨）
 aco_locate.py find / extract               skirt_follow.py（影项目，不随包）─► fit_skirt.blend
 AcoHarness unpack-export → x1 / x2 / x5     face_rig.py（Blender）─► fit_face.blend + face.json        [pose_preview.py 离线看脸]
 AcoHarness export-glb → 卡珊德拉骨架 GLB     export_karin_lods.py ─► karin_lod0/1.glb ─► glb_rotate.py −90 ─► import-glb ─► karin_lod0/1.Mesh
   └─ glb_rotate.py +90                     aco_phys_skel.py ─► Hair_NEW_karin.Skeleton.xml
                                            build_mod.py ─► payload\（7 个 .data + skip.tsv）─► aco_install.py ─► 实机
```

## 0. 准备（一次）

- 给全部 forge 建索引（根目录的 forge，`dlc_*\*.forge` 和 `DataPC_*_dlc_patch_01.forge` 另放一个 TSV）。`aco_forge.py` 只用标准库，直接在测试机上跑，
  只把 TSV 拷回构建机。
- 用 `aco_locate.py find` 确认每个目标 ID 的全部副本和生效的那一份（[技术合同](TECHNICAL_CONTRACTS.md) §3、§5）；在测试机上 `aco_forge.py extract`
  提取，打包拷回构建机，用 AcoHarness `unpack-export` 解包并导出 XML。`build_mod.py` 期望的目录布局（`x1` 表和身体、`x2` 骨架和贴图模板、
  `x5` 弓的材质）见便携包 §0.3。
- 编译 AcoHarness（`acoharness/build.ps1`）：.NET SDK 的 Roslyn 对 .NET 9 运行时和 AnvilToolkit 1.3.6 编译，再把 AnvilToolkit、`Libs\` 和 `Odyssey.gfl`
  拷到输出目录。
- 拟合用的卡珊德拉骨架：`export-glb` 把 `ACD_Unisex_BaseSkeleton`、身体 LOD0、头 LOD0、附加骨架 `Male_BaseAddon`、`Male_AverageAddon`、`Female_Bottom`、
  `Female_Boobs` 和 `Kassandra_Head` 的骨架导出成一个 GLB，再 `glb_rotate.py +90` 转到影脚本的坐标系（[技术合同](TECHNICAL_CONTRACTS.md) §6）。

## 1. 拟合（`fit_karin.py`，Blender 5.0.1）

`fit_karin.py` 是影项目同名脚本的奥德赛副本，唯一的改动是 KP 物理骨的朝向（§1.3）。骨架对象名沿用 `NaoeRig`。

### 1.1 比例与关节（影项目的 v2 策略，`case-derived` 的数值）

- 动画驱动关节位置，改骨架静止姿势没有效果（影项目实测）：几何拟合到卡珊德拉的关节上，骨架不动。
- 全局比例 = Karin 躯干关节（大腿、胸、颈、肩、头）到目标关节的最小二乘：卡珊德拉是 **1.6541**。
- **刚性骨**（Hips、Spine、Chest、Neck、Head 和挂在它们下面的东西：衣服、胸、头发、尾巴）保持 Karin 的原形，不拉伸，只以几厘米的支点偏移跟随关节；
  所以报告里 Hips / Spine 的「误差」是刚性躯干的偏移，不是问题。四肢（锁骨到手、大腿到脚趾、手指）的关节对齐到目标关节，拉伸用 Karin 自己的关节间距；
  每根骨 `inherit_scale = NONE`。
- 脚：`--ground -0.008 --foot-scale 1.0 --foot-squash 0.8` —— 脚保持 Karin 的朝向，只把踝以下压扁到 0.8（鞋长和鞋宽不变），鞋底抬到 −0.008；
  抬升在小腿上从膝（0）渐变到踝（1），膝的支点不动。
- 骨名：Karin_Original（Unity FBX）用 `LeftUpperArm` / `LeftToeBase` 这类名字，脚本按名字形态自动适配。

### 1.2 权重

- 每根 Karin 骨映射到它最近的已映射祖先对应的目标骨；`Spine` 按高度在 `Spine` / `Spine1` / `Spine2` 之间、`Neck` 在 `Neck` / `Neck1` / `Head` 之间分摊；
  每顶点最多 4 个权重。
- 用户在 v3 之后：「比例什么的都可以了」（`runtime-confirmed`）。

### 1.3 KP 物理骨（`--phys`）

- `--phys <链根,…>` 把 Karin 的次级骨链保留成自己的骨（`KP_<名字>`），挂在映射后的目标骨下；输出的 `<out>_fit.json` 的 `phys` 表记每根 KP 骨的父骨、长度、方向。
- **奥德赛的物理骨沿局部 +X**（原版头发 / 马尾 / 裙链都是；影用 −Z）：骨的 head → tail 指向前方并垂直于链，roll 让 Z = X × Y，于是 X 就是链的方向
  （[物理](PHYSICS.md) §3）。
- 项目的链根表来自影项目（Karin_Original 的头发、脸颊发、丝带、鞋标、裙片、耳、尾巴），拟合里生成 139 根 KP 骨；导出的 LOD 裁到用到的骨后共 152 根。
- Karin_PicodraTech：34 个链根、180 根 KP 骨，网格 235 根骨；`--fix-bones Ornaments_1,…,Ornaments_4` 重建源骨架里缩成一点的发簪流苏链
  （[案例](cases/KARIN_PICODRATECH.md) §1）。

### 1.4 裙子跟随

影项目的 `skirt_follow.py`（不随包）把裙子部分蒙到大腿上：v3 用默认值，v5 起 `--max 0.95 --sigma 0.2`（[物理](PHYSICS.md) §5）。

## 2. 表情（`face_rig.py`）

在拟合后的 blend 上，把 Karin 自己的形状键（`kuchi_A`、`blink_L/R`）和眼骨权重拟合成「绑定偏移杠杆」蒙皮：下颌、两侧上眼睑、两侧虹膜。
v8：`--blink-angle 25 --jaw-angle 6 --lid-bone-L 0xB1A846F5 --lid-bone-R 0x86260864`（[表情](FACE.md)）。

- 成功的标志：日志里 `FACE eye L/R`、`FACE blink L/R`（杠杆长度、`explained`）、`FACE jaw`、末行 `FACE_RIG_OK`；`--report` 的 JSON 有每个通道的支点、角度和顶点数。
- blend 里的偏移骨仍摆在游戏的静止位置，所以打开看是正常的；`export_karin_lods.py` 按静止位置导出（存的是偏移后的顶点）。
- 离线看：`pose_preview.py` 用头部骨架的原版姿势摆骨并平涂渲染（Workbench，需要 OpenGL 上下文）；`aco_pose_sim.py` 在导出的 GLB 上做同样的蒙皮计算。

## 3. 导出与导入网格

- `export_karin_lods.py --ratios 1,0.5 --profile aco_tex1 --keep-full Body`：两级 LOD，材质名是新 Material ID，脸不减面（[技术合同](TECHNICAL_CONTRACTS.md) §7）；
  Karin_PicodraTech 用 `--profile aco_pt --keep-full Body.009`；
  `export_report.json` 记骨数和每级 LOD 的面 / 顶点数。
- `glb_rotate.py … −90` 转回奥德赛坐标系；`glb_info.py --joints` 可核对骨数和关节位置。
- `AcoHarness import-glb ./karin_lod0_ody.glb 0 ./karin_lod0.Mesh 00000104280E4653`（LOD1 → `0000018482B71630`）：日志打印顶点格式（应为
  `Pos3s_Norm4ub_Col4ub_Tex2s_Joint4_8bit`）、补白色 Color0 的顶点数、修正的 TBN 数和 `wrote …`。`mesh-bones` 可以把网格骨的 ID 与绑定和原版逐根比较。

## 4. 物理骨架（`aco_phys_skel.py`）

用原版 `ACD_CHF_PLA_Hair_NEW` 的 XML 做模板，`ACD_Unisex_BaseSkeleton` 提供基础骨，`--binds` 用 LOD0 的 `_ody.glb`（连没有蒙皮顶点的链根也有绑定），
`--fit` 用拟合报告。输出骨架 XML 和报告（每根模拟骨的深度、质心、gf、两个摆角范围）。日志 `bones N (base B, KP K), physics records R`：
v5 是 121 根（21 根基础骨、100 根 KP 骨）、66 条记录（[物理](PHYSICS.md) §2）。`--params` 追加参数行（按键合并，[物理](PHYSICS.md) §2），
`--attach SRC=DST` 让一条链挂在另一条上、不写自己的约束；Karin_PicodraTech 是 190 根、107 条（[物理](PHYSICS.md) §6）。

## 5. payload（`build_mod.py`）

1. **容器** `00000104280E464B`：复制解包目录，LODSelector 的 LOD2–4 指到 Karin LOD1（`bt_tool.lodsel` + `compile-xml`），容器里的两个网格换成 Karin 的，
   `pack-data`（沿用原 `.data` 的元数据）。
2. **独立 LOD**：LOD0 / LOD1 的解包目录里唯一的 `0_-_*.Mesh` 换成 Karin 的；LOD0 再追加材质、纹理组和贴图（`add_materials`：对象 1…n，
   [技术合同](TECHNICAL_CONTRACTS.md) §8）。
3. **表**：VisualMaster 去列 2；头部表去列 1–8、14；头发表去列 9 / 10 / 13 并清空 `DynamicResources`。每张表 `bt_tool.edit` → `compile_fixed`
   （日志 `restored N null-ref padding bytes (M inside dropped cells)`）→ 打包。
4. **物理骨架**（`--skeleton`）：`compile_fixed` 编译 `aco_phys_skel.py` 的 XML，打包成 `00000194D13C465D`。
5. 写 `skip.tsv`（SharedGroup 的旧版头发表），删临时目录，末行 `BUILD_OK <out>`。

`--model original|pt` 选材质那一段（ID 基数、4 个部位的贴图、有没有自带法线贴图、要不要翻 G，见 `build_mod.MODELS`）；表和物理骨架那几步与模型无关。
`build_mod.py` 先删再建输出目录，**连 `tmp\` 也会在末尾删掉**：要核对材质，就对输出目录里留下的各数据文件目录（如 LOD0 那个）的对象做 `export-xml` 回读。

v1 构建后把打好的容器重新解包，所有对象完好（`offline-accepted`）。

## 6. 安装与实机

- 把 `payload\` 拷到测试机（项目里打成 zip、分块传过去），游戏关闭时 `aco_install.py uninstall`（旧版）→ `install <payload>` → `status`。
- 实机测试和截图流程见 [开发工具](DEV_TOOLING.md) §4、[验证与发布](VALIDATION_AND_RELEASE.md) §2。

## 7. 可重复性

没有像别的项目那样做过 Blender 一段（拟合、表情、导出）的逐字节重建比较。Python 一段（2026-10-24 测过）：`aco_phys_skel.py` 的骨架 XML 在相同输入下逐字节相同；
`build_mod.py` 重建出的 **`.data` 容器每次字节都不同**，但解包后的内部文件逐个相同 —— 比较两次构建时解包后比内部文件，不要直接比 `.data` 的哈希。可重新部署的包用 `BUILD_INFO.json` 记下每一步的参数、
用 `MANIFEST.sha256` 记下每个文件的哈希，发行身份以 payload 的哈希为准（[验证与发布](VALIDATION_AND_RELEASE.md) §3）。
