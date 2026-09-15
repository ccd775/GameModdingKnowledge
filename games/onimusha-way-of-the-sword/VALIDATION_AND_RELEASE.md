# 验证与发布

## 1. 加载路线：散装文件是本 build 唯一可用的方式

正式版 build `24769601` 上的实测结论（`runtime-confirmed`）：

- **Mod PAK 不可用。** 游戏拒绝未加密的 Mod PAK，装上会得到 `file looks corrupted`
  启动中止。REFramework 官方 nightly 的 PAK 完整性绕过在本 build 失效，日志里能直接
  看到分诊线索：

  ```text
  Found pak_load_fn @ ..., using it as reference to find sha3_code_start!
  Found vmovups sequence of length 5 at ..., likely sha3_code_start!
  Found sha3_code_start @ ... using vmovups sequence!
  Could not find sha3_rsa_code_end, cannot restore unencrypted paks!
  ```

- **散装文件可用，且默认开启。** 同一份日志里 `LooseFileLoader_Enabled=true` /
  `LooseTextureLoader_Enabled=true`。散装文件不是 PAK，不经过签名校验，**绕开整个
  闸门**。

因此现行安装方式是把 payload 直接铺到游戏根目录下的 `natives/STM/...`。卸载 = 删除
该 `natives` 目录，不覆盖任何官方文件。

验证散装文件是否**真的被采用**：REFramework 会写出一份已加载散装文件清单，逐条核对。
本项目据此确认除过场专用的一个 MDF 外全部生效。

`invariant`：PAK 与 ZIP 照旧构建并保留（供绕过修复后或分发使用），但 README 必须写明
「不要在本 build 上装 PAK」，且**主交付物是散装 ZIP**。

### 若要走 PAK 路线（备用，未关闭）

本项目推导过本 build 的补丁常量（EXE SHA-256、`IMAGE_SIZE`、PAK loader 函数区间、
`sha3_code_start`、SHA3 tail RVA 与 delta）。两个可复用的点：

- 上游的三个 tail 签名在本 EXE 上 **0 命中**，只有本地此前 build 推出的 RAX 形态签名
  命中 —— 签名要按 build 重推，不要指望上游。
- `SHA3_TAIL_DELTA` 必须**运行时实证**：静态读第一条 `vmovups` 会得到偏小的值
  （本例 `0x151` vs 真值 `0x159`），因为真正的起点是**基本块起点**。

补丁必须 build-scoped 且 fail-closed；游戏更新即失效。

## 2. 打包器血统规则

> 每个发行版有**自己的**打包器；所有此前的打包器保持**字节冻结**，使旧版本永远可
> 复现。

本项目已有五个打包器（Demo PAK 版 / 正式版迁移 / 物理版 / 几何修复版 / 阻尼版），彼此
派生但互不覆盖。派生时最容易漏的是**硬编码的自检守卫**（例如
`if STAGE_ROOT.name != "stage_physics": 拒绝清理`）—— 派生后第一次跑就会以
`FAIL: refusing to clean unexpected stage` 暴露，属于设计正确的失败。

## 3. 发布闸门

按依赖顺序，每一道都拦过真实错误：

1. **输入锁**：源模型、donor、原生提取件全部按 SHA-256 锁定。
2. **结构闸门**：对**自己追加生成**的二进制（本项目是 chain2）回读并断言
   `group / setting / node / 字节数` 四元组与数组边界。纯哈希锁挡不住「写了一半但
   哈希被一起更新」。
3. **部署一致性闸门（parity）**：逐文件比对 stage 与游戏 `natives/` 下的散装部署，
   **路径集合双向相等**（多一个文件也算失败）+ 每个文件 SHA-256 相同。
   理由：一个版本能被「冻结」的唯一依据是用户实机跑过；如果发行包和他跑的不是同一堆
   字节，这个冻结就没有意义。
   **这道闸门真的救过一次**：第二套服装的 Mesh 没有跟着更新，只有 `ch001_00` 的三个
   槽更新了 —— 而实机渲染的恰恰是第二套服装。没有它就会发出一个「修了但没生效」的包。
4. **PAK 反解**：只依赖内嵌 manifest 列包/解包，逐 payload 比 SHA-256。
5. **确定性双跑**：完整构建两次，PAK / PAK ZIP / 散装 ZIP 全部逐字节相同。
6. **终端用户校验**：把交付 ZIP 解到干净目录，核对条目数、根目录只有
   `natives/` 与 `README.txt`、无外层包装目录、每个 payload 与部署逐字节相同。

ZIP 要可复现：固定 `date_time`、条目排序、无外层包装目录。

## 4. 运行时状态必须分层写

本项目在这一条上被自己的继承代码咬过：派生的打包器原样打印了
`parity : ... byte-identical to the play-tested deployment` 和
`runtime status : PASS`，而当时那一版**根本没跑过游戏**。

规则：

- 打包器打印的文案、release report 的 `runtime_status`、以及**随包发出的 README**
  三处都要改，漏一处就会向用户撒谎。
- 同一个包里不同改动的验收级别不同时，**逐项分层写**。例如：
  某项「实机确认于某日」；某项「离线已验证，并在同一份部署里运行至今无缺陷报告，
  **但未被单独签收**」；某项「继承自更早版本的实机确认」。
- 「parity 通过」证明的是**部署一致**，不是**玩过**。这两句话不能互相替代。

## 5. 一个不容易发现的验证脚本陷阱

一次性写的校验脚本容易把**版本号写死**。本项目的 ZIP 校验脚本留着上一版的路径，于是
拿旧 ZIP 去比新部署，报了一个假的 `CONTENT MISMATCH`。把版本参数化之后才 PASS。

推论：**校验脚本失败时，先怀疑校验脚本自己指错了对象**，再怀疑产物。

## 6. Blender 无头构建的退出码不可信

`blender --background --python foo.py` 在脚本抛出未捕获异常时**仍然返回 exit 0**，
并照常打印 `Blender quit`。

判定标准要用产物和日志：grep `Traceback`；检查输出目录里的 `BUILD_INCOMPLETE` 标记
是否还在（成功时构建器会删掉它）；或核对 stdout 末尾的 `outputs` JSON 是否给出了全部
槽位的 SHA-256。另外 Blender 的 stdout 有缓冲，中途 `tail` 日志看不到进展**不代表
卡死**。
