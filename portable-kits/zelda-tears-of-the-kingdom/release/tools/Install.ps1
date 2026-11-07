<#
.SYNOPSIS
  安装 Karin_Original 王国之泪 mod 包（yuzu 系模拟器），可选给最近的存档添加 Karin 套装。
.PARAMETER UserDir
  模拟器 user 目录（含 load / nand / sdmc）。缺省自动查找 %APPDATA%\yuzu 等，找不到会提示输入。
.PARAMETER NoSave
  不修改存档。
.PARAMETER Yes
  不询问，直接给存档添加套装。
#>
[CmdletBinding()]
param([string]$UserDir, [switch]$NoSave, [switch]$Yes)
$ErrorActionPreference = 'Stop'
$TITLE = '0100F2C0115B6000'
$Pkg = Split-Path -Parent $PSScriptRoot

function Find-UserDir {
    foreach ($n in 'yuzu', 'suyu', 'sudachi', 'citron', 'eden', 'torzu') {
        $p = Join-Path $env:APPDATA $n
        if (Test-Path (Join-Path $p 'nand')) { return $p }
    }
    return $null
}

Write-Host '=== Karin_Original 王国之泪 mod 安装 ===' -ForegroundColor Cyan
$running = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '^(yuzu|suyu|sudachi|citron|eden|torzu)' }
if ($running) { throw ("模拟器正在运行（{0}），请先退出。" -f (($running | Select-Object -Expand ProcessName -Unique) -join ', ')) }

if (-not $UserDir) { $UserDir = Find-UserDir }
if (-not $UserDir) {
    Write-Host '没有在 %APPDATA% 找到模拟器数据目录（便携版 yuzu 的 user 文件夹在模拟器 exe 旁边）。'
    $UserDir = (Read-Host '请输入模拟器的 user 目录完整路径（含 load、nand 文件夹）').Trim('"', ' ')
}
if (-not (Test-Path (Join-Path $UserDir 'nand'))) { throw "不是有效的 user 目录（缺少 nand）：$UserDir" }
Write-Host "user 目录：$UserDir"

$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$loadT = Join-Path $UserDir "load\$TITLE"
$bkRoot = Join-Path $UserDir "load\${TITLE}__backup_$ts"   # sibling of the title folder: not loaded as a mod
New-Item -ItemType Directory -Force $loadT | Out-Null
$moved = $false

foreach ($m in Get-ChildItem (Join-Path $Pkg "load\$TITLE") -Directory) {
    $dst = Join-Path $loadT $m.Name
    if (Test-Path $dst) {
        New-Item -ItemType Directory -Force $bkRoot | Out-Null
        Move-Item $dst (Join-Path $bkRoot $m.Name); $moved = $true
        Write-Host "  旧的 $($m.Name) 已移到备份"
    }
    Copy-Item -Recurse $m.FullName $dst
    $n = @(Get-ChildItem $dst -Recurse -File).Count
    Write-Host "  安装 $($m.Name)（$n 个文件）" -ForegroundColor Green
}

$ucSrc = Join-Path $Pkg 'sdmc\UltraCam'
if (Test-Path $ucSrc) {
    $ucDst = Join-Path $UserDir 'sdmc\UltraCam'
    if (Test-Path $ucDst) {
        New-Item -ItemType Directory -Force $bkRoot | Out-Null
        Move-Item $ucDst (Join-Path $bkRoot 'sdmc_UltraCam'); $moved = $true
    }
    New-Item -ItemType Directory -Force (Split-Path $ucDst) | Out-Null
    Copy-Item -Recurse $ucSrc $ucDst
    Write-Host '  安装 UltraCam 设置（sdmc\UltraCam）' -ForegroundColor Green
}
if ($moved) { Write-Host "原有的同名 mod / 设置已备份到：$bkRoot" }

# LayeredFS: for the same file the folder whose name sorts first wins
$ours = @(Get-ChildItem (Join-Path $Pkg "load\$TITLE") -Directory | Select-Object -Expand Name)
$others = @(Get-ChildItem $loadT -Directory | Where-Object { $ours -notcontains $_.Name })
if ($others.Count) {
    Write-Host ''
    Write-Host ('该游戏还有其他 mod：{0}' -f (($others | Select-Object -Expand Name) -join ', ')) -ForegroundColor Yellow
    $before = @($others | Where-Object { [string]::CompareOrdinal($_.Name, '00_Karin_Original') -lt 0 })
    if ($before.Count) { Write-Host ('  注意：{0} 排在 00_Karin_Original 前面，若也改了 Armor_1061 / RESTBL 会盖过本 mod。' -f (($before | Select-Object -Expand Name) -join ', ')) -ForegroundColor Yellow }
}

if (-not $NoSave) {
    Write-Host ''
    $ans = if ($Yes) { 'y' } else { Read-Host '给最近的存档添加一套 Karin 装备（火焰头饰 / 火焰服 / 火焰裤子）？[Y/n]' }
    if ($ans -eq '' -or $ans -match '^[yY]') {
        & (Join-Path $PSScriptRoot 'Give-KarinArmor.ps1') -UserDir $UserDir
    }
}
Write-Host ''
Write-Host '完成。启动模拟器，在游戏属性 → 附加组件里确认这些 mod 已勾选。' -ForegroundColor Cyan
