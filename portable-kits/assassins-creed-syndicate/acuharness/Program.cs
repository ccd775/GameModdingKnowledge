// Headless driver for AnvilToolkit.dll (1.3.x), forked from ACOd/tools/AcoHarness for Assassin's Creed Unity.
// Game = env ACU_GAME (AnvilToolkit Game enum name), default Unity.
// Commands are added incrementally; see Usage().
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using AnvilToolkit.FileTypes.AnvilNext.Containers;
using AnvilToolkit.Utils;

static class Harness
{
    static readonly Game G = Enum.Parse<Game>(Environment.GetEnvironmentVariable("ACU_GAME") ?? "Unity");

    static int Main(string[] args)
    {
        if (args.Length < 1) { Usage(); return 2; }
        if (Environment.GetEnvironmentVariable("ACSH_DEBUG") == "1")
            AppDomain.CurrentDomain.FirstChanceException += (s, e) =>
                Console.Error.WriteLine("FIRST-CHANCE " + e.Exception.GetType().Name + ": " + e.Exception.Message + Environment.NewLine + new System.Diagnostics.StackTrace(1, true));
        string atkDir = Environment.GetEnvironmentVariable("ATK_DIR") ?? AppContext.BaseDirectory;
        DataStorage.ActiveGame = G;
        // 1.3.6 embeds ACOdyssey.schema / ACOrigins.schema but leaves them out of SchemaFileNames
        DataStorage.SchemaFileNames.TryAdd(Game.Odyssey, "ACOdyssey");
        DataStorage.SchemaFileNames.TryAdd(Game.Origins, "ACOrigins");
        if (DataStorage.GlobalScimitarClassReader == null)
            DataStorage.GlobalScimitarClassReader = new AnvilToolkit.FileTypes.AnvilNext.ScimitarClassReader();
        DataStorage.DirectXTexPath = Path.Combine(AppContext.BaseDirectory, "Libs", "DirectXTexNetImpl.dll");
        DataStorage.ElapsedTime = (uint)DateTime.UtcNow.Subtract(new DateTime(1970, 1, 1)).TotalSeconds;
        DataStorage.TempPath = Path.Combine(Path.GetTempPath(), "AnvilToolkit");
        Directory.CreateDirectory(DataStorage.TempPath);
        DataStorage.OodleLocation = Path.Combine(atkDir, "Libs");
        string rt = Environment.GetEnvironmentVariable("ATK_RUNTIME")
            ?? AppContext.BaseDirectory;
        args = FixArgs(args);
        if (Directory.Exists(rt)) Directory.SetCurrentDirectory(rt);
        Preload();
        if (args[0].ToLowerInvariant() == "batch")
        {
            // batch <commands.tsv>: one command per line (tab-separated, absolute paths) in this process, so the
            // ~1-2 s startup + name-table preload is paid once; prints "BATCH <n> rc=<rc>" after each command
            int bad = 0, n = 0;
            foreach (var line in File.ReadAllLines(args[1]))
            {
                if (line.Trim().Length == 0) continue;
                int rc = Dispatch(FixArgs(line.Split('\t')));
                Console.WriteLine($"BATCH {++n} rc={rc}");
                Console.Out.Flush();
                if (rc != 0) bad++;
            }
            return bad == 0 ? 0 : 1;
        }
        return Dispatch(args);
    }

    // relative paths resolve against the caller's directory (Main then switches to the runtime dir)
    static string[] FixArgs(string[] args)
    {
        for (int i = 0; i < args.Length; i++)
            if (args[i].Contains('/') || args[i].Contains('\\') || args[i].StartsWith("."))
                args[i] = Path.GetFullPath(args[i]);
        int ri = Array.IndexOf(args, "--rawdir");
        if (ri >= 0)
        {
            SetExplorerPath(Path.GetFullPath(args[ri + 1]));
            args = args.Where((a, i) => i != ri && i != ri + 1).ToArray();
        }
        return args;
    }

    static int Dispatch(string[] args)
    {
        try
        {
            switch (args[0].ToLowerInvariant())
            {
                case "games":
                    foreach (var g in Enum.GetValues<Game>())
                        Console.WriteLine($"{(int)g}	{g}	schema={(DataStorage.SchemaFileNames.TryGetValue(g, out var sn) ? sn : "-")}");
                    return 0;
                case "unpack-data":
                    return UnpackData(args[1], args[2]);
                case "export-xml":
                    DataStorage.LoadSchema();
                    for (int i = 1; i + 1 < args.Length; i += 2) ExportXml(args[i], args[i + 1]);
                    return 0;
                case "export-xml-dir":
                    DataStorage.LoadSchema();
                    return ExportXmlDir(args[1], args[2], args.Length > 3 ? args[3] : "*");
                case "debug-data":
                {
                    using var br = new System.IO.BinaryReader(File.OpenRead(args[1]));
                    var a = new CompressedFileData(br, G);
                    var b = new CompressedFileData(br, G);
                    Console.WriteLine($"meta {a.Data?.Length} files {b.Data?.Length}");
                    return 0;
                }
                case "unpack-export":
                {
                    // unpack-export <outroot> <data...>: <outroot>/unpacked/<name>/ and <outroot>/xml/<name>/
                    DataStorage.LoadSchema();
                    int bad = 0;
                    for (int i = 2; i < args.Length; i++)
                    {
                        string nm = Path.GetFileNameWithoutExtension(args[i]);
                        string ud = Path.Combine(args[1], "unpacked", nm);
                        if (!Directory.Exists(ud) && UnpackData(args[i], ud) != 0) { bad++; continue; }
                        bad += ExportXmlDir(ud, Path.Combine(args[1], "xml", nm), "*", SkipExt);
                    }
                    return bad == 0 ? 0 : 1;
                }
                case "export-glb":
                {
                    // export-glb <out.glb> <files...>: .Mesh and .Skeleton resource files (first skeleton = main)
                    DataStorage.LoadSchema();
                    var meshes = new List<AnvilToolkit.FileTypes.AnvilNext.Models.Mesh>();
                    var skels = new List<AnvilToolkit.FileTypes.AnvilNext.Models.Skeleton>();
                    for (int i = 2; i < args.Length; i++)
                    {
                        Console.WriteLine($"load {Path.GetFileName(args[i])}");
                        var sf = new AnvilToolkit.FileTypes.AnvilNext.ScimitarFile(args[i], G);
                        if (sf.Data is AnvilToolkit.FileTypes.AnvilNext.Models.Mesh m)
                        {
                            if (string.IsNullOrEmpty(m.Name)) m.Name = Path.GetFileNameWithoutExtension(args[i]).Split("_-_").Last();
                            meshes.Add(m);
                        }
                        else if (sf.Data is AnvilToolkit.FileTypes.AnvilNext.Models.Skeleton s)
                        {

                            skels.Add(s);
                        }
                        else Console.WriteLine($"skip {args[i]}: {sf.Data?.GetType().Name}");
                    }
                    AnvilToolkit.FileTypes.AnvilNext.Models.AnvilGLTF.CreateGLTF(args[1], meshes, skels,
                        new List<AnvilToolkit.FileTypes.AnvilNext.Physics.SoftBody>());
                    Console.WriteLine($"GLB {args[1]}: {meshes.Count} meshes, {skels.Count} skeletons");
                    return 0;
                }
                case "debug-mesh":
                {
                    DataStorage.LoadSchema();
                    using var br = new AnvilToolkit.BiendianBinaryReader(new MemoryStream(File.ReadAllBytes(args[1])));
                    new AnvilToolkit.FileTypes.AnvilNext.ScimitarFile(G).ReadHeader(br, G);
                    var sc = new AnvilToolkit.FileTypes.AnvilNext.ScimitarClass(br, G, 0u);
                    Console.WriteLine($"class hash {sc.Hash}");
                    if (sc.Hash == 1096652136u)
                        new AnvilToolkit.FileTypes.AnvilNext.Models.Mesh(sc).ReadFromFileRPG(br);
                    else
                        typeof(AnvilToolkit.FileTypes.AnvilNext.Models.Skeleton).GetConstructor(new[] { typeof(AnvilToolkit.FileTypes.AnvilNext.ScimitarClass) })!
                            .Invoke(new object[] { sc });
                    return 0;
                }
                case "mesh-info":
                {
                    DataStorage.LoadSchema();
                    for (int i = 1; i < args.Length; i++)
                    {
                        var sf = new AnvilToolkit.FileTypes.AnvilNext.ScimitarFile(args[i], G);
                        if (sf.Data is not AnvilToolkit.FileTypes.AnvilNext.Models.Mesh m || m.Failed) { Console.WriteLine($"{args[i]}: not a mesh / failed"); continue; }
                        var v0 = m.Vertices.Count > 0 ? m.Vertices[0] : null;
                        Console.WriteLine($"{Path.GetFileName(args[i])}: id={m.ID:X16} verts={m.Vertices.Count} faces={m.Faces.Count} prims={m.Primitives.Count} bones={m.Bones.Count} " +
                            $"fmt={v0?.Format} mfmt={m.VertexFormat} stride={m.VertexStride} joints={v0?.JointCount} scale={m.Scale} vscale=({m.VertexScale.x},{m.VertexScale.y},{m.VertexScale.z}) " +
                            $"mats={string.Join(",", m.CompiledMeshMaterials.Select(r => r.ToString()))} blendshapes={m.BlendShapesData.Count} skinwrap={m.SkinWrapProxies.Count} useSkinWrap={m.UseSkinWrap} useBlend={m.UseBlendShape}");
                    }
                    return 0;
                }
                case "scan-refs":
                {
                    // scan-refs <forge> <list.tsv: offset\tsize\tlabel> <idHex,idHex,...> [classId]
                    // decompress each data file in memory; print objects (optionally of one class) containing any needle ID
                    var needles = args[3].Split(',').Select(h => (h, BitConverter.GetBytes(Convert.ToUInt64(h, 16)))).ToArray();
                    uint cls = args.Length > 4 ? uint.Parse(args[4]) : 0u;
                    using var forge = File.OpenRead(args[1]);
                    int n = 0, hits = 0;
                    foreach (var line in File.ReadLines(args[2]))
                    {
                        var p = line.Split('\t');
                        var buf = new byte[int.Parse(p[1])];
                        forge.Position = long.Parse(p[0]); forge.ReadExactly(buf);
                        n++;
                        try
                        {
                            var df = new DataFile(buf, G);
                            foreach (var fd in df.FilesByID.Values)
                            {
                                if (cls != 0 && fd.Type != cls || fd.Data == null) continue;
                                foreach (var (h, nb) in needles)
                                    if (fd.Data.AsSpan().IndexOf(nb) >= 0) { Console.WriteLine($"HIT\t{h}\t{fd.ID:X16}\t{fd.Name}\t{p[2]}"); hits++; }
                            }
                        }
                        catch (Exception e) { Console.WriteLine($"ERR\t{p[2]}\t{e.GetType().Name}"); }
                        if (n % 200 == 0) Console.Error.WriteLine($"{n} scanned, {hits} hits");
                    }
                    Console.WriteLine($"DONE {n} data files, {hits} hits");
                    return 0;
                }
                case "scan-objs":
                {
                    // scan-objs <forge> <list.tsv: offset\tsize\tlabel> <idHex,idHex,...>
                    // decompress each data file in memory; print every object whose own ID is one of the needles
                    // (Unity embeds copies of the same objects, e.g. Arno's BuildTables, in several data files)
                    var want = args[3].Split(',').Select(h => Convert.ToUInt64(h, 16)).ToHashSet();
                    using var forge = File.OpenRead(args[1]);
                    int n = 0, hits = 0;
                    foreach (var line in File.ReadLines(args[2]))
                    {
                        var p = line.Split('\t');
                        var buf = new byte[int.Parse(p[1])];
                        forge.Position = long.Parse(p[0]); forge.ReadExactly(buf);
                        n++;
                        try
                        {
                            var df = new DataFile(buf, G);
                            foreach (var fd in df.FilesByID.Values)
                                if (want.Contains(fd.ID)) { Console.WriteLine($"OBJ\t{fd.ID:X16}\t{fd.Name}\t{p[2]}"); hits++; }
                        }
                        catch (Exception e) { Console.WriteLine($"ERR\t{p[2]}\t{e.GetType().Name}"); }
                        if (n % 500 == 0) Console.Error.WriteLine($"{n} scanned, {hits} hits");
                    }
                    Console.WriteLine($"DONE {n} data files, {hits} hits");
                    return 0;
                }
                case "mesh-binds":
                {
                    // mesh-binds <mesh> <out.json>: bind transforms of the mesh bones (mesh space)
                    DataStorage.LoadSchema();
                    var sf = new AnvilToolkit.FileTypes.AnvilNext.ScimitarFile(args[1], G);
                    if (sf.Data is not AnvilToolkit.FileTypes.AnvilNext.Models.Mesh m) { Console.WriteLine("not a mesh"); return 1; }
                    var rows = new List<string>();
                    foreach (var b in m.Bones.OfType<AnvilToolkit.FileTypes.AnvilNext.Models.MeshBone>())
                    {
                        var x = b.Matrix;
                        rows.Add(System.FormattableString.Invariant(
                            $"\"{b.Name}\": [{x.M11}, {x.M12}, {x.M13}, {x.M14}, {x.M21}, {x.M22}, {x.M23}, {x.M24}, {x.M31}, {x.M32}, {x.M33}, {x.M34}, {x.M41}, {x.M42}, {x.M43}, {x.M44}]"));
                    }
                    File.WriteAllText(args[2], "{\n" + string.Join(",\n", rows) + "\n}\n");
                    Console.WriteLine($"{rows.Count} bones -> {args[2]}");
                    return 0;
                }
                case "mesh-bones":
                {
                    // mesh-bones <mesh>: print the bone name IDs (skinning palette order)
                    DataStorage.LoadSchema();
                    var sf = new AnvilToolkit.FileTypes.AnvilNext.ScimitarFile(args[1], G);
                    if (sf.Data is not AnvilToolkit.FileTypes.AnvilNext.Models.Mesh m) { Console.WriteLine("not a mesh"); return 1; }
                    foreach (var b in m.Bones)
                        Console.WriteLine(b is AnvilToolkit.FileTypes.AnvilNext.Models.MeshBone mb
                            ? $"{mb.Name}\t{mb.NameString}\t{mb.Matrix.M41:F4},{mb.Matrix.M42:F4},{mb.Matrix.M43:F4}\t" +
                              string.Join(",", new[] { mb.Matrix.M11, mb.Matrix.M12, mb.Matrix.M13, mb.Matrix.M21, mb.Matrix.M22, mb.Matrix.M23, mb.Matrix.M31, mb.Matrix.M32, mb.Matrix.M33 }.Select(f => f.ToString("F4")))
                            : b is AnvilToolkit.FileTypes.AnvilNext.Models.Bone bb ? bb.Name.ToString() : b.GetType().Name);
                    return 0;
                }
                case "reserialize":
                {
                    // reserialize <in> <out>: parse and write back (identity test)
                    DataStorage.LoadSchema();
                    var sf = new AnvilToolkit.FileTypes.AnvilNext.ScimitarFile(args[1], G);
                    if (sf.Data == null || sf.Data.Failed) { Console.WriteLine("read failed"); return 1; }
                    return sf.Serialize(args[2], G) ? 0 : 1;
                }
                case "import-glb":
                    DataStorage.LoadSchema();
                    return ImportGlb(args);
                case "pack-data":
                {
                    // pack-data <extracted_dir> <orig.data|-> <out.data>
                    AnvilToolkit.FileTypes.AnvilNext.Containers.Data.MetaData old = null;
                    if (args[2] != "-" && File.Exists(args[2]))
                        using (var br = new BinaryReader(new MemoryStream(File.ReadAllBytes(args[2]))))
                            old = DataFile.GetMetaData(br, G);
                    var df = new DataFile(G);
                    SetBool(df, "Batch", true);
                    using var fs = new FileStream(args[3], FileMode.Create, FileAccess.ReadWrite);
                    var (err, msg) = df.Serialize(fs, args[1], old, false);
                    Console.WriteLine(msg);
                    return err ? 1 : 0;
                }
                case "make-patch-meta":
                {
                    // make-patch-meta <head_meta_dir> <ParentForgeName> <out_dir>
                    string src = args[1], parent = args[2], outDir = args[3];
                    Directory.CreateDirectory(outDir);
                    string F(string ext) => Directory.GetFiles(src, "*." + ext).Single();
                    var pfi = new PrefetchingFileInfos();
                    pfi.Deserialize(F("PrefetchInfo"), G);
                    var pio = new PrefetchInfoOverrides();
                    pio.Deserialize(F("PrefetchInfoOverrides"), G);
                    var dfm = new DeletedFilesManifest();
                    dfm.Deserialize(F("DeletedFilesManifest"), G);
                    Console.WriteLine($"head: PrefetchingFileInfos objects={pfi.Objects.Count}; overrides sets=" +
                        string.Join(",", pio.OverrideSets.Select(s => $"{s.ParentForgeName}:{s.Objects.Count}")) +
                        "; deleted sets=" + string.Join(",", dfm.Sets.Select(s => $"{s.ParentForgeName}:{s.DeletedFiles.Count}")));
                    if (pio.OverrideSets.Any(s => s.ParentForgeName == parent) || dfm.Sets.Any(s => s.ParentForgeName == parent))
                        throw new Exception("head already has a set for " + parent);
                    var ns = new PrefetchInfoOverrideSet { ParentForgeName = parent };
                    ns.Objects.AddRange(pfi.Objects);
                    pio.OverrideSets.Insert(0, ns);
                    dfm.Sets.Insert(0, new DeletedFilesManifestSet { ParentForgeName = parent });
                    if (!pio.Serialize(Path.Combine(outDir, Path.GetFileName(F("PrefetchInfoOverrides"))), G)) return 1;
                    if (!dfm.Serialize(Path.Combine(outDir, Path.GetFileName(F("DeletedFilesManifest"))), G)) return 1;
                    foreach (var ext in new[] { "PrefetchInfo", "MetaFile", "PrefetchingManifest" })
                        File.Copy(F(ext), Path.Combine(outDir, Path.GetFileName(F(ext))), true);
                    // verify by re-reading
                    var chk = new PrefetchInfoOverrides();
                    chk.Deserialize(Path.Combine(outDir, Path.GetFileName(F("PrefetchInfoOverrides"))), G);
                    Console.WriteLine("new overrides sets=" + string.Join(",", chk.OverrideSets.Select(s => $"{s.ParentForgeName}:{s.Objects.Count}")));
                    return chk.OverrideSets[0].Objects.Count == pfi.Objects.Count ? 0 : 1;
                }
                case "prefetch-show":
                {
                    // prefetch-show <meta_dir> <idHex...>: prefetch objects for data file IDs in PrefetchInfo + every override set
                    DataStorage.ActiveGame = G;
                    string F(string ext) => Directory.GetFiles(args[1], "*." + ext).Single();
                    var ids = args.Skip(2).Select(h => Convert.ToUInt64(h, 16)).ToHashSet();
                    var pfi = new PrefetchingFileInfos();
                    pfi.Deserialize(F("PrefetchInfo"), G);
                    var pio = new PrefetchInfoOverrides();
                    pio.Deserialize(F("PrefetchInfoOverrides"), G);
                    void Show(string where, IEnumerable<PrefetchFileInfoObject> objs)
                    {
                        foreach (var o in objs.Where(o => ids.Contains(o.ID)))
                            Console.WriteLine($"{where}\t{o.ID:X16}\tfilters={o.FilterTables.Count}\tdeps={string.Join(",", o.PrefetchFileInfos.Select(p => p.ID.ToString("X16") + (p.DataLayerFilterIndices.Count > 0 ? "[" + string.Join("/", p.DataLayerFilterIndices) + "]" : "")))}");
                    }
                    Console.WriteLine($"PrefetchInfo objects={pfi.Objects.Count}; override sets=" + string.Join(",", pio.OverrideSets.Select(s => $"{s.ParentForgeName}:{s.Objects.Count}")));
                    Show("PrefetchInfo", pfi.Objects);
                    foreach (var s in pio.OverrideSets) Show("override:" + s.ParentForgeName, s.Objects);
                    return 0;
                }
                case "prefetch-dump":
                {
                    // prefetch-dump <file.prefetch|PrefetchInfo> <out.tsv>: every object -> its prefetch deps (Odyssey .prefetch files)
                    var pfi = new PrefetchingFileInfos();
                    pfi.Deserialize(args[1], G);
                    using var w = new StreamWriter(args[2]);
                    foreach (var o in pfi.Objects)
                        w.WriteLine($"{o.ID:X16}\t{o.FilterTables.Count}\t" + string.Join(",", o.PrefetchFileInfos.Select(p => p.ID.ToString("X16") +
                            (p.DataLayerFilterIndices.Count > 0 ? "[" + string.Join("/", p.DataLayerFilterIndices) + "]" : ""))));
                    Console.WriteLine($"{pfi.Objects.Count} objects -> {args[2]}");
                    return 0;
                }
                case "prefetch-add":
                {
                    // prefetch-add <in.prefetch> <out.prefetch> <edits.tsv: dataIdHex \t depHex,depHex...>
                    // appends deps to existing objects of an Odyssey .prefetch file (object inserted in ID order if missing)
                    var pfi = new PrefetchingFileInfos();
                    pfi.Deserialize(args[1], G);
                    foreach (var line in File.ReadLines(args[3]).Where(l => l.Trim().Length > 0 && !l.StartsWith("#")))
                    {
                        var p = line.Split('\t');
                        ulong id = Convert.ToUInt64(p[0], 16);
                        var o = pfi.Objects.FirstOrDefault(x => x.ID == id);
                        if (o == null)
                        {
                            o = new PrefetchFileInfoObject { ID = id };
                            int at = pfi.Objects.FindIndex(x => x.ID > id);
                            pfi.Objects.Insert(at < 0 ? pfi.Objects.Count : at, o);
                        }
                        foreach (var d in p[1].Split(',').Select(h => Convert.ToUInt64(h, 16)))
                            if (!o.PrefetchFileInfos.Any(x => x.ID == d)) o.PrefetchFileInfos.Add(new PrefetchInfo { ID = d });
                        Console.WriteLine($"{id:X16}\t{string.Join(",", o.PrefetchFileInfos.Select(x => x.ID.ToString("X16")))}");
                    }
                    return pfi.Serialize(args[2], G) ? 0 : 1;
                }
                case "prefetch-find":
                {
                    // prefetch-find <meta_dir> <depHex>: prefetch objects (own + override sets) that list depHex
                    DataStorage.ActiveGame = G;
                    string F(string ext) => Directory.GetFiles(args[1], "*." + ext).Single();
                    ulong dep = Convert.ToUInt64(args[2], 16);
                    var pfi = new PrefetchingFileInfos(); pfi.Deserialize(F("PrefetchInfo"), G);
                    var pio = new PrefetchInfoOverrides(); pio.Deserialize(F("PrefetchInfoOverrides"), G);
                    foreach (var o in pfi.Objects.Where(o => o.PrefetchFileInfos.Any(p => p.ID == dep)))
                        Console.WriteLine($"PrefetchInfo\t{o.ID:X16}\t{o.PrefetchFileInfos.Count} deps");
                    foreach (var s in pio.OverrideSets)
                        foreach (var o in s.Objects.Where(o => o.PrefetchFileInfos.Any(p => p.ID == dep)))
                            Console.WriteLine($"override:{s.ParentForgeName}\t{o.ID:X16}\t{o.PrefetchFileInfos.Count} deps");
                    return 0;
                }
                case "prefetch-edit":
                {
                    // prefetch-edit <meta_dir> <out_dir> <edits.tsv: dataIdHex \t add|set \t depHex,depHex...>
                    // Applies each edit to every override set holding that data file ID and to the forge's own
                    // PrefetchInfo (object inserted in ID order if missing, seeded with the effective override deps).
                    DataStorage.ActiveGame = G;
                    string src = args[1], outDir = args[2];
                    Directory.CreateDirectory(outDir);
                    string F(string ext) => Directory.GetFiles(src, "*." + ext).Single();
                    var pfi = new PrefetchingFileInfos();
                    pfi.Deserialize(F("PrefetchInfo"), G);
                    var pio = new PrefetchInfoOverrides();
                    pio.Deserialize(F("PrefetchInfoOverrides"), G);
                    bool Sorted(List<PrefetchFileInfoObject> l) => l.Zip(l.Skip(1)).All(p => p.First.ID < p.Second.ID);
                    Console.WriteLine($"sorted: own={Sorted(pfi.Objects)} " + string.Join(" ", pio.OverrideSets.Select(s => $"{s.ParentForgeName}={Sorted(s.Objects)}")));
                    void Apply(PrefetchFileInfoObject o, string mode, List<ulong> deps)
                    {
                        if (mode == "set") o.PrefetchFileInfos.Clear();
                        foreach (var d in deps)
                            if (!o.PrefetchFileInfos.Any(p => p.ID == d)) o.PrefetchFileInfos.Add(new PrefetchInfo { ID = d });
                    }
                    foreach (var line in File.ReadLines(args[3]).Where(l => l.Trim().Length > 0 && !l.StartsWith("#")))
                    {
                        var p = line.Split('\t');
                        ulong id = Convert.ToUInt64(p[0], 16);
                        var deps = p[2].Split(',').Select(h => Convert.ToUInt64(h, 16)).ToList();
                        PrefetchFileInfoObject seed = null;
                        foreach (var s in pio.OverrideSets)
                            foreach (var o in s.Objects.Where(o => o.ID == id))
                            {
                                Apply(o, p[1], deps); seed ??= o;
                                Console.WriteLine($"override:{s.ParentForgeName}\t{id:X16}\t{o.PrefetchFileInfos.Count} deps");
                            }
                        var own = pfi.Objects.FirstOrDefault(o => o.ID == id);
                        if (own == null)
                        {
                            own = new PrefetchFileInfoObject { ID = id };
                            if (seed != null) own.PrefetchFileInfos.AddRange(seed.PrefetchFileInfos.Select(x => new PrefetchInfo { ID = x.ID }));
                            int at = pfi.Objects.FindIndex(o => o.ID > id);
                            pfi.Objects.Insert(at < 0 ? pfi.Objects.Count : at, own);
                        }
                        Apply(own, p[1], deps);
                        Console.WriteLine($"own\t{id:X16}\t{string.Join(",", own.PrefetchFileInfos.Select(x => x.ID.ToString("X16")))}");
                    }
                    if (!pfi.Serialize(Path.Combine(outDir, Path.GetFileName(F("PrefetchInfo"))), G)) return 1;
                    if (!pio.Serialize(Path.Combine(outDir, Path.GetFileName(F("PrefetchInfoOverrides"))), G)) return 1;
                    foreach (var ext in new[] { "DeletedFilesManifest", "MetaFile", "PrefetchingManifest" })
                        File.Copy(F(ext), Path.Combine(outDir, Path.GetFileName(F(ext))), true);
                    foreach (var b in Directory.GetFiles(outDir, "*.bak")) File.Delete(b);
                    return 0;
                }
                case "reflex-xml":
                {
                    // reflex-xml <blob.bin> <out.xml>: parse a ReflexSkeletonConstraints BinaryData blob with the toolkit's
                    // Reflex3 (Mirage v2) reader and dump it as XML; prints a per-type summary
                    DataStorage.ActiveGame = G;
                    var blob = File.ReadAllBytes(args[1]);
                    var sets = new List<AnvilToolkit.FileTypes.AnvilNext.Models.Reflex3Constraints.Reflex3SkeletonConstraint>();
                    using (var br = new AnvilToolkit.BiendianBinaryReader(new MemoryStream(blob)))
                        while (br.BaseStream.Position < br.BaseStream.Length)
                        {
                            long at = br.BaseStream.Position;
                            try { sets.Add(new AnvilToolkit.FileTypes.AnvilNext.Models.Reflex3Constraints.Reflex3SkeletonConstraint(br)); }
                            catch (Exception e) { Console.WriteLine($"FAILED at set {sets.Count} offset {at}: {e.Message}"); return 1; }
                        }
                    var root = new System.Xml.Linq.XElement("ReflexSets", sets.Select(s => s.ToXml()));
                    root.Save(args[2]);
                    foreach (var (s, i) in sets.Select((s, i) => (s, i)))
                        Console.WriteLine($"set {i}: ReflexVersion={s.ReflexVersion} state={s.StateBuffer.Length} constraints=" +
                            string.Join(",", s.Constraints.GroupBy(c => c.GetType().Name).Select(g => $"{g.Key}x{g.Count()}")));
                    // round-trip check (StateBuffer is dropped by Write, as the toolkit does on export)
                    using var ms = new MemoryStream();
                    using (var bw = new AnvilToolkit.BiendianBinaryWriter(ms))
                        foreach (var (s, i) in sets.Select((s, i) => (s, i))) { s.Index = i; s.Write(bw); }
                    Console.WriteLine($"blob {blob.Length} bytes -> rewritten {ms.ToArray().Length} bytes (state buffers dropped)");
                    return 0;
                }
                case "reflex-compile":
                {
                    // reflex-compile <in.xml> <out.bin>: inverse of reflex-xml (state buffers empty; engine rebuilds them)
                    DataStorage.ActiveGame = G;
                    var sets = new List<AnvilToolkit.FileTypes.AnvilNext.Models.Reflex3Constraints.Reflex3SkeletonConstraint>();
                    using (var xr = System.Xml.XmlReader.Create(args[1]))
                        while (xr.Read())
                            if (xr.NodeType == System.Xml.XmlNodeType.Element && xr.Name == "Reflex3SkeletonConstraint")
                                sets.Add(new AnvilToolkit.FileTypes.AnvilNext.Models.Reflex3Constraints.Reflex3SkeletonConstraint(xr));
                    using var fs = File.Create(args[2]);
                    using var bw = new AnvilToolkit.BiendianBinaryWriter(fs);
                    foreach (var (s, i) in sets.Select((s, i) => (s, i))) { s.Index = i; s.Write(bw); }
                    Console.WriteLine($"compiled {sets.Count} sets, {sets.Sum(s => s.Constraints.Count)} constraints -> {args[2]}");
                    return 0;
                }
                case "pack-forge":
                {
                    // pack-forge <folder> <out.forge>
                    var ff = new ForgeFile { ShowMessages = true };
                    ff.Serialize(args[1], args[2], G).Wait();
                    return File.Exists(args[2]) ? 0 : 1;
                }
                case "tex-info":
                case "tex-export":
                {
                    // tex-info <TextureMap...> | tex-export <TextureMap> <out.dds>
                    DataStorage.LoadSchema();
                    var files = args[0] == "tex-export" ? new[] { args[1] } : args.Skip(1).ToArray();
                    foreach (var f in files)
                    {
                        var sf = new AnvilToolkit.FileTypes.AnvilNext.ScimitarFile(f, G);
                        if (sf.Data is not AnvilToolkit.FileTypes.AnvilNext.Materials.Texture.TextureMap t || t.Failed) { Console.WriteLine($"{f}: not a texture / failed"); continue; }
                        Console.WriteLine($"{Path.GetFileName(f)}: id={t.ID:X16} {t.Width}x{t.Height} mips={t.MipMapCount} fmt={t.PixelFormat} gamma={t.GammaSettings} type={t.MapType} tex={t.TextureFormat} topmips={t.CompiledMips?.Length}");
                        if (args[0] == "tex-export") File.WriteAllBytes(args[2], t.ToDDS());
                    }
                    return 0;
                }
                case "tex-import":
                {
                    // tex-import <orig.TextureMap> <in.dds> <out.TextureMap> [--id HEX] [--maptype NAME]: TextureViewer.ReplaceImage + Save
                    // (Odyssey: orig must have inline mips only, top-mip loading opens a file dialog; the output keeps orig's
                    // CompiledMips, i.e. none -> every mip inline. --id/--maptype create a new texture from a template.)
                    DataStorage.LoadSchema();
                    var sf = new AnvilToolkit.FileTypes.AnvilNext.ScimitarFile(args[1], G);
                    var orig = (AnvilToolkit.FileTypes.AnvilNext.Materials.Texture.TextureMap)sf.Data;
                    var nf = AnvilToolkit.FileTypes.AnvilNext.Materials.Texture.TextureMap.FromDDS(File.ReadAllBytes(args[2]));
                    var nt = (AnvilToolkit.FileTypes.AnvilNext.Materials.Texture.TextureMap)nf.Data;
                    nt.MapType = orig.MapType;
                    nt.CompiledMips = orig.CompiledMips;
                    nt.ID = orig.ID;
                    for (int i = 4; i < args.Length; i++)
                    {
                        if (args[i] == "--id") nt.ID = Convert.ToUInt64(args[++i], 16);
                        else if (args[i] == "--maptype") nt.MapType = Enum.Parse(nt.MapType.GetType(), args[++i]) is var mt ? (dynamic)mt : nt.MapType;
                    }
                    sf.Data = nt;
                    bool ok = sf.Serialize(args[3], G);
                    var chk = (AnvilToolkit.FileTypes.AnvilNext.Materials.Texture.TextureMap)new AnvilToolkit.FileTypes.AnvilNext.ScimitarFile(args[3], G).Data;
                    Console.WriteLine($"wrote {args[3]} ok={ok} readback: {chk.Width}x{chk.Height} mips={chk.MipMapCount} fmt={chk.PixelFormat} gamma={chk.GammaSettings} failed={chk.Failed}");
                    return ok && !chk.Failed ? 0 : 1;
                }
                case "compile-xml":
                    DataStorage.LoadSchema();
                    return DataStorage.ActiveSchema.CompileXML(args[1], args[2]) ? 0 : 1;
                default:
                    Usage();
                    return 2;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.ToString());
            return 1;
        }
    }

    // TextureMap reading resolves top-mip RawAssets relative to the GUI Game Explorer's CurrentPath.
    static void SetExplorerPath(string dir)
    {
        var ge = (AnvilToolkit.Windows.GameExplorer)System.Runtime.CompilerServices.RuntimeHelpers.GetUninitializedObject(typeof(AnvilToolkit.Windows.GameExplorer));
        ge.CurrentPath = dir;
        DataStorage.Windows[typeof(AnvilToolkit.Windows.GameExplorer)] = ge;
    }

    static void Preload()
    {
        // AnvilToolkit loads its name tables on background tasks; wait until they settle.
        GameFileList.CheckStrings();
        HashedData.CheckStrings();
        int last = -1;
        for (int i = 0; i < 600; i++)
        {
            System.Threading.Thread.Sleep(250);
            int n = (GameFileList.List?.Count ?? 0) + (HashedData.HashedStrings?.Count ?? 0);
            if (n == last && n > 0) break;
            last = n;
        }
    }

    // import-glb <in.glb> <mesh-selector> <out.Mesh> <id-hex> [--joints 4|8|16] [--no-autoscale]
    // mesh-selector: glTF mesh name, numeric index, or the decimal ID used as mesh name.
    // Replicates MeshViewer.ReplaceMesh + MeshImportOptions defaults for Shadows.
    static int ImportGlb(string[] args)
    {
        string glb = args[1], sel = args[2], outPath = args[3];
        ulong id = Convert.ToUInt64(args[4], 16);
        int forceJoints = 0; bool autoScale = true; (double x, double y, double z) offset = (0, 0, 0);
        for (int i = 5; i < args.Length; i++)
        {
            if (args[i] == "--joints") forceJoints = int.Parse(args[++i]);
            else if (args[i] == "--no-autoscale") autoScale = false;
            else if (args[i] == "--offset") { var o = args[++i].Split(',').Select(double.Parse).ToArray(); offset = (o[0], o[1], o[2]); }
        }
        var res = AnvilToolkit.FileTypes.AnvilNext.Models.AnvilGLTF.FromGLTF(glb);
        if (res.Meshes.Count == 0) { Console.WriteLine("GLB contains no meshes"); return 1; }
        AnvilToolkit.FileTypes.AnvilNext.Models.Mesh mesh = null;
        if (int.TryParse(sel, out int idx) && idx < res.Meshes.Count && sel.Length < 6) mesh = res.Meshes[idx];
        mesh ??= res.Meshes.FirstOrDefault(m => m.Name == sel || m.ID.ToString() == sel);
        if (mesh == null)
        {
            Console.WriteLine("mesh not found; available: " + string.Join(", ", res.Meshes.Select(m => $"{m.Name}/{m.ID}")));
            return 1;
        }
        if (offset != (0, 0, 0))
        {
            foreach (var v in mesh.Vertices) { v.Position.x += offset.x; v.Position.y += offset.y; v.Position.z += offset.z; }
            mesh.BoundingBox.Min.x += offset.x; mesh.BoundingBox.Min.y += offset.y; mesh.BoundingBox.Min.z += offset.z;
            mesh.BoundingBox.Max.x += offset.x; mesh.BoundingBox.Max.y += offset.y; mesh.BoundingBox.Max.z += offset.z;
        }
        var v0 = mesh.Vertices[0];
        var fmt = v0.FormatData;
        int joints = v0.JointCount;
        fmt.Color = 0;
        if (v0.Color0 != null) fmt.Color++;
        if (v0.Color1 != null) fmt.Color++;
        fmt.Binormals = v0.Binormals != null && joints > 0 && fmt.Binormals;
        fmt.Tangents = v0.Tangents != null && fmt.Tangents;
        fmt.Skinning = forceJoints > 0 ? forceJoints : joints;
        fmt.UV = v0.TEXCOORD_0 != null ? 1 : 0;
        if (G == Game.Unity || G == Game.Syndicate)
        {
            // MeshImportOptions for Unity/Syndicate: version 2, no wide indices. Skinned v2 formats are
            // Pos3s_Col1s_Norm3ub_Col1ub_Tan4ub_Binorm4ub_Tex2s_Joint{4,8}: two colors (Col1s in Pos.w, Col1ub in Norm.w),
            // tangent + binormal, one UV.
            if (mesh.Bones.Count > 255) { Console.WriteLine($"{mesh.Bones.Count} mesh bones > 255 (no wide indices in v2)"); return 1; }
            int filled = 0;
            foreach (var v in mesh.Vertices)
            {
                if (v.Color0 == null) { v.Color0 = new AnvilToolkit.Common.PackedRGBA(1.0, 1.0, 1.0, 1.0); filled++; }
                if (v.Color1 == null) v.Color1 = new AnvilToolkit.Common.PackedRGBA(1.0, 1.0, 1.0, 1.0);
                if (v.Binormals == null && v.Tangents != null)
                {
                    var n = v.Normals; var t = v.Tangents;
                    v.Binormals = new AnvilToolkit.Common.PackedU8Vector4(n.y * t.z - n.z * t.y, n.z * t.x - n.x * t.z, n.x * t.y - n.y * t.x, 0);
                }
            }
            if (filled > 0) Console.WriteLine($"white Color0/Color1 on {filled} vertices");
            fmt.Color = 2; fmt.Tangents = true; fmt.Binormals = true;
            fmt.Version = 2;
            fmt.WideIndices = false;
        }
        else if (G == Game.Odyssey || G == Game.Origins)
        {
            // MeshImportOptions for Origins/Odyssey: version 4, no wide indices. The only skinned v4 formats are
            // Pos3s_Norm4ub_Col4ub_Tex2s_Joint{4,8}_8bit: normal+tangent+binormal sign packed, one color, one UV.
            if (mesh.Bones.Count > 255) { Console.WriteLine($"{mesh.Bones.Count} mesh bones > 255 (no wide indices in v4)"); return 1; }
            int filled = 0;
            foreach (var v in mesh.Vertices)
            {
                if (v.Color0 == null) { v.Color0 = new AnvilToolkit.Common.PackedRGBA(1.0, 1.0, 1.0, 1.0); filled++; }
                if (v.Binormals == null && v.Tangents != null)
                {
                    var n = v.Normals; var t = v.Tangents;
                    v.Binormals = new AnvilToolkit.Common.PackedU8Vector4(n.y * t.z - n.z * t.y, n.z * t.x - n.x * t.z, n.x * t.y - n.y * t.x, 0);
                }
            }
            if (filled > 0) Console.WriteLine($"white Color0 on {filled} vertices");
            fmt.Color = 1; fmt.Tangents = true; fmt.Binormals = true;
            fmt.Version = 4;
            fmt.WideIndices = false;
        }
        else
        {
            if (fmt.Color > fmt.UV) fmt.Color = Math.Max(1, fmt.UV); // Shadows skinned formats pair colors with UV sets
            fmt.Version = 5;
            fmt.WideIndices = mesh.Bones.Count > 255;
        }
        var vf = AnvilToolkit.FileTypes.AnvilNext.Models.VertexFormats.GetVertexFormat(fmt);
        Console.WriteLine($"mesh {mesh.Name}: verts={mesh.Vertices.Count} faces={mesh.Faces.Count} bones={mesh.Bones.Count} prims={mesh.Primitives.Count} " +
            $"joints={joints}->{fmt.Skinning} color={fmt.Color} uv={fmt.UV} tan={fmt.Tangents} bin={fmt.Binormals} wide={fmt.WideIndices} => {vf}");
        if (vf == AnvilToolkit.Utils.VertexFormat.Null) { Console.WriteLine("no matching vertex format"); return 1; }
        // Mesh.UpdateMeshSettings equivalent (without the WPF options window)
        foreach (var v in new[] { v0 })
        {
            if (!fmt.Tangents) { v.Tangents = null; v.Binormals = null; }
            else if (!fmt.Binormals) v.Binormals = null;
            if (fmt.Color < 3) { v.Color2 = null; v.Color3 = null; v.Color4 = null; }
            if (fmt.Color < 2) v.Color1 = null;
            if (fmt.Color < 1) v.Color0 = null;
            if (fmt.UV < 2) { v.TEXCOORD_1 = null; v.TEXCOORD_2 = null; v.TEXCOORD_3 = null; v.TEXCOORD_4 = null; }
        }
        if (autoScale)
        {
            double num = Math.Ceiling(mesh.BoundingBox.AbsoluteMax);
            mesh.Scale *= (float)num;
            double inv = 1.0 / mesh.Scale;
            mesh.VertexScale = new AnvilToolkit.Utils.Vector3(inv, inv, inv);
        }
        Console.WriteLine($"sanitized TBN on {SanitizeTbn(mesh)} vertices");
        mesh.ID = id;
        var sf = new AnvilToolkit.FileTypes.AnvilNext.ScimitarFile(G) { Data = mesh };
        bool ok = sf.Serialize(outPath, G);
        Console.WriteLine(ok ? $"wrote {outPath} scale={mesh.Scale} vfmt={mesh.VertexFormat} stride={mesh.VertexStride} bbox=({mesh.BoundingBox.Min.x:F3},{mesh.BoundingBox.Min.y:F3},{mesh.BoundingBox.Min.z:F3})-({mesh.BoundingBox.Max.x:F3},{mesh.BoundingBox.Max.y:F3},{mesh.BoundingBox.Max.z:F3})" : "serialize failed");
        return ok ? 0 : 1;
    }

    // Zero/NaN normals or tangents (degenerate UVs) make Vertex.encodeBaseVector produce NaN and abort
    // Mesh.Write half-way. Renormalize and rebuild an orthonormal frame where needed.
    static int SanitizeTbn(AnvilToolkit.FileTypes.AnvilNext.Models.Mesh mesh)
    {
        static (double, double, double) N(double x, double y, double z)
        {
            double l = Math.Sqrt(x * x + y * y + z * z);
            return (l > 1e-8 && !double.IsNaN(l)) ? (x / l, y / l, z / l) : (double.NaN, 0, 0);
        }
        int fixedCount = 0;
        foreach (var v in mesh.Vertices)
        {
            bool changed = false;
            var n = v.Normals;
            var (nx, ny, nz) = N(n.x, n.y, n.z);
            if (double.IsNaN(nx)) { (nx, ny, nz) = (0, 0, 1); changed = true; }
            n.x = nx; n.y = ny; n.z = nz;
            if (v.Tangents != null)
            {
                var t = v.Tangents;
                double d = t.x * nx + t.y * ny + t.z * nz;
                var (tx, ty, tz) = N(t.x - d * nx, t.y - d * ny, t.z - d * nz);
                if (double.IsNaN(tx))
                {
                    // any vector perpendicular to n
                    var (ax, ay, az) = Math.Abs(nx) < 0.9 ? (1.0, 0.0, 0.0) : (0.0, 1.0, 0.0);
                    (tx, ty, tz) = N(ay * nz - az * ny, az * nx - ax * nz, ax * ny - ay * nx);
                    changed = true;
                }
                t.x = tx; t.y = ty; t.z = tz;
                if (v.Binormals != null)
                {
                    var b = v.Binormals;
                    double bx = ny * tz - nz * ty, by = nz * tx - nx * tz, bz = nx * ty - ny * tx;
                    double s = b.x * bx + b.y * by + b.z * bz;
                    if (double.IsNaN(s) || Math.Abs(s) < 1e-6) { s = 1; changed = true; }
                    s = Math.Sign(s);
                    b.x = bx * s; b.y = by * s; b.z = bz * s;
                }
            }
            if (changed) fixedCount++;
        }
        return fixedCount;
    }

    static void Usage()
    {
        Console.Error.WriteLine("AcsHarness unpack-data <file.data> <outdir>");
        Console.Error.WriteLine("AcsHarness export-xml <resource> <out.xml> [<resource> <out.xml> ...]");
        Console.Error.WriteLine("AcsHarness export-xml-dir <dir> <outdir> [glob]");
        Console.Error.WriteLine("AcsHarness compile-xml <in.xml> <out.resource>");
        Console.Error.WriteLine("AcsHarness batch <commands.tsv>   (one tab-separated command per line, one process)");
    }

    static int UnpackData(string dataPath, string outDir)
    {
        var df = new DataFile(G);
        typeof(DataFile).GetProperty("ExtractFolder")!.SetValue(df, Path.GetFullPath(outDir));
        SetBool(df, "Batch", true);
        using var fs = new FileStream(dataPath, FileMode.Open, FileAccess.Read, FileShare.Read);
        var (err, msg) = df.Deserialize(fs);
        Console.WriteLine(msg);
        return err ? 1 : 0;
    }

    static void SetBool(object o, string name, bool v)
    {
        var t = o.GetType();
        var p = t.GetProperty(name);
        if (p != null && p.CanWrite) { p.SetValue(o, v); return; }
        var f = t.GetField(name, System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic)
             ?? t.GetField($"<{name}>k__BackingField", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic);
        f?.SetValue(o, v);
    }

    static void ExportXml(string res, string outXml)
    {
        var obj = DataStorage.ActiveSchema.ReadFile(res);
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outXml))!);
        obj.ToXml().WriteToFile(outXml, 1, UTF8: true);
        Console.WriteLine($"XML {res} -> {outXml}");
    }

    static readonly HashSet<string> SkipExt = new(StringComparer.OrdinalIgnoreCase)
    { ".Mesh", ".TextureMap", ".CompiledMip", ".Animation", ".CompiledTextureMap", ".HairMesh", ".RawAsset", ".CompiledMesh" };

    static int ExportXmlDir(string dir, string outDir, string glob, HashSet<string> skip = null)
    {
        int bad = 0;
        foreach (var f in Directory.GetFiles(dir, glob))
        {
            if (skip != null && skip.Contains(Path.GetExtension(f))) continue;
            try { ExportXml(f, Path.Combine(outDir, Path.GetFileName(f) + ".xml")); }
            catch (Exception ex) { bad++; Console.WriteLine($"FAIL {Path.GetFileName(f)}: {ex.Message}"); }
        }
        return bad == 0 ? 0 : 1;
    }
}
