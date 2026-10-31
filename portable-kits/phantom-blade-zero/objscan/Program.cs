// objscan: locate the UObject array of a running UE game whose GUObjectArray layout defeats UE4SS / Dumper-7 scans.
// Usage: objscan <pid|exe name>
// Scans every writable section of the main module for a pointer P such that either P (fixed array) or *P (first chunk)
// holds FUObjectItems whose Object->(int32 at k) == item index for consecutive indices. Prints the hit, stride, object
// offset inside the item, InternalIndex offset inside UObject, and the surrounding dwords (to read Num/Max fields).
using System.Diagnostics;
using System.Runtime.InteropServices;

static class N
{
    [DllImport("kernel32")] public static extern IntPtr OpenProcess(uint a, bool i, int pid);
    [DllImport("kernel32")] public static extern bool ReadProcessMemory(IntPtr h, IntPtr a, byte[] b, IntPtr n, out IntPtr r);
}

class Mem
{
    readonly IntPtr h; readonly Dictionary<ulong, byte[]> pages = new();
    public Mem(IntPtr h) { this.h = h; }
    public byte[] Page(ulong p)
    {
        if (pages.TryGetValue(p, out var b)) return b;
        b = new byte[4096];
        if (!N.ReadProcessMemory(h, (IntPtr)(long)p, b, (IntPtr)4096, out var r) || (long)r != 4096) b = null;
        if (pages.Count > 400000) pages.Clear();
        pages[p] = b; return b;
    }
    public bool Q(ulong a, out ulong v)
    {
        v = 0; var pg = Page(a & ~0xFFFUL); if (pg == null) return false; int o = (int)(a & 0xFFF);
        if (o > 4088) { var lo = new byte[8]; for (int i = 0; i < 8; i++) { if (!B(a + (ulong)i, out lo[i])) return false; } v = BitConverter.ToUInt64(lo); return true; }
        v = BitConverter.ToUInt64(pg, o); return true;
    }
    public bool D(ulong a, out int v) { v = 0; if (!Q(a, out var q)) return false; v = (int)(uint)q; return true; }
    bool B(ulong a, out byte v) { v = 0; var pg = Page(a & ~0xFFFUL); if (pg == null) return false; v = pg[a & 0xFFF]; return true; }
    public byte[] Read(ulong a, int n) { var b = new byte[n]; N.ReadProcessMemory(h, (IntPtr)(long)a, b, (IntPtr)n, out _); return b; }
}

class P
{
    static ulong modLo, modHi;
    static bool Heap(ulong v) => v >= 0x10000 && v < 0x7FFFFFFFFFFF && (v & 7) == 0 && (v < modLo || v >= modHi);
    static bool InMod(ulong v) => v >= modLo && v < modHi;

    static int Main(string[] a)
    {
        Process pr = int.TryParse(a[0], out int pid) ? Process.GetProcessById(pid)
            : Process.GetProcessesByName(Path.GetFileNameWithoutExtension(a[0])).OrderByDescending(x => x.WorkingSet64).First();
        var h = N.OpenProcess(0x0410, false, pr.Id);
        if (h == IntPtr.Zero) { Console.WriteLine("OpenProcess failed " + Marshal.GetLastWin32Error()); return 1; }
        var m = new Mem(h);
        ulong bas = (ulong)(long)pr.MainModule.BaseAddress;
        var hdr = m.Read(bas, 0x1000);
        int pe = BitConverter.ToInt32(hdr, 0x3C);
        int nsec = BitConverter.ToUInt16(hdr, pe + 6), optSz = BitConverter.ToUInt16(hdr, pe + 20);
        uint sizeImg = BitConverter.ToUInt32(hdr, pe + 24 + 56);
        modLo = bas; modHi = bas + sizeImg;
        Console.WriteLine($"pid {pr.Id} base 0x{bas:X} size 0x{sizeImg:X}");
        int sh = pe + 24 + optSz;
        var secs = new List<(string n, ulong va, uint sz, uint ch)>();
        for (int i = 0; i < nsec; i++)
        {
            int o = sh + i * 40;
            string n = System.Text.Encoding.ASCII.GetString(hdr, o, 8).TrimEnd('\0');
            secs.Add((n, BitConverter.ToUInt32(hdr, o + 12), BitConverter.ToUInt32(hdr, o + 8), BitConverter.ToUInt32(hdr, o + 36)));
            Console.WriteLine($"  sec {n,-8} va 0x{secs[^1].va:X} size 0x{secs[^1].sz:X} ch 0x{secs[^1].ch:X}");
        }
        int hits = 0; var sw = Stopwatch.StartNew();
        foreach (var s in secs.Where(s => (s.ch & 0x80000000) != 0))
        {
            for (ulong off = 0; off + 8 <= s.sz; off += 8)
            {
                ulong at = bas + s.va + off;
                if (!m.Q(at, out var p) || !Heap(p)) continue;
                foreach (bool chunked in new[] { true, false })
                {
                    ulong items = p;
                    if (chunked) { if (!m.Q(p, out items) || !Heap(items)) continue; }
                    if (Test(m, items, out int S, out int oo, out int k, out int good))
                    {
                        hits++;
                        Console.WriteLine($"HIT {(chunked ? "chunked" : "fixed")} at 0x{at:X} (rva 0x{at - bas:X}, {s.n}) items 0x{items:X} stride {S} objOff {oo} idxOff 0x{k:X} good {good}");
                        var w = m.Read(at - 0x20, 0x60);
                        for (int j = 0; j < 0x60; j += 16)
                            Console.WriteLine($"   {(long)j - 0x20,4:X}: {BitConverter.ToUInt64(w, j):X16} {BitConverter.ToUInt64(w, j + 8):X16}  ({BitConverter.ToInt32(w, j)},{BitConverter.ToInt32(w, j + 4)},{BitConverter.ToInt32(w, j + 8)},{BitConverter.ToInt32(w, j + 12)})");
                        if (chunked)
                        {
                            for (int c = 0; c < 40; c++) { m.Q(p + (ulong)c * 8, out var cp); if (cp == 0) { Console.WriteLine($"   chunks: {c} non-null before first null"); break; } }
                        }
                        if (hits > 30) return 0;
                    }
                }
            }
        }
        Console.WriteLine($"done hits {hits} in {sw.Elapsed.TotalSeconds:F1}s");
        return 0;
    }

    static bool Test(Mem m, ulong items, out int S, out int oo, out int k, out int good)
    {
        S = oo = k = good = 0;
        foreach (int s in new[] { 16, 24, 32, 40, 48, 56, 64 })
            foreach (int o in new[] { 0, 8, 16 })
            {
                if (o >= s) continue;
                if (!m.Q(items + (ulong)(s + o), out var o1) || !Heap(o1)) continue;
                if (!m.Q(o1, out var vt) || !InMod(vt)) continue;
                for (int kk = 8; kk <= 0x38; kk += 4)
                {
                    if (!m.D(o1 + (ulong)kk, out int v) || v != 1) continue;
                    int g = 0;
                    for (int i = 1; i <= 32; i++)
                    {
                        if (!m.Q(items + (ulong)(i * s + o), out var oi) || !Heap(oi)) continue;
                        if (m.D(oi + (ulong)kk, out int vi) && vi == i) g++;
                    }
                    if (g >= 24) { S = s; oo = o; k = kk; good = g; return true; }
                }
            }
        return false;
    }
}
