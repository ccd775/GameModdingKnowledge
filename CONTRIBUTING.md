# Contributing

新增案例时请遵循每个游戏目录的 README 和现有文档格式。

每条重要结论至少写明：

- 游戏 build、工具版本和证据等级；
- 输入/输出的身份摘要或哈希（不要上传私有 payload）；
- 适用范围，以及明确的未观察场景；
- 被拒绝或被 supersede 的旧假设；
- 可复现的最小命令或检查步骤。

提交前运行：

```powershell
python -m pip install -r requirements.txt
python -B tests/test_portable_tools.py
python -B tests/test_export_portability.py
powershell -NoProfile -ExecutionPolicy Bypass -File tools/validate_public_tree.ps1
```

修改迁移脚本后同步 PROVENANCE.json 中的 portable_sha256；original_sha256 保持原始取证值。测试使用合成数据，禁止把游戏/模型 payload 放入 fixtures。
