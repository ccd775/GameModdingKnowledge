# Watch Dogs Karin 默认服装替换 Mod 1.3.0 部署说明

## 适用范围

本 Mod 仅完整替换 Aiden 的默认“私法制裁者”服装，包括角色模型与贴图。其他可购买服装、换装皮肤、囚服及剧情特殊服装不在支持范围内。

## 前置条件

- PC 版《Watch Dogs》。
- 游戏 `bin` 目录内已安装 NexusTools ModManager。
- ModManager / NexusTools 版本满足 `minTntVersion: 1.1.1`。
- 安装或调整 Mod 前先退出游戏。

ModManager 位于游戏安装目录的 `bin` 子目录，路径因用户安装位置而异：

```text
<watch-dogs-install>\bin\ModManager.exe
```

正式发布包：

```text
dist/karin_replacer_v1_3_0.zip
大小：5752682 bytes
SHA256：5B2BE5A472F5AFCA0B0F42BF3BA80B89FE24481701E72C846DA00B86041701FB
```

不要解压发布 ZIP，也不要手工复制或替换 DAT/FAT 文件。

## 安装

1. 退出《Watch Dogs》。
2. 打开游戏安装目录下的 `bin/ModManager.exe`。
3. 在 ModManager 中选择安装 Mod，并选取 `dist/karin_replacer_v1_3_0.zip`。
4. 确认列表中出现 `Karin Default Outfit Replacer`，版本为 `1.3.0`。
5. 确认 Karin Mod 已启用。
6. 如果同时安装了 Living City，将 Karin Mod 移到 `Living_City` 上方。不要改变其他 Mod 的启用状态或顺序。
7. 应用 ModManager 改动后，从 ModManager 的启动入口或 Ubisoft Connect 启动游戏。
8. 进入服装界面并装备默认“私法制裁者”服装。

## 验收要点

装备默认“私法制裁者”后检查：

- Aiden 的完整几何模型已被 Karin 替换，而不只是贴图改变。
- 角色正反朝向与移动方向一致。
- 双马尾首端与绿色发带孔位基本对齐。
- 头发和尾巴颜色、光照表现正常，不再异常发灰。
- 鞋底高度正常，鞋子前部完整且没有明显陷入地面。
- 围脖在常规站立、跑动和轻微抬头时没有夸张拉伸。

已知限制：少数持枪或插兜动画中仍可能出现轻微手指变形。该限制已经用户验收并接受。

## 从旧版升级

1. 退出游戏并打开 ModManager。
2. 安装 `karin_replacer_v1_3_0.zip`。
3. 本 Mod 各版本使用同一个 `friendlyId`，应由 ModManager 替换旧版；不要让两个 Karin 版本同时存在或同时启用。
4. 再次确认 Karin 已启用，并位于 `Living_City` 上方。
5. 启动游戏并装备默认“私法制裁者”进行验收。

## 卸载

1. 退出游戏。
2. 在 ModManager 中禁用或移除 `Karin Default Outfit Replacer`。
3. 不要同时移除 Living City 或更改其他无关 Mod。
4. 应用变更后启动游戏，确认默认服装已恢复。

## 回滚到 1.2.0

若需要回滚：

1. 退出游戏。
2. 在 ModManager 中移除或替换当前 Karin 1.3.0。
3. 安装 `dist/karin_replacer_v1_2_0.zip`。
4. 确认只启用一个 Karin 版本，并仍位于 `Living_City` 上方。
5. 启动游戏，装备默认“私法制裁者”并检查角色。

## 常见故障

### 只有贴图被替换，仍是 Aiden 的几何模型

- 确认安装的是 1.3.0 正式 ZIP，而不是旧包。
- 确认 Karin Mod 已启用并位于 `Living_City` 上方。
- 在 ModManager 中重新安装正式 ZIP，然后重新启动游戏。
- 确认当前装备确实是默认“私法制裁者”。

### 角色仍显示 Aiden

- 检查当前服装是否为默认“私法制裁者”。其他服装和剧情特殊服装不属于本 Mod 的替换范围。
- 检查 Karin Mod 是否启用，以及是否被其他角色替换 Mod 覆盖。

### 头发或尾巴像旧版一样发灰

- 通常表示旧版资源仍在生效。用 ModManager 重新安装 1.3.0 正式 ZIP。
- 确保没有同时启用旧版 Karin Mod。
- 保持 Karin 位于 `Living_City` 上方后重新启动游戏。

### 剧情服装没有替换

这是预期行为。本 Mod 仅支持默认“私法制裁者”，不支持囚服或其他剧情特殊服装。

### 安装后游戏无法启动

1. 退出游戏和 ModManager。
2. 重新打开 ModManager，暂时禁用 Karin Mod 后测试游戏。
3. 如果游戏恢复启动，重新安装 1.3.0 正式 ZIP，并保持推荐顺序。
4. 若仍有问题，回滚到 `dist/karin_replacer_v1_2_0.zip`。
5. 不要为排查本 Mod 而批量禁用、删除或重排其他无关 Mod。

## 完整性校验

在发布包所在目录打开 PowerShell：

```powershell
$package = Get-Item -LiteralPath '.\dist\karin_replacer_v1_3_0.zip'
$package.Length
(Get-FileHash -LiteralPath $package.FullName -Algorithm SHA256).Hash
```

预期输出：

```text
5752682
5B2BE5A472F5AFCA0B0F42BF3BA80B89FE24481701E72C846DA00B86041701FB
```

如果大小或 SHA256 不一致，不要安装该文件；应重新取得正式发布包。
