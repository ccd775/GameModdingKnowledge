# 兼容命令入口

这两个 PowerShell 包装器转到 [modkit.py](../portable-kits/common/modkit.py) 的统一实现，避免重复维护。初始化的 Game 参数使用目录 ID，例如 left-4-dead-2。hash_manifest 对目录工作，输出 v2 清单，拒绝空目录和输入树内的 manifest。

推荐直接读 [公共运行说明](../portable-kits/common/README.md) 使用 Python CLI。发布检查为 [check_repository.py](../tools/check_repository.py)，需要安装 requirements.txt。
