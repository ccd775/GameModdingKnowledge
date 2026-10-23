# 验证与发布

## 1. 离线闸门

- **索引与副本**：`aco_forge.py index` 能读全部 forge（版本 28）；`aco_locate.py find` 列出的每个目标 ID 的副本与预期一致（v1.5.6：表和身体容器在
  `DataPC_SharedGroup_00`、`DataPC_patch_01`、`dlc_43`、`dlc_58` 和 `DataPC_ACD_Connection` 里都有，[技术合同](TECHNICAL_CONTRACTS.md) §3）。
- **网格**：`import-glb` 的日志里顶点格式是 `Pos3s_Norm4ub_Col4ub_Tex2s_Joint4_8bit`、骨数 ≤ 255；`mesh-bones` 和原版比，同名骨的绑定位置差在 0.1 mm 内。
- **表情**：`face_rig.py` 的报告里眨眼的 `explained` 接近 1（v5 0.983）、下颌约 0.76；杠杆长度要和眼睛的尺度相称 —— 杠杆越长，非闭眼方向的姿势被放大得越多
  （v6 的 1.44 m 出了问题）。`pose_preview.py`：静止 = 原模型、眨眼的中间状态干净、扭转姿势在 0.5 权重下不撕裂；`aco_pose_sim.py` 看眼睑对各姿势的响应。
  **离线通过不代表实机通过**：v7 离线全部正常，实机被扫视驱动的偏移推翻。
- **物理骨架**：`aco_phys_skel.py` 的骨数和记录数与上一版一致，或者变化正好是这一版要改的。
- **payload**：每张表 `compile_fixed` 打印 `restored N null-ref padding bytes`；末行 `BUILD_OK`；7 个 `.data` 加 `skip.tsv`。改动大时把打好的数据文件重新解包
  核对对象（v1 做过）。
- **安装**：`install` 为每个 ID 打印它写进的 forge 列表；`status` 的 `source` 指向这一版的 payload。

## 2. 实机闸门

1. 游戏关闭；`uninstall`（旧版）→ `install` → `status`。用户在测试机上时，先问再结束游戏。
2. 读测试存档：正面、背面、侧面截图看装备是否隐藏、有没有残留的辫子 / 脸、贴图是否正确。
3. 跑动、急停：裙片和大腿、双马尾 / 尾巴 / 耳朵的摆动。
4. 脸部特写：静止几秒和眨眼。眼睑的问题是几帧之内的切换，**请用户录 10–20 秒的录像**，逐帧看两只眼（[开发工具](DEV_TOOLING.md) §5）。
5. 对话 / 过场里的强表情（至今没做）。
6. 收尾：退出游戏或留给用户；删掉测试机上的临时文件；释放桌面锁。

## 3. 可重新部署的包

v8 打成一个不依赖构建环境、能在别的机器上重新部署的包 `ACOd_KarinOriginal_v8`（zip 5 766 118 字节，SHA-256
`697c02e25bb6ecf29749114cc3d41447fcea55ad4b941cb98f6c6fa4455773b7`）。zip 含游戏数据和模型，**私有，不发布**；这里只记结构和做法。

```text
ACOd_KarinOriginal_v8\
  payload\           7 个数据文件 + skip.tsv（与用户实测的 build_v8 逐字节相同）
  aco_install.py     安装器（= 便携包 scripts/aco_install.py 的项目原件，SHA-256 7672e2bd…）
  _env.cmd           找游戏目录和 Python
  install.cmd        先卸载旧安装，再安装 payload\
  uninstall.cmd      卸载
  status.cmd         查看状态
  README.md          中文说明：内容、要求、安装 / 卸载、原理、注意事项（更新游戏前先卸载）、已知限制、文件
  BUILD_INFO.json    版本、游戏、状态、各步参数、每个 payload 文件的字节数与 SHA-256、安装器哈希
  MANIFEST.sha256    除它自己以外所有文件的 SHA-256
```

- `_env.cmd` 的查找顺序：第一个参数 → 环境变量 `ACO_GAME_DIR` → Ubisoft Connect 的注册表
  `HKLM\SOFTWARE\WOW6432Node\Ubisoft\Launcher\Installs\5059` 的 `InstallDir`。把 `/` 换成 `\`、去掉末尾的 `\`，要求目录里有 `ACOdyssey.exe`；
  Python 先找 `py -3`，再找 `python`。找不到时说明原因并给出手动指定的用法。
- `install.cmd`：`call _env.cmd %1` → `aco_install.py uninstall` → `aco_install.py install "%~dp0payload"` → 提示「更新或校验游戏文件前先 uninstall.cmd」。
  `uninstall.cmd` / `status.cmd` 同样先 `call _env.cmd %1`。任何一步失败都以非 0 退出。
- `.cmd` 文件不在便携包里（仓库不收 `.cmd`），按上面的描述重写即可；`aco_install.py` 用便携包的版本时，`_env.cmd` 设好的 `ACO_GAME_DIR` 照样生效。
- payload（v8）：

  | 文件 | 字节 | SHA-256 |
  | --- | --- | --- |
  | `00000103E739C903_ACD_CHF_PLA_Kassandra_VisualMaster.data` | 682 | `c64fc5e6f7082d7a5caa76cd63bcb97dee3ef61b2ff783b5eea0a20f4dd81f2c` |
  | `00000104280E464B_ACD_CHF_PLA_B01_A01_BodyKassandra.data` | 815 495 | `712b260e589e01f224b99d5f8d8b73ce0e83401f659bce29cf3746a00cce785a` |
  | `00000104280E4653_ACD_CHF_PLA_B01_A01_BodyKassandra_LOD0.data` | 4 890 287 | `2916cefafb4ab157e38fae20abd08d084bbfdb466f248bdf516295c7573b557e` |
  | `00000146D5F5EB4C_ACD_CHF_PLA_Kassandra_Hair.data` | 507 | `c145da0813d694407b3f06b4f7b4c2dbd4c5281c57a968ab6526cf5437bc4356` |
  | `0000016424DFAD4B_ACD_CHF_PLA_Kassandra_Head.data` | 1 485 | `f408e657be18c4d6a374fe254af1ad0805e64843c18e3cdde0dcfdb8b73a2985` |
  | `0000018482B71630_ACD_CHF_PLA_B01_A01_BodyKassandra_LOD1.data` | 305 434 | `62cff4b84813060a4fa38ca7d7f3e19f8bff67c282b1bbb610dd624231166fc5` |
  | `00000194D13C465D_ACD_CHF_PLA_Hair_NEW.data` | 15 537 | `640ab46440c5008611cfd52723c810bd1bfbda083cdb0738c6c4bb9d7abfe6af` |
  | `skip.tsv` | 46 | `83e8e43f3e3d215a588842f564b882d4889f27338bd81bf0b5dd50af443f4e70` |

- **实测重新部署（2026-10-23，测试机）**：把包解压后运行不带参数的 `install.cmd`：从注册表 `…\Installs\5059` 的 `InstallDir` 找到游戏目录，卸载了之前的安装
  状态，把每个 ID 写进全部副本（根目录和 `dlc_*` 下的 forge，包括 `dlc_58` 的 `DataPC_ACD_Connection`）；`status.cmd` 显示来源是包里的
  `payload`。payload 与用户实测的 build_v8 逐字节相同，实机结论按身份继承；这次重新部署本身记录的是安装层面的结果。

## 4. 证据分层与未测场景

| 项目 | 证据级 |
| --- | --- |
| v1：Karin 网格和蒙皮在游戏里正确 | `runtime-load-pass`（agent 截图） |
| v1：品红色、装备仍显示（只改了 SharedGroup） | `runtime-rejected` |
| v2：贴图正确、装备和卡珊德拉的脸消失；辫子残留在后颈 | `runtime-load-pass`（agent）；用户：「整体看起来都还可以」；辫子 `runtime-rejected` |
| v3：背面 / 侧面没有辫子（弓和箭袋仍在） | `runtime-load-pass`（agent 截图） |
| 比例、模型与材质（v3 起） | `runtime-confirmed`（用户：「比例什么的都可以了」） |
| 双马尾、脸颊头发物理（v4 起） | `runtime-confirmed`（用户） |
| 尾巴 / 耳朵（v5 → v6） | v5 用户：尾巴「尚可」、耳朵「不够明显」；v6 的软化 `runtime-load-pass`，用户未单独评价 |
| 裙片只向外摆 + 跟随大腿（v5 起） | `runtime-load-pass`；之后没有再报穿模，用户未单独确认 |
| 眼睑 v8（褶骨 25°） | `runtime-confirmed`（用户 2026-10-23：「看起来可以了」） |
| 眼睑 v4 / v5 / v6 / v7 | `runtime-rejected`（[表情](FACE.md) §6） |
| 虹膜挂视线骨（v6 起） | 包含在 v8 的接受里；虹膜转动幅度没有单独确认 |
| 下颌（v5 起） | `runtime-load-pass`；幅度小，未专门调 |
| 安装器卸载 | 测试机上 forge 长度回到原值；合成 forge 上逐字节还原（便携包核对） |
| 包的重新部署 | 安装层面（注册表定位、卸载旧状态、写入全部副本、状态指向包） |

未测或未做：对话和过场里的强表情（全闭 / 眯眼姿势在 25° 闭合下可能越过闭合位置，`hypothesis`）、DLC 区域（DLC forge 里的副本装了，但没去看）、
年老的（现代篇）卡珊德拉、其它游戏版本 / 平台、4K 贴图（现在 2048）、头发透明卡片的透明效果、物理链与身体的穿插、骑马 / 游泳 / 战斗中的
裙片和尾巴（未逐项检查）。已知限制：眨眼预计只闭约 20–35 %（v7d 量出的褶骨眨眼峰值 5–9° ÷ 25°，v8 没有逐帧量过）；v7 录像里两眼有时不一样，v8 是否还看得出没有单独确认（`hypothesis`）；弓和箭袋仍显示；嘴的幅度小。
