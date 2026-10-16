# 技术合同

除标注外均为 `days_gone_classic` build `10034136` 上的实测。

## 1. 游戏与 pak

- 引擎：Bend 改过的 UE 4.11。游戏自己的包是 `FileVersionUE4 500`、licensee `34`，名字表带哈希；
  **原版 UE 4.11.2 cook 出来的包（`498` / licensee `0`）游戏照样加载**（参考 mod 和本项目都靠这一点）。
- pak v3、zlib、挂载点 `../../../BendGame/Content/`。主包 `BendGame\Content\Paks\BendGame-WindowsNoEditor.pak`
  （和 `_P`），流式包在 `BendGame\Content\sfpaks\`（含 `startuppackages.pak`）。不加密。
- CUE4Parse 能读游戏包（DgExport 默认 EGame；读原版 4.11 cook 出来的 mod 包时设 `DGX_GAME=GAME_UE4_11`）。
  **游戏贴图是 Bend 格式，CUE4Parse 解不了**；mod 用原版 4.11 cook 的贴图，游戏能正常显示。
- 每个动画、蓝图、网格都能用 `upkg.py`（本项目的最小 uasset 读写器：名字表、导入 / 导出表、带标签属性、追加导出 / 导入）
  按字节改。

## 2. mod 加载

- mod pak 放 `BendGame\Content\Paks\~mods\`，命名 `zz_*_P.pak`（`_P` 后缀当补丁包，`zz` 让它最后挂载）。
- 必须把 `BendGame\Content\sfpaks\startuppackages.pak` 改名为 `disabled_startuppackages.pak`（参考 mod 的安装说明就这样要求；
  本项目只在改名后的环境里测过）。
- 用户自己放在 `%LOCALAPPDATA%\BendGame\Saved\Paks` 的其它 mod（无限油、快速搜刮）与本 mod 共存。
- 只能在游戏关闭时替换 pak。替换迪肯的 mod 之间互相覆盖。

## 3. 目标资产与使用者

- 玩家 pawn `Libraries/Blueprints/Player/BendDefaultPlayerPawn`：`CharacterMesh0` = `deacon_head_standard`，
  `PhysicsAssetOverride` = `deacon_master_PhysicsAsset2`（20 个刚体、19 个约束），动画蓝图 `Animation/Deacon/Deacon_VimBlueprint`
  （原版 AnimBlueprint，3 356 个动画节点，其中只有 7 个 AnimDynamics）。
- 迪肯由 `Characters/Deacon/looks/` 下 66 个 `BendSkeletalMeshLook` 组成部件；**每个 look 的主部件（`MasterPartIndex`）都是头部网格**
  （`deacon_head_{standard,flashback,scrag_beard}`），它是主姿势组件、跑动画蓝图。
- 做法（与参考 mod 相同）：全部几何放进 `deacon_head_standard`；`patch_looks.py` 把每个 look 的主部件指向 Karin 网格和
  Karin 的材质实例（look 按槽号覆盖材质），其它部件的网格设为 null。只改 int32 包索引并追加导入，属性布局与游戏的版本 500
  序列化器字节兼容。
- 衣服原有的 APEX 布料（`deacon_up_standard` 的 .apx）随部件一起消失；`deacon_master_BoneController` 驱动的辅助骨不受影响。

## 4. 骨架与重定向

- `deacon_master_Skeleton` 547 骨，根 `Align`（没有 `Armature`）。身体骨和 `Head` / 眼 / `Jaw` 的平移重定向是 `Skeleton`
  （长度取网格 → 可以用 Karin 的比例），`Hips` 是 `AnimationScaled`，`face_*` 和辅助骨是 `Animation`。
- Karin 按 1.30 倍缩放，迪肯骨架的每段骨按 Karin 缩放后的比例重设长度（朝向和关节角保持迪肯的，`build_body.py --prop karin`）；
  t0 试验过直接对到迪肯骨位（`--prop deacon`，1.40 倍、头下移 5 cm 缩短 2.1 倍的脖子拉伸），没有采用。手指映射到 `*Hand{Thumb,Index,Middle,Ring}1-3`、
  `*InHandPinky1-3`，脊柱分到 `spine..spine4`，脖子 `Neck` / `Neck1`。
- 编辑器导入 FBX 时会给网格建自己的 `_Skeleton`；`make_pak.py` 把网格的骨架导入改指 `/Game/Characters/Deacon/deacon_master_Skeleton`，
  并把根骨的局部姿势改成参考 mod 的布局（`Armature` 绕 X −90°，`Align` 单位）。
- **面部**：`face_*` 关节由 `face_rig.py` 挪到 Karin 脸上；pak 里带一份改过的 `deacon_master_Skeleton`，把 280 个 `face_*` 的重定向改成
  `AnimationRelative`（`skel_retarget.py`），动画的平移就加在 Karin 的关节位置上而不是迪肯的。
- **烘焙叠加动画的重定向**（UE 4.11 `UAnimSequence::RetargetBoneTransform`）：`Skeleton` 模式的骨平移增量被清零，`Animation` /
  `AnimationRelative` 保留原始增量（引擎里检查 `Skeleton|Animation` 的 `check` 在 shipping 里被编译掉，`AnimationRelative` 也照常工作）。

## 5. 网格专用骨与参考姿势

- 网格可以带骨架里没有的骨：126 根 `KO_*`（VRM spring 链）、20 根 `KB_*`（眼睑）都能加载、蒙皮，动画蓝图节点按名字找得到。
- UE 导入时把骨名里的 `.` 改成 `_`、空格改成 `-`。FName 带数字后缀时按「基名 + 编号」存（`KO_Skirt_0` = `KO_Skirt` #1），
  往包里写骨名要这样拆。
- **UE 加载网格时从参考姿势重建逆绑定矩阵**（`USkeletalMesh::CalculateInvRefMatrices`，不序列化）。所以 cook 之后直接改参考姿势数组
  （每一份序列化副本都要改）就能给网格专用骨加旋转和非均匀缩放，蒙皮在静止时不变（`blink_amp.py`）。
- UE 的 FTransform 组合不表示切变：父骨的非均匀缩放加子骨旋转只能得到「旋转 × 对角缩放」形式的线性映射，设计放大骨时按这个约束。

## 6. 材质实例与网格缓冲

- Karin 的材质实例是游戏 MI 的副本（`mi_deacon_head` 给皮肤类、`mi_deacon_eyelash_hair` 给透明），保留游戏 cook 好的静态排列着色器图，
  只把贴图导入改指 Karin 的贴图或游戏的空白贴图。
- **带内联着色器图的 MI，导出数据在文件里的位置不能动**：头部只要变长（例如多 236 字节），加载就
  `LowLevelFatalError ... Invalid BufferCount=0`；挪动 125 个着色器 SkipOffset 也没用。`retarget_inplace.py` 改写名字表里不用的字符串
  （头部大小不变，备用名补齐长度）；导出保留游戏 MI 的名字，look 导入 `/Game/Karin/Materials/MI_Karin_X.mi_deacon_head`。透明 MI 没有着色器图，可以变长。
- 迪肯的材质贴图（S/R/DPM/T）按迪肯的头部 UV 画，会把毛孔搬到 Karin 脸上 → 换成 `BlankTextures/material_roughNonMetal_m`；皱纹贴图换空白。
- UE 4.11 导入按「计算法线」处理，VRM 自带的法线丢了（脸上阴影发脏）。不进编辑器的修法：在 cook 后的 GPU 蒙皮顶点缓冲里原地改
  （`skelmesh_normals.py`）。缓冲头在 `MeshExtension (1,1,1)` / `MeshOrigin (0,0,0)` 之后：`int32 32, int32 count`；每个顶点
  TangentX u8[4]、TangentZ u8[4]、骨索引 u8[4]、权重 u8[4]、位置 f32[3]、UV f16[2]。双面角点按绕序归边。位置也可以这样改
  （`skelmesh_positions.py`，裙下身体内收）；文件里没有别的位置副本。

## 7. 动画

- 面部情绪（`facial/FaceMoods`）、瞬时表情（`facial/Momentary`）、口型（`vo/lipsync/dcn_visemes-*`）都是 `AKF_PerTrackCompression`、
  `AAT_LocalSpaceBase` 叠加动画，基准 `misc/dcn_ref_pose` 第 0 帧。**CUE4Parse 把它们解成常数轨道**；`anim_pertrack.py` 自己解：
  文件里的轨道是按骨顺序依次存放（平移、旋转、缩放），偏移表只决定内存里的位置；用大小字段定位字节流，嵌套曲线结构跳过。
- 叠加增量：旋转 `q_anim · q_base⁻¹` 在父骨（Head）空间左乘，平移相加。
- 口型：`AnimationSets/DeaconLipSyncAnims` 列出 17 个口型（AA AH AO AW CH EH EY F IH L M N OY R W X Y，各 2 帧），
  台词的口型数据在 `Audio/_lipsync_data/*.lsd`（文本：`phn_vis <起> <止> <n> <口型> <权重> …`，33 ms 一步，音素名是 ARPAbet）。
  抽样的两条台词里，每步最大的非静止权重中位数 0.39、90% 分位 0.77。

## 8. 动画蓝图图手术

在已烘焙的 `Deacon_VimBlueprint` 里加节点（`abp_springs.py`），规则来自 UE 4.11 源码（AnimNodeBase、AnimBlueprintGeneratedClass、
AnimInstanceProxy）和三次崩溃：

- `AnimNodeProperties` = 类字段链（`Children` → `Next`）里所有动画节点结构属性，按链的顺序。
- `FPoseLink::LinkID` **正序**直接索引它；`RootAnimNodeIndex`、烘焙状态机里的节点索引、编进 ubergraph 的节点索引
  （`GetInstanceAssetPlayerTime`、`GetRelevantAnimTime` 等约 170 处调用）都是**倒序**（`Num-1-i`）。
- 所以新节点的结构属性导出要插在**链头**（类的 `Children`），倒序索引全都不用动，旧的每个 pose `LinkID` 加 M。
  **数组里的链接也要加**（BlendListByBool/Enum/Int 的 `BlendPose`、LayeredBoneBlend、PseudoStateInstanceRingBuffer：t22 统计时 2 480 个链接里有 880 个在数组里）。
- 新链插在某个已有节点前面：新链第一个节点接它原来的输入，它接新链最后一个节点。
- CDO 里的节点标签从同类模板节点复制（没有暴露输入）；平面限制元素从另一个节点复制。
- 失败记录：插在链尾 → 倒序索引全错，状态机的姿势链接成环，加载时栈溢出（WER：ucrtbase c0000005；dump：一个返回地址在 10 MB 栈上重复 8 万次；
  Steam 之后一直说游戏在运行，要先关「回報問題」窗口）。漏改数组里的链接 → 能进游戏，几秒后 A-pose。
- `AnimNode_BoneDrivenController`：从零写进 CDO 的节点能被解析，但**在游戏里没有任何效果**（连常数 15 cm 的 Head 抬升都不生效）。
  **克隆图里已有的 `AnimNode_CopyBone`**（`RightHandProp → ref04`）可用：改源 / 目标骨、`ControlSpace = BCS_ParentBoneSpace`（直接复制局部变换数值）
  和平移 / 旋转 / 缩放开关。
- t31 的图：3 356 个原节点 + 101 个新节点（10 个 CopyBone + 91 个 AnimDynamics），检查过 2 479 个 pose 链接。
