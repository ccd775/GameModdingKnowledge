# 验证与发布

## 1. 离线闸门

- 构建器报告：`missing_face_keys` 为空、`slots_unmapped` 为空、`bones.body` = 原版身体骨数、`body_bones_added` 列出补上的骨、布料段的面数 / 锚点数、
  `degenerate_cloth_tris`。
- UE：每一步的完成标记；`ue_cloth.py` 每段布料的报告（顶点、固定点、backstop 数）；`ue_blink.py` 的两种门控自测（`BLINK_OK`）；`ue_morphdump.py` 的形变名单。
- 读回（[构建流水线](BUILD_PIPELINE.md) §4）：骨数和 `*_child` 骨、材质槽、形变数、布料资产数、动画蓝图节点和门控。
- 姿势探针（Blender）：在游戏动画的典型姿势下量布料和皮肤的穿透，判断穿模是来自几何还是来自模拟。

## 2. 实机闸门

1. 用户关掉游戏后再安装；`~mods` 里另一套 Karin 包先移走（安装脚本会删）。
2. 用户检查：成年两套服装、序章少年魂、过场的脸与口型、平时眨眼、各段布料（站立、走、跑、战斗）、颜色。
3. 一版只放一类改动；每轮反馈记进 PROJECT_STATE，旧的结论只收窄、不删。

## 3. 发行包

```text
KarinPBZ_<日期>_v<n>/
  install.cmd        powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*  然后 pause
  uninstall.cmd      同上，带 -Uninstall
  install.ps1        便携包 release/install.ps1
  README.txt         中文，UTF-8 BOM + CRLF，不写本机路径
  files/
    z_KarinPBZ_P.pak / .ucas / .utoc
    SHA256SUMS.txt   「哈希  文件名」，CRLF
```

`install.ps1`（Windows PowerShell 5.1 / PowerShell 7）：

- 找游戏：注册表里的 Steam 路径 → `libraryfolders.vdf` → `appmanifest_4115450.acf` 的 `installdir`；找不到就要求 `-GameDir`；
- buildid 与打包时不同就警告；游戏在运行就拒绝；
- 复制前核对包内哈希，复制后再核对；`-Check` 只报告状态；`-Uninstall` 只删自己的三个文件，`~mods` 空了就删掉；
- `~mods` 里有另一套 Karin 包（`z_KarinPT_P.*`）时安装会删除它（两套替换同样的资产），`-Check` 会提示。

测试（项目里做过，2026-10-30 / 10-31）：对真实安装 `-Check`；游戏运行时拒绝安装；假游戏目录上的安装 / 检查 / 版本不符 / 文件被改 / 卸载（含 `~mods` 里另有别的 pak 时保留目录）/
包损坏拒绝 / 找不到游戏目录；带假 `z_KarinPT_P.*` 时安装把它删掉、别的 pak 不动。

## 4. 未测场景

- 醉剑修复（v3）只读回了骨，没有进游戏复测；其它用到 `*_child` 骨的武器没有逐一检查。
- 其它服装（各自的身体网格，没替换；它们的头被隐藏了，换上后头部显示不正常）。
- groom 头发关闭或质量低时的过场（两张脸可能闪）。
- 大动作下的布料（翻滚、处决、骑乘）、拍照模式、对话特写。
- Karin_PicodraTech 整体（构建、读回、安装过，用户没有反馈）。
