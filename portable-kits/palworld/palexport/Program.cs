// PalExport: headless CUE4Parse exporter for Palworld (UE 5.1, legacy pak). Derived from SbExport.
// Usage: PalExport <paksDir> <usmap or -> <oodleDll> <outDir> <command> [args...]
//   list <regex>                 list package paths matching regex
//   json <pkg>...                JSON dump of all exports of each package
//   export <fmt> <pkg>...        export meshes/textures (fmt: uemodel|gltf|psk)
//   skel <pkg>...                exact ref-skeleton / morph / section dump of a skeletal mesh or skeleton
//   raw <pkg>...                 save raw package bytes (uasset/uexp/ubulk)
using System.Text.RegularExpressions;
using CUE4Parse.Compression;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider.Usmap;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Animation;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Versions;
using CUE4Parse_Conversion;
using CUE4Parse_Conversion.Options;
using Newtonsoft.Json;

if (args.Length < 5)
{
    Console.Error.WriteLine("usage: PalExport <paksDir> <usmap or -> <oodleDll> <outDir> <command> [args...]");
    return 2;
}
var (paksDir, usmap, oodle, outDir, cmd) = (args[0], args[1], args[2], args[3], args[4]);
var rest = args.Skip(5).ToArray();
Directory.CreateDirectory(outDir);

OodleHelper.Initialize(oodle);
var extra = (Environment.GetEnvironmentVariable("PALX_EXTRA") ?? "").Split(';', StringSplitOptions.RemoveEmptyEntries).Select(d => new DirectoryInfo(d)).ToArray();
var provider = new DefaultFileProvider(new DirectoryInfo(paksDir), extra, SearchOption.TopDirectoryOnly, true, new VersionContainer(EGame.GAME_UE5_1));
if (usmap != "-") provider.MappingsContainer = new FileUsmapTypeMappingsProvider(usmap);
provider.Initialize();
var mounted = provider.Mount();
Console.Error.WriteLine($"mounted {mounted} containers, {provider.Files.Count} files");

string NormPkg(string p)
{
    p = p.Replace('\\', '/');
    if (p.StartsWith("/Game/")) p = "Pal/Content/" + p[6..];
    var dot = p.LastIndexOf('.');
    if (dot > p.LastIndexOf('/')) p = p[..dot];
    return p;
}

switch (cmd)
{
    case "list":
    {
        var rx = new Regex(rest.Length > 0 ? rest[0] : ".", RegexOptions.IgnoreCase);
        foreach (var k in provider.Files.Keys.Where(k => rx.IsMatch(k)).OrderBy(k => k)) Console.WriteLine(k);
        break;
    }
    case "json":
        foreach (var a in rest)
        {
            var pkgPath = NormPkg(a);
            var pkg = provider.LoadPackage(pkgPath + ".uasset");
            var json = JsonConvert.SerializeObject(pkg.GetExports(), Formatting.Indented);
            var dst = Path.Combine(outDir, pkgPath + ".json");
            Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
            File.WriteAllText(dst, json);
            Console.WriteLine($"json {dst}");
        }
        break;
    case "raw":
        foreach (var a in rest)
        {
            var pkgPath = NormPkg(a);
            foreach (var kv in provider.SavePackage(pkgPath + ".uasset"))
            {
                var dst = Path.Combine(outDir, kv.Key);
                Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
                File.WriteAllBytes(dst, kv.Value);
                Console.WriteLine($"raw {dst} {kv.Value.Length}");
            }
        }
        break;
    case "export":
    {
        var fmt = rest[0] switch { "gltf" => EMeshFormat.Gltf2, "psk" => EMeshFormat.ActorX, _ => EMeshFormat.UEFormat };
        var opts = new ExportOptions(meshFormat: fmt, exportMaterials: false, exportMorphTargets: true, socketFormat: ESocketFormat.None);
        var session = new ExportSession();
        foreach (var a in rest.Skip(1))
            foreach (var obj in provider.LoadPackageObjects(NormPkg(a)))
                if (obj is USkeletalMesh or USkeleton or UAnimSequence or CUE4Parse.UE4.Assets.Exports.Texture.UTexture or CUE4Parse.UE4.Assets.Exports.StaticMesh.UStaticMesh)
                    session.Add(obj);
        var results = await session.RunAsync(outDir, opts, null, CancellationToken.None);
        foreach (var r in results)
            Console.WriteLine($"{(r.Success ? "ok" : "FAIL")} {r.ObjectPath} {string.Join(";", r.DiskFilePaths ?? Array.Empty<string>())} {r.Error?.Message}");
        break;
    }
    case "skel":
        foreach (var a in rest)
        {
            var pkgPath = NormPkg(a);
            foreach (var obj in provider.LoadPackageObjects(pkgPath))
            {
                object dump = null;
                if (obj is USkeletalMesh sm)
                {
                    var rs = sm.ReferenceSkeleton;
                    dump = new
                    {
                        type = "SkeletalMesh",
                        name = sm.Name,
                        skeleton = sm.Skeleton?.ToString(),
                        bones = rs.FinalRefBoneInfo.Select((b, i) => new
                        {
                            i, name = b.Name.Text, parent = b.ParentIndex,
                            t = new[] { rs.FinalRefBonePose[i].Translation.X, rs.FinalRefBonePose[i].Translation.Y, rs.FinalRefBonePose[i].Translation.Z },
                            q = new[] { rs.FinalRefBonePose[i].Rotation.X, rs.FinalRefBonePose[i].Rotation.Y, rs.FinalRefBonePose[i].Rotation.Z, rs.FinalRefBonePose[i].Rotation.W },
                            s = new[] { rs.FinalRefBonePose[i].Scale3D.X, rs.FinalRefBonePose[i].Scale3D.Y, rs.FinalRefBonePose[i].Scale3D.Z },
                        }).ToArray(),
                        morphs = sm.MorphTargets?.Select(m => m.Name).ToArray(),
                        materials = sm.SkeletalMaterials?.Select(m => new { slot = m.MaterialSlotName.Text, mat = m.MaterialInterface?.ToString() }).ToArray(),
                        lods = sm.LODModels?.Select(l => new
                        {
                            verts = l.NumVertices,
                            sections = l.Sections.Select(s => new { s.MaterialIndex, s.NumTriangles, s.NumVertices, s.BaseVertexIndex, bones = s.BoneMap?.Length }).ToArray(),
                            requiredBones = l.RequiredBones?.Length,
                        }).ToArray(),
                    };
                }
                else if (obj is USkeleton sk)
                {
                    var rs = sk.ReferenceSkeleton;
                    dump = new
                    {
                        type = "Skeleton",
                        name = sk.Name,
                        bones = rs.FinalRefBoneInfo.Select((b, i) => new
                        {
                            i, name = b.Name.Text, parent = b.ParentIndex,
                            retarget = sk.BoneTree != null && i < sk.BoneTree.Length ? sk.BoneTree[i].ToString() : null,
                            t = new[] { rs.FinalRefBonePose[i].Translation.X, rs.FinalRefBonePose[i].Translation.Y, rs.FinalRefBonePose[i].Translation.Z },
                            q = new[] { rs.FinalRefBonePose[i].Rotation.X, rs.FinalRefBonePose[i].Rotation.Y, rs.FinalRefBonePose[i].Rotation.Z, rs.FinalRefBonePose[i].Rotation.W },
                            s = new[] { rs.FinalRefBonePose[i].Scale3D.X, rs.FinalRefBonePose[i].Scale3D.Y, rs.FinalRefBonePose[i].Scale3D.Z },
                        }).ToArray(),
                    };
                }
                if (dump == null) continue;
                var dst = Path.Combine(outDir, pkgPath + "." + obj.Name + ".skel.json");
                Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
                File.WriteAllText(dst, JsonConvert.SerializeObject(dump, Formatting.Indented));
                Console.WriteLine($"skel {dst}");
            }
        }
        break;
    case "mappings":
    {
        var rx = new Regex(rest.Length > 0 ? rest[0] : ".", RegexOptions.IgnoreCase);
        var m = provider.MappingsForGame;
        foreach (var kv in m.Enums.Where(e => rx.IsMatch(e.Key)).OrderBy(e => e.Key))
            Console.WriteLine($"enum {kv.Key}: " + string.Join(", ", kv.Value.Select(v => $"{v.Value}={v.Key}")));
        foreach (var kv in m.Types.Where(t => rx.IsMatch(t.Key)).OrderBy(t => t.Key))
        {
            Console.WriteLine($"struct {kv.Key} : {kv.Value.SuperType}");
            foreach (var pi in kv.Value.Properties.Values.OrderBy(v => v.Index))
                Console.WriteLine($"    [{pi.Index}] {pi.Name} : {pi.MappingType?.Type} {pi.MappingType?.StructType}{pi.MappingType?.EnumName} {pi.MappingType?.InnerType?.Type} {pi.MappingType?.InnerType?.StructType}");
        }
        break;
    }
    default:
        Console.Error.WriteLine($"unknown command {cmd}");
        return 2;
}
return 0;
