using System.Text;
using System.Text.RegularExpressions;
using ReeLib;
using ReeLib.Pak;

namespace DD2Tool;

internal static class Program
{
    static int Main(string[] args)
    {
        if (args.Length == 0) { Help(); return 1; }
        try {
            switch (args[0]) {
                case "toc": return Toc(args[1], args[2]);
                case "resolve": return Resolve(args[1], args[2], args[3], args.Length > 4 ? args[4] : null);
                case "extract": return Extract(args[1], args[2], args[3], args[4]);
                case "meshinfo": return MeshTools.MeshInfo(args[1], args[2]);
                case "meshconv": return MeshTools.MeshConv(args[1], args[2], args[3]);
                case "rszdump": return RszTools.Dump(args[1], args[2], args[3], args.Length > 4 ? int.Parse(args[4]) : 12);
                case "pack": return Pack(args[1], args[2]);
                case "meshdiag": return MeshDiag.Run(args[1], args[2]);
                case "mdfinfo": return MdfTools.Info(args[1], args[2]);
                case "meshreorder": return MeshReorder.Run(args[1], args[2], args[3]);
                case "tex2dds": return TexTools.ToDds(args[1], args[2]);
                case "dds2tex": return TexTools.FromDds(args[1], args[2], args[3]);
                case "mdfrt": return MdfBuild.RoundTrip(args[1], args[2]);
                case "mdfbuild": return MdfBuild.Build(args[1]);
                case "chaininfo": return ChainTools.Info(args[1], args[2]);
                case "chainrt": return ChainTools.RoundTrip(args[1], args[2]);
                case "chainbuild": return ChainBuild.Build(args[1]);
                default: Help(); return 1;
            }
        } catch (Exception e) {
            Console.Error.WriteLine("FAIL: " + e);
            return 2;
        }
    }

    static void Help()
    {
        Console.WriteLine("DD2Tool toc <pak> <out.tsv>");
        Console.WriteLine("DD2Tool resolve <pak> <oldList> <outList> [extraVersionsSpec]  (spec: ext=ver,ext=ver)");
        Console.WriteLine("DD2Tool extract <pak> <list> <regex> <outDir>");
        Console.WriteLine("DD2Tool meshinfo <mesh> <out.json>");
        Console.WriteLine("DD2Tool rszdump <reeResDir> <file.pfb|user|scn> <out.txt> [maxDepth]");
        Console.WriteLine("DD2Tool meshconv <inMesh> <outMesh> <versionConfig e.g. 'DD2' | 'DD2 (old v2)'>");
        Console.WriteLine("DD2Tool pack <out.pak> <rootDir containing natives/>");
    }

    static int Pack(string outPak, string rootDir)
    {
        var w = new PakWriter();
        w.AddFilesFromDirectory(rootDir, true);
        w.SaveTo(outPak);
        var check = OpenPak(outPak);
        foreach (var f in Directory.EnumerateFiles(rootDir, "*", SearchOption.AllDirectories)) {
            var rel = Path.GetRelativePath(rootDir, f).Replace('\\', '/');
            var h = PakUtils.GetFilepathHash(rel);
            var ok = check.Entries.Any(e => e.CombinedHash == h);
            Console.WriteLine($"  {(ok ? "OK " : "MISSING")} {rel} ({new FileInfo(f).Length} B)");
        }
        return 0;
    }

    static PakFile OpenPak(string pak)
    {
        var p = new PakFile { filepath = pak, IncludeUnknowns = true };
        p.ReadContents(pak, new Dictionary<ulong, string>());
        Console.WriteLine($"PAK {pak}: v{p.Header.majorVersion}.{p.Header.minorVersion} feature=0x{(int)p.Header.featureFlags:X} files={p.Header.fileCount} entries={p.Entries.Count} remaps={p.Remaps?.Entries.Length ?? 0} chunks={p.ChunkEntries?.chunks.Length ?? 0}");
        return p;
    }

    static int Toc(string pak, string outPath)
    {
        var p = OpenPak(pak);
        using var w = new StreamWriter(outPath, false, new UTF8Encoding(false));
        w.WriteLine("hash\toffset\tcsize\tdsize\tcompression\tencryption\toffsetType");
        foreach (var e in p.Entries) {
            w.WriteLine($"{e.CombinedHash:X16}\t{e.offset}\t{e.compressedSize}\t{e.decompressedSize}\t{e.compression}\t{e.encryption}\t{e.offsetType}");
        }
        if (p.Remaps != null) {
            using var rw = new StreamWriter(outPath + ".remaps.tsv", false, new UTF8Encoding(false));
            foreach (var r in p.Remaps.Entries) rw.WriteLine($"{r.a1:X8}\t{r.a2:X8}\t{r.b1:X8}\t{r.b2:X8}");
        }
        return 0;
    }

    static readonly Regex PathRx = new(@"^(?<base>.+?)\.(?<ext>[A-Za-z0-9_]+)\.(?<ver>\d+)(?<suffix>(?:\.[A-Za-z0-9]+)*)$", RegexOptions.Compiled);

    // Known new DD2 (TU3.2, 2026-09) date-versioned formats (from RE-Engine-Lib bf0e5e5).
    static readonly Dictionary<string, int> KnownNew = new(StringComparer.OrdinalIgnoreCase) {
        ["mesh"] = 260421070,
        ["tex"] = 251211553,
        ["gpuc"] = 260421224,
    };

    static int Resolve(string pak, string oldList, string outList, string? extraSpec)
    {
        var known = new Dictionary<string, int>(KnownNew, StringComparer.OrdinalIgnoreCase);
        if (!string.IsNullOrEmpty(extraSpec)) {
            foreach (var kv in extraSpec.Split(',', StringSplitOptions.RemoveEmptyEntries)) {
                var parts = kv.Split('=');
                known[parts[0]] = int.Parse(parts[1]);
            }
        }
        var p = OpenPak(pak);
        var toc = new HashSet<ulong>(p.Entries.Select(e => e.CombinedHash));
        var found = new Dictionary<ulong, string>();
        var stats = new SortedDictionary<string, int>(StringComparer.Ordinal);
        int lines = 0;
        foreach (var raw in File.ReadLines(oldList)) {
            var line = raw.Trim();
            if (line.Length == 0) continue;
            lines++;
            var cands = new List<(string path, string tag)> { (line, "same") };
            var m = PathRx.Match(line);
            if (m.Success) {
                var ext = m.Groups["ext"].Value;
                var ver = long.Parse(m.Groups["ver"].Value);
                var b = m.Groups["base"].Value;
                var sfx = m.Groups["suffix"].Value;
                if (known.TryGetValue(ext, out var nv) && nv != ver) cands.Add(($"{b}.{ext}.{nv}{sfx}", $"{ext}:{ver}->{nv}"));
                if (ver < 100000) {
                    for (int d = 1; d <= 12; d++) cands.Add(($"{b}.{ext}.{ver + d}{sfx}", $"{ext}:{ver}->{ver + d}"));
                }
            }
            foreach (var (c, tag) in cands) {
                var h = PakUtils.GetFilepathHash(c);
                if (toc.Contains(h)) {
                    if (found.TryAdd(h, c)) {
                        var ext = m.Success ? m.Groups["ext"].Value.ToLowerInvariant() : "?";
                        var key = tag == "same" ? $"{ext}:{(m.Success ? m.Groups["ver"].Value : "")} same" : tag;
                        stats[key] = stats.GetValueOrDefault(key) + 1;
                    }
                    break;
                }
            }
        }
        File.WriteAllLines(outList, found.Values.OrderBy(x => x, StringComparer.Ordinal), new UTF8Encoding(false));
        Console.WriteLine($"old list lines={lines} toc={toc.Count} resolved={found.Count} unknown={toc.Count - found.Count}");
        foreach (var kv in stats) Console.WriteLine($"  {kv.Key}\t{kv.Value}");
        return 0;
    }

    static int Extract(string pak, string list, string regex, string outDir)
    {
        var reader = new PakReader { Filter = new Regex(regex, RegexOptions.IgnoreCase), MaxThreads = 8 };
        reader.PakFilePriority.Add(pak);
        reader.AddFilesFromListFile(list);
        var missing = new List<string>();
        var n = reader.UnpackFilesTo(outDir, missing);
        Console.WriteLine($"extracted={n} missing={missing.Count}");
        foreach (var mm in missing.Take(50)) Console.WriteLine("  missing: " + mm);
        return 0;
    }
}
