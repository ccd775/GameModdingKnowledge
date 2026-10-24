如果你觉得内容有帮助，可以前往https://ifdian.net/a/ccd775 赞助我以获得贴贴！
# Game Modding Shared Knowledge

供人和 agent 接续长线 Mod 项目的知识库与便携工具包。它包含二十五款游戏的实际项目方法、成功与失败记录（其中十八款附便携工具包）、19 个原项目迁移脚本、MK1 参数化工具、对马岛 / 西之绝境 / 战神5 构建器、浪人崛起的 KT 引擎格式工具、龙之信条2 的 DD2Tool 与 REFramework 注入脚本、师父的 UE 4.26 编辑器插件与 Blender 构建器、幻兽帕鲁的 UE 5.1 编辑器插件与 KawaiiPhysics 离线模拟器、漫威蜘蛛侠2 的 i30 格式读写与安装器、往日不再的 UE 4.11 烘焙动画蓝图插节点与面部权重求解工具、巫师3 次世代版的 bundle / metadata.store 读写与 dyng / mimic 生成器、刺客信条：奥德赛的 forge v28 原地安装器与 Reflex3 物理骨架生成器和公共运行工具；不需要注册 Skill。

## 从这里开始

1. 阅读 [PLAYBOOK.md](PLAYBOOK.md)，选择当前项目需要的阶段。
2. 打开相应 [便携工具说明](portable-kits/README.md)，用脚本的 --help 确认参数。
3. 创建独立项目，记录当前 build、源模型、工具和候选。暂停时保存下一步与证据。
4. 按当前游戏资源适配角色专属构建脚本；离线检查和实机验收分别记录。

| 游戏 | 知识入口 | 已验证历史范围 |
| --- | --- | --- |
| 真人快打1 | [MK1](games/mortal-kombat-1/README.md) | 多角色可见效果验收、骨架/骨盆/材质与 IoStore 排障；T1000 v8 材质复发仍在调查，未宣称全动作通过 |
| 龙之信条2 | [Dragon's Dogma 2](games/dragons-dogma-2/README.md) | Karin PicodraTech v1.3.0 / Karin_Original v1.0.1 替换玩家角色（build 25290080 + DLC）：不改原生文件，REFramework Lua 在游戏构建身体时递入网格 / 材质 / chain，皮肤烘焙改道、体型表清空、骨驱动表情；用户本机实机用到 PicodraTech v1.2.0（比例问题由用户发现后修复），Original v1.0.1 裙摆修复经用户确认（「这次好了」）；v1.3.0、表情与 DLC build 由 agent 在测试机实机自测（读档、装备预览、头像、物理、表情、拍照、走跑跳攻蹲），表情幅度用户未单独确认；过场 / 攀爬 / 死亡未测，只替换女性人类 |
| 鬼武者：新生 | [Onimusha WotS](games/onimusha-way-of-the-sword/README.md) | Karin→宫本武藏 v1.11.0：几何与 chain2 v17 次级物理均由用户实机确认；仅散装文件路线可用 |
| 怪物猎人：荒野 | [MHWs](games/monster-hunter-wilds/README.md) | Karin_Original→女装备 ch03_060_000 r6（BoneSystem 独立骨骼）：武器挂点、野外地图、裙摆碰撞与哑光材质经用户验收；依赖新版 REFramework 散装贴图加载；表情未单独签收 |
| 地平线：西之绝境 | [Horizon Forbidden West](games/horizon-forbidden-west/README.md) | Karin_Original 替换贝塔 1.1.0（经 Mod Manager 角色切换扮演）：过场动画中的手指修复经用户确认；面部绑到 719 面部骨（照片模式表情可用，不眨眼）；裙摆、双马尾、尾巴借用 Beta 的 PBD 粒子摆动，经用户认可（2026-10-24）；身体只换 LOD0 |
| 战神：诸神黄昏 | [God of War Ragnarök](games/god-of-war-ragnarok/README.md) | Karin_Original 替换奎托斯与同伴芙蕾雅：外观与行走由 agent 实机自测；用户实机看过芙蕾雅并反馈膝盖穿模，已修正共享源模型（烘焙 `kisekae_Knee`）后重建，修复版用户未单独确认；无次级物理与表情 |
| 对马岛之魂 导演剪辑版 | [Ghost of Tsushima](games/ghost-of-tsushima/README.md) | Karin 替换忠赖的铠甲：PicodraTech 第四构建经用户实机验收；Karin_Original 经用户认可（未指明版本，当时发布为 v4）（均为 2026-09-30，场景未逐项列出）；只替换 LOD0，无次级物理 |
| 鬼泣5 | [DMC5](games/devil-may-cry-5/README.md) | KarinPT→V：标题画面经用户确认；Karin_Original→Nero / Dante / V 三包 v1.2：Nero / Dante 实战经用户验收（含裙摆碰撞修复），V 实战与过场经用户确认（含过场拉伸修复）；Nero / Dante 的过场修补、魔人形态、立绘未检查 |
| 真三国无双 起源 | [DW Origins](games/dynasty-warriors-origins/README.md) | Karin PicodraTech→鸾翼将装：修复接缝/外套脏/翻领发糊（源模型重烘焙、UV 切开重排）经用户实机验收，脸部"可接受"；Karin_Original→鸾翼将装 v20261002a：从 FBX 构建、复用同网格的脸、按原版辅助骨分布迁移权重，仅由 agent 读档在旅馆/装备界面截图验证，用户未验收；无次级物理 |
| 浪人崛起 | [Rise of the Ronin](games/rise-of-the-ronin/README.md) | Karin_Picodra：头发 / 脸 / 下身材质 / 背标 / 上衣 UV / 手指动画逐项经用户验收（20260908f 为基线）；20261004a 的腿部分段权重、13 张共用贴图恢复（NPC 发白）与下身 SHADING 仅离线检查；Karin_Original 从 FBX 构建，两种头部变体由 agent 实机自测；无物理与表情，室内绑腿未解决 |
| 剑星 | [Stellar Blade](games/stellar-blade/README.md) | Karin_Original→EVE 初始服装 `CH_P_EVE_09` v1.0：从 VRM 完整构建（UE 4.26 SB 分支，IoStore）；后处理 AnimBP 由编辑器插件无界面生成（ControlRig、运行时改腿长、28 个 KawaiiPhysics，物理链借用游戏骨架配件链）；比例、材质、物理与裙摆穿模修复经用户实机验收；表情未在游戏里检查，服装变体未替换 |
| 杀手暗杀世界 | [Hitman WOA](games/hitman-world-of-assassination/README.md) | Signature Suit 0.1.0 在 Dartmoor 的基础动作 |
| 看门狗 | [Watch Dogs](games/watch-dogs/README.md) | 默认服装 v1.3.0，保留少数手指变形限制。2026-10-03 起不再需要 ZModeler：纯 Python 写出 XBG 的 1.4 / 1.5 和 Karin_Original 0.1.2 经用户实机认可；Karin_Original 只确认了读档和脸部。附通用 VRM 构建器，配置驱动，可逐字节重建 0.1.2。2026-10-06 物理（链、大衣布料）经实机验收；2026-10-10 私有头部材质兼容 Windy City II；2026-10-24 面部表情（改写面部定义 dpdx）第一轮实机：嘴会动，眨眼和视线的修正版尚未实机 |
| 刺客信条黑旗记忆重置 | [Black Flag Resynced](games/assassins-creed-black-flag/README.md) | 角色替换及最终 1.6.1 修复，用户于 9 月 6 日确认 |
| 生化危机4重制版 | [RE4R](games/resident-evil-4-remake/README.md) | 多个角色案例，具体场景/build 分别记录 |
| 求生之路2 | [L4D2](games/left-4-dead-2/README.md) | 多个实机确认案例，另有静态完成待复测项目 |
| 绝地潜兵2 | [HD2](games/helldivers-2/README.md) | Unit/绑定/材质多案例；splat 等分支单独验收 |
| PRAGMATA | [Pragmata](games/pragmata/README.md) | Karin_Original→Hugh、Karin_kipfel→Diana v0.3.0：从源模型完整构建（refskel / 原生 rest 两条骨架路线、Env_Emissive 材质、从零插入 chain2 与 prefab 组件、裙摆碰撞体与节点胶囊）经用户验收；另为 Gamer JP 的两个替换 mod 加装物理（phys3 用户认可）；无表情，GPU 发丝与其它服装未覆盖 |
| 师父 | [Sifu](games/sifu/README.md) | Karin_Original→女主默认服装 v6：从 VRM 构建（W 骨架、游戏面部姿势资产驱动表情、眼球转动）、后处理动画蓝图里的 RigidBody 骨链、NvCloth 裙摆（插件补上 backstop）；裙摆按用户实机反馈改了五轮后「基本好了」；另外四个 Karin 模型（两套 PicodraTech、Umbrella、Y）v1 只做了离线检查，未进游戏；对话口型、过场、第 2/3 套服装未测 |
| 幻兽帕鲁 | [Palworld](games/palworld/README.md) | Karin_Original→女性玩家默认服装 r4：从 VRM 构建（Karin 自己的比例、11 个面部形变、隐藏发型），服装层动画蓝图里 7 个 KawaiiPhysics 节点；加载、物理运行、眨眼经用户实机确认；r3 手感偏硬、跑动时大腿穿出裙片，r4 用 KawaiiPhysics 1.17.1 的离线移植在游戏跑步动画上复现后重调，手感待用户判断；其余表情、游泳 / 滑翔 / 战斗中的裙摆未测 |
| 漫威蜘蛛侠2 | [Marvel's Spider-Man 2](games/marvels-spider-man-2/README.md) | Karin_Original→Peter / Miles 全部 108 个战衣与便装模型（v1：一次拟合按骨架签名批量写入、面部骨骼表情、裙子权重、头比例 1.45，用户实机验收）；v2：逆向 AnimDynamics 每帧门控后，把弹簧物理挂到带面罩战衣共用的头 actor 上（NeverCull、关节包围球、HeadManager 补胯部关节），91 套带面罩战衣经用户抽查确认；便装与 young 无物理，拍照模式 / 过场 / boss 战未逐项测 |
| 往日不再 | [Days Gone](games/days-gone/README.md) | Karin_Original→迪肯 t31（`days_gone_classic` 分支，Bend 改版 UE 4.11）：全部几何放进头部网格，往游戏的烘焙动画蓝图里插入 91 个逐骨 AnimDynamics 弹簧与 10 个 CopyBone；表情蒙到迪肯的 280 个面部关节，眨眼用网格专用放大骨，对话口型按 17 个口型逐顶点解权重；物理、眨眼、口型、头发幅度各经用户实机确认；照片模式右侧双马尾会被拉伸（未修），过场、骑车与其它服装未逐项测 |
| 巫师3 次世代版 | [The Witcher 3](games/the-witcher-3/README.md) | Karin_Original→杰洛特 v0.4.3（5.01，DX12）：不改脚本，覆盖全部 817 个杰洛特物品模板，发型物品承载整个 Karin 网格和 dyng 次级物理，头部物品带从形状键解出的 Karin 自己的表情骨架；dyng 靠挂锚点、滚转规则、刚性形状链接和头部碰撞代理保形，双马尾 / 侧发停下后的形状和跑动不穿脸经用户实机确认（「看起来好了」）；v0.4.4 修走动时髋侧穿出裙子，离线通过、待用户实测；骑马、HairWorks、游戏内 NPC 对话未测 |
| 刺客信条：奥德赛 | [AC Odyssey](games/assassins-creed-odyssey/README.md) | Karin_Original→卡珊德拉 v8（Ubisoft Connect v1.5.6）：不论装备的整角色替换（VisualMaster 去掉装备列，头部 / 头发表去掉脸和发型，Karin 的 LOD0 / LOD1 原地顶替卡珊德拉专属的身体 LOD，`ACD_Tex1` 材质），原地追加安装到 patch_01、SharedGroup 和 DLC forge 里的每一份副本；次级物理放进重建的头发物理骨架（Reflex3 type 21 记录），下颌 / 眼睑 / 虹膜用绑定偏移杠杆蒙到卡珊德拉的头部骨架；模型与材质、双马尾物理、v8 的眼睑（低增益、常态稳定）经用户实机确认（「看起来可以了」），眨眼按测量换算预计只闭约 20–35 %；尾巴 / 耳朵的软化未单独评价，对话 / 过场表情、DLC 区域未测 |
| 生化危机 安魂曲 | [RE9 Requiem](games/resident-evil-requiem/README.md) | Karin_Original→里昂 / 格蕾丝 v1.2.0：从源模型完整构建（refskel 路线、全部部件与 mdf2 变体、chain2 物理与无 Chain2 身体 prefab 注入、CollisionTarget=Self 让 chain2 自带碰撞体生效）；仅在「游戏模型」展柜由 agent 截图与运行时探针验证，实际游玩未测、用户未验收；另修复用户自制 Leon Karin 的乳胶感材质（离线） |

## 独立交接与验证

```powershell
python -m pip install -r requirements.txt
python -B tests/test_portable_tools.py
python -B tools/check_repository.py
python -B tools/export_kit.py --all --output ../Modding-Portable-Exports --zip
```

输出十八份不依赖父仓库的目录，以及对应 ZIP/文件哈希清单。每份包含该游戏文档、脚本、公共层和安装依赖说明。[验证记录](portable-kits/VALIDATION.md) 明确哪些进行了组件测试，哪些还需要专用工具和游戏实测。

## 下载便携包

[v0.2.0 Release](https://github.com/ccd775/GameModdingKnowledge/releases/tag/v0.2.0) 提供十款附便携工具包的游戏的独立目录 ZIP，以及对应的文件 SHA-256 清单（同名 `.files.json`）。下载后解压整个包，从包内 README.md 开始。[v0.1.0 Release](https://github.com/ccd775/GameModdingKnowledge/releases/tag/v0.1.0) 保留原六游戏包，不再更新。

| 游戏 | 独立便携 ZIP |
| --- | --- |
| 真人快打1 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.2.0/mortal-kombat-1.zip) |
| 地平线：西之绝境 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.2.0/horizon-forbidden-west.zip) |
| 战神：诸神黄昏 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.2.0/god-of-war-ragnarok.zip) |
| 对马岛之魂 导演剪辑版 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.2.0/ghost-of-tsushima.zip) |
| 杀手暗杀世界 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.2.0/hitman-world-of-assassination.zip) |
| 看门狗 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.2.0/watch-dogs.zip) |
| 黑旗记忆重置 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.2.0/assassins-creed-black-flag.zip) |
| 生化危机4重制版 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.2.0/resident-evil-4-remake.zip) |
| 求生之路2 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.2.0/left-4-dead-2.zip) |
| 绝地潜兵2 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.2.0/helldivers-2.zip) |

浪人崛起、龙之信条2、师父、幻兽帕鲁、漫威蜘蛛侠2、往日不再、巫师3 与奥德赛的便携包是 v0.2.0 之后加入的，还不在 Release 里，请用下面的命令自行导出。

单独导出某一款时运行（导出目录旁会生成同名 ZIP 和 `.files.json` 清单）：

```powershell
python -B tools/export_kit.py --game watch-dogs --output ../WatchDogs-Portable --zip
```

## 内容与证据

[工具来源](references/TOOL_SOURCES.md)、[迁移清单](portable-kits/PROVENANCE.json)、[能力边界](references/CAPABILITY_GAPS.md)、[项目模板](templates/)、[机器目录](CATALOG.json)。

历史项目命令可能依赖未迁移的角色脚本。540 处本地证据引用已转到 [来源索引](SOURCE_REFERENCES.md)，不会伪装成公开可下载文件。旧知识中的固定骨数、偏移、材质 ID 和阈值是案例值；新项目以当前资源测量为准。

原模型、参考 Mod、游戏资源、账号、DLL 和私人候选不随仓库发布。原创文档和脚本的使用权说明见 [NOTICE.md](NOTICE.md)。
