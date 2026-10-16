# 验证与发布

## 1. 离线闸门

- DgExport 读回 mod pak（`DGX_GAME=GAME_UE4_11`）：网格的骨 = 迪肯的骨 + `KO_*` + `KB_*`，父子正确；材质实例的贴图解析到 Karin 的贴图；66 个 look 指向 Karin 网格和 MI。
- `make_pak.py` 报告：`mesh_normals.unmatched = 0`、`uv_err_over_limit = 0`；`mesh_positions.moves_matched` 与上一版一致；文件数 79。
- `abp_springs.py` 报告：新增节点数、检查过的 pose 链接数（t31：101 个新节点、2 479 个链接），每个节点的骨、长度、刚度、限制、平面。
  只改参数时与上一版逐节点比较，确认只有目标组变了（t31：22 个节点）。
- `blink_amp.py`：断言眼睑骨组件空间静止位置不变；打印闭眼时每根眼睑骨的位移和期望值。
- `mouth_rig.py`：每个口型的目标唇缝 / 新唇缝 / 旧唇缝、平均与最大误差、非目标区域的最大位移、左右不对称；`--render` 联系表。
- 改权重的版本要比较新旧权重：变化的顶点只应涉及 `face_*`、`Head`、`Neck*`、`spine4`、`lowerPalette_jnt`、`tongue*`。

## 2. 实机闸门

1. 不存档，只读档。游戏和编辑器都关着时装 pak（校验 SHA-256）。
2. 进游戏：标题 → 「繼續」→ 待机。看整体（贴图、比例、待机动画）。
3. 物理：从背后跑步连拍（裙摆、狐尾、双马尾）；蹲下；停步后几秒内是否稳定。
4. 面部：镜头转到正面连拍 30 张左右（眨眼、待机时的嘴）；照片模式「臉部表情」逐个看（眨眼、闭眼、愤怒、开心……）。
5. 口型：需要台词。用户在实际对话里看；agent 不去触发剧情（可能自动存档）。
6. 收尾：「離開並回到桌面」退出；清理远端的截图帧；关掉自己打开的窗口（编辑器、SteamVR）。

## 3. 发行包

```text
Karin_Original_Deacon_t31/
  ~mods/zz_Karin_P.pak
  安装说明.txt          （安装、卸载、冲突、已知问题、SHA-256）
  preview_gameplay.png
```

安装说明要写：把 `~mods` 放进 `BendGame\Content\Paks`；把 `BendGame\Content\sfpaks\startuppackages.pak` 改名为
`disabled_startuppackages.pak`；不要和其它替换迪肯的 mod 同装；本 mod 不改存档；已知问题。

## 4. 证据分层与未测场景

| 项目 | 证据级 |
| --- | --- |
| 外观、贴图、待机 / 转身（t5） | `runtime-confirmed`（agent 截图；用户之后各轮反馈都基于这个外观） |
| 表情（照片模式「臉部表情」，t10） | `runtime-confirmed`（用户） |
| 物理：耳朵、侧发、双马尾、狐尾、裙摆（t27）、头发幅度（t31） | `runtime-confirmed`（用户） |
| 眨眼（t29） | `runtime-confirmed`（agent 连拍 + 用户） |
| 对话口型（t30） | `runtime-confirmed`（用户） |
| 照片模式双马尾拉伸 | `runtime-rejected`（已知问题，未修） |

未测或未逐项检查：66 个 look 里除默认装以外的服装与闪回头部、过场动画、骑车、战斗的全部动作、潜行 / 攀爬、
Remastered 分支、多显示器 / 高分辨率下的加载。
