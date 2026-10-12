# 验证与发布

## 1. 工具级闸门（开工前）

可用命令：`chainrt` / `mdfrt`（chain / MDF 读入写出比较）、`meshconv` 往返、`meshinfo`、`toc` + `resolve` + `extract`。本项目实际做过的：

- 新 build：dump 新 TOC，用旧路径表 resolve，把依赖的原生文件与上一 build 逐字节比较（[技术合同](TECHNICAL_CONTRACTS.md) §6）。
- 原生 `body_000_f` 经 `meshconv "DD2 (old v2)"` 转给 RE Mesh Editor 0.66 作 Blender 参照；Karin 网格经 `meshinfo` 回读骨表。
- 原生 chain 用 `chaininfo` dump 全部字段作模板与参照（`angleMode`、`angleLimitRadius`、碰撞标志）。

## 2. 构建后闸门

构建脚本里的断言与检查：

- 加权骨 ≤ 256（断言）；每顶点 ≤ 8 影响；`meshreorder` 后前 192 根骨与 `body_000_f` 同名同序。
- `chainbuild` 写完立即回读，打印 group / setting 数。
- profile 之间互不影响：改一个 profile 后另一个的 spec / 资产逐字节不变（`cmp`）。
- 生成的第二个 Lua 脚本与生成器同步（`make_original_lua.py --check`）。
- 确定性：同一源两次构建逐字节一致；修复版与上一版逐字段比较（`chaininfo` 两版 diff），只有预期变化。

建议再加（本项目靠实机发现，未做成离线闸门）：`K_*` 骨 +X 指向子骨；每个 chain 节点的 `angleLimitDirection` 与静止方向一致；
4 个兼容材质名在网格与 MDF 里都在。

## 3. 实机闸门

1. 备份存档并记哈希；只读档、不存档。
2. 冷启动 → 标题 → 继续 → 日志出现首次完整维护（`Karin on <GO>`）判定进入游戏；`Exception occurred|hook error` 计数为 0。
3. 装备界面预览、暂停菜单头像（菜单模型）都是 Karin；强制重建装备 / 身体部件后保持。
4. 压力脚本（对话手势、走动、跳跃、攻击、蹲、暂停菜单、装备界面）多轮，进程存活、日志无异常。
5. 「放弃保存回标题 + 读档」重建一次；REFramework「Reset scripts」一次。
6. 表情各通道在拍照模式下强制满幅截图；物理按用户关注的动作录制或截图。
7. 收尾：存档与备份逐字节比较；游戏目录只留发行文件（开发控制台、探针移走）。

## 4. 发行包

```text
<Mod>_DD2_vX.Y.Z/
  pak_mods/<Mod>.pak
  reframework/autorun/<mod>.lua
  README.md
<Mod>_DD2_vX.Y.Z.zip
<Mod>_DD2_vX.Y.Z.sha256.txt   （README、PAK、Lua、zip 的 SHA-256）
```

- README 写：前置（REFramework nightly，版本）、安装（把两个目录复制到游戏根目录）、与另一个替换 Mod 互斥、卸载（删两个文件）、
  只替换女性人类玩家、开关在下次读档生效、已知限制、**更新记录**（每版改了什么、哪些只改了数据没改脚本）。
- 旧版本移到 `_superseded/`，不覆盖。
- 游戏本体 PAK 从不改动。还原 = 删除 `dinput8.dll`、`pak_mods/<Mod>.pak`、`reframework/autorun/<mod>.lua`、`reframework/data/<mod>*`。

## 5. 证据分层（本项目）

| 项 | 级别 |
| --- | --- |
| `pak_mods` 注入的独立路径资源被脚本引用后加载 | `runtime-load-pass` |
| 构建时注入（网格 / 材质 / chain）、烘焙改道、体型表清空 | `runtime-confirmed`（v1.2.0：agent 多次冷启动、重读档、压力 0 异常；用户本机使用） |
| 装备预览、暂停头像、拍照模式 | agent 实机观察（拍照模式只在测试机上看过） |
| PicodraTech chain（方案 F） | 随 v1.0 – v1.2 被用户接受（未单独签收）；v1.3.0 未改 chain 参数（`K_Belt_String_1_L/R` 的权重并回父骨后，这两条短链不再带顶点，影响可忽略） |
| Original 物理 o4 的双马尾 / 尾巴摆幅 | 用户确认「裙子差不多刚好了」；最后一次加大摆幅未单独确认 |
| Original v1.0.1 裙摆外倾锥 | `runtime-confirmed`（用户：「这次好了」；逐帧数据只录了 v1.0.0 与 f4） |
| 表情（眨眼、张嘴、视线） | agent 在测试机实机逐通道验证（强制满幅截图 + 实时录制）；用户未单独确认，幅度常数未签收 |
| 2026-10 更新 / DLC 下原样可用 | agent 在测试机实机自测；Original 另经用户本机（无 DLC）实测 |
| 男性、兽人玩家 | 设计上保持原样（不替换），未逐项实测 |

**未测场景**：过场动画、攀爬大型魔物、梯子、布娃娃 / 死亡、角色编辑（新建角色 / 整容）时的构建、骑乘、长时间开放世界游玩；
随从 / NPC 缓存玩家 joint 的情况（序章牢房 30 个角色实测为 0）。
