# Agent 入口（生化危机 安魂曲）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态在独立工程的 `README_*.md` 记录里，
不在这里；本目录只提供方法和已被证伪的假设。

## 接手一个新任务前

1. 核对 Steam appmanifest 的 `buildid`（本目录快照为 `23634047`）。**build 变了，部件变体、prefab 后缀、骨数和
   偏移都要重新提取验证**；游戏更新改过的 prefab 之后，注入过组件的 mod 必须重建。
2. RSZ 类型库用 REasy 仓库的 `rszre9.json`（与本 build 对上）；先让读写器对一批原生 `.pfb.18` 做逐字节往返。
3. 读 Fluffy 的 `Games/RE9/installed.ini`，确认当前启用的是哪几个包。**替换同一角色的 mod 互斥**
   （本项目：用户自己的「Leon Karin」与「Leon Karin Original」只能开一个）。
4. 桌面可能被别的会话共用（本项目期间另一会话在测别的游戏）。启动游戏、发键鼠之前先约好屏幕；
   测完关掉游戏，并告诉对方屏幕已释放。

## 硬性规矩（本项目已付过学费）

- **加载自带 chain2 的每个 `via.motion.Chain2` 组件都要设 `CollisionTarget = 0`（Self）。** 原生值 1（Extern）
  只碰角色 `.clsp`，chain2 里的模型碰撞体等于不存在（v1.1 实测：裙片节点陷在大腿胶囊里 6 cm）。
  注入的组件和原生槽位的组件都要改。
- **任何材质的 `NormalRoughnessMap` 都不要留 `systems/rendering/NullNormal.tex`。** 它解码为 `(127,127,254,0)`，
  alpha = 粗糙度 0，实机像乳胶。用一张平法线、粗糙度 1 的小 NRMR（64×64 BC7 线性 `(128,128,255,255)`）。
  也要检查参考 mod 自带的 NRMR：有的只是 NullNormal 的 8×8 副本。
- **改一个部件号就改它的所有变体和所有 mdf2 变体**（路径表里 `<mesh 名>_NN.mdf2.51` 全部写）。
  漏掉的变体在对应场景里显示原模型，漏掉的 mdf2 变体会让材质名对不上。
- **展柜截图不能证明物理。** 展柜对喂了专用动画（`PartsMotionData`）的部件关闭 Chain2；碰撞要靠运行时探针读
  节点与碰撞体的世界坐标。
- **refskel 是整个角色号共用的。** 改 `ch01.refskel.8` 会让里昂的其它服装（ch0150–0153）也按新比例变形；
  报告里写明，不要说成只影响替换模型。
- **用 Fluffy 安装，不要手工拷文件进游戏目录。** 手工部署测试后，按 `installed.ini` 还原并清掉多出来的文件，
  否则游戏目录与 Fluffy 记录分叉。更新包：在 Fluffy 停用 → 替换 Mods 下的包 → Refresh → 启用 → 逐文件比哈希。
- **主菜单不要长按方向键。** 长按会连跳，曾一路跳到「退出游戏」再被确认键确认，看起来像崩溃。
- **构建前清空输出目录**；打包器先跑独立验证器，`VERIFY: PASS` 才允许打包。
- **不要声称实机通过。** 离线闸门、预览渲染、展柜截图分别是 `offline-accepted` / `offline-accepted` /
  `runtime-load-pass`；用户在实际游玩里确认之后才是 `runtime-confirmed`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系。
