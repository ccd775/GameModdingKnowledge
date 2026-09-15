# 公开快照与证据边界

整理日期：2026-09-15。历史游戏基线为 Steam build 17941244；更换 build 后须重新提取原生合同。以下为维护者项目记录与用户反馈的整理，本次公开迁入只重新执行合成/便携性检查，没有重新运行游戏。

| 案例 | 当前记录 | 不可推导的结论 |
| --- | --- | --- |
| Nyako Normal → Sindel | 用户接受贴图、原发隐藏、腿部修正版 | 不代表所有动画/皮肤/断肢通过 |
| PicodraTech | Tanya/LiMei pelvis-flat-v9、Mileena head-hide-v10曾接受；最新尾部三者tail-v11及Kitana tail-v2获接受 | 尾形恢复不是新增独立物理 |
| Riptide | Ermac v7、Noob v6、Ashrah v5当前可见效果接受 | 不跨角色统一覆盖版本/材质 |
| Karin Y | Rain/Smoke/Scorpion v9当前可见效果接受 | Rain Gear001_A/B/C是手杖；不能作为衣物隐藏 |
| Karin Chrome | Reiko/Liu Kang v6b接受；首次v6因Cook旧资产废弃 | 刚性掌面回退不是通用逐指方案 |
| UnendingFlame | Sektor/Kenshi/Cyrax v9接受肩线等可见效果 | 不按旧v8斜肩日志重修；保留接受的附属物隐藏 |
| Wasakura | 三角色v5获“脖子好了很多”反馈 | 45%跨度/约5cm不是跨角色常量 |
| 9b3d | T1000 v8曾正常，后在未切换装备/调色板、预览前18位角色后再次灰色颗粒；安装hash仍匹配v8。其它三角色v5b，腰部保持接受状态 | T1000材质稳定性尚未解决，不能把历史接受当成当前修复完成 |
| Umbrella | Homelander/Conan v8获“其他都还好，柯南的武器被意外隐藏了”；材质/身体/胯部当前可见效果接受 | Conan v9-weapon仅离线通过，安装被运行中的游戏阻止；武器恢复未实机验收 |

入口：[案例目录与流程](README.md)、[Umbrella与包依赖故障](cases/UMBRELLA_HOMELANDER_CONAN.md)、[9b3d调查](cases/9B3D_QUAD.md)。

历史文章中的“最终”“接受”“待测”必须连同上述后续反馈阅读。保存原机器报告，再追加新反馈和安装hash；不得把历史记录改成从未发生失败。

## 公开文件与本地证据

本目录包含原创文档、参数化源码、合成测试与空项目模板。原模型、游戏chunk、Cook/安装三件套、截图、私人验收JSON和角色专属硬编码脚本均不包含。文中反引号内的 `MK1/...`、`Work/...`、`SOP/...` 是原工程的证据名称，不是本仓库可下载路径，也不能据此执行命令。

公开工具入口为 [scripts/README.md](scripts/README.md)；已迁入脚本哈希见 [PROVENANCE](../../portable-kits/PROVENANCE.json)。其余本机证据说明见 [来源索引](../../SOURCE_REFERENCES.md)。二进制偏移、骨数、chunk ID、通道值和尺寸均属于各案例的观测值，需要在新输入上重测。
