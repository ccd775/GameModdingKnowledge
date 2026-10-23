# 表情

## 1. 游戏的面部驱动

- 原版头部网格（`Biped_Skeleton`，140 根骨）有 144 个 FACS 风格的形变：`eye_blink_l/r`、`eye_low_blink`、`eye_open`、`eye_in_* / eye_out_*`、
  `brows_*`、`jaw_drop`、`jaw_drop_mid`、`smile_*`、`o_wide`、`kiss`、`funnel_*`、`lips_stretch_*` 等，单个位移 0.3–2.6 cm。
- 头部数据资产的 `FacialPoseAsset`（`SK_Young_M_Head_Master_Facial_Anim_PoseAsset`，男女共用）有 42 个姿势：口型（如 `Pose_AAA` → `jaw_drop_mid` 0.47）、
  眨眼（`eye_blink_l/r` 1）、挑眉、眯眼、头和眼的俯仰 / 偏转 / 滚转；共输出 108 条曲线。眼睛偏转靠 `eye_out_l` / `eye_in_r` 这类形变，
  俯仰靠 `eye_open` / `eye_blink`；下巴、牙、舌、眼骨只动几度。
- 曲线按名字驱动形变，所以**替换的头只要带同名形变**就能眨眼、对口型、看向目标；不用改面部姿势资产或动画蓝图（`runtime-confirmed`）。
- HL 的 `UMorphTarget` 格式与原版 4.27 相同，原版编辑器导入的形变直接能用。

## 2. 映射与构建

- `face_map.json`：HL 形变名 → [源形变键, 权重, 可选的左右]。Karin 的源形变是 VRChat 口型、眨眼和 MMD 表情。例子：
  - `eye_blink_l` ← `blink_L`；`eye_low_blink` ← 下眼睑上抬左右；`eye_open` ← 惊讶 + 上看 0.6。
  - 视线：`eye_out_l` ← 左看（左半边），`eye_in_l` ← 右看（左半边），右眼对称。
  - 眉：`mayu_up` / `sad_1` / `angry_1` / `down` 组合。
  - 口：`jaw_drop_mid`、`jaw_drop` ← あ × 1.6；`jaw_drop_close` ← あ × 0.8；`ee` ← い × 1.2；`o` ← お；`kiss` ← う；
    `funnel_*` ← う 0.35（分左右）；`lips_stretch_*` ← い 0.5 + 嘴宽 0.4；下唇下拉 ← え 0.6。
  - 笑：`smile_*` ← 嘴角上扬两种合成；`smile_open` ← 笑 2 + あ 0.3；`frown` ← 嘴角下压；`corner_neg` ← 生气嘴 0.6。
- `fit.py` 在头部部件上生成 HL 同名的形状键：`delta = (源键 - 基础) × 权重`，分左右时乘 `wl = clip(0.5 + x / 0.008, 0, 1)`
  （她的左边是 +x，中线两侧 8 mm 过渡）。Karin：56 个（日志 `head morphs 56 of 56`）。
- UE 导入时打开形变导入，并且**先删除旧资产再导入**（reimport 沿用旧设置，曾导入 0 个）。烘焙后读回：56 个形变，
  眨眼最大位移 4.2 cm、`jaw_drop_mid` 1.53 cm。
- 进游戏前用 Blender 渲染几组形变组合（眨一只眼、张嘴、笑、看左看右），先排除左右颠倒和撕裂。

## 3. 动漫脸的着色

拟合后只重算法线时，鼻子和嘴周围出现写实的阴影（用户：「对于动漫人物来说这应该特殊处理的，不然显得面部脏兮兮的」）。
源模型作者给脸调过自定义法线；`fit.py` 把每个 loop 的法线按变形的雅可比带过去（[角色拟合](CHARACTER_FIT.md) §4），导入时用「导入法线」。
修复后（v10）agent 实机截图里脸部干净，用户之后没再提。

## 4. 范围与限制

- 只覆盖 144 个里能和源形变对应上的 56 个；口型是近似，不是逐音素精确。
- 头部顶点只绑 `Head`，眼骨、下巴骨的小幅转动对 Karin 的脸没有作用；视线和张嘴全靠形变。
- 证据：用户在 v1.0 的测试里说「表情和物理效果都正常」→ `runtime-confirmed`。过场动画里的特写表情没有单独看过。
