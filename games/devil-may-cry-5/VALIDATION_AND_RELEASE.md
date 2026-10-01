# 验证与发布

## 1. 离线闸门（offline-accepted）

网格（`ko_verify`，对照 PT 模板）：

- 模板骨（去掉 PT 专用骨）全部保留，bind 与父子关系不变（误差 < 1e-5）。
- 不残留 PT 专用骨。
- `KO_*` 骨世界旋转为单位阵；`local @ parentWorld == world`；`inverse == inv(world)`。
- 权重和为 255（容差 ±1），骨索引有效。
- 材质名与模板一致。
- 以 Nero 空间为模板时，头部和耳朵顶点与 PT 网格重合（检查 §1 的放置变换）。

V 改造（`verify_mesh`）：几何、法线、按骨名的权重与 Nero 网格一致；481 根共有骨的世界矩阵除 Hip 外不变；
fbxskel 方法能复现 Nero mod 的结果；生成的 MDF 与 Nero 材质签名一致，只有贴图路径不同；
头部 MDF 只有 `m_teeth` 改动。

chain（`ko_chain` 内置）：37 组可回读；静止穿透为 0；臀部和大腿的覆盖余量（见 [chain 物理](CHAIN_PHYSICS.md) §4）。

预览：Blender 平光渲染 T 姿势的正 / 侧 / 背面和一个弯腿姿势（`ko_render check`）。只算 `offline-accepted`。

打包（`ko_package`）：

- `natives/` 下每个路径都对照游戏路径表核对。Nero 有 4 个、Dante 有 7 个路径不在表里
  （例如 `pl0010_13.chain.21`、魔人 / 真魔人的身体 chain）。这些路径都来自 PT 包，其中身体 chain 的内容
  换成了 Karin_Original 的；作为已知项接受。
- 每个 MDF 的贴图引用必须落在包内或游戏路径表里，不允许残留 `KazamiRika` 路径。
- 写出 sha256 清单；zip 顶层文件夹名就是 mod 名。
- 更新已有版本时，逐文件比较新旧 zip，确认只有预期的文件变了（v1.1 只改了身体 chain 和 `modinfo.ini`）。

## 2. 标题画面自测（runtime-load-pass）

- 用 `steam://rungameid/601150` 启动。窗口约 6 秒出现，约 1 分钟进入标题画面。
- 输入：DMC5 不接受合在一起的按键事件，要分别发送按下和抬起（AutoHotkey 桥接）。
- **只关启动弹窗**（网络错误弹窗，偶尔有登录奖励弹窗）。不要在标题画面按 Enter，那会继续存档进入实战。
- 标题画面同屏有三个角色：Nero 在左，Dante 居中且背对镜头，V 在右。场景是背光的，最容易暴露材质的明暗问题；
  但看不出战斗中的物理问题。
- 标题画面闲置约 45 秒后会播放宣传视频，截图要在这之前，或者等视频结束。
- 用户装了 REFramework 时，启动后可能开着它的覆盖菜单。不要去动它。
- 在标题画面做 A/B：先备份，再只替换游戏 `natives` 下的单个文件，重启比较；结束后还原，并核对没有残留。
  本项目用这个办法排除了物理（空 chain）和法线（几何法线版网格），把发黑问题定位到 albm 的 alpha。

## 3. Fluffy 安装与原地更新

- 用 GUI 自动化操作 Fluffy 时：
  - 普通的快速点击会被忽略，用 200 ms、1 像素的拖动来点。
  - 单击一次切换一次安装状态，双击等于装了又卸。每次切换后读 `installed.ini` 确认。
  - 新开窗口的第一次点击可能只是取得焦点。
- Fluffy 会一直占用正在预览的 mod 的 zip。替换 zip 前先正常关闭 Fluffy（CloseMainWindow），换完再启动。
- **原地更新**：文件列表不变时（例如 v1.1 只改了 chain 内容），按 `installed.ini` 的路径直接覆盖游戏目录里的散装文件，
  同时替换 `Mods` 里的 zip，然后逐个核对哈希。这样 `installed.ini` 仍然准确，卸载时也能删干净。
  文件列表一旦变了，就必须在 Fluffy 里卸载再重装。
- 不要改变用户当前的安装选择。例如用户把 V 换回 PT 版时，只更新 zip，不替用户切换。

## 4. 运行时分层

| 级别 | 做法 | 本项目 |
| --- | --- | --- |
| `offline-accepted` | §1 闸门 + 预览 | 全部版本 |
| `runtime-load-pass` | §2 标题画面自测 | PT V；Original v1.0 三个角色；Original v1.1 的 Nero / Dante |
| `runtime-confirmed` | 用户验收 | PT V（标题画面）；Original Nero / Dante（实战，v1.1 修复裙摆后） |

Original V 的 v1.1 chain 没有在游戏里加载过：用户测试时 V 装的是 PT 版。
