# Karin PBZ mod: install, uninstall or check. Windows PowerShell 5.1 or PowerShell 7.
#   install.ps1 [-GameDir <folder that holds ProjectPBZ>]   install (the game must be closed)
#   install.ps1 -Uninstall [-GameDir ...]                    remove the mod files
#   install.ps1 -Check [-GameDir ...]                        game folder, game build, installed state
param([string]$GameDir, [switch]$Uninstall, [switch]$Check)
$ErrorActionPreference = 'Stop'
$Names = 'z_KarinPBZ_P.pak', 'z_KarinPBZ_P.ucas', 'z_KarinPBZ_P.utoc'
# the other Karin mod (PicodraTech) replaces the same game assets: only one of the two may be installed
$OtherNames = 'z_KarinPT_P.pak', 'z_KarinPT_P.ucas', 'z_KarinPT_P.utoc'
$AppId = '4115450'
$BuildId = '26266538'
$Files = Join-Path $PSScriptRoot 'files'

$Sums = @{}
foreach ($line in Get-Content (Join-Path $Files 'SHA256SUMS.txt')) {
    $a = $line.Trim() -split '\s+'
    if ($a.Count -ge 2) { $Sums[$a[1]] = $a[0] }
}

function Find-GameDir {
    $libs = @()
    foreach ($k in 'HKCU:\Software\Valve\Steam', 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam', 'HKLM:\SOFTWARE\Valve\Steam') {
        $p = Get-ItemProperty $k -ErrorAction SilentlyContinue
        foreach ($r in @($p.SteamPath, $p.InstallPath)) {
            if (-not $r) { continue }
            $libs += $r
            $vdf = Join-Path $r 'steamapps\libraryfolders.vdf'
            if (Test-Path $vdf) {
                foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) { $libs += $m.Groups[1].Value.Replace('\\', '\') }
            }
        }
    }
    foreach ($l in $libs) {
        $dir = 'PBZ'
        $acf = Join-Path $l "steamapps\appmanifest_$AppId.acf"
        if (Test-Path $acf) {
            $m = [regex]::Match((Get-Content $acf -Raw), '"installdir"\s+"([^"]+)"')
            if ($m.Success) { $dir = $m.Groups[1].Value }
        }
        $d = Join-Path $l "steamapps\common\$dir"
        if (Test-Path (Join-Path $d 'ProjectPBZ\Content\Paks')) { return (Resolve-Path $d).Path }
    }
}

function Get-GameBuild([string]$Dir) {
    $acf = Join-Path (Split-Path (Split-Path $Dir)) "appmanifest_$AppId.acf"
    if (Test-Path $acf) {
        $m = [regex]::Match((Get-Content $acf -Raw), '"buildid"\s+"(\d+)"')
        if ($m.Success) { return $m.Groups[1].Value }
    }
}

function Test-Same([string]$Path, [string]$Name) {
    (Test-Path $Path) -and ((Get-FileHash $Path -Algorithm SHA256).Hash -eq $Sums[$Name])
}

function Get-State {
    $present = @($Names | Where-Object { Test-Path (Join-Path $Mods $_) })
    $same = @($Names | Where-Object { Test-Same (Join-Path $Mods $_) $_ })
    if ($present.Count -eq 0) { '未安装' }
    elseif ($same.Count -eq $Names.Count) { '已安装，与本包一致' }
    else { '已安装其他版本，或文件不全' }
}

if (-not $GameDir) { $GameDir = Find-GameDir }
if (-not $GameDir -or -not (Test-Path (Join-Path $GameDir 'ProjectPBZ\Content\Paks'))) {
    Write-Host '没有找到游戏目录。请用 -GameDir 指定含 ProjectPBZ 文件夹的那一层，例如：' -ForegroundColor Red
    Write-Host '  powershell -ExecutionPolicy Bypass -File .\install.ps1 -GameDir "<Steam 库>\steamapps\common\PBZ"'
    exit 1
}
$Mods = Join-Path $GameDir 'ProjectPBZ\Content\Paks\~mods'
Write-Host ('游戏目录：{0}' -f $GameDir)
$build = Get-GameBuild $GameDir
if (-not $build) { Write-Host '游戏版本：未知（没有找到 Steam 的 appmanifest）' }
elseif ($build -eq $BuildId) { Write-Host ('游戏版本：buildid {0}，与 mod 一致' -f $build) }
else { Write-Host ('注意：游戏版本是 buildid {0}，mod 是按 {1} 打包的。游戏更新后 mod 可能失效或导致崩溃，需要重新构建。' -f $build, $BuildId) -ForegroundColor Yellow }

$found = @($OtherNames | Where-Object { Test-Path (Join-Path $Mods $_) })
if ($Check) {
    Write-Host ('状态：{0}' -f (Get-State))
    if ($found.Count) { Write-Host ('另一套 Karin mod（PicodraTech 版）也在 ~mods 里：{0}。两套不能同时安装，安装本包时会删除它。' -f ($found -join ', ')) -ForegroundColor Yellow }
    exit 0
}

if (Get-Process PBZ -ErrorAction SilentlyContinue) {
    Write-Host '游戏正在运行，请先关闭游戏。' -ForegroundColor Red
    exit 1
}

if ($Uninstall) {
    $n = 0
    foreach ($f in $Names) {
        $p = Join-Path $Mods $f
        if (Test-Path $p) { Remove-Item $p -Force; $n++ }
    }
    if ((Test-Path $Mods) -and -not (Get-ChildItem $Mods -Force)) { Remove-Item $Mods }
    Write-Host ('已卸载，删除了 {0} 个文件。' -f $n)
    exit 0
}

foreach ($f in $Names) {
    if (-not (Test-Same (Join-Path $Files $f) $f)) {
        Write-Host ('包内文件缺失或损坏：{0}，请重新获取 mod 包。' -f $f) -ForegroundColor Red
        exit 1
    }
}
New-Item -ItemType Directory -Force $Mods | Out-Null
foreach ($f in $found) { Remove-Item (Join-Path $Mods $f) -Force }
if ($found.Count) { Write-Host ('已删除另一套 Karin mod（PicodraTech 版）的文件：{0}（两套替换的是同样的游戏资源）' -f ($found -join ', ')) }
foreach ($f in $Names) { Copy-Item (Join-Path $Files $f) $Mods -Force }
$state = Get-State
Write-Host ('已复制到：{0}' -f $Mods)
Write-Host ('状态：{0}' -f $state)
if ($state -ne '已安装，与本包一致') { exit 1 }
