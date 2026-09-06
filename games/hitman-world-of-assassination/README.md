# Hitman: World of Assassination

## 项目结果

目标是把 `karin_D7-E4-04` 替换为 Agent 47 的默认 Signature Suit。使用 Simple Mod Framework 生成并部署 RPKG；参考 Mod 提到的 Package Definition Patcher/XTEA 不需要额外安装，因为 SMF 已经承担 packagedefinition patching。

2026-07-22 的 0.1.0 候选在 Dartmoor 实机运行约 95 分钟，第三人称站立、前后移动、蹲伏、拔枪和瞄准均通过，游戏正常退出且没有新增 dump/WER。54/54 自定义资源和 16/16 单元测试通过。

## 可复用流程

1. 审计参考 Mod 的资源身份、RPKG 分区和依赖，不从文件名猜资源用途。
2. 在 Blender 中先锁定对象、骨架、材质、UV、形态键和贴图 provenance；导出前烘焙确定的外观状态。
3. 按目标角色的消费路径生成资源，保留 SMF 的安装/回滚边界；不要直接改原始游戏档案。
4. 进行文件级资源一致性、包解压回读和最小单元测试，再进入一个明确关卡的实机验收。
5. 验收报告写清地图、服装、动作、运行时长和未覆盖矩阵。0.1.0 仍有长发无二级物理、瞄准时遮挡左侧视野，以及翻越/ragdoll/跨地图 LOD 未覆盖的限制。

## 案例结论

- 参考 Mod 的前置说明不等于当前安装缺失；先确认实际加载框架是否已经完成同一职责。
- “能进入游戏”只证明加载路径；模型比例、透明边缘、动作和视野遮挡必须单独记录。
- 没有目标游戏安装或对应资源时，只能发布格式研究和源模型审计，不能宣称完成替换。

## 证据来源

- [工具链与脚本职责](TOOLCHAIN.md)
- 本工作区原始项目：`Mods/Hitman3/docs/`、`Mods/Hitman3/dist/`、`Mods/Hitman3/work/runtime-validation/`。
- 关联会话：`private-session (not distributed)`。

原始项目路径、模型和发布包不随本仓库分发。
