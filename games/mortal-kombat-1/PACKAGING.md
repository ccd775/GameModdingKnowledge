# UE、IoStore与部署合同

## 原生材质标量补丁：冻结模型

Riptide 材质终局采用自身原生 MI，不重新 Cook 已接受模型。Noob v6 只修改原生标量的四字节区间；Ermac v7 新增一个标量属性，需要同步扩充名称/哈希表、更新 header/export 位置与长度，以及 store size。保留原有属性、原生父链、纹理和损伤数据，不能把任意缺失参数当成原位写零。

原生 store 与 graph 的依赖顺序可以不同；本例验证长度及包含重复次数的完整集合相同，随后保持原生 store 顺序。原位修改保留全部 store，新增属性仅更新已证明变化的 size。不对 native MI 套 Cook normalize。详细审计与边界见 [原生材质补丁](NATIVE_MATERIAL_PATCHING.md)。

## 多目标容器标识与最小补丁

不同目录中的同名`cooked.utoc`可能派生相同container ID，最终包文件名不同不能证明ID独立。中间容器名也包含目标标识；用当前已识别格式验证toc与header ID一致，以及活动自定义包ID唯一。UnendingFlame定稿版本修正了这一点。不可无依据把固定header偏移推广到其它版本。

用户认可body后只修发饰，应将经过审计的native hider追加进该接受包，逐字节保留body、四张纹理与其它hider，不重新Cook全角色。Sektor V7新增1个ClothMesh包，原有25个package不变；复制native store并更新header/manifest即可。验收范围与哈希见 [案例](cases/UNENDINGFLAME_TRIO.md)。

## UE导入与保存

Karin Y的Scorpion须使用角色专属PhysicsAsset，Rain/Smoke使用MaleM；不能因主骨架相似就复制physics引用。编辑器为导入建立的依赖占位资产须显式保存，再通过实际Cook引用核对；占位资产本身不进入交付包。

- 定制UE 4.27 MK1；skeletal import使用目标原生Skeleton，关闭动画/材质/贴图自动导入和新PhysicsAsset生成，normal使用导入法线。
- 原生资产路径大小写、对象名、包ID、import/export hash及referenced package都核对；不是只重命名FBX。
- 通过 `mesh.set_editor_property('materials', slots)` 后 `save_loaded_asset(..., only_if_is_dirty=False)`，再从磁盘/Cook确认。曾有内存赋值看似成功，但保存未生效。
- 重导入可能留下旧material slots。首次单材质版可导入新唯一临时mesh，确认一槽，再备份旧asset并移动新asset到native路径。UE rename不一定留下redirector，仅在确实存在时才删除redirector；不能因断言失败把备份资产删掉。
- commandlet stdout未必包含普通 `unreal.log`；本例成功标记写在项目 `Saved/Logs/MK12.log`。检查退出码、异常、成功marker与真实磁盘时间。**Blender Python异常也可能返回进程0**，自动化应使用 `--python-exit-code 1` 并检查新生成报告/时间/hash，不能只依赖退出码或旧报告。

### 几何版本的UE资产身份门禁

配置或打包脚本读取新的FBX路径，不会自动把该FBX导入UE Content。Karin Chrome首次`Candidate-v6`在未重导入的情况下直接Cook，Reiko输出UCAS/UTOC与v4完全相同；这不是高效复用，而是Cook继续消费旧UAsset。该候选未部署，分别重导入两角色v6 FBX并核对报告后，才在独立工作目录生成`Candidate-v6b`。

只要本轮声称改变几何，Cook前至少核对：

- candidate FBX的路径、生成时间、字节数和hash；
- 本轮UE导入报告记录的input FBX hash与candidate一致；
- native目标路径的UAsset已在本轮保存，时间/hash与旧版关系可解释；
- Cook日志、Cooked UAsset和stage均属于本轮，不从旧目录无条件续跑；
- 预期变化的body package/chunk/container hash发生变化。允许不变的D/N、hider或空PAK必须在变更白名单中明确标注。

若应变化的hash意外不变，先停止部署并验证资产身份，不通过改候选标签、复制旧报告或重新pack来制造“新版”。同一工程顺序处理多角色时，每个目标都要有独立input hash与导入报告；一个角色成功重导入不能证明另一个也完成。

## 最小Cook与标准三件套

慢启动、缓存写入失败与多目标续跑先看本页末尾的[缓存隔离](#缓存隔离慢启动与分阶段续跑)。不要用增加重试次数代替定位实际失败阶段。

先Cook WindowsNoEditor，只把明确需要替换的Cook资产放入stage，路径树形如：

```text
stage/MK12/Content/Disk/Char/<Target>/Skin/<ID>/Mesh/<Body>.uasset
stage/MK12/Content/Disk/Char/<Target>/Skin/<ID>/Mesh/<Body>.uexp
stage/MK12/Content/.../Texture/... .uasset/.uexp/.ubulk
```

存在的split文件都复制。用retoc `to-zen --version UE4_27 <stage> <output.utoc>`生成容器。空pak沿用已验证的合法空pak来源并记录哈希，不把零字节文件命名成pak。`.pak/.ucas/.utoc`作为一个整体安装。

global.utoc/ucas只用于独立目录UModel回读。最终Output可能为回读暂存了global，但部署/交付必须**只选择自己的三个文件**，不能glob复制整个Output到游戏目录。

## 本案例UE4 Zen兼容修正：专用，不是通用转换器

retoc0.1.5产生的单export包与native MK1样本不同：

| 字段 | 失败候选 | 本案例可运行布局 |
| --- | --- | --- |
| ExportBundle | 2 bundles | 1 bundle |
| command words | `0,1,1,1,0,0,0,1` | `0,2,0,0,0,1` |
| dependency arcs | source -1/0/1、target1 | 0→0 |
| container store size | 0 | 实际本例package chunk长度 |

案例脚本对**单export、固定graph尺寸**做严格断言，更新graph offset、container store bundle count及size；保留payload。还在明确匹配native骨序后恢复native FTransform数组。不能对任意多export包或新版本引擎套用这些偏移。

UE4 Initial container header包含package ID表与32字节store entries。新增native hair覆盖时，登记asset path、package ID、native package graph依赖和store相对偏移。toc container ID需与实际header一致，不借用Kitana容器身份制造冲突。

原理文档用于判断问题；实际执行前阅读本机案例代码及输入断言。通用脚本只做检查，不自动猜测binary layout并写入。

## 为什么“包正确”还不代表替换成功

下方加载顺序观察针对既有案例；新增多 export 原生包需先满足文末专门合同。

`retoc verify`证明容器可解析，不证明引擎选中了它。曾经`z_...`候选在viewer可读，游戏仍原版；换到`a_...`后生效。本案最终名称 `a_nyako_sindel_bundle_P`。**这只是本地加载顺序观察，不是可靠的全版本字典序规则。**扫描所有冲突包，记录文件名、path覆盖集合、启用清单，绑定进程重启后的测试结果。

对新的目标不要复用同一个Sindel包名；每个mod唯一标识，明确哪些路径有意覆盖，禁止多个活动候选竞争同一资源。只修改一个身体网格时可在已知良好容器中替换一个chunk，并断言纹理/hider等其余chunk完全一致。

## 前置与启动配置

本机已经验证HeadRemover V2配置：

```ini
[/Script/EngineSettings.GameMapsSettings]
GameInstanceClass=/Game/HeadModV2/MK12_HeadRemoval.MK12_HeadRemoval_C
```

位于当前用户的 `AppData/Local/MK12/Saved/Steam/Config/WindowsNoEditor/Engine.ini`。只适用于该前置，不无条件覆盖其他GameInstanceClass。先备份，再按当前Mod说明合并。Steam参数、TTH DLL、逻辑Mod、角色三件套分开记。

## 安装规则

使用 [deploy_trio.ps1](scripts/deploy_trio.ps1) 默认预检：核对3个源hash、唯一文件名前缀、Paks路径、备份路径和游戏进程。传 `-Install` 后才安装。脚本拒绝在MK12运行时替换，也拒绝覆盖游戏原始pakchunk/global；备份不可在Paks内。

出现失败时不要反复换文件名、混用新旧三件套。正常退出游戏，将备份完整恢复，核对恢复hash，再重启。部署脚本会在写入失败时尝试恢复，并保留备份/状态；若恢复也失败必须人工检查，不继续启动。

脚本不自动修改前置、steam参数或启动游戏。手动恢复可同样用备份的三个文件作为输入，以记录的源hash运行预检和安装。游戏自动更新后重新确认build/native哈希，旧binary patch不可直接运行。

## 多 export 原生包：必须保留原生 store

Mileena Face001 包含 **989 exports**，Face002 包含 **816 exports**，本例各为 1 bundle；面罩包则各 1 export。不能把 `exports=1` 的 body/hair 代码直接套给 face，也不能移除断言继续打包。

v10 安全增量路线：

1. 从同一游戏 build 的原生容器取得 header 和目标 package store entry，锁定资源哈希。
2. 仅修改独立 PSK 完整验证的 render indices；保留全部 export、bundle commands、graph 和其余 payload。
3. 给候选容器新增该 package ID、路径，复制对应原生 store entry 的 size、export count、bundle count、load order、imported packages；重建 entry 的相对依赖偏移。
4. 验证 export map 大小与原生 export count 相符。本案例每项 72 bytes、单 bundle command 布局只作为布局断言，不推广到别的引擎版本。
5. 重建 container header、保持 toc/header container ID 一致，verify 后再次 unpack 比较全部 chunk。

若原生图结构不符合已审计布局，停止使用该构建器，扩展解析/证据后再做；不要回退到猜 offset。此路线不是对原生多 export 包再做单 export Zen normalize。

## 尾项修复的变更预算

### 删除 package 后必须审核重定向表

Wasou v5 在移除每角色 21 个旧自定义材质/纹理 package 后，虽然 chunk、manifest、store/graph 审计通过，仍因 header suffix 中的 21 条旧自重定向而启动崩溃。用户移除 Wasou 后恢复启动。`rebuild_container_header` 原样保留 suffix，并不自动同步 `PackageRedirects`。

本机 `AsyncLoading2.cpp::ApplyRedirects` 对缺失目标执行 `FindOrAdd(SourceId)` 可留下空 store entry，随后遍历 `ImportedPackages` 时解引用；Wasou 转储为 RVA 0x281d373、读空指针+0x1c，与该路径一致。v6 仅清除精确删除白名单中的重定向，42 个潜在空条目归零，全部资产 chunk/store 不变；截至此记录仅离线通过，未安装验收。案例入口为 MK1/karin_wasou_kunglao_quanchi/STARTUP_REDIRECT_REPAIR_V6.md。

删除资产时须同时检查文化映射和重定向目标是否可在最终活动 package 集合中解析，不能只检查 graph/store 导入依赖。不要跨格式盲删 suffix；Wasou 专用脚本断言空文化映射、自重定向和已识别尾部布局。不要据此重打其它已验收包。

撤销误隐藏也须有删除白名单。Karin Y v9移除雨的三个手杖override时，同时删除mod chunk、目录映射和package-store entry，重建header并回读确认三处均无残留；原生资源仍存在且hash匹配。其余角色只改body/header。仅从文件系统删raw chunk，或把原生安装包也删掉，均不是完整撤销覆盖。原生依赖和其它活动覆盖仍须核对，参考 [案例](cases/KARIN_Y_TRIO.md)。

用户认可身体和贴图后，头部修复不应重建它们。v10 原有 8 个 package chunk 逐字节不变，仅增加 4 个 hider 和修改 header/manifest。反之，v9 只改身体时，4 张纹理及已有 hider 必须保持不变。allowlist 由任务预先确定，不能事后把全部变化自动放行。

UE/Cook 目录按任务隔离；多角色部署清单明确到每组三件套，单角色补丁不可调用无过滤的“三角色全部部署”脚本。部署后再比对未在本轮范围中的已接受包哈希。

## 缓存隔离、慢启动与分阶段续跑

UnendingFlame V9的默认`-DDC=NoShared`仍将Local节点指向引擎`DerivedDataCache`。日志实测随机读0.16MB/s、延迟85.73ms，并多次出现Put失败。工程和Boot缓存隔离，**不代表所有Local缓存已经隔离**。

1. 先记录本轮PID、命令、工作目录、日志时间及最后进展。区分进程未初始化、资产导入/保存、Cook、退出清理与回读工具；日志没有更新不能立即认定死锁，出现`Exiting`也不等于已收到进程成功退出码。按阶段设置有依据的观察/重试界限，避免长时间重复启动完整链。
2. 查本机实际缓存图、环境覆盖和Editor设置优先级；以日志里的最终路径和测速为准。本例只给本任务子进程设置`UE-LocalDataCachePath=<任务独立可写目录>`，使用C盘本地缓存后实测36.44MB/s、0.02ms。首次新缓存会补编译着色器，不能把重建缓存当作模型退化。保留旧缓存，不修改其它任务配置或关闭安全软件。
3. 本机源码支持`-NoEnginePlugins`和`-EnablePlugins=`。本例最终导入只启用PythonScriptPlugin、EditorScriptingUtilities，Cook另启用TextureFormatOodle、OodleData。插件名从实际`.uplugin`核实；误写`OodleTexture`曾导致启动失败。该配置只对本例用到的资产验证过，不是其它工程通用模板。缺少骨骼简化插件时，本例未生成新LOD，并通过最终LOD0几何回读；其它项目需要简化或插件资产时必须保留依赖。
4. 后台进程使用明确工作目录、独立stdout/stderr日志、stdin空输入和无窗口模式；Python本机案例用`subprocess.CREATE_NO_WINDOW`。本轮还做过文件预读，这些变化和缓存迁移同时发生，**未证明任一启动参数或预读独自解决了全部延迟**，不将整批预读和反复重启作为标准流程。只终止确认属于当前任务的失败/卡住进程，不影响其它工程。
5. 源码管理检出提示不等于最终资产保存失败，也不能直接忽略。核对save结果、真实磁盘文件、目标原生路径、生成时间和后续Cook引用。本例有检出提示但资产成功写盘，最终Cook为0错误、5警告；只因最终原生引用和回读均通过才交付，不把这些警告推广为可无条件放行。

同一工程多角色可在一次UE进程内**顺序**导入，再一次Cook多个明确body目录；输入/输出身份和报告仍按目标隔离。本例本机Cook源码支持重复`-CookDir=`参数，换版本先核验。纹理虽可能因硬依赖参与Cook，最终stage和包仍只采纳body，纹理及隐藏资源从原包逐字节复用。

续跑逐阶段验证输入和产物，不凭“目录存在”“完成marker存在”就跳过。本例导入报告记录FBX hash，Cook缓存记录输入uasset hash和各输出文件hash；若资产在导入后又被改动，须重新核对它与源FBX/报告的对应关系。跨任务消费同名Cook残留不可接受。最终包还要验证raw骨架/引用、全部chunk往返及几何/UV/姿势回读。用户已接受后，单独增加验收记录，不能为了更新文档再次跑安装脚本。
