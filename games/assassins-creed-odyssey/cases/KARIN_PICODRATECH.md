# 案例：Karin_PicodraTech → 卡珊德拉（2026-10-24）

游戏：PC Ubisoft Connect 版（产品 5059）v1.5.6，`ACOdyssey.exe`。源模型：Karin_PicodraTech 的统一图集 blend（10 个网格、237 根骨的 VRoid 骨架、
`kuchi_A` / `blink_L` / `blink_R` 形状键、`Eye.L` / `Eye.R` 眼骨；4 张 4096² 图集，每张都有 ColorAlpha，头发和两张服装图集有 Normal，两张服装图集有 Emission），
是刺客信条：影项目的第一个模型，和 Karin_Original 的 VRoid 头部、形状键同源；不随本库发布。

**用户需求**：Karin_Original v8 通过实机验收后（[案例：Karin_Original](KARIN_ORIGINAL.md)），「使用 Karin_PicodraTech 制作一个新的 mod，同样的需要装配物理和表情。
暂不进行自主测试」。所以这一版 **agent 没有安装、也没有进游戏**，全部结论都是 `offline-accepted`。

## 1. 流程

流程和 v8 相同（[构建流水线](../BUILD_PIPELINE.md)）。下面只记换模型时改了什么、为什么改。

| 步骤 | Karin_PicodraTech v1 | 与 Karin_Original v8 的差别 |
| --- | --- | --- |
| 拟合 | `fit_karin.py --scale auto --ground -0.008 --foot-scale 1.0 --foot-squash 0.8 --phys <34 个链根> --fix-bones Ornaments_1,Ornaments_2,Ornaments_3,Ornaments_4` | 比例 1.7655（Original 1.6541），鞋底抬升 3.77 cm（`FIT feet` 的 `lift`）；180 根 KP 骨。发簪流苏 `Ornaments_1…4` 在源骨架里全部缩在头部中心、长度为 0，物理没有力臂：`--fix-bones` 沿各骨蒙皮顶点的质心重建这条链（影项目 2026-10-07 加的选项） |
| 裙子跟随 | 不做 | 外套下摆片（`KP_Outer*`）离中线 0.22–0.36 m，挂在大腿外侧，不会被大腿穿出；Original 的裙子要 `skirt_follow` |
| 表情 | `face_rig.py --blink-angle 25 --jaw-angle 6 --lid-bone-L 0xB1A846F5 --lid-bone-R 0x86260864` | 参数同 v8。报告：眨眼 `explained` 0.985、杠杆 0.49 m，下颌 0.758 |
| 导出 | `export_karin_lods.py --ratios 1,0.5 --profile aco_pt --keep-full Body.009` | 新的 `aco_pt` 配置：每张图集一个 `ACD_Tex1` 材质（0x2A0CA5B0001…4）；脸在这个 blend 里叫 `Body.009`；`Karin_Alpha` 删掉。网格 235 根骨（上限 255），LOD0 约 8.8 万三角面、LOD1 约 4.4 万 |
| 物理骨架 | `aco_phys_skel.py --params params.json --attach "KP_Code_L=KP_Hair_Tail_L;KP_Code_R=KP_Hair_Tail_R"` | 190 根骨（10 根基础骨、180 根 KP 骨）、107 条物理记录（Original 121 / 66）。参数见 [物理](../PHYSICS.md) §6；`--attach` 是这一版新加的 |
| payload | `build_mod.py --model pt --skeleton …` | 新的 `--model pt`：头发和两张服装图集的 3 个材质用图集自带的法线贴图（头发图集的 G 翻转），皮肤 / 脸用共用的平法线，见 §2 |
| 发行 | `make_dist.py <包目录> <payload> <info.json>` | 安装器、`.cmd` 入口与 v8 包相同；两个包共用状态文件，按安装器的逻辑可以互相切换（推断，§4） |

## 2. 贴图的判断

- **透明通道不用**：在 UV 上采样各网格用到的图集 alpha，只有 `Karin_Alpha` 的面（红晕、泪痕等只在表情形状键下露出的叠加层）用到透明，其余网格的透明裁切面积是 0 %。
  `Karin_Alpha` 和 Original 一样删掉，4 个材质都是不透明的 `ACD_Tex1`。漫反射取 ColorAlpha 的 RGB。
- **法线贴图的绿通道方向用旋度测试判断**（`normal_curl.py`）：高度场 h 烘出的法线有 nx = −∂h/∂u、ny = −∂h/∂v，所以 ∂nx/∂行 和 ∂ny/∂列 都是 h 的混合导数，
  只差一个符号。两者的相关系数 < 0 说明绿色朝图像上方（原版奥德赛：卡珊德拉身体 −0.30、头 −0.25；合成的 GL 约定 −0.925、DX 约定 +0.925）。
  PicodraTech 的头发图集 +0.78 → `build_mod.py` 把 G 翻过来；两张服装图集约 0（编织 / 细节纹理不是高度场，来源也混杂），**判断不了**，保持原样。
  皮肤 / 脸的图集没有法线贴图，用共用的平法线。
- **空白区域先填平再缩小**：图集里没用到的区域是黑色 (0, 0, 0)。4096 → 2048 的 LANCZOS 缩小把黑色混进 UV 岛的边缘，归一化后成了强烈倾斜的法线，
  每个 UV 岛周围一圈接缝线。在原分辨率上先把这些像素填成 (128, 128, 255) 再缩小（`build_mod.normal_png`）。
- **自发光不用**：服装图集里约 9 % 的面积有自发光（外套上的白色发光线条），`ACD_Tex1` 没有自发光输入，这些线条应该只显示底色（推断，未在游戏里看过）。
- 法线写成 `ACD_Tex1` 的布局（RG = XY，B = 金属度 0，A = 光泽度 70，[技术合同](../TECHNICAL_CONTRACTS.md) §8）。

## 3. 离线核对（`offline-accepted`）

- **拟合**：正面 / 侧面 / 背面渲染（影项目的视图渲染脚本，带贴图），比例与 Original 的拟合一致，贴图正确。
- **表情**：`pose_preview.py`（这一版加了 `rot`：按骨 ID 直接转）在褶骨 7° / 15° / 25°、下颌 3° / 6°、看向四个方向、单眼扭转 4063973011 下与 v8 的表现一致：
  静止睁开、逐渐闭合、嘴张开、虹膜转动、眼睑不撕裂。
- **材质**：编译后的材质 / 纹理组 XML 回读，引用的贴图 ID 正确、`TwoSided` 为 True。
- **共用脚本没有破坏 Original**：用改过的 `build_mod.py` / `aco_phys_skel.py` 重建 v8，物理骨架 XML 逐字节相同；7 个数据文件里的 24 个内部文件与 v8 包
  逐个相同。**`.data` 容器本身每次构建的字节都不同**（内部文件相同），所以比较两次构建要解包后比内部文件，不能直接比 `.data` 的哈希。
- 没有做：任何实机检查。物理参数、头发法线翻转、A 的符号、骨数 / 约束数是否有引擎上限（190 / 107 比 v8 的 121 / 66 多）都等用户实测。

## 4. 发行

私有包 `ACOd_KarinPicodraTech_v1`（zip 13 884 565 字节，SHA-256 `455a08b4b4c3934d5fc86b5a295673f3ee5ab5579b99d36e0f0e062d37668117`），结构同 v8 包
（[验证与发布](../VALIDATION_AND_RELEASE.md) §3），payload 的 7 个 ID 也与 v8 相同。两个包共用 `aco_install.py` 和 `<游戏目录>\.karin_aco_state.json`；
卸载只依据状态文件，所以按安装器的逻辑，任一个包的 `install.cmd`（先卸载、再安装）都能换掉另一个（推断：实测过的只有 v8 包在旧安装状态上的重新部署）。

| 文件 | 字节 | SHA-256 |
| --- | --- | --- |
| `00000103E739C903_ACD_CHF_PLA_Kassandra_VisualMaster.data` | 682 | `ee72e6b1b3034e0449a2041774f1dc8317a1dc094f8fe8364137fbe7dc69739e` |
| `00000104280E464B_ACD_CHF_PLA_B01_A01_BodyKassandra.data` | 1 513 302 | `c2ae7b60eb2b3821cf0df18cd6bf4e197a7472a58162e438692a63907595b97a` |
| `00000104280E4653_ACD_CHF_PLA_B01_A01_BodyKassandra_LOD0.data` | 12 319 826 | `3e987dc88262d357c53426dc5cfb63d826773524689fbc52605c12287c38a586` |
| `00000146D5F5EB4C_ACD_CHF_PLA_Kassandra_Hair.data` | 507 | `d3bd09c0cc15c636ef273012823fb9d9936ccffe15785dab9bc36a94d7977cca` |
| `0000016424DFAD4B_ACD_CHF_PLA_Kassandra_Head.data` | 1 485 | `e1dcb05e1176795346782d1d8eb78b90a15b647f8ba162718269c173175825c7` |
| `0000018482B71630_ACD_CHF_PLA_B01_A01_BodyKassandra_LOD1.data` | 542 478 | `51cd0da9a1fb42aeab9f9663abc4635582dea8c7de88b3a8d6c38806dbcae416` |
| `00000194D13C465D_ACD_CHF_PLA_Hair_NEW.data` | 24 473 | `f5d64d06235e241b4ec2524cbafbfb21ee5b8d09764a27a62dd5891dc447d243` |
| `skip.tsv` | 46 | `83e8e43f3e3d215a588842f564b882d4889f27338bd81bf0b5dd50af443f4e70` |

VisualMaster、头部表、头发表和 `skip.tsv` 的内容与 v8 相同（表的编辑与模型无关），但 `.data` 字节不同（§3：容器每次构建都不同）。安装器与 v8 包相同（SHA-256 `7672e2bd…`）。

## 5. 关键判断

- **换模型时脚本按「模型」参数化，而不是复制一份**：`export_karin_lods.py` 加配置 `aco_pt`，`build_mod.py` 加 `--model pt`（材质 ID 段、贴图、法线处理都放进
  `MODELS` 表），`aco_phys_skel.py` 加 `--attach`。每改一个共用脚本就重建 v8 做回归（§3）。
- **不确定的符号不赌**：外套下摆片的前后摆（B，方向从原版马尾推断，v5 的裙片按它改了之后没有再报穿模）取偏向一侧的范围，侧摆（A，符号未确认）取对称的 ±0.1（[物理](../PHYSICS.md) §1）。
- **参数表的合并规则要先读代码**：`params_for` 把所有匹配的行按键合并，宽的 `"off": true` 会漏进它下面更具体的行（[物理](../PHYSICS.md) §2）。第一次生成时蝴蝶结的根、
  环和飘带基节都没有模拟，看报告的记录数才发现（100 → 107 条）。
- 物理参数是影项目里 PicodraTech 的调校换算到奥德赛的范围，第一版。用户测完之后按反馈调。
