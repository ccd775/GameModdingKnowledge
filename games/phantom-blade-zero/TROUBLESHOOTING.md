# 排障手册

| 症状 | 原因 | 处理 |
| --- | --- | --- |
| 装上 mod 后某把武器（醉剑）的模型消失、攻击没有判定 | 身体（领导者）缺原版身体的 `weapon_*_child` / `ik_weapon_*_child` 骨；醉态攻击动画驱动 `weapon_r_child` | 原版身体的骨一根不能少：构建器把缺的骨补到父骨上；读回比较骨名（[技术合同](TECHNICAL_CONTRACTS.md) §4） |
| 游戏一加载 mod 就崩 | 无版本号 cook 的包 | 用默认（带版本号）的 cook |
| 容器放进 `~mods` 没有效果 | 只有 `.utoc` / `.ucas`，没有伴随的 `.pak` | 加一个只装小文本的 `z_<名>_P.pak` |
| 原版的某个部件也被换掉 / 不见了 | 占位资产进了容器 | 容器清单只收目标资产和 `Mods/<名>/` |
| 网格不可见 | 覆盖了分层材质的第 1 层 | 只改第 0 层 |
| 整件发白 | 改了全局材质参数；或贴图不是虚拟纹理 | 第 0 层 + VT |
| 成年脸深棕、眼睛发灰，少年正常 | `RefreshMaterialParamByHead` 把头的槽 0 换成动态材质实例并设 `HealthPercentage` | 脸放槽 1，槽 0 放隐藏三角（[面部](FACE.md) §3） |
| 平时游玩不眨眼 | 平时游玩的头不跑 `Hun_CopyPose(_Head)`；游戏自己的面部数据不用 Karin 的曲线 | 脸放睫毛片上，`Hun_CopyPose` 里加门控的眨眼循环（[面部](FACE.md) §4–5） |
| 过场没有脸 | 过场角色的睫毛片带 `bInfluencedByMainHairMode`，开 groom 时被隐藏 | 两张脸：头上的脸平时缩在里面，过场由 `KarinFaceShow` 放大 |
| 斗鸡眼 | 眼睛权重给了原版的眼根骨（位置差 4–6 cm） | 眼睛区域跟头走 |
| 侧发、双马尾、裙摆被拉长 | 挂在游戏的链骨上，链骨被动画和后处理摆姿势 | 改用 Chaos 布料（[物理](PHYSICS.md) §1） |
| 下半截裙子像湿的 | 双面裙的两层焊成同一批粒子，法线抵消；加上游戏的雨水湿润 | 单面裙；湿润参数清零 |
| 刘海上有暗斑 | 闭合发束的内外层焊在一起，法线抵消 | 删内层面 |
| 裙子沿褶线闪光 | 绑定用模拟网格的平均法线重建渲染法线，窄褶上偏 60–90° | 平滑外壳做模拟网格（`sim_slot`） |
| 跑动时大腿 / 臀部穿出裙片 | 模拟把裙片往里推 | backstop + CCD；碰撞体用第 85 百分位 |
| 某段布料完全不动，日志 `CreateFromSkeletalMesh failed` | 焊接后有退化三角 | 构建器删退化三角；`ue_cloth.py` 任何一段失败都让这一步失败 |
| 绑第二个 section 到同一布料资产失败 | 每个 LOD 只能绑一个 section | 合并成一个槽、合成贴图 |
| 删旧物理资产后保存身体时在 AsyncLoading2 断言 | 旧布料还引用它 | 复用同一个物理资产 |
| 新导入的网格带着上一版的材质槽名 | 无界面运行时资产注册表还没扫完，删除被跳过，导入并进了旧网格 | `search_all_assets(True)`；导入后断言没有旧槽 |
| 读回看到 `Blinn_Hero_Hun_*` 之类的原版槽名 | 读的是原版（没设 `PBZX_EXTRA`） | `PBZX_EXTRA` 指向输出目录 |
| `.ucas` 大小和上一版一样 | 内容变了大小也可能不变 | 用哈希和读回判断 |
| UnrealPak 报 `Failed to obtain package name from file name ...Hun_New_V1/Mesh/*.uexp` | groom 占位的 `.uexp` 名与包名不对应 | 无害 |
| `ue_run` 的脚本参数丢了 / 路径错 | commandlet 的 `-script=` 吃掉 `\u`、`\U` | 正斜杠路径；整个 `-script="..."` 用一个原样参数传 |
| 嵌套 SSH 命令报「命令行太长」 | 两层 base64 EncodedCommand 超过 Windows 命令行长度 | 拆小，或先把脚本文件传过去再执行 |
