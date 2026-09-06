# RE4R 便携包

先读 [角色 SOP](../../games/resident-evil-4-remake/CHARACTER_REPLACEMENT_SOP.md) 和 [技术合同](../../games/resident-evil-4-remake/TECHNICAL_CONTRACTS.md)。实际附带以下 PAK 工具：

```powershell
python portable-kits/resident-evil-4-remake/scripts/re4_pak_analyze.py hash natives/stm/example.mesh.221108797
python portable-kits/resident-evil-4-remake/scripts/re4_pak_analyze.py list ../MyMod/Ref/reference.pak --candidates ../MyMod/Work/candidate-paths.txt --magic
python portable-kits/resident-evil-4-remake/scripts/re4_pak_analyze.py extract-index ../MyMod/Ref/reference.pak 0 ../MyMod/Work/entry-0.bin
```

路径表每行一个虚拟路径，通过 lower/upper hash pair 匹配。解析器限定 KPKA v4、stored/raw-DEFLATE/zlib 的 Mod 包子集，不处理加密、签名或 Zstandard 官方 PAK。不带 --magic 时仅解析表，提取前检查压缩支持。

Blender 源审计由公共 audit_blend_source.py 提供。Mesh/MDF/Chain 编辑使用外部 [RE 工具](../../references/TOOL_SOURCES.md)，先对当前原生 Mesh 做导入/导出/回读身份测试，再按 consumer slot 分区。保持材质索引、FBXSKEL parent/bind、PFB 双层路径闭包。没有声称复制了全部角色 retarget/Chain builder；agent 按当前源/目标骨架生成项目实现。
