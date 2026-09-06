# HD2 资源与导出合同

> 置信度：AQ whole-unit swap、mesh coordinate serialization、triplet 结构来自工具源码和多轮 roundtrip，属于 `format-confirmed`；具体 Unit 数量、FileID、draw 范围属于 `case-specific`。

## Patch triplet

HD2 Mod 资源以同 stem 的三文件工作：

```text
<archive_id>.patch_<index>
<archive_id>.patch_<index>.gpu_resources
<archive_id>.patch_<index>.stream
```

三者是一个原子发布单元。`.stream` 可以是合法的 0-byte 文件，不能因为为空而省略。任何缺少 companion、stem 不一致或成员改名都会破坏合同。

### patch index

- index 是安装位置，不是版本号真值。
- Mod Manager 可以在安装/启停时重排 index；已安装版本必须以同 stem 三件套的大小和 SHA-256 识别，不能以包内原编号识别。
- 新部署选择未占用且高于当前同 archive 最大值的 index。
- 不覆盖旧 index，不根据历史记录猜测 live 文件仍存在。
- 发布包内 index 与报告、成员哈希、回滚路径绑定。

## 资源类型与引用闭包

角色替换通常至少包含：

- `Unit`：网格、LOD、transform/bind、局部骨调色板和材质 section。
- `Material`：child 参数、parent 引用和 TextureMap 引用。
- `TextureMap`：DDS payload 与采样元数据。

最终闭包必须满足：

```text
model material reference
  -> local private child Material OR known stock parent contract
  -> every local TextureMap exists in final archive
  -> no unintended donor-local child/texture ID remains
```

只允许已知 stock parent 作为外部引用。本地 child Material/TextureMap 必须私有化，避免与另一 Mod 在同一 archive namespace 中按加载顺序互相串贴图。

## 目标 Unit 是全局资源，不是套装内私有实例

- `project-proven` 军械库中的两个套装名称可能消费同一个 Unit FileID；应先建立 `armor kit -> body type -> equipment role -> Unit FileID` 图，再按完整 FileID 去重编译。
- `project-proven` 一个 Unit override 会影响该 FileID 的全部消费者，不能按当前 armor kit 条件化。报告必须同时列主要目标和连带消费者，运行时矩阵也覆盖后者。
- `project-proven` “两个套装素材复用”只有在消费者图和目标 FileID 相同后才能成立；外观相似、文件名相似或 RawMesh 字节相同都不足以合并目标。

DR03 的 CM-10/EX-00 路线通过共享 Unit 一次覆盖多个消费者，同时发现其他 armor kit 也复用 hips undergarment。方法与 blast-radius 证据见 [DR03 案例](case-studies/Karin_DR03_CM10_EX00.md)。

## AQ whole-unit donor swap

AQ Modified 2.4.3 的已确认导出语义不是“目标 Unit + 新 RawMesh”。流程是：

```text
Z_ObjectID -> load complete donor Unit entry
replace donor RawMesh/sections using Blender objects
save complete donor entry
rewrite output FileID to Z_SwapID_N target
```

因此最终目标 ID 携带 donor 的：

- TransformInfo
- BoneInfo / local palette
- MeshInfo transform
- inverse bind
- material-section/draw structure
- 其他 donor entry 元数据

### 实际影响

1. donor 选择决定骨架和运行时变形合同，不能只按外观挑选。
2. `Z_ObjectID` 必须指向已证明可运行且结构兼容的 donor Unit。
3. `Z_SwapID_N` 只负责最终目标 FileID；不要误以为 target bind 会自动保留。
4. 编译后必须验证这些字段的 provenance，不能只检查 target ID 和顶点数。

## 多目标同外观：两种合法 lineage，不能混用

多个装备目标使用同一外观时，先决定最终序列化 Unit 的 bind 来源：

### A. 保留 target-native profile

适用于 Slim/Stocky、槽位或动画合同确实不同，且每个 target-native Unit 已被证明与 authoring 几何相容的情况。每个 profile 独立推导 palette、分件 seam 和权重，并分别编译；几何相同不能替代 bind 兼容证明。

### B. 按角色使用完整 carrier 并克隆

适用于多个目标应获得完全相同的几何、坐标和绑定，而 target-native `TransformInfo/BoneInfo` 不同的情况：

```text
one proven complete carrier per logical role
-> compile every positive LOD exactly once
-> save/reload and lock TransformInfo + core bone bind
-> clone complete serialized Unit payload to target FileIDs
```

- 克隆必须携带完整 Toc/GPU/Stream payload，只改 entry FileID；不能只复制 RawMesh。
- 同角色全部目标的完整 payload 唯一哈希数必须为 1。
- 编译前后锁 `TransformInfo`，以及 `NumBones + RealIndices + inverse-bind matrices` 组成的核心 bone-bind signature。
- AQ 可因材质 section 重建 BoneInfo remap；应对 remap 建允许列表，不能把整个 BoneInfo 哈希变化自动解释成 bind 变化。
- body、helmet 等角色可使用不同完整 carrier；carrier policy 按角色声明。
- owner 的 header、TransformInfo、BoneInfo、MeshInfo、inverse bind 与 culling 必须作为一个 lineage 保存/回读；不能从多个 Unit 拼出看似可序列化的混合容器。
- 每个 owner RawMesh/LOD 使用自己的实际 `MeshInfoIndex` 与 `DEV_BoneInfoIndex`。不要因当前合同恰好常见 `LOD0=M3/B0` 就硬编码到新 donor。

Umbrella v1 把相同几何分别写入 RS6/RS67/RS100 的 target-native Unit，运行时出现全身、肩胯和头盔分离；v2 改为按角色编译一次并克隆完整 Unit。v2 仍待运行时验证，方法和反例见 [Umbrella 案例](case-studies/Karin_Umbrella_RS6_RS67_RS100.md)。

SSF v3 也把同一肩臂几何写入缺少 shoulder 语义的 target-native torso，并用 clavicle fallback/覆写掩盖不兼容；v4 改为六个 DS42 body owner 分别编译一次、完整克隆到 FS37/SC15 后获用户运行时验收。该案例为 complete carrier-per-role 路线增加了正向运行时证据，见 [SSF 案例](case-studies/Karin_SSF_FS37_SC15.md)。

## Authoring 对象合同

在 O44/New_SR24 路线中已验证的合同：

- `LegacyWeightNames=True`。
- 顶点组为局部 palette 名 `0_N`，而非任意全局骨名。
- 每个导出对象/材质 section 的 `0_N` 要按该 donor Unit 的 BoneInfo 显式映射。
- 网格不依赖 Armature Modifier 参与导出。
- object transform 为 identity。
- 顶点位于 donor mesh-local 坐标。

这是一个可复用模式，但新 donor 仍需回读验证，不能假设所有插件版本和所有资源完全相同。

## 坐标空间

AQ 的 `GetMeshData` 路径会直接序列化 `mesh.vertices[].co`，不会自动应用 Blender object matrix。与此同时，Unit 的 MeshInfo transform 和 inverse bind 仍按 donor/目标资源合同工作。

### 常见错误

```text
armature-space/world-space vertex
  -> directly written as mesh-local
  -> runtime MeshInfo transform applies again
  -> whole model offset, stretch, limb displacement
```

### 正确做法

明确记录每条变换：

```text
source object local
-> source armature/world
-> optional global rigid/similarity transform
-> donor armature
-> inverse donor mesh-to-armature
-> donor mesh local written to vertices.co
```

对刚性验证使用齐次矩阵，分别检查位置、方向、尺度、行列式和反射；不要只比较 bounds。

## Unit 的局部骨调色板

同一全局语义骨在不同 Unit/material 中可能对应不同 `0_N`。必须以每个 Unit 的 BoneInfo 解析，不得建立一次全局 index 表后套用所有对象。

每个导出对象验证：

- 所有顶点组都能解析到本 Unit palette。
- 未使用/未知组没有非零权重。
- 每点 influence 数不超过目标格式上限。
- 权重归一并在 float32 序列化后仍满足容差。
- 左/右骨不跨侧污染。

### 跨 Unit seam 的 palette 交集与自然权重

当 Torso/Arm、Torso/Hips 等对象复制了同一坐标边界时，共享权重语义必须同时存在于最终序列化 lineage 两侧的所有 Unit 和所有 LOD：

```text
shared_palette(profile, seam)
  = intersection(all participating final-lineage Unit/LOD semantic palettes)
```

- 保留 target-native profile 时从各 target/profile BoneInfo 求交；完整 carrier clone 时从参与接口的 carrier role/LOD BoneInfo 求交。两种 lineage 不能混用。
- 不从参考 Mod 直接复制某个骨名；参考只提供方法，骨名由当前最终 lineage 的 BoneInfo 决定。
- 不把所有 Slim/Stocky 先压成一个全局最小交集。若各 profile 的合法交集不同，只复制受影响的 authoring role，并为每个 profile 编译自己的权重；几何、UV、法线和材质仍可冻结为相同。
- 报告语义点/边数量、每 profile 的逻辑 face coverage 和实际序列化行数。物理对象复制不等于重复消费源面。
- 编译后将 local bone index 经实际 BoneInfo `RealIndices` 还原成语义骨名，再验证两侧完整权重行；不能比较跨 Unit 的裸 `0_N` 数字。
- 在任何 shared-bone override 之前，必须让接口两侧分别通过预定 final-lineage projection，并报告自然完整权重行的逐点误差。自然误差已为 0 时，默认保留原权重；不能为了“更整齐”再锁成单骨或添加固定过渡圈。
- 很大的 `max_weight_error_before_override` 是 palette/lineage/投影合同失败，不是允许覆写的理由。after-override 误差为 0 不能抹掉 before-override 报警。
- 若 target-native 容器缺少 Ref 已证明必需的 shoulder/thigh 等语义，应先检查是否选错 final lineage；不能立即把缺骨语义降级到 clavicle、chest、knee 或 root。
- 每条 seam 独立决定是否需要 post edit，并记录理由、骨名、点数与 before/after 误差。某一肩缝天然正确，不代表腰髋也天然正确；某一腰缝需要共享骨，也不授权改写肩缝。

DR03 中 Slim 使用 clavicle、Stocky 使用 chest，是由目标 palette 交集产生的 `case-specific` 结果，不是通用骨名表。

## Rest pose 与 inverse bind

中立蒙皮的基本关系应近似：

```text
rest_global[bone] * inverse_bind[bone] = identity
```

但这只证明内部中立自洽，不证明游戏给出的外部驱动矩阵与自定义 rest 相容。任何 rest 修改必须同时验证：

- 每个 Unit/local palette 的 inverse bind 重算正确。
- 相关父子骨 origin 和 basis 连续。
- donor 源、编译 Unit 与外部运行时 skeleton 合同一致。
- 真实或可证明的外部姿态不会产生剪切。

逐骨复制另一个角色的 origin 往往在多权重边界产生 `sum(weight * origin_delta)` 型 LBS 剪切；不要把 neutral identity 当充分条件。

## LOD 与 Slim/Stocky

- 参考 Mod 可能让 Slim/Stocky payload 逐字节相同，但目标 FileID 仍必须分别覆盖。
- 复制 LOD 可以暂时优先保证形体一致，但有性能成本，必须披露。
- 真 LOD 优化是独立任务，需重新做 topology、weights、draw、AQ roundtrip 和运行时切换门禁。
- 每级 LOD 都要验证 section start/count、material ID、vertex stride、UV 和 palette，不能只看 LOD0。
- 可见角色的每个实际正 LOD 都必须承载可见且语义正确的材质。不能把 LOD1-LOD3 换成 suppression glass；若临时复制 LOD0，需披露性能成本并逐 LOD 回读。

## 装备槽与接口归属

角色由多个可组合槽构成。桥接几何必须放在始终存在的所属身体槽：

- 颈口 bridge 放在 Helmet 时，换原版/其他头盔会消失。
- 腹部 bridge 若跨 Torso/Hip 分属两个动画语义，可能形成环状断层。
- 隐藏/suppression Unit 若未覆盖，旧衣服、外套、裤袜或鞋可能重新出现。
- 完整头部若被编入 armor/body，而 Helmet Unit 被 suppression，会出现“穿盔甲时有头、单独头盔槽为空”。

`project-proven` 源面必须按实际消费者槽位建立唯一 ownership：每个源面恰好出现一次，可见角色之间不重复，可见 Unit 与 suppression Unit 集合互斥。对完整角色替换，头、脸、发、耳与头饰通常应由实际 Helmet target 消费；Torso 只持有身体侧几何。具体对象清单和 target FileID 是 `case-specific`，必须从当前 customization/manifest 与参考 Mod 重新测量。

验证接口不只检查“面存在”，还要检查：

- 最终编译 Unit 的顶高/底高。
- head/neck/torso anchor 相对位置。
- 合理重叠量与动画下 seam 距离。
- 原版和至少一个其他自定义可组合装备。

## Material section 与 draw contract

每个 LOD 的 section 合同包含 material ID、start index 和 index count。材质 ID 正确但 start/count 错一处，可能造成：

- 刘海消失或采错材质。
- 一部分身体落入 gore/透明 section。
- 越界、漏面或不可预测渲染。

draw 数值必须从当前序列化 Unit 测量并锁入项目合同。New_SR24 历史上的 `54879` 与 `54882` 差异说明：不要把旧脚本中的 magic number 沿用到新几何。

## Suppression Unit

`project-proven` 隐藏原生装备应作用于可渲染几何，而不是只把原材质替换成透明、alpha-zero 或 glass。shader 仍可能产生 base opacity、specular、refraction 或排序效果；Karin Nyako RE2310 的运行时反例显示这种做法会留下蓝色透明塑料叠层。

隐藏叠加槽可使用经过验证的极小退化/塌缩 Unit，或经当前工具链证明的 zero-draw section，但必须：

- 与目标槽和所有 LOD 一一对应。
- 正 render LOD 与 culling LOD 分开处理；不要把 culling body 当可见几何一起压缩。
- 保留目标 Unit 的 customization header、TransformInfo/BoneInfo、MeshInfo/LOD 结构、palette、indices、section 和原材质合同，除非另有逐字段证据。
- 只把正 render LOD 的 position stream 收缩到确定性微型占位，并回读有限值、权重、bounds 与 section。
- 有合法格式、palette、section 和 bounds；正 draw section 不得依赖所谓 suppression glass。
- 在运行时确实不可见且不崩溃。
- 保持为冻结 payload，不在后续可见模型修复中重新生成。

`case-specific` Karin Nyako RE2310 v5 使用 `1e-6 m` 级占位，离线硬门为每轴 `<=2e-5 m`，覆盖 12 个 suppression Unit 的 48 个 render LOD。该数量和阈值只证明该案例；新目标必须从参考占位、浮点精度、culling 与运行时结果重新校准。

最终包不能额外包含参考 Mod 的旧子目录/多组 patch，因为它们可能以更高优先级重新覆盖 suppression 目标。

## AQ roundtrip 的边界

AQ `Unit.Save()` 可能规范化 offset 或 material-slot 元数据。因此：

- Unit 的通用验证采用 load-only + 独立语义/provenance 检查。
- 不把每个 Unit 的 load-save 字节完全一致设为无条件格式真值。
- Material/TextureMap 在当前工具链中可做适用的 load-save 检查。
- 最终 triplet 仍应做整档 roundtrip 和 payload identity，但要明确比较层级。

报告应区分：

```text
semantic equality
serialized field equality
resource payload byte identity
whole triplet byte identity
```

四者不能互相替代。
