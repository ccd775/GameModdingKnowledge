# 验证与发布

## 1. 离线闸门

- 构建日志有 `[karin_build] DONE`；报告里 dyng 的节点 / 链接 / 三角形 / 模拟节点数与上一版一致，或者变化正好是这一版要改的；`dyng_bone_matrix_err` 在 1e-5 以下。
- `fix_cr2w_skeleton_names.py` 的输出：dyng `fixed 230 bone names`、w3fac `fixed 356 bone names`（换模型后数字会变，但不能是 0）。
- `checks/rule_check.py`：所有 look-at 节点的滚转误差 0°。
- 改了身体、裙子或碰撞：`checks/blender/skirt_walk_sink.py`（走、快走、慢跑、冲刺各 8 帧），`snug` / `current` 两种模式都不穿。
- 改了头发或头部碰撞：`checks/blender/idle_view.py`（全身）和 `idle_head.py`（头部）渲染目标形状，`checks/blender/face_geom.py` 看头发离脸的距离和碰撞中心。
- 改了比例：`karin_preview.py`（导出的网格重新导入、包围盒与源 blend 一致），再在原版动画的姿势里看肩部。
- 打包：829 个文件；`metadata.store` 重新生成；记下两个文件的 SHA-256。
- 换游戏版本：`checks/regen_metadata_compare.py` 先确认 store 写出器仍然对得上原版。

**便携包复现（2026-10-23）**：在一个全新的工作目录里依次运行便携包的 `prepare.ps1` 和 `pipeline.ps1`（含 Blender，不部署）：

- 829 个打包文件中 822 个与 v0.4.4 逐字节相同（全部 817 个物品模板、dyng、w3fac、脸部网格、两个存根）；
- 身体 `karin_body.w2mesh`：顶点顺序不同，`checks/blender/cmp_w2mesh.py` 比较顶点（位置 + 按骨名的权重）、面、UV 的多重集合和骨组，全部相同。
  同一个便携包连跑两次，顶点顺序也不同，这是导出器的行为，不是移植造成的；
- 6 张 xbm：写着源 PNG 的绝对路径，换了工作目录就不同；把路径归一化后每张只差 22 个字节，都在 CR2W 头部的文件长、偏移和 CRC 字段上，像素数据相同；
- 因此 `blob0.bundle` / `metadata.store` 的哈希与 v0.4.4 不同（长度相同：8 041 799 / 147 450 B）；
- 用便携包在新工作目录里生成的三个物品模板，加上项目构建 v0.4.4 时的 depot（网格、贴图、dyng、w3fac），经便携包的 `build_mod.py` + `w3metadata_write.py`
  打出的 `blob0.bundle`（`597794E9…0090C16A`）和 `metadata.store`（`177B780A…12A63B9629`）与 v0.4.4 逐字节相同。
- 同一工作目录里，便携包的 `rule_check.py`（91 个节点，0°）、`skirt_walk_sink.py`（全刚性 1 个顶点 0.7 cm，当前 / snug 0）、`face_geom.py`
  （最佳中心 (0.02, −0.02)，平均夹角 13.5°；采用的 (0.03, −0.02) 为 13.7°）的结果与项目里原脚本的结果一致；`idle_view.py`、`idle_head.py`、`karin_preview.py` 正常出图，`cmp_w2mesh.py` 对不同的网格（脸）报告不等。

## 2. 实机闸门

1. 用户在玩时不部署；部署前确认游戏可以被结束。部署后核对游戏目录里两个文件的 SHA-256。
2. 读威伦的测试存档：正面、背面、**侧面**待机截图（比例、肩、形状），和 `idle_view.py` 的目标形状对比。
3. 冲刺急停：0.5 秒间隔连拍 10 秒左右，链甩出去后应在几秒内回到原形，不折、不扭、不卡在外翻。走路急停同样看一次（尾巴折叠就是走完停下才出现的）。
4. 跳跃、战斗（拔剑、举过头顶的攻击）看肩部和裙摆；游泳看头发。
5. 表情：新游戏开场过场（浴室），连拍看眨眼和口型。
6. 收尾：退出游戏或留给用户；清掉临时截图；结束残留的按键脚本进程。

## 3. 发行包

```text
modKarinReplacer_v0.4.4.zip
  mods/modKarinReplacer/content/blob0.bundle
  mods/modKarinReplacer/content/metadata.store
  README.md          （这一版改了什么、测试状态、以前版本的修改、内容、已知限制）
  SHA256.txt         （两个文件的长度和 SHA-256）
  安装说明.txt        （适用版本、包内容、安装、看不到效果时、校验、卸载；UTF-8 BOM、CRLF）
```

安装说明要写：把 `mods` 文件夹复制到游戏目录（和 `bin`、`content` 同级），覆盖旧版；不要多套一层文件夹；不需要脚本合并或前置 mod；
`EnabledLocal=true`；和其它改杰洛特外观的 mod 冲突；只替换模型资源、不写存档，装卸都不影响存档；未在 HairWorks 开启时测试。
用户要求每个发行都是带 README 和安装说明的 zip。

| 版本 | blob0.bundle SHA-256 | metadata.store SHA-256 | zip SHA-256 |
| --- | --- | --- | --- |
| v0.4.3 | `8C4D15B2DA427B8CB1706A1562A0277EF4D45E68DBCCD7EFE9BF2F49C58AE0C9` | `74407EBDB6170FC7EF82302C5F00A3DC4A5BBD7CEF127067E358A368962B8489` | `D7212A8416472F3C10799B2937ADC91DA20046E5823FC7403C9360CD866FE1EC` |
| v0.4.4 | `597794E9A0E1A1982CDFFF5E6CFBAC1B601D434C174EFC60FE22AD4B0090C16A` | `177B780AA74E6572EAB34DF9CB5967BA19C931603484A7E59C8B9E12A63B9629` | `D0B4708691E697EAEBA0702DD1EDFCDBD36626D13FB21B0C20684CB91B3DC05F` |

## 4. 证据分层与未测场景

| 项目 | 证据级 |
| --- | --- |
| 加载（bundle v5 + store v7）、空模板隐藏杰洛特（T1） | `runtime-load-pass`（agent） |
| 外观与动作：夜晚 / 正午（冥想）、跪、走、冲刺、跳、银剑战斗、物品栏（r2） | `runtime-load-pass`（agent 截图） |
| 比例：脖子、上身、肩（v0.2 → v0.4.0） | `runtime-load-pass`（agent 截图）；用户在之后的轮次没有再提，但没有明确确认 |
| 表情：开场过场眨眼、口型（v0.1、v0.2） | `runtime-load-pass`（agent 连拍） |
| 物理：头发、尾巴保形、跑动不穿脸（v0.4.3） | `runtime-confirmed`（用户：「看起来好了」） |
| 走动时髋侧不穿裙（v0.4.4） | `offline-accepted`；已部署，待用户实测 |
| v0.4.3 走动时髋侧少量穿出裙片 | `runtime-rejected`（用户） |

未测或未逐项检查：骑马、主菜单背景里的杰洛特（独立实体，没有替换）、HairWorks 开启、带表情构建的战斗、腿抬到接近水平的动作对裙子、
游戏中与 NPC 的对话（只看过开场过场）、DX11 模式、其它游戏版本。已知限制：剑鞘穿过双马尾；洗澡等裸体场景里 Karin 仍穿着衣服（衣服和身体是同一个网格）；
物品栏灯光下脸部阴影很硬；举手过头时肩胛附近有褶皱；表情与原始形状键约差 8 %。
