# 霍格沃茨之遗（Hogwarts Legacy）

## 范围

这里整理 Steam《霍格沃茨之遗》（App `990080`，WB 改过的 UE 4.27「Phoenix」，IoStore）把黑魔法套装替换成 Karin 的可复用合同，
来自 2026-10-19 → 10-23 的一个项目：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| 里程碑 1（v1–v6） | 模型与材质替换：Karin 拟合到 HL 骨架（男 / 女两套比例）、身体和衣服进黑魔法套装上衣、头和头发进特定的脸型 / 发型预设、其余套装部件换空模型 | `runtime-confirmed`（用户实机，经头小、脖子长、肩宽、锁骨塌、腿露原版皮肤五轮反馈后「看起来可以了」） |
| 里程碑 2（v7–v12） | 次级物理（95 根动态骨、AnimDynamics 单骨节点，挂在部件自己的动画蓝图里）和表情（游戏面部姿势资产驱动的 56 个 HL 同名形变） | `runtime-confirmed`（用户：v12「这次的挺好的了」，「表情和物理效果都正常」） |
| 女巫版发行 v1.0 → v1.1 | 只替换女性体型；女版材质实例按字节克隆到空闲的 `_F` 路径，男版保持原版 | v1.0 `runtime-rejected`（玩几分钟后崩溃）；v1.1 `runtime-confirmed`（用户：「玩了一会儿还可以，没有闪退」） |

快照只对游戏版本 `1613387`（Steam buildid `20773316`，2026-10）有效。**容器格式、网格序列化、资产路径、骨数是 `build-sensitive`**；
拟合参数和物理参数是 `case-derived`。

本作的主要贡献：

- **2025-01-30「数据序列化 + 光追」更新后的网格格式**：那次更新让几乎所有旧网格 mod 失效。原因是每个
  `FSkelMeshRenderSection` 多了一个 uint32；在原版 UE 4.27 cook 出来的包里补上它，再修正导出表的大小和偏移就能用
  （[技术合同](TECHNICAL_CONTRACTS.md) §2）。
- **只装原版 UE 4.27 编辑器**：游戏路径上放占位（骨架、物理资产、母材质、材质实例），只把自己的资产 cook 出来，
  retoc 转成 IoStore 放进 `~mods`。材质实例不能新建（HL 的每个材质实例尾部多一个唯一哈希），只能借用游戏自己的。
- **部件自己跑物理**：没有 `AnimClass` 的套装部件靠主姿势跟随身体，网格上的后处理蓝图不会运行；给上衣和发型的数据资产
  注入 `AnimClass`，指向编辑器插件生成的「CopyPoseFromMesh → AnimDynamics」蓝图，就有了不改游戏蓝图的次级物理。
- **一个真实崩溃的排查方法**：「模组崩溃，建议卸载、改用官方模组」的弹窗是游戏的崩溃报告器，不是反 mod 检测；
  从 `Saved\Crashes` 里的转储定位到「网格里有骨架没有的骨」（[排障手册](TROUBLESHOOTING.md) §1）。

与其它 UE 目录的关系：剑星（`games/stellar-blade/README.md`）同样走 IoStore；师父（`games/sifu/README.md`）、幻兽帕鲁、往日不再同样
用原版编辑器 + 游戏路径占位。本作独有的是更新后的 section 字段、材质实例尾部哈希和装备 / 角色部件数据资产。

## 核心方法

- 先用 retoc 把目标资产转成 legacy 包，用 CUE4Parse（HLMeshProbe）dump 成 JSON：网格、骨架参考姿势、角色部件 / 装备外观数据资产、
  动画蓝图、物理资产、面部姿势资产、捏脸预设表；再决定方案。
- 不改骨架和动画。身体、头、头发分别替换「黑魔法套装上衣」「存档用的脸型预设」「发型预设」的网格；套装的其它部件换成空模型，
  袜子和鞋槽指向空部件（腿部皮肤在袜子部件里）。
- 网格参考姿势逐骨等于游戏的（cook 后按 JSON 精确写回）；比例差在 Blender 里用 TPS 变形吃掉。
- 每一类改动（拟合、材质、物理参数、表情）单独进实机反馈；物理参数先用离线模型（`feel_sim.py`、`swing_check.py`）比较候选。
- 烘焙后用 CUE4Parse 读回：材质槽、骨数、形变数、动画蓝图的目标骨架、数据资产里注入的引用；发行前检查每个网格的骨都在它引用的骨架里。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。
实机证据来自用户的口头反馈和截图，以及 agent 在测试机上的截图和崩溃转储；文档逐项写明是哪一种。未测场景见
[验证与发布](VALIDATION_AND_RELEASE.md) §4。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：容器与加载、更新后的网格 / 材质格式、骨架、装备与角色部件、动画类、面部、捏脸预设、崩溃报告器
- [构建流水线](BUILD_PIPELINE.md)：提取 → Blender 拟合 → 物理参数 → UE 导入与蓝图生成 → cook → 补丁与数据资产修改 → IoStore → 安装
- [角色拟合](CHARACTER_FIT.md)：重摆姿势、TPS 控制点、躯干 / 肩 / 颈的比例、权重、法线、动态骨
- [物理](PHYSICS.md)：AnimDynamics 语义、单骨节点、集中杆模型、碰撞球、四轮调参
- [表情](FACE.md)：面部姿势资产、HL 形变名映射、动漫脸的法线
- [排障手册](TROUBLESHOOTING.md)：症状 → 原因 → 处理（含崩溃转储分析）
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门、发行包结构、捏脸说明、证据分层、未测场景
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)：v1 → v12 → 发行 v1.1 的每一轮
- [便携工具包](../../portable-kits/hogwarts-legacy/README.md)：Blender 拟合脚本、UE Python、编辑器插件源码、HLMeshProbe 源码、包补丁脚本

## 公开边界

不含源模型、游戏资源、提取出的 JSON、发行 pak、崩溃转储或 UE 引擎源码。便携包里的脚本是项目脚本去掉本机路径后的副本；
Karin 专属的骨名、链表、形变映射和物理参数是案例值，换模型时要按当前资源重新测量。
