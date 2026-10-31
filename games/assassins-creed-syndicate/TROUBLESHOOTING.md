# 排障手册

大革命的条目（Logo 处闪退、裙子穿模、harness 路径解析……）见大革命的排障手册（完整仓库里的 `games/assassins-creed-unity/TROUBLESHOOTING.md`）；这里只列枭雄项目遇到的。

## 1. 模型与加载

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| 某些场景（菜单、藏身处、某段任务、一战记忆）里还是原版双胞胎或装备 | 那里加载的是另一份内嵌副本 | 重新扫描副本（表 + 头部 LOD），确认那个数据文件在 `twin_*.tsv` 里、每个 forge 的行都被替换 |
| 莉迪亚·弗莱也变成了 Karin | 她的头部表用伊薇的头部 LODSelector | 预期行为；不想要就得给她单独的 LOD，项目没做 |
| 过场里还是原版双胞胎 | 预渲染 Bink 视频（`videos\*.bk2`） | 改不了 |
| 拟合脚本找不到 `Hips` / `Head` | 探针 GLB 的骨是数字 ID | 先过 `glb_names.py` |
| 伊薇的下颌 / 眼球骨对不上 | 工具的别名（`JAW`、`EYE_LEFT`）的 CRC32 不是骨 ID | 以节点 `extras.Name` 为准，`glb_names.py` 已处理 |
| 膝盖皮肤从过膝袜里穿出 | `kisekae_Knee` 不移动顶点 | `fit_karin.py --hide-band body_2:0.20:0.46:0.15`（[构建流水线](BUILD_PIPELINE.md) §3） |
| 百褶裙褶边有污渍状暗影 | 源模型的卡通自定义法线 | `export_karin_lods.py --split-normals skirt:40`；修后剩下的轻微痕迹在绑定姿势渲染里不出现，判断为运行时光照（褶的自阴影、AO、头发阴影）或蒙皮，不是法线 |

## 2. 物理

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| 两只耳朵静止时朝同一侧歪 | `LocalOwnGravity` 的重力不在骨自己的坐标系里 | 改回 GlobalGravity rest-on-edge，耳朵加 `upright` 偏移 |
| 双马尾一直快速高频抖动 | 相邻链节都挂 BallJoint（v2、v4） | 只模拟 0 / 2 / 4 节 |
| 双马尾走两步就整根甩起来、没有链感 | 每节锥角一样大且摩擦小（v3 18°） | 逐节分级：根节小锥大摩擦，往梢递增 / 递减 |
| 耳朵 / 双马尾硬、一动就到限位 | rest-on-edge 加大摩擦（v1，5–10 倍于原版头发） | 降摩擦、加锥角，按上一行分级 |

## 3. 工具链

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| `build_mod.py` 跑了十几分钟没有任何输出 | stdout 在管道里块缓冲 | 等末行 `BUILD_OK`；看 `ACS_SCRATCH\build_tmp` 里的作业目录判断进度 |
| 解包慢十几倍 | 中间产物在同步盘里 | `ACS_SCRATCH` 指向本地目录 |
| 远程（SSH）里 Blender 的 Workbench 渲染崩溃（访问冲突） | 会话里没有 OpenGL | 改用 Cycles（CPU）渲染检查图 |
| 要提取原版副本，但 mod 装着 | 索引行指向追加的数据 | 用构建缓存 `ACS_SCRATCH\vanilla`，或先卸载；`make_release.py` 经状态文件读原位置 |
| 安装器说没有写权限 | 游戏在 Program Files 下 | 右键 `.cmd` → 以管理员身份运行；拒绝时什么都没改 |
| 安装器列出「differ from the vanilla ones」 | 那份副本和制作时的原版内容不同（别的版本或别的 mod） | 照样替换了；若游戏异常，卸载后在那个版本上重新构建 |
