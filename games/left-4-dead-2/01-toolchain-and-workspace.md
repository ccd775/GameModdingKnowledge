# 工具链与工作区

## 1. 已验证工具职责

| 工具 | 职责 | 关键限制 |
| --- | --- | --- |
| Blender LTS | 源模型审计、形态键烘焙、骨架/权重编辑、预览渲染 | 固定版本；插件行为可能随版本变化 |
| Blender Source Tools | 导出 SMD、VTA、DMX | 需要特别检查单位和 armature data 缩放 |
| SourceIO | 导入和独立检查 MDL/VTF/VMT | 用于检查，不是本流程的 Source 1 导出器 |
| Crowbar | 反编译受支持的 MDL、查看 QC/SMD | 并非所有版本可解；曾遇到 v53 只读到 header |
| `studiomdl.exe` | 编译 MDL/VVD/VTX/PHY | 必须来自目标 L4D2 安装和分支 |
| `vtex.exe` | 编译 VTF | L4D2 分支有尺寸、标志位和临时 `.pwl.vtf` 行为 |
| `vpk.exe` | 构建与列出 VPK | 列表成功不等于 payload 与 loose tree 一致 |
| HLMV | 快速检查模型、动画、命中盒和物理 | 可能从挂载路径加载原版同名模型 |

Karin 项目曾验证 Blender 4.2.23 与 4.5.12，最终固定在 4.5.12 LTS；Blender Source Tools 使用 3.4.x；SourceIO 使用 5.5.4；Crowbar 使用 0.74。这些是复现信息，不是永久推荐版本。新项目开始时应重新验证当前稳定组合。

## 2. 使用游戏自带编译器

Source 1 各游戏和各分支的模型版本、shader、打包细节不同。必须使用目标 Left 4 Dead 2 安装目录中的：

```text
bin/studiomdl.exe
bin/vtex.exe
bin/vpk.exe
bin/hlmv.exe
```

不要用 Garry's Mod、CS:S、Source SDK Base 或其他游戏的 StudioMDL 替代。记录 Steam build ID、可执行文件版本和 SHA-256。

## 3. 挂载顺序

原生资产的有效版本不一定在 `left4dead2/pak01_dir.vpk`。曾观察到的优先级是：

```text
update -> dlc3 -> dlc2 -> dlc1 -> base -> hl2
```

审计目标 survivor 前先读取当前 `gameinfo.txt`，按实际 SearchPaths 找到最先命中的 QC/MDL/VMT。不要只解包 base VPK。

## 4. 推荐目录结构

```text
project/
  src/                 # 人工维护的 source-of-truth
    scripts/
    qc/
    runtime/
  references/          # 哈希锁定的原生/社区参考
  tools/               # 固定版本工具或其版本清单
  work/                # 可再生的中间产物
    compile_sandbox/   # 带 gameinfo.txt 的隔离游戏根
    material_build/
    release_<candidate>/
  build/               # 可交付候选或稳定构建
  reports/             # JSON、Markdown、截图、哈希
  docs/
  PROJECT_STATE.md
  source-lock.json
```

`work/` 可以重建，但不要在没有确认候选清单的情况下批量删除。同步盘可能锁住刚生成的文件，重建脚本应使用明确路径和有限重试。若出现 `*_冲突文件_*` 或类似同步副本，应让严格闭包验证失败，并在新的 run/candidate 目录重建；不要自动删除未知冲突后继续从原树发布。

## 5. Source 单位

本流程使用的换算：

```text
1 Source unit = 1.905 cm = 0.01905 m
1 m = 52.49343832020997 Source units
```

Blender Source Tools 的常见错误是只设置 `armature.scale`。这样根节点看似正确，子骨骼局部平移仍可能保留米单位。

正确做法：

1. 保持对象矩阵为 identity。
2. 对 `armature.data` 缩放 `52.49343832020997`。
3. 对每个唯一 mesh data block 缩放相同倍数，并启用 shape key 数据缩放。
4. 再次确认对象矩阵仍为 identity。
5. 重新导出 SMD、VTA 和 reference animation。

最终以重新导入编译 MDL 后的骨端点、包围盒和地面接触验证单位，不以 Blender 视图的“看起来正常”为证据。

## 6. 隔离编译沙盒

`compile_sandbox` 至少包含：

```text
gameinfo.txt
models/
materials/
```

QC 使用目标相对路径，但 StudioMDL 的 `-game` 指向沙盒。这样可以：

- 避免污染正式安装；
- 固定 include 和 material 搜索范围；
- 为 HLMV 提供可重复的加载环境；
- 用唯一 preview alias 排除原版同名模型被误加载。

## 7. Windows 与同步盘注意事项

- BaiduSync 等同步软件可能在 VTEX 退出后继续占用输出文件。对 `unlink` 和 `write_bytes` 使用有限重试，例如 121 次、每次 0.25 秒，总计约 30 秒。
- 同步客户端生成的冲突副本必须作为 manifest 外 extra 报错。保全并哈希后换新输出树，避免其被误打进 VPK。
- source lock 对工作区内文件优先记录 project-relative path 或显式 logical root；若工具
  必须保存绝对路径，应把“内容身份”和“物理位置”分开。同步盘从一个盘符迁到另一个
  盘符时，旧 lock/report 是历史快照，不原地改写；为新候选生成明确的 root-remap 或新
  lock，再用原 bytes/SHA 证明内容未变。路径不存在不等于源内容发生变化，但旧绝对
  path verifier 也不能伪报通过。
- 只对已解析并确认位于项目内的目标路径做清理。
- 遇到 Blender、HLMV 等 OpenGL/DirectX 或难以自动化的窗口时，可使用 `control-special-windows-apps` 技能进行截图和输入；先完整阅读其 `SKILL.md`。
- 保存原始 HLMV 截图，截图中包含窗口标题、模型名和当前 sequence。裁剪图只用于汇总，不替代原始证据。

## 8. 工具版本锁模板

每个项目至少记录：

```json
{
  "game_build_id": "<steam build id>",
  "blender": {"version": "<version>", "sha256": "<hash>"},
  "blender_source_tools": {"version": "<version>", "sha256": "<hash>"},
  "sourceio": {"version": "<version>", "sha256": "<hash>"},
  "crowbar": {"version": "<version>", "sha256": "<hash>"},
  "studiomdl": {"path": "<path>", "sha256": "<hash>"},
  "vtex": {"path": "<path>", "sha256": "<hash>"},
  "vpk": {"path": "<path>", "sha256": "<hash>"}
}
```

路径用于复现，哈希用于证明实际使用的二进制。
