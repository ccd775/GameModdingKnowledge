# 构建流水线

命令见 [便携包 README](../../portable-kits/assassins-creed-syndicate/README.md)。耗时是构建机（6 个并行）上的实测。

```text
acs_forge.py index（40 forge，几秒）
  -> scan_objs.py / objs_to_tsv.py（表与头部 LOD 的全部副本，每组 forge 约 20 分钟）
  -> 探针 GLB：export-glb -> glb_names.py -> glb_rotate.py +90 -> measure_glb.py（鞋底）
  -> make_meshes.py（两兄妹各：fit_karin -> face_rig -> export_karin_lods -> glb_rotate -90 -> import-glb -> acs_phys_skel，约 4 分钟）
  -> build_mod.py（318 份副本，约 12 分钟，payload 约 870 MB）
  -> acs_install.py install（游戏关闭）
  -> make_release.py（solid xz + vanilla.tsv + 嵌入式 Python）
```

## 1. 索引与副本

- 索引覆盖根目录和 `dlc_*` 的全部 forge；`scan_objs.py` 跳过 `_gi` / `_grid`，伦敦、London_20、London_21 这几个大 forge 单独一组，6 组并行。
- 扫两份：表（`build_mod.TABLES` 的 20 个 ID）→ `twin_objs.tsv`；头部 LOD（8 个 ID）→ `twin_meshes.tsv`。`build_mod.py` 只取这些 ID 的命中，
  对命中的每个数据文件 ID 取它在索引里的**所有**行。

## 2. 探针 GLB（拟合坐标系）

每位双胞胎：`export-glb` 基础骨架（雅各布 `ACVI_CHR_SHR_Male`，伊薇 `ACVI_CHR_SHR_Female`）+ 头部 LOD0 + 一件服装的身体 LOD0 + 它的附加骨架 + 头部骨架
→ `glb_names.py`（CRC32 骨名、别名修正）→ `glb_rotate.py +90` → `<out_root>/probe/<twin>_fitframe.glb`。`measure_glb.py` 量出两人的鞋底都在约 0.000，
所以 `--ground 0.0`。

## 3. 拟合（`fit_karin.py`）

- `--scale auto`（得 1.6541）、`--foot-scale 1.0`、`--foot-squash 0.8`、`--ground 0.0`，stage 2 加 35 个链根（`--phys`）：
  `Hair_tail_L/R, Tail, Skirt_0, Skirt_1..7_L/R, Skirt_8, Hair_side_L/R, Hair_front_root, Ribbon_L/R, Ear_L/R, Ribbon_camisole, Ribbon_tops_L/R,
  Ribbon_hand_L/R_root, Cheek_Root_L/R, Shoes_tag_L/R`。
- **膝盖隐藏带**（v3）：源模型 `body_2` 的 `kisekae_Knee` 设为 1 却不移动任何顶点，膝盖一圈（源 z 0.31–0.40，位于 `kisekae_LowerLeg 1` 与 `kisekae_UppeLeg 2`
  之间）保持原尺寸，离过膝袜（`knee_socks` 上缘 z 0.524）只有 2 mm，游戏里从袜子里穿出。`--hide-band body_2:0.20:0.46:0.15`：在形态键烘焙之后，
  把 z 0.20–0.46 里被烘焙留在原位的腿部顶点按同侧、同高度（|dz| < 0.01）的环中心收到 15 % 半径（和 kisekae 键的做法一样），共 234 个顶点。
  `kisekae_UppeLeg 2` 保持关闭（它的上环正好是袜口）。

## 4. 表情与导出

- `face_rig.py` 每位双胞胎单独跑（[表情](FACE.md)）。
- `export_karin_lods.py --profile acs_weapon --mat-base <base> --ratios 1,0.5,0.25,0.12 --keep-full Body --split-normals skirt:40`：材质改名为
  `base + 1..4` 的材质 ID、合并、三角化、≤ 4 权重、裁骨、减面。
- **裙片法线**（v3）：百褶裙（769 顶点，没有重合顶点或面）带手调的卡通法线，最多偏离平坦褶面 50°，游戏里褶边出现污渍状暗影。`--split-normals skirt:40`
  清掉自定义法线、平滑着色、40° 以上的边切开：裙子每个角的法线都在其面法线 30° 以内；和 v2 比，218 个服装顶点法线改变（平均 33°），位置不变。
  褶面内部的边全是 < 15°（平滑）或 ≥ 40°（折痕），15–40° 的边都在腰带，所以再降角度对褶面没有影响。
- `glb_rotate.py -90` 后 `import-glb <glb> 0 <out.Mesh> <原版头部 LOD 的 ID>`。

## 5. 物理骨架

`acs_phys_skel.py <JacobFrye_Hair 模板> karin_lod0_acs.glb Karin_Phys_<twin>.Skeleton.xml --id <base + 0xF00>`；旁边写 `.BallJointCommonData.xml` 和
`.LiteRagdoll.xml`（ID +1 / +2）。参数见 [物理](PHYSICS.md) §4。

## 6. payload（`build_mod.py`）

- 先编译两兄妹的材质、TextureSet、贴图（texconv BC7）和物理对象，每个只编译一次。
- 每份副本一个作业：从原版提取（缓存在 `ACS_SCRATCH\vanilla\<forge>\<ID>`）、解包、导出表 XML → 原版 XML 重新编译必须逐字节相同 → 改表（去可视列、物理列）
  → 头部 LOD 换成 Karin → 追加这位双胞胎的材质 / 贴图 / 物理对象 → `pack-data`。全部命令用 harness `batch` 一个进程跑完。
- 没有目标表也没有头部 LOD 的副本记进 `skip.tsv`；任何作业失败都继续跑完再一起报错，不写 `BUILD_OK`。

## 7. 安装与发行

- `acs_install.py install <payload>` / `uninstall` / `status`，游戏必须关闭（[技术合同](TECHNICAL_CONTRACTS.md) §8）。
- `make_release.py <zip> s2=<payload> --python <embed zip>`（[验证与发布](VALIDATION_AND_RELEASE.md) §3）。
