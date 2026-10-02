# 验证与发布

## 离线闸门

下面各项都检查最终写出的 wad 和 lodpack，不检查中间场景。

- **逐顶点回读（`verify_build.py kratos|valk <输出目录>`，加上构建时的同一组 `--base-wad`、`--fit`、`--fit-lods`、`--karin-bones`、`--rigspec`）。** 把每个计划槽位从输出的 wad 和 lodpack 解码回来，和源几何逐顶点比对：
  - 位置误差小于 1e-5，三角形完全相同；
  - 每个顶点的骨骼集合包含源数据里权重大于 0.02 的骨，权重误差小于 0.01；
  - 用到的骨骼编号小于骨骼数；芙蕾雅还要求每根骨都在原版蒙皮里出现过（不带蒙皮的控制骨直接判失败）；
  - 定义的哈希是原哈希或原哈希 + 1；
  - 每个隐藏定义指向的零块确实全零，而且不与任何计划槽位的顶点区或索引区重叠。

  最后一行 `BAD 0` 才算通过。只检查「骨骼索引小于骨骼数」不够：芙蕾雅头颈组的 u16 骨骼被写成 11 bit 打包时，这项照样通过，见 [排障手册](TROUBLESHOOTING.md)。
- **槽位报告（`mesh_report.json`）。** 每个定义的组号、LOD、切换距离、容量、各部件选中的精度。改参数后先和上一版逐项比较，特别是有没有部件被丢弃（`dropped`）。
- **屈膝模拟（`knee_sim.py`，芙蕾雅）。** 用游戏实际拿到的数据检查膝盖穿模：
  - 从输出里解码头颈组（皮肤）和脚部组（袜子）的网格；
  - 按芙蕾雅的绑定骨架做线性蒙皮，让两条小腿绕膝关节弯 0°、30°、60°、90°；
  - 每个腿部皮肤顶点在绑定姿势下找最近的 6 个袜子顶点，弯曲后取它们法线方向有符号距离的中位数，大于 1 mm 记为穿出。

  在绑定姿势下先定好对应关系，是为了防止弯曲后把关节另一侧折过来的袜面当成「最近」。之前在 Blender 里直接测最近距离的做法结果不稳定，已经放弃。
- **诊断贴图。** 不确定游戏里看到的东西来自哪个材质时，把各贴图族换成不同的纯色（头红、手臂绿、头发蓝……），出一个诊断贴图包进游戏看颜色。

离线全部通过，只能算 `offline-accepted`。

### 本案的离线结果

| 检查 | 奎托斯 | 芙蕾雅 |
| --- | --- | --- |
| `verify_build.py` | 10 个槽位全部 OK，`BAD 0` | 19 个槽位全部 OK，`BAD 0` |
| 屈膝模拟，修正前（膝盖区穿出的顶点数） | — | 30°–90° 时 1–4 个 |
| 屈膝模拟，修正后 | — | 各角度都是 0（脚部 LOD0、LOD1 两套袜子） |

脚踝一圈有几个顶点在静止姿势就被判为穿出，它们在鞋里面，修正前后相同。

## 复现基线

改构建脚本之前，先用同一组输入重建，确认输出与上一版逐字节相同：

- **输入：** 拟合结果（`fit`、`fit_lods`、`fit_valk`、`fit_valk_lods` 里的 npz 和 `summary.json`）、`karin_bones.json`、两份 rigspec、底板 wad（奎托斯是参照 mod 的 `r_heroa00.wad`，SHA-256 `2ccddd1c…`；芙蕾雅是原版 `r_freyavalkyrie00.wad`，SHA-256 `cefacaae…`）、游戏的 `root.lodpack`。
- **2026-10-02 的结果：**
  - 项目目录的工具不经 Blender 直接重建两个 mod，wad 和 lodpack 与发布文件逐字节相同；
  - 便携包脚本重建两个角色的 wad、lodpack、texpack 及其 `.toc`，共 10 个文件与发布文件逐字节相同，槽位报告和贴图计划也相同。环境和改动见 [验证记录](../../portable-kits/VALIDATION.md)。
- **发布文件的 SHA-256：**

| 文件 | SHA-256 |
| --- | --- |
| 奎托斯 `r_heroa00.wad` | `c8b43fc479f58eedb9f7e1568d64ffef29dfee69a755f4648174032d2809c57e` |
| `KarinOriginal.lodpack` | `a483890fc0648625e4e7f4a07d78bff19b5bf260d99911e8f6a636bb16645aa5` |
| `KarinOriginal.texpack` | `b37d5ca57f3a31678a043e8d41f29f0787e3f6f424603c7175093ed3ca916be1` |
| 芙蕾雅 `r_freyavalkyrie00.wad` | `f003da61bba1724cea18783f37bd2a01336d1e381ac1b309367441170dcdb04f` |
| `KarinOriginalFreya.lodpack` | `408cc758bb7f92ce9765eeef84a08ab2d9e82eb6e15cbd48834fc4e97309e1b2` |
| `KarinOriginalFreya.texpack` | `20d321c016495dc27e7aee4b6f2b42111c24ceee5deac09d7c1e1663c20a11f9` |

拟合那一步在 Blender 里运行，没有做逐字节复现；换了 Blender 版本后，改为比较拟合 summary 和回读结果。

## 实机测试方法

这是 agent 自测的流程，测完得到的是 `runtime-load-pass`，不等于用户验收。

1. **先确认用户没在玩。** `GoWR.exe` 在运行就等它关掉，不要结束用户的进程。
2. **备份。** 被覆盖的 wad、`exec/boot-options.json`、游戏目录里的 `settings.ini` 都先留一份。
3. **窗口模式。** 把 `settings.ini` 的 `DisplayMode` 改成 `Windowed`，`WindowSize` 改成 `1280 x 720`。测完改回用户原来的值。
4. **部署。** 复制 wad、补丁包和 boot-options。
5. **启动。** 打开 `steam://rungameid/2322010`，按进程找 `GoWR` 的主窗口。启动时 Steam 可能弹出 PSPC SDK 运行库的 UAC 提权窗口，不要替用户点。
6. **判断卡死。** 窗口出现后等约 50 秒，按一次回车，再量 5 秒内进程的 CPU 时间增量：卡在开场 logo 时接近 0，正常运行约 15 秒（多核累计）。进程消失说明崩溃，游戏目录的 `.crashdata` 里会有 dmp。
7. **读档。** 菜单里的按键要按住约 0.12 秒，瞬时按键常被丢掉。主菜单「继续」读档，然后截图。
8. **看角色。**
   - 鼠标把光标移到窗口上下方可以俯仰镜头；本项目里水平转动不稳定，靠走动、后退和同伴的跟随来换角度；
   - 暂停菜单按 H 进照相模式，可以用 WASD / C / Z 平移镜头。
9. **检查清单：** 能否读档；正面、背面、侧面的外观和贴图；走动时肩、裙摆、尾巴；俯视（奎托斯版有黑斑，见 [案例](cases/KARIN_ORIGINAL.md)）；拉远后的 LOD。
10. **收尾。** 关游戏，恢复 `settings.ini`；不要存档。

不要用 Steam 的「验证文件完整性」来恢复原版：Steam 离线时验证会失败，本项目的一次失败还删掉了 `exec/boot-options.json`（之后按 Steam 日志里的 SHA1 精确还原）。

## 发布

每个 mod 一个文件夹，结构照游戏的 `exec` 目录：

```text
KarinOriginal_Kratos/
  boot-options.json                      只登记本 mod 的包
  boot-options（奎托斯+芙蕾雅同时安装时使用）.json
  patch/KarinOriginal.lodpack(.toc) / .texpack(.toc)
  wad/pc_le/r_heroa00.wad
  说明.txt
```

芙蕾雅版另有 `原版备份/r_freyavalkyrie00.wad`。

- **`说明.txt` 的内容：**
  - 适用 build 和 GoWR.exe 的 SHA-256；
  - 替换的是哪个文件，以及为什么是它（芙蕾雅版写明 `r_freyavalkyrie00` 与 `r_freya00` 的区别，并提醒装过旧版的人还原 `r_freya00.wad`）；
  - 安装、卸载、同时安装两个 mod 的做法；
  - 内容和各距离的精度；
  - 已在游戏里验证的范围、未验证的范围、已知限制。
- **冲突：** 替换同一个 wad 的 mod 只能装一个。奎托斯版与 KarinPicodraTech_Kratos 互斥；两个 mod 的补丁包可以同时留在 `exec/patch/` 里，切换时只换 wad 和 boot-options。
- **许可：** 发布包含有从源模型转换出来的网格和贴图。公开分享前，先确认源模型的许可是否允许再分发；本库不收任何发布包。
