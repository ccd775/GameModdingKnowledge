# Karin PT 项目案例

本文件保存本次项目的实测参数、关键转折和失败证据。它用于展示方法如何落地，不定义其他角色的固定标准。

## 1. 项目来源与目标

- 用户源模型：`Shared/Models/Optimized/Karin_PicodraTech/Karin_PT_Unified_Atlas.blend`
- 同目录 VRM：用于参考 VRChat/VRM spring 和 collider 意图
- 主要参考 Mod：`L4d2/ref/ccd_unendingFlame/`
- 项目目录：`L4d2/Karin_PT_L4D2/`
- 目标接口：Rochelle 世界模型、第一人称手臂与 HUD 路径
- 动画体态基准：Zoey 的动画/比例接口，同时保持 Karin 原始角色比例

项目详细证据仍以 `Karin_PT_L4D2/reports/`、`docs/SOP.md`、`PROJECT_STATE.md` 和候选 manifest 为准。

## 2. 骨架与比例

实测：

- source-to-target 映射 237 行；
- 最终目标 126 骨；
- 113 direct，124 ancestor-collapse；
- 58 根原生公共 bonemerge 骨；
- 最终 126 骨由 59 ordinary、61 JiggleRule、6 QuatInterp 组成。

一个 120 骨候选被判定为回归：6 根 procedural helper 被 StudioMDL 裁掉。修复不是盲目把骨名写回 QC，而是恢复 helper 的有效权重与 procedural 定义。

编译骨架与预期 rest skeleton 比较：

- parent mismatch：0；
- head RMSE：约 `0.0000056452 m`；
- tail RMSE：约 `0.00255822 m`；
- 最大端点误差：约 `0.0287159 m`。

## 3. 动画比例方案

最早结果出现缩头缩肩、上半身/腹部拉伸和角色体态明显偏离。根因是错误地把角色绑定/体态向原版 survivor 身体压缩。

最终方案：

- 保持 Karin/Picodra 同角色 rest skeleton 和身体比例；
- 公共 Valve 骨使用 Zoey 动画接口；
- reference SMD 使用 native Zoey local translations + Karin local rotations；
- target SMD 使用 Karin bind transforms；
- 用隐藏 autoplay delta proportion sequence 连接两者。

Karin 的 proportion target 仅对 pelvis 增加：

```text
2.750011 Source units = 0.05238770955 m
```

它是从地面接触测量得到的项目值，不可复制到其他角色。没有独立移动鞋、脚骨、网格、IK、bbox 或 ragdoll。

原生 sequence 接口保留 928 行 `$declaresequence`、924 个 unique 名，4 个有意重复；编译后 932 sequences。include model 顺序保持：

1. `survivors/anim_teenangst.mdl`
2. `survivors/gestures_TeenAngst.mdl`
3. `survivors/anim_producer.mdl`
4. `survivors/anim_gestures.mdl`

proportion sequence flags 为 1052，即 `HIDDEN | POST | AUTOPLAY | DELTA`。

## 4. 高跟鞋形态键

首个实机/预览问题是脚露出鞋子。`Foot_HighHeel` 虽在 8 个 mesh 上有同名 key，只有 `Body.003` 有非零 delta。

最终处理：

- 将有效高跟鞋 delta 烘焙到 Basis 和所有保留相对 key；
- 删除 `Foot_HighHeel`，避免二次应用；
- 1,886 个顶点变化；
- 最大位移约 `0.0305431835 m`；
- 59 个其他 shape key 保留。

该问题证明只枚举 shape key 名称是不够的，审计必须计算实际 delta。

## 5. 表情与权重

- 最终 face VTA：base + 30 个 flex frame；
- SMD 权重限制：每顶点最多三影响；
- 无未加权顶点、无缺失目标骨；
- 若 Blender face export 在完整写出 VTA 后卡住，使用结构化 VTA 重缩放并验证 frame 0。

## 6. 物理与附件

- 61 个 `$jigglebone` block；
- 15 个唯一参数 profile；
- 原生 Rochelle physics SMD 声明 79 节点；
- 18 个骨实际拥有 hull；
- 加入必要祖先后使用 21 节点、490 三角形；
- 最终 PHY 18 solids，每个一个 convex。

早期 physics 错位来自预变换顶点后又触发 StudioMDL named-bone bind conversion，即双重变换。最终让 StudioMDL 完成绑定转换，并验证同轮 checksum 与 HLMV overlay。

## 7. 材质与 Boomer bile

最终世界模型有 11 个 VMT。所有外露材质都通过：

```vmt
patch
{
    include "materials/models/survivors/survivors_it_shared.vmt"
    insert
    {
        // material parameters
    }
}
```

早期静态验证认为 bile include 正确，但用户实机截图显示头、耳和头发被 bile 覆盖，而大面积蓝色衣物没有。这把根因定位到只有衣物使用的 EmissiveBlend。

失败方案：

- `ClothA_Blue` / `ClothB_Blue` 使用额外 EmissiveBlend pass；
- 该 pass 不采样共享 `$detail`/IT；
- 参数职责还一度放反，使发光图按固定 flow 角落采样；
- 干净衣物颜色层在污渍之后叠加，视觉上盖掉 bile。

最终方案：

- 移除两个衣物材质全部 `$emissiveblend*`；
- 普通非透明材质用约 `(8,9,8)/255` 的低强度 SelfIllum mask；
- 两个作者 emission 灰度图映射为 `8 + round(source * 8 / 255)`，得到约 8..16/255；
- 透明材质保留正常照明例外，避免未证明的 translucent + SelfIllum 组合；
- 8 个全局低光 VMT + 2 个作者 mask VMT + 1 个透明例外；
- zero EmissiveBlend。

该最终材质候选先通过静态验证，随后由用户在 L4D2 中手工实机确认正常。确认覆盖本次修复目标：衣物能够接受 Boomer bile，SelfIllum 微光表现正常。对应候选为 `release/Karin_PT_Rochelle_ZoeyProportions_BileGlowSelfIllum.vpk`，SHA-256 `A201FA053507E16C441B85EEE57E54625A706A222E3D408F5288DFB3B7C1F39B`。这属于用户运行证据，不是自动化游戏测试，也不自动证明透明排序、第一人称手臂等无关项目。

## 8. VTF 构建

- 目标最大尺寸 2048；
- 生成 mipmaps；
- color + alpha 使用 DXT5；
- normal/emission 在本案例使用 DXT1；
- normal 黑色无定义像素先中性化，再 resize 与归一化；
- 使用 `invertgreen`；
- L4D2 VTEX 未按预期接受文本 `srgb` key，因此构建器对 VTF header sRGB bit 做显式补丁并记录变更 byte offset；
- 删除 VTEX 生成的 `.pwl.vtf`。

BaiduSync 曾在 VTEX 退出后继续锁住 VTF。构建器对删除和写回使用最多约 30 秒的有限重试。

## 9. Arms/HUD 与发布

Rochelle 目标路径：

```text
models/survivors/survivor_producer.*
models/weapons/arms/v_arms_producer_new.*
materials/vgui/s_panel_lobby_producer.vtf
materials/vgui/s_panel_producer.vtf
materials/vgui/s_panel_producer_incap.vtf
```

早期曾通过固定长度 `mechanic -> producer` token 替换直接复用同角色 Picodra arms，VVD/VTX byte-identical。用户指出这不满足“第一人称必须来自所提供 Blend”，因此该方案已否决，只保留为失败血缘证据。

最终 source-derived arms 从已验收 world SMD 按源 polygon manifest 抽取：`Body=9636`、`ClothA_Blue=2064`、`ClothB_Blue=6342`，总计 18,042 tris。参考 arms 只提供 55 骨 ABI、49 bonemerge、idle/proportion 动画及同角色权重指导。可见几何使用统一 similarity（scale `1.072`、offset `[0,1.43,0.14]` Source units），54,126 条 edge 局部非均匀 stretch 为 0；参考 SMD corners 按五位坐标去重/平均后的最近点权重沿源 topology 平滑 24 轮，再一次性 top-3，左右骨串零泄漏，triangle-corner L1 最大 `0.973790`。

最终运行候选为 `release/KarinPT_Rochelle_SourceArms.vpk`，33 payload、44,031,174 bytes，SHA-256 `D59B4B001AC2B63BF1E61A0E136BC8E6E9326DAE5AC99B8A30CE05FD270AA0CA`。它与废弃长名包 payload 完全相同；旧 14 件 `ko_komado_pt` 手臂材质完全删除。用户在 2026-08-14 确认短名、唯一副本、预启用和完整重启的组合修复后 Mod 能挂载并替换 Rochelle。该确认不自动覆盖所有武器动作、FOV 和肩口极限姿态，仍需逐项 smoke test。文件数是本候选实测，不是通用值。证据见 [Karin source-derived 第一人称手臂运行确认](evidence/karin-source-arms-runtime-confirmation-2026-08-14.md)，完整工作流见 [从角色源模型制作第一人称手臂](17-first-person-arms-from-source.md)。

最终三件 arms companion 的正向 SHA-256 为 MDL `8CA326BB03910BB919E489BFEE3B49161058DA3F6DDDEAEDD918F2DD34F3D65F`、VVD `9BBA6B0E747B6FD277B9981747EA62F2B6461EA9C2CDCB9368843B060D1CF2BD`、DX90.VTX `5F10FD88D66BB20BB05F73EB612FE6A1E509D602D78748B72D3B9C0B806E7D2C`。SourceIO 回读为 55 骨、11,620 compiled vertices、18,042 tris、三个项目材质、最多三影响；55 definebone、49 bonemerge、`idle`/`arml_proportions` sequence 合同与锁定 ABI 一致。HLMV 证据为 `reports/ui/hlmv-source-arms-final-smooth-front.png` 与 `reports/ui/hlmv-source-arms-final-smooth-angle.png`；它们只覆盖 front/angle 静态视角，不代表完整掌心、双腕口、肩口、背面或武器动作矩阵。

运行挂载反例也应保留：当 33/33 VPK payload、世界四件 companion 和 material closure 都正确，而游戏仍显示完整原版 Rochelle 时，先调查 addon 挂载/优先级/重启时序，不要重新做模型。Karin 的组合挂载修复已经用户确认有效，但缺少故障会话的 load-order 日志，不能把长文件名单独定为唯一根因。

## 10. 最重要的项目教训

1. 角色替换借用动画接口，不借用原版身体比例。
2. 脚穿鞋和脚落地必须分别诊断。
3. procedural helper 的保留需要权重和规则，不是仅有骨名。
4. StudioMDL 已做的 bind conversion 不要预做第二遍。
5. VMT 静态闭包无法证明额外 shader pass 会接受 L4D2 bile。
6. 用户实机截图是第一类运行证据，应反向推动验证器补洞。
7. HLMV 同名路径可能加载原版，必须使用唯一 alias 证明模型血缘。
8. 交付 VPK 必须由 manifest 和 payload 哈希证明来自本项目，而不是参考包。
9. Basis 烘焙修复只能解决 mesh/skeleton 整体错位，不能替代逐 edge 的 helper 映射连续性检查。
10. 第一人称几何进入 view space 时优先保持 triangle shape；权重转移后要沿源拓扑平滑，并量化角点权重连续性。
