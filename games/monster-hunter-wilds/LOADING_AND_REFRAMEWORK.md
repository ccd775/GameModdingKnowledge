# 加载与 REFramework

## 1. 开机机理：缺贴图 = 标题前永久黑屏，不是崩溃

`case-derived`，但对本作装备替换普遍适用：

- 启动流程：厂商 logo → （离线时）「无法连接至服务器 R1152-AAA-AAA2」对话框 → 标题
  场景（帐篷里 Alma、艾露猫和玩家自己的猎人）。
- 标题场景**要等玩家装备构建完成才淡入**。只要装备 MDF 引用的某张贴图拿不到（不存在，
  或加载器拿不到散装贴图），装备构建就永久挂起：画面一直黑，但**游戏循环还在跑**
  （REFramework 的每帧回调持续触发，日志持续打印 `Windows message hook is still intact`）。
- 因此「黑屏不崩溃」首先怀疑贴图可达性，而不是 Mesh/骨架/物理。Mesh、MDF、chain2、
  clsp、fbxskel 等散装文件在旧 REFramework 下也都能正常加载。
- 那个服务器对话框与 mod 无关（只装 BoneSystem 也出现），按确认键（F）关闭即可。

## 2. REFramework 版本门槛（build-sensitive）

同一个游戏 exe `1.42.0.2`（2026-08-15）上的实测：

| REFramework | 散装 `.tex` | 未加密 mod PAK | 结论 |
| --- | --- | --- | --- |
| `v1.5.9.1+103`（nightly 01212，commit `7db3502b`，2026-01 构建） | **装备构建挂起 → 黑屏**；连原版字节原样放回原版路径也黑 | **被忽略**（画面与未安装逐像素同亮度） | 任何自定义贴图都无法加载；旧 Karin mod 同样黑屏 |
| `v1.5.9.1+507`（nightly 01424，commit `d1461375`） | 正常加载 | 未测 | 散装贴图方案可用；r5–r6 全部在此版本上通过 |

日志分诊线索：

```text
# 旧版：PAK 绕过未安装
[IntegrityCheckBypass]: Restoring unencrypted paks...
[IntegrityCheckBypass]: Could not find sha3_rsa_code_start!
# 新版：散装贴图加载器生效
[LooseTextureLoader]: Hooked wcsstr call at 0x... for DStorage .tex bypass
[LooseTextureLoader]: Found DirectStorage file open function at 0x...
```

新版 DLL 里能搜到字符串 `LooseTextureLoader` 与 `pak_mods`；旧版没有。判断用户环境
时，先看 `re2_framework_log.txt` 开头的 `Commit hash` / `Commits past tag`。

上游线索（`reference-inferred`，2026-09-30 从 REFramework GitHub 检索，未逐条复现）：

- 早有 issue 报告散装贴图会让游戏进不了主菜单；之后加入了感知 DirectStorage 的
  `LooseTextureLoader`，默认开启。
- 后续版本支持游戏根目录 `pak_mods/` 文件夹（任意文件名的 PAK），并有直接加载其中
  PAK 的改动；本例没有用到。
- 有报告称 nightly 01424 在本 build 上运行正常，但开启 FSR3 帧生成时启动可能失败；
  本例用户开着帧生成，未遇到。

`invariant` 规则：

- **每次游戏 exe 更新都要重新确认 REFramework 能力。** 本例旧 Karin mod 在
  1.042.00.00 修复后可用，exe 更新到 `1.42.0.2` 后在旧 REFramework 下同样黑屏 ——
  症状与「新 mod 有错」一模一样。
- 随包 README 写明所需的 REFramework 版本下限，以及「旧版会在标题前黑屏」。

## 3. 推荐加载路线

- **散装文件**：`natives/STM/...` + `reframework/data/BoneSystem/*.json`，用 Fluffy Mod
  Manager 的 ZIP 安装。贴图放 `natives/STM/streaming/<dir>/`，MDF 写 `streaming/<dir>/...`。
- PAK 路线仅作备用。未加密、无压缩的 KPKA 4.0 写法（已按参考 mod 的贴图 PAK 布局与
  哈希核对）：头 `KPKA` + `<BBhII`（4, 0, 0, 条目数, 0）；每条目 48 字节 `<QQQQQQ`
  （`lower | upper << 32`、偏移、压缩大小、原始大小、属性 0、校验 0）；数据紧跟目录。
  Fluffy 把 PAK mod 安装成下一个 sub 补丁号
  `re_chunk_000.pak.sub_000.pak.patch_NNN.pak`。旧 REFramework 会忽略它（见上表）。

## 4. Fluffy Mod Manager 协作

- ZIP 内有一个顶层 mod 目录，含 `modinfo.ini`（`name`、`version`、`description`、
  `author`、`category`、`NameAsBundle`、`screenshot`）、预览图、README 与 payload。
- Fluffy 在它自己的游戏配置目录里用 `installed.ini` 逐文件记录每个已启用 mod，并在
  游戏根目录放 `ModdedByFluffyModManager.txt`。
- 测试时手工改过游戏目录，就要么按 `installed.ini` 逐文件哈希还原，要么明确告诉用户
  「当前目录与 Fluffy 记录不一致，切换版本时先在 Fluffy 里停用旧版再启用新版」。
- 同一装备只能启用一个替换 mod（本例与旧 Karin mod 都替换 `ch03_060_000`）。
