# Resident Evil 4 (2023) Remake

## 范围

这里整理 RE4R 角色替换的通用合同和九个 Karin 案例：Ashley、Luis、Merchant、Ada、Krauser、Leon 等。完整专题文档保存在本目录，案例中的路径、hash、骨数和 Chain 参数只对注明的游戏 build 有效。

## 核心方法

- 先建立当前 build 的 consumer matrix 和 immutable input lock，再做 Blender 或二进制修改。
- 按 consumer slot 分区几何，建立完整 parent closure、归一化 bounded weights 和逐行 source-to-target bone map。
- 把 Mesh、MDF、submesh material index 以及查询这些索引的 gameplay component 视为一个合同；MDF-only lookup 通过不等于结构闭包。
- 分开审计 source UV intent、导出后的 UV stream、材质采样、透明度、emission 和 normal。
- Chain topology、rest frame、terminal、参数和碰撞分开改变；一个分支的运行时拒绝不等于整个角色绑定失败。
- PFB/RSZ/JCNS 修改必须来自当前 build，要求语义字段差分、序列化回读、确定性构建和候选绑定的运行时报告。
- 高跟鞋、脚骨方向、鞋底平面和地面接触是不同命题，不能用一个角度或最低点代替全部证明。

## 证据纪律

本库定义 `reference-inferred`、`offline-accepted`、`runtime-load-pass`、`runtime-rejected` 和 `runtime-confirmed` 五类证据。运行时拒绝要停止候选晋级，但保留已被独立证明的离线子合同；新 build、工具或 schema 出现时重新提取和验证。

## 阅读入口

- [详细索引](DETAILS_INDEX.md)
- [角色替换 SOP](CHARACTER_REPLACEMENT_SOP.md)
- [技术合同](TECHNICAL_CONTRACTS.md)
- [排障手册](TROUBLESHOOTING.md)
- [验证与发布](VALIDATION_AND_RELEASE.md)
- [案例目录](cases/)
- [项目记录模板](templates/PROJECT_RECORDS.md)

## 公开边界

本目录只包含文档和轻量模板，不包含模型、纹理、参考 Mod、游戏 PAK 或发布包。案例文档保留失败和证据边界，便于复现思路而不是复制私有资源。

