# Umbrella → Homelander / Conan：加载表、单位、材质与武器

历史游戏基线17941244，定制UE4.27、retoc0.1.5、Blender4.5.12；源为统一骨架与四页图集的Karin Umbrella。原模型/游戏payload不分发。本次公开记录来自项目离线报告和用户反馈，不是重新进行游戏验证。

## 最新状态

v8两者材质、身体和胯部获用户“其他都还好”反馈，另指出柯南武器被误隐藏。柯南v9-weapon仅撤销两处武器覆盖并通过离线检查，因MK12运行而未安装；不能声称武器已恢复。祖国人维持v8。详见[当前证据范围](../STATUS.md)。

## 资源内容与包表必须一致

v5将材质内容换回原生，但容器store仍留旧构建的size=0、2 bundles、3个依赖，包含未安装资源。v6从同build恢复原生MI store的size、bundle和29项依赖顺序，body/纹理按已识别单export合同修正bundle及store。native多export不套此normalize。

修正离线加载缺陷不等于找到全部崩溃根因：两套Umbrella移出后游戏仍以相同栈退出。隔离Wasou两包后用户确认恢复启动；其后审计发现删除旧资产时遗留自重定向。共享[打包规范](../PACKAGING.md)记录该故障机制。应分别核对chunk、manifest、package store、graph、culture map和redirect目标，不能只检查资源字符串或retoc verify。

## 单位错误不能靠回填RefPose掩盖

v6实机只有少量扭曲网格。旧构建根骨scale100、子骨平移为原生1/100，并捕获后放行骨架断言。v7采用明确厘米单位、单位对象变换和全新UE导入/Cook，先逐骨核对名称/顺序/父链/局部平移旋转缩放，再恢复原生RefPose。两角色246/251骨是案例值，不通用。最终91405个源顶点双向覆盖与五个关节回读检查通过；实机之后能显示完整形象。

## 材质要追到运行时赋值和实际通道

祖国人默认Skin001_A蓝图引用Skin001_Default/Cloth/Metal，运行时覆盖body单槽，导致Karin采样原生战衣。v8将三处材质import指向自身Body001，同时更新一个graph依赖及native store；26个exports和序列化payload保留。32字节变化是本案例审计结果，不是跨角色固定补丁。

柯南脸、上袖和护目镜发黑。旧脚本将源ORM当ART、DetailMasks当CSM，缺少shader通道依据。v8改用128²兼容性中性mask，保留D/N和native MI字节；不是完整源PBR重现。40个网格的真实材质图片与UV逐loop核对、最终贴图四页回读通过，用户随后接受其它可见效果。[材质审计方法](../NATIVE_MATERIAL_PATCHING.md)。

## 共同骨盆场必须真正作用于顶点

旧报告虽写`pelvis_common_space`，执行仍将Hips和大腿分别锚定，髋关节处产生约4.6/4.9cm纵向错位。v8以实际源/目标髋中点建立共同场，让皮肤、裤子、腰带与大腿上段在同一空间过渡；完整头/手臂/鞋/尾巴冻结。下垂挂带按连通片顶部锚点保源形，不按高度套人体场。

静态裤子10158个顶点的近表面负向样本由约16–17%降至约0.75%，源自身约0.66%；抬腿检查仍约3%。该最近法向指标不是严格实体碰撞，不能据此宣布全动作零穿插。通用算子和调用方职责见[重定向检查](../RETARGET_CHECKS.md)。

## 撤销武器误隐藏

历史清单把`SK_Conan_Gear001_A`和`SK_Conan_Gear_Sword_Template`与脸/头发一起隐藏。独立PSK包含Blade弯曲链与grab_location，旧隐藏分别退化33634/4994个三角形；Gear不能按目录判断为服装。

v9-weapon从v8移除精确两项override，同时撤销chunk、目录和store条目，让游戏回落到原生武器。两项追加资源无自重定向，保留其余suffix并检查依赖/redirect解析；9个剩余资源块逐字节不变，包含身体、MI、四纹理、三份头发/脸隐藏。原生资源hash重新确认，其它活动包无同ID覆盖，verify及raw往返通过。

retoc整目录list是合并后的视图，不能用它证明底层原生资源不存在；原生包需单独取证，竞争覆盖需逐个自定义容器查。部署默认预检拒绝运行中的游戏，因此本候选在本公开快照时仍未安装。
