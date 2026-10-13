// SifuExport: headless CUE4Parse exporter for Sifu (UE 4.26) and loose mod paks.
// Usage: SifuExport <paksDir> <outDir> <command> [args...]
//   env SIFU_AES=0x...   optional AES key; SIFU_USMAP=path optional mappings; SIFU_OODLE=path optional oodle dll
//   SIFU_GAME=GAME_UE4_26 (EGame name)
//   list <regex>                 list package paths matching regex
//   json <pkg>...                JSON dump of all exports of each package
//   export <fmt> <pkg>...        export meshes/textures (fmt: uemodel|gltf|psk)
//   skel <pkg>...                exact ref-skeleton / morph / section dump of a skeletal mesh or skeleton
//   raw <pkg>...                 save raw package bytes (uasset/uexp/ubulk)
using System.Text.RegularExpressions;
using CUE4Parse.Compression;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.FileProvider;
using CUE4Parse.MappingsProvider.Usmap;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Assets.Exports.Animation;
using CUE4Parse.UE4.Assets.Exports.SkeletalMesh;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Versions;
using CUE4Parse_Conversion;
using CUE4Parse_Conversion.Animations;
using CUE4Parse_Conversion.Options;
using Newtonsoft.Json;

if (args.Length < 3)
{
    Console.Error.WriteLine("usage: SifuExport <paksDir> <outDir> <command> [args...]");
    return 2;
}
var (paksDir, outDir, cmd) = (args[0], args[1], args[2]);
var rest = args.Skip(3).ToArray();
Directory.CreateDirectory(outDir);

var oodle = Environment.GetEnvironmentVariable("SIFU_OODLE");
if (!string.IsNullOrEmpty(oodle)) OodleHelper.Initialize(oodle);
var game = Enum.Parse<EGame>(Environment.GetEnvironmentVariable("SIFU_GAME") ?? "GAME_UE4_26");
var provider = new DefaultFileProvider(paksDir, SearchOption.TopDirectoryOnly, true, new VersionContainer(game));
var usmap = Environment.GetEnvironmentVariable("SIFU_USMAP");
if (!string.IsNullOrEmpty(usmap)) provider.MappingsContainer = new FileUsmapTypeMappingsProvider(usmap);
provider.Initialize();
var aes = Environment.GetEnvironmentVariable("SIFU_AES");
if (!string.IsNullOrEmpty(aes)) provider.SubmitKey(new FGuid(), new FAesKey(aes));
var mounted = provider.Mount();
Console.Error.WriteLine($"mounted {mounted} containers, {provider.Files.Count} files");

string NormPkg(string p)
{
    p = p.Replace('\\', '/');
    if (p.StartsWith("/Game/")) p = "Sifu/Content/" + p[6..];
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
                if (obj is USkeletalMesh or USkeleton or CUE4Parse.UE4.Assets.Exports.Texture.UTexture or CUE4Parse.UE4.Assets.Exports.StaticMesh.UStaticMesh)
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
    case "anim":
    {
        // anim <pkg> <frame>...: decoded parent-space bone transforms of an AnimSequence at the given frames
        var pkgPath = NormPkg(rest[0]);
        var seq = provider.LoadPackageObjects(pkgPath).OfType<UAnimSequence>().First();
        var set = seq.Skeleton.Load<USkeleton>().ConvertAnims(seq);
        var cseq = set.Sequences[0];
        var rs = set.Skeleton.ReferenceSkeleton;
        var frames = new List<object>();
        foreach (var f in rest.Skip(1).Select(float.Parse))
        {
            var bones = new List<object>();
            for (var b = 0; b < rs.FinalRefBoneInfo.Length; b++)
            {
                var pos = rs.FinalRefBonePose[b].Translation;
                var rot = rs.FinalRefBonePose[b].Rotation;
                var keyed = b < cseq.Tracks.Count && cseq.Tracks[b] != null && cseq.Tracks[b].HasKeys();
                var scl = rs.FinalRefBonePose[b].Scale3D;
                if (keyed) cseq.Tracks[b].GetBoneTransform(f, cseq.NumFrames, ref rot, ref pos, ref scl);
                bones.Add(new { name = rs.FinalRefBoneInfo[b].Name.Text, keyed, t = new[] { pos.X, pos.Y, pos.Z }, q = new[] { rot.X, rot.Y, rot.Z, rot.W } });
            }
            frames.Add(new { frame = f, bones });
        }
        var dst = Path.Combine(outDir, pkgPath + ".anim.json");
        Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
        File.WriteAllText(dst, JsonConvert.SerializeObject(new { name = seq.Name, numFrames = cseq.NumFrames, fps = cseq.FramesPerSecond, frames }, Formatting.Indented));
        Console.WriteLine($"anim {dst} frames={cseq.NumFrames}");
        break;
    }
    case "file":
        foreach (var a in rest)
        {
            var data = provider.Files[a].Read();
            var dst = Path.Combine(outDir, a);
            Directory.CreateDirectory(Path.GetDirectoryName(dst)!);
            File.WriteAllBytes(dst, data);
            Console.WriteLine($"file {dst} {data.Length}");
        }
        break;
    case "grep":
    {
        var rx = new Regex(rest[0], RegexOptions.IgnoreCase);
        var needles = rest.Skip(1).Select(n => System.Text.Encoding.ASCII.GetBytes(n)).ToArray();
        foreach (var k in provider.Files.Keys.Where(k => k.EndsWith(".uasset") && rx.IsMatch(k)).OrderBy(k => k))
        {
            byte[] data;
            try { data = provider.Files[k].Read(); } catch { continue; }
            foreach (var n in needles)
                if (data.AsSpan().IndexOf(n) >= 0) { Console.WriteLine($"{k}	{System.Text.Encoding.ASCII.GetString(n)}"); }
        }
        break;
    }
    default:
        Console.Error.WriteLine($"unknown command {cmd}");
        return 2;
}
return 0;
