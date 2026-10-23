using Serilog;
using System.Buffers.Binary;
using CUE4Parse;
using CUE4Parse.FileProvider;
using CUE4Parse.UE4.Assets;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Versions;

// usage:
//   HLMeshProbe probe <ue427|hl> <dir> [nameFilter]
//   HLMeshProbe patch <inDir> <outDir>
//     Converts stock-UE4.27 cooked skeletal meshes to the post-2025-01 Hogwarts Legacy layout:
//     inserts a uint32 (=1, bVisibleInRayTracing) after bCastShadow in every FSkelMeshRenderSection,
//     then fixes the export map SerialSize/SerialOffset and BulkDataStartOffset. Other files are copied.
Serilog.Log.Logger = new Serilog.LoggerConfiguration().MinimumLevel.Warning().WriteTo.Console().CreateLogger();
switch (args[0])
{
    case "probe": Probe(args[1] == "hl" ? EGame.GAME_HogwartsLegacy : EGame.GAME_UE4_27, args[2], args.Length > 3 ? args[3] : ""); break;
    case "patch": Patch(args[1], args[2], args.Length > 3 ? args[3] : null); break;
    case "mat": Mat(args[1] == "hl" ? EGame.GAME_HogwartsLegacy : EGame.GAME_UE4_27, args[2], args.Length > 3 ? args[3] : ""); break;
    case "dump": Dump(args[1] == "hl" ? EGame.GAME_HogwartsLegacy : EGame.GAME_UE4_27, args[2], args[3], args.Length > 4 ? args[4] : ""); break;
    case "json": Json(args[1] == "hl" ? EGame.GAME_HogwartsLegacy : EGame.GAME_UE4_27, args[2], args.Length > 3 ? args[3] : ""); break;
    default: Console.WriteLine("unknown mode"); return 2;
}
return 0;

static DefaultFileProvider Open(string dir, EGame game)
{
    var p = new DefaultFileProvider(dir, SearchOption.AllDirectories, new VersionContainer(game));
    p.Initialize();
    return p;
}

static List<string> Describe(DefaultFileProvider provider, string key, bool print)
{
    var lines = new List<string>();
    HLProbe.Sections.Clear(); HLProbe.Infl.Clear();
    try
    {
        var pkg = provider.LoadPackage(provider.Files[key]);
        foreach (var exp in pkg.GetExports())
        {
            if (exp is not USkeletalMesh sk) continue;
            var lods = sk.LODModels ?? [];
            lines.Add($"lods={lods.Length} " + string.Join(" | ", lods.Select(l => $"v={l.NumVertices} s={l.Sections.Length} uv={l.NumTexCoords}")));
            lines.Add("infl=" + string.Join(",", HLProbe.Infl.Select(i => $"{i.Max}/{i.Verts}v/{i.Bones}b")));
            lines.Add($"slots=" + string.Join(",", sk.SkeletalMaterials.Select(m => m.MaterialSlotName.Text)) + $" mats={sk.SkeletalMaterials.Length} bones={sk.ReferenceSkeleton.FinalRefBoneInfo.Length} tail={HLProbe.End.Valid - HLProbe.End.Pos}");
        }
    }
    catch (Exception e)
    {
        lines.Add($"FAIL {e.GetType().Name}: {e.Message.Split('\n')[0]}");
    }
    if (print)
    {
        Console.WriteLine($"{(lines.Any(l => l.StartsWith("FAIL")) ? "FAIL" : "OK  ")} {key}");
        foreach (var l in lines) Console.WriteLine("   " + l);
        foreach (var s in HLProbe.Sections)
            Console.WriteLine($"   sec pos={s.Pos} abs={s.AbsPos} next=0x{s.Next:X8} mat={s.Mat} tris={s.Tris}");
    }
    return lines;
}

static void Probe(EGame game, string dir, string filter)
{
    var provider = Open(dir, game);
    foreach (var key in provider.Files.Keys.OrderBy(k => k))
        if (key.EndsWith(".uasset") && key.Contains(filter, StringComparison.OrdinalIgnoreCase))
            Describe(provider, key, true);
}

static void Patch(string inDir, string outDir, string? refJson)
{
    var refPose = new Dictionary<string, float[]>();
    if (refJson != null)
        foreach (var b in Newtonsoft.Json.Linq.JObject.Parse(File.ReadAllText(refJson))["bones"]!)
            refPose[(string) b["name"]!] = b["r"]!.Select(x => (float) x).Concat(b["t"]!.Select(x => (float) x)).Concat(b["s"]!.Select(x => (float) x)).ToArray();
    inDir = Path.GetFullPath(inDir);
    outDir = Path.GetFullPath(outDir);
    var src = Open(inDir, EGame.GAME_UE4_27);
    var expected = new Dictionary<string, List<string>>();
    foreach (var file in Directory.EnumerateFiles(inDir, "*", SearchOption.AllDirectories))
    {
        var rel = Path.GetRelativePath(inDir, file);
        var dst = Path.Combine(outDir, rel);
        Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
        if (!file.EndsWith(".uasset")) { if (!File.Exists(Path.ChangeExtension(file, ".uasset")) || !file.EndsWith(".uexp")) File.Copy(file, dst, true); continue; }
        var key = src.Files.Keys.First(k => Path.GetFullPath(Path.Combine(inDir, k)).Equals(file, StringComparison.OrdinalIgnoreCase)
                                            || k.EndsWith(rel.Replace('\\', '/'), StringComparison.OrdinalIgnoreCase));
        HLProbe.RefPosePos = -1;
        var desc = Describe(src, key, false);
        var refPosePos = HLProbe.RefPosePos;
        string[] boneNames = [];
        try { var skm = src.LoadPackage(src.Files[key]).GetExports().OfType<USkeletalMesh>().FirstOrDefault(); if (skm != null) boneNames = skm.ReferenceSkeleton.FinalRefBoneInfo.Select(b => b.Name.Text).ToArray(); } catch { }
        var uexpPath = Path.ChangeExtension(file, ".uexp");
        var uexpDst = Path.ChangeExtension(dst, ".uexp");
        var positions = HLProbe.Sections.Select(s => s.Pos).Distinct().ToList();
        if (positions.Count == 0 || desc.Any(l => l.StartsWith("FAIL")))
        {
            if (desc.Any(l => l.StartsWith("FAIL"))) Console.WriteLine($"WARN not a clean UE4.27 mesh, copied as-is: {rel} :: {string.Join(";", desc)}");
            File.Copy(file, dst, true);
            if (File.Exists(uexpPath)) File.Copy(uexpPath, uexpDst, true);
            continue;
        }
        var pkg = (Package) src.LoadPackage(src.Files[key]);
        var sum = pkg.Summary;
        var uasset = File.ReadAllBytes(file);
        var uexp = File.ReadAllBytes(uexpPath);
        if (uasset.Length != sum.TotalHeaderSize) throw new Exception($"{rel}: uasset size {uasset.Length} != TotalHeaderSize {sum.TotalHeaderSize}");

        // exact HL reference pose (in place, same size): FTransform = quat xyzw, translation xyz, scale xyz
        if (refPose.Count > 0 && refPosePos >= 0)
        {
            var n = BinaryPrimitives.ReadInt32LittleEndian(uexp.AsSpan((int) refPosePos));
            if (n != boneNames.Length) throw new Exception($"{rel}: ref pose count {n} != bones {boneNames.Length}");
            var hit = 0;
            for (var i = 0; i < n; i++)
            {
                if (!refPose.TryGetValue(boneNames[i], out var v)) continue;
                var at = (int) refPosePos + 4 + i * 40;
                for (var k = 0; k < 10; k++) BinaryPrimitives.WriteSingleLittleEndian(uexp.AsSpan(at + k * 4), v[k]);
                hit++;
            }
            Console.WriteLine($"refpose {rel}: {hit}/{n} bones set from reference");
        }
        // uexp: insert 01 00 00 00 at each section position (descending so earlier offsets stay valid)
        var ms = new MemoryStream();
        var cuts = positions.OrderBy(p => p).ToList();
        long last = 0;
        foreach (var p in cuts)
        {
            ms.Write(uexp, (int) last, (int) (p - last));
            ms.Write([1, 0, 0, 0]);
            last = p;
        }
        ms.Write(uexp, (int) last, uexp.Length - (int) last);
        var newUexp = ms.ToArray();

        // export map
        var absCuts = cuts.Select(p => p + sum.TotalHeaderSize).ToList();
        for (var i = 0; i < pkg.ExportMap.Length; i++)
        {
            var e = pkg.ExportMap[i];
            var at = sum.ExportOffset + i * 104;
            var size = BinaryPrimitives.ReadInt64LittleEndian(uasset.AsSpan(at + 28));
            var off = BinaryPrimitives.ReadInt64LittleEndian(uasset.AsSpan(at + 36));
            if (size != e.SerialSize || off != e.SerialOffset) throw new Exception($"{rel}: export {i} layout mismatch");
            var inside = absCuts.Count(c => c >= off && c < off + size);
            var before = absCuts.Count(c => c < off);
            BinaryPrimitives.WriteInt64LittleEndian(uasset.AsSpan(at + 28), size + 4 * inside);
            BinaryPrimitives.WriteInt64LittleEndian(uasset.AsSpan(at + 36), off + 4 * before);
        }

        // BulkDataStartOffset (int64 in the summary)
        long bdso = sum.BulkDataStartOffset;
        var hits = new List<int>();
        for (var o = 0; o + 8 <= sum.NameOffset; o++)
            if (BinaryPrimitives.ReadInt64LittleEndian(uasset.AsSpan(o)) == bdso) hits.Add(o);
        if (hits.Count != 1) throw new Exception($"{rel}: BulkDataStartOffset {bdso} found {hits.Count} times");
        BinaryPrimitives.WriteInt64LittleEndian(uasset.AsSpan(hits[0]), bdso + 4 * absCuts.Count(c => c < bdso));

        File.WriteAllBytes(dst, uasset);
        File.WriteAllBytes(uexpDst, newUexp);
        expected[rel.Replace('\\', '/')] = desc;
        Console.WriteLine($"patched {rel}: {cuts.Count} sections, uexp {uexp.Length} -> {newUexp.Length}");
    }

    // verify with HL rules
    var chk = Open(outDir, EGame.GAME_HogwartsLegacy);
    var bad = 0;
    foreach (var (rel, want) in expected)
    {
        var key = chk.Files.Keys.First(k => k.EndsWith(rel, StringComparison.OrdinalIgnoreCase));
        var got = Describe(chk, key, false);
        var ok = got.SequenceEqual(want) && HLProbe.Sections.All(s => s.Next == 1);
        if (!ok) { bad++; Console.WriteLine($"VERIFY FAIL {rel}\n   want {string.Join(" / ", want)}\n   got  {string.Join(" / ", got)}"); }
    }
    Console.WriteLine(bad == 0 ? $"verify ok ({expected.Count} meshes)" : $"verify FAILED {bad}");
    if (bad != 0) Environment.Exit(1);
}

static void Json(EGame game, string dir, string filter)
{
    var provider = Open(dir, game);
    foreach (var key in provider.Files.Keys.OrderBy(k => k))
    {
        if (!key.EndsWith(".uasset") || !key.Contains(filter, StringComparison.OrdinalIgnoreCase)) continue;
        Console.WriteLine($"##### {key}");
        try { Console.WriteLine(Newtonsoft.Json.JsonConvert.SerializeObject(provider.LoadPackage(provider.Files[key]).GetExports(), Newtonsoft.Json.Formatting.Indented)); }
        catch (Exception e) { Console.WriteLine($"FAIL {e.GetType().Name}: {e.Message}"); }
    }
}

static void Mat(EGame game, string dir, string filter)
{
    var provider = Open(dir, game);
    foreach (var key in provider.Files.Keys.OrderBy(k => k))
    {
        if (!key.EndsWith(".uasset") || !key.Contains(filter, StringComparison.OrdinalIgnoreCase)) continue;
        HLProbe.MatHashPos = -1; HLProbe.End = (0, 0);
        try
        {
            var pkg = provider.LoadPackage(provider.Files[key]);
            foreach (var exp in pkg.GetExports())
            {
                if (exp is not CUE4Parse.UE4.Assets.Exports.Material.UMaterialInterface mi) continue;
                var uexp = File.ReadAllBytes(Directory.GetFiles(dir, Path.GetFileNameWithoutExtension(key) + ".uexp", SearchOption.AllDirectories)[0]);
                var hash = HLProbe.MatHashPos >= 0 && HLProbe.MatHashPos + 20 <= uexp.Length ? Convert.ToHexString(uexp, (int) HLProbe.MatHashPos, 20) : "?";
                Console.WriteLine($"{key} {exp.ExportType} hashpos={HLProbe.MatHashPos} uexp={uexp.Length} hash={hash}");
            }
        }
        catch (Exception e) { Console.WriteLine($"FAIL {key}: {e.Message.Split((char)10)[0]}"); }
    }
}

// dump <hl|ue427> <dir> <outDir> [filter] : LOD0 geometry + skin + ref skeleton of skeletal meshes, bones of skeletons -> JSON
static void Dump(EGame game, string dir, string outDir, string filter)
{
    var provider = Open(dir, game);
    Directory.CreateDirectory(outDir);
    var inv = System.Globalization.CultureInfo.InvariantCulture;
    foreach (var key in provider.Files.Keys.OrderBy(k => k))
    {
        if (!key.EndsWith(".uasset") || !key.Contains(filter, StringComparison.OrdinalIgnoreCase)) continue;
        try
        {
            foreach (var exp in provider.LoadPackage(provider.Files[key]).GetExports())
            {
                CUE4Parse.UE4.Assets.Exports.Animation.FReferenceSkeleton? rs = null;
                var o = new Dictionary<string, object?>();
                o["name"] = exp.Name; o["type"] = exp.ExportType;
                if (exp is USkeletalMesh sk)
                {
                    rs = sk.ReferenceSkeleton;
                    o["materials"] = sk.SkeletalMaterials.Select(m => new { slot = m.MaterialSlotName.Text, mat = m.MaterialInterface?.ToString() }).ToList();
                    var lod = sk.LODModels![0];
                    var v = lod.VertexBufferGPUSkin.VertsFloat;
                    o["pos"] = v.SelectMany(x => new[] { x.Pos.X, x.Pos.Y, x.Pos.Z }).ToArray();
                    o["nrm"] = v.SelectMany(x => new[] { x.Normal[2].X, x.Normal[2].Y, x.Normal[2].Z }).ToArray();
                    o["uv"] = v.SelectMany(x => new[] { x.UVs[0].U, x.UVs[0].V }).ToArray();
                    var idx = Enumerable.Range(0, lod.Indices!.Length).Select(i => lod.Indices[i]).ToArray();
                    var secs = new List<object>();
                    var vb = new int[v.Length * 4]; var vw = new float[v.Length * 4];
                    foreach (var s in lod.Sections)
                    {
                        secs.Add(new { mat = s.MaterialIndex, first = s.BaseIndex, tris = s.NumTriangles, baseVert = s.BaseVertexIndex, nverts = s.NumVertices });
                        for (var i = (int) s.BaseVertexIndex; i < s.BaseVertexIndex + s.NumVertices; i++)
                            for (var k = 0; k < 4; k++)
                            {
                                vb[i * 4 + k] = s.BoneMap[v[i].Infs.BoneIndex[k]];
                                vw[i * 4 + k] = v[i].Infs.BoneWeight[k] / 255f;
                            }
                    }
                    o["idx"] = idx; o["sections"] = secs; o["bi"] = vb; o["bw"] = vw;
                    o["morphs"] = sk.MorphTargets.Length;
                    // morph target deltas (LOD0) -> <name>_morphs.json: {morph: {i: [render vertex], d: [dx,dy,dz,...]}}
                    var md = new Dictionary<string, object>();
                    foreach (var mi in sk.MorphTargets)
                    {
                        if (!mi.TryLoad(out CUE4Parse.UE4.Assets.Exports.Animation.UMorphTarget? mt) || mt == null || mt.MorphLODModels.Length == 0) continue;
                        var verts = mt.MorphLODModels[0].Vertices;
                        md[mt.Name] = new { i = verts.Select(x => (int) x.SourceIdx).ToArray(), d = verts.SelectMany(x => new[] { x.PositionDelta.X, x.PositionDelta.Y, x.PositionDelta.Z }).ToArray() };
                    }
                    if (md.Count > 0) File.WriteAllText(Path.Combine(outDir, exp.Name + "_morphs.json"), Newtonsoft.Json.JsonConvert.SerializeObject(md));
                }
                else if (exp is CUE4Parse.UE4.Assets.Exports.Animation.USkeleton skel) rs = skel.ReferenceSkeleton;
                else continue;
                o["bones"] = rs!.FinalRefBoneInfo.Select((b, i) => new {
                    name = b.Name.Text, parent = b.ParentIndex,
                    t = new[] { rs.FinalRefBonePose[i].Translation.X, rs.FinalRefBonePose[i].Translation.Y, rs.FinalRefBonePose[i].Translation.Z },
                    r = new[] { rs.FinalRefBonePose[i].Rotation.X, rs.FinalRefBonePose[i].Rotation.Y, rs.FinalRefBonePose[i].Rotation.Z, rs.FinalRefBonePose[i].Rotation.W },
                    s = new[] { rs.FinalRefBonePose[i].Scale3D.X, rs.FinalRefBonePose[i].Scale3D.Y, rs.FinalRefBonePose[i].Scale3D.Z } }).ToList();
                var path = Path.Combine(outDir, exp.Name + ".json");
                File.WriteAllText(path, Newtonsoft.Json.JsonConvert.SerializeObject(o));
                Console.WriteLine($"dumped {exp.Name} ({exp.ExportType})");
            }
        }
        catch (Exception e) { Console.WriteLine($"FAIL {key}: {e.GetType().Name} {e.Message.Split((char)10)[0]}"); }
    }
}
