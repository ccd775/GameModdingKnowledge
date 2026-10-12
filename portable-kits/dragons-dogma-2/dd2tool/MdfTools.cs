using System.Text.Json;
using System.Text.Json.Nodes;
using ReeLib;
using ReeLib.Mdf;

namespace DD2Tool;

internal static class MdfTools
{
    public static MdfFile Load(string path)
    {
        var mdf = new MdfFile(new FileHandler(path));
        if (!mdf.Read()) throw new Exception("mdf read failed: " + path);
        return mdf;
    }

    public static int Info(string path, string outJson)
    {
        var mdf = Load(path);
        var arr = new JsonArray();
        foreach (var m in mdf.Materials) {
            var h = m.Header;
            var tex = new JsonArray();
            foreach (var t in m.Textures) tex.Add(new JsonObject { ["type"] = t.texType, ["path"] = t.texPath });
            var par = new JsonArray();
            foreach (var p in m.Parameters) par.Add(new JsonObject {
                ["name"] = p.paramName, ["n"] = p.componentCount, ["x"] = p.parameter.X, ["y"] = p.parameter.Y, ["z"] = p.parameter.Z, ["w"] = p.parameter.W });
            var gp = new JsonArray();
            foreach (var g in m.GpuBuffers) gp.Add(new JsonObject { ["name"] = g.name, ["path"] = g.path });
            arr.Add(new JsonObject {
                ["name"] = h.matName, ["mmtr"] = h.mmtrPath, ["shaderType"] = h.shaderType.ToString(),
                ["alphaFlags"] = h.alphaFlags, ["flags"] = h.Flags.ToString(), ["ukn"] = h.ukn, ["ukn1"] = h.ukn1,
                ["textures"] = tex, ["params"] = par, ["gpbf"] = gp,
            });
        }
        var root = new JsonObject { ["path"] = path, ["fileVersion"] = mdf.FileHandler.FileVersion, ["version"] = mdf.version, ["materials"] = arr };
        File.WriteAllText(outJson, root.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"{Path.GetFileName(path)}: {mdf.Materials.Count} materials -> {outJson}");
        return 0;
    }
}

internal static class TexTools
{
    public static int ToDds(string tex, string outDds)
    {
        var t = new TexFile(new FileHandler(tex));
        if (!t.Read()) throw new Exception("tex read failed");
        t.SaveAsDDS(outDds);
        Console.WriteLine($"{Path.GetFileName(tex)}: {t.Header.format} {t.Header.width}x{t.Header.height} mips={t.Header.mipCount} -> {outDds}");
        return 0;
    }

    public static int FromDds(string templateTex, string inDds, string outTex)
    {
        var ms = new MemoryStream();
        ms.Write(File.ReadAllBytes(templateTex));
        ms.Position = 0;
        var fh = new FileHandler(ms, outTex);
        var t = new TexFile(fh);
        if (!t.Read()) throw new Exception("template tex read failed");
        var dds = new ReeLib.DDSFile(new FileHandler(inDds));
        if (!dds.Read()) throw new Exception("dds read failed");
        t.LoadDataFromDDS(dds);
        File.WriteAllBytes(outTex, ms.ToArray());
        // verify
        var chk = new TexFile(new FileHandler(outTex));
        if (!chk.Read()) throw new Exception("written tex does not read back");
        Console.WriteLine($"{Path.GetFileName(outTex)}: {chk.Header.format} {chk.Header.width}x{chk.Header.height} mips={chk.Header.mipCount}");
        return 0;
    }
}

internal static class MdfBuild
{
    static byte[] Save(MdfFile mdf, string pathForVersion)
    {
        var ms = new MemoryStream();
        var fh = new FileHandler(ms, pathForVersion);
        mdf.FileHandler = fh;
        if (!mdf.Write()) throw new Exception("mdf write failed");
        return ms.ToArray();
    }

    public static int RoundTrip(string path, string outPath)
    {
        var mdf = MdfTools.Load(path);
        var bytes = Save(mdf, outPath);
        File.WriteAllBytes(outPath, bytes);
        var orig = File.ReadAllBytes(path);
        Console.WriteLine($"roundtrip {Path.GetFileName(path)}: {orig.Length} -> {bytes.Length} identical={orig.AsSpan().SequenceEqual(bytes)}");
        return 0;
    }

    // spec: { "template": mdf, "templateMaterial": name, "output": path,
    //         "materials": [ { "name", "alphaTest": bool, "twoSided": bool, "textures": {type: path}, "params": {name: [x,y,z,w]} } ] }
    public static int Build(string specPath)
    {
        var spec = JsonNode.Parse(File.ReadAllText(specPath))!.AsObject();
        var tmplPath = spec["template"]!.GetValue<string>();
        var outPath = spec["output"]!.GetValue<string>();
        var mdf = MdfTools.Load(tmplPath);
        var src = mdf.Materials.First(m => m.Header.matName == spec["templateMaterial"]!.GetValue<string>());
        mdf.Materials.Clear();
        foreach (var node in spec["materials"]!.AsArray()) {
            var mo = node!.AsObject();
            var c = src.Clone();
            c.Header.matName = mo["name"]!.GetValue<string>();
            var flags = c.Header.Flags;
            if (mo["alphaTest"]?.GetValue<bool>() == true) flags |= MaterialFlags.BaseAlphaTestEnable; else flags &= ~MaterialFlags.BaseAlphaTestEnable;
            if (mo["twoSided"]?.GetValue<bool>() == true) flags |= MaterialFlags.BaseTwoSideEnable; else flags &= ~MaterialFlags.BaseTwoSideEnable;
            c.Header.Flags = flags;
            if (mo["textures"] is JsonObject texs) {
                foreach (var kv in texs) {
                    var t = c.Textures.FirstOrDefault(x => x.texType == kv.Key) ?? throw new Exception($"texture slot {kv.Key} not in template");
                    t.texPath = kv.Value!.GetValue<string>();
                }
            }
            if (mo["params"] is JsonObject pars) {
                foreach (var kv in pars) {
                    var p = c.Parameters.FirstOrDefault(x => x.paramName == kv.Key) ?? throw new Exception($"param {kv.Key} not in template");
                    var a = kv.Value!.AsArray().Select(v => v!.GetValue<float>()).ToArray();
                    p.parameter = new System.Numerics.Vector4(a[0], a.Length > 1 ? a[1] : 0, a.Length > 2 ? a[2] : 0, a.Length > 3 ? a[3] : 0);
                }
            }
            mdf.Materials.Add(c);
        }
        if (spec["copyMaterials"] is JsonArray copies) {
            foreach (var cn in copies) {
                var co = cn!.AsObject();
                var srcMdf = MdfTools.Load(co["file"]!.GetValue<string>());
                foreach (var nn in co["names"]!.AsArray()) {
                    var name = nn!.GetValue<string>();
                    var m = srcMdf.Materials.First(x => x.Header.matName == name);
                    mdf.Materials.Add(m.Clone());
                }
            }
        }
        var bytes = Save(mdf, outPath);
        File.WriteAllBytes(outPath, bytes);
        var chk = MdfTools.Load(outPath);
        Console.WriteLine($"mdfbuild -> {outPath}: {chk.Materials.Count} materials ({string.Join(", ", chk.Materials.Select(m => m.Header.matName + "[" + m.Header.Flags + "]"))})");
        return 0;
    }
}
