# mktest.ps1 -Pkgs "a+b+c" : test container z_PBZTest_P with the listed cooked plugin packages (paths under
# HuaShira/Content, no extension; a trailing \* takes a folder) and install it into Paks\~mods (replacing the test
# container and the Karin mods).
# -Root / PBZ_ROOT: work root with UE\ProjectPBZ (cooked); -UE / UE_ROOT: UE 5.7 install; -GameDir / PBZ_GAME_DIR: the
# folder that holds ProjectPBZ. The game must be closed. Output in <Root>\out_test.
param([string]$Pkgs, [string]$Root = $env:PBZ_ROOT, [string]$UE = $env:UE_ROOT, [string]$GameDir = $env:PBZ_GAME_DIR)
$List = $Pkgs.Split([char]43)
$ErrorActionPreference = 'Stop'
if (-not $Pkgs -or -not $Root -or -not $UE -or -not $GameDir) { throw 'need -Pkgs and -Root / PBZ_ROOT, -UE / UE_ROOT, -GameDir / PBZ_GAME_DIR' }
if (Get-Process PBZ -ErrorAction SilentlyContinue) { throw 'PBZ.exe is running: close the game first' }
$pak = Join-Path $UE 'Engine\Binaries\Win64\UnrealPak.exe'
$proj = Join-Path $Root 'UE\ProjectPBZ\ProjectPBZ.uproject'
$cooked = Join-Path $Root 'UE\ProjectPBZ\Saved\Cooked\Windows'
$meta = "$cooked\ProjectPBZ\Metadata"
$plug = "$cooked\ProjectPBZ\Plugins\HuaShira\Content"
$Out = Join-Path $Root 'out_test'; $Name = 'z_PBZTest_P'
Remove-Item -Recurse -Force $Out -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $Out, "$Out\tmp" | Out-Null
$files = foreach ($p in $List) { if ($p.EndsWith('\*')) { Get-ChildItem (Join-Path $plug $p.TrimEnd('*')) -Recurse -File } else { Get-ChildItem (Join-Path $plug ($p + '.*')) -File } }
$files | ForEach-Object { '"{0}" "../../../ProjectPBZ/Plugins/HuaShira/Content/{1}" -compress' -f $_.FullName, $_.FullName.Substring($plug.Length + 1).Replace('\', '/') } | Set-Content "$Out\resp.txt"
'-Output="{0}\{1}.utoc" -ContainerName={1} -ResponseFile="{0}\resp.txt"' -f $Out, $Name | Set-Content "$Out\cmds.txt"
& $pak $proj "-CreateGlobalContainer=$Out\tmp\global.utoc" "-PackageStoreManifest=$meta\packagestore.manifest" "-CookedDirectory=$cooked" "-Commands=$Out\cmds.txt" "-ScriptObjects=$meta\scriptobjects.bin" -compressionformats=Oodle -platform=Windows -unattended 2>&1 | Select-String ' Error' | Select-Object -First 5
'test' | Set-Content "$Out\tmp\t.txt"
'"{0}\tmp\t.txt" "../../../ProjectPBZ/Content/Mods/PBZTest/t.txt"' -f $Out | Set-Content "$Out\pakresp.txt"
& $pak "$Out\$Name.pak" "-create=$Out\pakresp.txt" -platform=Windows -unattended 2>&1 | Select-String ' Error' | Select-Object -First 3
Remove-Item -Recurse -Force "$Out\tmp"
$dst = Join-Path $GameDir 'ProjectPBZ\Content\Paks\~mods'
# only the test container and the two Karin mods (same game assets); other mods in ~mods stay
Remove-Item "$dst\z_PBZTest_P.*", "$dst\z_KarinPBZ_P.*", "$dst\z_KarinPT_P.*" -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item "$Out\$Name.*" $dst -Force
"packages: " + @($files | Where-Object Extension -eq '.uasset').Count
