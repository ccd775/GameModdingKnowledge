# 验证、版本和交接

## 证据分级

- E0：计划/假设。
- E1：文件结构和数字检查。
- E2：Blender、FBX、UModel或Cook回读检查。
- E3：实机出现指定外观/动作，已知安装版本。
- E4：用户在已说明范围接受该版本。

这些是记录类别，不是自动评分。E2不可代替E3；E4也不可扩张为所有场景通过。所有pass值必须来自实际运行的检查或明确用户反馈。

## 每版最低检查

| 范围 | 检查 |
| --- | --- |
| 源身份 | source/hash不变，角色和skin明确 |
| 几何 | 顶点/loop/topology、被修改集合、未修改集合一致 |
| 骨架 | native顺序/parents/raw local transforms，root scale |
| 权重 | 正值、归一化、真实影响槽数、左右及有效骨索引 |
| 比例 | 头身、肩肘、髋膝、鞋底、发尾长度；不能只看包围盒 |
| 骨盆/裤子 | 源/目标髋中点及Hips距离、共同映射残差、裤口间隙、屈髋/屈膝；见RETARGET_CHECKS |
| 服装 | 袖口不跟手指，sock与skin相容，shoe不被toe折弯 |
| 长衣/布料helper | helper父链与实际语义、下摆局部边长、几何场和目标权重场一致、弯腰/抬臂；不能只看静态pose |
| 手部与上衣 | 各指段方向/掌面/roll，静止与屈指轮廓；同源索引上衣跨度；腰封/附件共同根 |
| 导出 | 0/30/60/90屈膝及其它相关pose往返，geometry/UV/weights |
| 材质 | 实际槽数、import hash、sampler UV、纹理format/sRGB/alpha |
| Cook | 实际读取D尺寸和内容，不止editor属性；错误和marker检查 |
| 版本身份 | candidate FBX hash=UE导入报告input hash；本轮Content/Cooked时间与hash；应变化的body/container不得意外复用旧hash |
| 包 | retoc verify、目录/依赖/store、raw chunk diff |
| 可见性 | 原生head/hair/cloth/gore分别检查 |
| 武器保留 | Gear/Prop实际用途，握持和渲染资源，误隐藏撤销的chunk/path/store及原生可用性 |
| 安装 | 退出MK12、备份完整trio、安装hash和启动时间 |
| 实机 | 默认调色板、加载完成、自定义斗士、必要动作/切换 |

每个新角色追加实机测试：普通战斗、左右朝向、蹲伏、跳跃、踢腿、被击、近/远LOD、换装备/调色板、相关终结技/断肢。若未测，写untested；不可复制其它角色的通过状态。

## 冻结成功候选

Riptide 最终分别冻结 Ermac v7、Noob v6、Ashrah v5，见 [案例](cases/RIPTIDE_TRIO.md)。用户先后确认脚鞋、Noob 正常与 Ermac 去发光结果。本轮总结须再次读取三个目标实际安装哈希，另写接受清单；历史 `installed.json` 中的 pending 保留为当时状态。既不要求兄弟角色统一版本号，也不把可见效果扩张成全动画/断肢认证。

Karin Y v9于2026-09-14获“可以了”确认，记录E4为用户实际查看的三角色当前效果；最终60姿势及容器回读仍属于E2，不覆盖未明确测试的战斗/LOD/断肢。历史机器报告中的untested保留，另写用户验收清单并重新读取实际安装hash。这样既不把已接受版本误判为仍待测，也不伪造全场景验收。见 [案例](cases/KARIN_Y_TRIO.md)。

Output保存三个文件及SHA-256；可编辑Blend/FBX、Atlas、脚本版本及机器报告保留在工程。公共playbook只存原创文档/小工具，不附用户模型、提取的游戏asset或未经许可的第三方Mod。

项目manifest应能定位source、native inputs、工具版本/hash、build脚本、实际Output和运行证据。不把含密码的完整会话、Steam账户信息或用户配置全量dump纳入归档。游戏manifest只摘buildid，不复制LastOwner等无关字段。

## 本案例最终范围

E4：Nyako Normal替换Sindel，默认调色板颜色正确、native hair已隐藏、鞋底高度、比例和最后一版腿部效果由用户接受。E2：原生221骨transform、单材质8192、FBX姿势回读和最终包几何检查。未经完整覆盖：所有fatality、physics/长发碰撞、online、其它皮肤、全部脚踝旋转动作。

### 三角色验收补充

2026-09-12 新增 E4：PicodraTech Karin → Tanya / Li Mei 的 pelvis-flat-v9，以及 Mileena 的 head-hide-v10（保持 v9 身体不变）。用户在本次安装后表示“我看过了，感觉都可以了”。范围为其实际查看的角色外观，包括此前报告的体型/裤子/踮脚/原版头部问题；不推定完成全部动作、装备、LOD、嘴部特殊状态或断肢测试。版本身份见 [案例哈希](cases/PICODRATECH_TRIO.md)。

### 尾部验收补充

2026-09-13 尾部后续 E4：Kitana tail-v2 获“kitana的正常了”确认；Tanya/LiMei/Mileena tail-v11安装后获“看起来可以了”确认。新版取代此前v9/v10尾巴状态，不覆盖历史验收记录。只接受实际查看的外观，不扩大为独立尾巴物理、全部动画或断肢通过。规则见 [附属物源形恢复](APPENDAGES.md)。

### UnendingFlame验收补充

2026-09-13 UnendingFlame V6用户表示赛克特发饰未隐藏、“其他的看起来都可以了”。Kenshi/Cyrax当前可见效果接受；Sektor身体/比例/贴图接受，发饰尾项另修V7。V7新增包的结构和回读验证不代表已在游戏确认。具体版本见 [UnendingFlame案例](cases/UNENDINGFLAME_TRIO.md)。

### Karin Chrome双角色验收补充

2026-09-14 新增E4：Karin Chrome → Reiko / Liu Kang Candidate-v6b。用户先确认v4解决材质变暗但手部和大衣仍异常；v6b安装后表示“已经正常了”。接受范围为其当前查看的材质亮度、手部轮廓和大衣下摆，不推定完整逐指动作、所有动画、衣物物理、LOD、断肢或联网。首次`Candidate-v6`因未重导入UE资产而Cook旧几何，已废弃且未部署；版本哈希与边界见 [案例](cases/KARIN_CHROME_REIKO_LIUKANG.md)。

### 指南自身验证

新增数学算子后运行 `python -B scripts/test_retarget_math.py`，防止轴向缩放泄漏到横截面、末端缺省尺度、共同骨盆场折叠与小图集页纵向摆放回归。测试不读取游戏或源模型，仍需实际项目的几何测量和回读。

运行 `python -B scripts/test_tools.py`、`python -B scripts/test_psk_index_plan.py`，再运行仓库 `tools/check_repository.py`检查链接、JSON、语法与公开边界。脚本合成测试不代表新的游戏运行验收。角色专属历史脚本只能在案例约束/源哈希内视为已验证；拷贝到新角色后的修改必须重新测试。
