# 迁移验证记录

整理日期：2026-09-06。状态：便携脚本组件测试，不是六款游戏新 Mod 的端到端验收。

测试环境：Python 3.12.10、lz4 4.4.5、markdown-it-py 4.0.0；requirements.txt 与实际测试版本一致。

## 实际迁入

19 个原项目 Python 文件；每项在 PROVENANCE.json 中记录源相对位置、原始大小与 SHA-256。保留的是作者在工作区编写的算法/包装器，未复制参考 Mod、模型、纹理、原游戏文件或第三方 DLL。

迁移改动包括：显式输入/输出路径；XBT/PAK 输出防覆盖；VTA 的原 126 骨/31 帧参数化；Forge 的 LZ4 独立于本机 Oodle 路径、field 8 才按需加载已固定 DLL；StudioMDL 新输出检查；RE4 table/payload bounds 检查。格式专属限制仍保留，不将其变成全格式支持声明。

新公共 modkit 提供 init、inventory、verify、doctor、checkpoint、package。旧 PowerShell helper 只保留兼容入口，不再复制到 common 子目录。

## 合成回归

运行 `python -B tests/test_portable_tools.py`：12 项测试通过，使用运行时创建的合成 fixture，没有读取游戏或私人模型。

- 新项目创建、追加断点、重复写入拒绝。
- 完整文件集合/hash 校验、额外文件拒绝、两份 ZIP 字节相等。
- 空输入、越界路径拒绝。
- XBT 提取/注入字节相等、DDS 格式不匹配与覆盖拒绝。
- PRIM/GLB 相同数据通过、顶点改变失败、损坏 GLB 失败。
- 合成 Forge 替换、重复构建相等、独立 extractor 回读；LZ4 不加载 Oodle。
- VTA 使用 1 骨/2 帧的非旧角色合同缩放，保留法线，重复输出拒绝。
- VPK payload CRC 正向/反向和路径隔离。
- KPKA DEFLATE 提取与表/负索引反例。
- HD2 三件套与错误范围检查；LUT header/行内容检查。
- 所有命令行脚本的 --help 启动检查。

未执行：RPKG 实际 TEXT 编译、StudioMDL 实际角色编译、用户 HD2SDK UV 编译、Oodle DLL 分支、六款游戏部署与新运行时测试。原项目的实机验收记录保留为历史证据。

另在 Blender 4.2.23 上创建并保存合成三角网格/UV/材质/shape-key 场景，实际运行迁入的源审计器并核对 JSON。命令使用 --python-exit-code 1，避免脚本异常被 Blender 默认退出码掩盖。合成 Blend 和报告在包外生成，不作为用户模型分发。

## 继续维护

`tests/test_export_portability.py` 另外执行一次覆盖六份导出目录的隔离测试：路径含空格，不使用父仓库代码，逐项检查实际脚本存在，并运行导出包自身的组件测试。未选择游戏的测试显式跳过，所选游戏和公共层通过；六份均通过本地链接、JSON、脚本 provenance 哈希与 Python 语法检查。

修改脚本后重新运行相关测试，更新迁移后的 hash，并检查 standalone 导出。新 build 导致格式失败时记录错误和精确输入身份，修正当前分支，不静默删除检查或复制旧角色常量。
