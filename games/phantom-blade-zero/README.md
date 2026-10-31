# 影之刃零（Phantom Blade Zero）

## 范围

这里整理 Steam《影之刃零》（App `4115450`，S-GAME 改过的 UE 5.7.4，IoStore）主角「魂」（资产名 `Hun`）替换的可复用合同，
来自 2026-10-29 → 10-31 的两个交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin_Original v3 | 从 VRM 完整构建的成年魂（普通服装、十年前服装）和序章少年魂；Chaos 骨骼网格布料（裙摆、双马尾、尾巴、耳朵、刘海与侧发）；MetaHuman 表情曲线名的 43 个形变 + 34 个 ARKit 别名；平时游玩靠自带的眨眼动画蓝图、过场靠游戏自己的面部动画；身体补回原版的 4 根武器子骨（醉剑） | `runtime-confirmed`（用户本机实机：外观、裙摆五轮、刘海、耳朵、眨眼、过场有脸，「这次看起来都好了」）；v3 的醉剑修复只做了烘焙后读回，未进游戏 |
| Karin_PicodraTech v1 | 同一套脚本的分支：按材质合并的 blend 源模型、10 个网格角色、7 段布料（双马尾、刘海、耳朵、带蝴蝶结的尾巴、外套下摆、耳机线、腰带），合成的尾巴贴图 | `offline-accepted`（构建、烘焙读回、装进游戏）；用户没有反馈 |

快照只对 Steam buildid `26266538`（引擎版本串 `5.7.4-301524+42ecbfa37f78`）有效。**IoStore 容器格式、资产路径、骨数、
材质参数名是 `build-sensitive`**；布料参数、比例 1.30 / 1.37 是 `case-derived`。

与其它 UE 目录的关系：师父（本库 `games/sifu/README.md`）和幻兽帕鲁（`games/palworld/README.md`）同样只装 UE 编辑器、
在游戏路径上放占位资产、只 cook 自己的资产；本作是 UE 5.7，加载走 IoStore（`.utoc` / `.ucas` + 一个只为让引擎挂载的小
`.pak`），物理用引擎自带的 **Chaos 骨骼网格布料**，表情跟 MetaHuman 的曲线名走。

本作的主要贡献：

- **破解保护后的反射信息**：UE4SS 和原版 Dumper-7 都找不到 GUObjectArray；自写的内存扫描器 `objscan` 定位重排过的
  FChunkedFixedUObjectArray，打补丁的 Dumper-7 导出 usmap，再用 `usmap_fix.py` 去掉 Dumper-7 误把 `PropertyLinkNext` 当
  `FField::Next` 带进来的继承属性（13 万条），CUE4Parse 才能正确解析骨骼网格、蓝图、数据表；
- **领导者网格才是武器的挂点**：游戏里 `CharacterMesh0` 装的是身体网格本身，其它部件 CopyPose 跟随；替换身体时漏掉原版身体
  多出来的骨（`weapon_*_child`），武器（醉剑）就丢了模型和判定（[技术合同](TECHNICAL_CONTRACTS.md) §4）；
- **UE 5.7 Chaos 骨骼网格布料的可编程构建**：编辑器插件从材质槽建布料、做权重图（最大距离、backstop）、换法线、设置求解器；
  记录了 `ClothingAssetFactory` 的焊点 / 退化三角 / 每 LOD 一段的硬限制和百褶裙法线摇摆的解法（[物理](PHYSICS.md)）；
- **MetaHuman 头上的表情**：形变按 `CTRL_expressions_*` 曲线命名就会被游戏驱动；成年头的槽 0 在运行时被换成动态材质实例
  （「66 天」效果），脸要放到槽 1；平时游玩的头不跑自己的动画蓝图，眨眼放在睫毛片组件上（[面部](FACE.md)）。

## 核心方法

- 先用 PbzExport（CUE4Parse）把目标网格、骨架、外观数据表、角色蓝图（含字节码）、动画蓝图 dump 成 JSON / uemodel，再定方案。
- 替换外观表默认两行（`普通服装`、`10年前服装`）和序章的少年魂用到的网格；骨架、动画蓝图不动。关节位置按骨架的重定向模式
  （AnimationScaled：方向来自原版、长度来自 Karin；Animation：原版偏移），绑定朝向保持原版，网格按区域刚体变换摆上去。
- 每一类改动（几何、材质、布料、表情）单独进实机反馈；用户实机看到的问题先离线复现（Blender 姿势探针、读回 cooked 数据）。
- 烘焙后的容器用 PbzExport 读回（`PBZX_EXTRA` 指向输出目录），核对骨数、材质槽、形变数、布料绑定、动画蓝图节点。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。
实机证据来自用户的口头反馈（用户自己启动和游玩游戏；agent 不启动、不结束游戏进程）。未测场景见
[验证与发布](VALIDATION_AND_RELEASE.md) §4。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：容器与加载、加密与 usmap、目标资产与外观表、骨架与重定向、领导者网格与武器骨、占位与隐藏、材质
- [构建流水线](BUILD_PIPELINE.md)：提取 → Blender 构建 → UE 导入 → 材质 → 布料 → 动画蓝图 → cook → 容器 → 读回 → 安装
- [物理](PHYSICS.md)：Chaos 骨骼网格布料的分段、参数、碰撞体、百褶裙外壳、backstop、硬限制；被放弃的 RigidBody 骨链
- [面部](FACE.md)：曲线命名、ARKit 别名、成年头发暗的原因、两张脸的方案、眨眼叠加动画蓝图、过场里的 groom 开关
- [材质与贴图](MATERIALS_AND_TEXTURES.md)：分层材质只改第 0 层、虚拟纹理、湿润参数、亮度系数、PicodraTech 图集与合成贴图
- [开发工具](DEV_TOOLING.md)：PbzExport、objscan、Dumper-7 补丁、usmap_fix、UE 5.7 内容工程与插件 PBZModTools、远程构建机
- [排障手册](TROUBLESHOOTING.md)：症状 → 原因 → 处理
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门、读回、发行包与安装脚本、证据分层、未测场景
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)：r1 → v3 的每一轮反馈
- [案例：Karin_PicodraTech](cases/KARIN_PICODRATECH.md)：blend 源模型的分支与第一版
- [便携工具包](../../portable-kits/phantom-blade-zero/README.md)：Blender 构建器、UE Python、编辑器插件源码、PbzExport / objscan 源码、PowerShell 流水线、安装脚本

## 公开边界

不含源模型、游戏资源、提取出的 JSON / uemodel、usmap、发行容器、游戏 AES 密钥或 UE 引擎源码。便携包里的脚本是项目脚本去掉本机路径后的副本，
Karin 专属的骨名、网格角色和参数是案例值，换模型时要按当前资源重新测量。
