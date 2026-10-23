# 排障手册

除标注外均为本项目实测（v1.5.6）。

## 1. 安装与加载

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 装了以后装备照常显示、改动像没生效 | 只改了 `DataPC_SharedGroup_00` 的副本；patch_01 和 DLC forge 里的副本压过它 | 每一份副本都替换（`aco_install.py` 自动找全；[技术合同](TECHNICAL_CONTRACTS.md) §3） |
| Karin 的网格和动作对，但整个是品红色 | 材质放在身体容器里，DLC 里的容器副本是只有 LODSelector 的空壳，材质没被加载 | 材质、纹理组、贴图放进 patch_01 的 LOD0 数据文件 |
| `install` 报 `<ID> not found in any forge` | ID 写错，或游戏版本变了 | `aco_locate.py find` 核对；版本变了先重建索引（[Agent 入口](AGENTS.md) 第 1 条） |
| `already installed; uninstall first` | 状态文件存在 | 先 `uninstall`；游戏在装着时被更新 / 校验过的话见下一行 |
| 游戏更新或校验文件后 mod 失效 / 异常 | 更新替换了 forge，状态文件里的旧行已不对应 | **不要卸载**：删 `<游戏目录>\.karin_aco_state.json`，Ubisoft Connect 校验文件，重新安装 |
| `close the game first` | `ACOdyssey` 进程还在 | 退出游戏，或 `taskkill /im ACOdyssey.exe /f`（先问） |
| 卸载时 `backup of <文件> does not match its recorded hash` | `root\` 覆盖过的文件的备份被改过 | 不还原那个文件；用 Ubisoft Connect 校验 |
| 担心要改 `.prefetch` | — | 不需要：数据文件的根引用按需加载（v2 起） |

## 2. 工具链

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 导出 XML 时 NullReference | AnvilToolkit 1.3.6 的 `SchemaFileNames` 里没有奥德赛 | harness 启动时补 `ACOdyssey` |
| `tex-info` / `tex-export` 卡住不动 | 读顶层 mip 时等 GUI 文件对话框 | 结束进程；只用内联 mip 的贴图 |
| `tex-import --maptype MapMask0` 报错 | 枚举里没有这个名字 | 传数字 `12` |
| harness 说找不到文件 | 不带斜杠的参数按 harness 所在目录解析 | 写成 `./文件` |
| `unpack-data` / `export-xml-dir` 用相对路径失败 | — | 用绝对路径（或逐个文件 `export-xml`） |
| 编译后的表 / 骨架和原版差几个字节 | 写出器把空引用后的填充字节写成 0（原版 1）；XML 里补 `ReferenceType="1"` 不起作用 | `build_mod.compile_fixed` |
| `compile_fixed` 断言「映射到意外的字节」 | 按位置对齐时，被删掉的单元打乱了偏移 | 已按 `difflib` 匹配块映射；仍失败时检查改动是否碰到了别的引用 |
| 打出来的数据文件里多了 `.bak` | `compile-xml` 在覆盖的文件旁留备份 | 打包前删掉（`build_mod.pack` 这样做） |
| `import-glb`：`mesh bones > 255` | 奥德赛的 v4 顶点格式没有宽索引 | 导出时裁骨（`export_karin_lods.py`），减少 KP 骨 |
| `import-glb` 写到一半失败 / NaN | 退化 UV 造成零 / NaN 法线或切线 | harness 的 TBN 修正（已内置） |
| `aco_phys_skel.py` 在链根上 KeyError | `mesh-bones` 的输出里没有不带蒙皮顶点的 KP 链根 | `--binds` 用 `_ody.glb`（逆绑定矩阵里每个关节都有） |
| `face_rig.py --jaw-angle` 只蒙上几个顶点 | 杠杆搜到 1.69 m，权重全 < 0.01；或眨眼段覆盖了嘴的数据 | 杠杆限在 `--jaw-lever` 内；嘴段重新取数据（已修） |
| Git Bash 里 `/正则/` 参数变成路径 | MSYS 路径转换 | `MSYS_NO_PATHCONV=1` |
| Python 打不开 `/c/...` 形式的路径 | Git Bash 的路径写法 | 用带盘符的 Windows 写法 |
| 测试机上打印名字时 UnicodeEncodeError | 控制台是 GBK | 脚本把 stdout 改成 UTF-8（已内置） |
| Blender 输出写到意外的位置 | 相对路径按 Blender 的当前目录解析 | 用绝对路径 |
| 大文件传到测试机时卡住 | 链路带宽有限 | 分块传、截图缩成 JPEG |

## 3. 外观

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| 卡珊德拉的脸还在 | 头部表列 1–7 | 去掉列 1–8 和 14 |
| 辫子还在后颈 | 发型来自头发表列 9 / 10 / 13，行的 `DynamicResources` 也加载发型网格 | 去掉这三列并清空 `DynamicResources` |
| 弓和箭袋仍显示 | 不在 Outfit 列里 | 已知，没有处理 |
| （预防）远处的 LOD 变回原版身体 | LOD2–4 是共用的女性身体 | 容器的 LODSelector 把 LOD2–4 指到 Karin 的 LOD1，不替换共用身体（按设计做的，没有见过这个症状） |
| 打算用皮肤 / 服装模板 | 这些模板的漫反射是编码数据（皮肤参数、染色区），不是颜色 | 用 `ACD_Tex1`（离线分析后就换了，没有进游戏试） |

## 4. 物理

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| 尾巴、耳朵没有物理 | v4 时这两组关着 | 打开（v5） |
| 跑动时大腿从前裙片穿出 | 裙片对称摆动，向内摆进了腿 | 前片只许向外（B ≥ 0）、后片 B ≤ 0；裙子跟随大腿（v5） |
| 尾巴偏硬、耳朵不明显 | 范围小、gf 低 | 放大范围、提高 gf（v6，用户未单独评价） |

## 5. 表情

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| 眨眼只闭 1/4 | 沿用影的 40° 闭合角；游戏里眨眼时骨转得少得多 | 降闭合角（但见下两行） |
| 大多数时候半闭、在几个状态之间跳 | 眼睑骨静止时不是 0°，还随扫视驱动的跟随姿势切换；增益高把这些都放大 | 低增益（v8：褶骨 25°），接受眨眼不完全 |
| 上眼睑撕裂 / 打折 | 长杠杆（1.44 m）把单眼扭转姿势放大成厘米级横移 | 不用长杠杆 + 预转；换成扭转更小的褶骨 |
| 两眼有时不一样（v7 录像） | 很多姿势只管一只眼 | 已知；低增益时应该不明显（v8 没有单独确认，`hypothesis`） |
| 虹膜不动 | 挂在眼窝骨上（它从来不转） | 挂视线骨 |
| 说话时嘴几乎不动 | 刚性下颌拟合在 11°，游戏说话时下颌转得小 | `--jaw-angle 6`（杠杆） |
| 离线渲染里偏移区域有黑斑 | 自定义法线是从存下的偏移形状推出来的 | Workbench 平涂 |
| 离线渲染里嘴 / 下颌的子骨错位 | 偏移骨的子骨在保存的姿势里也显示偏移 | 重建每根骨的游戏静止位置（`pose_preview.py` 已这样做） |
| SSH 会话里跑 `pose_preview.py` 崩溃 | Workbench 需要 OpenGL 上下文 | 在交互桌面会话里跑（一次性 `schtasks /IT`） |
| 用网格量原版眼睛开度，眨眼满权重还有 0.85 | 找缝隙的方法本身不成立 | 不用这个方法 |
