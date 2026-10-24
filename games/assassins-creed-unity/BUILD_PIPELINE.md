# 构建流水线

逐条命令见 [便携包 README](../../portable-kits/assassins-creed-unity/README.md)；这里写每一步做什么、产出什么、项目里的数字。
v7 = 2026-10-24 用户接受的版本。

```text
acu_forge.py index ──► index.tsv ──► scan_objs.py ──► objs_to_tsv.py ──► arno_tables.tsv
                                                                        │
prep_karin_original.py ─► 源 blend + 贴图                                 │
export-glb（亚诺骨架 + 参考网格）─► glb_rotate +90 ─► fit_karin.py（--phys）─► face_rig.py
   ─► export_karin_lods.py ─► glb_rotate −90 ─► import-glb ×4 ─► karin_lod0..3.Mesh
                                         └─► acu_phys_skel.py ─► Karin_Phys（骨架 + 碰撞对象）
build_mod.py（每个副本一个 batch 作业）─► payload/ ─► acu_install.py / make_release.py
```

## 1. 索引与副本

1. `acu_forge.py index <游戏>\*.forge <游戏>\dlc_*\*.forge > index.tsv`：63 个 forge、180 245 行。纯标准库，几秒钟。
2. `scan_objs.py <log> <对象 ID…> <forge 过滤…>`：对选中的 forge，把每个数据文件交给 harness 的 `scan-objs`（内存里解压，按对象 ID 匹配）；
   `objs_to_tsv.py arno_tables.tsv <log…>`。目标 ID 是 `build_mod.py` 的 `TABLE_DROPS` 里的表（和附加骨架表 `0x1453680995`）。v1.5.1：189 个数据文件。
3. `build_mod.py` 另外把索引里名字含 `LegacyAvatar`、又不是贴图（`*Map`）的数据文件都加进作业，共约 470 个作业。

## 2. 源模型

`prep_karin_original.py`（Blender 5.0，后台）：Karin_Original 只有 VRM 和一个 Unity FBX（`Karin(Clone)_BlenderSafe.fbx`，膝盖已烘焙），没有 blend 和贴图文件夹。
用自动骨朝向导入（每根骨的 Y 指向子骨，拟合和物理链方向都靠它），应用骨架和网格的对象变换（米、前 −Y、上 +Z、左 +X），去掉 `PBCollider_*` 等辅助空物体，
把打包的贴图写成 `Karin_<Face|Alpha|Body|Hair|HairClipping|Costume>.png`。形态键保留（FBX 里已设好的装扮 / 内衣键由拟合脚本烘焙）。

## 3. 拟合

1. `export-glb` 导出拟合用的骨架 GLB：`ACU_BaseSkeleton_Male` + 亚诺的头部、上衣、裤子 LOD0（参考）+ 附加骨架 `ArmsSimple`、`Armpits`、`LegsRollbones`、
   `ForeArmTwist`、`ArmsFlat_Upper`、`Dress_Simple_HV_Col` + 头部骨架 `CN_U_Arno_Head_Rig`。
2. `glb_rotate.py … 90`（大革命的原始坐标系 = 奥德赛的，[技术合同](TECHNICAL_CONTRACTS.md) §6）。
3. `fit_karin.py … --scale auto --ground -0.004 --foot-scale 1.0 --foot-squash 0.8 --phys <35 个链根>`：比例 1.6541，平移 (−0.0152, 0.0947, 0)；
   骨架 208 根，映射 51 根；KP 物理骨 139 根（含 `_end`），用到的骨 147 根。链根（与影项目同一份列表）：`Hair_tail_L/R`、`Tail`、`Skirt_0`、
   `Skirt_1..7_L/R`、`Skirt_8`、`Hair_side_L/R`、`Hair_front_root`、`Ribbon_L/R`、`Ear_L/R`、`Ribbon_camisole`、`Ribbon_tops_L/R`、`Ribbon_hand_L/R_root`、
   `Cheek_Root_L/R`、`Shoes_tag_L/R`。KP 骨的局部 +X 沿链。
4. 检查：`render_compare.py`（Workbench，正 / 侧面的 Karin、亚诺、叠加）。Blender 的相对路径按 C 盘解析，参数全写绝对路径。

## 4. 表情

`face_rig.py`（奥德赛副本，`GAME_BONES` 换成大革命的头部骨）在拟合结果上加下颌、上眼睑、眼球的绑定偏移蒙皮（[表情](FACE.md)）。v7 用默认参数。

## 5. 导出与导入

1. `export_karin_lods.py -- <out> --ratios 1,0.5,0.25,0.12 --profile acu_weapon --keep-full Body`：材质名改成目标 Material ID（`acu_weapon` 档：
   `0x4B41520001..04`），合并、三角化、白顶点色、≤ 4 权重、裁骨、减面。v7：159 根骨，四个 LOD 的顶点 / 三角形 46 006 / 29 280、23 003 / 16 293、
   11 453 / 8 623、8 754 / 6 657；去掉 `Karin_Alpha` 材质的 408 个面（眼泪、脸红等叠加层，中性姿势下藏在头里，只靠表情形态键露出来）。
2. 每个 LOD `glb_rotate.py … -90`，再 `import-glb ./karin_lod<i>_acu.glb 0 ./karin_lod<i>.Mesh <原版 LOD ID>`（[技术合同](TECHNICAL_CONTRACTS.md) §5、§7）。

## 6. 物理骨架

`acu_phys_skel.py <ACU_U_Arno_Hair.Skeleton.xml> karin_lod0_acu.glb karin_phys.Skeleton.xml --id 323218444032 --report phys_report.json`：
121 根骨（100 根 KP）、55 个 BallJoint，旁边写 `karin_phys.BallJointCommonData.xml` 和 `karin_phys.LiteRagdoll.xml`（裙片碰撞）。
`--no-collide` 不写碰撞对象，`--capsule-scale <f>` 放大胶囊半径（诊断用）。细节见 [物理](PHYSICS.md)。

## 7. payload

`build_mod.py <mesh_dir> <out_dir> --phys karin_phys.Skeleton.xml`：

- 每个表作业：提取并解包这一份副本（缓存在 `ACU_SCRATCH\vanilla\<forge>\<IDHEX>\`，只导出 BuildTable 的 XML）→ 改列（`bt_tool.edit`）→
  一个 `batch`：原版 XML 重新编译比对 + 编译改过的表 + `pack-data`。附加骨架表的作业还把 `Karin_Phys` 的三个对象追加进数据文件，并把一个布料附加骨架
  的单元格改指 `Karin_Phys`（[物理](PHYSICS.md) §1）。6 个作业并行；470 个作业约 15 分钟（大部分时间是第一次提取没缓存的副本）。
- 头部容器（一个通用 payload，给全部 15 份）：换 4 个 LOD 网格，加 4 个材质、4 个纹理组、4 张漫反射、4 张平法线、1 张高光图（[技术合同](TECHNICAL_CONTRACTS.md) §8）。
- 末行 `BUILD_OK`。v7：456 个按 forge 的数据文件 + 1 个通用数据文件 + `skip.tsv`（14 行），232.7 MB。康纳（Connor）旧时代服装的附加骨架表里没有可用的布料单元格，
  打印 15 条 `WARN … no cloth add-on cell`，那身服装没有物理。
- **`ACU_SCRATCH` 放在同步盘之外**：项目目录在同步盘里时，解包出来的每个文件都被同步客户端处理，一个数据文件从约 2 s 变成约 30 s。
- harness 的 `batch` 让每个数据文件只起一个进程（原来每条命令 1–2 s 的启动 + 名字表预加载，一个数据文件约 40 s）。

## 8. 安装与发行

- 本机：`acu_install.py install <out_dir>\payload` → `status` → `uninstall`（游戏关闭）。
- 发行：`make_release.py <out.zip> v7=<payload>` → `payload_v7.tar.xz`（solid xz，按文件名排序让同一个数据文件的各个版本挨在一起压缩：232 MB → 44 MB）、
  `install_v7.cmd`、`uninstall.cmd`、`status.cmd`、`README.txt` 和 `acu_install.py`，并加上本机原版每个 forge 的大小（`vanilla_sizes.tsv`）。
  见 [验证与发布](VALIDATION_AND_RELEASE.md) §3。
