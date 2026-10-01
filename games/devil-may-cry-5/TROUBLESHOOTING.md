# 排障手册

## 症状定位表

| 症状 | 成因 | 处理 | 证据级 |
| --- | --- | --- | --- |
| 标题画面里角色背光一侧整片发黑（Nero、V 像剪影） | Env_Emissive 用 albm 的 alpha 控制自发光；alpha 按「金属度」填了 0 | albm alpha 填 255 | `runtime-load-pass`（标题画面 A/B：换 PT albm、换 alpha 255 版都恢复亮度），之后随包被用户接受 |
| 平坦区域出现面片感，或法线整体倾斜 | NRMR 按 sRGB 编码（PT 包就是这样），128 被解码成非中性值 | NRMR 用 BC7_UNORM，tex 头 `0x500` | `offline-accepted`（与原生格式对照；随 v1.0 一起加载正常） |
| 裙子内外层闪烁 | 继承了 PT MDF 的双面位，单面源模型的内外层几乎重合 | 清掉使用图集的材质的 bit0 | 随 v1.0 一起被接受 |
| 衣褶、鞋底、缝线处法线发糊 | RE 导出器每个顶点只保留第一个角的法线 | 在法线不连续（> 2°）的边上拆顶点，再写回自定义法线 | `offline-accepted` |
| 皮肤局部发黑或发亮 | 源 `body_2` 的自定义法线损坏（零向量角、朝内） | 皮肤改用平滑几何法线 | `offline-accepted` |
| 实战中站立、跑动时大腿和臀部从裙子后面露出 | PT 下半身胶囊太细（0.08，在骨轴上），臀部没覆盖；裙 setting 重力 −20、回弹 0.007 | 按网格表面拟合胶囊，加骨盆胶囊；裙 setting 与角度限制收紧（[chain 物理](CHAIN_PHYSICS.md) §4） | `runtime-confirmed`（v1.1） |
| 小飘带一出生就被弹飞或抖动 | 飘带节点静止时就嵌在身体胶囊里 | 这类节点关碰撞 | `offline-accepted` |
| Blender 预览全黑 | 贴图按预乘 alpha 解释 | 图像 `alpha_mode = 'NONE'` | `offline-accepted` |
| Blender 无界面导入 / 导出时崩溃（`EXCEPTION_ACCESS_VIOLATION`） | RE Mesh Editor 调用 `wm.console_toggle()` | 在工作副本里把这一调用改成 `pass` | 工具层 |
| 导出后约 18% 的法线变了 | Blender 4.0 重导会重算自定义法线 | 原样转换时把源网格的法线 / 切线流搬回去，再断言一致 | `offline-accepted` |
| RE Mesh Editor 写出的 MDF 加载异常 | 它的写出器不能往返 v10 | 用只追加、整体平移偏移的最小改动编辑器 | `offline-accepted` |
| 自动化时 Fluffy 不响应点击，或装了又卸 | 点击太快被忽略；双击切换两次 | 用 200 ms 拖动来点，每次只点一下，然后读 `installed.ini` | 工具层 |
| 替换 Fluffy 的 zip 时报「文件被占用」 | Fluffy 占用正在预览的 zip | 先关 Fluffy，换完再启动 | 工具层 |
| 自测时进入了实战 | 在标题画面按了 Enter（继续存档） | 只关启动弹窗；实战交给用户 | 用户反馈 |

## 已被证伪的捷径

- **「标题画面发黑是物理或网格的问题」**：换成空 chain、换成几何法线版网格，都没有改善；只有换 albm 才改善。
- **「把 PT 链原样套到新服装上」**：PT 的下半身胶囊是为另一套服装设计的，罩不住 Karin_Original 的臀部和大腿
  （54% 顶点在碰撞范围外）。
- **「三个身体共用一份 chain」**：骨盆胶囊挂在 Hip 上，三套网格的 Hip bind 不同。被 v1.1 的「每个身体一份」取代
  （supersedes v1.0）。
- **「为了 1.5 cm 余量把骨盆胶囊再放大一点」**：会把后侧裙片在静止时顶起 1.7 cm，改变外形。取余量 0.7 cm 的版本。

## 反复出现的元错误

- **只看传输成功，不核对结果**：PowerShell 变量名不分大小写，`$W`（目录）被循环变量 `$w` 覆盖，复制悄悄失败。
  复制后一律核对哈希。
- **参考 mod 的结论凭印象写**：曾经以为 PT Dante 没改 fbxskel，实测发现两个 PT mod 都按网格 bind 改写过。
  写进文档之前要用数据复核。
