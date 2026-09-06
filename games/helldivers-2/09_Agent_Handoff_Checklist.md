# 长线 Mod 任务 Agent 交接清单

> 目标：让下一位 Agent 能从证据继续工作，而不是重新研究或误用历史失败候选。

## 每轮结束前必须更新

- `SOP.md` 顶部当前状态。
- 当前接受 authoring、visible triplet、final triplet、ZIP 的路径/大小/SHA-256。
- 当前工具与脚本版本/hash。
- 每逻辑角色的 complete carrier、编译次数、clone target 和 bind signature；若不使用 clone，写明 target-native profile 兼容证据。
- 每条活动 seam 的自然 final-lineage 权重误差、post edit 清单与理由；肩部是否明确无 blanket override/人工过渡圈。
- 专项差分姿态的 moving/excluded bones、实际 coverage、seam gap 与邻接 edge ratio。
- 用户指定参考的精确目录、authoring Blend、compiled triplet、原始角色身份和哈希；列出明确禁用的旧参考 lineage。
- 源 Blend 保存中的非零 shape-key map，以及候选是否已在分件/retarget 前烘焙。
- 本轮用户反馈截图路径/hash。
- 当前允许变化域和冻结域。
- 部署模式：新槽或精确 lineage 替换；后者附 live 旧三件套哈希与禁止共存门禁。
- 本轮正式接受报告及被拒绝报告。
- 若用户手动验收，记录精确候选/package、用户原话、接受范围，以及未观察部署/未提供矩阵/未自动化测试等限制。
- 未执行事项：部署、启动、运行时验证等。
- 可复现命令，使用绝对或项目根相对路径。

## 交接摘要模板

```markdown
## Current objective

## User-observed issue
- Screenshot:
- Screenshot SHA-256:
- Deployed triplet/index, if known:

## Last runtime-accepted baseline
- Artifact:
- SHA-256:
- What the user confirmed:

## Current candidate
- Authoring Blend:
- Visible triplet:
- Final triplet:
- ZIP:

## Allowed changes

## Frozen domains

## Accepted gates
- Authoring:
- Pose:
- Shoulder/limb signed axis, mirror, closure and partition:
- Natural seam weights before edits / per-seam post edits:
- Targeted pose moving/excluded bones and coverage:
- Saved shape-key bake:
- Suppression and equipment-slot ownership:
- Compiled postflight:
- Shader UV/sampler reachability:
- Material/integration:
- Reproducibility:
- Runtime:

## Rejected/superseded candidates

## Exact next action

## Authorization state
- May edit source model:
- May deploy to game data:
- May launch Steam/game:
```

## 接手时的第一组动作

1. 读公共知识库 `README`、`QUICKSTART` 和相关专题。
2. 完整读项目 `SOP.md` 当前状态、最新版本段和恢复命令。
3. 验证摘要中所有关键哈希，而非相信路径名。
4. 检查 `Output/` 是否只含当前接受包。
5. 检查是否有用户或其他 Agent 新改动；工作区可脏，不回滚未知改动。
6. 检查 Blender/AQ/游戏进程状态，避免并发或未授权启动。
7. 在写入前生成新候选路径；不覆盖现有产物。

## 并行 Agent 的边界

适合并行：

- 只读审计不同证据域。
- 分析姿态 outliers、材质像素和 namespace 碰撞。
- 撰写不冲突的独立报告。
- 对同一只读输入运行纯 Python 分析。

不适合并行：

- 两个 AQ archive merge/material rewrite/roundtrip。
- 两个 Agent 编辑同一 `.blend` 或同一报告路径。
- 一个 Agent 改模型、另一个 Agent 同时以旧哈希编译。
- 任何并行写 game `data`。

分派任务时明确输入只读、允许输出目录、禁止保存 `.blend`、是否可以使用 AQ，以及返回的哈希/指标。

## 状态汇报规范

向用户汇报时先说结果，再说证据：

- 修了什么，冻结了什么。
- 具体通过哪些门禁和关键指标。
- 成品路径和 SHA-256。
- 是否部署、是否启动游戏。
- 仍需用户验证的内容。

不要把“候选生成”“离线通过”“已经部署”“游戏内通过”写成同一句模糊的“已完成”。

## 遇到冲突时

- 文件变化来自用户或其他 Agent，默认保留并理解，不回滚。
- 若当前输入哈希不符，停止写入并重新建立 provenance。
- 若旧 SOP 与实际文件冲突，以只读哈希和用户最新指令为准，同时修正文档。
- 若部署授权不清楚，继续完成离线工作，但不写游戏目录。
- 若运行时截图与全部报告冲突，候选判为 runtime rejected，并补充门禁缺口。

## 任务关闭条件

只有同时满足用户请求范围内的全部条件才可关闭：

- 正式候选、最终 triplet、ZIP 和报告存在且哈希绑定。
- 所有必需离线门禁通过。
- 拒绝候选已隔离。
- SOP 与公共知识（若产生新通用结论）已更新。
- 用户要求的部署/运行时验证已执行，或明确记录为未授权/不要求。
- 没有仍运行的必要工具进程或待收集的 Agent 结果。
