# Karin for DEATH STRANDING 2 - collects what the mod author needs to port the mod to this game build. Read-only.
#
#   collect.ps1 [-GameDir <folder with DS2.exe>] [-Out <folder>] [-Yes] [-ReportOnly]
#   collect.ps1 -GraphPath <streaming_graph.core> -LinksPath <streaming_links.stream> -CacheRoot <LocalCacheWinGame> ...
#
# Writes KarinMod_data_<version>.zip:
#   report.json / groups.tsv / types.txt  the build's streaming-graph structure (as diagnose.ps1 did): every group's
#                                         fingerprints; for the groups the mod touches their subgroups, spans (SHA-1 of
#                                         the decompressed data), stream locators and raw link records
#   collect.json                          what was taken, per group and per package file
#   LocalCacheWinGame\package\...         streaming_graph.core and streaming_links.stream as they are, and every package
#                                         file that holds data of the groups below, cut down: a DSAR archive keeps its
#                                         header and whole chunk table but only the (still compressed) chunks with that
#                                         data, the other chunks are empty (csize 0) so reading them fails instead of
#                                         returning zeros; a plain file becomes <name>.karin_ranges (offset/length list +
#                                         data) for the author to rebuild as a sparse file
# Groups: the mod's own and those its build reads (full: objects and stream data), and everything they reach through
# subgroups (objects only). -ReportOnly writes just the structure report (a few MB). DS2.exe is never copied.
param(
    [string]$GameDir,
    [string]$Out,
    [string]$GraphPath,
    [string]$LinksPath,
    [string]$CacheRoot,
    [switch]$Yes,
    [switch]$ReportOnly
)
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Say([string]$m) { Write-Host $m }
function Fail([string]$m) { Write-Host ''; Write-Host "[失败] $m" -ForegroundColor Red; exit 1 }

# ------------------------------------------------------------------ game folder (same search as install.ps1)
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
function Test-GameDir([string]$d) { return $d -and (Test-Path (Join-Path $d 'LocalCacheWinGame\package\streaming_graph.core')) }

$version = 'unknown'
$buildId = ''
if (-not $GraphPath) {
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
    $CacheRoot = Join-Path $GameDir 'LocalCacheWinGame'
    $GraphPath = Join-Path $CacheRoot 'package\streaming_graph.core'
    $LinksPath = Join-Path $CacheRoot 'package\streaming_links.stream'
    $exe = Join-Path $GameDir 'DS2.exe'
    if (Test-Path $exe) { $version = (Get-Item $exe).VersionInfo.FileVersion }
    $acf = Join-Path (Split-Path -Parent (Split-Path -Parent $GameDir)) 'appmanifest_3280350.acf'
    if (Test-Path $acf) {
        $m = [regex]::Match((Get-Content $acf -Raw), '"buildid"\s+"(\d+)"')
        if ($m.Success) { $buildId = $m.Groups[1].Value }
    }
    if (Test-Path (Join-Path $GameDir 'KarinMod_backup\state.json')) {
        Fail '游戏里装着 Karin mod。请先运行“卸载.bat”（或在 Steam 里验证游戏文件），再运行本工具。'
    }
}
Say "游戏版本：$version"
if ($buildId) { Say "Steam 构建号：$buildId" }

# the mod's groups and those its build reads, in full (objects and stream data)
$Full = 6744, 12706, 31123, 31225, 50108, 50109, 50110, 50113, 50116, 50120, 50121, 58946, 67632, 67673, 67695, 67696,
        67699, 67704, 67706, 50107, 50118, 50119, 67700, 67711, 67633, 67636, 67685, 67648, 67690, 34853, 74336,
        12715, 31301, 75978
# groups described in detail in report.json: those plus the targets of the outfit table
$Detail = @($Full) + @(39983, 40436, 65631, 58940, 43771, 67631, 34852, 5494)

# ------------------------------------------------------------------ reader (C#: 80 000 groups and LZ4 are slow in script)
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$refs = @([System.IO.Compression.ZipArchive].Assembly.Location, [System.IO.Compression.ZipFile].Assembly.Location)
Add-Type -Language CSharp -ReferencedAssemblies $refs -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;

public class KarinCollect
{
    byte[] G, L;
    string cache;
    int posTypeHashes, nTypeHashes, posTypeData, posLoc, nLoc, posSpan, nSpan, nGroups, posSub;
    int[] gpos;
    public ulong TypeHash, LinkTableId;
    public int LinkTableSize, GraphLength, LinksLength;
    public List<string> Files = new List<string>();
    Dictionary<int, int> byId = new Dictionary<int, int>();

    int I32(int p) { return BitConverter.ToInt32(G, p); }

    public KarinCollect(string graph, string links, string cacheRoot)
    {
        G = File.ReadAllBytes(graph);
        L = File.ReadAllBytes(links);
        cache = cacheRoot;
        GraphLength = G.Length; LinksLength = L.Length;
        TypeHash = BitConverter.ToUInt64(G, 0);
        int p = 12 + 16 + 1;
        nTypeHashes = I32(p); posTypeHashes = p + 4; p += 4 + 8 * nTypeHashes;
        int n = I32(p); posTypeData = p + 4; p += 4 + n;
        LinkTableId = BitConverter.ToUInt64(G, p); p += 8;
        LinkTableSize = I32(p); p += 4;
        nLoc = I32(p); posLoc = p + 4; p += 4 + 8 * nLoc;
        n = I32(p); p += 4 + 4 * n;
        nSpan = I32(p); posSpan = p + 4; p += 4 + 12 * nSpan;
        nGroups = I32(p); p += 4;
        gpos = new int[nGroups];
        for (int i = 0; i < nGroups; i++) { gpos[i] = p; byId[I32(p)] = i; p += 68 + 16 * I32(p + 64); }
        int nSub = I32(p); posSub = p + 4; p += 4 + 4 * nSub;
        n = I32(p); p += 4 + 16 * n;
        n = I32(p); p += 4 + 4 * n;
        int nf = I32(p); p += 4;
        for (int i = 0; i < nf; i++)
        {
            int len = I32(p); p += 4;
            if (len > 0) { Files.Add(Encoding.UTF8.GetString(G, p + 4, len)); p += 4 + len; } else Files.Add("");
        }
    }

    static string Hex(byte[] b, int chars)
    {
        StringBuilder s = new StringBuilder();
        foreach (byte x in b) s.Append(x.ToString("x2"));
        string h = s.ToString();
        return chars > 0 && chars < h.Length ? h.Substring(0, chars) : h;
    }
    static string Sha1(byte[] b, int off, int len, int chars)
    {
        using (SHA1 h = SHA1.Create()) return Hex(h.ComputeHash(b, off, len), chars);
    }
    static string Esc(string s) { return s.Replace("\\", "\\\\").Replace("\"", "\\\""); }
    int F(int gi, int field) { return I32(gpos[gi] + field); }
    byte[] TypeBytes(int gi)
    {
        int start = F(gi, 40), count = F(gi, 44);
        byte[] th = new byte[8 * count];
        for (int i = 0; i < count; i++)
        {
            int ti = BitConverter.ToUInt16(G, posTypeData + 20 + 2 * (start + i));
            Array.Copy(G, posTypeHashes + 8 * ti, th, 8 * i, 8);
        }
        return th;
    }
    byte[] SubBytes(int gi) { byte[] b = new byte[4 * F(gi, 20)]; Array.Copy(G, posSub + 4 * F(gi, 16), b, 0, b.Length); return b; }
    List<int> Subgroups(int gi)
    {
        List<int> r = new List<int>();
        for (int i = 0; i < F(gi, 20); i++)
        {
            int id = BitConverter.ToInt32(G, posSub + 4 * (F(gi, 16) + i)), sg;
            if (byId.TryGetValue(id, out sg)) r.Add(sg);
        }
        return r;
    }
    void Span(int k, out int fi, out bool patch, out long off, out long len)
    {
        int q = posSpan + 12 * k;
        uint f = BitConverter.ToUInt32(G, q);
        fi = (int)(f & 0x7FFFFFFF); patch = (f >> 31) != 0;
        len = BitConverter.ToUInt32(G, q + 4); off = BitConverter.ToUInt32(G, q + 8);
    }
    void Locator(int k, out int fi, out long off)
    {
        ulong v = BitConverter.ToUInt64(G, posLoc + 8 * k);
        fi = (int)(v & 0xFFFFFF); off = (long)(v >> 24);
    }

    // ---------------------------------------------------------------- structure report
    public void WriteGroups(string path)
    {
        using (StreamWriter w = new StreamWriter(path, false, new UTF8Encoding(false)))
        {
            w.WriteLine("GroupID\tNumObjects\tGroupSize\tSubGroupCount\tRootCount\tSpanCount\tTypeCount\tLinkSize\tLocatorCount\tUUIDs\ttypes_sha1\tlinks_sha1\tsubgroups_sha1");
            for (int gi = 0; gi < nGroups; gi++)
            {
                byte[] th = TypeBytes(gi), sb = SubBytes(gi);
                int ls = F(gi, 48), ln = F(gi, 52);
                string links = ls >= 0 && ls + ln <= L.Length ? Sha1(L, ls, ln, 12) : "out-of-range";
                w.WriteLine(string.Join("\t", new string[] {
                    F(gi, 0).ToString(), F(gi, 4).ToString(), BitConverter.ToInt64(G, gpos[gi] + 8).ToString(),
                    F(gi, 20).ToString(), F(gi, 28).ToString(), F(gi, 36).ToString(), F(gi, 44).ToString(),
                    ln.ToString(), F(gi, 60).ToString(), F(gi, 64).ToString(),
                    Sha1(th, 0, th.Length, 12), links, Sha1(sb, 0, sb.Length, 12) }));
            }
        }
    }

    public void WriteTypes(string path)
    {
        using (StreamWriter w = new StreamWriter(path, false, new UTF8Encoding(false)))
            for (int i = 0; i < nTypeHashes; i++) w.WriteLine(BitConverter.ToUInt64(G, posTypeHashes + 8 * i).ToString("X16"));
    }

    // ---------------------------------------------------------------- package files (DSAR: LZ4 chunks, or plain)
    class Archive
    {
        public string path; public FileStream f; public bool plain; public long total;
        public byte[] header, table; public long[] off, coff; public int[] size, csize;
    }
    Dictionary<int, Archive> archives = new Dictionary<int, Archive>();
    public string PathOf(int fi)
    {
        string name = Files[fi];
        int c = name.IndexOf(':');
        return (c >= 0 ? name.Substring(c + 1) : name).Replace('\\', '/');
    }
    Archive Open(int fi)
    {
        Archive a;
        if (archives.TryGetValue(fi, out a)) return a;
        a = new Archive();
        a.path = Path.Combine(cache, PathOf(fi).Replace('/', '\\'));
        a.f = new FileStream(a.path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        a.header = new byte[32];
        ReadFull(a.f, a.header, 32);
        if (BitConverter.ToUInt32(a.header, 0) != 0x52415344) { a.plain = true; a.total = a.f.Length; }
        else
        {
            int n = BitConverter.ToInt32(a.header, 8);
            a.total = BitConverter.ToInt64(a.header, 24);
            a.table = new byte[32 * n];
            ReadFull(a.f, a.table, a.table.Length);
            a.off = new long[n]; a.coff = new long[n]; a.size = new int[n]; a.csize = new int[n];
            for (int i = 0; i < n; i++)
            {
                a.off[i] = BitConverter.ToInt64(a.table, 32 * i); a.coff[i] = BitConverter.ToInt64(a.table, 32 * i + 8);
                a.size[i] = BitConverter.ToInt32(a.table, 32 * i + 16); a.csize[i] = BitConverter.ToInt32(a.table, 32 * i + 20);
            }
        }
        archives[fi] = a;
        return a;
    }
    public void CloseAll() { foreach (Archive a in archives.Values) a.f.Dispose(); archives.Clear(); }
    static void ReadFull(Stream s, byte[] b, int n)
    {
        int got = 0;
        while (got < n) { int r = s.Read(b, got, n - got); if (r <= 0) throw new Exception("short read"); got += r; }
    }
    static void Lz4(byte[] src, int sLen, byte[] dst, int dLen)
    {
        int s = 0, d = 0;
        while (s < sLen)
        {
            int token = src[s++];
            int lit = token >> 4;
            if (lit == 15) { int b; do { b = src[s++]; lit += b; } while (b == 255); }
            Buffer.BlockCopy(src, s, dst, d, lit); s += lit; d += lit;
            if (s >= sLen) break;
            int back = src[s] | (src[s + 1] << 8); s += 2;
            int ml = token & 15;
            if (ml == 15) { int b; do { b = src[s++]; ml += b; } while (b == 255); }
            ml += 4;
            int m = d - back;
            if (back <= 0 || m < 0) throw new Exception("bad LZ4 data");
            if (back >= ml) { Buffer.BlockCopy(dst, m, dst, d, ml); d += ml; }
            else for (int i = 0; i < ml; i++) dst[d++] = dst[m++];
        }
        if (d != dLen) throw new Exception("LZ4 size mismatch");
    }
    int ChunkAt(Archive a, long offset) { int i = Array.BinarySearch(a.off, offset); return i < 0 ? ~i - 1 : i; }
    string HashRange(int fi, long offset, long length)
    {
        Archive a = Open(fi);
        using (SHA1 h = SHA1.Create())
        {
            if (a.plain)
            {
                byte[] buf = new byte[1 << 20];
                a.f.Seek(offset, SeekOrigin.Begin);
                while (length > 0)
                {
                    int r = a.f.Read(buf, 0, (int)Math.Min(buf.Length, length));
                    if (r <= 0) throw new Exception("short read");
                    h.TransformBlock(buf, 0, r, null, 0); length -= r;
                }
            }
            else
            {
                int i = ChunkAt(a, offset);
                while (length > 0)
                {
                    if (BitConverter.ToUInt32(a.table, 32 * i + 24) % 256 != 3) throw new Exception("unknown chunk type");
                    byte[] src = new byte[a.csize[i]];
                    a.f.Seek(a.coff[i], SeekOrigin.Begin);
                    ReadFull(a.f, src, src.Length);
                    byte[] d = src;
                    if (a.csize[i] != a.size[i]) { d = new byte[a.size[i]]; Lz4(src, src.Length, d, d.Length); }
                    int s = (int)(offset - a.off[i]);
                    int take = (int)Math.Min(length, d.Length - s);
                    h.TransformBlock(d, s, take, null, 0);
                    offset += take; length -= take; i++;
                }
            }
            h.TransformFinalBlock(new byte[0], 0, 0);
            return Hex(h.Hash, 0);
        }
    }

    public string Detail(int[] ids)
    {
        StringBuilder s = new StringBuilder();
        s.Append("[");
        bool first = true;
        foreach (int id in ids)
        {
            int gi;
            if (!byId.TryGetValue(id, out gi)) continue;
            if (!first) s.Append(",");
            first = false;
            s.Append("\n{\"gid\":").Append(id).Append(",\"index\":").Append(gi);
            string[] names = { "NumObjects", "SubGroupStart", "SubGroupCount", "RootStart", "RootCount", "SpanStart", "SpanCount",
                               "TypeStart", "TypeCount", "LinkStart", "LinkSize", "LocatorStart", "LocatorCount" };
            int[] at = { 4, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60 };
            for (int k = 0; k < at.Length; k++) s.Append(",\"").Append(names[k]).Append("\":").Append(F(gi, at[k]));
            s.Append(",\"GroupSize\":").Append(BitConverter.ToInt64(G, gpos[gi] + 8));
            byte[] th = TypeBytes(gi);
            s.Append(",\"types_sha1\":\"").Append(Sha1(th, 0, th.Length, 0)).Append("\",\"types\":[");
            for (int i = 0; i < th.Length / 8; i++) s.Append(i > 0 ? "," : "").Append("\"").Append(BitConverter.ToUInt64(th, 8 * i).ToString("X16")).Append("\"");
            s.Append("],\"subgroups\":[");
            for (int i = 0; i < F(gi, 20); i++) s.Append(i > 0 ? "," : "").Append(BitConverter.ToUInt32(G, posSub + 4 * (F(gi, 16) + i)));
            s.Append("],\"spans\":[");
            for (int i = 0; i < F(gi, 36); i++)
            {
                int fi; bool patch; long off, len;
                Span(F(gi, 32) + i, out fi, out patch, out off, out len);
                string hash;
                try { hash = HashRange(fi, off, len); } catch (Exception e) { hash = "error: " + Esc(e.Message); }
                s.Append(i > 0 ? "," : "").Append("{\"file\":").Append(fi).Append(",\"patch\":").Append(patch ? 1 : 0)
                 .Append(",\"offset\":").Append(off).Append(",\"length\":").Append(len).Append(",\"sha1\":\"").Append(hash).Append("\"}");
            }
            s.Append("],\"locators\":[");
            for (int i = 0; i < F(gi, 60); i++)
            {
                int fi; long off;
                Locator(F(gi, 56) + i, out fi, out off);
                s.Append(i > 0 ? "," : "").Append("[").Append(fi).Append(",").Append(off).Append("]");
            }
            int ls = F(gi, 48), ln = F(gi, 52);
            s.Append("],\"links_sha1\":\"").Append(ls + ln <= L.Length ? Sha1(L, ls, ln, 0) : "out-of-range").Append("\"");
            s.Append(",\"links_b64\":\"").Append(ls + ln <= L.Length ? Convert.ToBase64String(L, ls, ln) : "").Append("\"}");
        }
        s.Append("\n]");
        CloseAll();
        return s.ToString();
    }

    // ---------------------------------------------------------------- extraction plan
    public List<int> FullFound = new List<int>(), Missing = new List<int>(), CoreOnly = new List<int>();
    public List<string> MissingFiles = new List<string>();
    long TotalOf(int fi) { try { return Open(fi).total; } catch (IOException) { return -1; } catch (UnauthorizedAccessException) { return -1; } }
    Dictionary<int, List<long[]>> ranges = new Dictionary<int, List<long[]>>();   // file -> [offset, end)
    Dictionary<int, bool[]> keep = new Dictionary<int, bool[]>();                 // DSAR file -> chunks taken
    public long Estimate;
    void Add(int fi, long a, long b)
    {
        List<long[]> r;
        if (!ranges.TryGetValue(fi, out r)) { r = new List<long[]>(); ranges[fi] = r; }
        r.Add(new long[] { a, b });
    }
    public void Plan(int[] fullIds)
    {
        HashSet<int> full = new HashSet<int>();
        foreach (int id in fullIds) { int gi; if (byId.TryGetValue(id, out gi)) { full.Add(gi); FullFound.Add(id); } else Missing.Add(id); }
        HashSet<int> all = new HashSet<int>(full);
        Stack<int> todo = new Stack<int>(full);
        while (todo.Count > 0) foreach (int sg in Subgroups(todo.Pop())) if (all.Add(sg)) todo.Push(sg);
        // where each stream ends: the next locator or span start in the same file (stream data is packed back to back)
        Dictionary<int, List<long>> bounds = new Dictionary<int, List<long>>();
        for (int k = 0; k < nLoc; k++) { int fi; long off; Locator(k, out fi, out off); Bound(bounds, fi, off); }
        for (int k = 0; k < nSpan; k++) { int fi; bool p; long off, len; Span(k, out fi, out p, out off, out len); Bound(bounds, fi, off); }
        foreach (List<long> v in bounds.Values) v.Sort();
        foreach (int gi in all)
        {
            if (!full.Contains(gi)) CoreOnly.Add(F(gi, 0));
            for (int i = 0; i < F(gi, 36); i++)
            {
                int fi; bool p; long off, len;
                Span(F(gi, 32) + i, out fi, out p, out off, out len);
                Add(fi, off, off + len);
            }
            if (!full.Contains(gi)) continue;
            for (int i = 0; i < F(gi, 60); i++)
            {
                int fi; long off;
                Locator(F(gi, 56) + i, out fi, out off);
                List<long> v = bounds[fi];
                int k = v.BinarySearch(off + 1);
                if (k < 0) k = ~k;
                long total = TotalOf(fi);
                long end = k < v.Count ? v[k] : total;
                Add(fi, off, total < 0 ? end : Math.Min(end, total));
            }
        }
        CoreOnly.Sort();
        foreach (int fi in new List<int>(ranges.Keys))     // not on disk (an uninstalled language pack, say)
            if (TotalOf(fi) < 0) { ranges.Remove(fi); MissingFiles.Add(PathOf(fi)); }
        Estimate = G.Length + L.Length;
        foreach (KeyValuePair<int, List<long[]>> kv in ranges)
        {
            Archive a = Open(kv.Key);
            if (a.plain) { foreach (long[] r in Merged(kv.Value)) Estimate += r[1] - r[0]; continue; }
            bool[] t = new bool[a.off.Length];
            foreach (long[] r in kv.Value)
                for (int i = Math.Max(0, ChunkAt(a, r[0])); i < t.Length && a.off[i] < r[1]; i++) t[i] = true;
            keep[kv.Key] = t;
            for (int i = 0; i < t.Length; i++) if (t[i]) Estimate += a.csize[i];
            Estimate += 32 + a.table.Length;
        }
    }
    static void Bound(Dictionary<int, List<long>> b, int fi, long off)
    {
        List<long> v;
        if (!b.TryGetValue(fi, out v)) { v = new List<long>(); b[fi] = v; }
        v.Add(off);
    }
    static List<long[]> Merged(List<long[]> r)
    {
        r.Sort(delegate(long[] x, long[] y) { return x[0].CompareTo(y[0]); });
        List<long[]> m = new List<long[]>();
        foreach (long[] x in r)
        {
            if (x[1] <= x[0]) continue;
            if (m.Count > 0 && x[0] <= m[m.Count - 1][1]) m[m.Count - 1][1] = Math.Max(m[m.Count - 1][1], x[1]);
            else m.Add(new long[] { x[0], x[1] });
        }
        return m;
    }

    // ---------------------------------------------------------------- package
    static void CopyRange(Stream from, long pos, long len, Stream to, byte[] buf)
    {
        from.Seek(pos, SeekOrigin.Begin);
        while (len > 0)
        {
            int r = from.Read(buf, 0, (int)Math.Min(buf.Length, len));
            if (r <= 0) throw new Exception("short read");
            to.Write(buf, 0, r); len -= r;
        }
    }
    public string WritePackage(ZipArchive z, Action<string> progress)
    {
        byte[] buf = new byte[1 << 20];
        StringBuilder s = new StringBuilder("[");
        int done = 0;
        List<int> files = new List<int>(ranges.Keys);
        files.Sort();
        foreach (int fi in files)
        {
            Archive a = Open(fi);
            string entry = "LocalCacheWinGame/" + PathOf(fi);
            long bytes = 0; int taken = 0, total = 0;
            if (a.plain)
            {
                List<long[]> m = Merged(ranges[fi]);
                using (Stream o = z.CreateEntry(entry + ".karin_ranges", CompressionLevel.Fastest).Open())
                {
                    BinaryWriter w = new BinaryWriter(o);
                    w.Write(0x474E524B); w.Write(1); w.Write(a.total); w.Write(m.Count);
                    foreach (long[] r in m) { w.Write(r[0]); w.Write(r[1] - r[0]); }
                    w.Flush();
                    foreach (long[] r in m) { CopyRange(a.f, r[0], r[1] - r[0], o, buf); bytes += r[1] - r[0]; }
                }
                total = taken = m.Count;
            }
            else
            {
                bool[] t = keep[fi];
                byte[] table = (byte[])a.table.Clone();
                long first = 32 + table.Length, pos = first;
                for (int i = 0; i < t.Length; i++) if (t[i]) { pos += a.csize[i]; taken++; }
                long end = pos;
                pos = first;
                for (int i = 0; i < t.Length; i++)
                {
                    if (t[i]) { Array.Copy(BitConverter.GetBytes(pos), 0, table, 32 * i + 8, 8); pos += a.csize[i]; }
                    else { Array.Copy(BitConverter.GetBytes(end), 0, table, 32 * i + 8, 8); Array.Copy(BitConverter.GetBytes(0), 0, table, 32 * i + 20, 4); }
                }
                total = t.Length;
                using (Stream o = z.CreateEntry(entry, CompressionLevel.Fastest).Open())
                {
                    o.Write(a.header, 0, 32);
                    o.Write(table, 0, table.Length);
                    for (int i = 0; i < t.Length; i++) if (t[i]) { CopyRange(a.f, a.coff[i], a.csize[i], o, buf); bytes += a.csize[i]; }
                }
            }
            s.Append(done > 0 ? "," : "").Append("\n{\"file\":\"").Append(Esc(PathOf(fi))).Append("\",\"index\":").Append(fi)
             .Append(",\"plain\":").Append(a.plain ? "true" : "false").Append(",\"taken\":").Append(taken).Append(",\"of\":").Append(total)
             .Append(",\"bytes\":").Append(bytes).Append("}");
            done++;
            if (progress != null) progress(string.Format("{0}/{1} {2}", done, files.Count, PathOf(fi)));
        }
        CloseAll();
        return s.Append("\n]").ToString();
    }
}
'@

# ------------------------------------------------------------------ run
if (-not (Test-Path $GraphPath) -or -not (Test-Path $LinksPath)) { Fail '找不到 streaming_graph.core 或 streaming_links.stream。' }
Say '正在读取 streaming_graph.core……'
$d = New-Object KarinCollect -ArgumentList $GraphPath, $LinksPath, $CacheRoot
if ($d.Files -contains 'cache:package/package.99.00.core.stream') {
    Fail '这份 streaming_graph.core 里有 Karin mod 的数据文件。请先运行“卸载.bat”（或在 Steam 里验证游戏文件），再运行本工具。'
}
if (-not $Out) { $Out = $Here }
$tag = ($version -replace '[^0-9A-Za-z.]', '_')
$name = if ($ReportOnly) { "KarinMod_diagnose_$tag" } else { "KarinMod_data_$tag" }
$zip = Join-Path $Out ($name + '.zip')
try { [IO.File]::OpenWrite($zip + '.test').Dispose(); Remove-Item ($zip + '.test') -Force }
catch { $zip = Join-Path ([Environment]::GetFolderPath('Desktop')) ($name + '.zip') }
if (-not $ReportOnly) {
    $d.Plan([int[]]$Full)
    $mb = [int]($d.Estimate / 1MB)
    Say ("要收集：{0} 个组的完整数据、{1} 个关联组的对象数据，zip 约 {2} MB。" -f $d.FullFound.Count, $d.CoreOnly.Count, $mb)
    if ($d.Missing.Count) { Say ('（这个版本里没有这些组：' + ($d.Missing -join ', ') + '）') }
    if ($d.MissingFiles.Count) { Say ('（这些数据文件不在硬盘上，跳过：' + ($d.MissingFiles -join ', ') + '）') }
    $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot((Resolve-Path (Split-Path -Parent $zip)).Path))
    if ($drive.AvailableFreeSpace -lt $d.Estimate + 200MB) { Fail ("{0} 的剩余空间不够（需要约 {1} MB）。请用 -Out 指定别的文件夹。" -f $drive.Name, ($mb + 200)) }
    if (-not $Yes) {
        Say "zip 会保存到：$zip"
        Say '按回车开始；不想继续就直接关掉这个窗口。'
        [void](Read-Host)
    }
}
if (Test-Path $zip) { Remove-Item $zip -Force }
$fs = [IO.File]::Open($zip, 'CreateNew')
$z = New-Object IO.Compression.ZipArchive -ArgumentList $fs, ([IO.Compression.ZipArchiveMode]::Create)
$ok = $false
try {
    function Add-Text([string]$entry, [string]$text) {
        $w = New-Object IO.StreamWriter -ArgumentList $z.CreateEntry($entry, [IO.Compression.CompressionLevel]::Optimal).Open(), (New-Object Text.UTF8Encoding $false)
        $w.Write($text); $w.Dispose()
    }
    $tmp = [IO.Path]::GetTempFileName()
    try {
        $d.WriteGroups($tmp); [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($z, $tmp, 'groups.tsv', 'Optimal')
        $d.WriteTypes($tmp); [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($z, $tmp, 'types.txt', 'Optimal')
    } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
    Say '正在核对 mod 相关的组……'
    $groupsJson = $d.Detail([int[]]$Detail)
    $meta = [ordered]@{
        format = 2; exe_version = $version; steam_buildid = $buildId
        graph_type_hash = $d.TypeHash.ToString('X16'); graph_length = $d.GraphLength; links_length = $d.LinksLength
        link_table_size = $d.LinkTableSize; link_table_id = $d.LinkTableId
        files = @($d.Files)
    }
    $metaJson = $meta | ConvertTo-Json -Depth 3 -Compress
    Add-Text 'report.json' ($metaJson.Substring(0, $metaJson.Length - 1) + ',"groups":' + $groupsJson + '}')
    if (-not $ReportOnly) {
        Say '正在复制 streaming_graph.core 和 streaming_links.stream……'
        [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($z, $GraphPath, 'LocalCacheWinGame/package/streaming_graph.core', 'Optimal')
        [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($z, $LinksPath, 'LocalCacheWinGame/package/streaming_links.stream', 'Optimal')
        Say '正在收集游戏数据（会读取几 GB 的游戏文件，需要几分钟）……'
        $filesJson = $d.WritePackage($z, [Action[string]]{ param($m) Write-Host "  $m" })
        $c = [ordered]@{ format = 1; exe_version = $version; steam_buildid = $buildId
                         full = @($d.FullFound); missing = @($d.Missing); missing_files = @($d.MissingFiles)
                         core_only = @($d.CoreOnly) }
        $cj = $c | ConvertTo-Json -Depth 3 -Compress
        Add-Text 'collect.json' ($cj.Substring(0, $cj.Length - 1) + ',"files":' + $filesJson + '}')
    }
    $ok = $true
} finally {
    $z.Dispose(); $fs.Dispose()
    if (-not $ok) { Remove-Item $zip -Force -ErrorAction SilentlyContinue }
}
Say ''
Write-Host "完成：$zip" -ForegroundColor Green
$size = (Get-Item $zip).Length
if ($ReportOnly) {
    Say ('（{0} KB，只有游戏数据的结构信息）请把这个 zip 发给 mod 作者。' -f [int]($size / 1KB))
} else {
    Say ('（{0} MB）请把这个 zip 上传到网盘发给 mod 作者。里面是 mod 涉及的那部分游戏数据，不含 DS2.exe，不含存档。' -f [int]($size / 1MB))
}
