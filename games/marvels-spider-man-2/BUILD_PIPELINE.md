# 构建流水线

脚本都在 [便携包](../../portable-kits/marvels-spider-man-2/README.md) 的 `scripts/` 里，环境变量和依赖见那里的 README。
需要准备三样东西：游戏目录（`SM2_GAME`）、ALERT 的 `dat1lib`（`SM2_ALERT`）、源 VRM（`SM2_VRM`）。
中间产物写在工作目录（`SM2_WORK`）下的 `native/`、`reports/`、`build_sig*/`、`builds/`。

## 1. 索引与提取

```powershell
python -B sm2_index.py                        # 一次：dagstr 名字 -> toc 资产表（native/asset_index.json）
python -B sm2_find.py "hero_spiderman_.*\.model"   # 按正则查资产
python -B sm2_extract.py <资产路径>             # 解出原版资产到 native/
python -B suit_models.py                      # 战衣链（reward loadout -> loadout -> vanity -> model）-> reports/suit_models.json
python -B survey_targets.py                   # 目标模型 + 骨架签名 + looks -> reports/targets.json
```

## 2. 批量构建（v1 的基础部分）

```powershell
python -B sm2_batch.py --refit --face --out ../builds/t14_karin_static.stage
```

1. 每种骨架签名挑一个代表模型，跑一次 `sm2_karin_geo.py` 拟合（[角色拟合](CHARACTER_FIT.md) §1）。已有缓存就复用，`--refit` 强制重跑。
2. 贴图（4 张）+ 材质（1 个）+ 108 个目标模型 + 3 个头模型写成一个 `.stage`。
3. `--face`：战衣的 `mask` look 放静态的 Karin 脸，三个头模型换成绑好面部骨骼的 Karin 脸。
4. `--dyn`：链保留为 `karin_*` 关节，并且每个模型加动力学段。只用于试验（T6–T11），因为战衣里的动力学只跑 1 秒（[物理](PHYSICS.md) §3）。

## 3. 物理载体

两个载体脚本都读 `build_sig_dyn/` 里带链关节的拟合，所以先跑一次 `python -B sm2_batch.py --refit --dyn --face --out <任意>.stage`。只需要它生成的拟合，这次构建出的 `.stage` 本身不用。

```powershell
# v1：蜘蛛猫背包挂件（Miles 一套战衣）
python -B sm2_prop_test.py --base ../builds/t14_karin_static.stage --out ../builds/t17_prop_soft.stage [--delta ../builds/t17_delta.stage]
# v2：头部载体，覆盖全部 91 套带面罩战衣（约 20 min，91 个身体逐个去链）
python -B sm2_head_carrier.py --base <v1.stage> --out ../builds/v2.stage [--delta ../builds/v2_delta.stage] `
    --never-cull --joint-bsphere 1.0 --map-body --masked --blank-prop `
    --name "Karin Original (Peter & Miles, all suits) v2" --description "..."
```

- `--delta` 另外写一个只含改动资产的小包，安装成 `install base.stage delta.stage`，测试时不用每次重传 70 MB。
- `sm2_head_carrier.py` 的选项是按试验逐个加的，可以单独开关来复现每一步：
  - `--never-cull`：头 actor 打开 NeverCull（T21）；
  - `--joint-bsphere`：放大载体的关节包围球（T21）；
  - `--map-body`：HeadManager 映射补上胯部三关节（T22）；
  - `--masked`：91 个战衣身体去链（T23）；
  - `--blank-prop`：蜘蛛猫背包网格全部退化（T23）；
  - `--cat-actor`：把头 actor 换成猫挂件式的 actor（T20，已证伪）。
- `--masked` 读工作目录里的 `reports/masked_suits.json`（`{"models": [模型路径, …]}`）。没有脚本自动生成它，也可以用多个 `--suit` 代替。
- 去链的战衣列表来自 loadout 表：每个 loadout 的头 actor 都是 `hma_hed_base` 的战衣模型（本项目为 91 个，没有混用）。
  换 build 后要重新生成这张表。

## 4. 离线闸门（每个候选都跑）

```powershell
python -B sm2_verify_stage.py <stage> --sheet ../reports/<名>_readback.png  # 权重和、0x80、顶点到主关节距离、LOD 共用一块
python -B sm2_verify_face.py <stage>                                       # 面罩脸 vs 头模型脸、面部权重
python -B test_dyn_model.py <stage>                                        # 关节表 / Lookup / 层级 / 镜像 / 动力学段读回
python -B test_dyn_roundtrip.py                                            # 改了 i30_dynamics 后必跑：原版逐字复现
python -B test_actor_roundtrip.py [--all]                                  # 改了 i30_actor 后必跑：actor 逐字节往返
python -B sm2_pose_check.py ../build_sig_dyn/<签名>/karin_geo.npz --png <图>    # 蹲 / 栖 / 坐 / 跨步的裙子穿插率
```

- 三个检查都要 0 bad：`sm2_verify_stage`、`test_dyn_model`、`sm2_verify_face`。
- 增量包与完整包要逐资产比较：同一个资产的字节必须相同。
- 改了 actor 后，`i30_actor_edit.verify` 重新解码，检查计数、偏移、哈希和引用表；未改动的组件必须与原来逐字段相同。

## 5. 打包与安装

```powershell
python -B sm2_install.py --game <游戏目录> install <a.stage> [<b.stage> ...]   # 每次都从 toc.BAK 重来
python -B sm2_install.py --game <游戏目录> status
python -B sm2_install.py --game <游戏目录> uninstall
```

发行包的结构和发布前的演练见 [验证与发布](VALIDATION_AND_RELEASE.md) §3。

## 6. 测试机循环（本项目的做法）

- 本机构建，然后用 `scp` 传到测试机，**核对 SHA-256 后**再安装。远程链路在 70 MB 传输中途断过。
- 安装前确认游戏没在运行；从 SSH 只做安装和查询，游戏由用户自己启动（SSH 在 session 0，从那里启动的游戏看不见）。
- 安装后在 toc 里查改动资产所在的归档（应为 `d\mods\mod<i>`），确认装上的确实是新包。
- 一版只让一类改动进实机，每次的结论都写进项目的 PROJECT_STATE。
