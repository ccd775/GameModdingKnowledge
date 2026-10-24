# 验证与发布

## 1. 离线闸门

- **索引与副本**：`acu_forge.py index` 能读全部 63 个 forge（版本 27）；`objs_to_tsv.py` 汇总出的副本清单和上一版一致，或者变化能解释（v1.5.1：
  21 个 forge 的 189 个数据文件）。
- **原版往返**：`build_mod.py` 对每一份副本先把原版表 XML 重新编译，必须和原版逐字节相同，否则停下（每次构建都做）。
- **网格**：`import-glb` 的日志里是 v2 顶点格式、骨数 ≤ 255；网格的每根骨都在某个加载的骨架里（基础骨架 53、头部骨架 6、`Karin_Phys` 100）。
- **物理骨架**：和原版骨架逐项对照（[物理](PHYSICS.md) §2）：`ChildBoneCount` = 后代数、`Index` = 位置、键是自己的、BallJoint 的 `LiteRagdoll` /
  `OrientationBone` 为空；原版骨架重新编译逐字节相同。`--report` 的骨数、BallJoint 数（v7：121 / 55）和偏移与上一版一致，或者变化正好是这一版要改的。
- **payload**：末行 `BUILD_OK`；数据文件数与 `skip.tsv` 行数与上一版相同（v7：456 + 1 + 14 行）；唯一的 `WARN` 是康纳。比较两次构建要**解包后比对象**
  （容器字节每次都不同）。
- **发行包往返**：在有原版游戏的机器上用包里的 `.cmd` 跑 安装 → 状态 → 卸载，全部 forge 回到原版大小、状态文件删除（每个发行包都做过）。

## 2. 实机闸门

1. 游戏关闭；`uninstall`（旧版）→ `install` → `status`。
2. 启动到 Logo 之后（附加骨架有错会在这里闪退）。
3. 读档：正面、背面、侧面看装备是否全部隐藏、有没有残留的头发 / 牙齿、贴图是否正确。
4. 跑动、急停、转身：双马尾 / 尾巴静止时保持源模型的形状、摆动幅度，跑动时大腿是否穿出裙子。
5. 脸部特写：静止和眨眼（录 10–20 秒，逐帧看）；对话里的嘴。
6. 自定义界面里的模型、旧时代服装、过场（至今没做）。
7. 本项目 v3 起第 2–5 步由用户在另一台电脑上做，agent 只交付包；本机测试要先确认授权，遇到 Ubisoft Connect 登录就交给用户（[开发工具](DEV_TOOLING.md) §5）。

## 3. 可重新部署的包

`make_release.py` 打的 zip（不压缩，里面的 xz 已经压过）：

```text
Karin_ACU_v7.zip
  payload_v7.tar.xz   payload/（456 个按 forge 的数据文件 + 通用的头部容器 + skip.tsv）+ payload/vanilla_sizes.tsv
  install_v7.cmd      %PY% acu_install.py install "payload_v7.tar.xz" %*
  uninstall.cmd       %PY% acu_install.py uninstall %*
  status.cmd          %PY% acu_install.py status %*
  README.txt          用法与每个标签的说明（UTF-8 BOM、CRLF）
  acu_install.py      安装器（= 便携包 scripts/acu_install.py 的项目原件）
```

- `.cmd` 先 `cd /d "%~dp0"`，有 `py` 启动器就用 `py -3`，否则 `python`；多余的参数（如 `--game "<目录>"`）原样传给安装器；最后 `pause`。目标机器要 Python 3.8+。
- `payload_v7.tar.xz` 是 solid xz（preset 9 extreme），文件按名字排序，让同一个数据文件在各 forge 的版本挨在一起压缩：232.7 MB → 44.2 MB。
- `vanilla_sizes.tsv` 是制作机上**原版**每个 forge 的大小（装着 mod 时从安装状态里取原长）；目标机器的 forge 大小不一致时安装器拒绝。
  用户另一台电脑上的原版 forge 大小与制作机相同（v3 时核对）。
- v7 的包：`Karin_ACU_v7.zip`，44 244 950 字节，SHA-256 `63AE3E1FD77C7EBCDB793CD7F7C6ADFB05E1F0F06D59DCE35711E58F4064F22D`；`payload_v7.tar.xz`
  44 232 152 字节。zip 含游戏数据和模型，**私有，不发布**；这里只记结构和做法。
- 往返测试（2026-10-24，制作机，只动文件、不启动游戏）：`install_v7.cmd` → `status.cmd` → `uninstall.cmd`，63 个 forge 回到原版大小，状态文件删除。
  之前每个中间包（v2 / v3、v4 / v4p、v5、v6 / v6n、v7 / v7x）都同样往返过。
- 中间包里放过诊断用的标签：v4p（v4 的骨架 + v2 的网格，区分闪退在骨架还是网格）、v6n（v6 不带碰撞对象）、v7x（胶囊半径 ×2）。都没有用上：对应的主版本通过了。
- 便携包核对（2026-10-24）：用便携包的 `build_mod.py` 和重新编译的 AcuHarness 重建 v7，457 个数据文件的 14 585 个对象与发行的 v7 逐字节相同；
  用便携包的 `make_release.py` 打包发行的 v7 payload，`payload_v7.tar.xz`、`.cmd`、README 与发行包逐字节相同（[VALIDATION.md](../../portable-kits/VALIDATION.md)）。

## 4. 未测场景

- 自定义界面 / 菜单里的模型（v2 那次键盘鼠标没能操作暂停菜单，之后没再看）；
- 旧时代服装（表已改，游戏里没检查）；康纳那身没有物理；
- DLC「亡者之王」自己的亚诺表（`SDN_Arno_BodyCust`、`SDN_Arno_Legacy`，没处理）；派对服装 `CN_P_Arno_Party`（15 份，没处理）；
- 过场、对话口型、眨眼的幅度（表情没有单独评价）；
- 合作模式、其它玩家看到的模型；
- 非 Steam 版本（Ubisoft Connect 独立版）、其它 build。
