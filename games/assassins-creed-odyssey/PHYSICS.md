# 物理（Reflex3 物理骨架）

Karin 的双马尾、侧发、刘海、脸颊发、丝带、鞋标、裙片、耳、尾巴用游戏自己的 Reflex3 物理：拟合时把这些骨链保留成 `KP_*` 骨，
身体网格蒙在它们上面；再把卡珊德拉专属的头发骨架 `ACD_CHF_PLA_Hair_NEW` 重建成「Reference 起的父链 + KP 骨 + 每根模拟骨一条 Physics 约束」，
替换它的每一份副本。v5 的骨架：121 根骨（21 根基础骨、100 根 KP 骨）、66 条物理记录。第二个模型 Karin_PicodraTech v1（2026-10-24，未实测）：
190 根骨（10 根基础骨、180 根 KP 骨）、107 条记录（§6）。

## 1. 奥德赛的 Reflex3 blob（2026-10-19 解出，`build-sensitive`）

- 骨架对象里的 `Reflex3Constraints.BinaryData`（XML 里是 `Unsigned8` 数组）。**格式比影 / 幻景旧**：AnvilToolkit 1.3.6 的 Reflex3 读取器只认幻景，
  读不了；`aco_phys_skel.py` 直接写字节。
- blob = `66 66 46 40`（f32 3.1）+ 紧挨着的记录 `[u8 类型][正文]`，没有魔数和状态块。
- BoneInfo = u32 骨 ID、u32 父 ID（约束相对的那根骨）、4×4 行主序矩阵（平移在第 3 列）= 绑定时的 父⁻¹ · 骨。骨 ID = 骨名的 CRC32。
- **类型 21 = Physics，固定 377 字节**（原版头发、马尾 H47、箭袋、独眼巨人的裙子里都有）：

  | 偏移 | 内容 |
  | --- | --- |
  | +0 | u8 21 |
  | +1 | u32 骨 ID、u32 父 ID |
  | +9 | M0 = 父⁻¹ · 骨（行主序 [R\|t]） |
  | +73 | M1（原版 ≈ M0；写出器写 M0） |
  | +137 | M2 = 父骨在网格坐标系里的绑定（原点在地面） |
  | +201、+265 | M3 = M4 = M0 |
  | +329 | `00 00 00 01` |
  | +333、+337 | f32 范围 A 的 min、max（弧度） |
  | +341 | u8 1 |
  | +342、+346 | f32 范围 B 的 min、max（弧度） |
  | +350 | f32 质心距离（米） |
  | +354、+358 | f32 0、0 |
  | +362 | f32「gf」（原版 0.1–1.0，往链梢变大；马尾从根 0.25 到梢 1.0） |
  | +366 | f32 重力（9.8；辫子 15） |
  | +370 | u8 标志（写 1），后跟 2 个 0 字节 |
  | +373 | u32 链深度 |

- 语义：原版链骨局部 +X 沿链、+Y 前后、+Z = X × Y（[技术合同](TECHNICAL_CONTRACTS.md) §6）。从原版马尾的范围（挂在脑后的尾巴 B = [−1.05, 0]）推断
  **B = 绕局部 Z 摆（+ = 梢向 +Y，向前）、A = 绕局部 Y 摆（侧向）**（`reference-inferred`；v5 按它把裙片改成只向外摆后，没有再报穿模）。
  **gf 被当作重力系数，含义没有确认**（`hypothesis`）。
- **A 的正负方向没有确认**（`hypothesis`）。原版里唯一一个单侧的 A 是独眼巨人裙子的前片：A = [0, 0.38]。如果它的意思是「只许向外摆」，
  那么 +A = 梢向骨的 +Z，和右手定则（绕 +Y 转正角时 +X 转向 −Z）相反。只有这一个样本，**没有拿它做依据**：凡是左右方向要紧的链（PicodraTech 的外套下摆片），
  A 都取对称范围，偏向一侧的限制只放在 B 上（B 的方向也是从原版马尾推断的 `reference-inferred`，v5 的裙片按它改了之后没有再报穿模）。
- 别的记录类型（7 / 1 / 0 三连、6 / 2 / 66、裙子和披风的 8 + 1:366、布料 63）没有解，本项目不需要。
- 骨架 XML 往返也有空引用填充字节的问题（2 个字节），同样用 `compile_fixed` 修（[技术合同](TECHNICAL_CONTRACTS.md) §9）。

## 2. 物理骨架的位置与重建（`aco_phys_skel.py`）

- 头发表列 3 的 `ACD_CHF_PLA_Hair_NEW`（`00000194D13C465D`）是卡珊德拉专属的附加骨架，跟头发表一起加载；整个替换成 Karin 的骨架，写进每一份副本
  （`runtime-confirmed`：v4 起 KP 骨在游戏里加载并摆动）。
- 模板 = 原版 `Hair_NEW` 的 XML：对象 ID、`SkeletonKey` / `HierarchyKey` 和骨以外的字段保留（影项目里替换过的骨架用旧键也能跑）。
- 基础骨：KP 链根的父骨及其全部祖先，骨块从 `ACD_Unisex_BaseSkeleton` 复制（和原版 `Female_Boobs` 附加骨架同一个坐标系：Reference 起、原点在 Hips、
  根的默认局部位置 (0, 0, 0.964)）。
- KP 骨：全局变换 = Karin LOD0 网格里的绑定（`_ody.glb` 的逆绑定矩阵求逆，连没有蒙皮顶点的链根也有；或 AcoHarness `mesh-bones` 的输出），
  从网格坐标系换到骨架坐标系；局部 = 父的全局⁻¹ · 全局，所以静止姿势 = 绑定姿势。
- 从 `Reference` 深度优先排序；`Index`、`ChildBoneCount`（= 后代数）、内联对象 ID（0xF8000000 + 序号）、`RootBone`、`RootBoneDefaultLocalPosition`、
  `Reflex3Constraints` 的对象 ID 都按新骨表重写，`BinaryData` 换成新 blob。
- 每根要模拟的 KP 骨一条类型 21 记录：深度 0（链根）只有 `root` 时才模拟；`step` = 每隔几节模拟一节（中间的刚性跟随）；
  质心 = `com_rel` × 携带长度（自己这一段 + 到下一个模拟节点之前的刚性跟随段），至少 0.03 m；`gf` 可以是 [根, 梢] 的线性渐变；重力 9.8；
  M2 用父骨的网格绑定。
- 参数表 `DEFAULT_PARAMS` 的行是 `[正则, {字段}]`，`--params` 的行排在它前面。**按键合并，不是整行取第一个**（`params_for`）：从后往前把所有匹配的行
  都 `update` 进来，再把第一个匹配的非 `*` 行 `update` 一次；结果是每个键取最靠前的那条匹配行的值。正则用 `re.match`（前缀匹配、不分大小写），
  所以 `KP_Tail` 也匹配 `KP_Tail_Ribbon`，宽的行里的键会漏进更具体的名字：
  - 想让宽行 `"off": true` 下面的某几节照常模拟，具体的行要写 `"off": false`；
  - 别的链继承来的 `step`、`gf` 渐变同样要显式覆盖（PicodraTech 的蝴蝶结飘带 `KP_Tail_Ribbon` 从尾巴的 `KP_Tail` 继承了 `step 2`，要写 `"step": 1`）。
  第一次生成时这两处都漏了，蝴蝶结的根、环和飘带基节没有记录；看日志的记录数（100 → 修正后 107）和 `--report` 才发现。
  JSON 字符串里正则的反斜杠要双写，经 shell heredoc 或编辑工具转写时常被吃掉一个、成了非法 JSON；数字直接写 `[0-9]`，不用 `\d`。
- `--attach SRC=DST[;…]`（2026-10-24，同影项目 `make_phys_skel` 的做法）：SRC 链根以下的每根骨改挂到 DST 链上离它最近的一段（按绑定位置算点到线段的距离），
  自己不写约束，也不计入 DST 链的携带长度和 gf 渐变。PicodraTech 的耳机线 `KP_Code_L/R` 挂到双马尾上（影项目里单独模拟时它们下垂、不跟着马尾走）。

## 3. KP 骨的朝向（`fit_karin.py --phys`）

奥德赛的原版物理链骨沿局部 +X（头发、马尾、裙链都是；影用 −Z）。拟合脚本建 KP 骨时让骨的 head → tail 指向前方并垂直于链，roll 让 Z = X × Y，
于是局部 X 就是链的方向、Y 朝前（矢状）。范围 A / B 因此和原版的含义一致（§1）。

## 4. 各版参数与用户评价（`case-derived`）

角度为弧度，`com_rel` 除默认行外都是 0.6。v6 的值就是便携包 `aco_phys_skel.py` 的 `DEFAULT_PARAMS`，v7 / v8 沿用。

| 链（`KP_` 前缀） | v4（首版） | v5 | v6（v8 沿用） |
| --- | --- | --- | --- |
| `Hair_tail`（双马尾） | step 2，A ±0.35，B [−0.6, 0.1]，gf 0.25 → 1.0 | 同 v4 | 同 v4 |
| `Hair_side` | A ±0.2，B [−0.3, 0.1]，gf 0.5 | 同 | 同 |
| `Hair_front` | A ±0.12，B [−0.12, 0.08]，gf 0.3 | 同 | 同 |
| `Cheek` | A ±0.15，B [−0.15, 0.1]，gf 0.3 | 同 | 同 |
| `Ribbon_hand` / `Ribbon_(camisole\|tops)`（含根）/ 其它 `Ribbon` | ±0.3 / ±0.25 / A ±0.3、B [−0.3, 0.1]，gf 0.6 | 同 | 同 |
| `Shoes_tag`（含根） | ±0.3，gf 0.6 | 同 | 同 |
| `Skirt` | 全部 A ±0.2，B ±0.2，gf 0.5 | 前片 0 / 1 / 2：A ±0.15，B [0, 0.3]；3：B [0, 0.25]；侧片 4：B ±0.15；后片 5–8：B [−0.3, 0]；gf 0.5 | 同 v5 |
| `Ear`（含根） | 关 | A / B ±0.08，`com_rel` 0.5，gf 0.15 | A / B ±0.25，gf 0.5 |
| `Tail` | 关 | step 2，A ±0.25，B ±0.2，gf 0.2 → 0.5 | step 2，A ±0.35，B ±0.3，gf 0.3 → 0.75 |
| 默认 `*` | A / B ±0.2，`com_rel` 0.5，gf 0.5，重力 9.8，不模拟链根 | 同 | 同 |

- v4 的取值都在原版（头发、马尾、裙子、箭袋的样本）范围内，并沿用影项目的经验：长链少模拟几节、质心约 0.2 m、耳朵和尾巴在世界重力下会塌。
- **v4，用户**：「双马尾、面颊头发的物理效果良好」（`runtime-confirmed`）；「尾巴和耳朵则没有明显可见物理」（当时关着）；「大腿前方在跑动时会穿出裙片」
  （`runtime-rejected`）。
- **v5，用户**：尾巴「尚可，稍微再柔软一点」，耳朵「不够明显，可以再柔弱一些」。裙片（§5）之后没有再报。
- **v6**：尾巴、耳朵按上面的话放大范围、提高 gf。v6–v8 都带着这组参数在游戏里跑过，用户的反馈都集中在眼睑，**没有单独评价 v6 的尾巴 / 耳朵**
  （`runtime-load-pass`）。

## 5. 裙片

- 里程碑 1（v1–v3）裙子刚性地蒙在髋上，跑动时大腿可能穿出（当时记为待办）。v4 起裙片是 KP 物理链，摆角对称 → 跑动时大腿从前片穿出（用户）。
- v5：**裙片只许向外摆**：前片的 +Y 朝外，B ≥ 0；后片的 +Y 朝向身体，B ≤ 0；侧片保持对称的小范围。同时用影项目的 `skirt_follow.py --max 0.95 --sigma 0.2`
  （不随包）加强裙子对大腿的跟随。之后没有再报穿模，但用户没有单独确认（`runtime-load-pass`）。

## 6. Karin_PicodraTech v1 的参数（`case-derived`，未实测）

34 个链根、180 根 KP 骨（含 `--fix-bones` 重建的发簪流苏 `Ornaments_1…4`）。双马尾、侧发、刘海、发带、狐耳、尾巴的名字能被 `DEFAULT_PARAMS`（v6）匹配上，
直接沿用；其余用 `--params` 的 17 行，是影项目里 PicodraTech 的调校换算到奥德赛的范围。角度为弧度；`com_rel` 除 `*` 默认行（0.5，`Belt_Ribbon`、
`Pocket_String` 落在这一行）外都是 0.6，蝴蝶结的几行直接给质心 `com`（米）。

| 链（`KP_` 前缀） | 记录数 | A | B | gf | 说明 |
| --- | --- | --- | --- | --- | --- |
| `Hair_Tail`（双马尾） | 8 | ±0.35 | [−0.6, 0.1] | 0.25 → 1.0 | v6 默认行，step 2 |
| `Code`（耳机线） | 0 | — | — | — | `--attach` 到双马尾 |
| `Hair_Side` / `Hair_Front` / `Ribbon`（发带） | 4 / 4 / 2 | ±0.2 / ±0.12 / ±0.3 | [−0.3, 0.1] / [−0.12, 0.08] / [−0.3, 0.1] | 0.5 / 0.3 / 0.6 | v6 默认行 |
| `Ear`（狐耳，含根） / `Tail`（尾巴） | 4 / 3 | ±0.25 / ±0.35 | ±0.25 / ±0.3 | 0.5 / 0.3 → 0.75 | v6 默认行 |
| `Ahoge`（呆毛） | 3 | ±0.2 | ±0.2 | 0.2 | |
| `Accessory_Ear`（头顶饰件，含根） / `Halo`（光环，含根） | 2 / 1 | ±0.12 / ±0.08 | 同 A | 0.3 / 0.2 | 刚性饰件，小范围 |
| `Ornaments`（发簪流苏） | 3 | ±0.3 | ±0.3 | 0.6 | |
| `Breast`（含根） | 2 | ±0.06 | ±0.06 | 0.3 | |
| `OuterA` / `OuterB` / `OuterC` / `OuterD`（外套下摆片） | 6 / 9 / 6 / 6 | ±0.1 | [−0.15, 0.3] / [−0.25, 0.25]（中后片 `OuterB`、`OuterB_<n>`：[−0.25, 0.05]） / [−0.3, 0.1] / [−0.3, 0.05] | 0.5 | B 偏向一侧（前片多向前、后片多向后；两侧的 `OuterB` 对称），A 对称（§1） |
| `Back_Ribbon` / `Tail_Ribbon`（背后蝴蝶结的环 / 飘带） | 5 / 2 | ±0.12 / ±0.2 | 同 A | 0.5 | 只模拟根、环和飘带的基节（质心 0.25 / 0.15 / 0.2 m），其余 `"off": true` 刚性跟随（§2 的合并规则） |
| `Belt_Ribbon` / `Pocket_String` | 11 / 6 | ±0.2 | ±0.2 | 0.5 | `*` 默认行 |
| `Belt_String` / `Right_Belt` | 2 / 2 | ±0.25 | ±0.25 | 0.6 | |
| `Leg_Ring_Ribbon` / `Leg_Ribbon` | 4 / 12 | ±0.3 | ±0.3 | 0.6 | |

链根（`fit_karin.py --phys`，源骨名，34 个）：

```text
Hair_Tail.L,Hair_Tail.R,Tail_1,OuterA.L,OuterB.L,OuterC.L,OuterD.L,OuterA.R,OuterB.R,OuterC.R,OuterD.R,OuterB,Belt_Ribbon_Root,Hair_Side_1.L,Hair_Side_1.R,Ribbon_1.L,Ribbon_1.R,Ahoge,Hair_Front_Root,Breast_1.L,Breast_1.R,Ear_1.L,Ear_1.R,Code.L,Code.R,Leg_Ring_Root.L,Leg_Ribbon_Root.R,Belt_String_1.L,Belt_String_1.R,Right_Belt_1,Ornaments_1,Accessory_Ear.L,Accessory_Ear.R,Halo
```

`--params` 的 17 行（`aco_phys_skel.py --params`，排在 `DEFAULT_PARAMS` 前面；`"off": false` / `"step": 1` 是为了挡住宽行漏进来的键，§2）：

```json
[
 ["KP_Tail_Ribbon(_4)?$", {"off": false, "step": 1, "a": [-0.2, 0.2], "b": [-0.2, 0.2], "com": 0.2, "gf": 0.5}],
 ["KP_Tail_Ribbon", {"off": true}],
 ["KP_Back_Ribbon_Root", {"off": false, "a": [-0.12, 0.12], "b": [-0.12, 0.12], "com": 0.25, "gf": 0.5}],
 ["KP_Back_Ribbon(_[LR4])?$", {"off": false, "a": [-0.12, 0.12], "b": [-0.12, 0.12], "com": 0.15, "gf": 0.5}],
 ["KP_Back_Ribbon", {"off": true}],
 ["KP_OuterB(_[0-9])?$", {"a": [-0.1, 0.1], "b": [-0.25, 0.05], "com_rel": 0.6, "gf": 0.5}],
 ["KP_OuterA", {"a": [-0.1, 0.1], "b": [-0.15, 0.3], "com_rel": 0.6, "gf": 0.5}],
 ["KP_OuterB", {"a": [-0.1, 0.1], "b": [-0.25, 0.25], "com_rel": 0.6, "gf": 0.5}],
 ["KP_OuterC", {"a": [-0.1, 0.1], "b": [-0.3, 0.1], "com_rel": 0.6, "gf": 0.5}],
 ["KP_OuterD", {"a": [-0.1, 0.1], "b": [-0.3, 0.05], "com_rel": 0.6, "gf": 0.5}],
 ["KP_Ahoge", {"a": [-0.2, 0.2], "b": [-0.2, 0.2], "com_rel": 0.6, "gf": 0.2}],
 ["KP_Breast", {"root": true, "a": [-0.06, 0.06], "b": [-0.06, 0.06], "com_rel": 0.6, "gf": 0.3}],
 ["KP_Accessory_Ear", {"root": true, "a": [-0.12, 0.12], "b": [-0.12, 0.12], "com_rel": 0.6, "gf": 0.3}],
 ["KP_Halo", {"root": true, "a": [-0.08, 0.08], "b": [-0.08, 0.08], "com_rel": 0.6, "gf": 0.2}],
 ["KP_Ornaments", {"a": [-0.3, 0.3], "b": [-0.3, 0.3], "com_rel": 0.6, "gf": 0.6}],
 ["KP_Leg_(Ring|Ribbon)", {"a": [-0.3, 0.3], "b": [-0.3, 0.3], "com_rel": 0.6, "gf": 0.6}],
 ["KP_(Belt_String|Right_Belt)", {"a": [-0.25, 0.25], "b": [-0.25, 0.25], "com_rel": 0.6, "gf": 0.6}]
]
```

不做 `skirt_follow`：下摆片离中线 0.22–0.36 m，挂在大腿外侧。实机效果、A 的方向、190 根骨 / 107 条约束是否碰到引擎的上限都没有观察过。

## 7. 未决

- v6 尾巴 / 耳朵的软度等用户评价。
- Karin_PicodraTech v1 的全部链都没有在游戏里看过（§6）。A 的正负方向（§1）要靠一个只给单侧 A 的诊断构建来确认（例如让一侧下摆片只许向外摆，看它往哪边去）。
- gf 的确切含义、其它记录类型、布料约束都没有解；只用了类型 21。
- 没有给物理链加碰撞；头发与身体的穿插没有专门检查。
