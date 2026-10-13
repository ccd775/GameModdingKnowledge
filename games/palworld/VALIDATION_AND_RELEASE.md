# 验证与发布

## 1. 离线闸门

Blender 构建（`report.json`）：

- 骨数（r3 为 189）、顶点数；`groups_not_bones` 为空；`joint_mismatch_cm` 为 0；链骨 X 轴误差（`chain_x_axis_err_deg`）接近 0；
- 每个面部形变的最大位移（太小说明配方没起作用）；缺失的形态键列在 `warnings` 里；
- 物理组：每组的根骨、胶囊半径和由 VRM 碰撞体缩小前的半径；被丢掉的胶囊列在 `warnings` 里。

预览（agent 看图）：全身正侧背、腿部特写、面部形变网格图；`probe_run_pose.py` 的屈髋最大帧（裙子刚性，看最坏情况）。

物理（`kawaii_sim.py`）：冲刺和慢跑两个动画上，`RESULT` 的穿模数、`FLARE` 的平均 / 最大角度；`bind=1` 下静止姿态的推动量接近 0。

UE：

- `ue_import.py` 日志：骨架骨数、网格骨数、每个槽的 MI、脸的形变列表、`IMPORT_OK`；
- `ue_build_abp.py`：编译 `errors=0`，读回的 `PhysicsSettings`、`Gravity`、曲线与参数文件一致，`ABP_OK`；
- cook：`Success - 0 error(s)`；
- pak 读回（`verify_paks.ps1`）：身体 189 骨、3 个槽；26 个脸型都带 11 个形变；37 个发型都只有 3 个顶点；AnimBP 实现
  `ALI_HumanCloth_C`，7 个 Kawaii 节点的根骨、胶囊、参数正确；MI 的父级是游戏的 MI，没有新的静态开关组合。

## 2. 实机闸门

1. 游戏关闭时安装到 `~mods`；用户已有的同类 mod 先问再动。
2. 读档（女性角色、初期装备）：不崩溃；身体、头发、兽耳、尾巴、服装都在；脸和身体对齐；比例对。
3. 物理：跑动、冲刺、跳跃中看双马尾、尾巴、裙摆的姿态（跑动时双马尾水平后飘、起跳时上扬，不可能来自刚性挂接）。
   手感（柔软度）只能由用户判断。
4. 表情：Steam F12 连拍，找眨眼帧；其余表情由游戏状态触发，单独记录是否看到。
5. 收尾：删掉自己的截图（含缩略图），不动用户的；关掉自己开的窗口。

## 3. 发行包

```text
KarinPal_rN/
  README.md
  Pal/Content/Paks/~mods/{Karin_Body_P, Karin_Face_P, Karin_HideHair_P}.pak
KarinPal_rN.zip            同内容
```

README 写明：适用版本；各包作用；安装（把 `Pal` 合并到游戏根目录）与卸载；角色需女性；护甲时用古典式化妆台设「初期装备」
（身体和头部）；隐藏发型会让男性角色没头发；联机只本地可见；冲突；三个 pak 的 SHA256；版本记录。
zip 用 `testzip` 检查，pak 哈希与构建机输出比对。

## 4. 证据分层与未测场景（r4）

| 项 | 证据级 |
| --- | --- |
| 加载、比例、脸对齐、各部件可见 | `runtime-confirmed`（r3，用户与 agent 截图） |
| 物理在运行 | `runtime-confirmed`（r3，跑动 / 跳跃截图，用户看到） |
| 眨眼 | `runtime-confirmed`（用户） |
| r3 的物理手感、跑动时裙片 | `runtime-rejected`（用户：偏硬、耳朵不柔软；大腿根穿出） |
| r4 手感与裙片 | `runtime-load-pass`（加载、粗看正常）；用户判断待定 |
| 古典式化妆台「初期装备」显示 Karin | `reference-inferred`（游戏文本 + 攻略） |

未测：除眨眼外的表情；游泳、滑翔、骑乘、攀爬、蹲伏、战斗动作中的裙摆；背负武器的插槽位置；角色创建界面（眼睛位置、发色）
对 Karin 的影响；头发的淡紫色调；多人联机。
