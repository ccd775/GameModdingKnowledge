# 构建流水线

命令和参数见 [便携包说明](../../portable-kits/nioh-2/README.md)。本页讲每一步做什么、为什么这样做、产物是什么。
构建输入放在一个工作目录里（便携包里叫 `N2_BUILD`）：`source/`（源模型导出）、`build1/`（贴合结果）、`data/`（骨号与关节）、`fa3/`（帧分析）、`asm/`（着色器反汇编）、`texconv/`。

## 1. 抓帧分析

- 角色：女性、长马尾、穿隼套装（外观），站在**装备界面**。装备界面光照稳定、角色居中，所有护甲都画；关卡里要另外看绘制顺序（[技术合同](TECHNICAL_CONTRACTS.md) §4）。
- `d3dx.ini`：`hunting = 1`、`export_shaders = 1`，帧分析选项带上 vb / ib / cb / 贴图转储。按 `F8` 抓一帧。
  - 一次完整转储有上万个文件、几百 MB。等写完再打包拉回；游戏还开着时不要移动正在写的文件夹（3DMigoto 还持有日志）。
- `fa_parse.py <FrameAnalysis 目录> --json fa.json`：每次绘制的 VS / PS 哈希、vb / ib 哈希、输入布局、顶点 / 索引数、绑定的 PS 贴图。
- `fa_list.py`、`fa_mesh.load_draw()`：按布局把某次绘制的 vb / ib 解成 numpy 数组（位置、权重、骨号、法线、UV、切线、三角形）。
- 着色器反汇编（`ShaderCache\<hash>-vs.txt` / `-ps.txt`）拷进 `asm/`，用来确认 cb0 布局（[技术合同](TECHNICAL_CONTRACTS.md) §3）。

## 2. 全局骨号与关节

- `bones.py <FrameAnalysis 目录> <fa.json> <out.json> <draw …>`：读每次绘制的 `vs-cb0` 调色板，按矩阵相等把各绘制的条目归并成全局骨号 `g<n>`，并记下每个全局骨在哪件护甲的第几个条目（构建时从那里取矩阵）。
- `n2_skel.py <bones.json> <joints.json>`：全局骨号按加权中心手工标名（骨盆、脊椎、胸、颈、头、锁骨、上臂、前臂三段扭转、手、五指、大腿三段、小腿、脚踝、脚、脚趾、袴前片、围巾链…）；
  关节 = 父子两根骨的矩阵把同一点映射到同一世界位置的那个点，向权重交界处正则化。产物 `data/joints.json`。
- 装备界面的姿势就是绑定姿势附近的站姿，但围巾和袴前片的链静止时偏离绑定姿势 20–25°（早期借它们做物理时要先摆回去；现在不用了）。

## 3. 源模型

- Karin_Original 的 FBX，和本库仁王3 项目是同一个文件（哈希相同），所以直接复用那边 Blender 4.0.2 后台导出的 `source/`：`source.json`、`source.npz`（10 个部件约 29.5k 顶点、骨骼、权重）、
  `shapekeys.json` / `.npz`（闭眼等形态键）、`textures/`。导出脚本见仁王3 便携包的 `scripts/blender/ko_extract_source.py` 和 `scripts/n3build/blender_shapekeys.py`。
- `Karin_Alpha` 材质（眼部叠加层，408 个三角形）需要混合，build1 起就没有带。

## 4. 贴合（`n2_conform.py`）

- 源模型整体缩放 `N2_HEAD_SCALE`（默认 150：米 → 厘米，并让头和游戏的头一样大），平移到 Karin 的 Neck 落在游戏的颈关节上。
- 头和颈保持刚性；其余人形骨各做一个仿射：骨段方向和长度对齐游戏关节，截面保持；再用 Karin 自己的权重做 LBS。方法来自仁王3 / 浪人的 Karin 构建，只是关节换成从仁王2 蒙皮矩阵解出来的。
- 权重写成记号：`g<n>` 全局骨号；`face<e>` 脸调色板的条目（只在脸上）。物理部件（头发、耳朵、尾巴、裙子）的记号在构建器里改成模拟骨 `s<n>`。
- 产物：`build1/conformed.npz`、`build1/conform.json`（含 Karin 的关节在游戏空间的位置，离线物理测试也用它）。
- 检查：`check_skin.py` 用帧分析里那一帧的真实矩阵（按 `merge_a.hlsl` 的方式在 Python 里拼合并调色板）蒙皮 Karin，叠在原版角色上出图。
  它只重建调色板 A：build4 起头发、耳朵、尾巴、裙子改用调色板 B（66 根），对 build4 / build5 的输出会在骨号越界处报 `IndexError`。要再用它，得按 `merge_a.hlsl` 补上调色板 B 和模拟骨的静止矩阵。

## 5. 权重

- 身体、衣服：贴合给出的权重。
- **裙子**（`skirt_from_body`，build3 起）：权重从下面那块身体抄，再往裙摆渐变到同侧大腿。
  - 抄身体：对每个裙子顶点取 `body_2`（皮肤）和 `underwear` 上最近的 128 个顶点，高斯宽度 1 cm 加权（随间隙自适应），在网格上平滑 3 次；只留骨盆、脊椎、胸、腿这些骨（`SKIRT_TOKENS`）。
  - 大腿份额：Y 112 cm 以上为 0，到 Y 80 cm（裙摆）升到 0.85；前后正中 ±6 cm 内左右两条大腿平滑过渡（`SKIRT_Y_TOP / SKIRT_Y_HEM / SKIRT_THIGH_MAX / SKIRT_LR_CM`）。
  - 这样腰部和它盖住的皮肤动得完全一样，下摆跟着大腿：抬腿时前片被带起来，而不是被顶穿。
  - 这一套权重同时是裙摆物理的静止位置（[物理](PHYSICS.md) §3）。
- 物理部件：按链把源模型的骨映射到模拟骨；没有链的部分落到默认记号（头发、耳朵 → 头 g8，尾巴 → 骨盆 g0，裙子 → 权重场）。
- 脸：从原版脸迁移，见 [表情](FACE.md) §1。
- 量化：权重 f16，最后一个权重补足使总和精确为 1；允许负权重（`pack_weights`）。

## 6. 贴图

- 4 张颜色贴图（身体、衣服、头发、脸）用 DirectXTex `texconv` 转 `BC7_UNORM_SRGB`，2048 × 2048。
- 游戏的光照下源贴图过亮：在线性空间里乘一个系数（`ALBEDO_SCALE`：脸、身体 0.65，头发、衣服 0.55）再转。
- 其它槽用 4 × 4 的常量 DDS：`flat_normal`、`white`、`spec_a`、`refrough_b`、`artior_b`（后两个取原版脸贴图的均值）。

## 7. 生成 Mod（`n2_build.py <工作目录> <输出>\KarinN2`）

- `meshes/`：宿主 A 的 `karinA.vb`（30274 顶点，48 字节）和四个 IB（身体、衣服用调色板 A；`hair_b`、`costume_b` 用调色板 B），脸的 `karinB.vb0` / `vb1` / `karinB_face.ib`（3379 顶点、5064 三角形）、`karinB_blink.buf`（每顶点闭眼形态键位移 + 左右）。
- `textures/`：上一节的 9 张 DDS。
- 计算着色器：`merge_a.hlsl`（拼合并调色板 A / B，过期帧外推）、`merge_s1.hlsl` / `merge_s2.hlsl`（影子布局）、`sim_a.hlsl`（23 条弹簧链）、`blink_b.hlsl`（眨眼）、`tick.hlsl` / `stamp.hlsl`（帧计数与帧戳）。
  链参数、碰撞体、调色板映射表都直接写成着色器里的常量。
- `karin.ini`：挂钩、隐藏、资源、自定义着色器和两个宿主的覆盖段（[技术合同](TECHNICAL_CONTRACTS.md)）。
- 副产物 `build1/build_report.json`：各部件顶点数、两个调色板（每个记号取自哪件护甲的哪个条目）、宿主统计、脸的拟合残差和迁移距离、模拟链 / 骨 / 碰撞体半径。
- 断言：每个调色板 ≤ 85 根骨、每个记号都有源绘制、宿主 A 顶点数 < 65536（u16 索引）。

## 8. 编译检查

- `c46.py <d3dcompiler_46.dll> <*.hlsl>`：用 Mod Enabler 自带的 `d3dcompiler_46.dll`（ctypes 调 `D3DCompile`，`cs_5_0`）编译全部计算着色器。
  它比 fxc 10 严：多分量类型 UAV 的读取（`RWBuffer<float4>` 读）会报 X3676，fxc 不报。

## 9. 离线检查

- `check_skin.py`：蒙皮叠图（§4；只支持单调色板的 build1–3 输出）。
- 物理：`checks/simtest.py`（双马尾 / 尾巴）、`checks/eartest.py`（狐耳，带减速的停步、转身、前冲）、`simcheck/`（裙子的静止穿模、按 `sim_a.hlsl` 逐行移植的 Python 模拟、动画驱动、尾巴调参），见 [物理](PHYSICS.md) §5。
- 改了 `write_sim_shader` 要手动同步 `simcheck/simpy.py`。

## 10. 部署

- 整个 `KarinN2` 文件夹放进 `<游戏目录>\Mods\`。替换旧版本时先删旧文件夹，免得留下过期文件；改过着色器后删掉 3DMigoto 在旁边生成的编译缓存（`*.bin`）。
- 游戏开着时按 `F10` 重载。
- 交付前核对：发行包和测试机上的文件逐个比哈希；用构建包重建一遍，和发行包逐字节比较（`README.md` 是手写的，不参与比较）。
