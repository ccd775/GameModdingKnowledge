# Agent 入口（Devil May Cry 5）

先读 [README](README.md)，再按当前问题进入对应文档。本目录只提供方法和已被证伪的假设；
项目当前状态与构建脚本在项目目录 `DMC5/Work/`。

## 接手一个新任务前

1. 核对 Steam appmanifest 的 `buildid`（本目录快照为 `24901913`）。build 变了就重新提取原生文件，
   复核路径表和各文件版本号。
2. 读 Fluffy 的 `Games/DMC5/installed.ini`，确认当前装的是哪几个包。用户会自己在 PT 版和
   Original 版之间切换（例如测 Original 的 Nero / Dante 时，V 装的是 PT 版），**不要擅自改动**。
3. 确认参考 mod 的完整文件树：PT 包里除了身体，还带着隐藏头发 / 头部用的空网格、场景、头发槽 chain，
   新包要原样继承这些文件。
4. 分清这一版改的是网格、材质还是物理。一版只让一类改动进入实机反馈，否则无法归因。

## 硬性规矩（本项目已付过学费）

- **标题画面自测只能关启动弹窗**（网络错误弹窗，偶尔有登录奖励弹窗）。在标题画面按 Enter 会
  「继续」存档，直接进入实战，用户明确不希望这样。实战由用户测。
- **albm 的 alpha 填 255。** 用 Env_Emissive 时，alpha 控制自发光。按「金属度」理解填 0，
  背光的标题画面里角色会整片发黑。
- **NRMR 用 BC7_UNORM**（tex 头 `0x1C = 0x500`）。PT 包里的 NRMR 是 sRGB，平坦法线会被解成倾斜的。
- **单面源模型要清掉 MDF 的双面位**（材质 flags bit0）。PT 的 MDF 里有材质开着双面
  （如 Nero 的 `m_coat` / `m_leg`）；Karin_Original 的裙子内外层几乎重合，继承双面会闪烁。
- **RE Mesh Editor 每个顶点只导出一个法线**（取第一个角）。法线不连续处要先拆顶点，否则衣褶、
  鞋底和缝线的法线会糊在一起。
- **不要用 RE Mesh Editor 写 MDF v10。** 它的写出器不能往返 DMC5 的 MDF（修了 TEXTURE_ENTRY_SIZE
  之后 101 个里也只有 1 个逐字节一致）。用只追加、整体平移偏移的最小改动编辑器。
- **不要把 PT chain 的下半身碰撞体直接套给另一套服装。** 它们只是骨轴上半径 0.08 的胶囊，
  罩不住 Karin_Original 的臀部和大腿（见 [chain 物理](CHAIN_PHYSICS.md) §4）。
- **Hip 挂的碰撞体按身体分别生成。** Nero / V / Dante 三套网格的 Hip bind 不同，偏移不能共用。
- **复制文件后核对哈希。** 一次 PowerShell 复制因为 `$W` 和 `$w` 不区分大小写（循环变量覆盖了
  目录变量）而悄悄失败，靠哈希核对才发现。
- **不要声称实机通过。** 离线闸门全绿、预览渲染正确都只是 `offline-accepted`；标题画面正常是
  `runtime-load-pass`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系。
