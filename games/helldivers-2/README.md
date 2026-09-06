# Helldivers 2

## 范围与状态

本目录覆盖 AQ/ArchiveQT、HD2SDK、FileDiver 和脚本审计下的角色 Unit 替换、Unit triplet、骨调色板、UV0/UV1/UV2、Material/TextureMap namespace、Armor LUT/splat、确定性打包与安全部署。Nyako RE2310、SSF FS37/SC15 等案例证明了肩缝、rest/bind、自然权重、完整 Unit clone 和资源闭包方法；Armor LUT splat 和运行时组件开关仍按项目 SOP 标记待验证或研究中。

## 核心方法

- 记录 `archive.patch_N`、`.gpu_resources`、`.stream` 三件套及其 ownership；一个 ZIP 只交付一个完整 triplet。
- 先审计目标 Unit 的 TransformInfo、BoneInfo、局部 palette、LOD、draw range、材质 section 和资源引用，再选择 target-native 或完整 carrier/clone lineage。
- 保留源角色比例，显式处理 rest/inverse bind、肩部 seam、手指、脚底、shape key 和动态骨；不要按原生骨长逐段拉伸来“适配”。
- UV 层存在不等于 sampler 语义正确；BaseColor、normal/NAR、decal、alpha、emission 和 LUT 分开验证。
- child Material/TextureMap 使用确定性私有 namespace，同时扫描完整 ID 与 high32/ShortID 碰撞；资源闭包必须在安装树和运行时顺序下复核。
- AQ 写入和合并串行执行。编译后反序列化回读，第二次独立构建逐字节比较，最后才进入部署或人工任务内验证。
- 部署授权、启动游戏授权和自动化测试授权分别记录；运行时拒绝保留为拒绝证据，不能用离线 acceptance 覆盖。

## 阅读入口

- [详细索引](DETAILS_INDEX.md)
- [快速开始](QUICKSTART.md)
- [端到端工作流](01_EndToEnd_Workflow.md)
- [资源合同](02_HD2_Resource_Contracts.md)
- [材质、UV 与 namespace](04_Materials_Textures_Namespace.md)
- [编译、打包与部署](05_Compilation_Merge_Package_Deploy.md)
- [验证与证据](06_Validation_And_Evidence.md)
- [案例目录](case-studies/)
- [模板](templates/)

## 公开边界

不包含游戏 patch、个人模型、第三方 Mod、贴图、Material/TextureMap payload 或发布 ZIP。案例中出现的 FileID、阈值和 hash 只用于说明证据写法，不能直接复制到新 build。

