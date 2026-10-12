using System.Collections;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Nodes;
using ReeLib;
using ReeLib.Common;

namespace DD2Tool;

internal static class Reflect
{
    const BindingFlags F = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance;

    public static JsonNode? ToJson(object? o, int depth = 0)
    {
        if (o == null) return null;
        var t = o.GetType();
        if (o is string s) return JsonValue.Create(s);
        if (t.IsEnum) return JsonValue.Create(o.ToString());
        if (t.IsPrimitive) {
            return o switch {
                float f => JsonValue.Create(float.IsFinite(f) ? f : 0f),
                double d => JsonValue.Create(double.IsFinite(d) ? d : 0d),
                _ => JsonValue.Create(Convert.ToDouble(o)),
            };
        }
        if (o is System.Numerics.Vector2 v2) return new JsonArray(v2.X, v2.Y);
        if (o is System.Numerics.Vector3 v3) return new JsonArray(v3.X, v3.Y, v3.Z);
        if (o is System.Numerics.Vector4 v4) return new JsonArray(v4.X, v4.Y, v4.Z, v4.W);
        if (o is System.Numerics.Quaternion q) return new JsonArray(q.X, q.Y, q.Z, q.W);
        if (depth > 8) return JsonValue.Create(o.ToString());
        if (o is IEnumerable e) {
            var arr = new JsonArray();
            foreach (var x in e) arr.Add(ToJson(x, depth + 1));
            return arr;
        }
        if (t.IsValueType && t.GetFields(F).Length == 0) return JsonValue.Create(o.ToString());
        var obj = new JsonObject();
        for (var tt = t; tt != null && tt != typeof(object); tt = tt.BaseType) {
            foreach (var f in tt.GetFields(F | BindingFlags.DeclaredOnly)) {
                if (f.Name.Contains("k__BackingField")) {
                    var pn = f.Name.Substring(1, f.Name.IndexOf('>') - 1);
                    if (pn is "FileHandler" or "Start" or "Size") continue;
                    obj[pn] = ToJson(f.GetValue(o), depth + 1);
                    continue;
                }
                if (typeof(FileHandler).IsAssignableFrom(f.FieldType)) continue;
                if (obj.ContainsKey(f.Name)) continue;
                obj[f.Name] = ToJson(f.GetValue(o), depth + 1);
            }
        }
        return obj;
    }
}

internal static class ChainTools
{
    public static int Info(string path, string outJson)
    {
        var chain = new ChainFile(new FileHandler(path));
        if (!chain.Read()) throw new Exception("chain read failed");
        var root = new JsonObject {
            ["path"] = path,
            ["Header"] = Reflect.ToJson(chain.Header),
            ["Settings"] = Reflect.ToJson(chain.Settings),
            ["WindSettings"] = Reflect.ToJson(chain.WindSettings),
            ["Groups"] = Reflect.ToJson(chain.Groups),
            ["Collisions"] = Reflect.ToJson(chain.Collisions),
            ["ChainLinks"] = Reflect.ToJson(chain.ChainLinks),
            ["HitFlags"] = Reflect.ToJson(chain.HitFlags),
        };
        File.WriteAllText(outJson, root.ToJsonString(new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"{Path.GetFileName(path)}: groups={chain.Groups.Count} settings={chain.Settings.Count} collisions={chain.Collisions.Count} links={chain.ChainLinks.Count} -> {outJson}");
        return 0;
    }

    public static int RoundTrip(string path, string outPath)
    {
        var chain = new ChainFile(new FileHandler(path));
        if (!chain.Read()) throw new Exception("chain read failed");
        var ms = new MemoryStream();
        chain.FileHandler = new FileHandler(ms, outPath);
        if (!chain.Write()) throw new Exception("chain write failed");
        File.WriteAllBytes(outPath, ms.ToArray());
        var orig = File.ReadAllBytes(path);
        Console.WriteLine($"roundtrip {Path.GetFileName(path)}: {orig.Length} -> {ms.Length} identical={orig.AsSpan().SequenceEqual(ms.ToArray())}");
        return 0;
    }
}

internal static class ChainBuild
{
    static ChainFile Load(string path)
    {
        var c = new ChainFile(new FileHandler(path));
        if (!c.Read()) throw new Exception("chain read failed: " + path);
        return c;
    }

    static void SetField(object o, string name, JsonNode v)
    {
        var f = o.GetType().GetField(name, System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)
            ?? throw new Exception($"{o.GetType().Name} has no field {name}");
        object val = f.FieldType switch {
            var t when t == typeof(float) => v.GetValue<float>(),
            var t when t == typeof(int) => v.GetValue<int>(),
            var t when t == typeof(uint) => v.GetValue<uint>(),
            var t when t == typeof(byte) => v.GetValue<byte>(),
            var t when t == typeof(bool) => v.GetValue<bool>(),
            var t when t == typeof(System.Numerics.Vector2) => new System.Numerics.Vector2(v[0]!.GetValue<float>(), v[1]!.GetValue<float>()),
            var t when t == typeof(System.Numerics.Vector3) => new System.Numerics.Vector3(v[0]!.GetValue<float>(), v[1]!.GetValue<float>(), v[2]!.GetValue<float>()),
            var t when t.IsEnum => Enum.Parse(t, v.GetValue<string>()),
            _ => throw new Exception($"unsupported field type {f.FieldType} for {name}"),
        };
        f.SetValue(o, val);
    }

    // spec: {
    //   "base": chain (header + groups/settings kept), "output": path,
    //   "settings": { "<key>": { "file": chain, "index": n, "set": { field: value } } },
    //   "groups": [ { "joints": [root..terminal], "setting": key, "template": { "file": chain, "group": n },
    //                 "radius": [r0, r1] (linear root->tip) , "node": { field: value }, "group": { field: value } } ]
    // }
    public static int Build(string specPath)
    {
        var spec = JsonNode.Parse(File.ReadAllText(specPath))!.AsObject();
        var outPath = spec["output"]!.GetValue<string>();
        var chain = Load(spec["base"]!.GetValue<string>());
        if (spec["clearBase"]?.GetValue<bool>() == true) {
            chain.Groups.Clear();
            chain.Settings.Clear();
            chain.ChainLinks.Clear();
            chain.WindSettings.Clear();
            chain.Collisions.Clear();
        }
        var cache = new Dictionary<string, ChainFile>();
        ChainFile Get(string p) => cache.TryGetValue(p, out var c) ? c : cache[p] = Load(p);

        var settings = new Dictionary<string, ReeLib.Chain.ChainSetting>();
        int nextId = chain.Settings.Count == 0 ? 0 : chain.Settings.Max(s => s.id) + 1;
        foreach (var kv in spec["settings"]!.AsObject()) {
            var so = kv.Value!.AsObject();
            var src = Get(so["file"]!.GetValue<string>()).Settings[so["index"]!.GetValue<int>()];
            var s = (ReeLib.Chain.ChainSetting)src.Clone();
            s.id = nextId++;
            s.WindSettings = null;
            s.windId = 0;
            if (so["set"] is JsonObject set) foreach (var f in set) SetField(s, f.Key, f.Value!);
            chain.Settings.Add(s);
            settings[kv.Key] = s;
        }
        foreach (var gn in spec["groups"]!.AsArray()) {
            var go = gn!.AsObject();
            var joints = go["joints"]!.AsArray().Select(j => j!.GetValue<string>()).ToList();
            var tf = go["template"]!.AsObject();
            var tg = Get(tf["file"]!.GetValue<string>()).Groups[tf["group"]!.GetValue<int>()];
            var g = new ReeLib.Chain.ChainGroup();
            foreach (var f in typeof(ReeLib.Chain.ChainGroupBase).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)) {
                var v = f.GetValue(tg);
                if (v is Array arr) v = arr.Clone();
                f.SetValue(g, v);
            }
            g.name = joints[^1];
            g.terminalNameHash = MurMur3HashUtils.GetHash(joints[^1]);
            g.Settings = settings[go["setting"]!.GetValue<string>()];
            g.WindSettings = null;
            g.windId = 0;
            // group field overrides, e.g. "clspFlags1": "V15, V16" (which of the character's collision shapes it hits)
            if (go["group"] is JsonObject gset) foreach (var f in gset) SetField(g, f.Key, f.Value!);
            var tnode = tg.ChainNodes[0];
            var radius = go["radius"]?.AsArray().Select(x => x!.GetValue<float>()).ToArray() ?? new[] { tnode.collisionRadius, tnode.collisionRadius };
            var aldir = go["aldir"]?.AsArray();
            for (int i = 0; i < joints.Count; i++) {
                var n = (ReeLib.Chain.ChainNode)tnode.Clone();
                n.JiggleData = null;
                n.angleLimitDirection = System.Numerics.Quaternion.Identity;
                if (aldir != null) {
                    var q = aldir[i]!.AsArray();
                    n.angleLimitDirection = new System.Numerics.Quaternion(q[0]!.GetValue<float>(), q[1]!.GetValue<float>(), q[2]!.GetValue<float>(), q[3]!.GetValue<float>());
                }
                float t = joints.Count == 1 ? 0 : i / (float)(joints.Count - 1);
                n.collisionRadius = radius[0] + (radius[^1] - radius[0]) * t;
                if (go["node"] is JsonObject nset) foreach (var f in nset) SetField(n, f.Key, f.Value!);
                g.ChainNodes.Add(n);
            }
            typeof(ReeLib.Chain.ChainGroupBase).GetField("nodeCount", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)!.SetValue(g, (byte)joints.Count);
            g.ChainSubGroups.Clear();
            typeof(ReeLib.Chain.ChainGroupBase).GetField("subGroupCount", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)!.SetValue(g, (short)0);
            chain.Groups.Add(g);
        }
        var ms = new MemoryStream();
        chain.FileHandler = new FileHandler(ms, outPath);
        if (!chain.Write()) throw new Exception("chain write failed");
        File.WriteAllBytes(outPath, ms.ToArray());
        var chk = Load(outPath);
        Console.WriteLine($"chainbuild -> {outPath}: groups={chk.Groups.Count} settings={chk.Settings.Count} (L_Breast hash check {MurMur3HashUtils.GetHash("L_Breast")})");
        return 0;
    }
}
