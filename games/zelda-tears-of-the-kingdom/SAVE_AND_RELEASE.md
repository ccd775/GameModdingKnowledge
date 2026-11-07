# 存档与发行

## 1. 发行包

`assemble_package.py` 生成两个版本（v7c）。文件数和大小是本案的值：

| 版本 | 内容 | 文件数 | ZIP |
| --- | --- | --- | --- |
| Full | `00_Karin_Original` + `01_Kalin_Base` + `02_Visuals_UltraCam` + `sdmc/UltraCam` 设置 | 1933 | 约 100 MB |
| Lite | `00_Karin_Original` + `02_Visuals_UltraCam` + `sdmc/UltraCam` 设置 | 41 | 约 9.8 MB |

- `01_Kalin_Base` 和 `02_Visuals_UltraCam` 是用户自己装的 mod，不在本库里：
  - `01_Kalin_Base`：多套防具的 Kalin 造型、女性化动作、Link 本体模型、日语语音等；
  - `02_Visuals_UltraCam`：exefs 画面 / 镜头 mod。
- `03_kalin` 不打包，因为它的 1061 文件全部被 `00_` 覆盖。
- 包里的 `install.bat` / `give_armor.bat` 只是用 `chcp 65001` 和 `powershell -ExecutionPolicy Bypass` 调用 `tools\*.ps1`。
- **要求**：游戏 1.2.0（RESTBL 是 `Product.120`，UltraCam 的 exefs 也按 1.2.0 装）、yuzu 系模拟器。
  - Ryujinx 要手动复制到 `mods\contents\0100f2c0115b6000\` 和 `sdcard\UltraCam`。
  - 存档工具只认 yuzu 系的存档目录。

## 2. 安装器（`Install.ps1`）

1. 模拟器（yuzu / suyu / sudachi / citron / eden / torzu）在运行时拒绝安装。
2. 自动找 `%APPDATA%\<模拟器>\`，以有 `nand` 为准。便携版 yuzu 的 `user` 文件夹在 exe 旁边，这时提示输入路径，或用 `-UserDir` 传入。
3. 复制 `load\0100F2C0115B6000\*`。同名的旧 mod 先移到 `load\0100F2C0115B6000__backup_<时间>\`：它和 title 文件夹同级，不会被当作 mod 加载。
4. 复制 `sdmc\UltraCam`，旧的设置备份为 `sdmc_UltraCam`。
5. 列出该游戏的其他 mod。排序在 `00_Karin_Original` 前面的单独警告，因为它们改了 1061 或 RESTBL 时会盖过本 mod。
6. 询问是否运行存档工具（`-NoSave` 跳过，`-Yes` 不问）。

## 3. `progress.sav` 的结构

位置：`nand\user\save\0000000000000000\<用户 ID>\0100F2C0115B6000\slot_XX\progress.sav`。没有校验和，改完直接生效。

**文件布局**（`build-sensitive`）：

| 位置 | 内容 |
| --- | --- |
| 0x00 | magic `0x01020304` |
| 0x08 | u32，哈希表的结束偏移 |
| 0x20 起 | 哈希表：8 字节一项，(u32 哈希, u32 值) |

**哈希表**
- 哈希为 0 的项是类型段的标记，值 = 类型号。
- Bool 类型（0）：值直接存在表项里。
- String64Array 类型（17）：值是数据区的偏移，那里是 u32 个数 + 每项 64 字节的 UTF-8 字符串。

**防具包**：String64Array，哈希 `0x754E8549`，300 格，每格一个装备名，例如 `Armor_1061_Head`。

**获得标记**：`IsGet.<装备>`、`IsGetAnyway.<装备>`，都是 Bool。哈希 = MurmurHash3 x86_32（seed 0）作用于标记名的 UTF-8。

## 4. 存档工具（`Give-KarinArmor.ps1`）

- **默认对象**：给最近写入的存档槽（「继续游戏」读的那个）的防具包加 `Armor_1061_Head / Upper / Lower`。
  - `-Items` 可以换成其他装备，例如满级的 `Armor_1064_*`。
  - `-Slot N` / `-AllSlots` 选槽，`-DryRun` 只报告。
- **防具包定位**：按哈希表找。找不到这个哈希时，退回到「个数 ≥ 100、非空项全是 `Armor_*` 的 String64Array」。
- **写入规则**：只写空格子；已经有的装备跳过。
- **获得标记**：把存在的 `IsGet` / `IsGetAnyway` 标记置 1，与正常拾取一致。
- **备份**：修改前把整个槽文件夹复制到 `save_backup\slot_XX_<时间>\`。
- **运行限制**：模拟器（含 Ryujinx）运行时拒绝修改，否则游戏下次保存会覆盖。
- **PowerShell 5.1 的坑**：大于 0x7FFFFFFF 的十六进制字面量会变成负的 int32，所以 Murmur3 的常量写成 `[uint64]` 十进制再取掩码。
- **文件编码**：脚本要存成带 BOM 的 UTF-8，否则 5.1 读中文会乱码。

**与「修改器」的区别**
- 用户手里的 `塞尔达传说-王国之泪修改器V1.1.2 汉化版.exe` 其实是 .NET 的 TOTK-SaveGame-Editor 汉化版（反编译确认）。
  - 它也往防具包写 64 字节的装备名，但固定写偏移 400376 处的前 5 格，适用于 1.1.0 大小（2,307,656 字节）的存档。
  - 这样会覆盖玩家已有的防具，也不置获得标记。
- 用户的 slot_00 里已经有 1061 三件，`IsGet` 为 0，应是之前用这个编辑器加的。

**核对**
- 项目里：在用户存档的副本上，用 PowerShell 5.1 和 7 各跑一次。只有目标格子和标记的字节变化。
- 模拟的 user 目录端到端测试：
  - 旧 mod 和设置被移到备份；
  - 只改最新的槽，旧槽不动；
  - 槽的备份在包里。
- 本库：合成存档的测试见 `tests/test_portable_tools.py` 的 `ZeldaTotkTools`，覆盖按哈希、按内容回退、DryRun、二次运行不改、坏文件拒绝。
- 游戏里读档后看到装备：没有单独实机测试，因为用户的存档本来就有这套。
