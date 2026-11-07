# 排障

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| 上衣 / 下装显示别的 mod 的贴图（黑上衣 + 蓝色、蓝鞋） | 套装的染色动画按材质名把 `_a0` 换成 `Armor_1061_*_Alb.<n>`，旧 mod 用这些名字放了自己的图集 | 材质改名为 `Mt_KarinOri_*`（[技术合同](TECHNICAL_CONTRACTS.md) §3） |
| 权重写上去不生效 / 部件跟着 Head 不动 | 骨骼不在平滑矩阵表里 | TotkMdl `smoothBones` 重建表 |
| Switch Toolbox / TotkMdl 打不开零售版模型 | 零售版顶点数据是 mesh codec | 用 Switch Toolbox 另存过的版本当基础模型 |
| TotkMdl 加载任何模型都抛异常 | Switch Toolbox 的 TexToGoFolder 读某些原版 txtg（很小的 `CmnTex_*`）会抛异常 | 给 TotkMdl 的游戏目录不放 `TexToGo/`（`romfs_st`） |
| 腰带下露出肚子，大腿穿出裙子 | 裙摆权重映射深了一段，裙子逆着布料动 | 按 Link 的裙骨段分权重，身体缩进裙内 1.2 cm（[重定向与比例](RETARGET_AND_PROPORTIONS.md) §5） |
| 狐耳在移动时放射状拉长 | 负权重 + 摆角大的骨骼（单点吊坠、跑动时的后发） | 只借铰链式、摆角小的骨骼，降低增益（[物理](PHYSICS.md) §4–§5） |
| 刘海走动后一直翘着 | 借的是单点吊坠，自转后没有回复力 | 改借铰链（Momi_A_2） |
| 狐耳僵硬，起跑急停不动 | 借的铰链只左右摆 | 本作头部 cloth 里没有不拉长耳朵的前后摆来源，接受；可试正权重的后发 |
| 头显得小 / 脖子长 | 只按 `S_BODY` 定头的缩放；按段拉伸让身体的实际倍率更大 | 量脚到 Head 关节的实际倍率；头部下沉 |
| 肩宽、方肩 | Link 的 Arm_1 固定在 ±18.3 cm | 在 T 姿势里压扁手臂轴线以上的部分；不要搬手臂 |
| 压肩后眨眼变差 | Body 物体里有脸，脸的两侧被压扁 | 扣掉 Neck / Head 子树和手的权重 |
| 眨眼完全不动 / 眼睛变形 | 普通权重下 Link 眼皮的行程太小；或权重被截成 8 位 | 带符号、可大于 1 的权重，脸部网格用 `Format_32_32_32_32_Single`，TotkMdl 重写 `_w` 属性（[面部](FACE.md)） |
| Syroot 读不了动画 BFRES | 本作的动画用 FMAA 块 | `fska.py` |
| yuzu「转储 RomFS」卡死 | 在 `Banc/` 里出错 | NxExtract 叠加基础版和更新 NCA |
| PhysicsTool / 探针 / ilspycmd 一启动就崩 | 本机 Windows 版本上的 CET 兼容 | 用 `dotnet <dll>` 运行，设 `DOTNET_EnableCETCompat=0` |
| PowerShell 5.1 算出的哈希不对 | 大于 0x7FFFFFFF 的十六进制字面量是负的 int32 | 常量写成 `[uint64]` 十进制，每步取 32 位掩码 |
| 5.1 下脚本里的中文乱码 | 文件没有 BOM | 存成带 BOM 的 UTF-8；bat 里先 `chcp 65001` |
| 存档改了又被还原 | 改的时候模拟器还开着，游戏下次保存时覆盖 | 先完全退出模拟器（工具会拒绝） |
| 本 mod 没生效 | 另一个排序更靠前的 mod 提供了同名文件或 RESTBL | 安装器会列出；改名或停用那个 mod |
