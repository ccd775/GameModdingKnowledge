# Agent 入口（PRAGMATA）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态在独立工程的
`README_*.md` 记录里，不在这里；本目录只提供方法和已被证伪的假设。

## 接手一个新任务前

1. 核对 Steam appmanifest 的 `buildid`（本目录快照为 `24543093`）。**build 变了，所有后缀号、
   prefab 路径、骨数和偏移都要重新提取验证**；游戏更新被改过的 prefab 后 mod 必须重建。
2. 确认 RSZ 类型库是**正式版**的（REasy 的 `rszpragmata.json`）。demo 版的库 CRC 对不上，
   症状是 Mesh / CharacterBodyParts 等类型读出来错位。
3. 用全量 prefab 扫描找出**所有**引用目标身体 mesh 的 prefab 和 GameObject，再决定注入范围。
4. 分清这一版改的是几何、材质还是物理；一版只让一类改动进入实机反馈，否则无法归因。

## 硬性规矩（本项目已付过学费）

- **mesh 用 raw 模式读写。** RE Mesh Editor 自己的法线/UV 重编码有损；raw 模式按原字节保留
  法线、UV、颜色和权重，并用往返闸门证明载荷一致。
- **不要整块拷别的文件的 mesh 头。** 固定偏移在不同布局下含义不同（曾把第一个 mesh group 的
  索引数写成 245,496）；只从同槽原生供体拷 `lodGroupNameHash`（`0x0c`）。
- **从别的 mdf 拷来的材质条目要把 `GPUBufferOffset` 清零**，且 AlphaTest 条目排在 Emissive
  前面（编辑器写出 bug，见 [技术合同](TECHNICAL_CONTRACTS.md) §4）。发布前做「偏移清零后重写仍逐字节一致」。
- **不要复用角色原生 `.clsp` 给替换模型当碰撞。** Hugh 的 clsp 里有背包机械臂、颈后推进器、
  0.2 m 胸腔胶囊，Karin 身上没有这些部件；需要碰撞时在 chain2 里拟合自己的模型碰撞体。
- **插入 Chain2 组件时 `UpdateTiming` 用 4**（原生头发全是 4）。从布料部件复制来的 3 会让移动中的
  链条表现异常（见 [物理](CHAIN2_PHYSICS.md) §4）。
- **不要为了治抖把 `reduceSelfDistanceRate` 一路调高。** 它是「跟随」旋钮，调高会让跑动时头发
  不甩；先查 UpdateTiming。
- **审查期间冻结被审文件。** 双轨审查时主控改了 README，GPT 席因快照哈希不符直接 BLOCK；
  审查包写哈希，改动等所有席位回来再做。
- **构建前清空输出目录。** 旧产物会被打包器一起带走。
- **不要声称实机通过。** 离线闸门全绿、确定性双跑、预览渲染正确都只是 `offline-accepted`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系。
