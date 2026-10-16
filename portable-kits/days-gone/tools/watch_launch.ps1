# Launch Days Gone through Steam and record what the game process does (port of the build machine's watchgame.ps1; run
# it in the user's desktop session). Output folder: -OutDir, default <DG_WORK_ROOT>\out (DG_WORK_ROOT or -WorkRoot):
# watch.txt (pid and start offset, exit code and times, window titles, processes started since the launch, screens) and
# watch1.png (whole desktop about 1.2 s after the game process starts). Gives up after 40 s without a DaysGone process
# and stops watching after 150 s.
[CmdletBinding(PositionalBinding = $false)]
param([string]$WorkRoot = $env:DG_WORK_ROOT, [string]$OutDir)
if (-not $OutDir) {
  if (-not $WorkRoot) { throw 'Set DG_WORK_ROOT (or pass -WorkRoot) to the working folder, or pass -OutDir' }
  $OutDir = Join-Path $WorkRoot 'out'
}
$out = Join-Path $OutDir 'watch.txt'; New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
function Shot($f) { $b = [System.Windows.Forms.SystemInformation]::VirtualScreen; $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size); $bmp.Save($f); $g.Dispose(); $bmp.Dispose() }
$t0 = Get-Date
Start-Process 'steam://rungameid/1259420'
$p = $null
while (-not $p -and ((Get-Date) - $t0).TotalSeconds -lt 40) { $p = Get-Process DaysGone -ErrorAction SilentlyContinue | select -First 1; Start-Sleep -m 20 }
if (-not $p) { "no process within 40 s" | Set-Content $out; exit }
$null = $p.Handle
$log = @("found pid $($p.Id) at +$([int]((Get-Date) - $t0).TotalMilliseconds) ms")
$shot = $false; $titles = @()
while (-not $p.HasExited -and ((Get-Date) - $t0).TotalSeconds -lt 150) {
  $p.Refresh(); if ($p.MainWindowTitle) { $titles += $p.MainWindowTitle }
  if (-not $shot -and ((Get-Date) - $p.StartTime).TotalMilliseconds -gt 1200) { Shot (Join-Path $OutDir 'watch1.png'); $shot = $true }
  Start-Sleep -m 50 }
$log += "exited=$($p.HasExited) code=$($p.ExitCode) (0x{0:X8}) start=$($p.StartTime.ToString('HH:mm:ss.fff')) exit=$(if ($p.HasExited) { $p.ExitTime.ToString('HH:mm:ss.fff') })" -f $p.ExitCode
$log += "titles: " + (($titles | select -Unique) -join ' | ')
$log += "procs started since launch:"
$log += Get-CimInstance Win32_Process | ? { $_.CreationDate -gt $t0 } | % { "  $($_.ProcessId) $($_.Name) parent=$($_.ParentProcessId) $($_.CommandLine)" }
$log += "screens: " + (([System.Windows.Forms.Screen]::AllScreens | % { "$($_.DeviceName) $($_.Bounds.Width)x$($_.Bounds.Height) primary=$($_.Primary)" }) -join '; ')
$log | Set-Content $out
