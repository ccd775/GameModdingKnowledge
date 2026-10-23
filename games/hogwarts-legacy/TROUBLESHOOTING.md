# 排障手册

除标注外均为本项目实测。

## 1. 玩几分钟后弹出「模组崩溃」（v1.0，2026-10-19 → 10-23）

**症状**：表情和物理都正常，玩一两分钟到五分钟后游戏退出，弹窗说模组导致崩溃、建议卸载模组并使用官方模组。用户怀疑是官方检测非官方 mod。

**结论**：不是检测，是真崩溃；原因是头部和空模型网格带了 `Biped_Skeleton` 里没有的 95 根动态骨。

排查步骤（换别的崩溃也适用）：

1. `%LOCALAPPDATA%\Hogwarts Legacy\Saved\Crashes\` 下三个转储：`CrashUserData.json` 里 `ErrorMessage: Unhandled exception`、
   `CrashType: Crash`、`UnofficialModsPresent: true`；`CrashContext.runtime-xml` 的启动后秒数 64 / 310 / 130，三份的 `PCallStack` 完全相同。
   弹窗文字来自 `UnofficialModsPresent`（[技术合同](TECHNICAL_CONTRACTS.md) §8）。Windows 事件日志里没有对应的应用错误（UE 自己处理了异常）。
2. 解析 minidump（标准库就够）：异常流（类型 6）给出 `C0000005` 读访问、地址 `HogwartsLegacy.exe+0x5506030`，读的是 `[rdx + r8*8]`，
   `rdx` 两次为 0、一次为悬空指针；线程上下文给寄存器；内存流（类型 5）只有栈附近和寄存器指向的少量内存，没有 exe 的代码。
3. 代码从磁盘上的 exe 取：按节表把 RVA 换成文件偏移，按 `.pdata` 找函数边界（段名被加固工具改过，但 `.pdata` 可用），用 capstone 反汇编。
   崩溃点连读三个 16 字节（48 字节的 `FTransform`），循环里按 8 字节步长读 `{int32 SourceIndex; float BlendWeight}`（`FPerBoneBlendWeight`），
   上一层按 24 字节步长遍历子姿势（`FCompactPose`）后调用一个 10 参数函数 → `FAnimationRuntime::BlendPosesPerBoneFilter`，
   即「按骨骼分层混合」节点的求值；在游戏线程的组件 tick 里。
4. 从寄存器和转储内存读数组长度：基础姿势、权重数组、唯一一个混合姿势都是 362 根骨；骨骼容器里按骨架索引的数组是 267。
   267 = `Biped_Skeleton` 的 260 + 7 根虚拟骨；362 = 355 + 7。Karin 的身体和头发用自带骨架（355，无虚拟骨），
   只有**引用 `Biped_Skeleton` 却带着 355 根骨的网格**（头、12 个空模型）符合。
5. 三次都崩在紧凑姿势第 97 根骨（`rbx = 0x61`），读到的 `SourceIndex` 是 90 / 71 / −1（只有 1 个混合姿势，合法值只能是 0）。
   头部网格第 97 根骨是 `Ear_L`：**第一根骨架里没有的骨**，0–96 全在骨架里。
6. 原版 UE 4.27 在建权重表时对找不到的骨（-1）有 `ensure` 保护；HL 这里为什么仍读到无效数据没有查到代码级原因
   （推测是拿 -1 当了索引，`hypothesis`）。触发条件（第一根骨架外的骨）和修复是确定的：分层混合只在某些动画状态下才有有效的混合姿势，
   所以不是一进游戏就崩。

**修复（v1.1）**：导出时只给会变形到动态骨的网格（身体、头发）保留它们，其它网格去掉游戏骨架里没有的骨（头部顶点本来就只绑 `Head`，外观不变）。
检查：组装后的 legacy 包里，引用 `Biped_Skeleton` 的网格名字表不应再有 `Ear_L` / `Tail`；头部仍有 56 个形变。用户实机：「玩了一会儿还可以，没有闪退」。

**教训**：编辑器导入会把缺的骨自动补进占位骨架，占位工程看不出问题；发行前要对照游戏骨架查每个网格的骨。

## 2. 构建与打包

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 游戏里整个人是灰色棋盘格 | 烘焙后的网格材质槽全是 `null`：UE Python 取出的 `SkeletalMaterial` 是副本，改了没写回 | 新建列表整体 `set_editor_property('materials', …)`；已导入的用 `ue_fixmat.py` 重挂；CUE4Parse 读回核对 |
| 头部导入了 0 个形变 | reimport 沿用资产里存的旧导入设置（当时没开形变） | 导入前删除目标资产 |
| 导入后多出一根根骨 `HLArmature` | FBX 的骨架对象不叫 `Armature` | 导出前改名 `Armature` |
| 导入后网格缩小 100 倍 / 放大 100 倍 | FBX 单位换算重复或缺失 | Blender 里用米导出、不做单位换算，UE 导入时换成厘米；读回关节位置与 HL 差 0 |
| 从代理网格建不出物理资产 | 代理太简单 | 占位物理资产直接复制引擎教程里的物理资产（只要路径对，不进包） |
| HLMeshProbe `patch` 校验失败 | 包被解析两次，section 位置重复，插了两次 | 位置去重（`Distinct()`） |
| HLMeshProbe 启动即崩（.NET 10，「Windows doesn't fully support CET」） | CET 兼容 | `<CETCompat>false</CETCompat>` |
| CUE4Parse 编译失败在 Natives | 没有本地编译工具链 | `CUE4PARSE_SKIP_NATIVE=1` |
| UBT「Could not find NetFxSDK install dir」 | 只装了 VS2022 | HKCU 下补一个指向空目录的 NETFXSDK 4.8 键，编完删除 |
| 插件编译 C2248（`UAnimGraphNode_AnimDynamics::Node` 私有）、LNK2019（`GetPrivateStaticClass`） | 该类没有导出 | 按类名 `FindObject<UClass>` + 通用 `NewNodeOfClass`；`Node` 用反射取 |
| retoc `--filter` 什么都没取到 | 名字不准确 | 先在路径清单里查准确的资产名（例：`DA_HUM_F_Hair_StuHair18_PrincessLong_Bangs1` 没有 `_Master`） |
| Git Bash 里 `/Game/...` 参数变成 Git 安装目录下的路径 | MSYS 路径转换 | `MSYS_NO_PATHCONV=1` |
| Git Bash 的 tar 报「Cannot connect to C: resolve failed」 | 把盘符当成远程主机 | 用相对路径或 `--force-local` |
| 远端 Windows tar 解不开 `.tar.xz` | 没有外部 xz | 用 Python 的 `tarfile` 解（`filter='data'`） |
| 只做女版时，男版黑魔法套装也变了 | 女版豪华套装直接用男版的材质实例和贴图 | 女版材质实例按字节克隆到 `_F` 路径（[技术合同](TECHNICAL_CONTRACTS.md) §3） |

## 3. 实机外观与物理

| 症状（用户反馈或 agent 截图） | 原因 | 处理 |
| --- | --- | --- |
| 头特别小，尾巴根附近的腰被拉长 | 躯干按 Hips 对齐、头没随身体放大 | [角色拟合](CHARACTER_FIT.md) §2 |
| 脖子太长，肩膀太宽，脖子像圆柱插在锁骨上 | HL 肩关节宽且低 | `shoulder_in`、`head_offset`、颈部用 `g_head` |
| 脖子到锁骨塌陷 | 颈根下移的同时肩抬高 | 颈根不下移，肩颈权重混合 |
| 腿上露出原角色的皮肤 | 从装备外观里删掉袜子 / 鞋，游戏退回光腿（腿部皮肤在袜子部件里） | 袜子 / 鞋改指向空的裤子部件 |
| 戴帽子或拉起兜帽后光头 | 发型部件按帽型 / 兜帽换成共用网格 | 发型数据资产的覆盖全部指回 `DefaultMesh` |
| 鼻子和嘴周围有阴影，脸「脏兮兮」 | 拟合时丢了源模型的自定义法线 | 法线按雅可比带过去（[表情](FACE.md) §3） |
| 裙片静止时压进臀部和大腿 | 裙子重力 0.4 对 12° 限制 | 重力 0 + 内收上限 3° |
| 马尾、尾巴轻轻一动就快速大幅甩动 | 约 2 Hz、阻尼比约 0.1、运动输入比例 1 | 集中杆模型（[物理](PHYSICS.md) §3） |
| 物理整体太弱；跑动时大腿穿出裙片 | 刚度过大；大腿碰撞球在髋关节，不随腿摆 | 加强；大腿固定位置球 + 质心靠下摆 |
| 摆动太软、回正极慢 | 6 个 0.75 Hz 节点串联 | 提频、ζ 0.45–0.48、隔骨模拟 |
| 玩几分钟后崩溃，弹窗建议卸载模组 | 网格带了骨架外的骨 | §1 |

## 4. 存档与测试机

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 放进去的存档在读档列表里看不到 | Steam 云在启动时还原了旧的 `SaveGameList.sav` | 进程出现后立刻删掉它，游戏按存档文件重建列表 |
| 游戏菜单不响应模拟的按键和点击 | 发送输入的隐藏 PowerShell 抢了前台 | 同一进程里 `AttachThreadInput + SetForegroundWindow` 后再 `SendInput` |
| 传大文件时远程连接全部卡住几分钟 | 端口映射带宽小 | xz 压缩、限速单连接上传、截图在远端缩成 JPEG |
