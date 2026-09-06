# Karin SelfIllum 修复用户实机确认

## 结论

2026-08-08，用户在当前 Mod 制作任务中明确反馈：

> SelfIllum 修复方案我测过了，正常，可以写入知识库。

据当前任务上下文，该反馈对应以下修复候选：

- VPK：`release/Karin_PT_Rochelle_ZoeyProportions_BileGlowSelfIllum.vpk`
- 大小：`64,840,249` bytes
- SHA-256：`A201FA053507E16C441B85EEE57E54625A706A222E3D408F5288DFB3B7C1F39B`
- Loose tree：`work/release_zoey_bile_selfillum_final/game/`
- Payload：47/47 与 loose tree 逐字节一致

## 被确认的修复

失败候选的 `ClothA_Blue` 与 `ClothB_Blue` 使用 EmissiveBlend 额外 pass，用户实机观察到头部、头发和身体能显示 Boomer bile，但大面积蓝色衣物保持干净。

修复候选完成：

- 删除两个衣物材质的全部 `$emissiveblend*` 参数；
- 继续通过 `survivors_it_shared.vmt` 接收 Boomer bile；
- 改用标准 VertexLitGeneric pass 内的 `$selfillum` 与独立 `$selfillummask`；
- 将作者灰度 emission 映射到 `8..16/255`，同时保留低亮度背景和作者发光区域。

用户的“正常”确认将以下项目记为 `user-confirmed pass`：

- 衣物接受 Boomer bile；
- SelfIllum 微光表现符合预期；
- 修复没有继续出现此前 EmissiveBlend 覆盖干净衣物的问题。

## 证据边界

- 这是用户手工 L4D2 实机反馈，不是自动化游戏测试。
- 当前消息未附带新的截图或录像，因此证据形式为用户明确书面确认。
- 该确认针对 SelfIllum 材质修复，不自动覆盖透明排序、所有光照极端情况、第一人称手臂、动画或物理。
- 其他角色即使使用相同公式，也必须重新验证自己的 UV、底图、遮罩、透明组合和游戏表现。

## 关联证据

- `L4d2/Karin_PT_L4D2/reports/release/zoey-bile-selfillum-fix-lineage-audit.md`
- `L4d2/Karin_PT_L4D2/reports/materials/material-build-boomer-selfillum-final.json`
- `L4d2/Karin_PT_L4D2/reports/materials/material-output-validation-boomer-selfillum-final.json`
- `L4d2/Karin_PT_L4D2/reports/runtime/user-boomer-clothing-emissiveblend-failure.png`
- `L4d2/SharedKnowledge/06_materials_vtf_boomer_glow.md`
