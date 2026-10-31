# Karin for DEATH STRANDING 2: ON THE BEACH - installer / uninstaller (Windows PowerShell 5.1 or later).
#
#   install.ps1 -Variant NoExpression | Expression [-GameDir <folder with DS2.exe>]
#   install.ps1 -Uninstall [-GameDir ...]
#
# The mod data is one archive (karin.core.stream). Installing adds it to the game's own streaming graph as a new
# package file (package.99.00.core.stream), points the touched groups' spans and stream locators at it, and applies
# the mod's link edits to streaming_links.stream. Nothing of a game version is shipped: the graph and links of the
# copy being modded are patched, after checking that every group the mod touches is the same as in the build the
# mod was made from (objects, types, subgroups, links). If any differs, nothing is written.
# Originals go to <game>\KarinMod_backup; files are replaced via a temp file and a rename, never written in place.
param(
    [ValidateSet('NoExpression', 'Expression')][string]$Variant,
    [switch]$Uninstall,
    [string]$GameDir
)
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ArchiveName = 'package.99.00.core.stream'
$FileEntry = 'cache:package/' + $ArchiveName

function Say([string]$m) { Write-Host $m }
function Fail([string]$m) { Write-Host ''; Write-Host "[失败] $m" -ForegroundColor Red; exit 1 }

# ------------------------------------------------------------------ game folder
function Find-SteamGame {
    $roots = @()
    foreach ($k in 'HKCU:\Software\Valve\Steam', 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam', 'HKLM:\SOFTWARE\Valve\Steam') {
        try {
            $p = Get-ItemProperty $k -ErrorAction Stop
            foreach ($v in $p.SteamPath, $p.InstallPath) { if ($v) { $roots += ($v -replace '/', '\') } }
        } catch { }
    }
    $libs = @()
    foreach ($r in ($roots | Select-Object -Unique)) {
        $libs += $r
        $vdf = Join-Path $r 'steamapps\libraryfolders.vdf'
        if (Test-Path $vdf) {
            foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) { $libs += ($m.Groups[1].Value -replace '\\\\', '\') }
        }
    }
    foreach ($l in ($libs | Select-Object -Unique)) {
        $acf = Join-Path $l 'steamapps\appmanifest_3280350.acf'
        if (Test-Path $acf) {
            $m = [regex]::Match((Get-Content $acf -Raw), '"installdir"\s+"([^"]+)"')
            if ($m.Success) {
                $d = Join-Path $l ('steamapps\common\' + $m.Groups[1].Value)
                if (Test-Path (Join-Path $d 'LocalCacheWinGame\package\streaming_graph.core')) { return $d }
            }
        }
    }
    return $null
}

function Test-GameDir([string]$d) {
    return $d -and (Test-Path (Join-Path $d 'LocalCacheWinGame\package\streaming_graph.core'))
}

if (-not $GameDir) {
    foreach ($c in (Split-Path -Parent $Here), $Here, (Split-Path -Parent (Split-Path -Parent $Here))) {
        if (Test-GameDir $c) { $GameDir = $c; break }
    }
}
if (-not $GameDir) { $GameDir = Find-SteamGame }
if (-not $GameDir) {
    Say '没有自动找到游戏。请把游戏文件夹（里面有 DS2.exe 的那个文件夹）的路径粘贴到这里，然后按回车：'
    $GameDir = (Read-Host).Trim('"', ' ')
}
if (-not (Test-GameDir $GameDir)) { Fail "这里不是死亡搁浅 2 的游戏文件夹：$GameDir" }
$GameDir = (Resolve-Path $GameDir).Path
$Pkg = Join-Path $GameDir 'LocalCacheWinGame\package'
$GraphPath = Join-Path $Pkg 'streaming_graph.core'
$LinksPath = Join-Path $Pkg 'streaming_links.stream'
$ArchivePath = Join-Path $Pkg $ArchiveName
$Backup = Join-Path $GameDir 'KarinMod_backup'
$StatePath = Join-Path $Backup 'state.json'
Say "游戏文件夹：$GameDir"
$exe = Join-Path $GameDir 'DS2.exe'
if (Test-Path $exe) { Say ('游戏版本：' + (Get-Item $exe).VersionInfo.FileVersion) }
if (Get-Process DS2 -ErrorAction SilentlyContinue) { Fail '游戏正在运行，请先退出游戏再运行。' }

# ------------------------------------------------------------------ helpers
function Get-Sha([byte[]]$b, [int]$off, [int]$len, [string]$algo) {
    $h = [System.Security.Cryptography.HashAlgorithm]::Create($algo)
    return ([BitConverter]::ToString($h.ComputeHash($b, $off, $len)) -replace '-', '').ToLower()
}
# .NET, not Get-FileHash: Windows PowerShell started from PowerShell 7 inherits a module path that can't load it
function Get-FileSha256([string]$p) {
    $s = [IO.File]::OpenRead($p)
    try { return ([BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($s)) -replace '-', '') }
    finally { $s.Dispose() }
}
function Put-U32([byte[]]$b, [int]$pos, [uint32]$v) { [Array]::Copy([BitConverter]::GetBytes($v), 0, $b, $pos, 4) }
function Put-U64([byte[]]$b, [int]$pos, [uint64]$v) { [Array]::Copy([BitConverter]::GetBytes($v), 0, $b, $pos, 8) }
function Get-Crc32C([byte[]]$data) {
    # CRC32C (Castagnoli), initial value 0, no final xor: the checksum Decima stores with each string
    $t = New-Object 'uint32[]' 256
    for ($i = 0; $i -lt 256; $i++) {
        [uint32]$c = $i
        for ($k = 0; $k -lt 8; $k++) {
            if ($c -band 1) { $c = [uint32](($c -shr 1) -bxor 2197175160) } else { $c = [uint32]($c -shr 1) }
        }
        $t[$i] = $c
    }
    [uint32]$c = 0
    foreach ($x in $data) { $c = [uint32]($t[($c -bxor $x) -band 255] -bxor ($c -shr 8)) }
    return $c
}
# replaces a game file without writing into it (a hard-linked copy elsewhere keeps its data)
function Replace-File([string]$path, [byte[]]$bytes) {
    $tmp = $path + '.karin_tmp'
    [IO.File]::WriteAllBytes($tmp, $bytes)
    Remove-Item $path -Force
    Rename-Item $tmp (Split-Path -Leaf $path)
}
function Restore-File([string]$from, [string]$path) {
    $tmp = $path + '.karin_tmp'
    Copy-Item $from $tmp -Force
    Remove-Item $path -Force
    Rename-Item $tmp (Split-Path -Leaf $path)
}

# ------------------------------------------------------------------ uninstall
function Invoke-Uninstall {
    if (-not (Test-Path $StatePath)) {
        if (Test-Path $ArchivePath) { Remove-Item $ArchivePath -Force; Say '已删除残留的 mod 数据文件。' }
        Say '没有发现已安装的 Karin mod。'
        return
    }
    $st = Get-Content $StatePath -Raw | ConvertFrom-Json
    $g = Get-FileSha256 $GraphPath
    $l = Get-FileSha256 $LinksPath
    if ($g -eq $st.installed_graph -and $l -eq $st.installed_links) {
        Restore-File (Join-Path $Backup 'streaming_graph.core') $GraphPath
        Restore-File (Join-Path $Backup 'streaming_links.stream') $LinksPath
        Say '已还原游戏原来的 streaming_graph.core 和 streaming_links.stream。'
    } else {
        # the game was updated or its files verified since: those files are the game's own now, keep them
        Say '游戏文件在安装 mod 之后已被更新或校验过，保留现在的文件，不做还原。'
    }
    if (Test-Path $ArchivePath) { Remove-Item $ArchivePath -Force }
    Remove-Item $Backup -Recurse -Force
    Say '卸载完成。'
}

if ($Uninstall) { Invoke-Uninstall; exit 0 }
if (-not $Variant) { Fail '请用 -Variant NoExpression 或 -Variant Expression 指定要安装的版本。' }

# ------------------------------------------------------------------ install: load the mod
$ModDir = Join-Path $Here $Variant
$man = Get-Content (Join-Path $ModDir 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$Archive = Join-Path $ModDir $man.archive.file
if (-not (Test-Path $Archive) -or (Get-Item $Archive).Length -ne [long]$man.archive.size) { Fail "mod 数据文件缺失或不完整：$Archive" }
Say "要安装：$($man.title)"
if (Test-Path $StatePath) {
    Say '检测到已安装的 Karin mod，先卸载旧的……'
    Invoke-Uninstall
}

# ------------------------------------------------------------------ parse the graph
$G = [IO.File]::ReadAllBytes($GraphPath)
$L = [IO.File]::ReadAllBytes($LinksPath)
function U32([int]$p) { return [BitConverter]::ToUInt32($G, $p) }
function I32([int]$p) { return [BitConverter]::ToInt32($G, $p) }
if (([BitConverter]::ToUInt64($G, 0)).ToString('X16') -ne $man.graph_type_hash) { Fail '这个游戏版本的 streaming_graph.core 格式不同，mod 不兼容。' }
# the graph object (after its type hash and size) is followed by a few zero bytes, kept as they are
$trailer = $G.Length - 12 - (U32 8)
if ($trailer -lt 0 -or $trailer -gt 16) { Fail 'streaming_graph.core 已损坏或不完整，请先在 Steam 里验证游戏文件。' }
$p = 12 + 16 + 1
$nTypeHashes = U32 $p; $posTypeHashes = $p + 4; $p += 4 + 8 * $nTypeHashes
$nTypeData = U32 $p; $posTypeData = $p + 4; $p += 4 + $nTypeData
$p += 8
$linkTableSize = I32 $p; $p += 4
$nLoc = U32 $p; $posLoc = $p + 4; $p += 4 + 8 * $nLoc
$n = U32 $p; $p += 4 + 4 * $n
$nSpan = U32 $p; $posSpan = $p + 4; $p += 4 + 12 * $nSpan
$nGroups = U32 $p; $p += 4
$want = @{}
foreach ($grp in $man.groups) { $want[[int]$grp.gid] = $null }
for ($i = 0; $i -lt $nGroups; $i++) {
    $gid = I32 $p
    if ($want.ContainsKey($gid)) { $want[$gid] = $p }
    $p += 68 + 16 * (U32 ($p + 64))   # GroupID, NumObjects, GroupSize (int64), 12 uint32, ObjectUUIDs
}
$nSub = U32 $p; $posSub = $p + 4; $p += 4 + 4 * $nSub
$n = U32 $p; $p += 4 + 16 * $n
$n = U32 $p; $p += 4 + 4 * $n
$posFilesCount = $p
$nFiles = U32 $p; $p += 4
$names = @()
$firstCrcOk = $true
for ($i = 0; $i -lt $nFiles; $i++) {
    $len = U32 $p; $p += 4
    if ($len -gt 0) {
        $crc = U32 $p
        $nameBytes = New-Object byte[] $len
        [Array]::Copy($G, $p + 4, $nameBytes, 0, $len)
        if ($i -eq 0 -and (Get-Crc32C $nameBytes) -ne $crc) { $firstCrcOk = $false }
        $names += [Text.Encoding]::UTF8.GetString($nameBytes)
        $p += 4 + $len
    } else { $names += '' }
}
$endFiles = $p
$posPfoCount = $p
if ((U32 $p) -ne $nFiles) { Fail 'streaming_graph.core 的结构和预期不同，mod 不兼容。' }
$p += 4
for ($i = 0; $i -lt $nFiles; $i++) { $p += 4 + 4 * (U32 $p) }
$endPfo = $p
$posPflCount = $p
if ((U32 $p) -ne $nFiles) { Fail 'streaming_graph.core 的结构和预期不同，mod 不兼容。' }
$p += 4
for ($i = 0; $i -lt $nFiles; $i++) { $p += 4 + 4 * (U32 $p) }
$endPfl = $p
if (-not $firstCrcOk) { Fail '文件名校验算法和预期不同，mod 不兼容。' }
if ($names -contains $FileEntry) { Fail "游戏的 streaming_graph.core 里已经有 $ArchiveName（可能是之前没卸载干净）。请在 Steam 里验证游戏文件后再安装。" }
if ($L.Length -ne $linkTableSize) { Fail 'streaming_links.stream 和 streaming_graph.core 不匹配，请先在 Steam 里验证游戏文件。' }

# ------------------------------------------------------------------ check every touched group
$bad = @()
$typeIdxBase = $posTypeData + 20
foreach ($grp in $man.groups) {
    $e = $want[[int]$grp.gid]
    if ($null -eq $e) { $bad += "组 $($grp.gid)：找不到"; continue }
    $f = @{ NumObjects = I32 ($e + 4); GroupSize = [BitConverter]::ToInt64($G, $e + 8); SubGroupCount = I32 ($e + 20)
            SpanCount = I32 ($e + 36); TypeCount = I32 ($e + 44); LinkSize = I32 ($e + 52); LocatorCount = I32 ($e + 60) }
    $c = $grp.check
    $why = @()
    foreach ($k in 'NumObjects', 'GroupSize', 'SubGroupCount', 'SpanCount', 'TypeCount', 'LinkSize', 'LocatorCount') {
        if ([long]$f[$k] -ne [long]$c.$k) { $why += $k }
    }
    if (-not $why) {
        $subStart = I32 ($e + 16); $spanStart = I32 ($e + 32); $typeStart = I32 ($e + 40)
        $linkStart = I32 ($e + 48); $locStart = I32 ($e + 56)
        $th = New-Object byte[] (8 * $f.TypeCount)
        for ($i = 0; $i -lt $f.TypeCount; $i++) {
            $ti = [BitConverter]::ToUInt16($G, $typeIdxBase + 2 * ($typeStart + $i))
            [Array]::Copy($G, $posTypeHashes + 8 * $ti, $th, 8 * $i, 8)
        }
        if ((Get-Sha $th 0 $th.Length 'SHA1') -ne $c.types_sha1) { $why += 'types' }
        $subs = @(for ($i = 0; $i -lt $f.SubGroupCount; $i++) { I32 ($posSub + 4 * ($subStart + $i)) })
        if (($subs -join ',') -ne (@($c.subgroups) -join ',')) { $why += 'subgroups' }
        if ((Get-Sha $L $linkStart $f.LinkSize 'SHA1') -ne $c.links_sha1) { $why += 'links' }
        foreach ($s in $grp.spans) {
            if ((U32 ($posSpan + 12 * ($spanStart + $s.k) + 4)) -ne [uint32]$s.vanilla_length) { $why += "span $($s.k)" }
        }
        foreach ($le in $grp.link_edits) {
            $a = [int]($linkStart + $le.rel)
            $old = (($L[$a..($a + [int]($le.old.Length / 2) - 1)] | ForEach-Object { $_.ToString('x2') }) -join '')
            if ($old -ne $le.old) { $why += "link @$($le.rel)" }
        }
        $grp | Add-Member -NotePropertyName spanStart -NotePropertyValue $spanStart
        $grp | Add-Member -NotePropertyName locStart -NotePropertyValue $locStart
        $grp | Add-Member -NotePropertyName linkStart -NotePropertyValue $linkStart
    }
    if ($why) { $bad += "组 $($grp.gid)：$($why -join ', ')" }
}
if ($bad) {
    Say ''
    Say '这个游戏版本里，mod 要改的部分和制作 mod 时的版本不一样：'
    $bad | Select-Object -First 12 | ForEach-Object { Say "  $_" }
    Fail 'mod 和这个游戏版本不兼容，没有改动任何文件。需要针对这个版本重新制作 mod。'
}
Say "兼容性检查通过（$($man.groups.Count) 个组）。"

# ------------------------------------------------------------------ patch in memory
[uint32]$newIndex = $nFiles
foreach ($grp in $man.groups) {
    foreach ($s in $grp.spans) {
        $q = $posSpan + 12 * ($grp.spanStart + $s.k)
        Put-U32 $G $q $newIndex
        Put-U32 $G ($q + 4) ([uint32]$s.length)
        Put-U32 $G ($q + 8) ([uint32]$s.offset)
    }
    foreach ($lc in $grp.locators) {
        Put-U64 $G ($posLoc + 8 * ($grp.locStart + $lc.k)) (([uint64]$lc.offset -shl 24) -bor [uint64]$newIndex)
    }
    foreach ($le in $grp.link_edits) {
        for ($i = 0; $i -lt [int]($le.new.Length / 2); $i++) {
            $L[[int]($grp.linkStart + $le.rel + $i)] = [Convert]::ToByte($le.new.Substring(2 * $i, 2), 16)
        }
    }
}
# append the archive to Files, PackFileOffsets ([]) and PackFileLengths ([4], as every other .core.stream package)
$nameBytes = [Text.Encoding]::UTF8.GetBytes($FileEntry)
$ms = New-Object IO.MemoryStream
$ms.Write($G, 0, $endFiles)
$ms.Write([BitConverter]::GetBytes([uint32]$nameBytes.Length), 0, 4)
$ms.Write([BitConverter]::GetBytes([uint32](Get-Crc32C $nameBytes)), 0, 4)
$ms.Write($nameBytes, 0, $nameBytes.Length)
$ms.Write($G, $endFiles, $endPfo - $endFiles)
$ms.Write([BitConverter]::GetBytes([uint32]0), 0, 4)
$ms.Write($G, $endPfo, $endPfl - $endPfo)
$ms.Write([BitConverter]::GetBytes([uint32]1), 0, 4)
$ms.Write([BitConverter]::GetBytes([uint32]4), 0, 4)
$ms.Write($G, $endPfl, $G.Length - $endPfl)
$N = $ms.ToArray()
$grow = 8 + $nameBytes.Length
Put-U32 $N $posFilesCount ([uint32]($nFiles + 1))
Put-U32 $N ($posPfoCount + $grow) ([uint32]($nFiles + 1))
Put-U32 $N ($posPflCount + $grow + 4) ([uint32]($nFiles + 1))
Put-U32 $N 8 ([uint32]($N.Length - 12 - $trailer))

# ------------------------------------------------------------------ write
New-Item -ItemType Directory -Force $Backup | Out-Null
Copy-Item $GraphPath (Join-Path $Backup 'streaming_graph.core') -Force
Copy-Item $LinksPath (Join-Path $Backup 'streaming_links.stream') -Force
Say ('正在复制 mod 数据（{0} MB）……' -f [int]([long]$man.archive.size / 1MB))
Copy-Item $Archive ($ArchivePath + '.karin_tmp') -Force
if (Test-Path $ArchivePath) { Remove-Item $ArchivePath -Force }
Rename-Item ($ArchivePath + '.karin_tmp') $ArchiveName
Replace-File $GraphPath $N
Replace-File $LinksPath $L
$state = [ordered]@{
    variant = $Variant; title = $man.title; archive = $ArchiveName; date = (Get-Date).ToString('s')
    original_graph = Get-FileSha256 (Join-Path $Backup 'streaming_graph.core')
    original_links = Get-FileSha256 (Join-Path $Backup 'streaming_links.stream')
    installed_graph = Get-FileSha256 $GraphPath
    installed_links = Get-FileSha256 $LinksPath
}
$state | ConvertTo-Json | Set-Content $StatePath -Encoding UTF8
Say ''
Write-Host "安装完成：$($man.title)" -ForegroundColor Green
Say '卸载请运行“卸载.bat”。游戏更新或在 Steam 里验证文件后，mod 会失效，重新运行安装即可。'
