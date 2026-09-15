# MK1 接续入口

先读STATUS.md的当前证据：T1000 v8材质后续复发，不能以历史接受停止调查；Umbrella v8其它可见效果接受，但柯南v9武器候选尚未安装。文中本机工程相对路径是未公开证据名称，只有本仓库真实提供的脚本可作为可运行入口。

Riptide 三角色于2026-09-14获当前可见效果接受：Ermac v7、Noob v6、Ashrah v5，见cases/RIPTIDE_TRIO.md。Ermac实际MI带_Emissive后缀，Noob原生标量3→0，Ermac需新增标量0；跨角色Ashrah路线未通过。先读NATIVE_MATERIAL_PATCHING.md，不重绑已接受脚鞋。源high heel脚型与整鞋底朝向分别检查，手机灰屏先查源Glass_Hidden。实际版本与本机验收清单优先于历史pending，不扩大到全动作/断肢。

Karin Y→Rain/Smoke/Scorpion v9于2026-09-14获用户可见效果接受，见cases/KARIN_Y_TRIO.md。手部须检查掌面/各指段方向；收头颈后量同源顶点的腰封→上衣→领口距离；相关挂件共用所属表面锚点，见UPPER_BODY_HANDS.md。Gear并非必然服装：Rain的Gear001_A/B/C实际是手杖，不能默认隐藏。已接受角色的遗留离线untested字段不覆盖后续用户验收，另记反馈清单。

Karin Chrome→Reiko/Liu Kang Candidate-v6b于2026-09-14获用户当前可见效果接受，见cases/KARIN_CHROME_REIKO_LIUKANG.md。Normal误作ART/CSM会变暗；布料helper最近祖先不等于目标动画驱动，应让衣物几何场与目标权重场一致；刚性手掌是有界回退，不用于默认逐指绑定。几何改版先重导入UE并核对input FBX、UAsset与Cook身份；Candidate-v6因复用旧资产已废弃。

长脖子跨会话复发的检查与最小修复见 [NECK_PROPORTIONS.md](NECK_PROPORTIONS.md)。初次适配及肩宽变化后都检查可见颈长；骨架兼容不等于源头颈比例正确。已认可肩宽冻结，只对完整头组平移与颈部过渡做局部实验，不照搬Wasakura的45%跨度/约5cm。纯函数与合成回归在scripts/neck_fit.py、test_neck_fit.py。

先读 README.md，再按问题选择 PLAYBOOK.md、RIGGING.md、PACKAGING.md 或 TROUBLESHOOTING.md。当前项目状态应位于该项目自己的 PROJECT_STATE.md，不从历史日志最后一段猜测。

新源/新骨架绑定需读 RETARGET_CHECKS.md，并把实际尺度矩阵、共同骨盆/服装映射和鞋部结果写入报告。不能将“已读指南”代替执行检查：XYZ段长缩放、Head隐式1倍、Hips与UpperLeg独立映射遮住裤子已在多个任务复发。只做附件尾项时按变更范围复用接受基线，不重建身体。基础算子及故障回归在scripts/retarget_math.py、test_retarget_math.py。

本目录是操作指导，不是要求无条件运行所有步骤的状态机。用户授权和当前任务范围优先。未经请求不发布、不上传模型或游戏资源，不改其他角色包。离线成功与实机验收分开记录。

Sindel 的 221 骨、原生 chunk ID、索引偏移、材质路径以及脚部过渡阈值是案例值，不是 MK1 通用常量。新的目标角色须重新提取和测量。不要直接执行本机案例快照中的硬编码脚本。

脚本在 scripts/，先看 scripts/README.md。新脚本默认只读或写入新文件；部署脚本默认预检，-Install 才写游戏目录。二进制补丁需要源哈希和已审核范围。禁止以跳过断言、写 accepted=true 或降低失败阈值代替修复。

三角色案例见 cases/PICODRATECH_TRIO.md：骨盆/短裤/大腿根共同映射，平底鞋左右归属用实际腿部权重，轴向骨长与径向体型分开。原版 face/mask/skin cloth 单独盘点；多 export 原生脸部必须保留原生 store，不套单 export normalize。psk_index_plan.py 只认完整索引流，未证明全部 LOD。Mileena v10、Tanya/LiMei v9 于 2026-09-12 获用户当前可见效果验收，不是全动画/断肢认证。

尾部后续见 APPENDAGES.md：Kitana tail-v2和三角色tail-v11于2026-09-13获用户当前可见效果接受，取代旧尾部版本。骨骼归属不决定静止几何应套哪种形变场；审查完整独立连通块、锚点与非修改集合，保留源尾形，不直接复用别的目标骨架/offset。仍未添加独立尾巴物理。
