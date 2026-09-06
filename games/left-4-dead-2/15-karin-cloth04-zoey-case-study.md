# Karin Cloth04 -> Zoey 案例

本文记录 `L4d2/cloth04_replace_zoey` 得到的可复用结论与个案参数。项目实测数字不得直接复制到新角色。

## 1. 项目来源与运行时迭代

- 用户源模型：`Shared/Models/Optimized/Karin_Cloth04/Karin_C4_Optimized.blend`，17 mesh、214 骨、56,816 顶点、10 材质、3 张 4096 图集。
- 同目录 VRM：`karin_c4.vrm`，VRM 0.x，31 个 spring group、11 个 collider group。
- 参考 Mod：`platinum 汎用04 1.12「zoey」.vpk`。它提供已工作的 Zoey ABI/动画/接口证据，但不含材质，不能视作通用角色 rest。
- v1.0 的实机截图显示侧发过摆、爆指、idle 双臂交叠。
- v1.1 把脸侧短发收紧到 `7.5 deg`，但第二轮截图仍显示爆指；light 扶栏杆 idle 看似左右手互换，因此 v1.1 也被实机否决。
- v1.2 改用 source-fit skeleton + no-LBS bind。正式 VPK 为 28,400,301 bytes，SHA-256 `2695036B9A35EC65E40ED7E3315DB85D0F6C6C3DDAE9BCE3BEA5F1C0D27157BF`，67/67 离线发布门通过；运行时状态保持 `pending_user_runtime_visual_test`。
- v1.2 随后的倒地截图暴露双马尾发根拉丝：手/指问题已消失，但双马尾首动态骨的 pivot 选在链远端。v1.3 改为 VRM path 0 支点并增加独立正负门；正式 VPK SHA-256 `B5931A9C17C16AAA54DE838C0C7EBEB659214CE71DF242A67ACE9AD98BD719B4`，73/73 离线发布门通过。2026-08-18 用户明确回复“验收通过”，因此 v1.3 在本任务验收范围内升级为 `user-confirmed pass`。

## 2. 最关键的根因：ABI 相同不等于 bind pivot 可复用

### 2.1 “左右手像反了”不代表 L/R 动画交换

本案例的第二轮截图很像左手跑到右手位置。逐层审计后，左右 clavicle/upperarm/forearm/hand/finger 的名称、index、parent、权重 side sign、原始 light 动画本地轨道都正确，没有 L/R swap。

真正差异在 bind：旧版把 Karin 几何绑定到 Platinum/Zoey 的 rest pivot。Karin 手/指带权几何质心相对这些 pivot 约低 `5..7 Source units`。动画本身正确，但它绕不属于该网格的支点旋转，于是手指呈放射状爆开，双臂也会在某些 idle 里横跨身体，看起来像互换。

通用诊断顺序应为：

1. 检查骨 name/index/parent 和 L/R side sign。
2. 检查原始动画 parent-local 轨道，而不是只看最终 global pose。
3. 计算每根 deform bone 的带权几何质心到 bind pivot 的距离，并与源模型对比。
4. 只有前两项真的显示交换时才改 L/R 映射；否则先修 bind pivot。

### 2.2 参考角色只锁 ABI 与旋转，不锁 pivot translation

v1.1 曾把“前 118 骨 rest 与成功参考一致”当成最终合同。第二轮实机证据证明这条假设过强：参考 Mod 的 rest 适合 Platinum 几何，不自动适合 Karin。

v1.2 source-fit target 改为：

- 保留全部 127 个骨名、顺序和父子关系。
- 保留前 70 个 Valve/interface 骨的 global rotation。
- 把 101 个有 Karin 源代表的 target pivot 放到经过统一 Source 换算后的源 bone head。
- 对源模型缺失的中间 spine 使用明确插值；未映射 helper 保留父局部 offset。

本案例最大 mapped pivot 误差为 `1.5503e-5 su`，前 70 global rotation 误差为 0。原则是“ABI/方向沿用目标游戏接口，旋转中心服从实际被驱动的网格”。

### 2.3 不要用全 LBS rebake 修 rest 不一致

曾评估把每个顶点从 Karin source rest 逐骨 LBS rebake 到 Platinum target rest。对于跨越多个骨、宽袖、服装和装饰三角，这不是刚体变换；本案例出现最高约 85x 的三角边长拉伸，因此方案被拒绝。

最终 bind 策略为 `none`：

- 所有 mesh basis 与 shape key 只做同一个 global similarity/Source 单位换算。
- 只重映射、合并、裁剪到 top 3 并归一化权重。
- 不对顶点做逐骨 rest rebake。
- 以拓扑边长不变作为硬门。本案例 17 mesh、150,257 条边，绝对/相对变化均为 0。

这个结论可复用：如果目标只是让游戏动画在源角色比例上工作，应先把骨 pivot source-fit，再用 proportion 轨道连接动画 rest；不要通过全模型 LBS 拉扯几何去迁就另一角色的 rest。

### 2.4 折叠 spring chain 时，代表骨必须是首动态段

双马尾每侧源链为一个静态锚 `Hair_tail_*__2` 加八个 VRM spring 段，但 Source 预算只给该链两个目标骨：静态 `HairBack_*_001` 与动态 `HairBack_*_002`。v1.2 以“保留控制 + 最大带权顶点数”为优先级，误选 path 6 的 `Hair_tail_*_007` 代表整个动态链。

这不是参数偏软，而是铰链位置错误：

- 错误动态 pivot 到静态锚约 `37.2468 su`；正确 path 0 `Hair_tail_*_001__2` 仅约 `2.07328 su`。
- 每侧 425 个根部共权过渡顶点到错误 pivot 的平均距离约 `35.7382 su`，改为 path 0 后约 `1.14953 su`。
- 旧版在正负 35 度 CPU skin 中，根部边最大伸长 `17.59x`，贴头皮顶点最大位移 `19.67 su`；正确支点加 v1.3 profile 后分别降到 `1.2291x` 与 `0.75263 su`。

因此 collapsed spring 的代表选择顺序必须是：VRM root/path position 0、与静态锚为 direct parent relation，然后才考虑带权顶点数。`jigglebone length` 只描述 Source solver 的模拟长度，不能把错误的 bind pivot 搬回发根；调低 stiffness、mass 或 angle 也不能从根本上修正远端铰链。

本案例保留两骨权重与 127 骨预算，不增加骨数。v1.3 对称 profile 为 `length=4.5872`、`tip_mass=10`、三向 `stiffness=100`、`damping=12`、`angle=20 deg`。world/light 的 38 条 JiggleRule payload 必须逐字段一致。发布门同时要求新候选通过，并要求 v1.2 负面对照失败，防止审计器恒通过。

## 3. Source proportions 的正确合同

锁定的原生 `anim_teenangst.mdl` parent-local rest 记为 `C`，source-fit target local rest 记为 `T`。v1.2 的公共 70 骨 translation corrective 为：

```text
delta.position = T.position - C.position
pelvis.delta.z += ground_lift
```

本案例 ground lift 为 `+0.733109 su`。70 个公共骨的 rotation delta 全部为 identity。成功参考的 translation 和 `L_Finger02/R_Finger02` 静态 rotation 只作诊断，不再是 Karin 的 hard gate。

这意味着对 Platinum 的绝对 rest/pose 严格等价必然为 false。正确动画门禁不是强迫两具不同 bind 的模型拥有相同 global pose，而是证明：

- L/R 名称、index、parent 与原始 parent-local 动画 ABI 保持。
- candidate proportions 能在编译量化容差内重建 candidate 自己的 bind。
- 动画相对各自 bind 的局部运动保持。

本案例 `compiled-light-animation-equivalence-sourcefit-v14c.json` 明确记录 `strict_reference_equivalence.accepted=false`、`relative_to_bind_motion_contract.accepted=true`。约 `0.5236 rad` 的 R_Finger02 差异是 source-fit identity profile 与 Platinum 模型专用静态 correction 的差，不是原始动画 rotation ABI 失败，更不是 L/R swap。

## 4. Interface 必须随 source-fit pivot 重新表达

### 4.1 Attachment

attachment 的本地 position 是在父骨 bind frame 中定义的。父骨 global rotation 虽保持，pivot translation 已变化，直接复制 Platinum 本地值仍会漂移。本案例旧值最大 global drift 为 `6.641827 su`。

正确做法是保留参考 attachment 的 global bind point，再用 source-fit parent 的逆矩阵求新 local position。30 个 attachment 重表达后的最大 global position error 为 `7.63e-6 su`。生成的 interface QCI 必须替换旧 block，不能与旧 attachment 并存。

### 4.2 Hitbox

hitbox 从最终 source-fit Blend 的身体几何重新拟合。本案例只允许 `Body`、`body_2`、`underwear`，排除头发、耳、尾、袖、裙摆和装饰；最终仍保留原生语义的 17 个 hitbox/hitgroup。

通用规则不变：按最近祖先上卷所有配饰顶点会把双马尾卷进 head、尾巴卷进 pelvis，造成远离身体也能受击。

## 5. Light 动画审计要区分绝对等价与 bind-relative 等价

light 包含 TeenAngst、ragdoll 和 DLC intro 等本地序列。source-fit 改了 bind translation 后，直接逐帧比较 candidate 与 Platinum 的 global position 必然出现数个 Source units 的差；这不是充分的失败证据。

应同时保留两类结论：

- strict reference comparison：诊断用，预期 false，用来量化 bind/profile 差异。
- relative-to-bind motion contract：发布 hard gate，检查九条原始动画的 parent-local ABI、proportion bind 重建和 bind-relative translation。

不要删除 strict false，也不要把 bind-relative true 改写成“与 Platinum 完全相同”。两者共同说明模型有意使用不同 bind，但仍消费相同游戏动画接口。

## 6. HLMV 失败不是姿态证据

L4D2 HLMV 直接加载旧 v1.1 和新 source-fit world/light 时，都在 `studiorender.dll` 同一位置异常退出，观察到 `0xc000041d` / `0xc0000005`。因为旧、新都复现，不能归因于 source-fit，也不能据此声明姿态通过或失败。

本案例改用 compiled MDL 解码、CPU skin、关键骨 pivot 距离、指骨段长度、三角形变形和 bind-relative 动画作为离线证据，并明确标记为 offline validation。最终报告 5/5 通过并生成 8 张非空姿态图；最终仍由用户在游戏中复测，任何 HLMV 截图、Blender 渲染或 CPU skin PNG 都不能冒充游戏实测。

后续用户已完成 v1.3 验收，追加证据见 [Karin Cloth04 Zoey v1.3 用户验收](evidence/karin-cloth04-zoey-v1.3-user-acceptance-2026-08-18.md)。发布 manifest 中的 `pending_user_runtime_visual_test` 是打包时快照，保持不变；运行确认通过 sidecar 追加。该反馈不应扩写为所有武器、FOV、地图和材质组合均有逐项矩阵。

## 7. 其他可复用规则

### 7.1 Crowbar `$definebone` 角度顺序与 SMD 不同

同一根骨，Crowbar QC 与 raw SMD skeleton rotation triple 的字段顺序不同。对本工具链
逐骨交叉验证后的换序为：

```text
QC $definebone (rx, ry, rz) == SMD skeleton (ry, rz, rx)
```

SMD 使用 radians，QC `$definebone` 使用 degrees。例如 Pelvis 的 SMD rotation
`(1.570796, 0, 0)` 对应 QC `(0, 0, 89.999982)`。需要 rest 数值时优先读反编译
SMD，并用趾尖高度、髋部高度等几何常识校验。v1.2 的最终 127 `$definebone` 直接从
source-fit target SMD 生成，避免从 QC 反推；生成后仍应从 compiled MDL 做 rest
roundtrip，不能只相信换序公式。

本案例文档早期曾把公式误记成 `(rz,rx,ry)`；该写法与实际
`generate_world_physics_contract.py`、原生 Hunter Crowbar QC/SMD 和已验收编译结果
冲突，已于 2026-08-18 纠正。不要从旧对话或缓存摘要恢复错误公式。

### 7.2 自生成 SMD 要防自反馈

物理/hitbox 拟合脚本读取 `*.smd` 时必须排除自己上一轮写出的 `physics.smd` 与 skeleton-only reference，否则盒体会逐轮长大并固化错误。

### 7.3 L4D2 vtex 没有 `dxt1` 键

24-bit TGA 默认编成 DXT1；需要 alpha 时才用 `"dxt5" "1"` 与 `"numchannels" "4"`。在 VTEX `.txt` 写 `dxt1` 会直接报 unsupported option。

### 7.4 图集名不证明 Alpha 存在

`*_Alpha` / `*_Transparent` 只是命名。本项目三张 color 图集的 alpha 全为 255；错误启用 `$translucent` 会让整片面出现问题。应以图集字节为准并记录缺失通道。

### 7.5 编译沙盒依赖不能进入 addon

隔离 StudioMDL 需要 `$includemodel` 对应的 MDL/ANI 和 `survivors_it_shared.vmt`，但这些都是游戏本体资产，只能进入编译沙盒，必须被最终 VPK denylist 拒绝。

## 8. Cloth04 v1.3 个案参数（不可复制）

- 缩放：`52.49343832020997 su/m`；ground lift `+0.733109 su`。
- world/light skeleton：127 骨；101 mapped pivot；前 70 global rotation 保持。
- bind：`mode=none`，17 mesh、56,816 顶点、95,300 原始三角；最终 world 源 74,364 三角。
- proportions：70 公共骨 `T-C+ground`；70 骨 rotation identity；Platinum strict equivalence false。
- world/light：LOD0 57,221，VTX 完整覆盖；30 attachment、17 hitbox。
- 动态：38 JiggleRule + 2 QuatInterpRule；`HairS1/HairS3=7.5 deg`，`HairBack_L/R_002=20 deg`，其余 34 根 `35 deg`。双马尾首段 profile 为 `length 4.5872 / mass 10 / stiffness 100 / damping 12`。
- world：70 bonemerge、30 flex rule、950 sequence、16 PHY solid。
- light：70 bonemerge、11 条有序本地 sequence、无 PHY、无 includemodel；bind-relative animation accepted。
- first-person arms：8,400 Cloth04 派生三角、53 骨、49 bonemerge、LOD0 5,346、VTX 5,346/5,346、参考可见几何重合 0。
- 材质：10 VMT + 7 VTF；低亮 mask 为 64x64 常量 `(8,9,8)`；未实现独立 Source eyeball。
- v1.2 -> v1.3 expected-change allowlist 恰为 8 个 entry：`addoninfo.txt`、world MDL/VVD/VTX/PHY、light MDL/VVD/VTX。arms、17 件材质、3 HUD 和 addonimage 哈希不变；world checksum 改变时 PHY 即使 hull 未改也随 companion family 同轮替换。

## 9. 最重要的教训

1. “动画看起来左右反了”先审计 bind pivot，不要直接交换 L/R。
2. 成功参考的 ABI 可以复用，角色专用 rest translation 不能未经验证照抄。
3. 让骨架贴合网格通常比用全 LBS 把网格拉到另一骨架更稳；拓扑边长是很有效的否决门。
4. source-fit proportions 应围绕 candidate 自己的 bind 审计；strict reference false 与 bind-relative true 可以同时成立。
5. attachment/hitbox 是 bind-space 接口，pivot 变化后必须重新表达/拟合。
6. 离线工具崩溃或离线渲染都不是游戏实测；发布时 pending 与发布后用户确认应保存为两条有序证据，不回写历史 manifest。
7. 折叠多段 spring chain 时，代表骨必须锁定首动态段；按带权顶点最多选择远端控制会制造长力臂和发根拉丝。
