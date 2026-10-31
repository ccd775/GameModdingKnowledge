# 验证与发布

## 1. 离线闸门（每次构建）

| 检查 | 位置 | 通过条件 |
| --- | --- | --- |
| 导入成功数 | `make_mod_ds2.ps1` | 每个网格 `success!` 的次数等于图元数；每张贴图至少替换一级 mip |
| stream-only 核心 | `make_mod_ds2.ps1` | 31123 / 12706 / 6744 的工具核心与 `.core.pristine` 逐字节相同（`stream-only <gid>: core unchanged, left out`） |
| 核心补丁 | `make.log` 的 `### patch <gid>` | 50108、50110 的 `variable bindings renamed`（35 + 15 个 effect）；字段补丁写进 67699 |
| 链接表 | `relink.py` | 每条重指都找到唯一一条记录，否则中止 |
| 打包 | `pack.log` | `core redirects` / `stream redirects` 的数量与上一版的差别能解释（v34：10 / 174；v34f：12 / 187） |
| 读回 | `verify_pack.py <out> <gid> <网格...>` | 经打包后的流图和包读回对象，解码网格位置：塌缩的网格图元 0 是一个点，Karin 的槽是她的包围盒 |
| 预览 | `preview.py` | 正 / 侧 / 背三视图，贴图页和权重分区一眼可查 |

`verify_pack.py` 只按顶点流的步长推进解码位置，第二个及以后的图元会错位（原版也一样）；要比较整个网格时直接比 stream 字节。

## 2. 实机测试

- 存档目录：`%USERPROFILE%\Documents\DEATH STRANDING 2 - ON THE BEACH\<ID>\`（文档文件夹可能被重定向到别的盘）；手动存档名 `manualsave<N>.dat`。
- 本项目用过两份存档：新开局（Porter 外观，开场）和一份第 17 章、46 小时的长存档（原来是 Suit 外观，带大量腐蚀和泥）。长存档是检查外观表、腐蚀、物理状态的关键。
- 每个版本列清要看的项（外观、物理、表情、装备、天气、淋浴），让用户逐项回报。用户通常自己进游戏测；需要 agent 自测时，先确认桌面锁和前台，按键用扫描码按住约 120 ms。
- 天气、存档状态、场景都会改变观感：同一个问题回报两次结果不同，先对齐场景。

## 3. 开发安装

`install.ps1 -Name <名>`：首次运行把游戏的流图、`package.18.00.core.stream`、链接表备份到 `%DS2_MODDING%\backup`，然后换成输出目录里的文件；`-Restore` 还原。只在游戏关闭时运行；写文件前先删除再复制（干净根目录里的硬链接保留原版数据）。

缺点：覆盖了文件序号 0x80 对应的拉美葡语语言包，整份流图和链接表是本机版本的。所以不用它发行。

## 发行包

### 结构

```
Karin_DS2\
  安装-无表情版.bat / 安装-有表情版.bat / 卸载.bat   （调 install.ps1；仓库不收 .bat，内容见便携包 README）
  install.ps1        （Windows PowerShell 5.1 即可，UTF-8 带 BOM）
  README.txt
  NoExpression\karin.core.stream + manifest.json   （240 MB）
  Expression\karin.core.stream + manifest.json     （267 MB）
```

`make_release.py <out> <变体目录> <标题>` 生成一个变体：

- 比较原版与打包后的流图，断言只有 SpanTable / LocatorTable 变了，每个变了的 span / locator 只属于一个组；
- 比较原版与 mod 的链接表，把改动的字节段归到它所在组的链接区间；
- 每个被改的组记下：
  - 重定向：span 序号 + 新偏移 / 长度（和原长度），locator 序号 + 新偏移；
  - 链接改动：相对组 `LinkStart` 的偏移 + 旧 / 新字节；
  - **原版指纹**：NumObjects、GroupSize、SubGroupCount、SpanCount、TypeCount、LinkSize、LocatorCount，类型哈希序列的 SHA-1，子组号列表，组链接字节的 SHA-1；
- 包文件原样复制成 `karin.core.stream`，记 SHA-256。

v34：无表情 16 组 / 10 个 span / 174 个 locator / 107 处链接改动；有表情 19 组 / 12 / 187 / 107。

### 安装器 `install.ps1`

1. 找游戏：参数 `-GameDir`，或安装器所在目录的上级，或 Steam（注册表 `SteamPath` → `libraryfolders.vdf` → `appmanifest_3280350.acf` 的 `installdir`），都没有就让用户粘贴路径。
2. 游戏在运行就退出；已装过就先卸载。
3. 解析用户自己的流图（布局见 [技术合同](TECHNICAL_CONTRACTS.md#3-流图-streaming_graphcore)），用 Files[0] 自检字符串校验算法（CRC32C）。
4. **逐组核对指纹**，再核对每处链接改动的旧字节、每个被换 span 的原长度。任何一项不同就列出组号和不同的项、退出，**不写任何文件**。
5. 在内存里改：span 指向新文件序号（= 原文件数），locator 的 `Data` = 偏移 << 24 | 新序号，写链接改动；在 Files 末尾追加 `cache:package/package.99.00.core.stream`，PackFileOffsets 追加 `[]`，PackFileLengths 追加 `[4]`，更新三个数组的个数和对象大小（保留对象后的 4 个零字节）。
6. 原文件备份到 `<游戏>\KarinMod_backup`（`state.json` 记安装前后的 SHA-256）；复制包；流图和链接表都写临时文件、删原文件、改名。
7. 卸载：当前流图和链接表仍是安装后的哈希才还原；否则（游戏更新或验证过）只删 mod 文件和备份。

要点：

- 不再覆盖任何语言包；Steam 更新或“验证文件”会还原流图，mod 自然失效，追加的包文件只是一个没人引用的文件。
- 发行包里没有任何游戏版本的流图或链接表；只要被改的组在用户的版本里和 1.0.48.0 相同，就能装。
- **限制**：组号变了（流图重排）或这些组的内容变了，安装器会拒绝；那时要用那个版本的文件重新做 mod。手头没有 Steam 版的文件，没验证过 Steam 版是否兼容。

### 测试（2026-10-31，KLN55MI，Windows PowerShell 5.1）

- 假游戏目录（原版流图和链接表的副本）：安装 6 秒；流图多 59 字节。
- 用 `ds2py` 读安装后的流图：Files 242 个、新条目的 CRC 正确；span / locator 与打包版一致（只有文件序号 0x80 → 241）；Groups、类型、子组和原版相同；链接表与打包版逐字节相同。
- 被改的组逐对象与打包版相同：无表情 15 个组、有表情 18 个组（31123 只比较了网格）。比较时把 locator 的文件序号归一。
- 卸载后流图和链接表与原版哈希相同；重复安装会先卸载；两个版本互相切换正常。
- 把 50108 的一个链接字节改掉后安装：报“组 50108：links”不兼容，退出码 1，没有写任何文件。
- 真实游戏（1.0.48.0）：先用开发安装器还原原版（`package.18.00` 恢复成 573 893 812 字节），再用发行安装器装无表情版，兼容性检查通过 16 个组。
- **未确认（截至 2026-10-31 提交时）**：游戏是否能读取追加的第 242 个文件（发行安装器装的版本还没有实机）；Steam 版的兼容性。
