流萤（春日手信）替换「魂」mod · 影之刃零（Phantom Blade Zero）
打包日期：{DATE}（第 1 版）
适用游戏版本：Steam 版 buildid 26367565

【内容】
- 成年魂（普通服装、十年前服装）和序章的少年魂替换为流萤·春日手信（水手服、格子短裙、过膝袜）。
- 体型：游戏里手和前臂固定使用魂的骨骼长度，所以成年形态整体放大约 13%（比 Karin、Lenko 略高），手臂比例和
  Lenko 相当；手做了收窄、变细；腿部从裙摆以下加粗约 10%。序章少年形态保持原大小。
- 物理：短裙、后长发、两侧小马尾、刘海和侧发、上衣胸前（含领结）。短裙有单独的碰撞体，静止时不会被臀部撑起，
  跑动时大腿会把裙片推开。
- 表情：过场动画里有表情和口型；平时游玩会自动眨眼。
- 平时游玩时受击、死亡没有面部表情（原版也没有）。
- 包含醉剑修复：身体模型带有原版的 4 根武器骨骼（weapon_l_child、weapon_r_child、ik_weapon_l_child、
  ik_weapon_r_child），使用醉剑时剑的模型和攻击判定正常。

【与 Karin、Lenko mod 的关系】
- 本 mod 和 Karin 系列（z_KarinPBZ_P.*、z_KarinPT_P.*）、Lenko（z_LenkoPBZ_P.*）替换的是同样的游戏资源，
  不能同时安装。本包的安装脚本会删除 ~mods 里的这些文件。
- 之后想换回其他 mod 时，先运行本包的 uninstall.cmd（或手动删除 z_FireflyPBZ_P.*），再安装那个 mod。

【已知限制】
- 只替换了默认的两套服装。其他服装用的是各自的身体模型，没有替换，换上后头部显示不正常（原版头部已被隐藏）。
- 不同的布料之间不会互相碰撞：动作幅度很大时，长发和短裙可能短暂交叉。
- 手指关节位置由游戏固定（魂的手），手指长度无法改短。
- 过场动画沿用 Karin / Lenko 的做法，没有单独测试；关闭或调低毛发（Groom）质量后，过场里的脸可能轻微闪烁。

【安装】
1. 关闭游戏。
2. 双击 install.cmd。脚本通过 Steam 找到游戏目录，校验包内文件，再复制到
   <游戏目录>\ProjectPBZ\Content\Paks\~mods\
3. 不需要 UE4SS 或其他加载器。

找不到游戏目录时，在本文件夹打开 PowerShell，运行：
   powershell -ExecutionPolicy Bypass -File .\install.ps1 -GameDir "<游戏目录>"
<游戏目录> 是含 ProjectPBZ 文件夹的那一层，例如 ...\steamapps\common\PBZ。
也可以手动安装：把 files 文件夹里的三个 z_FireflyPBZ_P.* 文件复制到上面的 ~mods 文件夹（没有就新建一个），
并删除 ~mods 里的 z_KarinPBZ_P.*、z_KarinPT_P.*、z_LenkoPBZ_P.*（如果有）。

【卸载】
关闭游戏，双击 uninstall.cmd；或者手动删除 ~mods 里的 z_FireflyPBZ_P.pak、z_FireflyPBZ_P.ucas、z_FireflyPBZ_P.utoc。

【查看状态】
   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Check
显示游戏目录、游戏版本，以及 mod 是否已安装、是否与本包一致。

【游戏更新后】
mod 是按 buildid 26367565 打包的，游戏更新后安装脚本会提示版本不一致。如果进游戏崩溃或角色显示异常，
先卸载，再按工作区 PROJECT_STATE.md 里的流程重新构建、打包。

【模型与使用规则】
模型：星穹铁道—流萤·春日手信，模型编辑：流云景，模型版权所属 miHoYo。
按模型的使用规则：请勿二次配布，请勿用于 18 禁、极端宗教宣传、血腥恐怖猎奇、人身攻击等作品，请勿用于商业用途。
本包用上述模型和游戏资源制作，仅供个人使用，请勿公开分发。
