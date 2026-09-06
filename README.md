如果你觉得内容有帮助，可以前往https://ifdian.net/a/ccd775 赞助我以获得贴贴！
# Game Modding Shared Knowledge

供人和 agent 接续长线 Mod 项目的知识库与便携工具包。它包含实际项目的方法、成功与失败记录、19 个迁移脚本和公共运行工具；不需要注册 Skill。

## 从这里开始

1. 阅读 [PLAYBOOK.md](PLAYBOOK.md)，选择当前项目需要的阶段。
2. 打开相应 [便携工具说明](portable-kits/README.md)，用脚本的 --help 确认参数。
3. 创建独立项目，记录当前 build、源模型、工具和候选。暂停时保存下一步与证据。
4. 按当前游戏资源适配角色专属构建脚本；离线检查和实机验收分别记录。

| 游戏 | 知识入口 | 已验证历史范围 |
| --- | --- | --- |
| 杀手暗杀世界 | [Hitman WOA](games/hitman-world-of-assassination/README.md) | Signature Suit 0.1.0 在 Dartmoor 的基础动作 |
| 看门狗 | [Watch Dogs](games/watch-dogs/README.md) | 默认服装 v1.3.0；保留少数手指变形限制 |
| 刺客信条黑旗记忆重置 | [Black Flag Resynced](games/assassins-creed-black-flag/README.md) | 角色替换及最终 1.6.1 修复，用户于 9 月 6 日确认 |
| 生化危机4重制版 | [RE4R](games/resident-evil-4-remake/README.md) | 多个角色案例，具体场景/build 分别记录 |
| 求生之路2 | [L4D2](games/left-4-dead-2/README.md) | 多个实机确认案例，另有静态完成待复测项目 |
| 绝地潜兵2 | [HD2](games/helldivers-2/README.md) | Unit/绑定/材质多案例；splat 等分支单独验收 |

## 独立交接与验证

```powershell
python -m pip install -r requirements.txt
python -B tests/test_portable_tools.py
python -B tools/check_repository.py
python -B tools/export_kit.py --all --output ../Modding-Portable-Exports --zip
```

输出六份不依赖父仓库的目录，以及对应 ZIP/文件哈希清单。每份包含该游戏文档、脚本、公共层和安装依赖说明。[验证记录](portable-kits/VALIDATION.md) 明确哪些进行了组件测试，哪些还需要专用工具和游戏实测。

## 下载便携包

[v0.1.0 Release](https://github.com/ccd775/GameModdingKnowledge/releases/tag/v0.1.0) 提供六款游戏的独立目录 ZIP，以及对应的文件 SHA-256 清单。下载后解压整个包，从包内 README.md 开始。

| 游戏 | 独立便携 ZIP |
| --- | --- |
| 杀手暗杀世界 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.1.0/hitman-world-of-assassination.zip) |
| 看门狗 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.1.0/watch-dogs.zip) |
| 黑旗记忆重置 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.1.0/assassins-creed-black-flag.zip) |
| 生化危机4重制版 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.1.0/resident-evil-4-remake.zip) |
| 求生之路2 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.1.0/left-4-dead-2.zip) |
| 绝地潜兵2 | [下载](https://github.com/ccd775/GameModdingKnowledge/releases/download/v0.1.0/helldivers-2.zip) |

## 内容与证据

[工具来源](references/TOOL_SOURCES.md)、[迁移清单](portable-kits/PROVENANCE.json)、[能力边界](references/CAPABILITY_GAPS.md)、[项目模板](templates/)、[机器目录](CATALOG.json)。

历史项目命令可能依赖未迁移的角色脚本。540 处本地证据引用已转到 [来源索引](SOURCE_REFERENCES.md)，不会伪装成公开可下载文件。旧知识中的固定骨数、偏移、材质 ID 和阈值是案例值；新项目以当前资源测量为准。

原模型、参考 Mod、游戏资源、账号、DLL 和私人候选不随仓库发布。原创文档和脚本的使用权说明见 [NOTICE.md](NOTICE.md)。
