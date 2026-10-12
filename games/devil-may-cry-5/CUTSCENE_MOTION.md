# 过场动作：身体骨平移轨导致的拉伸（motlist .85）

2026-10-07 的问题与修复。证据级：V 为 `runtime-confirmed`（用户：「V的过场好了」）；Nero / Dante / PT V
用的是同一方法、同一组骨，只做了离线校验和标题画面加载，相关过场没有在游戏里看过。

## 1. 症状与成因

- 症状：Original V 在实战中正常，但在部分过场里四肢和躯干被拉长、变形（胸口和肩膀最明显）。
- 成因（`case-derived`）：部分 event 动作在**每根身体骨**上带有常量平移轨（T），数值是原角色自己的骨长。
  Karin 的网格按自己的比例做了 bind，播这些动作时骨长被强制改回原角色的值，身体就被拉开
  （实测 Chest 偏 18 cm，肩膀和上臂偏 13–18 cm）。
- 实战动作没有这个问题：gameplay motlist 只对 root、`Null_Offset`、Hip、Head、`Neck_Middle`、拇指和布料骨带 T，
  其它身体骨都用网格 bind 的平移。
- 分布（build `24901913`）：V 的 315 个 event 动作里有 70 个带这种轨；Nero 和 Dante 几乎没有，
  只有 Nero `m63_100c`、Dante `m12_240`（`pl0130` 脏污形态）和 `m12_301`（`pl0120` 真魔人）。

## 2. motlist .85 / mot .65 布局（build-sensitive，逆向所得）

- motlist：头 `u32 85`、`'mlst'`；mot 指针表的偏移在 `0x10`，数量在 `0x30`。
- mot：头 `u32 65`、`'mot '`；`+0x10` 骨头指针，`+0x18` clip 头指针，`+0x50` 名字，`+0x58` 帧数，
  `+0x68` 起 `u16 boneCount`、`u16 clipCount`。
- BoneClipHeader，0x18 字节：`u16 boneIndex`、`u16 trackFlags`（1 = T，2 = R，4 = S）、`u32 hash`、`f32 weight`、
  `u32`、`u64 trackHdrOff`。
- TrackHeader，每条 0x28 字节，按 flag 依次排列：先 T，再 R，最后 S。

## 3. 修复方法

去掉指定身体骨的 T 轨，文件大小不变：

1. 把 clip 的 `trackFlags` 清掉 bit0。
2. `trackHdrOff += 0x28`，让它直接指向原来的 R 轨头。

没有 T 轨时，引擎用网格 bind 的平移，和实战动作的行为一致。轨数据本身不删，只是不再被引用。

**骨集合的选法**：先取 Karin 网格蒙皮用到的 DMC5 骨及其所有祖先（排除 `KO_*` 骨和 PT 专用骨），
再减去在该角色任一 gameplay motlist 里带 T 的骨。结果是 48 根：Chest、Stomach、Waist、Neck，
左右 Shoulder / UpperArm / Forearm / Hand / Palm，除拇指外各指 F1–F3，左右 Thigh / Shin / Foot / Foot_twist / Toe。
保留的有 root、Hip、Head、`Neck_Middle`、拇指，这些骨实战本来就带 T，Hip 的 T 还承载整体位移。

Nero、Dante、V 三个角色算出来的 48 根完全相同；KarinOriginal 和 KarinPT 的网格也相同。
所以每个角色只需要一套修补文件，PT 包和 Original 包共用（Original V 与 PT V 的 14 个文件逐字节一致）。

## 4. 产物（case-derived）

| 角色 | 修补的 motlist | mot / clip |
| --- | --- | --- |
| V | `m03_100`、`m04_200`、`m05_400`、`m07_300`、`m07_400`、`m09_100`、`m09_300`、`m09_400`、`m10_101` ev01 + ev02、`m10_200`、`m11_102`（以上 `pl0200`）、`m11_300_pl0230`、`m15_300_pl0232`，共 14 个，约 58 MB | 78 / 3743 |
| Nero | `m63_100c_pl0000_ev01` | 2 / 96 |
| Dante | `m12_240_pl0130_ev01`、`m12_301_pl0120_ev01` | 5 / 240 |

文件路径都在游戏路径表里（`natives/x64/event/...`），Fluffy 直接以散装文件替换。

## 5. 脚本（项目目录 `DMC5/Work/py/`）

- `motinfo.py`：解析 motlist，列出每个 mot 的骨、clip、flag 统计。
- `mot_strip_t.py`：`strip(path, bones)` 做上面的两步改写；`verify(orig, patched, bones)` 断言只有被改的 clip 头
  有字节差异、新偏移指向的正是原来的 R 轨头、指定骨上不再有 T。
- `ko_cutscene.py`：参数 `--roots`（按补丁优先级的 natives 根目录）、`--events`（event 路径正则）、
  `--gameplay`（gameplay motlist 的 glob）、`--mesh`（一个或多个 Karin 身体网格）、`--out`。
  它计算骨集合，修补所有命中的 event motlist，并写出 `cutscene_fix.json`（骨列表、每个文件的 mot、clip 数、
  改动字节数、sha256）。
- 打包：`ko_package.py` 用 `EXTRA` 把 `ko/cutscene_<角色>/natives` 并入包；`build_package.py`（PT V）同样并入 V 的那套。

## 6. 已知局限

- Karin 的四肢比例和原角色不同，去掉 T 之后，过场里手与道具、手与他人的接触点可能有几厘米偏差。
  这是用骨长换外形，不可兼得。
- 有极少数 mot 里，T 可能本身就是动作的一部分（不是常量）。目前选骨时不区分常量轨和动画轨，
  V 的验收里没有看到问题。
- 只修补了身体网格所用的骨。V 裸身 `pl0210` 和裂纹形态共用同一组骨，已覆盖；新角色或新 build 要重新跑脚本，
  不能照抄文件列表。
