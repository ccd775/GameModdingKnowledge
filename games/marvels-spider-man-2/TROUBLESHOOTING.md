# 排障手册

除标注外，均为本项目实测。

## 1. 加载与显示

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 标题画面 Peter 身体整件不显示，头照常（T1） | 删了 Ziva2 / AnimVertInfo2 / VertSmooth，但 `ModelBuilt` 的 0x10000000 位没清 | 删 anim-vert 段时同时清这一位（T2 通过） |
| 标题场景加载时崩溃，`Spider-Man2.exe+0x2b40c6f` 读空指针，日志里有 CreateGraphicsPipelineState 失败（T4） | 用了 `*_sand` 材质图，它只给 fmt 5 网格用 | 人物用 `basic_normal_gloss(_subsurface)` |
| 标题画面是 Karin，进游戏后还是原版战衣（T4b） | 存档装备的战衣是另一个模型 | 替换全部 108 个目标模型（`sm2_batch.py`） |
| 某些外观预设（tuxedo、teacher、spider_suit、dj_suit）里角色隐身（T5，离线发现） | Karin 只放在 body/Default 槽，这些 Look 组看不到 | `cover_looks` 给这些组再挂同一块几何 |
| 用 ALERT 读资产头后，长度或偏移错乱 | ALERT 按 i29 的 36 B 固定头切，i30 的头是变长的 | 按 `pairs` / `extra` 字段读变长头 |
| 新贴图在游戏里不生效 | `.stage` 条目没带贴图 meta | 带上 72 B meta（STG 包装 flags 2） |
| 角色变形、权重不生效 | 用到的关节没有 0x80 位 | 重映射后补 0x80（`flag_skinned`） |

## 2. 物理

| 现象（用户反馈或截图） | 原因 | 处理 |
| --- | --- | --- |
| 耳朵、尾巴、头发被拉成面条，一端缩到脚下一团（T9） | 追加的 0x01 关节没有 `ModelMirrorIds` 项，游戏里停在模型原点 | 给新的 0x01 关节补自映射项并更新 mirror count |
| 选战衣 / 关菜单后物理只动约 1 秒，然后卡成一团（T10） | T5 链记录的第 3、4 字写成了 `(弯曲数, 首链节) (粒子数, 首粒子)`，从第 1 条链起粒子错位 | 改为 `(链节数, 首粒子) (粒子数, 0)`；回归比较时非规格化浮点按位比较 |
| 链条按重力自然垂下，但约 1 秒后冻结（T11） | 战衣部件没有 owner actor，过不了每帧门控 | 动力学放到有 owner + AnimController 的模型上（[物理](PHYSICS.md) §3–§4） |
| 只在按 ESC 的瞬间有物理（T12 / T13） | 同上；改 ModelBuilt 包围球半径无效 | 同上 |
| 物理持续、柔软，但全部垂到底，耳朵塌在头顶（T15） | 约束类型 0（Simple）不做锥限制 | 改类型 1（Cone） |
| 耳朵几乎不动，其它部件太弹（T16） | 锥角太小（碰锥壁反弹）、阻尼低、重力小 | 放宽锥角、阻尼 0.35–0.5、重力 -0.5 ~ -2.5（T17） |
| 追加的 HeroSuitAddition 不生效，身体已去链所以头发完全消失（T18） | 同类型组件只认第一条 | 改用头部载体 |
| 头发会绘制、跟随头，但一直冻结（T19 / T20） | 头 actor 的 NeverCull = false，载体关节包围球只有约 1 mm，相机永远在更新距离外 | NeverCull = true，关节包围球放大到 1 m（T21） |
| 尾巴有物理但不跟身体：中段错位，爬行 / 下蹲时悬在胯部高度（T21） | HeadManager 只映射 a_body / chest / neck / head / 锁骨，载体的 pelvis 跟着 a_body；尾根还有 spine 权重回退到 a_body | 载体加 pelvis / spine / spine_helper1，并加进三个 actor 的 CustomJointMap（T22） |
| 带面罩战衣出现两套头发（T21 测试期间） | 战衣身体没去链，载体又画了一套 | 91 个身体去链（T23） |

## 3. 工具与环境

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| scp 中途 Connection closed，之后 SSH 握手一直超时 | 远程链路（端口映射）断开 | 用户重启远程或重开映射；**每次上传后核对 SHA-256** |
| `Connection refused` | 远程工具重启后端口映射没有自动恢复 | 请用户重新启用映射 |
| 从 SSH 启动的游戏看不见，截图黑屏 | SSH 在 session 0 | 游戏从用户会话启动（用户自己点，或用桌面代理） |
| `test_dyn_model` 在静态战衣上报 IndexError | 去链后的身体没有 `karin_*` 关节 | 没有链关节的模型按静态处理（已修） |
| 家族判断错，Miles 经典战衣用了 Peter 的对齐 | 只看 `/hero_spiderman_miles_` 前缀 | 用文件夹名里是否有 `miles` 判断 |
