# Burst screen capture daemon for the interactive desktop (start it from Win+R, it runs hidden).
# Capture folder <dir>: -Dir, default <SIFU_WORK_ROOT>\cap.
# Trigger: write "<frames> <interval_ms> <tag> [scale]" into <dir>\go.txt; "quit" stops the daemon.
# Frames land in <dir>\<tag>_NNN.jpg plus <tag>.txt (timestamps); <tag>.done marks completion.
param([string]$Dir)
if (-not $Dir) {
  if (-not $env:SIFU_WORK_ROOT) { throw 'Pass -Dir or set SIFU_WORK_ROOT (captures go to <SIFU_WORK_ROOT>\cap)' }
  $Dir = Join-Path $env:SIFU_WORK_ROOT 'cap'
}
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
Add-Type -Namespace W32 -Name Dpi -MemberDefinition '[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();'
[W32.Dpi]::SetProcessDPIAware() | Out-Null
New-Item -ItemType Directory -Force $dir | Out-Null
$go = Join-Path $dir 'go.txt'
Set-Content (Join-Path $dir 'daemon.alive') $PID
$jpg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
$ep = New-Object System.Drawing.Imaging.EncoderParameters 1
$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality, [long]85)
$b = [System.Windows.Forms.Screen]::PrimaryScreen
$W = $b.Bounds.Width; $H = $b.Bounds.Height
while ($true) {
  Start-Sleep -Milliseconds 40
  if (-not (Test-Path $go)) { continue }
  $cmd = (Get-Content $go -Raw).Trim()
  Remove-Item $go -ErrorAction Ignore
  if ($cmd -eq 'quit') { break }
  $p = $cmd -split '\s+'
  $n = [int]$p[0]; $iv = [int]$p[1]; $tag = $p[2]
  $scale = if ($p.Count -gt 3) { [double]$p[3] } else { 0.5 }
  $w2 = [int]($W * $scale); $h2 = [int]($H * $scale)
  $full = New-Object System.Drawing.Bitmap $W, $H
  $gf = [System.Drawing.Graphics]::FromImage($full)
  $frames = New-Object System.Collections.Generic.List[System.Drawing.Bitmap]
  $times = New-Object System.Collections.Generic.List[double]
  $sw = [Diagnostics.Stopwatch]::StartNew()
  for ($i = 0; $i -lt $n; $i++) {
    $target = $i * $iv
    while ($sw.Elapsed.TotalMilliseconds -lt $target) { Start-Sleep -Milliseconds 1 }
    $times.Add($sw.Elapsed.TotalMilliseconds)
    $gf.CopyFromScreen(0, 0, 0, 0, $full.Size)
    $small = New-Object System.Drawing.Bitmap $w2, $h2
    $gs = [System.Drawing.Graphics]::FromImage($small)
    $gs.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::Bilinear
    $gs.DrawImage($full, 0, 0, $w2, $h2)
    $gs.Dispose()
    $frames.Add($small)
  }
  for ($i = 0; $i -lt $frames.Count; $i++) {
    $frames[$i].Save((Join-Path $dir ('{0}_{1:D3}.jpg' -f $tag, $i)), $jpg, $ep)
    $frames[$i].Dispose()
  }
  $gf.Dispose(); $full.Dispose()
  ($times | ForEach-Object { '{0:F1}' -f $_ }) -join "`n" | Set-Content (Join-Path $dir "$tag.txt")
  Set-Content (Join-Path $dir "$tag.done") 'ok'
}
Remove-Item (Join-Path $dir 'daemon.alive') -ErrorAction Ignore
