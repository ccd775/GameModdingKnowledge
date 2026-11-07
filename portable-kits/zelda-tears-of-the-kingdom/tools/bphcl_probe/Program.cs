using System.Reflection;
using System.Collections;
var dir = Environment.GetEnvironmentVariable("PHYSICSTOOL_DIR")   // portable kit
    ?? throw new InvalidOperationException("Set PHYSICSTOOL_DIR to the PhysicsTool-2.2.0-win-x64 folder.");
AppDomain.CurrentDomain.AssemblyResolve += (s, e) => { var p = Path.Combine(dir, new AssemblyName(e.Name).Name + ".dll"); return File.Exists(p) ? Assembly.LoadFrom(p) : null; };
var doc = HKCLTool.NativeBphclDocument.Open(args[0]);
object G(object o, string n) => o.GetType().GetProperty(n)?.GetValue(o);
IEnumerable<object> L(object o) => ((IEnumerable)o).Cast<object>();
var skels = L(doc.Skeletons).ToDictionary(s => (string)G(s, "Name"), s => L(G(s, "Bones")).ToList());
foreach (var c in doc.Cloths)
{
    var ts = L(G(c, "TransformSetDefinitions")).First(); var tsName = (string)G(ts, "Name");
    var bones = skels.TryGetValue(tsName, out var bl) ? bl.Select(b => (string)G(b, "Name")).ToList() : new List<string>();
    var sc = L(G(c, "SimCloths")).First(); var parts = L(G(sc, "Particles")).ToList();
    var tri = L(G(sc, "TriangleIndices")).Select(Convert.ToInt32).ToList();
    string P(int i) { var v = (System.Numerics.Vector4)G(parts[i], "Position"); return ((bool)G(parts[i], "Fixed") ? "F" : "o") + i + $"({v.X*100:F1},{v.Y*100:F1},{v.Z*100:F1})"; }
    Console.WriteLine($"== {c.Name}");
    foreach (var d in L(G(c, "SimpleMeshBoneDeformers")))
        foreach (var tp in L(G(d, "TriangleBonePairs")))
        {
            int bi = Convert.ToInt32(G(tp, "BoneOffset")) / 64; int to = Convert.ToInt32(G(tp, "TriangleOffset")) / 2;
            var nm = bi < bones.Count ? bones[bi] : "#" + bi;
            Console.WriteLine($"  {nm,-28} tri {to/3}: {P(tri[to])} {P(tri[to+1])} {P(tri[to+2])}");
        }
    foreach (var cs in L(G(sc, "ConstraintSets")))
        Console.WriteLine($"  cs {G(cs, "Name")} {G(cs, "ClassName")}");
}
