# 工具来源与环境准备

此表是本案用过的版本/来源，不是当前可下载性或最新版声明。换机器或游戏更新后先确认作者说明与hash。实际本机路径和exe SHA-256只保存在私人案例manifest。

| 工具 | 本案版本/职责 | 作者入口 |
| --- | --- | --- |
| Blender | 4.5.12 LTS；源模型求值、重绑、FBX和姿势检查 | [Blender](https://www.blender.org/download/) |
| MK1定制Unreal Editor | 4.27-MK1-release；实际项目Cook | [授权仓库release](https://github.com/kboykboy2/UnrealEngine/releases/tag/4.27-MK1-release) |
| retoc | 0.1.5；IoStore提取、转换、验证 | [作者release](https://github.com/trumank/retoc/releases/tag/v0.1.5) |
| ACL UModel | 本机umodel_acl_2.1；`-game=mk12 -nomorph` | [作者论坛资料](https://www.gildor.org/smf/index.php?topic=8718.0) |
| FModel | August2026本机版本；资源浏览辅助 | [作者releases](https://github.com/4sval/FModel/releases) |
| PSK/PSA导入 | 本机有Blender4.x兼容修改，迁移要保留diff | [插件来源](https://github.com/matyalatte/blender3d_import_psk_psa) |
| MK12TTH | 本机使用v0.5.0；前置加载支持 | [作者release](https://github.com/thethiny/MK12TTH/releases/tag/v0.5.0) |

Epic/GitHub访问入口：[Unreal on GitHub](https://www.unrealengine.com/ue-on-github)。需要关联和接受组织邀请的情况由用户在正常登录网页中完成。仓库404可能是授权不可见，不应直接判断仓库不存在；不要让用户在会话里给密码。

HeadRemover/Dismember Hider使用本机已保存、用户已授权的包和随包说明，记录title/作者/版本/hash。此指南不复制未经重新核验的Nexus数字ID，也不把不同角色hider视作通用文件。

## 配置时保存的证据

- exe版本/hash、源下载链接、私有release授权情况（只记是否获准，不记token）。
- 定制UE项目一份小型导入/Cook smoke测试及日志。
- retoc当前版本help输出与原生样本header比较。
- Blender源文件打开无丢图；PSK插件骨架导入后名前缀、单位和bone collection兼容性。
- 进程/磁盘/显存检查；保存失败或内存不足时不拿旧输出当新结果。

不要把仅在本机成功的工具版本升级推断为所有模型兼容。确定新工具chain后以一个小型已知模型做回读回归，再批量制作。
