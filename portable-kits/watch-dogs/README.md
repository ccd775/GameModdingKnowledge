# 看门狗便携包

先读 [游戏知识](../../games/watch-dogs/README.md) 和 [不用 ZModeler 生成 XBG](../../games/watch-dogs/XBG_WITHOUT_ZMODELER.md)。

本包附带 Karin 1.4、1.5、Karin_Original 0.1.2 实际使用的 XBG 写出器（不需要 ZModeler）、骨架修改、FAT v8 打包和不依赖 texconv 的贴图编码脚本，以及原有的 XBT 工具。

- **Python 版本**：XBT 工具和 FAT 工具只需标准库，Python 3.10+。XBG 写出器、骨架工具和 `xbt_encode.py` 需要 numpy；钉住的 numpy 2.5 需要 Python 3.12+（测试环境 Python 3.14.0）。
- **运行位置**：以下命令都从交接包根目录执行。
- **不随包提供**：游戏文件、模板 XBG、模型、ModManager 都由用户自备。

```powershell
python -m pip install -r requirements.txt -r portable-kits/watch-dogs/requirements.txt
$Kit = "portable-kits/watch-dogs/scripts"
```

## XBG：不用 ZModeler

```powershell
# 0. 从上一版运行包解出模板（char01.xbg 的条目名是 E886A8DB）
python -B $Kit/extract_fat8.py ../MyMod/Ref/old_mod.fat ../MyMod/Ref/old_mod

# 1. FBX（模型名含 LOD0 / LOD1）-> char01.xbg；写完自动回读，必须看到 READBACK PASS
python -B $Kit/build_xbg_from_fbx.py --fbx ../MyMod/Work/handoff.fbx --template-xbg ../MyMod/Ref/old_mod/E886A8DB.xbg `
  --output ../MyMod/Work/char01.xbg --report ../MyMod/Work/char01.build.json

# 2. 可选：按模型改骨架（只改位置；未列出的关节随父骨刚性移动；面部骨骼改了也无效）
python -B $Kit/xbg_skeleton_patch.py ../MyMod/Ref/old_mod/E886A8DB.xbg ../MyMod/Work/targets.json ../MyMod/Work/template_fitted.xbg
python -B $Kit/xbg_skeleton.py ../MyMod/Work/template_fitted.xbg --joint "L UpperArm"

# 3. 贴图：PNG -> donor XBT（尺寸、格式、mip 数与 donor 一致），不需要 texconv
python -B $Kit/xbt_encode.py ../MyMod/Work/coat_d.png ../MyMod/Ref/old_mod/<hash>.xbt ../MyMod/Work/<hash>.xbt

# 4. 替换条目重打 FAT/DAT（键可以是 8 位哈希或游戏路径）
python -B $Kit/repack_fat8.py ../MyMod/Ref/old_mod.fat ../MyMod/Output/my_mod.fat `
  graphics/characters/char/char01/char01.xbg=../MyMod/Work/char01.xbg
```

第 4 步的键也可以直接写哈希，例如 `E886A8DB=../MyMod/Work/char01.xbg`。游戏路径的哈希是小写反斜杠路径的 FNV-1 64 位值取低 32 位。

最后把 `my_mod.fat`、`my_mod.dat` 和 `modconfig.json` 放进 zip，用 ModManager 安装。`modconfig.json` 的写法沿用旧包，`packs` 填 FAT 文件名（不带扩展名），见 [部署与回滚](../../games/watch-dogs/DEPLOYMENT_WATCH_DOGS_KARIN.md)。换了 `friendlyId` 和 pack 名的新 mod 可以与旧版并存，但同一时间只能启用一个。

### 检查门

- `build_xbg_from_fbx.py` 输出 `READBACK PASS`：写出后重新解码，所有量化值与意图逐值相等。
- 调色板长度与模板不同时，写出器会重新计算矩阵表前的补零。用 `xbg_skeleton.py` 确认 `bind @ inv_bind` 的残差没有变大。模板自带约 0.04 的残差，来自原版面部和外套物理骨。
- 面数核对：每个 LOD 的面数应等于 FBX 三角化后的面数（报告 JSON 的 `faces`）。
- 实机：读档、外观、基础动作。

`targets.json` 的格式是 `{"关节名": [x, y, z]}`，坐标为 XBG 模型空间（米）：左为 −X，前为 +Y，上为 +Z。

## XBT：原有工具

```powershell
python -B $Kit/xbt_tool.py inspect ../MyMod/Ref/low.xbt
python -B $Kit/xbt_tool.py extract ../MyMod/Ref/low.xbt ../MyMod/Work/low.dds
python -B $Kit/xbt_tool.py inject ../MyMod/Ref/low.xbt ../MyMod/Work/replacement.dds ../MyMod/Work/new.xbt
python -B $Kit/audit_xbt_templates.py ../MyMod/Ref/textures ../MyMod/Work/xbt-audit
python -B $Kit/build_xbt_pair.py ../MyMod/Ref/source.png ../MyMod/Ref/low.xbt ../MyMod/Ref/low_high.xbt ../MyMod/Work/pair --texconv $Texconv --expected-texconv-sha256 $TexconvSHA256
```

注入保留 donor header，拒绝 DDS 尺寸、mip、格式不一致的输入，也拒绝覆盖已有输出；`--force` 只用于格式实验。pair builder 限定 XBT 123 + legacy DXT1/DXT5，low 为完整 mip，high 为单 mip。模板审计只在同一目录内配对，不递归猜测。

## 脚本

| 脚本 | 职责 |
| --- | --- |
| `build_xbg_from_fbx.py` | 入口：FBX 两个 LOD -> char01.xbg，写后逐值回读，拒绝覆盖已有输出 |
| `xbg_model.py` | XBG 结构读取（材质表、调色板、节点表、LOD 描述符、GPU 缓冲区） |
| `xbg_codec.py` | 顶点编解码与整文件写出；以模板保留材质表、骨架、矩阵表和物理块，并重新计算矩阵表的 16 字节对齐 |
| `fbx_reader.py`、`fbx_mesh.py` | 纯 Python 二进制 FBX 7.x 读取，按角点展开网格、UV、颜色、材质和蒙皮 |
| `fbx_to_xbg.py` | ZModeler 约定的转换：坐标 `(−x, −y, z)`、绕序反转、v 翻转、前 4 个权重量化、按材质名匹配模板槽位 |
| `xbg_skeleton.py` | 读取绑定姿势和逆绑定矩阵，做姿势和线性蒙皮；命令行检查残差 |
| `xbg_skeleton_patch.py` | 移动关节并同步更新节点局部平移与逆绑定矩阵；写后验证，失败时删除输出 |
| `xbt_encode.py` | PNG -> donor XBT，Pillow 逐级 DXT1/DXT5 编码，保留 donor 文件头 |
| `extract_fat8.py`、`repack_fat8.py` | 未压缩 FAT v8 / DAT 解包与重打包；条目 16 字节对齐，键可用游戏路径 |
| `xbt_tool.py`、`audit_xbt_templates.py`、`build_xbt_pair.py` | 原有 XBT 解析、注入、模板审计和 texconv 配对构建 |

## 限制

- 只支持 char01 骨架和模板里的材质槽。每个顶点最多 4 个权重，每个子网格最多 65,535 个顶点，调色板最多 255 根骨骼；超出时直接报错，不会静默拆分。
- 从 VRM 直接构建（Karin_Original）的脚本没有收录：它与该模型的材质名、部件名绑定。做法见游戏文档。
- 输出与 ZModeler 语义一致，但不逐字节一致。
- 测试只用合成数据：`python -B tests/test_portable_tools.py`。
