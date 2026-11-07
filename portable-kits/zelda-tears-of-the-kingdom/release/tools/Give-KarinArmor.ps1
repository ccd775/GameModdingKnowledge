<#
.SYNOPSIS
  给王国之泪存档的防具包添加一套装备（默认 Armor_1061 火焰头饰 / 火焰服 / 火焰裤子 = 本 mod 替换的 Karin 套装）。

.DESCRIPTION
  直接修改 progress.sav（yuzu 系模拟器：nand\user\save\0000000000000000\<用户ID>\0100F2C0115B6000\slot_XX）。
  思路参考 TOTK-SaveGame-Editor（把 64 字节的装备名写进防具包数组），但：
    - 按哈希表定位防具名数组（String64Array，hash 0x754E8549，300 格），不依赖固定偏移；
    - 只写空格子，已有的装备跳过，不会覆盖玩家已有防具；
    - 同时把 IsGet.<装备> / IsGetAnyway.<装备> 置 1（与正常拾取一致）；
    - 修改前把整个 slot 文件夹备份到 -BackupDir；模拟器运行中拒绝修改。
  progress.sav 没有校验和，改完直接生效；读档后在防具栏即可看到。

.PARAMETER UserDir
  模拟器的 user 目录（含 nand、load、sdmc 的那个）。缺省时自动查找 %APPDATA%\yuzu 等。
.PARAMETER Slot
  要修改的存档槽（0-5）。缺省 = 最近写入的槽（即“继续游戏”会读的那个）。
.PARAMETER AllSlots
  所有槽都加。
.PARAMETER Items
  要添加的装备 ID。
.PARAMETER DryRun
  只报告，不写文件。
.PARAMETER SavePath
  直接指定一个 progress.sav（测试用；仍会备份）。
#>
[CmdletBinding()]
param(
    [string]$UserDir,
    [int]$Slot = -1,
    [switch]$AllSlots,
    [string[]]$Items = @('Armor_1061_Head', 'Armor_1061_Upper', 'Armor_1061_Lower'),
    [switch]$DryRun,
    [string]$SavePath,
    [string]$BackupDir = (Join-Path (Split-Path -Parent $PSScriptRoot) 'save_backup')
)
$ErrorActionPreference = 'Stop'
$TITLE = '0100F2C0115B6000'
$ARMOR_NAME_HASH = [uint32]1968080201   # 0x754E8549
$TYPE_BOOL = 0; $TYPE_STRING64_ARRAY = 17

function Get-Murmur3([string]$s) {
    # MurmurHash3 x86_32, seed 0 (TotK GameData flag-name hash). uint64 arithmetic + masks (PS 5.1 safe).
    $M = [uint64]4294967295
    $key = [Text.Encoding]::UTF8.GetBytes($s); $h = [uint64]0; $c1 = [uint64]3432918353; $c2 = [uint64]461845907
    $n = [Math]::Floor($key.Length / 4)
    for ($i = 0; $i -lt $n; $i++) {
        $k = [uint64][BitConverter]::ToUInt32($key, $i * 4)
        $k = ($k * $c1) -band $M; $k = (($k -shl 15) -bor ($k -shr 17)) -band $M; $k = ($k * $c2) -band $M
        $h = $h -bxor $k; $h = (($h -shl 13) -bor ($h -shr 19)) -band $M; $h = ($h * [uint64]5 + [uint64]3864292196) -band $M
    }
    $k = [uint64]0; $t = $key.Length - $n * 4
    for ($i = $t - 1; $i -ge 0; $i--) { $k = ($k -shl 8) -bor [uint64]$key[$n * 4 + $i] }
    if ($t -gt 0) { $k = ($k * $c1) -band $M; $k = (($k -shl 15) -bor ($k -shr 17)) -band $M; $k = ($k * $c2) -band $M; $h = $h -bxor $k }
    $h = $h -bxor [uint64]$key.Length
    $h = $h -bxor ($h -shr 16); $h = ($h * [uint64]2246822507) -band $M; $h = $h -bxor ($h -shr 13); $h = ($h * [uint64]3266489909) -band $M; $h = $h -bxor ($h -shr 16)
    return [uint32]$h
}

function Find-UserDir {
    $c = @()
    foreach ($n in 'yuzu', 'suyu', 'sudachi', 'citron', 'eden', 'torzu') { $c += (Join-Path $env:APPDATA $n) }
    foreach ($p in $c) { if (Test-Path (Join-Path $p 'nand\user\save')) { return $p } }
    return $null
}

function Edit-Save([string]$path) {
    $b = [IO.File]::ReadAllBytes($path)
    if ($b.Length -lt 0x40 -or [BitConverter]::ToUInt32($b, 0) -ne 0x01020304) { throw "不是王国之泪 progress.sav：$path" }
    $end = [BitConverter]::ToUInt32($b, 8)
    # hash table: 8-byte entries (hash, value) from 0x20; hash 0 = type-section marker (value = type index)
    $sec = -1; $arr = $null; $arrCands = @(); $bools = @{}
    for ($o = 0x20; $o -lt $end; $o += 8) {
        $h = [BitConverter]::ToUInt32($b, $o); $v = [BitConverter]::ToUInt32($b, $o + 4)
        if ($h -eq 0) { $sec = [int]$v; continue }
        if ($sec -eq $TYPE_BOOL) { $bools[$h] = $o }
        elseif ($sec -eq $TYPE_STRING64_ARRAY) { if ($h -eq $ARMOR_NAME_HASH) { $arr = $v } else { $arrCands += $v } }
    }
    function Read-Names([uint32]$off) {
        $cnt = [BitConverter]::ToUInt32($b, $off); $names = New-Object string[] $cnt
        for ($i = 0; $i -lt $cnt; $i++) { $names[$i] = [Text.Encoding]::UTF8.GetString($b, $off + 4 + $i * 64, 64).Split([char]0)[0] }
        return , $names
    }
    if ($null -eq $arr) {   # fallback: the String64Array whose filled entries are all Armor_*
        foreach ($v in $arrCands) {
            $nm = Read-Names $v; $f = @($nm | Where-Object { $_ })
            if ($nm.Length -ge 100 -and $f.Count -gt 0 -and @($f | Where-Object { $_ -notlike 'Armor_*' }).Count -eq 0) { $arr = $v; break }
        }
    }
    if ($null -eq $arr) { throw '找不到防具包数组（存档版本不支持？）' }
    $names = Read-Names $arr
    $filled = @($names | Where-Object { $_ }).Count
    Write-Host ("  防具包：{0}/{1} 格已用" -f $filled, $names.Length)
    $changed = $false
    foreach ($it in $Items) {
        $idx = [Array]::IndexOf($names, $it)
        if ($idx -ge 0) { Write-Host "  已有  $it（第 $idx 格）" }
        else {
            $idx = [Array]::IndexOf($names, '')
            if ($idx -lt 0) { Write-Warning "防具包已满，无法添加 $it"; continue }
            $buf = New-Object byte[] 64; $nb = [Text.Encoding]::UTF8.GetBytes($it); [Array]::Copy($nb, $buf, [Math]::Min(63, $nb.Length))
            [Array]::Copy($buf, 0, $b, $arr + 4 + $idx * 64, 64); $names[$idx] = $it; $changed = $true
            Write-Host "  添加  $it -> 第 $idx 格"
        }
        foreach ($flag in "IsGet.$it", "IsGetAnyway.$it") {
            $h = Get-Murmur3 $flag
            if ($bools.ContainsKey($h)) {
                $o = $bools[$h]
                if ([BitConverter]::ToUInt32($b, $o + 4) -ne 1) { [Array]::Copy([BitConverter]::GetBytes([uint32]1), 0, $b, $o + 4, 4); $changed = $true; Write-Host "        $flag = 1" }
            }
        }
    }
    return @{ Changed = $changed; Bytes = $b }
}

# ---------------------------------------------------------------- main
$running = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(yuzu|suyu|sudachi|citron|eden|torzu|Ryujinx)' }
if ($running -and -not $DryRun) { throw ("模拟器正在运行（{0}），请先完全退出再改存档，否则游戏下次保存会覆盖修改。" -f (($running | Select-Object -Expand ProcessName -Unique) -join ', ')) }

if ($SavePath) { $targets = @(Get-Item -LiteralPath $SavePath) }
else {
    if (-not $UserDir) { $UserDir = Find-UserDir }
    if (-not $UserDir -or -not (Test-Path (Join-Path $UserDir 'nand\user\save'))) { throw '找不到模拟器 user 目录，请用 -UserDir 指定（含 nand 文件夹的那个 user 目录）。' }
    $saves = @(Get-ChildItem (Join-Path $UserDir 'nand\user\save') -Recurse -Filter progress.sav -ErrorAction SilentlyContinue |
               Where-Object { $_.FullName -match "\\$TITLE\\slot_\d\d\\progress\.sav$" } | Sort-Object LastWriteTime -Descending)
    if ($saves.Count -eq 0) { throw "在 $UserDir 下没有找到王国之泪存档。" }
    if ($AllSlots) { $targets = $saves }
    elseif ($Slot -ge 0) { $targets = @($saves | Where-Object { $_.Directory.Name -eq ('slot_{0:D2}' -f $Slot) }) }
    else { $targets = @($saves[0]) }
    if ($targets.Count -eq 0) { throw "没有找到 slot_$('{0:D2}' -f $Slot)。" }
}

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
foreach ($t in $targets) {
    Write-Host ("{0}  （{1}）" -f $t.FullName, $t.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))
    $r = Edit-Save $t.FullName
    if (-not $r.Changed) { Write-Host '  无需修改。'; continue }
    if ($DryRun) { Write-Host '  [DryRun] 未写入。'; continue }
    $bk = Join-Path $BackupDir ("{0}_{1}" -f $t.Directory.Name, $ts)
    New-Item -ItemType Directory -Force $bk | Out-Null
    Copy-Item (Join-Path $t.DirectoryName '*') $bk -Force
    [IO.File]::WriteAllBytes($t.FullName, $r.Bytes)
    Write-Host "  已写入。原存档备份在：$bk"
}
