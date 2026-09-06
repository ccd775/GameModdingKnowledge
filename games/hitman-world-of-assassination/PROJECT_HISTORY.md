# Karin D7-E4-04 -> HITMAN World of Assassination 角色替换 Mod SOP

## 1. 目标

将工作区中的 `karin_D7-E4-04.blend` / `karin_D7-E4-04.fbx` 制作为可部署到
HITMAN World of Assassination 的完整玩家角色模型替换 Mod。默认目标以参考 Mod 为准：
替换 Agent 47 的 Signature Suit（默认西装），不覆盖所有任务伪装。

首选交付格式为 Simple Mod Framework (SMF) 源 Mod；只有在工具验证要求下才额外生成
独立 RPKG。源资产和游戏原始 RPKG 始终保持只读。

## 2. 固定路径

- 项目根目录：`<workspace>\Mods\Hitman3`
- 游戏目录：`<steam-library>\steamapps\common\HITMAN 3`
- 游戏资源：`<steam-library>\steamapps\common\HITMAN 3\Runtime`
- 参考 Mod：`参考\chunk0patch1.rpkg`
- Blender 源文件：`karin_D7-E4-04.blend`
- FBX 交换文件：`karin_D7-E4-04.fbx`
- 下载工具：`tools\`
- 解包与中间文件：`work\`
- SMF 工程：`mod\`
- 最终交付：`dist\`

## 3. 源文件基线

| 文件 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| `参考\chunk0patch1.rpkg` | 10727623 | `C209103F3A97E2C544DBFC554DDAA230F2999EAE9BC2E6506A5CFDE1F969CB85` |
| `karin_D7-E4-04.blend` | 164833622 | `B2C0A711853060C50E0C8CF7BC1935A16794A90FA41060E003CFBF272C920920` |
| `karin_D7-E4-04.fbx` | 146710396 | `354D0F7B58BA339876E53AEB6E8F990C71EE62D20D328FB1A5FC20C100D3EC49` |

每次阶段开始前复核哈希；任何破坏性编辑只允许发生在 `work\model\` 下的副本。

## 4. 已确认的技术约束

1. starter suit 的角色资源必须位于 `chunk0`，否则跨关卡加载会崩溃。
2. 47 的可动画身体网格是 weighted PRIM；Glacier Blender Add-on 可读取但目前不能导出
   weighted PRIM，因此不能只靠该插件完成完整角色。
3. RPKG Tool 的 GLB 重建流程可保留原资源容器和骨骼数据；编辑后的网格名称、骨骼影响、
   导出轴向与原载体必须满足工具要求。
4. Season 1 和 Season 2/3 骨架不兼容。本项目使用 WoA 当前 Agent 47 S3 骨架作为最终骨架。
5. 参考 Mod 是旧式 `chunk0patch1.rpkg`。它只用于识别资源布局和可工作的替换策略，
   最终工程使用 SMF 以降低更新和 Mod 冲突风险。
6. 头部命中、布料/头发、第一人称遮挡、过场动画和 ragdoll 都需要单独验证；“能显示”
   不等于完成。

## 5. 工具版本登记

| 工具 | 固定版本 | 用途 | 状态 |
| --- | --- | --- | --- |
| RPKG Tool CLI/GUI | 2.34.0 | 解包、模型 GLB/TGA 导出与重建、RPKG 检查 | 已固定并使用 |
| Simple Mod Framework | 2.33.40 | Mod 合成、部署、回滚 | 已固定并使用 |
| GlacierKit | 1.12.15 | 资源检索、实体编辑、路径/哈希检查 | 已固定并使用 |
| Blender | 4.2.23 LTS | 重绑、权重、材质、UV、GLB 导出与离线预览 | 已固定并使用 |
| io_scene_glacier | 项目审计副本 | PRIM/BORG 格式与材质合同只读检查 | 仅用于研究/只读检查 |

下载后必须记录来源 URL、文件哈希和实际可执行文件版本，不能只记录“latest”。

## 6. 阶段流程

### A. 取证与载体确认

1. 用 RPKG Tool 导入参考包，列出所有资源哈希、类型、依赖与删除列表。
2. 从当前游戏 Runtime 解析同哈希资源，确认参考包是否仍适配当前 WoA。
3. 找出 Signature Suit 的 charset、outfit TEMP/TBLU、body weighted PRIM、BORG、
   MATI、TEXT/TEXD、碰撞资源和 hitbox 相关资源。
4. 从原游戏提取未修改的目标模型与全部依赖，保存到 `work\carrier\original\`。
5. 从参考 Mod 提取对应模型与全部依赖，保存到 `work\reference\extracted\`。
6. 对两组资源生成机器可读清单和 SHA-256，禁止靠文件名猜测覆盖关系。

通过标准：能明确回答每个参考包文件替换了哪个当前游戏资源，以及它为何需要存在。

### B. Karin 资产规范化

1. 以只读方式载入 `.blend`，记录 Blender 文件版本、对象、网格、骨架、动作、材质、
   图像、顶点/三角面数、UV、shape keys 和外部路径。
2. 若 `.blend` 与 `.fbx` 内容不一致，以 `.blend` 为主、FBX 为故障恢复输入。
3. 在 `work\model\` 保存工作副本；统一单位、轴向、对象变换和命名。
4. 移除重复/不可见/无用网格，修复非法几何、法线、UV 与贴图路径。
5. 评估材质槽和纹理预算；必要时合并材质及重排 UV，保留可复现的烘焙记录。

通过标准：无缺失贴图、无非预期负缩放、无未应用关键变换，并有完整资产报告。

### C. 骨架与权重适配

1. 导入从当前游戏提取的 Agent 47 S3 BORG/weighted PRIM 作为比例与骨骼基准。
2. 将 Karin 调整到 47 bind pose；保留 47 骨名、层级、bind matrices 和必要骨骼集合。
3. 将 Karin 网格绑定到 47 骨架。自动转权重仅作为起点，逐关节检查肩、肘、腕、
   手指、髋、膝、踝、颈、下颌及裙摆/头发区域。
4. 将每顶点骨骼影响限制为载体资源支持的上限，规范化权重并清理零权重组。
5. 生成至少一个主 LOD；是否生成额外 LOD 取决于载体结构和性能检查。

通过标准：在标准极限姿势下无明显爆点、关节断裂、未绑定顶点或错误骨骼影响。

### D. 材质、纹理与 Glacier 资源

1. 对每个最终材质建立 Diffuse/Base Color、Normal、Spec/Rough/Metal 等 Glacier 映射。
2. 纹理尺寸、压缩、alpha 和色彩空间必须与承载 MATI/TEXT 约束一致。
3. 导出 GLB 时保持载体要求的 mesh/node 名称；关闭 `+Y Up`，包含全部骨骼影响。
4. 使用 RPKG Tool 从编辑后的 GLB 重建 PRIM/TEXT/TEXD；保存重建日志。
5. 用 RPKG Tool 再次导出重建结果做 round-trip 比较。

通过标准：重建无错误，round-trip 的网格数量、材质、骨骼和边界盒符合预期。

### E. SMF 工程与部署

1. 在 `mod\Karin.D7E404\` 建立 `manifest.json` 和 `content\chunk0\`。
2. 优先做对现有 Signature Suit 资源的最小替换；仅在需要新增 outfit 结构时创建
   charset/outfit/globaldata 实体补丁。
3. manifest 固定 frameworkVersion，列出 contentFolders、必要 dependencies 和冲突说明。
4. 部署前备份 SMF 配置和当前 Mod 列表；禁止手工覆盖原始 Runtime RPKG。
5. 通过 SMF 部署，再检查生成补丁与日志。

通过标准：SMF 可重复部署/卸载；卸载后 Runtime 回到部署前状态。

### F. 游戏内验证矩阵

至少验证：

- 默认站立、行走、奔跑、冲刺、蹲伏、翻越、攀爬、拖拽尸体。
- 手枪、长枪、近战、投掷、瞄准、装填、制服目标。
- 镜子、过场动画、任务简报/出口、湿身或雨天（若材质支持）。
- 近景面部/头发、肩颈、手指、裙摆/衣物穿插。
- 被击中、爆炸、昏迷、死亡 ragdoll，以及头部命中判定。
- 至少三个不同年代/分区关卡，确认 starter suit 的 chunk0 可用性。
- 1080p 下前景与远景 LOD、帧时间和显存异常。

每项记录 PASS / FAIL / BLOCKED，失败项必须有截图、日志或明确复现步骤。

## 7. 回滚规则

1. 不改动 `karin_D7-E4-04.blend`、`karin_D7-E4-04.fbx` 和 `参考\`。
2. 不手工覆盖游戏原始 base/patch RPKG。`chunk0patch300.rpkg` 只能由 SMF 生成或清理。
3. 每次部署前记录 Runtime 中新增/变化文件的哈希和时间戳。
4. 若游戏无法启动，先从 SMF load order 移除 Karin 并重新部署，再核对 Runtime；保留其他用户 Mod，
   不要删除游戏原包。

## 8. 当前进度（2026-07-22）

- 参考包、当前 Signature Suit TEMP/TBLU、可见/碰撞 PRIM、BORG、MATI 与 TEXT/TEXD
  闭包均已审计；最终实体补丁只面向当前 TBLU `0046BB3BE76661CC`。
- Karin 已重定向到 235-joint 女性载体骨架，整理为六个可见槽位；生产 GLB、最终 PRIM、
  18 对 Karin TEXT/TEXD 与两套碰撞资源均已完成。
- SMF 源 Mod `mod\Karin.D7E404`、SMF 安装副本和 109 文件候选包均通过结构校验；
  manifest 仍为预验收版本 `0.1.0`。
- 已完成部署前备份并由 SMF 成功部署到 `Runtime\chunk0patch300.rpkg`；部署日志无
  `ERROR`、`WARN`、`failed` 或 `exception`。
- 离线模型、贴图、SMF 部署和实际 patch300 独立解包检查已通过；游戏内启动、动作、命中、ragdoll、光照、LOD、
  不同关卡与地面高度仍需人工验收，因此不得宣称 1.0 完成。

## 9. 研究来源

- Glacier Modding suit guides: `https://glaciermodding.org/docs/modding/hitman/guides/suitmodding/`
- Glacier 2 Blender Add-on: `https://glaciermodding.org/docs/modding/hitman/tools/blender/`
- RPKG Tool: `https://github.com/glacier-modding/RPKG-Tool`
- Simple Mod Framework: `https://github.com/atampy25/simple-mod-framework`
- GlacierKit: `https://github.com/atampy25/glacierkit`

来源用于解释工具和格式，最终判断必须由本地当前游戏文件、参考包和 round-trip 测试验证。

## 10. 固化检查点（2026-07-22，游戏 3.270.1）

### 10.1 源资产与部署前只读基线

| 对象 | 版本/大小 | SHA-256 |
| --- | --- | --- |
| `参考\chunk0patch1.rpkg` | 10,727,623 bytes | `C209103F3A97E2C544DBFC554DDAA230F2999EAE9BC2E6506A5CFDE1F969CB85` |
| `karin_D7-E4-04.blend` | 164,833,622 bytes | `B2C0A711853060C50E0C8CF7BC1935A16794A90FA41060E003CFBF272C920920` |
| `karin_D7-E4-04.fbx` | 146,710,396 bytes | `354D0F7B58BA339876E53AEB6E8F990C71EE62D20D328FB1A5FC20C100D3EC49` |
| `Retail\HITMAN3.exe` | 3.270.1.0 | `B4FB04F460FD67E67F21264D7AD0D64BC081FBA62EC71E36B898D04DB9E8620D` |
| 部署前 `Runtime\packagedefinition.txt` | Steam build 23678892 | `3C916E0807385FF6406EE40A014F8DB2D1C5E9BFCF4C85B504A446E94CF400FD` |

每次恢复任务时先复核前三项源资产和游戏 EXE。第五项是部署前 clean baseline；Karin 已部署时，
当前 packagedefinition 应改为 10.7 记录的部署后哈希，不能要求它仍等于 clean baseline。游戏版本或
源资产哈希改变时，不允许直接沿用实体索引；重新执行当前 Runtime 的 TEMP/TBLU 提取和实体迁移验证。

### 10.2 固定工具链

- Blender `4.2.23 LTS`：`tools\blender-4.2.23-windows-x64\blender.exe`
- RPKG Tool CLI `2.34.0`：`tools\rpkg-2.34.0\rpkg-cli.exe`
- Simple Mod Framework `2.33.40`：`tools\simple-mod-framework-2.33.40\`
- GlacierKit `1.12.15`：`tools\glacierkit-1.12.15\PFiles\GlacierKit\GlacierKit.exe`
- 下载包、可执行文件 URL 与 SHA-256：`work\model\audit\tool_manifest.json`

不要使用 `latest` 替代以上固定版本。Blender 源文件头为 `BLENDER-v402`；规范输入为 `.blend`，FBX 仅作恢复输入，因为 FBX 丢失 `Dots Stroke` 材质并改变 46 根骨尾端。

### 10.3 已确认的参考资源合同

- 当前 Signature Suit：TEMP `00FF8C6314EA882E`，TBLU `0046BB3BE76661CC`。
- 参考可见 weighted PRIM：`00D11B968A0DA0AA`，BORG：`00BE1067BB335864`。
- 女性身体碰撞 PRIM：`009F932F166B84AA`，BORG：`00E6A8821E63B8BD`。
- 女性头部碰撞 PRIM：`0097F489BCD30E09`，外部 BORG：`00BA47B9FA866AD2`。
- 可见载体固定为 6 个视觉分区、235 joints；六个 raw PRIM material ID 依次为 `1..6`。该值是 PRIM dependency index：dependency `0` 是 BORG，dependency `1..7` 是 MATI `x0..x6`，所以可见槽位实际使用 MATI `x0..x5`，MATI `x6` 未被可见分区使用。
- 参考包的 58 个非零外部依赖在当前 Runtime 中均存在，但它的实体层不能直接复用：它覆盖旧 Knight TBLU `009E68E96BBF470A`、遗漏当前 `knight_hair`，并重复使用 entity ID `806bb8a1909ee658`。最终 Mod 只能使用当前 Signature Suit 的 QuickEntity patch。

实体补丁位于 `mod\Karin.D7E404\content\chunk0\KarinSignatureSuit.entity.patch.json`。恢复后运行：

```powershell
python work\entity-migration\build_entity_migration.py
```

只有 `work\entity-migration\validation.json` 为 `status: pass` 才能继续打包。补丁使用三个唯一实体 ID `d7e4040000000001..3`，且不得出现旧 Knight TBLU。

### 10.4 模型与骨架输入事实

- Karin：10 mesh、47,052 vertices、88,512 triangles、243 deform bones、12 materials；v3 构建实际提取
  17 张内嵌图像（10 diffuse、5 normal、2 emissive）。
- 源骨名与目标骨架精确同名为 0；必须做完整重定向，不能只改骨名。
- 必须烘焙当前可见 shape key：`Body/Ahoge_big=1`、`Body/Hair_tail_volume_up=1`、`Body.003/Foot_OFF=1`、`Body.003/Toe_OFF=1`，随后移除 morph target。
- 初始身高比例估计 `1.383329` 仅用于起点；最终以头、肩、髋、膝、踝等 landmark 拟合为准。
- `work\model\audit\comparison.md` 是规范审计报告；`work\model\audit\preview\karin_parts_contact_sheet.png` 是部件基准图。
- 已完成重定向工作副本为 `work\model\rig-prototype\karin_retargeted.blend`，SHA-256
  `114B6307119D257D4B579F5C0FB6877DFF61FC0B1E540F1337E07CD13CDE6069`。它使用目标 235-joint
  骨架，47,052 个原始顶点全部有权重、最多 4 个 influence，且权重已规范化。

坐标轴规则已经用 RPKG 2.34 源码和真实 round-trip 确认：

1. 不给载体额外旋转，不 Apply Transform。
2. 保留载体 Armature、mesh parent 和 world matrix。
3. 将世界直立的 Karin 顶点写入载体 mesh local 时使用 `carrier.matrix_world.inverted() @ karin.matrix_world`。
4. glTF 导出必须关闭 `+Y Up`，即 Blender 参数 `export_yup=False`；打开会使游戏内模型横躺。

### 10.5 六槽位与纹理规则

规范配置为 `config\karin_build.json`：

| 槽位 | Karin 对象 | 参考材质 ID | 纹理组 |
| ---: | --- | ---: | --- |
| 0 | `Body` | 1 | `...01A/02A/03A` |
| 1 | `Body.009 + Body.010` | 2 | `...11A/12A/13A` |
| 2 | `Body.003` | 3 | `...21A/22A/23A` |
| 3 | `Body.006` | 4 | `...31A/32A/33A` |
| 4 | `Body.001` | 5 | `...41A/42A/43A` |
| 5 | `Body.002 + Body.005 + Body.007 + Body.008` | 6 | `...51A/52A/53A` |

注意 raw material ID 不能按哈希尾号理解；正确纹理组是 `x0` 到 `x5`，不是 `x1` 到 `x6`。槽位 0、1、5 使用 2x2 atlas；其余使用单格。UV cell 变换必须与 `scripts\build_texture_atlases.py` 的 bottom-origin 行号一致，并保留 8 px 边缘扩展。

v3 纹理使用 17 张源图：10 张 diffuse、5 张 normal 和 2 张 emission mask。以下记录本次构建的
实际参数；重复运行时应把三个输出目录改为新的空目录，验证后再晋升，禁止覆盖现有审计证据：

```powershell
& tools\blender-4.2.23-windows-x64\blender.exe `
  --background --factory-startup --disable-autoexec karin_D7-E4-04.blend `
  --python scripts\blender\extract_packed_images.py -- `
  --config config\karin_build.json `
  --output work\model\textures\source-v3

python scripts\build_texture_atlases.py `
  --config config\karin_build.json `
  --source-dir work\model\textures\source-v3 `
  --output work\model\textures\atlases-v3-x0-x5-emissive-baked

python scripts\rebuild_text_resources.py `
  --config config\karin_build.json `
  --atlas-dir work\model\textures\atlases-v3-x0-x5-emissive-baked `
  --carrier-text-dir work\reference\converted\reference-models\visible\00D11B968A0DA0AA.PRIM\TEXT\chunk0patch1.rpkg `
  --build-dir work\build\text-resources-4096-v3 `
  --rpkg-cli tools\rpkg-2.34.0\rpkg-cli.exe
```

输出为 x0 到 x5 的 18 张 4096x4096 RGBA TGA，随后重建为 18 TEXT + 18 TEXD；每张 TEXT
均为 4096x4096、13 mip。`ClothA_Blue` 与 `ClothB_Blue` 的 emission mask 以 Screen、强度
`0.4` 烘入 diffuse RGB，alpha 逐像素保持不变。当前 `basic_discard` 角色 MATE 没有可用的
emissive sampler，因此这是保留发光标记颜色的稳定方案，不是真正自发光。

v3 TEXT/TEXD 包为
`work\build\text-resources-4096-v3\RPKGS\chunk0.rpkg`，50,748,126 bytes，SHA-256
`A0D14E0E4F432B9E057D6C7C90313F115FB3C32F1B4EEFB2D2865E8D654BB2B1`；重新解包后 36 个
资源二进制与 `REBUILT` 逐文件 SHA-256 一致。RPKG 重建输入的 `.TEXT.tga.meta`、
`.TEXT.meta` 和对应 `.TEXD.meta` 三者缺一不可。group x6 未被六个可见 mesh 使用，但仍属于
依赖闭包；它的 3 TEXT + 3 TEXD 继续使用参考包原件。

纹理格式审计结论：normal `0x55` 为 BC5；specular `0x5A` 回环为 RGBA8；diffuse 头 `0x49`
由 RPKG Tool 报告为 `DXGI_FORMAT_BC2_TYPELESS`。当前实际编码路径会把中间 alpha 二值化，
所以头发与面部 cutout 边缘必须在游戏近景中验收。完整证据见
`work\texture-review\REPORT.md` 和 `work\build\text-resources-4096-v3\build-manifest.json`。

### 10.6 PRIM 导出硬约束

生产 GLB 必须：

- 文件名、`metas\HASH.PRIM.glb.meta` 和 `metas\HASH.PRIM.meta` 与载体完全配套；RPKG 2.34
  重建 weighted PRIM 时两个 meta 都需要，不能只复制 `.PRIM.glb.meta`；
- 恰好 6 个连续 mesh datablock 后缀 `_0.._5`，每个一个 indexed triangle primitive；
- 每个 mesh 顶点和索引可由 unsigned 16-bit 表达，所有顶点有权重，最多 4 个非零 influence；
- 235 个 joint 名称集合与载体完全一致；不要求数据块顺序一致，且不含 animation、morph target
  和额外 skin；
- 只做一次最终 RPKG PRIM 重建，因为不改几何的 GLB 回建也会使权重产生小量量化变化。

从已重定向工作副本生成六槽生产模型。下列是本次实际参数；现有 `production-final` 是冻结证据，
需要重新生成时必须先把三个 output/report 参数改到新的空目录：

```powershell
& tools\blender-4.2.23-windows-x64\blender.exe `
  --background --disable-autoexec work\model\rig-prototype\karin_retargeted.blend `
  --python scripts\blender\build_karin_six_slot.py -- `
  --config config\karin_build.json `
  --carrier work\reference\converted\reference-models\visible\00D11B968A0DA0AA.PRIM\PRIM\chunk0patch1.rpkg\00D11B968A0DA0AA.PRIM.glb `
  --output-blend work\model\production-final\karin_six_slot.blend `
  --output-glb work\model\production-final\00D11B968A0DA0AA.PRIM.glb `
  --report-dir work\model\production-final

python scripts\validate_prim_glb.py `
  work\model\production-final\00D11B968A0DA0AA.PRIM.glb `
  --carrier work\reference\converted\reference-models\visible\00D11B968A0DA0AA.PRIM\PRIM\chunk0patch1.rpkg\00D11B968A0DA0AA.PRIM.glb `
  --joint-policy exact `
  --json-out work\model\production-final\glb-validation.json

$primRebuildRoot = Join-Path (Resolve-Path work\model) `
  ('prim-rebuild-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $primRebuildRoot | Out-Null
New-Item -ItemType Directory -Path "$primRebuildRoot\metas" | Out-Null
Copy-Item -LiteralPath work\model\production-final\00D11B968A0DA0AA.PRIM.glb `
  -Destination $primRebuildRoot
Copy-Item -LiteralPath work\model\production-final\metas\00D11B968A0DA0AA.PRIM.glb.meta `
  -Destination "$primRebuildRoot\metas"
Copy-Item -LiteralPath work\model\production-final\metas\00D11B968A0DA0AA.PRIM.meta `
  -Destination "$primRebuildRoot\metas"
& tools\rpkg-2.34.0\rpkg-cli.exe -rebuild_prim_in $primRebuildRoot

python -m unittest discover -s tests -v
```

生产 GLB 为 4,130,448 bytes，SHA-256
`0F42138D51AC1574BB185121A4B8FCAF4D40FB93667D45B9CC3FDFA5A2949AB0`；校验结果为 6 mesh、
58,625 个 glTF 拆分后顶点、235 joints、1 skin、0 animation、0 morph、0 error、0 warning。
最终 raw PRIM 位于 `work\model\production-final\REBUILT\00D11B968A0DA0AA.PRIM`，
2,881,584 bytes，SHA-256
`4F32E994413C4401DDA1B5E8E8D60C30EDEDDCD34794C70C1160551EAE12D8FD`。

最终 PRIM 必须与可见 BORG 一起放入临时 `chunk0` 才能再次导出 GLB。下列路径是本次已落盘的
回环证据；再次审计时保留同一只读 input，但把 package、extracted 和 JSON 输出改到新的时间戳目录：

```powershell
& tools\rpkg-2.34.0\rpkg-cli.exe `
  -output_path work\model\production-final\roundtrip-package-with-borg `
  -generate_rpkg_quickly_from work\model\production-final\roundtrip-package-input-with-borg\chunk0

& tools\rpkg-2.34.0\rpkg-cli.exe `
  -filter 00D11B968A0DA0AA `
  -output_path work\model\production-final\roundtrip-extracted-with-borg `
  -extract_prim_to_glb_from work\model\production-final\roundtrip-package-with-borg\chunk0.rpkg

python scripts\validate_prim_glb.py `
  work\model\production-final\roundtrip-extracted-with-borg\00D11B968A0DA0AA.PRIM.glb `
  --carrier work\reference\converted\reference-models\visible\00D11B968A0DA0AA.PRIM\PRIM\chunk0patch1.rpkg\00D11B968A0DA0AA.PRIM.glb `
  --joint-policy exact `
  --json-out work\model\production-final\roundtrip-glb-validation.json

python scripts\compare_prim_roundtrip.py `
  work\model\production-final\00D11B968A0DA0AA.PRIM.glb `
  work\model\production-final\roundtrip-extracted-with-borg\00D11B968A0DA0AA.PRIM.glb `
  --json-out work\model\production-final\roundtrip-comparison.json
```

`roundtrip-comparison.json` 为 `pass`：索引、顶点色和按骨名解析后的 joint influences 全部一致；
最大误差为 position `1.5911e-5 m`、normal `0.00392163`、UV `7.5102e-6`、weight
`0.01144457`，均低于脚本阈值。RPKG 会重排 skin joint 顺序并联合量化/规范化四个 byte 权重，
所以不能要求 raw joint index 或浮点权重逐字节一致；必须按 joint name 比较。

### 10.7 SMF 组装与已完成部署

最终源 Mod 位于 `mod\Karin.D7E404`，安装副本位于
`tools\simple-mod-framework-2.33.40\Mods\Karin.D7E404`。候选包
当前发布候选 `work\smf-packaging-review\final-candidate-v5-2048-stable` 的
`content\chunk0` 恰有 109 个文件：

- 54 个 raw Glacier 资源：2 BORG、7 MATI、3 PRIM、21 TEXT、21 TEXD；
- 对应 54 个 binary `.meta`；
- 1 个 `KarinSignatureSuit.entity.patch.json`。

候选、晋升后的源 Mod 和 SMF 安装副本均通过校验：

```powershell
python work\smf-packaging-review\verify_smf_package.py `
  mod\Karin.D7E404 `
  --json-out work\smf-packaging-review\promoted-mod-validation.json

python work\smf-packaging-review\verify_smf_package.py `
  tools\simple-mod-framework-2.33.40\Mods\Karin.D7E404 `
  --json-out work\smf-packaging-review\installed-mod-validation.json
```

两项都必须为 `status: pass`、109 files、0 errors、0 warnings。实体补丁 SHA-256 为
`0D191A94C33AFC8F627DF784E751613021BCDE8C1B364C6005F88AECB645B321`；manifest ID 为
`DroyLouo.KarinD7E404`，游戏内验收前版本保持 `0.1.0`。

SMF `config.json` 必须使用游戏绝对路径，且只启用 Karin；已存在的 `Realistic AI` 源目录保留、
不自动加入 load order。下列片段只展示必须核对的字段，禁止用它覆盖完整 `config.json`，其余原有
选项和数组必须保留：

```json
{
  "runtimePath": "C:\\SteamLibrary\\steamapps\\common\\HITMAN 3\\Runtime",
  "retailPath": "C:\\SteamLibrary\\steamapps\\common\\HITMAN 3\\Retail",
  "loadOrder": ["DroyLouo.KarinD7E404"]
}
```

正式部署流程：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\deployment_preflight.ps1 `
  -OutputPath .\work\deployment-preflight\ready-to-deploy.json `
  -AllowOverwrite

Set-Location .\tools\simple-mod-framework-2.33.40
& .\Deploy.exe --useConsoleLogging --doNotPause
Set-Location ..\..

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\deployment_preflight.ps1 `
  -OutputPath .\work\deployment-preflight\post-deploy.json `
  -AllowOverwrite
```

只有部署前快照的 `readiness.safeToInvokeDeploy=true` 才可运行 `Deploy.exe`。部署后快照会因为
检测到 SMF 管理的 patch300 和已改变的 packagedefinition 而返回 blocker；这是“当前已部署”的
预期结果，不能把它误判为部署失败。

本次 SMF 部署在 8 秒内完成，日志见 `work\deployment-preflight\deploy.stdout.log` 和 SMF
`Deploy.log`。实际生成：

| 对象 | 结果 |
| --- | --- |
| `Runtime\chunk0patch300.rpkg` | 18,071,575 bytes；SHA-256 `C9D83AB698C98ECEF055196102258DCA918259171C3F02744FC9F9E514ADA3FA` |
| `Runtime\packagedefinition.txt` | SHA-256 `5B73DD38DB4F3A5EDF31EAAA5F05E57829C9EC9EAA259E91D960EA29FC2FC2FD` |
| `Runtime\chunk30.rpkg` | 未变；SHA-256 `167C478C4CF9EB02514576AEB0D82E80604E58865FD7DAB5E32CCBD4CA28C785` |
| `Retail\thumbs.dat` | 未变；SHA-256 `623F127A949C6B6DE6E32FB1EE0F06E0705538A24DE5B1D278705DC998337871` |

### 10.8 部署备份与精确回滚

本次部署前备份位于
`work\deployment-backup\20260722-165618-before-karin`；`backup-inventory.json` 记录 11 个文件
及 SHA-256，包括 Runtime packagedefinition、25-byte `chunk30.rpkg`、Retail `thumbs.dat`、SMF
`config.json`、`cleanPackageDefinition.txt` 和原有 `Mods\Realistic AI`。部署前基线：

- `packagedefinition.txt`：`3C916E0807385FF6406EE40A014F8DB2D1C5E9BFCF4C85B504A446E94CF400FD`；
- 不存在 patch200..300，也不存在 base chunk >30；
- `chunk30.rpkg` 和 `thumbs.dat` 的哈希与上表相同。

通常只需在 `config.loadOrder` 中移除 `DroyLouo.KarinD7E404` 后重新运行 SMF Deploy；SMF 会清理
旧 patch300 并按其余 load order 重建。若需要恢复到本次部署前的逐字节状态，先退出游戏并确认
当前 patch 仍是本次已记录文件，再执行精确回滚：

```powershell
$gameRoot = '<steam-library>\steamapps\common\HITMAN 3'
$smfRoot = '<workspace>\Mods\Hitman3\tools\simple-mod-framework-2.33.40'
$backupRoot = '<workspace>\Mods\Hitman3\work\deployment-backup\20260722-165618-before-karin'
$patch = "$gameRoot\Runtime\chunk0patch300.rpkg"
$expectedPatchSha = 'C9D83AB698C98ECEF055196102258DCA918259171C3F02744FC9F9E514ADA3FA'

if (-not (Test-Path -LiteralPath $patch)) { throw "Missing deployed patch: $patch" }
if ((Get-FileHash -LiteralPath $patch -Algorithm SHA256).Hash -ne $expectedPatchSha) {
  throw 'Deployed patch differs from the recorded Karin build; do not delete it blindly.'
}

Remove-Item -LiteralPath $patch
Copy-Item -LiteralPath "$backupRoot\Runtime\packagedefinition.txt" `
  -Destination "$gameRoot\Runtime\packagedefinition.txt" -Force
Copy-Item -LiteralPath "$backupRoot\SMF\config.json" `
  -Destination "$smfRoot\config.json" -Force
Copy-Item -LiteralPath "$backupRoot\SMF\cleanPackageDefinition.txt" `
  -Destination "$smfRoot\cleanPackageDefinition.txt" -Force
```

`chunk30.rpkg` 和 `thumbs.dat` 本次没有变化，不要顺手删除或覆盖；只有重新计算哈希发现变化，才从
备份恢复对应文件。也不要删除整个 SMF `Mods`，否则会破坏用户原有的 `Realistic AI`。回滚后重新
运行 `deployment_preflight.ps1`，要求 packagedefinition 与 clean baseline 字节一致、
`managedPatches200Through300=[]`、`baseChunksAbove30=[]`，且 `chunk30.rpkg` 哈希恢复为基线。

### 10.9 最终验证状态、路径与已知限制

截至本次 SOP 更新，以下离线/静态门槛已通过：

| 检查 | 状态 | 证据 |
| --- | --- | --- |
| 当前 Signature Suit 实体迁移 | PASS（20 checks） | `work\entity-migration\validation.json` |
| 六槽 Blender/GLB 构建 | PASS | `work\model\production-final\build-report.json` |
| 生产 GLB 合同 | PASS（0 error / 0 warning） | `work\model\production-final\glb-validation.json` |
| PRIM + BORG 回环 | PASS | `work\model\production-final\roundtrip-glb-validation.json`、`roundtrip-comparison.json` |
| v3 离线六视图/姿势/面发预览 | PASS | `work\model\production\previews-v3\validation-report.json` |
| 18 TEXT + 18 TEXD 重建/二进制回环 | PASS | `work\build\text-resources-2048-v5-stable\build-manifest.json` |
| SMF v5 候选、源 Mod、安装副本 | PASS | `work\smf-packaging-review\final-candidate-v5-validation.json`；三个目录完整树哈希差异为 0 |
| 部署前安全检查 | PASS | `work\deployment-preflight\ready-to-deploy.json` |
| SMF 正式部署 | PASS（工具层） | `work\deployment-preflight\deploy.stdout.log`、`post-deploy.json` |
| 实际 v5 patch300 独立解包/实体/PRIM/六槽材质 | PASS | `work\deployed-validation\v5-static\DEPLOYED_V5_STATIC_VALIDATION.md` |
| 运行环境与启动路径审计 | PASS（只读准备） | `work\deployed-validation\RUNTIME_LAUNCH_AUDIT.md` |
| Python 单元测试 | PASS（16 tests） | 命令 `python -m unittest discover -s tests -v` |

实际 `Runtime\chunk0patch300.rpkg` 已独立解包到
`work\deployed-validation\static-20260722-171500`，结果为 56 个资源：2 BORG、7 MATI、3 PRIM、
21 TEXT、21 TEXD、1 TEMP、1 TBLU。当前 TEMP `00FF8C6314EA882E` 与 TBLU
`0046BB3BE76661CC` 均存在，旧 Knight TBLU 不存在。54 个自定义资源 payload 与
`mod\Karin.D7E404` 逐字节 SHA-256 一致；54 个 `.meta` 的资源身份、引用表、依赖 flags/hashes
及内存字段全部一致。整份 `.meta` 的哈希不应相等，因为 RPKG 重新打包会重算 package offset、
packed size 和 final size。

部署包直接导出的可见 GLB 为 5,056,176 bytes，SHA-256
`5830F37899B4AB9BBCC5B548785EF735343A763FF6CF78B10DD116A0586782C5`，与受控 PRIM+BORG
回环 GLB byte-exact；六槽、58,625 顶点、235 joints 和误差阈值再次全部通过。textured 导出还确认：
mesh `_0.._5` 分别使用 material `0..5`，material 6 只保留依赖闭包；v5 的 18 张实际使用图像均为
2048x2048，未用 x6 的两张图同样保留参考 carrier 的 2048x2048 契约。Runtime QuickEntity 的 body parts
恰好是 Karin 可见 PRIM、女性身体碰撞和女性头部碰撞三项。

复现时必须使用新的 `<new-id>` 输出目录，不能在旧审计目录上混合文件：

```powershell
& tools\rpkg-2.34.0\rpkg-cli.exe `
  -output_path work\deployed-validation\<new-id>\raw `
  -extract_from_rpkg '<steam-library>\steamapps\common\HITMAN 3\Runtime\chunk0patch300.rpkg'

& tools\rpkg-2.34.0\rpkg-cli.exe `
  -filter 00D11B968A0DA0AA `
  -output_path work\deployed-validation\<new-id>\prim `
  -extract_prim_to_glb_from '<steam-library>\steamapps\common\HITMAN 3\Runtime\chunk0patch300.rpkg'

python scripts\validate_prim_glb.py `
  work\deployed-validation\<new-id>\prim\00D11B968A0DA0AA.PRIM.glb `
  --joint-policy exact `
  --json-out work\deployed-validation\<new-id>\prim-validation.json

python scripts\compare_prim_roundtrip.py `
  work\model\production-final\00D11B968A0DA0AA.PRIM.glb `
  work\deployed-validation\<new-id>\prim\00D11B968A0DA0AA.PRIM.glb `
  --json-out work\deployed-validation\<new-id>\prim-roundtrip-comparison.json

& tools\rpkg-2.34.0\rpkg-cli.exe `
  -filter 00D11B968A0DA0AA `
  -output_path work\deployed-validation\<new-id>\textured `
  -extract_prim_textured_from '<steam-library>\steamapps\common\HITMAN 3\Runtime\chunk0patch300.rpkg'

& tools\rpkg-2.34.0\rpkg-cli.exe `
  -filter 00FF8C6314EA882E `
  -qn_format entity `
  -output_path work\deployed-validation\<new-id>\entity `
  -extract_entity_to_qn '<steam-library>\steamapps\common\HITMAN 3\Runtime'
```

RPKG 的 textured preview exporter 不输出 specular，也会省略 `COLOR_0`，因此
`textured-vs-untextured-geometry.json` 对颜色属性报告 `fail`，而
`textured-prim-validation.json` 报 6 个 warning。该限制只存在于预览 GLB 导出路径；直接 non-textured
部署 PRIM 导出包含六个 mesh 的 `COLOR_0`，并已通过精确顶点色比较，不能把这个预览告警误记为
部署 PRIM 缺色。

游戏启动、主菜单、Dubai 内容加载和长时间稳定性已通过；Signature Suit 的完整动作 F 节矩阵仍为
`PENDING`。启动前按
`work\deployed-validation\RUNTIME_LAUNCH_AUDIT.md` 确认 `Deploy.exe`、`Launcher.exe`、
`HITMAN3.exe` 均未运行，然后用标准 Steam 上下文启动：

```powershell
$launchStarted = Get-Date
Start-Process -FilePath 'steam://rungameid/1659040'
```

若只出现 Launcher，必须由用户点击 Play；不能把 Launcher 存活当作游戏已启动。启动后尤其必须检查：
Signature Suit 加载、站立/走跑/蹲伏/
翻越/攀爬/拖尸、武器与瞄准、过场/镜子、头部命中、被击/ragdoll、近景 alpha、不同光照、
至少三张跨年代地图、LOD/性能和脚底接地。通过前存在以下已知限制：

- 长发与发尾已经刚性归并到 head/pelvis 相关权重，没有独立二级物理动画；
- ClothA/ClothB 只保留烘进 diffuse 的发光标记，当前不是光照无关的真实 emissive；
- Glacier specular 为保守估算值，且 diffuse 编码会二值化中间 alpha，需在游戏近景和多光照调校；
- 头/身体碰撞沿用已验证的女性参考 carrier，不是按 Karin 外形重新制作，命中与穿插必须实测；
- 离线包围盒显示服装/足部局部最低点需要专门做地面接触检查，不能从静态预览推断无下陷。

只有部署包独立解包、完整游戏内矩阵和卸载/回滚演练都通过后，才把 manifest 从 `0.1.0` 升为
`1.0.0` 并制作最终归档。

恢复顺序：先复核 10.1 源资产哈希和 10.8 当前部署/备份哈希，再读
`work\reference\REPORT.md`、`work\model\audit\comparison.md`、`work\entity-migration\REPORT.md`、
`work\texture-review\REPORT.md` 以及 10.9 的最终机器可读报告；不要重新猜测已确认的资源关系，
也不要在未检查当前 SMF load order 时重复 Deploy。

## 11. 2026-07-22 v5 稳定化补充（覆盖 10.4、10.7、10.9 的发布值）

### 11.1 为什么最终版回退到 2048

v3 把 18 张使用中图集升到 4096，但错误沿用了 2048 carrier 的 36 个
`hash_size_in_video_memory` 字段；游戏在 71 秒时于 TEXT 流式释放路径触发 allocator abort。
v4 把 normal/spec 的字段修正为 `22,347,776`、diffuse 修正为 `11,173,888`，静态包完全正确，
但仍在 36 秒时以损坏的 XAudio callback vtable 形态崩溃。两个 dump 的证据与因果边界见
`work\deployed-validation\CRASH_DIAGNOSIS.md`。

最终 v5 只把图集和 mip 契约恢复为参考 carrier 原生值，实体、PRIM、BORG、MATI、hash 和六槽 UV
保持不变：

```powershell
python scripts\build_texture_atlases.py `
  --config config\karin_build_2048_stable.json `
  --output-dir work\model\textures\atlases-v5-2048-stable

python scripts\rebuild_text_resources.py `
  --config config\karin_build_2048_stable.json `
  --atlas-dir work\model\textures\atlases-v5-2048-stable `
  --build-dir work\build\text-resources-2048-v5-stable `
  --rpkg-cli tools\rpkg-2.34.0\rpkg-cli.exe
```

v5 输出为 18 个 2048x2048 / 12 mip TEXT 和 18 个 TEXD。36 个 candidate meta 与 carrier
逐字节相同，offset 40 分组为 24 个 `5,570,560`、12 个 `2,785,280`。RPKG 回读后 meta
只允许容器重写 offsets `8..10` 与 `32..34`；offset 40、依赖区和资源身份必须不变。

### 11.2 Package Definition Patcher 前置

参考 Mod 页面要求 Package Definition Patcher 或 XTEA Online Tool，是因为手工复制 RPKG 时必须提高
`packagedefinition.txt` 的 patch level。本流程通过 SMF 2.33.40 部署；它内置
`Third-Party\h6xtea.exe`，日志明确包含 `Patching packagedefinition`，因此不要重复安装 Nexus 113
或再次运行在线 XTEA 工具。

本机审计用 SMF 自带工具分别解密 clean/deployed 文件到
`work\runtime-validation\package-definition-audit`。clean 文件的主要分区为 `patchlevel=4`；部署后
31 个分区全部为 `patchlevel=310`，已经覆盖 `chunk0patch300.rpkg`。重复 patch 会让同一敏感文件
出现第二个写入者，反而降低回滚可控性。

### 11.3 v5 发布与运行证据

- 候选：`work\smf-packaging-review\final-candidate-v5-2048-stable`；109 content files。
- SMF 源目录和安装副本与候选完整树哈希差异均为 0。
- 部署日志：`work\deployment-v5\deploy.stdout.log`；stderr 为空，退出码 0。
- 实际 patch：18,071,575 bytes，SHA-256
  `C9D83AB698C98ECEF055196102258DCA918259171C3F02744FC9F9E514ADA3FA`。
- 独立解包：56 resources，54/54 custom payload 精确一致，详情见
  `work\deployed-validation\v5-static\DEPLOYED_V5_STATIC_VALIDATION.md`。
- run 1：进入主菜单，约 198 秒后 Steam 记录正常 exit code 0，无 dump/WER。
- run 2：连续响应 3,392.5 秒（56 分 32.5 秒），覆盖在线主菜单、Dubai 内容加载、过场和规划菜单；
  之后由验证脚本发送 `WM_CLOSE`，Steam exit code 0，无 dump/WER。
- run 3：连续响应 5,694 秒（94 分 54 秒），在 Career 库存和 Dartmoor 规划页明确选择
  `47's Signature Suit`，进入 `Death in the Family` 实际关卡后确认 Karin 模型、六槽贴图、站立、
  前进、蹲伏、手枪拔出与瞄准均可运行；之后正常关闭，Steam exit code 0，无 dump/WER。关键截图位于
  `work\runtime-validation\v5-run3-career`。

运行证据与剩余验收边界见 `work\runtime-validation\V5_RUNTIME_VALIDATION.md`。当前 0.1.0 可以作为
已完成实际角色加载和基础动作验证的稳定测试包交付。瞄准时，Karin 较大的头部与长发会比 47 原模型
遮挡更多左侧视野；长发也仍是刚性权重。冲刺时序、翻越/攀爬、拖尸、近战、受击/ragdoll、镜面/过场、
近景 alpha、狭窄空间碰撞和跨地图 LOD 矩阵完成前，仍不得标记为 1.0.0。
