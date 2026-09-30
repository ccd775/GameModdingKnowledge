# 对马岛便携包

先读 [游戏知识](../../games/ghost-of-tsushima/README.md) 和 [拟合与绑定](../../games/ghost-of-tsushima/FITTING.md)。

这是两个 Karin 项目实际使用的构建器，替换的是 Jin 的「忠赖的铠甲」。需要 Python 3.12+，因为钉住的 numpy 2.5 和 scipy 1.18 不支持更早的版本。以下命令都从交接包根目录执行：

```powershell
python -m pip install -r requirements.txt -r portable-kits/ghost-of-tsushima/requirements.txt
$env:GOT_GAME_DIR = "<Steam 库>\steamapps\common\Ghost of Tsushima DIRECTOR'S CUT"

# 默认：所有贴图页用 etcpak 压缩
python -B portable-kits/ghost-of-tsushima/scripts/build_karin.py --profile original --vrm ../MyMod/Ref/model.vrm --out ../MyMod/Output/gapack_misc_h_MyMod.psarc

# 复现项目构建：颜色页改用 DirectXTex texconv 2025.10.28.1，并校验它的哈希
$Texconv = "<DirectXTex 目录>\texconv.exe"
$TexconvSHA256 = "2cb5703c8ec81a8135bfe40ef63912c172862838f5345062515c93c3744a9f46"
python -B portable-kits/ghost-of-tsushima/scripts/build_karin.py --profile original --vrm ../MyMod/Ref/model.vrm --texconv $Texconv --expected-texconv-sha256 $TexconvSHA256 --out ../MyMod/Output/gapack_misc_h_MyMod.psarc

python -B portable-kits/ghost-of-tsushima/scripts/verify.py ../MyMod/Output/gapack_misc_h_MyMod.psarc --renders ../MyMod/Work/renders
```

## 脚本

| 脚本 | 职责 |
| --- | --- |
| `build_karin.py` | 入口。依次完成：读取原版归档，VRM 拟合与着地，遮挡剔除，减面，UV 拼页，权重映射，下垂姿势反解；然后写入 xmesh / xpps / SPS，打出不压缩的 PSARC 和 `.build.json` 报告 |
| `verify.py` | 离线校验：文件集合、容量、隐藏、贴图，以及回读后的贴图渲染和四个姿势渲染 |
| `fit.py` | 人形骨骼对应表、TPS 拟合与控制点 |
| `vrm.py` | VRM 1.0 / 0.x 读取；0.x 的朝向和拇指命名在这里转成 1.0 |
| `decimate.py` | QEM 减面：锁定接缝和边界，二次型不加权 |
| `atlas.py` | 按 UV 岛拼贴图页，像素与 UV 用同一个变换 |
| `gotfmt.py` / `gotarc.py` | hero.xpps、xmesh（SMBS）、SPS（XTBS）读写；DSAR / PSARC 读取与 mod PSARC 写入 |
| `render.py` | 软件光栅渲染，供校验出图 |

## 输入与输出

- **游戏目录**（`--game` 或环境变量 `GOT_GAME_DIR`）：只读取 `cache_pc\psarc` 下的原版归档，不写游戏目录。
- **源 VRM**（`--vrm`，必填）：模型不随包提供。
- **DirectXTex `texconv.exe`**（`--texconv`，可选；MIT 许可，由用户从 DirectXTex 的发布页自行获取）：
  - 本项目用的是程序自报的 2025.10.28.1 版，SHA-256 见上面的命令；
  - 不提供时，所有贴图页改用 etcpak 压缩，输出与项目构建不同，但两个 profile 的 etcpak 构建都通过了 `verify.py`；
  - `--expected-texconv-sha256` 必须和 `--texconv` 一起用。
- **中间目录**（`--work`，默认 `%TEMP%\got_karin_original_work`）：原版文件的解包缓存和索引。
  - 游戏更新后要删掉这个目录，否则会继续用旧的原版文件；
  - 两个构建**不要并行**共用同一个 `--work`。
- **输出：**
  - `.psarc` 放进 `<游戏目录>\cache_pc\psarc\` 即可生效；
  - 旁边的 `.build.json` 记录参数、容量、减面和着地数据，**其中含源 VRM 的本机绝对路径**，分享前要删掉或改掉这一项。

## profile 与参数

- **`--profile original` / `picodra` 是案例配置，不是通用配置。** 它们包含该模型的网格名到槽位的映射、遮盖剔除规则、裙摆骨、可减面网格清单、脚与肩的参数。新模型要在 `PROFILES` 里另写一个 profile，写法照这两个来。
- **可调参数：**
  - 比例：`--scale`（默认 1.45）、`--neck-drop`、`--chest-share`、`--head-scale`；
  - 肩：`--shoulder-fit`、`--arm-drop`、`--arm-hang`（最大 120）；
  - 脚：`--foot-scale`（仅限保留原鞋形的 profile）。
- **不写的参数取 profile 值。** 各参数的作用和实机教训见 [拟合与绑定](../../games/ghost-of-tsushima/FITTING.md)。

## 已验证与边界

- **可复现：** 满足以下条件时，便携脚本重建两个 profile 的输出与项目构建**逐字节相同**：
  - 同一 build（`23879181`）、同一 VRM；
  - 上面那个 texconv；
  - Python 3.14.0、numpy 2.5.2、scipy 1.18.0、Pillow 12.2.0、etcpak 0.9.15。

  结果：Original md5 `a30f3ac1…`；PicodraTech 第四构建 md5 `bf0a6e15…`。换了库版本后，重采样和压缩的字节可能变化，重跑 `verify.py` 确认结构即可。详见 [验证记录](../VALIDATION.md)。
- **只做一件事：** 只写入忠赖的铠甲 all-ranks 网格的 8 个 LOD0 部件。偏移、部件哈希、布料开关出现次数都是 `build-sensitive`；游戏更新后，先看构建器里的断言是否仍然通过。
- **不是安装器：** 不改游戏目录，不处理多个 mod 之间的冲突。
- **测试：** `python -B tests/test_portable_tools.py` 含 6 项对马岛合成测试，不需要游戏或模型：
  - PSARC 数据原样存储且按 8192 对齐；
  - 权重和法线打包；
  - 减面时边界锁定、面朝向不翻；
  - 拼页像素与 UV 一致，缩小比例下也一致，透明标记不丢色；
  - 下垂姿势反解；
  - 缺 VRM、缺游戏目录、texconv 参数错误或哈希不符时拒绝构建。

  如果没装本包的额外依赖，这些测试会跳过，并提示安装命令。
- **署名：** 格式知识部分参考 Dave349234 的 "Ghost of Tsushima Toolkit for Blender"（MIT，要求署名），见 [工具来源](../../references/TOOL_SOURCES.md)。这里的代码是本项目编写的，格式布局参考了该工具包。
