# 与 The Fall of Windy City II 兼容：私有头部材质

**证据等级：** 2026-10-10 在一台 PC 实机测试，NexusTools 1.1.13，The Fall of Windy City II 1.1.2（Nexus mod 552）排在 Karin 上方。

| 场景 | 结果 |
|---|---|
| WC2 + 修复前的 Karin_Original | 脸呈深褐色，复现了用户的报告 |
| WC2 + Karin_Original 1.0.1-test（本修复） | 脸正常（肤色、红眼） |
| 不装 Windy City + Karin_Original 1.0.1-test | 脸正常 |

蓝白 Karin 1.6.1-test 用同一处理。从发布包生成，除头部外逐字节不变。

## 原因

WC2 的 `tfowc2` 包覆盖了 Aiden 的头部材质 `graphics\_materials\mkamelaquino-m-20130115113413.material.bin`：

- 漫反射从 `char01_head_v2_d2.xbt` 改指 `char01_head_v2_d.xbt`；
- 高光从 `char01_head_v2_s2.xbt` 改指 `char01_head_v2_s_lowend.xbt`；
- 另外还改了几个材质参数。

替换 mod 只覆盖 `_d2/_n/_s2`。装了 WC2 后，Karin 的脸会按自己的 UV 去采样 Aiden 原版的 `_d`，所以发黑。

就算 mod 也覆盖 `_d` 和 `s_lowend`，WC2 排在上方时它自带的 `s_lowend` 照样胜出。NexusTools 1.1.13 的 `packs` 条件只有 `compatibleGameModes` 和 `compatibleVersions`，做不了"装了某个 mod 才启用"的补丁包。

WC2 还替换了全局着色器，并改了外套材质的参数，但贴图路径不变。它没有碰 `graphickit_models.lib`，所以不影响剧情模型的重定向。

## 修复（`private_head.py`，对已构建的包做后处理）

1. `char01.xbg` 头部槽的材质路径换成同长度的私有路径 `graphics\_materials\droylouo-m-20261010120000-h1a.material.bin`，并更新它的 FNV（XBG 只差 30 字节）。
2. 私有材质是原版头部材质的副本，三个贴图路径改成同长度的私有路径：
   - `karin_face_drl_d2.xbt`
   - `karin_face_drl_n.xbt`
   - `karin_face_drl_s2.xbt`

   它们都在 `graphics\characters\char\char01\` 下。材质里的路径记录是"参数名哈希 + 长度 + 字符串"，同长度替换不改变布局。
3. 私有贴图是单文件，整条 mip 链都在一个文件里，与 WC2 自带贴图的格式相同：
   - 内容是高流顶层，后接低流的各级；
   - XBT 前缀用高流的，0x19 字节改成 mip 总数；
   - DDS 头用低流的，宽、高和线性大小改成顶层的值。

   XBT 里的 4 字节 ID 沿用 donor 的；WC2 新增的贴图也共用 ID，说明它不与路径绑定。
4. 包里删掉 `char01_head_v2_d2/_n/_s2` 的低流和高流（6 个条目），商店服装里 Aiden 的模块化头部因此恢复原样。
5. 新路径的 FAT 哈希与本机 44 个 filelist 里的已知路径都不冲突。

接入方式：`repack_fat8.write()` 按条目字典写 FAT/DAT，可以增删条目；`package_mod.package(..., transform=private_head.privatize)` 在换完条目后调用它。

## 范围

- 放弃与 Windy City 1 的兼容（WC2 声明与 WC1 不兼容）。
- 只验证了 WC2 1.1.2 和不装 Windy City 两种情况；其他改头部材质的 mod 没有测试。
- 私有材质用原版参数，在 WC2 的着色器下渲染正常。
