# 西之绝境便携包

先读 [游戏知识](../../games/horizon-forbidden-west/README.md) 和 [构建流程](../../games/horizon-forbidden-west/BUILD_PIPELINE.md)。

这是 Karin_Original 替换贝塔项目实际使用的脚本。

- **Python 版本：** 需要 Python 3.12 或更高，因为钉住的 numpy 2.5 和 scipy 1.18 不支持更早的版本。
- **外部工具：** 导入那一步要用 id-daemon 的 `h2_pc_mi_091.exe` 和 DirectXTex 的 `texconv.exe`，两者都由用户自己获取。
- **运行位置：** 以下命令都从交接包根目录执行。

```powershell
python -m pip install -r requirements.txt -r portable-kits/horizon-forbidden-west/requirements.txt
$Kit = "portable-kits/horizon-forbidden-west/scripts"
$Tool = "<干净根>\LocalCacheWinGame"      # 内有 h2_pc_mi_091.exe、02_19A7C73A.core.pristine 和导出的骨架

# 0. 用 h2 工具导出原版（在 $Tool 中运行）：b2c4 LOD0 放进 Export，LOD1-7 分别放进 Lods\lod1 … lod7；面部骨架也放进 Export
#    h2_pc_mi_091.exe b2c4 0   …   h2_pc_mi_091.exe b2c4 7   以及   h2_pc_mi_091.exe 719 0

# 1. 拟合、权重、拼页，写出 ascii
python -B $Kit/build_hfw.py --vrm ../MyMod/Ref/model.vrm --export ../MyMod/Ref/Export --lods ../MyMod/Ref/Lods --work ../MyMod/Work --hide collapse --max-lod 7

# 2. 离线检查：5 个姿势的 OBJ
python -B $Kit/pose_preview.py ../MyMod/Work ../MyMod/Ref/Export ../MyMod/Work/poses

# 3. 转贴图，导入 25 个网格和 12 张贴图，收集 33 个 mod 文件
python -B $Kit/make_mod.py ../MyMod/Work $Tool "<DirectXTex 目录>\texconv.exe" ../MyMod/Output/mod

# 4. 就地修改 core：放大包围盒，把 CsNbtGen 改为 VsNbt
python -B $Kit/patch_bounds.py ../MyMod/Output/mod/02_19A7C73A.core ../MyMod/Work
```

最后把 `Output/mod` 下的文件、`modinfo.json` 和 `preview.png` 平放进 zip，拖进 HFW Mod Manager。做法见 [验证与发布](../../games/horizon-forbidden-west/VALIDATION_AND_RELEASE.md#发布)。

## 脚本

| 脚本 | 职责 |
| --- | --- |
| `build_hfw.py` | 入口。依次完成：VRM 读入，遮挡剔除，TPS 拟合与着地，按身体分区继承权重，两张 2048 颜色页和一张光泽页，上下身切分，面部骨架重映射，隐藏子网格；写出 `ascii/lod*_*.ascii`、`jobs.json`、`fit_report.json` |
| `fit_hfw.py` | VRM 人形骨到 Beta 骨架的对应表，以及 TPS 拟合；由对马岛便携包的 `fit.py` 改写 |
| `atlas.py` | 按 UV 岛拼页；在对马岛版本上增加了按栅格化足迹合并（`mask_merge`） |
| `vrm.py` | VRM 1.0 / 0.x 读取；与对马岛便携包中的同名文件逐字节相同 |
| `hfwascii.py` | h2 工具 ascii 网格和骨架的读写 |
| `make_mod.py` | 用 texconv 生成 DDS，从 `.pristine` 恢复 core，按 `jobs.json` 调用 h2 工具导入网格和贴图，核对成功数，收集 core 和 stream |
| `patch_bounds.py` | 原地修改 core：放大 4 个 LocalBounds，把 6 个 CsNbtGen SkinInfo 改成 VsNbt；查找不唯一或类型不符时拒绝修改 |
| `pose_preview.py` | 用写出的 ascii 对 5 个测试姿势做线性蒙皮，输出 OBJ |
| `gamekey.py` | 实机测试用：把游戏窗口切到前台，用扫描码按住发送按键（仅限 Windows，需要 pywinauto） |

## 输入与输出

- **h2 导出**：
  - `--export` 目录：`b2c4` LOD0 的全部 `b2c4_*.ascii`、`b2c4_skel_24.ascii` 和 `719_skel_0.ascii`；
  - `--lods` 目录：`lod1` 到 `lod7` 七个子目录，各放该 LOD 的导出。
  - 这些都是游戏资源，不随包提供。
- **源 VRM**（`--vrm`）：模型不随包提供。
- **工具目录**（`make_mod.py` 的第二个参数）：
  - 用专用目录，最好放在 [干净根目录](../../games/horizon-forbidden-west/FORMATS_AND_TOOLS.md#干净根目录) 里。教程是直接在游戏的 `LocalCacheWinGame` 里运行工具，本项目没有这样用；
  - 每次运行都会删掉其中的 `*.stream`、`lod*.ascii` 和 `new_*.ascii`，再从 `02_19A7C73A.core.pristine` 恢复 core。
- **texconv**：DirectXTex，MIT 许可。本项目用的是 2024.6.5.1 版，SHA-256 `9450ba6c…`。
- **输出**：
  - `--work` 目录：`ascii/`、`jobs.json`、`page_A.png`、`page_B.png`、`gloss_A.png`、`gloss_B.png`、`fit_report.json`，以及 `make_mod.py` 生成的 `dds/` 和 `make_log.json`；
  - mod 输出目录：33 个文件。
  - **`fit_report.json` 里有本机绝对路径**（VRM、导出目录和工作目录），分享前要删掉或改掉。

## 案例常量

`build_hfw.py` 顶部的常量是 Karin_Original 专用的，不是通用配置：

- 遮挡规则 `COVER_RULES` 和 `COVERED_BODY`；
- 脸页网格 `FACE_PAGE_MESHES`；
- 上下身强制归属 `UPPER_MESHES` / `LOWER_MESHES`；
- 光泽 `GLOSS`；
- 丢弃的材质 `Karin_Alpha`；
- 拼页用的 4 个材质名。

换模型时，这些常量要按新模型的网格名和材质名重写。

以下是 build `14835813` 的 Beta 布局（`build-sensitive`），游戏更新后要重新核对：

- `build_hfw.py` 里的槽位：`BODY_UPPER`、`BODY_LOWER`、`LOD_FACE_FILES`、`FACE719`；
- `make_mod.py` 里的贴图编号；
- `patch_bounds.py` 里的原版包围盒和 SkinInfo 计数。

可调参数：

- `--scale`（默认 1.3）、`--head-scale`、`--neck-drop`；
- `--shoulder-fit`（默认 0.3）、`--arm-drop`（默认 2 cm）；
- `--src-max`、`--hide`、`--max-lod`。

`--stage` 和 `--z-split` 是早期的参数，现在已经不起作用。

## 已验证与边界

- **可复现。** 满足以下条件时，用本包脚本重建 v4，mod 文件与实机测试过的版本**逐字节相同**：
  - 同一 build、同一 VRM、同一组 h2 导出；
  - texconv 2024.6.5.1 和 h2_pc_mi_091 0.9.1；
  - Python 3.14.0、numpy 2.5.2、scipy 1.18.0、Pillow 12.2.0。

  结果：30 个构建输出相同，33 个 mod 文件相同。详见 [验证记录](../VALIDATION.md)。
- **便携改动。** `make_mod.py`、`patch_bounds.py`、`pose_preview.py`、`gamekey.py` 改用 argparse，并加了 `--help`。`make_mod.py` 还会在缺少输入文件时直接报错。处理逻辑没有变；改动后重跑了一遍，结果仍然逐字节相同。
- **只做一件事。** 这套脚本只处理 Beta（b2c4），不是安装器，不改游戏目录，也不处理 mod 之间的冲突。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。其中 5 项西之绝境合成测试不需要游戏或模型：
  - ascii 读写往返；
  - 包围盒和 SkinInfo 补丁，以及它在类型不符时拒绝修改；
  - 权重量化和射线锥遮挡判定；
  - 拼页时掩码合并与包围盒合并的区别；
  - 姿势 FK 的转轴不动。

  没装本包的额外依赖时，这些测试会跳过，并提示安装命令。
- **署名。**
  - `fit_hfw.py`、`atlas.py`、`vrm.py` 沿用本库对马岛构建器的代码；
  - ascii 格式和导入导出命令来自 id-daemon 的工具及其教程，见 [工具来源](../../references/TOOL_SOURCES.md)。
