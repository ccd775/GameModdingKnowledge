# 验证与发布

## 1. 工具级往返闸门（开工前）

| 对象 | 闸门 |
| --- | --- |
| mesh（raw 模式） | 参考 mod / 原生 mesh 读入写出，载荷一致 |
| mdf2 | 参考 mod 的身体与脸 mdf2 读入写出逐字节一致；`GPUBufferOffset` / `mmtrsDataOffset` 清零后重写仍一致 |
| chain2.15 | 参考 mod 与原生文件读入写出逐字节一致 |
| pfb.18 / RSZ | 原生角色 prefab 读入写出逐字节一致（类型库 `rszre9.json`） |

改别人的 mdf2（例如只换贴图路径）时，对**每个**文件先做一次「读入即写出 = 原文件」，通过才改。

## 2. 构建后回读闸门（`VERIFY: PASS` 才允许打包）

验证器独立于构建器，从产物文件回读：

- **网格**：骨名无重复、父骨在前、加权骨都在骨表里；每顶点权重和 = 255、索引不越界；单 LOD。
- **骨架**：所有部件共享关节的 rest 偏差为 0；refskel 与网格 rest 一致（位置 < 1e-4、旋转 < 1e-3）。
- **屏蔽件**：4 顶点、骨表 = 原生、材质名 = 原生首材质。
- **材质**：路径表里该网格的**每个** mdf2 变体都存在，网格的每个材质名都在 mdf2 里，所有贴图路径能在产物或路径表里解析；
  贴图版本与 mip 数。
- **chain2**：链尖、碰撞体、link 引用的关节都存在于加载它的**所有**网格；节点数、setting id 自洽；表头
  `wilds_unkn0` 为原生值、首个 setting 带 Default。
- **prefab**：每个显示被替换身体的 prefab 恰有一个加载 Karin 身体 chain2 的 Chain2；**每个**加载 Karin chain2 的
  Chain2 的 `CollisionTarget = 0`；改过的 prefab 往返一致。

本项目结果：里昂 186 文件、格蕾丝 136 文件，两包 `VERIFY: PASS`。

## 3. 离线预览

用产物自身的权重与骨架渲染静止姿势和测试姿势（手臂放下、膝盖弯曲），检查扭转、塌陷、漏绑。只算 `offline-accepted`。

## 4. 打包与 Fluffy

- 包结构：`<包名>/modinfo.ini`（name / version / author / description / category / screenshot）、截图、`natives/stm/...`；
  另出 zip 和逐文件 SHA-256 清单。打包器先跑验证器，失败则拒绝。
- Category 用 `!Characters > Leon` / `!Characters > Grace`，便于在 Fluffy 里与同角色的其它 mod 放在一起（互斥要靠人看）。
- 安装与更新只走 Fluffy：停用 → 替换 `Fluffy/Games/RE9/Mods/` 下的包 → Refresh → 启用 → 用清单逐文件比对游戏目录哈希。
  手工拷进游戏目录的测试文件要先清掉，否则与 `installed.ini` 分叉。
- 替换别人的 mod 包（例如修用户自己的 mod）：先备份原包并核对原包内容与工作目录一致，再替换；记录原包哈希。

## 5. 展柜自测（agent 可做，`runtime-load-pass`）

自动化路线（前台窗口输入；菜单坐标取自本机截图，换机器或分辨率要重新截图定位）：

1. 结束 `re9.exe`，用 `steam://rungameid/3764200` 重启，等窗口出现后再等约 30 秒。
2. 按 `Insert` 关掉 REFramework 菜单。
3. 主菜单：**鼠标悬停**选中「奖励内容」，按住 `F` 再松开（`F` 是确认键）；再悬停选中「游戏模型」并确认；再确认一次进入展柜。
4. 默认显示格蕾丝；按 `E` 切到里昂。截图。

要点：

- **不要长按方向键**：主菜单会自动连跳，曾一路跳到「退出游戏」并被确认，表现得像崩溃。
- 键盘点按偶尔被吞掉，鼠标悬停 + 分开发送按下/松开最稳。
- Fluffy 把游戏的崩溃报告程序改了名，崩溃和退出都是静默的；判断「是不是崩了」先看是否误操作了退出。
- 物理要用 REFramework 探针读数值（[技术合同](TECHNICAL_CONTRACTS.md) §6），截图只能证明外观和加载。

## 6. 运行时证据分层（本项目）

| 项 | 级别 |
| --- | --- |
| 两包在展柜加载、几何与贴图正确、材质哑光 | `runtime-load-pass`（agent 截图） |
| 注入的 Chain2 让展柜里的里昂身体链运动 | `runtime-load-pass` |
| CollisionTarget = Self 后裙片在碰撞体外、双马尾停在躯干表面 | `runtime-load-pass`（探针数值，里昂展柜） |
| 「Leon Karin」哑光修复 | `offline-accepted`（同一修法在 v1.1 实机看到哑光；修后的包未进游戏） |
| 实际游玩、过场、第一人称、切割套件、其它服装、GPU 发丝 | 未检查 |

## 7. 审查

工作区规定 modding 的审查降档：本项目只做了主控自查（独立验证器 + 展柜 + 探针），没有派外部审查席。
