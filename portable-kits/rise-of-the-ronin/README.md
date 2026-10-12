# 浪人崛起便携工具

方法、合同和案例见 [游戏知识](../../games/rise-of-the-ronin/README.md)。
这里的脚本都从项目脚本整理而来：去掉了本机路径和项目常量，改成命令行参数，并用合成数据测试（迁移来源见 [PROVENANCE.json](../PROVENANCE.json)）。

| 脚本 | 职责 | 依赖 |
| --- | --- | --- |
| `g1m_tool.py` | G1M / G1H 读取（块、G1MG 分节、子网格、调色板、骨架、逆绑定）；原地隐藏子网格；塌缩占位三角形；检查绑定是否原生 | 标准库 |
| `g1t_tool.py` | G1T 头、DX12 64 KB tile 与线性互转、导出 DDS、原容器常量填充、比较、mip 链检查 | 标准库 |
| `ktdata.py` | `root.rdb/rdx` + fdata 提取；kidsobjdb / KTID 槽表；共用贴图审计（覆盖了哪些别的模型也在画的贴图） | 标准库 |
| `leg_weights.py` | 从原版腿建参考；按原版分段重新分配某个子网格的腿部权重并追加原生绑定；回读与离线姿势检查 | numpy、scipy |
| `shader_dump.py` | 把原生 shader 包拆成 DXIL；给出 dxc 时反汇编像素、顶点和蒙皮顶点着色器 | 标准库（可选 dxc） |

```powershell
python -m pip install -r requirements.txt -r portable-kits/rise-of-the-ronin/requirements.txt
$K = 'portable-kits/rise-of-the-ronin/scripts'
$G = '<游戏目录>/fdata_package_dx12'

# 盘点：一个模型的槽表，以及 mod 的覆盖与游戏原文件比较
python -B $K/ktdata.py slots --game-data $G --model 0x65152725 --mod-root <包>/RONPATCHER/root
# 共用贴图审计：改过、又被别的可见模型使用的贴图排在最前
python -B $K/ktdata.py usage --game-data $G --mod-root <包>/RONPATCHER/root `
    --own-models 0x65152725,0x8DC92828,0xD462CD01,0x4BA258DF,0x32460701,0x6277D7A9 --output usage.json
# 取原版文件
python -B $K/ktdata.py extract --game-data $G --hash 0x1E76FD2D --hash 0x4BA258DF --output originals

# 贴图
python -B $K/g1t_tool.py info originals/0x1e76fd2d.g1t
python -B $K/g1t_tool.py constant <原版>.g1t --rgba 8,150,232,255 --output fixed/<同名>.g1t
python -B $K/g1t_tool.py constant <原版>.g1t --float 1.0 --output fixed/<同名>.g1t
python -B $K/g1t_tool.py dds <文件>.g1t --mip 0 --output view.dds   # 再用 texconv 转 PNG
python -B $K/g1t_tool.py mips <mod 文件>.g1t --reference <原版>.g1t

# 模型
python -B $K/g1m_tool.py info 0x65152725.g1m --json info.json
python -B $K/g1m_tool.py check-binds 0x65152725.g1m --palette 5
python -B $K/g1m_tool.py hide originals/0xb24cac84.g1m --all --output root/0xb24cac84.g1m   # 清空玩家女性脸
python -B $K/g1m_tool.py collapse-placeholders 0x4ba258df.g1m --output fixed/0x4ba258df.g1m

# 腿：参考 → 应用 → 回读
python -B $K/leg_weights.py reference --body originals/0x4ba258df.g1m `
    --wear originals/0x32460701.g1m originals/0x6277d7a9.g1m --skeleton <模板>/0x65152725.g1m --output leg_ref.npz
python -B $K/leg_weights.py apply <模板>/0x65152725.g1m --submesh 6 --reference leg_ref.npz --output new/0x65152725.g1m
python -B $K/leg_weights.py apply <模板>/0x8dc92828.g1m --submesh 7 --reference leg_ref.npz `
    --reference-skeleton <模板>/0x65152725.g1m --output new/0x8dc92828.g1m
python -B $K/leg_weights.py check <模板>/0x65152725.g1m new/0x65152725.g1m --submesh 6

# 着色器（蒙皮规则）
python -B $K/shader_dump.py <游戏目录>/shader_dx12/0x00b6c7f0.file --output shader-audit --dxc <Windows SDK>/dxc.exe
```

所有写文件的命令在目标已存在时都会拒绝。用 `--help` 查看每个子命令的参数。

## 已验证的等价性

用项目留下的模板和 10-04 发布的成品对照（Python 3.14.0、numpy 2.5.2、scipy 1.18.0）：

- `leg_weights.py reference` 在三个原版模型上取出的 59097 个参考顶点，作为集合与项目的 `leg_ref.npz` 逐值相同。
- `leg_weights.py apply` 原地重做 20260916a 的 651 sub6，得到的每个顶点的权重、调色板和追加的绑定，都与发布的 20261004a 相同。
  - 8DC sub7 有 2 个顶点相差一个量化步长（2^-11），原因是两边计算骨架世界矩阵的浮点误差不同；调色板和绑定相同。
  - 回读指标与项目记录一致：静止姿态偏移 0.00198 / 0.0065；弯脚踝 35° 时，脚的平均位移从 0 变为 5.5 左右。
- `g1t_tool.py constant` 写出的 5 张 SHADING / BC5 修复，与发布包逐字节相同；对 `0x1E76FD2D` 写入 0.0 时，改动的正好是上游 mod 改过的 +0x3A / +0x3B 两个字节。
- `g1m_tool.py` 读出的原版 4BA 和绑腿的逆绑定，与骨架逆矩阵的误差不超过 0.007（例外见技术合同 §6）。G1H 能列出全部 41 个嵌入模型。

## 边界

- `ktdata.py` 在合成数据上测过：存储、两种 zlib 分块、两种 RDB 尾部、kidsobjdb、KTID、两个模型共用一张贴图。
  - 它的解析逻辑直接沿用项目里在真实数据上用过的代码（全游戏 KTID 扫描得出 1102 个模型的结论），但便携版本身没有在游戏数据上重跑过：整理时游戏未安装。
- `leg_weights.py` 只处理 8 骨、存 7 个以上权重的顶点缓冲，并且拒绝改动和别的可见子网格共用的顶点。默认的骨链、踝部过渡高度和姿势都是浪人女性骨架的数值。
- 新几何（从源模型构建）仍需 gust_stuff 导出 / 导入和 Blender。项目的 Karin_Original 构建脚本按 Karin 的网格名和比例写死，没有收进来，方法写在[角色替换](../../games/rise-of-the-ronin/CHARACTER_REPLACEMENT.md) §2。
- 不附带任何游戏文件、加载器或 mod 资源。
