# 制作下一个角色：端到端操作

## 0. 建立工程和验收范围

为每个“源模型×目标角色×目标皮肤”建立独立目录，不把下一个角色写入 Sindel 的工作目录。

```text
Project/
  PROJECT_STATE.md        当前唯一状态入口
  project.json           角色、路径、骨架、材质与部署约定
  source-lock.json       源模型/参考 Mod/工具/游戏 build 哈希
  Source/                不可变输入，或指向不可变输入的记录
  Native/                原生 mesh/skeleton/material/texture/cloth 提取
  Work/                  分阶段候选和局部脚本
  Reports/               实际计算的离线检查
  Runtime/               已安装哈希、动作与用户反馈
  Output/                可测试三件套，每版独立目录
  Backups/               已部署包与配置备份
```

首先记录源模型版本、目标默认皮肤、目标调色板、当前游戏 build、现有 Mod 列表。用户已经授予的本地构建/部署授权不必反复询问，但不得据此推断允许发布或覆盖别的角色。

## 1. 锁定环境，而不是重新下载一切

复用成功 Mod 的是资源合同与构建方法，不是默默把它的几何/贴图当成用户新模型。构建脚本须读取锁定的源 Blend/FBX，报告其哈希、实际网格/面数和材质来源。可以借鉴参考包中的兼容性中性纹理，但必须标明来源和用途。

本案例工具：Blender 4.5.12 LTS；MK1 定制 UE 4.27 `4.27-MK1-release`；retoc 0.1.5；ACL UModel 2.1；Python 3.12；PSK 导入插件（有 Blender 4.x 兼容调整）。FModel 可辅助查看资源。

记录实际 exe 哈希和来源。普通 Epic UE 4.27 不能当作已验证替代品。定制 UE 来源是授权访问的 `kboykboy2/UnrealEngine`，需要 Epic/GitHub 关联；不要复制账号、密码、访问令牌到脚本或报告。合法获取工具后本机复用，不把工具安装包混入角色 Mod。

对外部更新或首次获取的工具，重新查阅官方/作者当前说明；本指南记录的是本案例使用版本，不是“当前最新版”。

## 2. 先证明原版与前置能运行

保留现有能运行的 MK12TTH 和 Hide Head 配置，先测试目标默认皮肤。启动配置错误也可能导致短时崩溃，不能仅凭“装包后闪退”认定网格有错。

案例已用的前置：MK12TTH，HeadRemover V2；Kitana 另有 Dismember Hider。角色包位于 `MK12/Content/Paks`；HeadRemover 等逻辑包位于 `Paks/LogicMods`。实际路径和版本以已安装目录及随包说明为准。

Nyako 基线使用 `-fileopenlog -Kitana_1 -Sindel_1`；三角色案例后实际进程参数为 `-fileopenlog -Kitana_1 -Sindel_1 -Mileena_1 -Tanya_1 -LiMei_1`。隐藏头的 GameInstanceClass 在 [打包说明](PACKAGING.md) 中。后续角色的开关**必须查它的说明**，不要按名字拼接后当作已验证。保留原配置，仅新增必要项并可回滚。设置界面、保存文件、实际运行进程是三个检查点；参数生效仍不保证独立面罩/脸部全部隐藏。

## 3. 提取目标角色的资源合同

先锁定默认皮肤的真实 body mesh、skeleton、physics、材质、原生头/头发及 cloth companion，分别记录资产路径、包 ID、chunk ID、源哈希。

材质必须从原生身体实际引用反查，而不是默认拼接 Body001。Riptide 的 Ermac 实际带 `_Emissive` 后缀；先正确连接目标原生材质，再区分灰色回退和继承自发光。已有标量可做受哈希约束的原位修改，缺少显式覆盖需完整解析后新增；详见 [原生材质最小补丁](NATIVE_MATERIAL_PATCHING.md)。

若叶材质和图集回读正确仍灰，继续查皮肤/装备蓝图默认对象、`ObjectOverrides[Body]`、重新赋材质调用及 MaterialOverride 表；mesh 默认 MI 可能被装备系统替换。9b3d T1000补齐装备Body MI的v8曾获确认，后续预览多角色后又复发，见 [案例](cases/9B3D_QUAD.md)。找到覆盖表本身不代表已穷尽根因或证明长期稳定。

UModel 常用参数：`-game=mk12 -nomorph`。提取模型可用 `-export -gltf -notex`，独立骨骼/索引证据可用 ActorX PSK/PSKX。`-lods` 的输出必须清点；工具声称导出 LOD 不等于每个 LOD 实际都导出了。

retoc 常用：`list`、`get`、`unpack-raw`、`pack-raw`、`verify`、`to-zen --version UE4_27`。先用本机版本 `--help` 确认参数。解密材料通过本机安全配置提供，不把凭据或密钥写入公开模板。单独预览容器时可能需临时提供当前游戏 `global.utoc/ucas`，这两件仅供本地回读，不属于角色交付包。

**检查点：**目标 mesh 是正确角色/皮肤，原生骨架 hierarchy、rest transforms、sections、LOD、所有材质引用已记录。不能用 Kitana 的骨架和 ID 直接改名成 Sindel。

对Gear/Prop区分服装、面罩、武器及其实际渲染消费链。至少查看几何、骨骼和附着点，不按目录统一隐藏。Rain Gear001实际是手杖；资源名不含Staff也不能排除武器用途。参见 [Karin Y案例](cases/KARIN_Y_TRIO.md)。

## 4. 源模型评估与适配

新源/新骨架先完成 [重复故障预防检查](RETARGET_CHECKS.md) 中适用于本次变更的项目。输出实际段长和轴向/横向/头部尺度、源/目标髋中点与Hips差异、皮肤和服装共同映射、鞋底/脚踝数据。PicodraTech与UnendingFlame已重复证明仅重命名成功案例脚本会重新引入这些问题；不能等到进游戏才第一次看裤口和头身比。局部隐藏补丁不要求重跑已接受身体。

读取实际 evaluated mesh，而非只看未求值顶点：形态键、父级、约束和修改器可能影响位置。保存源文件，冻结在独立候选里，再重新绑定目标骨架。参考 [绑定规范](RIGGING.md)。

初次适配和收窄肩部后，检查可见颈长与源头颈比例，不能只通过骨架/FBX检查就进游戏。已接受其它部分时按 [头颈局部指南](NECK_PROPORTIONS.md) 冻结基线，检查完整头组、长发、领口衔接并只替换必要body；不重做全身。

肩宽与肩线分别测量：同时比较颈根到锁骨/上臂根的三维源向量和皮肤肩峰，不能只收窄X却保留不匹配的原生高差。肩线斜坡不等于颈部变长；实际下巴可能在独立面部对象中。先按[肩线指南](SHOULDER_CONTOURS.md)确定局部修法，保留相连衣物、受保护区域和原生运动枢轴的检查。

同时执行 [手部与上半身检查](UPPER_BODY_HANDS.md)：掌面与每个指段朝向；同源索引的腰封上缘/上衣/领口间距；皮肤与内外衣同场；挂件组的共同连接点。收头肩不应压短上衣，逐件保持最高点也不保证挂件相互连接。变形外观检查与导出一致性分别保留证据。

长大衣、背心或内搭使用源布料helper时，先审计每个helper的实际权重、连通块和父链语义。将所有helper无差别退化为最近Hips/Chest祖先，可能在静态图正常却在游戏动画中把下摆拉成长片。躯干主导部分可试验与目标权重一致的连续Hips–Spine–Chest场，袖/肩保留手臂影响，并避免再叠加一次body pelvis field；详见 [Karin Chrome案例](cases/KARIN_CHROME_REIKO_LIUKANG.md)。

先证明几何形状、源模型比例、完整权重数、单位和目标骨架一致，再进入材质。不要一次同时改材质、头发隐藏和骨架，使崩溃不可归因。

## 5. 优先测试单材质路径

Nyako 案例四个材质槽中只有 Body001 生效；改为一张 8192 图集和一个原生 Body001 材质后全部颜色正确。因此后续可优先测试“一个已验证原生材质 + 全部区域同一 Atlas”。先确认目标材质的采样、遮罩和透明语义，不直接假设四张纹理分别套四套原生身体材质都能工作。

同样不能为了“凑齐四通道”把 Normal 重复写入 ART/CSM。Karin Chrome v3 因此整体变暗；只覆盖已证明语义正确的 Color/Normal、保留目标原生 ART/CSM 后亮度恢复。UE工程里存在某纹理资产不等于它应进入最终stage；custom chunk白名单须按实际通道合同生成。

在保留原图前提下合并 Atlas 与变换 UV；使用 [脚本](scripts/README.md)，并测试 pixel/UV 对应。若是四张4096→8192，可保持像素尺寸；8192 需要用户同意及目标平台 Cook/运行验证。不要静默降成4096或宣称精度不变。

## 6. 导入、Cook、最小容器

多目标或并行任务隔离 UE 工程、Cook、stage、临时目录和最终输出。若复用一个 UE 工程，必须串行导入/Cook并核对输出身份；不能消费另一个任务刚覆盖的同名资产。

缓存也核对实际目录：本机`-DDC=NoShared`仍可能使用引擎目录Local缓存。出现慢启动或Put失败时先看新日志、缓存路径和读写测速，再配置本任务独立缓存；不要反复重跑完整链。已验证的多目标可在同一进程顺序导入、一次Cook明确的三个目录，但各目标输出及hash仍独立。详见[缓存与续跑](PACKAGING.md#缓存隔离慢启动与分阶段续跑)。

使用定制 UE、原生目标骨架、固定材质引用，不导入 FBX 自动生成材质，不生成新的 physics。通过 `set_editor_property` 和强制 save 保证更改落盘。

修改配置中的candidate FBX路径不会自动更新UE Content。每次几何版本变化都要先执行导入，并核对导入报告FBX hash、目标UAsset时间/hash和本轮Cook日志；若应变化的body/container hash意外与旧版相同，停止部署并检查是否Cook了旧资产。Karin Chrome首次Candidate-v6正由此被废弃，重新导入后才生成v6b。

仅打包真正替换的 mesh/texture/visibility 资产，排除编辑器占位材质、临时 Skeleton、工具辅助对象、旧测试包以及 global 容器。首次构建经 [PACKAGING.md](PACKAGING.md) 审核 Zen header、骨架原始字节及容器 store 信息。

## 7. 分别处理头、头发、断肢

Hide Head 不一定隐藏角色原生头发。对头发优先保留原始 skeleton/cloth 引用，必要时只退化可见索引；不要把原生 cloth mesh 随意替换成“一个小三角形”。断肢内部灰格可能属于独立资源，见 [可见性规范](MATERIALS_VISIBILITY.md)。

## 8. 安装与实机验证

头发以外还要检查 face、mask/装备、skin cloth（前帘、背后飘带、腰带）。修复尾项时优先在已接受容器中增加或替换已审计 chunk，不重新 Cook 全角色。新增头部包检查是否为多 export，并保留原生 store entry。

先做完整离线检查，再在游戏退出后备份并替换一整套 `.pak/.ucas/.utoc`。记录文件名及三个哈希。已知的旧测试包不能共存竞争同一路径。

必须等部署进程明确完成并核对安装哈希后再启动游戏；候选文件已生成不是安装完成证据。启动前协调正在操作游戏的用户，确认窗口与进程状态；不把无窗口直接认作崩溃。

快速进入“自定义→斗士”，避免停留主菜单触发 attract mode。切换斗士加载不完全即时，要确认加载完成才截图判断。截图按需保留，文字优先；用户反馈必须绑定到实际已安装版本。

## 9. 验收、冻结和复用

记录用户原话及已测试动作，不将“看起来可以”扩大为完整 QA。将可用包、可编辑 Blend/FBX、脚本版本、原生引用、测试报告和限制放入项目清单。后续修复只改变必要资产，复用已确认纹理和隐藏 chunk；保留一键可恢复的旧三件套。

Karin Chrome → Reiko / Liu Kang Candidate-v6b 已于2026-09-14获当前可见效果接受，覆盖用户明确提出的材质过暗、手部扭曲与大衣下摆拉伸。案例中的共同体型尺度、201/199骨数、刚性手掌回退及目标MI/chunk均不是跨角色常量；见 [案例](cases/KARIN_CHROME_REIKO_LIUKANG.md)。
