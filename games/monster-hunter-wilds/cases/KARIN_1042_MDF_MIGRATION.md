# 案例：1.042 更新后的装备 MDF 合同迁移

> 范围：修复一个第三方 Karin 角色替换 mod（替换 `ch03_060_000` 的 1–6 号部位，贴图在
> 自带 PAK 中）在游戏 1.042.00.00（2026-08-04/05，`patch_015`）更新后的材质问题。
> 状态：修复件部署后作为后续项目的可用参考；exe 在 2026-08-15 再次更新后的可用性
> 受 REFramework 版本影响，见 [加载](../LOADING_AND_REFRAMEWORK.md)。

## 症状

更新后自定义角色整体变黑，只剩少量自发光细节可见。

## 根因（binary comparison，`runtime-confirmed` 于当时 build）

对比 `patch_014` 与 `patch_015` 中的全部原版装备 MDF（扩展名仍为 `.mdf2.45`）：

- 每个装备材质的 MMTR 从 `Base_Equip.mmtr` 变为 `Base_Equip_NoMultiBlend.mmtr`；
- 删除了两个 MultiBlend 贴图槽（`MultiBlend_ALBDMap`、`MultiBlend_NRMMap`）和一个
  MultiBlend GPBF（`MultiBlend_BAB`）；
- 删除旧 MultiBlend 属性，新增 4 个属性，并按新模板重排属性顺序与填充；
- 结果是每个受影响材质比旧版小 946 字节。

贴图没有变化：mod 的贴图 PAK 含 MDF 引用的全部 13 张自定义贴图，版本仍为
`.tex.241106027`，`patch_015` 也没有替换相关原版贴图条目。

## 修复方法（invariant）

- **不要只改 MMTR 字符串。** 贴图槽、属性、GPBF、填充与顺序是同一个合同，一起变。
- 以当前 build 的原版 MDF 为模板逐个重建材质：保留同名贴图槽的自定义路径、同名属性
  的取值、材质名、标志位与材质顺序；被删除的 MultiBlend 槽原本只指向引擎空贴图、相关
  混合开关也都关闭，迁移不损失任何有效效果。
- 所有输出经同一解析器往返；其中两个部位的输出与当前原版合同文件逐字节相同。
- 部署前备份已安装的 MDF，部署后比对 SHA-256。

## 可迁移的经验

- 游戏更新后外观异常时，先抽「更新前后两层」的同一批原版文件做二进制对比，定位是
  MDF 模式变化、MMTR/shader 合同变化、TEX 版本/路径变化，还是加载路线问题。
- 论坛上的说法只作线索；以本机归档提取和二进制对比为准。
