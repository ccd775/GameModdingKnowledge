# 技术合同

标注：`[I]` = 本作样本里成立的格式 / 运行时事实，`[B]` = 随游戏版本或加载器版本变化（哈希、行号），`[C]` = 本案例的数值。
除注明外，都在游戏 1.25 + Nioh 2 Mod Enabler 1.1（3DMigoto 1.3.16）上实测。

## 1. 归档与被否定的改写路线

- `[I]` 游戏数据在 `<游戏目录>\archive\archive_00.lnk` … `archive_19.lnk`，魔数 `K300`。头 0x20 字节：条目数、总大小、对齐；
  每个条目 32 字节：偏移、大小、压缩后大小、压缩标志。压缩条目按 16 KB 分块，每块 `u32 (csize | 0x8000)` + zlib 数据，16 字节对齐。
  便携包 `n2lnk.py`（只读：列表、解包、建索引）和 `n2verify.py`（逐块解压校验）按这个格式写。
- `[I]` 模型在 `MDLTEXPK`（EXARG 贴图包 + `G1M_PACK`）里，G1M 版本 `_M1G7300`（v0037）；贴图是 `GT1G`。另有 3133 个 `M$w$` 条目，内容经过混淆，没有解开。
- `[I]` 按帧分析里玩家装备的顶点数和解码后的顶点位置，在全部 G1M 顶点缓冲里做指纹匹配（`g1m_index.py` → `fa_match.py` / `findmodel.py`），**没有找到玩家装备**。
  推测它们在混淆的 `M$w$` 条目里。所以本项目不改归档，改走 3DMigoto 在绘制时替换（`rejected`：「从归档取出玩家模型、改写后重打包」）。
- 社区参考：aluigi 的 `nioh.bms`（归档格式）、mnbskysb/RDBExplorer-nioh2、Mawpius/3d-fixes（3DMigoto Blender 插件的仁王2 分支）。都没有完整的替换流程。

## 2. Mod Enabler 的挂钩合同

- `[I]` Mod Enabler 就是 3DMigoto：游戏根目录的 `d3d11.dll`、`d3dcompiler_46.dll`、`d3dx.ini` 和 `Mods\`。`Mods\` 下每个文件夹的 ini 都会加载；`F10` 重载，`F2` 开关全部 Mod。
- `[I]` **`TextureOverride` 只在被挂钩的着色器上按 IB 匹配。** Mod Enabler 的 `d3dx.ini` 定义了 `CommandListN2General`（主 pass）和 `CommandListN2Shadows`（影子，设 `$shadow_mode = 1`）。
  只有当前绘制的着色器有一个 `ShaderOverride` 去 `run = CommandListN2General`（或者是 Mod Enabler 自己挂了的影子着色器），这次绘制的 IB 才会去匹配各 Mod 的 `TextureOverride`。
  - 推论：要隐藏一个部件，画它的**每一个**着色器都要挂钩。KarinN2 的挂钩表 `[B]`：
    - 角色网格的 11 个像素着色器：`d0e492840a2b7911`、`2b4f1e31175e9cbc`、`1c66ca69cf2a610c`、`b2f60a9e522cd98f`、`d2bf49c8ea14806d`、`b28794540ed533bc`、
      `350aaed214d440c4`、`4687106fff835666`、`65c8c4905227d570`、`eec27fd8b62a555b`、`7ec4d7cd2e0f82ca`；
    - 布料挂件的顶点着色器 `24f9a3d0d0d9c367`（它的 PS `7bfcb1a8…` 不在上面的表里；影子里是 VS `c153883c…` / PS `006f69e7…`，由 Mod Enabler 的影子挂钩覆盖）。社区 Mod「Basewear No Flap」挂的也是这个 VS；
    - 两个影子顶点着色器 `cefcd0d8bb9cb78b`、`e91b4a26b8c1704e` 只用来设 `$kn2_shadow = 1 / 2`（`post` 复位），告诉宿主当前是哪种影子布局；
    - 脸的顶点着色器 `7439d16e62ebca1f` 只设 `$kn2_facevs = 1`，让眨眼计算只在脸的主 pass 运行。
  - 所有 `ShaderOverride` 都写 `allow_duplicate_hash = true`，和别的 Mod 挂同一个哈希时不互相覆盖。
- `[I]` **不挂全屏 pass 的像素着色器。** 全屏后处理（如 VS `f8978790…`）不绑新的 IB，沿用上一次的（见过马尾的 IB）。挂了它，`handling = skip` 会把后处理跳过，整屏变黑（build1）。
- `[I]` 帧分析（`F8`）时 Mod Enabler 跳过各 Mod 的覆盖，除非 `d3dx.ini` 里 `$dump_modded_meshes = 1`。要转储 Mod 自己的缓冲时临时打开，用完改回。
- `[I]` 开发时的设置：`hunting = 1`（叠加层、`F8`）、`export_shaders = 1`（把着色器反汇编写到 `ShaderCache\<hash>-vs.txt` / `-ps.txt`）、`analyse_options = deferred_ctx_accurate share_dupes`。
  `[Profile]` 里的立体显示项在测试机上会让启动卡住，开发时注释掉；交付前 `d3dx.ini` 恢复原版。
- `[I]` 每次启动，3DMigoto 都会请求管理员权限更新 NVIDIA 驱动配置（UAC「Windows 主进程 (Rundll32)」）。拒绝后游戏正常，左上角显示一会儿 `WARNING: Profile update failed!`。

## 3. 蒙皮常量缓冲与顶点格式

- `[B]` 身体蒙皮 VS `73278b6e442d3c47`，`vs-cb0` 共 781 行 float4：
  - 0–4：头部 5 行；
  - 从第 5 行起每个调色板条目 3 行（3×4 行主序，绑定空间 → 世界），共 K 个条目；
  - 接着是上一帧的同一套调色板（第 `5 + 3K` 行起，运动模糊 / TAA 用）；
  - 第 780 行 `.x` = K（`vmL2WLength`，int）；773–775 行是蒙皮开关（bSkin）。
- `[I]` 顶点 BLENDINDICES 是 u8 × 4，值为**条目号 × 3**，所以一个调色板最多 85 个条目。权重 f16 × 4。
- `[C]` Karin 宿主 A 的顶点 48 字节：+0 位置 f32 × 3、+12 权重 f16 × 4、+20 骨号 u8 × 4（× 3）、+24 法线 f16 × 4（w = 0）、+36 UV f16 × 2、+40 切线 f16 × 4（w = 副切线符号）。
  切线约定 `[I]`：T 沿 −dP/dv，`w · cross(N, T)` 沿 −dP/du。
- `[B]` 脸的 VS `7439d16e62ebca1f`：每顶点 8 个权重 + int16 骨号（同样 × 3），调色板 128 个条目；`vs-cb0` 798 行，`vmL2WLength` 在第 797 行。
  Karin 的脸用两个缓冲：vb0（24 字节：位置、法线，f32）可被眨眼着色器改写；vb1（144 字节：+0 权重 f16 × 8、+16 骨号 i16 × 8、+32 切线、+76 UV）。
- `[B]` 两个影子 VS 的 cb0 布局不同：
  - `cefcd0d8…`：0–3 行 W2P 矩阵，第 4 行起调色板，388–390 行蒙皮开关，共 391 行；
  - `e91b4a26…`：第 0 行光源，1–4 行 W2P，第 5 行起调色板，389–391 行蒙皮开关，共 392 行。
  影子里不能直接用主 pass 的合并调色板，要按各自的布局转一份（`merge_s1.hlsl` / `merge_s2.hlsl`）。
- `[I]` 渲染是延迟着色（7 个 G-buffer RT）。`[C]` 宿主绘制在主 pass 里换掉的 PS 贴图槽：身体和衣服 t0 颜色、t1 高光常量（`spec_a` = 10, 10, 10, 180，哑光）、t2 白图、t4 平法线；
  脸 t0 颜色、t1 / t7 两张从原版脸量出的常量（`refrough_b`、`artior_b`）、t3 / t4 平法线。影子 pass 只换 t0。法线贴图没有做，光照是近似的。

## 4. 宿主绘制与合并调色板

- `[C]` 装备界面（隼套装）主 pass 的护甲绘制，按顺序：左护胫 `f8e46d5e`、左护手 `b7ed5500`、袴 `39df894a`、胸 `091c8de0`、左围巾 `3acd6cdf`、右围巾 `6f1d0023`、右护胫 `ee8051c8`、右护手 `0814c08f`。
  每件护甲的调色板只含它自己蒙皮用到的骨；同一根骨在不同绘制里的条目号不同。
- `[I]` 全局骨号：在同一帧里，同一根骨在所有绘制里的 3×4 矩阵相同。按矩阵相等把各绘制的条目归并成全局骨号 `g<n>`（`bones.py`），再按加权中心手工标名（骨盆 g0、脊椎 g1、胸 g2、颈 g3、头 g8、大腿 g11 / g12 …，`n2_skel.py`）。
- `[C]` **宿主 A = 右护手** `0814c08f`。它的 `TextureOverride`：
  1. `handling = skip`（原版护手不画）；
  2. 主 pass（`$kn2_shadow == 0`）：拷贝自己的 `vs-cb0`；`MergeA` 计算着色器把 8 件护甲的调色板按全局骨号拼成两个合并调色板 A、B（每根骨取自携带它的那件护甲）；`Sim` 计算着色器把物理结果写进 B 的模拟骨；
  3. `vb0` 换成 Karin 的缓冲，`vs-cb0 = copy` 调色板 A，画身体、衣服两个 IB；切到调色板 B，画头发、耳朵、尾巴、裙子；最后 `vs-cb0 = ref` 还原。
  - 其它 7 件护甲的 `TextureOverride` 只 `handling = skip` + 在主 pass 里把 `vs-cb0` 拷进各自的资源。
- `[C]` **宿主 B = 原版脸** `834bff26`：用脸自己那次绘制的 128 条目调色板，Karin 的脸权重直接写成脸调色板的条目号，游戏的表情骨直接驱动她（[表情](FACE.md)）。
- `[I]` **帧对齐**：关卡里主 pass 先画右护手（宿主 A），再画其它护甲；装备界面里右护手最后画。宿主 A 拷到的其它护甲调色板在关卡里是上一帧的。
  - 修法：`Tick` 计算着色器带 `max_executions_per_frame = 1`，每帧把计数器加一；每件护甲拷贝 `vs-cb0` 后运行 `Stamp<i>`，把当前计数写进自己的槽。
  - `MergeA` 发现某件护甲的帧戳不是本帧，就用它 cb 里的本帧矩阵 C 和上一帧矩阵 P 按匀速外推一帧：`M = C · P⁻¹ · C`。
  - 跑动时头发（宿主 A）和脸（宿主 B，本帧）的偏差中位数从 8.3 cm 降到 0.5 cm；起跑、急停或动画卡顿的那一帧仍可能差 1–2 cm。
- `[I]` 一个 `TextureOverride` 里可以画多个 IB：每次 `drawindexed = auto` 之前换 `ib`、`ps-t0`、`vs-cb0`。两个调色板就是这样切换的。
- `[I]` 3DMigoto 1.3.16 的自定义资源：`type = Buffer / RWBuffer / RWStructuredBuffer / RWByteAddressBuffer`，`data =` 给初值（可带格式，如 `data = R32_UINT 0 0 …`）；
  `bind_flags = vertex_buffer unordered_access` 的 `RWByteAddressBuffer` 可以先被计算着色器写、再当 `vb0` 用，`stride` 在绑定时生效（眨眼的动态顶点缓冲就是这样）。

## 5. 影子 pass

- `[I]` 影子由 Mod Enabler 的 `CommandListN2Shadows` 匹配同一批 IB，所以隐藏和宿主绘制在影子里同样生效；宿主 A 的 `else` 分支处理影子。
- `[C]` 影子分支：拷贝影子的 cb0，按 `$kn2_shadow` 选 `MergeS1` / `MergeS2`（以及调色板 B 的 `MergeS1B` / `MergeS2B`），从主 pass 的合并调色板读 K（第 780 行）后按影子布局写一份，再画同样的 IB；影子里只换 `ps-t0`。
- `[C]` 影子分支读的是最近一次主 pass 拼出的合并调色板；影子先于主 pass 画时，它就是上一帧的。影子里没有看出错位。

## 6. 隐藏

- `[C]` `HIDE_IBS` 共 45 个 IB：原版角色的全部护甲、皮肤、脸的各部分、眼睛、嘴、头发；隼头带（头盔和面罩 `07e1d521`、`eeded2d0`）；
  4 个刚体护甲件（VS `d637f756…`，护膝等）；两片裆前布料挂件 `c03cb62d`、`dfeb63e0`（布料 VS）。其中 8 件护甲源和脸另有自己的覆盖段，其余 36 个是单纯的 `handling = skip`。
- `[I]` 武器（火绳枪、弓、长柄、弯刃、链、短刃）和腰间的小物件**故意不隐藏**：收起和拔出用的是同一个模型，隐藏了战斗时手里的武器也会消失。
- `[I]` 发型和脸也是按 IB 识别的：换成别的发型或脸，那次绘制的 IB 不同，原版发型会显示出来，Karin 的脸也不会画（宿主 B 不触发）。这是「长马尾 + 制作时那张脸」这个前提的来源。
- 一次被报告、没有复现的现象：build4 里用户看到「半透明情况下还是原来的形象」，随后自己说已经好了；没有改动，原因不明（`hypothesis`：某个半透明 / 抖动淡出用的着色器没被挂钩）。再出现时先抓那一帧，查画原版角色的着色器。
