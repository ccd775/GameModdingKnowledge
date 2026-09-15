# 可复用脚本

这些是新写的参数化小工具，不是把Sindel脚本换成任意角色名就能工作的构建器。Python 3.10+；Atlas工具需Pillow。先运行 `python -B test_tools.py`。不包含游戏或私有模型fixtures。

Windows另外运行 `./test_deploy.ps1` 做合成目录部署检查，不修改真实游戏。测试范围见 [QA记录](../QA.md)。

## 1. 只读清单和差异

```powershell
python -B mk1_checks.py inventory ../Output/Candidate
python -B mk1_checks.py diff ../Native/raw/chunks ../Work/raw/chunks --allow BODY_CHUNK_ID --allow HEADER_CHUNK_ID
```

相对路径精确匹配；新增/删除也必须在allow中，否则exit1。不默认忽略container header，不把所有变化都自动加allow。inventory记录实际内容hash；输出可保存到工程报告，但不要把私人路径或payload上传公共仓库。

## 2. 四张图集拼合

```powershell
python -B atlas_quadrants.py ../Work/Atlas8192.png --pages Skin.png Hair.png ClothingA.png Accessories.png
```

输入顺序对应UV左下、右下、左上、右上。输出PNG和`.atlas.json`是新文件，禁止覆写。工具只拼图并校验RGBA，**不会修改Blender UV，也不会Cook**。模型的每一个loop按manifest象限转换 `(oldUV+q)/2`，合并材质后独立重开/FBX检查。未授权8192或目标不支持时先讨论选择，不能靠本工具容量上限推定批准。

## 3. 源哈希锁定的native render索引隐藏

```powershell
python -B mk1_checks.py hide-indices ../Native/hair.chunk ../Work/hair-hidden.chunk --plan ../Work/hair-index-plan.json
```

plan示例结构（示例数字不是任何真实角色offset）：

```json
{
  "source_sha256": "REPLACE_WITH_64_HEX",
  "buffers": [
    {"offset": 100, "width": 2, "count": 6, "vertex_count": 4, "buffer_sha256": "REPLACE_WITH_64_HEX"}
  ]
}
```

输入buffer_sha256来自独立提取并审核的原始索引字节；先核对PSK/LOD及三角形数据，再填plan。工具还检查native MultiSize的9字节头、范围、重叠和索引上界，仅折叠render索引，未触及其它字节。它不能证明覆盖了全部LOD，也不登记容器新增package/store；那些仍需专用打包脚本。

## 4. 完整三件套部署

```powershell
./deploy_trio.ps1 -SourceDirectory ../Output/Good -SourcePrefix a_example_P -GamePaksPath $gamePaks -InstalledPrefix a_example_P -ExpectedHashesJson ../Output/hashes.json -BackupRoot ../Backups
```

默认为只读预检，通过后**显式追加 `-Install`**才写入。hashes.json必须有`pak`、`ucas`、`utoc`三个实际64hex hash。游戏必须退出；备份在Paks外；prefix仅允许custom a_/z_；不允许partial destination trio。旧文件先完整备份，写入失败尝试恢复。不会复制global、修改Steam/Engine.ini或启动游戏。

复用旧备份做回滚时，源prefix是当时installed prefix，expected hashes使用备份记录中的OldHash；再预检/安装。完整安装不是跨文件系统原子操作，因此禁止游戏/其它部署任务在复制期间启动或写入。安全测试覆盖正常安装、hash拒绝和路径拒绝；无法以单元测试证明所有断电/磁盘损坏情况下恢复成功。

## 5. 完整 PSK 索引匹配 → 只读隐藏计划

```powershell
python -B psk_index_plan.py ../Native/face.chunk ../Work/face-plan.json --psk ../Native/face.psk
python -B mk1_checks.py hide-indices ../Native/face.chunk ../Work/face-hidden.chunk --plan ../Work/face-plan.json
```

第一步不修改 chunk；只在输出不存在时创建计划。完整比较 PSK wedge triangle 流与 native MultiSize buffer（16/32 位、三角顶点排列差异），不接受 prefix96/count/max 相同。第二步必须在人工审核范围后执行。计划含原始 chunk、每段 buffer、独立 PSK 哈希。

有多个真实导出的 LOD 时重复 `--psk`；任意提供的 PSK 无完整匹配则失败。工具不会猜缺失 LOD，也不能证明候选范围在游戏里被使用或原生其他流无需隐藏。匹配同一流的多段原生缓冲区会全部列出，需结合资源结构审核。只支持已识别 ActorX wedge/face 结构，未知格式拒绝。

运行 `python -B test_psk_index_plan.py`：覆盖重复缓冲、winding、32 位、前缀假阳性、损坏文件/越界、未匹配 LOD，以及与 hash-locked 补丁器的集成。测试通过不能替代实机验收。

## 6. 重定向数学算子与故障回归

`retarget_math.py`为标准库纯函数，无游戏路径、骨名、密钥、文件写入或自动部署：

- `fit_segment`：仅轴向拟合目标骨长，横截面尺度由调用方明确传入。
- `fit_terminal`：头部/末端必须明确传入尺度，无隐式identity回退。
- `pelvis_point`、`pelvis_weight`：共同髋中点空间场与C1高度过渡；极端收窄会翻折则拒绝。
- `atlas_pixel_rect`：可变尺寸UV页到PNG矩形的统一转换。

所有几何输入先统一坐标和单位；骨盆函数使用X横向/Z朝上。调用方仍负责源求值、骨架映射、服装/人体与独立附属物的归属划分、真正的目标关节测量及最终验证。参考 [检查说明](../RETARGET_CHECKS.md)，不要用纯函数通过代替实际角色通过。

运行 `python -B test_retarget_math.py`：6组，覆盖长脊柱不扩张体宽、旋转/反向骨轴、显式头部尺度、髋宽/裤子高度与翻折拒绝、过渡边界、2048小页定位。合成测试没有模型/游戏fixtures。

## 7. 头颈局部位移算子

`neck_fit.neck_point(point, neck_z=..., head_z=..., shift=..., head_weight=..., neck_weight=...)` 使用显式Z-up坐标、统一单位与已审核归一化权重，无默认缩短比例、不选择模型区域、不读写文件。纯Head（包括长发低处）统一平移，Neck使用C1过渡，其它点保持不动；拒绝非有限参数、错误权重及简化纯Neck场可能翻折的参数。它不证明变化权重的完整Jacobian或游戏动作安全。

运行 `python -B test_neck_fit.py`：覆盖头/低处长发刚性平移、保护集合与混合权重、颈根/顶部边界及导数、米/厘米等价、非法输入拒绝。完整选区、接缝、增量打包与证据要求见 [头颈指南](../NECK_PROPORTIONS.md)。现有Wasakura案例脚本尚未改成调用此函数；这是独立提取的参考实现，不是对游戏包的重新构建。

## 角色专属脚本的边界

Riptide 的 `riptide_native_properties.py`、`patch_ermac_emissive_v7.py`、`package_ermac_v7.py` 与 v4/v5 绑定/验证脚本在本机目标工程 `SOP/v*-evidence` 归档。它们含明确源哈希、命名、二进制布局和旧版依赖，不是通用工具；入口为 Ermac 工程 `SOP/RIPTIDE_PLAYBOOK_HANDOFF.md`。共享 [材质指南](../NATIVE_MATERIAL_PATCHING.md) 提供可复用审计流程，[案例](../cases/RIPTIDE_TRIO.md) 记录运行反馈。本次没有将专用解析器包装成通用 native MI 编辑器。

Karin Y三角色案例新增的源检查、逐指姿势、局部躯干和附件修复、实际容器UV/纹理回读、手杖覆盖撤销均保存在该本机工程的 `scripts/v9`，复用索引是 `PLAYBOOK_HANDOFF.md`。其源路径/对象名单/骨名/阈值与baseline版本硬编码，尚不是此目录内的便携工具；不要直接换角色名执行。算法与边界见 [手部与上半身](../UPPER_BODY_HANDS.md) 及 [Karin Y案例](../cases/KARIN_Y_TRIO.md)。本轮只归档已有脚本和证据，没有新增未经实测的通用绑定器。

下列工作仍需根据目标资源编写/适配，并按文档审计：原生骨架映射、evaluated geometry冻结、统一厘米、比例/鞋袜补偿、UE导入、Cook目录选择、Zen单bundle修正、native refpose恢复、native package/store登记。它们在本机案例归档中保留了确切代码及hash，不能不读就批量执行。

尾巴案例新增 `fix_source_tail.py`、`package_source_tail.py`、`verify_source_tail.py` 和 `deploy_tail_v11.ps1`，仍属于本机限定源/目标/旧基线的脚本，未作为便携一键工具分发。其算法与审核门槛见 [附属物指南](../APPENDAGES.md)。已安装新版后，旧基线检查/输出已存在的拒绝属于正常保护；不能删断言重跑。
