# Set the primary display's desktop resolution (port of the build machine's setres.ps1; its rungame.bat ran it with
# 1920 1080 before starting the game through Steam). Usage: set_resolution.ps1 [W] [H] [-ModesFile <txt>]
# Prints "result <n>" (ChangeDisplaySettings: 0 = changed, 1 = restart needed, negative = refused). -ModesFile also
# writes the display's modes (WxH@Hz, unique, sorted) and the result line to that file (the original wrote them to a
# fixed file in the user profile).
param([int]$W = 1920, [int]$H = 1080, [string]$ModesFile)
Add-Type @'
using System; using System.Runtime.InteropServices;
public class Res {
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
  public struct DEVMODE {
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmDeviceName;
    public short dmSpecVersion, dmDriverVersion, dmSize, dmDriverExtra; public int dmFields;
    public int dmPositionX, dmPositionY, dmDisplayOrientation, dmDisplayFixedOutput;
    public short dmColor, dmDuplex, dmYResolution, dmTTOption, dmCollate;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmFormName;
    public short dmLogPixels; public int dmBitsPerPel, dmPelsWidth, dmPelsHeight, dmDisplayFlags, dmDisplayFrequency;
    public int dmICMMethod, dmICMIntent, dmMediaType, dmDitherType, dmReserved1, dmReserved2, dmPanningWidth, dmPanningHeight; }
  [DllImport("user32.dll")] public static extern int EnumDisplaySettings(string dev, int mode, ref DEVMODE dm);
  [DllImport("user32.dll")] public static extern int ChangeDisplaySettings(ref DEVMODE dm, int flags);
}
'@
$dm = New-Object Res+DEVMODE; $dm.dmSize = [System.Runtime.InteropServices.Marshal]::SizeOf($dm)
$modes = @(); $i = 0
while ([Res]::EnumDisplaySettings($null, $i, [ref]$dm) -ne 0) { $modes += "$($dm.dmPelsWidth)x$($dm.dmPelsHeight)@$($dm.dmDisplayFrequency)"; $i++ }
if ($ModesFile) { $modes | Sort-Object -Unique | Set-Content $ModesFile }
[Res]::EnumDisplaySettings($null, -1, [ref]$dm) | Out-Null
$dm.dmPelsWidth = $W; $dm.dmPelsHeight = $H; $dm.dmFields = 0x80000 -bor 0x100000
$r = [Res]::ChangeDisplaySettings([ref]$dm, 1)
if ($ModesFile) { "result $r" | Add-Content $ModesFile }
"result $r"
