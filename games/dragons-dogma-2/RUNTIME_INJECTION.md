# 运行时注入：只把玩家构建成 Karin

钩子名、字段名、状态值是 `build-sensitive`（TU3.2 / 2026-10 两个 build 相同）；做法是 `invariant` 级经验。
脚本见便携包的 `reframework/karin_replacer.lua`。

## 1. 方案选择

| 方案 | 结论 |
| --- | --- |
| 直接替换 `body_000_f.mesh` + 清空装备网格 | `rejected`：所有同性别 NPC 都变成 Karin，所有人的装备消失 |
| 自定义 part prefab + catalog 条目 | 需要新的 TU3.2 RSZ 模板，未做 |
| v1.0–v1.1：运行时在活角色上 `setMesh` + 重绑 joint 缓存 | 可用但有引擎侧残余崩溃（冷启动约 1/5），已被取代（§4） |
| **v1.2 起：游戏构建身体时递入 Karin 资源** | 现行；多次冷启动、重读档、压力测试 0 异常 |

## 2. 游戏自己的换身体流水线

读档、换区域、菜单 mockup 都走同一条：

`app.PartSwapper.swapBodyMesh` → `CharacterEditManager.requestBodyMesh` → 回调
`<swapBodyMesh>b__198_0(Dictionary<PartsInstantiate, SwapInfo>)`。`SwapInfo.Parts` 是临时部件 GO（如 `body_000_f`），
带 `app.PartSwapMeshHolder{_Mesh}`，由它的 `swap(via.render.Mesh 目标)` 把网格放上角色；皮肤材质同理（临时 GO
`body_runtime_human`，`app.PartSwapMaterialHolder{_Material}`）；chain 走 `app.PartSwapper.setBodyChainAsset(ChainResourceHolder)`。
之后游戏按新网格骨架建立 joint 表，重绑、物理、IK、动画全部自己完成。

## 3. 注入点与规则

1. **`PartSwapMeshHolder.swap` pre-hook**：目标 GO 名为 `ch000000_00`（玩家）或 `MockupModel_ch000000_00`（菜单模型），
   且 holder 当前网格路径以 `Character/_kit/body/` 开头 → `holder._Mesh = Karin`。
2. **`PartSwapMaterialHolder.swap` pre-hook**：路径以 `AppSystem/CharaEdit/ch000/Material/Runtime/body_` 开头 → Karin MDF。
3. **`setBodyChainAsset` pre-hook**：目标身体已是 Karin 网格，且参数是原生 `body_chain.chain` → 换成 Karin chain。
   Karin chain 需要她的骨，绝不能留在原生身体上。
4. **皮肤烘焙改道**（§5）与**体型编辑表清空**（§6）。
5. 运行时只做廉价维护：Karin 可见组 0..7 打开、原头部关闭、隐藏掩码 8191（hook `set_HideSwapObjects` 防止游戏改回，
   并记下游戏每次想要的值，以便原地重建为原生身体时还回）。

细则（多数来自审查发现）：

- **每次构建一个决定**：网格和材质两个 hook 相隔毫秒、顺序不定，必须共用一个决定（按目标 GO 地址，每种 hand-over 各用一次，
  下一次同类 hand-over 开新决定；2 s 只是兜底）。否则选项或资源就绪状态在两者之间变化时，会拿到「Karin 网格 + 原生材质」。
- **只替换女性人类**：体型取玩家 `PartSwapper:get_Meta()` 的 `_Gender` / `_Species`。网格路径只分男女、皮肤路径只分人 / 兽人，
  两个 hook 各看一半会漏。菜单模型的 `get_Meta()` 经 REFramework 读不出（「not a managed object」），它就是玩家本人：
  玩家身体当前是 Karin 时才替换。
- **holder 字段只在 `swap()` 期间是 Karin 的**：post-hook 在字段仍是她的时放回原值（用 `thread.get_hook_storage()` 传递），
  部件释放的正好是它自己的资源。**不要**对她的 holder `add_ref()` / `release()`：实测下一次构建时报「not a managed object」。
- **资源就绪**：在标题画面 `sdk.create_resource` 创建，5 s 后才递出（引擎没有就绪查询，只能按时间）；构建发生在窗口内则保持原样并记日志。
  递出前确认她的 holder 仍是活的托管对象，否则重建（这一次构建保持原样）。
- **失败即关闭**：两个 holder hook、`bakingProcessing` / `build` / `setupApplyEditScales` hook、枚举名、用到的每个字段、`get_Meta`、
  hook storage 任一缺失 → 不递出 Karin，日志列出缺哪项。
- **开关在下一次构建（读档）时生效**，不在活角色上切换。
- 第二个 Mod（Original）的脚本由生成器从同一份源码改名、改路径、改全局表名生成；两个脚本都装时后装的闲置（互斥）。
- 帧内顺序（`via.ModuleEntry`）：UpdateScene 183 < BeginPhysics 192 < UpdateBehavior 245 < UpdateMotion 261 < EndPhysics 329。
  从 UpdateBehavior 起物理 / 动力学 / 动画作业已在工作线程上读 joint；**改骨（表情、链回位）放在 UpdateScene 前**。

## 4. v1.1 的运行时 `setMesh` 路线（已取代，教训仍有效）

- `setMesh` **总会**重建 joint 表并释放旧 `via.Joint`（骨架相同也一样；原版男→女互换也崩）。游戏脚本缓存了约 150 个
  joint 引用（对话手势的手部 IK 首先崩）。
- 通用重绑：从根 GO **及全部子孙 GO** 的组件出发，最深 5 层，跟单个 `app.*` 对象，也进 `List<app.X>` / `app.X[]`
  （每个 ≤ 4096 元素），收集 `Owner == 根 Transform` 的 joint 槽位（实测 464 个槽位，约 250 个在容器里：IK 预设、动画控制器、
  脚锁、攀爬肢体 IK、道具缩放……；14 个在子物体上：箭矢显示、视觉标记、头顶 UI 锚点、草地传感器）。
  - 换前**原样写回并读回**每个槽位，证明每个都写得进去；**不要**先写别的 joint 再写回（上一帧的作业可能正在读）。
  - 写法：字段 `set_field`；`List` 用 `set_Item`；**数组只能 `arr[i] = j`**（`Array.SetValue` 返回成功但不写）；
    **结构体元素是副本**：`get_Item` → `set_field` → `set_Item(i, 副本)`，每次写后读回。
  - `UpperBodyTransformer.setupJoints()` / `onJointConstructed()` 都是追加，先清空列表再调。
- 引擎侧依赖要先断开再重建：子部件 `SharedSkeleton` `unshare()`、`via.motion.Chain` 关闭并清资源、关节类组件
  （JointConstraints / IkLeg2 / RetargetRig / IkMultiLookAt2 / Ragdoll / Colliders……）关闭；换后逐个 `reset / restart`。
- 时机：只在 UpdateScene；新目标出现满 8 s 且 `Motion.get_JointsConstructed`、`Chain.get_Setuped`、`IkLeg2.get_Setuped` 都就绪、
  皮肤烘焙空闲。
- 原件要按**路径**重新 `create_resource` + `add_ref` 钉住；游戏自己的 holder 不保证资源驻留，用它换回会得到无 joint 的角色。
- 做到以上全部，仍有引擎侧（非脚本）工作线程崩溃（栈只有作业分发 + 引擎数学代码）。这是改走 §2 流水线的直接原因。
- 不要 hook `via.render.Mesh.setMesh` 去改参数：REFramework 解析到的是真正的 native 函数，参数已是解包后的 native 资源指针。

## 5. 皮肤烘焙状态机（反汇编得到）

`app.BodyDetailEditor.bakingProcessing(Int32)->Boolean` 推进 `<Baking>k__BackingField`（`app.BodyDetailEditor.BakingProcess`）：

| 值 | 状态 | 值 | 状态 |
| --- | --- | --- | --- |
| 0 | None | 8 | MaterialBake_BodyBakedResource（读 `<BodyBakedResourceID>` 数组） |
| 1 | DynamicTextureTableSlotAssign | 10 | MaterialBake_ShareResource |
| 2 | ApplyPrepare | 11 | BakingCheck |
| 3 | ApplyPrepareWaiting | 12 | FinishingProcess |
| 4 | ApplyParam | 13 | FinishingProcessWaiting |
| 5 | ApplyParamWaiting | 14 | Completed |
| 6 | MaterialBake（调 `MaterialBakerController.build`） | 15 | Failed |
| 7 | MaterialBakeWaiting（等 `<Baked>`） | | |

- 模式 `<MaterialBake>`（None / RuntimeBake / ShareRuntimeBake / PreBake）在 5 分派：1 → 6，2 → 10，其他 → **直接 12**。
- `build` 在自定义身体上必崩（桩子网格、原生材质、把原生身体子网格藏进网格都试过）。
- 做法：pre-hook 看到 Karin 身体处于 5/6/7 → 置 12（游戏自己的非烘焙路线）。处于 3/4 时**登记它的 baker**，`build` pre-hook 对登记的
  baker `SKIP_ORIGINAL`，post-hook 撤销登记——因为**一次调用会连跑多个状态**（3 就绪后落进 4，4 参数应用完落进 5 → 6 → `build`），
  只在入口看状态永远命中不了 6。跳过后停在 7，下一次调用被改到 12。
- 反例（`rejected`）：只跳 `build` 不改状态 → 8 读空数组崩；整个 `bakingProcessing` 跳过 → 读档卡住。

## 6. 体型编辑表（捏人比例）

游戏构建身体时套用存档的捏人体型：`app.BodyEditor.setupApplyEditScales` 取 `CharacterEditManager.getBodyEditJointScale(gender)`
（每个滑条 → 每个 joint 的 `JointEditData`）放进 `_ApplyEditScales`；`BodyEditorRoot.applyEdit`（每次 10 个 joint）算出各 joint 的
local TRS 并烘进 **base** 位姿：缩放沿层级连乘进子 joint 位置，骨盆高度随身高。原生骨架为此预先放大（脊椎段比 Karin 长约 28%），
Karin 骨架则被压扁（上身、手臂、头下发 / 耳骨约缩到一半；用户实机发现）。

- 做法：Karin 身体上 `setupApplyEditScales` post-hook 把 `_ApplyEditScales` 置空——`applyEdit` 自己的「无表」路径直接报告完成，
  骨架 = 网格静止姿势（实测 base 位置与网格完全一致，Hip 0.9667）。
- `rejected`：只改 `_JointEditValueDict`（值在 `applyEdit` 内已被消费）；`applyJointScales` / `trySetJointScale` 管的是碰撞体缩放。
- 验证：`via.Joint.get_BaseLocalPosition` 读 base 位姿，与网格骨表比较。

## 7. REFramework 细节

- `field:get_offset_from_base()` 对 `app.BodyEditor`（泛型基类 `BodyEditorBase<PartSwapper>`）及部分枚举字段**比实际偏移小 8**
  （对照反汇编）；按名字 `get_field` / `set_field` 不受影响。
- 脚本重置（「Reset scripts」）时 `on_script_reset` 不在游戏更新时序里，不要在那里改游戏对象；需要交接的状态写到
  `reframework/data/<mod>/` 由新实例读取。
- 脚本重置后 `method:get_function()` 可能返回映像前的桩地址，hook 仍然生效。
- 枚举值用静态字段 `get_data(nil)` 读；读不到就当作 hook 缺失（失败即关闭）。
