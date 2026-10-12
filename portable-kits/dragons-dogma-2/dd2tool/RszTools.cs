using System.Collections;
using System.Text;
using ReeLib;

namespace DD2Tool;

internal static class RszTools
{
    static RszParser? parser;

    static RszFileOption Option(string resDir)
    {
        if (parser == null) {
            parser = RszParser.GetInstance(Path.Combine(resDir, "rsz_template.json"));
            var patch = Path.Combine(resDir, "rsz_patch.json");
            if (File.Exists(patch)) parser.ReadPatch(patch);
        }
        return new RszFileOption(GameName.dd2, parser);
    }

    public static int Dump(string resDir, string input, string output, int maxDepth)
    {
        var opt = Option(resDir);
        var sb = new StringBuilder();
        var lower = input.ToLowerInvariant();
        var fh = new FileHandler(input);
        if (lower.Contains(".pfb.")) {
            var pfb = new PfbFile(opt, fh);
            if (!pfb.Read()) throw new Exception("pfb read failed");
            pfb.SetupGameObjects();
            sb.AppendLine($"# PFB {input}");
            sb.AppendLine("## resources");
            foreach (var r in pfb.ResourceInfoList) sb.AppendLine("  " + r.Path);
            sb.AppendLine("## userdata");
            foreach (var u in pfb.UserdataInfoList) sb.AppendLine("  " + u.Path);
            sb.AppendLine("## gameobjects");
            foreach (var go in pfb.GameObjects) DumpGo(sb, go, 0, maxDepth);
        } else if (lower.Contains(".user.")) {
            var user = new UserFile(opt, fh);
            if (!user.Read()) throw new Exception("user read failed");
            sb.AppendLine($"# USER {input}");
            sb.AppendLine("## resources");
            foreach (var r in user.ResourceInfoList) sb.AppendLine("  " + r.Path);
            foreach (var o in user.RSZ.ObjectList) DumpInst(sb, o, 1, maxDepth, new HashSet<object>(ReferenceEqualityComparer.Instance));
        } else if (lower.Contains(".scn.")) {
            var scn = new ScnFile(opt, fh);
            if (!scn.Read()) throw new Exception("scn read failed");
            scn.SetupGameObjects();
            sb.AppendLine($"# SCN {input}");
            foreach (var r in scn.ResourceInfoList) sb.AppendLine("  " + r.Path);
            foreach (var go in scn.GameObjects!) DumpScnGo(sb, go, 0, maxDepth);
        } else {
            throw new Exception("unsupported file " + input);
        }
        File.WriteAllText(output, sb.ToString(), new UTF8Encoding(false));
        Console.WriteLine($"dumped {input} -> {output} ({sb.Length} chars)");
        return 0;
    }

    static void DumpGo(StringBuilder sb, ReeLib.Pfb.PfbGameObject go, int depth, int maxDepth)
    {
        var ind = new string(' ', depth * 2);
        var name = go.Instance?.GetFieldValue("v0") ?? go.Instance?.Name;
        sb.AppendLine($"{ind}[GO] {name}");
        if (go.Instance != null) DumpInst(sb, go.Instance, depth + 2, maxDepth, new HashSet<object>(ReferenceEqualityComparer.Instance));
        foreach (var c in go.Components) {
            sb.AppendLine($"{ind}  (C) {c.RszClass.name}");
            DumpInst(sb, c, depth + 2, maxDepth, new HashSet<object>(ReferenceEqualityComparer.Instance));
        }
        foreach (var ch in go.Children) DumpGo(sb, ch, depth + 1, maxDepth);
    }

    static void DumpScnGo(StringBuilder sb, ReeLib.Scn.ScnGameObject go, int depth, int maxDepth)
    {
        var ind = new string(' ', depth * 2);
        sb.AppendLine($"{ind}[GO] {go.Instance?.Name}");
        if (go.Instance != null) DumpInst(sb, go.Instance, depth + 2, maxDepth, new HashSet<object>(ReferenceEqualityComparer.Instance));
        foreach (var c in go.Components) {
            sb.AppendLine($"{ind}  (C) {c.RszClass.name}");
            DumpInst(sb, c, depth + 2, maxDepth, new HashSet<object>(ReferenceEqualityComparer.Instance));
        }
        foreach (var ch in go.Children) DumpScnGo(sb, ch, depth + 1, maxDepth);
    }

    static void DumpInst(StringBuilder sb, RszInstance inst, int depth, int maxDepth, HashSet<object> seen)
    {
        var ind = new string(' ', depth * 2);
        if (depth > maxDepth) { sb.AppendLine($"{ind}..."); return; }
        if (!seen.Add(inst)) { sb.AppendLine($"{ind}<cycle {inst.RszClass.name}>"); return; }
        for (int i = 0; i < inst.Fields.Length && i < inst.Values.Length; i++) {
            var f = inst.Fields[i];
            var v = inst.Values[i];
            DumpValue(sb, f.name, v, depth, maxDepth, seen);
        }
    }

    static void DumpValue(StringBuilder sb, string name, object? v, int depth, int maxDepth, HashSet<object> seen)
    {
        var ind = new string(' ', depth * 2);
        switch (v) {
            case RszInstance ri:
                sb.AppendLine($"{ind}{name}: <{ri.RszClass.name}>");
                DumpInst(sb, ri, depth + 1, maxDepth, seen);
                break;
            case string s:
                sb.AppendLine($"{ind}{name}: \"{s}\"");
                break;
            case IList list when v is not string:
                sb.AppendLine($"{ind}{name}: [{list.Count}]");
                int n = 0;
                foreach (var item in list) {
                    if (n++ >= 400) { sb.AppendLine($"{ind}  ...({list.Count - 400} more)"); break; }
                    DumpValue(sb, $"[{n - 1}]", item, depth + 1, maxDepth, seen);
                }
                break;
            default:
                sb.AppendLine($"{ind}{name}: {FormatScalar(v)}");
                break;
        }
    }

    static string FormatScalar(object? v)
    {
        if (v == null) return "null";
        var t = v.GetType();
        if (t.IsPrimitive || v is Guid || v is decimal || t.IsEnum) return v.ToString() ?? "";
        var fields = t.GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
        if (fields.Length > 0 && fields.Length <= 20) {
            return "{" + string.Join(", ", fields.Select(f => $"{f.Name}={f.GetValue(v)}")) + "}";
        }
        return v.ToString() ?? "";
    }
}
