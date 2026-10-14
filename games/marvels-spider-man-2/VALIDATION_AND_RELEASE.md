# 验证与发布

## 1. 离线闸门

构建产物进实机之前必须全部通过：

- `sm2_verify_stage.py`：每个模型的 body look LOD0 解码回来，权重和为 1，带权关节都有 0x80，没有离主关节超过 0.7 m 的顶点（重映射错误），
  所有 LOD 共用一块几何。可以输出回读联系表（`--sheet`）。
- `sm2_verify_face.py`：面罩脸与头模型脸逐顶点重合（< 1 mm），面部网格权重和与 0x80 位正常。
- `test_dyn_model.py`：
  - bind 姿势与逆 bind 一致；
  - Lookup 排序完整、哈希正确；层级 / 叶子计数；
  - **每个 0x01 关节都在 ModelMirrorIds 里**；
  - 动力学段读回后重建一致；每个模拟关节都带权；T5 整数字段独立核对。
- actor：`i30_actor_edit.verify` 重新解码，检查计数、偏移、哈希、引用表；未改的组件逐字段相同；改前改后长度变化与预期一致。
- 增量包和完整包逐资产比较；回归重建（同一命令）与上一版本逐资产相同。
- 姿势检查（`sm2_pose_check.py`）：改了裙子或拟合参数时看蹲 / 栖 / 坐 / 跨步的穿插率。

这些都只算 `offline-accepted`。

## 2. 实机闸门

1. 游戏关闭时安装；首次前备份存档，之后只读档。
2. 上传的包先核对 SHA-256，安装后在 toc 里确认改动资产指向新归档。
3. 标题画面是第一个测试台：Peter 和 Miles 会出现在标题背景里（三种随机场景）。
4. 进游戏用 CONTINUE 读档，然后：战衣菜单里切换几套（两族都要有）→ 自由漫游、摆荡、急停、下蹲 / 爬行 → 镜头拉远拉近。
5. 物理要连续观察几秒以上，看是否在约 1 秒后冻结；单张截图不够。
6. 每轮只问一类问题（例如「物理是否持续」「尾巴是否跟随身体」），把用户原话记进 PROJECT_STATE。

## 3. 发行包

```text
Karin_SM2_v<N>/
  Karin_Original.stage        （Overstrike 也能直接装）
  installer/                  sm2_install.py、sm2_dat1.py、sm2_stage.py、crc64_table.py（纯标准库）
  install.bat / uninstall.bat （CRLF）
  README.md                   内容、两种装法、卸载、已知限制、SHA-256
```

- 发布前在临时目录里拷一份原版 toc 做演练：install → status → uninstall。核对两点：
  - 装后 toc 的 SHA-1 与测试机上实测的安装一致（v2：`69ce1233d4fe`）；
  - 卸载后回到原版（`318f4345f3a1`）。
- 发布包的 stage 与通过实机的测试包逐资产相同，只改包名和描述。zip 时间戳会让文件哈希不同，所以比较的是资产而不是文件。
- 新版本直接覆盖安装即可（都从 `toc.BAK` 重来），不需要先卸载旧版本。

## 4. 证据分层与未测场景

| 项目 | 证据 |
| --- | --- |
| 108 个模型的几何、贴图、材质 | 标题画面 + 多套战衣游戏内 `runtime-confirmed` |
| 裙子蹲姿 | `runtime-confirmed`（T9） |
| 表情（面部骨骼） | 离线渲染张嘴、抬眉、视线、微笑；实机只在部分场景看过 |
| v1 物理（蜘蛛猫战衣） | 菜单 + 游戏内 `runtime-confirmed`（T15–T17） |
| v2 物理（91 套带面罩战衣） | 用户抽查两族多套 `runtime-confirmed`（T21–T23）；未逐套检查 |

未测：
- 拍照模式拉远；
- 过场动画里的物理和表情；
- 共生体 Peter boss 战；
- antiock 的 nomask 剧情段（已知无链）；
- `hero_spiderman_invisible` 的使用场景；
- 便装与 young 的物理（未做）；
- 布料战衣（Havok cloth 的 meta 未动）。
