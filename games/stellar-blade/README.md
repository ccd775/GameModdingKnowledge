# Stellar Blade（剑星）

## 范围

这里整理 Steam《Stellar Blade》（App `3489700`，UE 4.26.2 的 SB 分支，IoStore）角色替换的可复用合同，
来自 2026-10-12 至 10-13 的一项交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin_Original → EVE `CH_P_EVE_09`（初始服装 Planet Diving Suit）v1.0 | 从 VRM 源模型完整构建身体（含 140 根次级骨的 28 条物理链）、脸（JALI 变形名）、隐藏原版头发；后处理 AnimBP：ControlRig + 运行时改腿长 + 28 个 KawaiiPhysics 节点 | `runtime-confirmed`（用户实机：比例、材质、物理、裙摆穿模修复后「这次好了」）；表情未在游戏里检查 |

所有骨名、骨数、半径、偏移和参数都是 `build-sensitive` 或 `case-derived` 快照，只对 build `24463856`
（游戏版本对应 usmap `SB-v1.4.1`）有效。

本作的主要贡献：

- **KawaiiPhysics 按 USkeleton 建链。** `FAnimNode_KawaiiPhysics::InitModifyBones` 遍历的是骨架资源的
  参考骨架，不是网格。网格独有的骨在编辑器里能动（导入时并进了 dummy 骨架），进游戏一根都不模拟。
  物理链必须落在游戏骨架已有的骨上，并且父骨一致。游戏骨架里有大量没用到的配件链可以借用。
- **骨架用 Animation 平移重定向，网格改不了比例。** 腿长、髋高只能在后处理 AnimBP 里用加性
  ModifyBone 改；这一点经过了运行时验证。
- **无 GUI 编写动画蓝图。** UE 4.26 的 Python 不能加动画图节点；一个小的编辑器 C++ 插件提供加节点、
  连线、按导出文本设嵌套属性、编译等接口，整个 AnimBP 由脚本生成。
- **紧身裙段不进物理。** 碰撞胶囊只挡关节，挡不住关节之间的布。髋关节以上的裙子直接复制身下皮肤的
  权重，物理只从髋关节往下。

## 核心方法

- 先导出原版服装的后处理 AnimBP 做模板：所有服装都是 InPose → ControlRig `BtoB_CtrlRig` → 若干
  KawaiiPhysics（每个链头一个节点）→ 输出。新 AnimBP 复现同一拓扑，ControlRig 用游戏路径上的
  dummy 类（不打包），运行时解析到游戏自带的 rig。
- 网格骨架 = 游戏骨架的子集 + 少量网格独有辅助骨（只由 ModifyBone / BoneDrivenController 驱动）。
  导入用 dummy 骨架、dummy 物理资源和 dummy 父材质，都放在游戏路径上，只打包新资源。
- Cook 后只挑出新资源，用 retoc 转成 UE4_26 的 IoStore 容器，文件名以 `_P` 结尾放进 `~mods`。
- 实机测试在远程测试机上做。物理和后处理效果不能凭单张截图下结论，要么用 ×2 缩放标记做诊断构建，
  要么连拍多帧。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` /
`runtime-rejected` / `runtime-confirmed`。

本项目付过的学费：三次凭停步、跳跃的单张截图宣称「物理生效」，实际物理从未运行（见
[排障手册](TROUBLESHOOTING.md)）。此后的规则：运行时结论要么来自用户的观察，要么来自不可能由刚性
挂接产生的证据（标记、连拍）。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：引擎与容器、骨架与重定向、服装 AnimBP、材质、打包、工具链
- [角色替换](CHARACTER_REPLACEMENT.md)：VRM → EVE 拟合、改腿长、权重、脸、隐藏件、材质与双面
- [Kawaii 物理](KAWAII_PHYSICS.md)：骨架借链、预设、胶囊拟合、曲线、裙摆跟腿、紧身段权重
- [验证与发布](VALIDATION_AND_RELEASE.md)：离线闸门、远程实机测试、诊断标记、发布包
- [排障手册](TROUBLESHOOTING.md)：症状导向的定位表与已被证伪的假设
- [案例：Karin_Original × EVE 09](cases/KARIN_ORIGINAL_EVE09.md)：版本轨迹与每一轮反馈

## 公开边界

本目录只有文档，不含源模型、参考 mod、游戏资源、导出的原生文件或发布包。构建脚本（Blender 构建、
UE 导入与 AnimBP 生成、编辑器插件、打包脚本）留在项目目录 `StellaBlade/Karin_Original_EVE09/Scripts/`，
这里只记录脚本职责、方法、结论和被拒绝的假设。
