如果你觉得内容有帮助，可以前往https://ifdian.net/a/ccd775 赞助我以获得贴贴！
# Game Modding Shared Knowledge

供人和 agent 接续长线 Mod 项目的知识库与便携工具包。它包含十六款游戏的实际项目方法、成功与失败记录（其中十款附便携工具包）、19 个原项目迁移脚本、MK1 参数化工具、对马岛 / 西之绝境 / 战神5 构建器和公共运行工具；不需要注册 Skill。

## 从这里开始

1. 阅读 [PLAYBOOK.md](PLAYBOOK.md)，选择当前项目需要的阶段。
2. 打开相应 [便携工具说明](portable-kits/README.md)，用脚本的 --help 确认参数。
3. 创建独立项目，记录当前 build、源模型、工具和候选。暂停时保存下一步与证据。
4. 按当前游戏资源适配角色专属构建脚本；离线检查和实机验收分别记录。

| 游戏 | 知识入口 | 已验证历史范围 |
| --- | --- | --- |
| 真人快打1 | [MK1](games/mortal-kombat-1/README.md) | 多角色可见效果验收、骨架/骨盆/材质与 IoStore 排障；T1000 v8 材质复发仍在调查，未宣称全动作通过 |
| 鬼武者：新生 | [Onimusha WotS](games/onimusha-way-of-the-sword/README.md) | Karin→宫本武藏 v1.11.0：几何与 chain2 v17 次级物理均由用户实机确认；仅散装文件路线可用 |
| 怪物猎人：荒野 | [MHWs](games/monster-hunter-wilds/README.md) | Karin_Original→女装备 ch03_060_000 r6（BoneSystem 独立骨骼）：武器挂点、野外地图、裙摆碰撞与哑光材质经用户验收；依赖新版 REFramework 散装贴图加载；表情未单独签收 |
| 地平线：西之绝境 | [Horizon Forbidden West](games/horizon-forbidden-west/README.md) | Karin_Original 替换贝塔 v4（经 Mod Manager 角色切换扮演）：读档、外观、奔跑转身由 agent 实机自测（2026-10-02），用户未单独确认；身体只换 LOD0，无次级物理与表情 |
| 战神：诸神黄昏 | [God of War Ragnarök](games/god-of-war-ragnarok/README.md) | Karin_Original 替换奎托斯与同伴芙蕾雅：外观与行走由 agent 实机自测；用户实机看过芙蕾雅并反馈膝盖穿模，已修正共享源模型（烘焙 `kisekae_Knee`）后重建，修复版用户未单独确认；无次级物理与表情 |
| 对马岛之魂 导演剪辑版 | [Ghost of Tsushima](games/ghost-of-tsushima/README.md) | Karin 替换忠赖的铠甲：PicodraTech 第四构建经用户实机验收；Karin_Original 经用户认可（未指明版本，当时发布为 v4）（均为 2026-09-30，场景未逐项列出）；只替换 LOD0，无次级物理 |
| 鬼泣5 | [DMC5](games/devil-may-cry-5/README.md) | KarinPT→V：标题画面经用户确认；Karin_Original→Nero / Dante / V 三包 v1.1：Nero / Dante 实战经用户验收（含裙摆碰撞修复）；Original V 的 v1.1 物理未在游戏里加载，魔人形态、过场、立绘未检查 |
| 真三国无双 起源 | [DW Origins](games/dynasty-warriors-origins/README.md) | Karin PicodraTech→鸾翼将装：修复接缝/外套脏/翻领发糊（源模型重烘焙、UV 切开重排）经用户实机验收，脸部"可接受"；Karin_Original→鸾翼将装 v20261002a：从 FBX 构建、复用同网格的脸、按原版辅助骨分布迁移权重，仅由 agent 读档在旅馆/装备界面截图验证，用户未验收；无次级物理 |
| 杀手暗杀世界 | [Hitman WOA](games/hitman-world-of-assassination/README.md) | Signature Suit 0.1.0 在 Dartmoor 的基础动作 |
| 看门狗 | [Watch Dogs](games/watch-dogs/README.md) | 默认服装 v1.3.0，保留少数手指变形限制。2026-10-03 起不再需要 ZModeler：纯 Python 写出 XBG 的 1.4 / 1.5 和 Karin_Original 0.1.2 经用户实机认可；Karin_Original 只确认了读档和脸部。附通用 VRM 构建器，配置驱动，可逐字节重建 0.1.2 |
| 刺客信条黑旗记忆重置 | [Black Flag Resynced](games/assassins-creed-black-flag/README.md) | 角色替换及最终 1.6.1 修复，用户于 9 月 6 日确认 |
| 生化危机4重制版 | [RE4R](games/resident-evil-4-remake/README.md) | 多个角色案例，具体场景/build 分别记录 |
| 求生之路2 | [L4D2](games/left-4-dead-2/README.md) | 多个实机确认案例，另有静态完成待复测项目 |
| 绝地潜兵2 | [HD2](games/helldivers-2/README.md) | Unit/绑定/材质多案例；splat 等分支单独验收 |
| PRAGMATA | [Pragmata](games/pragmata/README.md) | Karin_Original→Hugh、Karin_kipfel→Diana v0.3.0：从源模型完整构建（refskel / 原生 rest 两条骨架路线、Env_Emissive 材质、从零插入 chain2 与 prefab 组件、裙摆碰撞体与节点胶囊）经用户验收；另为 Gamer JP 的两个替换 mod 加装物理（phys3 用户认可）；无表情，GPU 发丝与其它服装未覆盖 |
| 生化危机 安魂曲 | [RE9 Requiem](games/resident-evil-requiem/README.md) | Karin_Original→里昂 / 格蕾丝 v1.2.0：从源模型完整构建（refskel 路线、全部部件与 mdf2 变体、chain2 物理与无 Chain2 身体 prefab 注入、CollisionTarget=Self 让 chain2 自带碰撞体生效）；仅在「游戏模型」展柜由 agent 截图与运行时探针验证，实际游玩未测、用户未验收；另修复用户自制 Leon Karin 的乳胶感材质（离线） |

## 独立交接与验证

```powershell
python -m pip install -r requirements.txt
python -B tests/test_portable_tools.py
python -B tools/check_repository.py
python -B tools/export_kit.py --all --output ../Modding-Portable-Exports --zip
```

输出十份不依赖父仓库的目录，以及对应 ZIP/文件哈希清单。每份包含该游戏文档、脚本、公共层和安装依赖说明。[验证记录](portable-kits/VALIDATION.md) 明确哪些进行了组件测试，哪些还需要专用工具和游戏实测。

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

单独导出某一款时运行（导出目录旁会生成同名 ZIP 和 `.files.json` 清单）：

```powershell
python -B tools/export_kit.py --game watch-dogs --output ../WatchDogs-Portable --zip
```

## 内容与证据

[工具来源](references/TOOL_SOURCES.md)、[迁移清单](portable-kits/PROVENANCE.json)、[能力边界](references/CAPABILITY_GAPS.md)、[项目模板](templates/)、[机器目录](CATALOG.json)。

历史项目命令可能依赖未迁移的角色脚本。540 处本地证据引用已转到 [来源索引](SOURCE_REFERENCES.md)，不会伪装成公开可下载文件。旧知识中的固定骨数、偏移、材质 ID 和阈值是案例值；新项目以当前资源测量为准。

原模型、参考 Mod、游戏资源、账号、DLL 和私人候选不随仓库发布。原创文档和脚本的使用权说明见 [NOTICE.md](NOTICE.md)。
