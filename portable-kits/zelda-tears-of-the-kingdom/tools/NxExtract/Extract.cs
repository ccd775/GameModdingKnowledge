using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using LibHac.Common;
using LibHac.Common.Keys;
using LibHac.Fs;
using LibHac.Fs.Fsa;
using LibHac.FsSystem;
using LibHac.Tools.Fs;
using LibHac.Tools.FsSystem;
using LibHac.Tools.FsSystem.NcaUtils;
using LibHac.Tools.FsSystem.RomFs;
using IOPath = System.IO.Path;

public static class NxExtract
{
    static KeySet Keys(string prod, string title)
    {
        var ks = KeySet.CreateDefaultKeySet();
        ExternalKeyReader.ReadKeyFile(ks, prod, title, null, null);
        return ks;
    }

    static IEnumerable<(string name, IStorage storage)> NcasIn(KeySet ks, string src)
    {
        if (src.EndsWith(".xci", StringComparison.OrdinalIgnoreCase))
        {
            var xci = new Xci(ks, new LocalStorage(src, FileAccess.Read));
            var part = xci.OpenPartition(XciPartitionType.Secure);
            foreach (var e in part.EnumerateEntries("*.nca", SearchOptions.Default))
            {
                using var f = new UniqueRef<IFile>();
                part.OpenFile(ref f.Ref, e.FullPath.ToU8Span(), OpenMode.Read).ThrowIfFailure();
                yield return ("xci:" + e.Name, f.Release().AsStorage());
            }
        }
        else if (Directory.Exists(src))
        {
            foreach (var p in Directory.GetFiles(src, "*.nca", SearchOption.AllDirectories))
                yield return (p, new LocalStorage(p, FileAccess.Read));
        }
        else yield return (src, new LocalStorage(src, FileAccess.Read));
    }

    public static string List(string prod, string title, string[] sources)
    {
        var ks = Keys(prod, title);
        var sb = new System.Text.StringBuilder();
        foreach (var src in sources)
            foreach (var (name, st) in NcasIn(ks, src))
            {
                try
                {
                    var nca = new Nca(ks, st);
                    var h = nca.Header;
                    sb.AppendLine($"{name}\t{h.TitleId:X16}\t{h.ContentType}\tkeygen={h.KeyGeneration}\trights={(h.HasRightsId ? "yes" : "no")}\tsize={st.GetSize(out long sz).IsSuccess() switch { true => sz, _ => -1 }}\tdata={(nca.CanOpenSection(NcaSectionType.Data))}");
                }
                catch (Exception ex) { sb.AppendLine($"{name}\tERROR {ex.GetType().Name}: {ex.Message}"); }
            }
        return sb.ToString();
    }

    static IFileSystem OpenRomFs(KeySet ks, string baseSpec, string patchSpec)
    {
        Nca Find(string spec)
        {
            // spec: "<source>|<ncaNameOrPath>"
            var parts = spec.Split('|');
            foreach (var (name, st) in NcasIn(ks, parts[0]))
                if (parts.Length == 1 || name.EndsWith(parts[1], StringComparison.OrdinalIgnoreCase)) return new Nca(ks, st);
            throw new FileNotFoundException(spec);
        }
        var baseNca = Find(baseSpec);
        IStorage s = string.IsNullOrEmpty(patchSpec)
            ? baseNca.OpenStorage(NcaSectionType.Data, IntegrityCheckLevel.None)
            : baseNca.OpenStorageWithPatch(Find(patchSpec), NcaSectionType.Data, IntegrityCheckLevel.None);
        return new RomFsFileSystem(s);
    }

    static Regex Glob(string g) => new Regex("^" + Regex.Escape(g.Replace((char)92, '/')).Replace(@"\*\*", ".*").Replace(@"\*", "[^/]*").Replace(@"\?", ".") + "$", RegexOptions.IgnoreCase);

    // mode "ls": list matches; mode "x": extract matches into outDir
    public static string Run(string mode, string prod, string title, string baseSpec, string patchSpec, string outDir, string[] patterns)
    {
        var ks = Keys(prod, title);
        var fs = OpenRomFs(ks, baseSpec, patchSpec);
        var rx = patterns.Select(Glob).ToArray();
        var sb = new System.Text.StringBuilder();
        long total = 0; int count = 0;
        foreach (var e in fs.EnumerateEntries("/", "*", SearchOptions.RecurseSubdirectories))
        {
            if (e.Type != DirectoryEntryType.File) continue;
            string rel = e.FullPath.TrimStart('/');
            if (!rx.Any(r => r.IsMatch(rel))) continue;
            count++; total += e.Size;
            if (mode == "ls") { sb.AppendLine($"{e.Size}\t{rel}"); continue; }
            string dst = IOPath.Combine(outDir, rel.Replace('/', IOPath.DirectorySeparatorChar));
            Directory.CreateDirectory(IOPath.GetDirectoryName(dst));
            using var f = new UniqueRef<IFile>();
            fs.OpenFile(ref f.Ref, e.FullPath.ToU8Span(), OpenMode.Read).ThrowIfFailure();
            using var src = f.Get.AsStream();
            using var o = File.Create(dst);
            src.CopyTo(o);
        }
        sb.AppendLine($"matched {count} files, {total} bytes");
        return sb.ToString();
    }
}
