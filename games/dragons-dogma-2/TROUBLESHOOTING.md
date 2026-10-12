# 排障手册

先看崩溃栈里的 `app.*` 类名或 `DD2.exe + 0x…` 偏移（RVA，可直接反汇编，见 [开发工具](DEV_TOOLING.md) §4）。

## 1. 崩溃（除标「社区报告」的行外均为本项目实测）

| 现象（崩溃栈 / 症状） | 原因 | 处理 |
| --- | --- | --- |
| 对话手势时 `app.UpperBodyTransformer.HandParentInfoHolder.initDataToApplyHandIK` | `setMesh` 总会重建 joint 表并释放旧 `via.Joint`；游戏脚本缓存了约 150 个 joint 引用 | 不在活角色上换身体（[运行时注入](RUNTIME_INJECTION.md) §2）；必须换时按名记录、换后重绑 |
| `app.PropsJointPosAdjuster.updateJointPos`（RIP 相同的两次） | 它的 `Info` 是 `List<ScaleInfo>`，**元素是结构体**，`get_Item` 返回副本，重绑写到了副本上；是否崩取决于那块内存是否被复用 | 结构体元素写回 `set_Item` 并读回核对（旧结论「进容器会崩」是误判） |
| 暗病：`SlamHandCtrl` / `HumanHandMotionCtrl` 的 `via.Joint[]` 一直失效 | `Array.SetValue` 不写入却返回成功 | 数组用 `arr[i] = j` 并读回 |
| 暗病：UBT 手臂 / 颈部列表每次换身体多一份（3 → 36） | `setupJoints` / `onJointConstructed` 都是追加 | 先清空再建 |
| 暗病：箭矢显示、视觉标记、头顶 UI、草地传感器的 joint 一直失效 | 只扫了根 GO 的组件 | 扫全部子孙 GO 的组件 |
| `app.BodyDetailEditor.bakingProcessing` | 皮肤烘焙途中换身体 | 等烘焙空闲；网格带原生材质名兼容桩 |
| 换身体后几毫秒～十几秒，工作线程 access violation（栈只有作业分发 + 引擎数学代码，符号是就近的无关方法名） | 引擎侧仍持有旧 joint / 网格：在 UpdateBehavior 里换、角色还在异步 setup 时换、chain 与 `SharedSkeleton` 仍绑旧 joint | 缓解：只在 UpdateScene 换、新目标等 8 s 且引擎就绪、断开再重建。根治：改走构建时注入 |
| 关闭替换后 7 ms 崩溃，日志「unresolved joints: root, Hip, …」 | 用游戏原 holder 换回，资源已不驻留 → 新 joint 表为空 | 按路径钉住原件 |
| 「Reset scripts」时 `setMesh` 内 access violation | 原件不驻留，且 `on_script_reset` 不在游戏更新时序里 | 重置回调里不改游戏，交接给新实例 |
| `create_resource` 后立刻用就崩 | 资源未加载完 | 预加载，按时间等 5 s |
| 构建时注入后 `MaterialBakerController.setupClusterSettings` / `build` 内崩溃（多为无栈硬崩） | 皮肤烘焙器处理不了自定义网格 | 烘焙状态机改道到 FinishingProcess |
| 只跳过 `build` → `bakingProcessing+0x447` 崩溃 | 下一状态读 `build` 才创建的 `<BodyBakedResourceID>` | 状态改到 FinishingProcess |
| pre-hook 判断「状态 == MaterialBake」从不命中，`build` 照跑并崩 | 一次调用里状态 4→5→6 连续执行 | 同时按 baker 登记跳过 `build` |
| 下一次构建时 `add_ref` 报「not a managed object」 | 对注入用的 holder 调了 `release()`，被释放 | 不对它 add_ref / release，post-hook 把字段放回原值 |
| 模组网格 + 原版 GPU Cloth → 崩溃或顶点炸成「纸团」；头盔 Wrap Deformer 炸网格 | 社区报告（本项目未复现） | 隐藏全部装备（掩码 8191）；身体上不挂原版 cloth |
| 缺 LOD 槽 → 崩溃 | 社区报告 | 每个 LOD 槽都写几何 |
| 「can't create a GPU buffer」 | TU3.2 mesh 头部 +72 没写 shape-key buffer 大小 | 写入 |
| 退出游戏时崩溃 / 卡住 | REFramework 01424 上游问题 | 无害；强杀时连 `CrashReport.exe` 一起杀 |
| 两次 REFramework 异常处理递归崩溃（ntdll AV，栈在 dinput8） | 未定位，未见与 Mod 相关 | 记录，继续观察 |

## 2. 非崩溃症状

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| 启动后窗口全黑，日志每 11 s「Unhooking/Hooking D3D12」 | hook 了 `BodyEditorRoot.bind/postBind/unbind`（地址相距 0x20 的极小 / 折叠函数） | 不 hook 极小方法 |
| 上身、手臂、头被压扁约一半（v1.2 首版，用户发现） | 游戏把存档捏人体型连乘进 base 位姿 | Karin 身体上清空 `_ApplyEditScales` |
| Karin 只显示一部分 | 身体 Mesh 默认只开 group 0 | `setPartsEnable(1..7, true)` |
| 头发 / 装备 / 原头部叠在 Karin 身上 | 隐藏掩码被游戏改回 | hook `set_HideSwapObjects` 强制 8191；头部 `set_Enabled(false)` |
| 链朝上飞 | `angleLimitDirection` 是单位四元数，或 `K_*` 骨 +X 不指向子骨 | [chain 物理](CHAIN_PHYSICS.md) §2 |
| 尾巴下垂、双马尾不摆 | `K_*` 骨没有逐帧回位，链没有静止形状 | `CHAIN_REST_POSE` + 零重力弱弹簧 |
| 裙摆翘太高 | 原生髋 / 脊椎胶囊包在裙根周围 | 裙组只碰大腿 `clspFlags1 = V15, V16` |
| 走路时裙片翻进身体（露腹部、内裤、大腿根） | 模板 75° 椭圆角度限制 + 腹部无碰撞 | 角度限制改窄，阻尼 / 弹簧无效 |
| 收窄后大腿从两片裙之间穿出 | 对称锥向外也被限住，大腿推不动裙摆 | 外倾锥（向内窄、向外宽） |
| 在线调参「全部倍率 = 1」后物理消失 | Lua 整数 `1` 传给 float setter，读回约 0 | 传 `1.0` |
| 表情卡住 | 原生头部失效后没有归零 | 失效即归零，3 s 后重收集 |
| 游戏内 Karin 贴图全是棋盘格（`--native-compat` 实验） | 贴图未驻留，原因未查 | 实验弃用 |
| 近距离镜头下猫耳和光环占满画面 | 模型尺寸 | 不是错误 |
| 某些技能让自定义网格不可见（社区报告） | 未实测 | 遇到时记录场景 |

## 3. 已被证伪的捷径

- 「同骨架的网格 `setMesh` 不会重建 joint」——会，原版男女互换也崩。
- 「进容器重绑会崩」——是结构体副本问题，写回即可。
- 「只跳过 `build` 就能绕开皮肤烘焙」——下一状态读空数组崩。
- 「改 `_JointEditValueDict` 就能去掉体型」——值在 `applyEdit` 内已被消费。
- 「调低阻尼 / 加大弹簧能把裙片拉出身体」——实测无效。
- 「hook `via.render.Mesh.setMesh` 改参数」——拿到的是 native 资源指针，塞托管 holder 得到空网格。
- 「REFramework LooseFileLoader 加载散装文件」——TU3.2 之后无效，只能走 `pak_mods`。
