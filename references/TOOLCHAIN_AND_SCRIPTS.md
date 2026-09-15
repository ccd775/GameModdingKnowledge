# 工具链与脚本路线

实际提供的脚本以 [便携包](../portable-kits/README.md) 的命令为准。[PROVENANCE.json](../portable-kits/PROVENANCE.json) 记录原项目迁移文件及 MK1 参数化工具的原始与公开版 SHA-256，包含修改标记。

| 游戏 | 工具职责与参数 |
| --- | --- |
| Mortal Kombat 1 | [便携命令](../portable-kits/mortal-kombat-1/README.md) |
| Hitman WOA | [便携命令](../portable-kits/hitman-world-of-assassination/README.md) |
| Watch Dogs | [便携命令](../portable-kits/watch-dogs/README.md) |
| Black Flag Resynced | [便携命令](../portable-kits/assassins-creed-black-flag/README.md) |
| RE4R | [便携命令](../portable-kits/resident-evil-4-remake/README.md) |
| L4D2 | [便携命令](../portable-kits/left-4-dead-2/README.md) |
| HD2 | [便携命令](../portable-kits/helldivers-2/README.md) |

各游戏原知识中的脚本职责表仍有大量角色专属实现；没有对应 portable-kits 脚本的名称是历史设计参考，不能假设文件已在交接包内。新项目需要按当前资源实现对应步骤，不要尝试调用不存在的旧路径。

[工具获取](TOOL_SOURCES.md) 说明外部编译器/插件和固定版本的方法。[公共运行层](../portable-kits/common/README.md) 负责项目记录、哈希、预检和装包；它不把单个阶段成功晋级成完整 Mod 实机通过。
