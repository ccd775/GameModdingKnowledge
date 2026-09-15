# Mortal Kombat 1 角色替换 Playbook

公开快照：2026-09-15。先读[当前证据范围](STATUS.md)；历史验收、后续复发和待安装候选分别记录。公开工具及独立导出命令见[便携入口](../../portable-kits/mortal-kombat-1/README.md)。

适用于**源 Blend/FBX → 游戏原生骨架 → 定制 UE Cook → IoStore → 游戏测试**。由 Karin 袖子修复、断肢隐藏以及 Karin Nyako Normal 替换辛黛尔的本机实践归纳。

验收基线：Steam build **17941244**；Nyako→Sindel 最终候选 UCAS SHA-256：
`e0ab3dd65b4faf9925c3ae2aef8a68b62c481a5308484bb99bc994e9373d09ee`。
用户确认贴图正确、原版头发隐藏，并在腿部修正版后表示“我觉得可以了”。这是本案例可见效果验收，**不代表全部动画、全部皮肤、全部终结技或联网兼容性已测试**。

## 阅读路线

9b3d 四角色当前为 T1000 v8、其余 v5b；T1000曾正常，后续未切换装备/调色板、预览前18位角色后灰色颗粒复发，hash仍为v8，材质问题继续调查。腰部保持接受状态。装备消费链、腹部辅助骨与局部保护见 [9b3d案例](cases/9B3D_QUAD.md)。

Umbrella两角色v8材质和胯部获当前可见效果接受；柯南武器误隐藏的v9候选离线通过但未安装。原生MI内容与store不一致、根骨单位错误、共同骨盆场只报告未执行、运行时赋材质及精确撤销武器覆盖见[案例](cases/UMBRELLA_HOMELANDER_CONAN.md)。

2026-09-14 UnendingFlame → Sektor / Kenshi / Cyrax V9获用户“挺好的”确认。收肩只改X而保留原生高差的失败路线、三维肩锚点和局部验证见[肩线指南](SHOULDER_CONTOURS.md)；历史与接受边界见[案例](cases/UNENDINGFLAME_TRIO.md)。默认NoShared缓存仍可指向引擎公共目录，排障见[打包指南](PACKAGING.md#缓存隔离慢启动与分阶段续跑)。

2026-09-14 Riptide 三角色最终接受版本为 Ermac v7、Noob v6、Ashrah v5。真实原生 MI、自发光覆盖、源 high heel 与整鞋朝向、手机玻璃及骨盆比例经验见 [Riptide 案例](cases/RIPTIDE_TRIO.md)；具体原生属性增量修改见 [材质补丁指南](NATIVE_MATERIAL_PATCHING.md)。

2026-09-14 Karin Y → Rain / Smoke / Scorpion v9获用户“可以了”确认。单位/形态键导出、黑色图集页、指段朝向、头肩与衣长、腰封连接及误隐藏手杖的经验见 [Karin Y 三角色](cases/KARIN_Y_TRIO.md)。这是当前可见效果接受，不代表全动画或断肢认证。

2026-09-14 Karin Chrome → Reiko / Liu Kang Candidate-v6b 获用户“已经正常了”确认。Normal误作ART/CSM导致变暗、布料helper退化到人体祖先造成大衣长片、逐指roll冲突及UE未重导入便Cook旧资产的经验见 [Karin Chrome双角色](cases/KARIN_CHROME_REIKO_LIUKANG.md)。刚性手掌是本案有界回退，不默认用于要求逐指动作的新角色。

2026-09-12 补充 PicodraTech Karin → Mileena / Tanya / Li Mei 三角色案例。用户在修复骨盆穿插、平底鞋和美莲娜原版头部后表示“我看过了，感觉都可以了”。当前可见效果已接受，未扩大到完整动画/断肢测试。版本、哈希和失败路线见 [三角色案例](cases/PICODRATECH_TRIO.md)。

2026-09-13 尾部后续：Kitana tail-v2和上述三角色tail-v11均获用户可见效果确认；静止源形、锚点与增量迁移经验见 [附属物指南](APPENDAGES.md)，旧版仍保留为历史。

| 目的 | 文档 |
| --- | --- |
| 制作下一个角色 | [端到端流程](PLAYBOOK.md) |
| 防止头身比例、胯部/裤子问题跨任务复发 | [重定向构建前检查](RETARGET_CHECKS.md) |
| 准备工具与来源记录 | [工具环境](TOOLS.md) |
| 骨骼、比例、袖子、鞋袜及屈膝 | [模型与绑定规范](RIGGING.md) |
| 手掌/指节扭曲、收头肩后上衣变短、腰封挂件悬空 | [手部与上半身](UPPER_BODY_HANDS.md) |
| 长脖子、肩宽修正后头颈不协调 | [头颈比例与局部修复](NECK_PROPORTIONS.md) |
| 颈根到肩峰呈长斜坡、源锁骨方向丢失 | [肩宽与肩线](SHOULDER_CONTOURS.md) |
| 尾巴/飘带扭曲、局部恢复与跨角色迁移 | [附属物源形恢复](APPENDAGES.md) |
| 材质、Atlas、透明与断肢 | [材质和可见性](MATERIALS_VISIBILITY.md) |
| 灰材质、强绿光、原生标量修改/新增 | [原生材质最小补丁](NATIVE_MATERIAL_PATCHING.md) |
| UE、IoStore、加载、备份 | [Cook 与打包](PACKAGING.md) |
| 原版未替换、闪退、灰模、变形 | [故障对照表](TROUBLESHOOTING.md) |
| 判断什么才算完成 | [验证与交接](VALIDATION.md) |
| 已确认与被否定的经验 | [Nyako→Sindel 案例](cases/NYAKO_SINDEL.md) |
| Karin Chrome的D/N通道、刚性手掌、大衣连续躯干场与Cook身份门禁 | [Reiko / Liu Kang 案例](cases/KARIN_CHROME_REIKO_LIUKANG.md) |
| UnendingFlame三角色的比例/胯部/图集/饰物案例 | [UnendingFlame 三角色](cases/UNENDINGFLAME_TRIO.md) |
| 可直接复用的小工具 | [脚本说明](scripts/README.md) |
| 本指南与脚本是否经过测试 | [QA记录](QA.md) |
| 开始新工程 | [项目模板](templates/PROJECT_STATE.md)、[配置模板](templates/project.example.json) |

## 能复用什么

- 证据链、源文件锁定、骨架原始数据检查、逐变量候选、回读、安装哈希和回滚流程。
- 已验证的单材质/单图集路径，作为新目标的**优先试验路线**，不是承诺所有材质都兼容。
- 原生头发索引退化隐藏的思路；必须重新定位和核对每个目标的索引缓冲。
- 参数化图集拼合、受哈希约束的索引隐藏、raw chunk 比较、完整三件套部署预检工具。

## 不在这个指南中承诺

不提供一键全角色重定向、不附带模型/游戏 payload/UE 安装包/第三方 Mod、不保证完整发丝物理或断肢系统重建。不自动修改 Steam 启动项或用户配置，不自动添加新的角色隐藏开关。

已接入仓库 `export_kit.py --game mortal-kombat-1` 及 `--all`。独立使用请导出完整单游戏包，使公共说明、依赖、测试和脚本一并携带。GitHub旧v0.1.0 Release仍为六游戏历史包，本次未追加Release附件。脚本只需标准Python；图集工具额外需要Pillow。
