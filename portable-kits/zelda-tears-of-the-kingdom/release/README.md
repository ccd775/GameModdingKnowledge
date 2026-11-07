# 王国之泪 · Karin_Original 角色替换 mod 包

把 **Armor_1061 火焰套装**（头饰 / 服 / 裤子；1062–1064 升级档共用同一模型）替换成 Karin，带头发、狐耳、裙摆物理、表情和眨眼。

## 两个版本

| 版本 | 内容 |
|---|---|
| **Full** | `00_Karin_Original` + `01_Kalin_Base` + `02_Visuals_UltraCam` + UltraCam 设置。与作者本机的完整环境一致。 |
| **Lite** | `00_Karin_Original` + `02_Visuals_UltraCam` + UltraCam 设置。只换这套装备，其他保持原版。 |

- `00_Karin_Original`：本 mod。替换 Armor_1061 系列的模型、贴图、头盔 pack、背包图标，并带合并后的 RESTBL。
- `01_Kalin_Base`：Kalin 基础包。多套防具改成 Kalin 造型，女性化动作，Link 本体模型，日语语音、中文文本等。
- `02_Visuals_UltraCam`：UltraCam 画面 / 镜头 mod（exefs + 环境色板）。`sdmc/UltraCam` 是它的设置文件。

## 要求

- 王国之泪 **1.2.0**（RESTBL 是 `Product.120`，UltraCam 的 exefs 也按 1.2.0 安装）。
- yuzu 系模拟器（yuzu / suyu / sudachi / citron / eden / torzu）。
  - Ryujinx 需手动安装：把 `load\0100F2C0115B6000\` 下的文件夹复制到 `%APPDATA%\Ryujinx\mods\contents\0100f2c0115b6000\`，把 `sdmc\UltraCam` 复制到 `%APPDATA%\Ryujinx\sdcard\UltraCam`。
  - 存档工具只支持 yuzu 系的存档目录。

## 安装

1. 退出模拟器。
2. 双击 `install.bat`。
   - 自动查找 `%APPDATA%\yuzu` 等数据目录。便携版 yuzu（`user` 文件夹在 exe 旁边）会提示输入 `user` 目录路径，也可以带参数运行：`install.bat -UserDir "<yuzu 目录>\user"`。
   - mod 复制到 `user\load\0100F2C0115B6000\`，UltraCam 设置复制到 `user\sdmc\UltraCam`。
   - 已有同名 mod 或设置时，旧的先移到 `user\load\0100F2C0115B6000__backup_<时间>\`（不会被当作 mod 加载）。
3. 安装器最后会询问是否给存档添加一套 Karin 装备，见下一节。
4. 启动游戏，在背包的防具栏穿上 **火焰头饰 / 火焰服 / 火焰裤子**。

yuzu 按文件夹名排序，同一文件**排在前面的 mod 生效**。`00_` 开头保证本 mod 盖过其他改 1061 的 mod（例如旧的 `03_kalin`）。

## 存档工具：添加装备

`give_armor.bat`，安装器也会调用它。它给**最近写入的存档槽**（即「继续游戏」读的那个）的防具包加入 `Armor_1061_Head / Upper / Lower`。

- 只写空格子，已经有的装备跳过，不会覆盖已有防具。
- 同时把这几件的「已获得」标记（`IsGet.*`、`IsGetAnyway.*`）置 1。
- 修改前把整个存档槽备份到本文件夹的 `save_backup\slot_XX_<时间>\`。要恢复时，把备份里的文件复制回原来的 `slot_XX` 文件夹。
- 模拟器运行中会拒绝修改，否则游戏下次保存会覆盖。

常用参数：

| 参数 | 作用 |
|---|---|
| `-Slot 2` | 改指定的槽 |
| `-AllSlots` | 所有槽都加 |
| `-DryRun` | 只看不改 |
| `-Items Armor_1064_Head,Armor_1064_Upper,Armor_1064_Lower` | 直接给满级（★★★★）版本 |
| `-UserDir "<yuzu 目录>\user"` | 指定 user 目录 |

原理参考 TOTK-SaveGame-Editor（往防具包写 64 字节的装备名），但按存档哈希表定位防具包数组（hash `0x754E8549`，300 格），不依赖固定偏移。

## 卸载

删除 `user\load\0100F2C0115B6000\` 里对应的文件夹，或在 yuzu 游戏属性的「附加组件」里取消勾选。要恢复安装前的 mod，从 `__backup_<时间>` 文件夹移回。

## 已知限制

- 染色对 Karin 模型无效。
- 右手不显示：护甲上衣不含右手指骨，右手是 Link 的独立模型。
- 狐耳只有左右摆。
  - 没有前后摆的原因：套装 cloth 里能前后摆的骨骼支点都在后脑，跑动时摆角很大，会把耳朵拉长。
