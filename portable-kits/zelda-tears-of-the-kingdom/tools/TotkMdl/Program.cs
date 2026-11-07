// TotkMdl: headless driver around Switch Toolbox's BFRES code for TotK (.bfres.mc).
// Commands:
//   info    <in.bfres[.mc]> <romfs> <out.json>
//   export  <in.bfres[.mc]> <romfs> <out.json>          (info + per-shape vertices/faces)
//   replace <in.bfres[.mc]> <romfs> <edit.json> <out.bfres.mc>
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

static class Program
{
    static string StDir;

    [STAThread]
    static int Main(string[] args)
    {
        StDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
        AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
        {
            string name = new AssemblyName(e.Name).Name + ".dll";
            foreach (var dir in new[] { StDir, Path.Combine(StDir, "Lib"), Path.Combine(StDir, "Lib", "Plugins") })
            {
                string p = Path.Combine(dir, name);
                if (File.Exists(p)) return Assembly.LoadFrom(p);
            }
            return null;
        };
        try { return Impl.Run(args); }
        catch (Exception ex) { Console.Error.WriteLine("ERROR: " + ex); return 1; }
    }
}

static class Impl
{
    public static int Run(string[] a)
    {
        if (a.Length < 3) { Console.Error.WriteLine("usage: info|export|replace <in> <romfs> ..."); return 2; }
        string cmd = a[0], input = a[1], romfs = a[2];
        if (cmd == "anims") { DumpAnims(input, a[3], a.Length > 4 ? a[4] : "."); Console.WriteLine("ok anims"); return 0; }
        // ST's loaders query the (normally present) main window; give them a hidden MDI form.
        Toolbox.Library.Runtime.MainForm = new System.Windows.Forms.Form { IsMdiContainer = true };
        Toolbox.Library.Runtime.TotkGamePath = romfs;
        var bf = Load(input);
        switch (cmd)
        {
            case "info": File.WriteAllText(a[3], Describe(bf, false).ToString(Formatting.Indented)); break;
            case "export": File.WriteAllText(a[3], Describe(bf, true).ToString(Formatting.None)); break;
            case "replace": Replace(bf, JObject.Parse(File.ReadAllText(a[3]))); Save(bf, a[4]); break;
            default: Console.Error.WriteLine("unknown command"); return 2;
        }
        Console.WriteLine("ok " + cmd);
        return 0;
    }

    // anims <raw anim .bfres> <romfs (unused)> <out.json> [boneRegex]
    // Skeletal anims: name, frame count, rotate mode, and for bones matching boneRegex the base data + raw curves.
    static void DumpAnims(string path, string outPath, string boneRegex)
    {
        var rx = new System.Text.RegularExpressions.Regex(boneRegex);
        var rf = new Syroot.NintenTools.NSW.Bfres.ResFile(new MemoryStream(File.ReadAllBytes(path)), false);
        var res = new JArray();
        foreach (var ska in rf.SkeletalAnims)
        {
            var ja = new JObject
            {
                ["name"] = ska.Name, ["frames"] = ska.FrameCount, ["rotate"] = ska.FlagsRotate.ToString(),
                ["loop"] = ska.Loop, ["baked"] = ska.Baked, ["nbones"] = ska.BoneAnims.Count,
            };
            var bones = new JArray();
            foreach (var ba in ska.BoneAnims)
            {
                if (!rx.IsMatch(ba.Name ?? "")) continue;
                var jb = new JObject
                {
                    ["name"] = ba.Name, ["flagsBase"] = ba.FlagsBase.ToString(), ["flagsCurve"] = ba.FlagsCurve.ToString(),
                    ["flagsTransform"] = ba.FlagsTransform.ToString(), ["beginRotate"] = ba.BeginRotate, ["beginTranslate"] = ba.BeginTranslate,
                    ["base"] = Fields(ba.BaseData),
                };
                var curves = new JArray();
                foreach (var c in ba.Curves)
                {
                    var keys = new JArray();
                    if (c.Keys != null)
                        for (int i = 0; i < c.Keys.GetLength(0); i++)
                        {
                            var row = new JArray();
                            for (int j = 0; j < c.Keys.GetLength(1); j++) row.Add(c.Keys[i, j]);
                            keys.Add(row);
                        }
                    curves.Add(new JObject
                    {
                        ["offset"] = c.AnimDataOffset, ["curveType"] = c.CurveType.ToString(), ["frameType"] = c.FrameType.ToString(),
                        ["keyType"] = c.KeyType.ToString(), ["start"] = c.StartFrame, ["end"] = c.EndFrame, ["scale"] = c.Scale,
                        ["valOffset"] = ToFloat(c.Offset), ["delta"] = c.Delta, ["hermite"] = c.IsHermite, ["stepFloat"] = c.IsStepFloat,
                        ["frames"] = c.Frames == null ? null : new JArray(c.Frames), ["keys"] = keys,
                        ["hermiteValues"] = c.HermiteValues == null ? null : new JArray(c.HermiteValues),
                        ["hermiteSlopes"] = c.HermiteSlopes == null ? null : new JArray(c.HermiteSlopes),
                    });
                }
                jb["curves"] = curves;
                bones.Add(jb);
            }
            ja["bones"] = bones;
            res.Add(ja);
        }
        File.WriteAllText(outPath, res.ToString(Formatting.None));
        Console.WriteLine($"{res.Count} skeletal anims");
    }

    static JToken Fields(object o)
    {
        if (o == null) return JValue.CreateNull();
        var t = o.GetType();
        if (t.IsPrimitive || o is string || t.IsEnum) return new JValue(t.IsEnum ? o.ToString() : o);
        var jo = new JObject();
        foreach (var f in t.GetFields(BindingFlags.Public | BindingFlags.Instance)) jo[f.Name] = Fields(f.GetValue(o));
        foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.Instance))
            if (p.GetIndexParameters().Length == 0) { try { jo[p.Name] = Fields(p.GetValue(o)); } catch { } }
        return jo;
    }

    static float ToFloat(object dword)
    {
        if (dword == null) return 0;
        var t = dword.GetType();
        foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Static))
            if ((m.Name == "op_Implicit" || m.Name == "op_Explicit") && m.ReturnType == typeof(float)) return (float)m.Invoke(null, new[] { dword });
        var p = t.GetProperty("Single") ?? t.GetProperty("Float");
        return p != null ? Convert.ToSingle(p.GetValue(dword)) : 0f;
    }

    static FirstPlugin.BFRES Load(string path)
    {
        var bf = new FirstPlugin.BFRES();
        bf.FileName = Path.GetFileName(path);
        bf.FilePath = path;
        bf.IFileInfo = new Toolbox.Library.IFileInfo();
        byte[] data = File.ReadAllBytes(path);
        if (path.EndsWith(".mc"))
        {
            var fmt = new Toolbox.Library.MeshCodecFormat();
            var ms = new MemoryStream();
            fmt.Decompress(new MemoryStream(data)).CopyTo(ms);
            data = ms.ToArray();
            bf.IFileInfo.FileIsCompressed = true;
            bf.IFileInfo.FileCompression = fmt;
        }
        bf.Load(new MemoryStream(data));
        return bf;
    }

    static void Save(FirstPlugin.BFRES bf, string outPath)
    {
        var raw = new MemoryStream();
        bf.Save(raw);
        byte[] bytes = raw.ToArray();
        if (outPath.EndsWith(".mc"))
        {
            var ms = new MemoryStream();
            new Toolbox.Library.MeshCodecFormat().Compress(new MemoryStream(bytes)).CopyTo(ms);
            File.WriteAllBytes(outPath.Substring(0, outPath.Length - 3), bytes);
            bytes = ms.ToArray();
        }
        File.WriteAllBytes(outPath, bytes);
        Console.WriteLine($"saved {outPath} {bytes.Length}");
    }

    static IEnumerable<Bfres.Structs.FMDL> Models(FirstPlugin.BFRES bf)
    {
        var coll = bf.GetModels();
        if (coll == null) yield break;
        foreach (var n in coll) if (n is Bfres.Structs.FMDL m) yield return m;
    }

    static JArray V(OpenTK.Vector2 v) => new JArray(v.X, v.Y);
    static JArray V(OpenTK.Vector3 v) => new JArray(v.X, v.Y, v.Z);
    static JArray V(OpenTK.Vector4 v) => new JArray(v.X, v.Y, v.Z, v.W);

    static JObject Describe(FirstPlugin.BFRES bf, bool withVerts)
    {
        var root = new JObject();
        var models = new JArray();
        foreach (var mdl in Models(bf))
        {
            var jm = new JObject { ["name"] = mdl.Text };
            var skl = mdl.Skeleton;
            var bones = new JArray();
            for (int i = 0; i < skl.bones.Count; i++)
            {
                var b = (Bfres.Structs.BfresBone)skl.bones[i];
                var q = b.Rotation;
                bones.Add(new JObject
                {
                    ["i"] = i, ["name"] = b.Text, ["parent"] = b.parentIndex,
                    ["smooth"] = b.SmoothMatrixIndex, ["rigid"] = b.RigidMatrixIndex,
                    ["pos"] = V(b.Position), ["quat"] = new JArray(q.X, q.Y, q.Z, q.W), ["scale"] = V(b.Scale),
                    ["rotType"] = b.RotationType.ToString(),
                });
            }
            jm["bones"] = bones;
            jm["nodeArray"] = new JArray(skl.Node_Array ?? new int[0]);
            var shapes = new JArray();
            foreach (var s in mdl.shapes)
            {
                var js = new JObject
                {
                    ["name"] = s.Text, ["material"] = s.GetMaterial()?.Text, ["skin"] = s.VertexSkinCount,
                    ["boneIndex"] = s.BoneIndex, ["nverts"] = s.vertices.Count, ["lods"] = s.lodMeshes.Count,
                    ["attrs"] = new JArray(s.vertexAttributes.Select(x => new JObject { ["name"] = x.Name, ["fmt"] = x.Format.ToString() })),
                    ["boneIndices"] = new JArray(s.BoneIndices.Select(x => (int)x)),
                };
                if (withVerts)
                {
                    var pos = new JArray(); var nrm = new JArray(); var uv = new JArray(); var bn = new JArray(); var bw = new JArray(); var col = new JArray();
                    foreach (var v in s.vertices)
                    {
                        pos.Add(V(v.pos)); nrm.Add(V(v.nrm)); uv.Add(V(v.uv0)); col.Add(V(v.col));
                        var names = new JArray();
                        foreach (var id in v.boneIds)
                        {
                            string nm;
                            if (s.VertexSkinCount <= 1) nm = id < skl.bones.Count ? skl.bones[id].Text : ("?" + id);
                            else nm = (skl.Node_Array != null && id < skl.Node_Array.Length) ? skl.bones[skl.Node_Array[id]].Text : ("?" + id);
                            names.Add(nm);
                        }
                        bn.Add(names); bw.Add(new JArray(v.boneWeights));
                    }
                    js["pos"] = pos; js["nrm"] = nrm; js["uv0"] = uv; js["col"] = col; js["boneNames"] = bn; js["boneWeights"] = bw;
                    js["boneIds"] = new JArray(s.vertices.Select(v => new JArray(v.boneIds)));
                    js["faces"] = s.lodMeshes.Count > 0 ? new JArray(s.lodMeshes[0].faces) : new JArray();
                }
                shapes.Add(js);
            }
            jm["shapes"] = shapes;
            var mats = new JArray();
            foreach (var m in mdl.materials.Values)
            {
                var jt = new JArray(m.TextureMaps.Select(t => new JObject { ["name"] = t.Name, ["sampler"] = t.SamplerName }));
                var opts = new JObject();
                foreach (var kv in m.shaderassign.options) opts[kv.Key] = kv.Value;
                var samplers = new JObject();
                foreach (var kv in m.shaderassign.samplers) samplers[kv.Key] = kv.Value;
                var attribs = new JObject();
                foreach (var kv in m.shaderassign.attributes) attribs[kv.Key] = kv.Value;
                mats.Add(new JObject { ["name"] = m.Text, ["textures"] = jt, ["shader"] = m.shaderassign.ShaderModel, ["archive"] = m.shaderassign.ShaderArchive, ["options"] = opts, ["samplers"] = samplers, ["attribs"] = attribs });
            }
            jm["materials"] = mats;
            models.Add(jm);
        }
        root["models"] = models;
        return root;
    }

    // edit.json:
    // { "delete": ["shape", ...],
    //   "shapes": { "shapeName": { "pos":[x,y,z,...], "nrm":[...], "uv0":[u,v,...], "uv1":[...]?, "col":[r,g,b,a,...]?,
    //                              "bones":[["b1","b2"],...], "weights":[[w1,w2],...], "faces":[i,...], "skin": n? } },
    //   "textures": { "materialName": { "oldTex": "newTex" } } }
    // Additional edit keys (applied in this order):
    //   "copyMaterials": { "targetMat": "sourceMat" }       deep copy (bfmat export/import), target keeps its name
    //   "samplerTextures": { "mat": { "_a0": "TexName" } }  set texture by sampler name
    //   "smoothBones": [bone names]                          rebuild smooth matrix list (Node_Array), no rigid entries
    //   "newShapes": [ { "name", "template", "material" } ]  empty shape with the template's attribute layout/skin count
    static void Replace(FirstPlugin.BFRES bf, JObject edit)
    {
        foreach (var mdl in Models(bf))
        {
            var del = new HashSet<string>(((JArray)edit["delete"] ?? new JArray()).Select(x => (string)x));
            var templates = new Dictionary<string, Bfres.Structs.FSHP>();
            foreach (var s in mdl.shapes) templates[s.Text] = s;
            foreach (var s in mdl.shapes.Where(s => del.Contains(s.Text)).ToList())
            {
                mdl.shapes.Remove(s);
                s.Parent?.Nodes.Remove(s);
                Console.WriteLine("deleted shape " + s.Text);
            }

            foreach (var kv in (JObject)edit["copyMaterials"] ?? new JObject())
            {
                var dst = mdl.materials[kv.Key]; var src = mdl.materials[(string)kv.Value];
                var m = (Syroot.NintenTools.NSW.Bfres.Material)typeof(object)
                    .GetMethod("MemberwiseClone", BindingFlags.NonPublic | BindingFlags.Instance).Invoke(src.Material, null);
                m.Name = dst.Text;
                FirstPlugin.BfresSwitch.ReadMaterial(dst, m);
                // SetMaterial() rewrites these collections on save; give the copy its own instances.
                foreach (var f in m.GetType().GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
                {
                    var v = f.GetValue(m);
                    if (v == null) continue;
                    var t = v.GetType();
                    if (t.IsGenericType && t.GetGenericTypeDefinition() == typeof(List<>))
                        f.SetValue(m, Activator.CreateInstance(t, v));
                    else if (v is Syroot.NintenTools.NSW.Bfres.ResDict rd)
                    {
                        var nd = new Syroot.NintenTools.NSW.Bfres.ResDict();
                        for (int i = 0; i < rd.Count; i++) nd.Add(rd.GetKey(i));
                        f.SetValue(m, nd);
                    }
                }
                dst.Material = m;
                Console.WriteLine($"material {dst.Text} <- copy of {src.Text}");
            }

            foreach (var kv in (JObject)edit["samplerTextures"] ?? new JObject())
            {
                var mat = mdl.materials[kv.Key];
                foreach (var t in mat.TextureMaps)
                {
                    var nn = (string)((JObject)kv.Value)[t.SamplerName];
                    if (nn != null) { Console.WriteLine($"tex {kv.Key}.{t.SamplerName}: {t.Name} -> {nn}"); t.Name = nn; }
                }
            }

            var texEdits = (JObject)edit["textures"] ?? new JObject();
            foreach (var kv in texEdits)
            {
                if (!mdl.materials.TryGetValue(kv.Key, out var mat)) { Console.WriteLine("WARN no material " + kv.Key); continue; }
                foreach (var t in mat.TextureMaps)
                {
                    var nn = (string)((JObject)kv.Value)[t.Name];
                    if (nn != null) { Console.WriteLine($"tex {kv.Key}: {t.Name} -> {nn}"); t.Name = nn; }
                }
            }

            if (edit["smoothBones"] is JArray sb)
            {
                var want = new HashSet<string>(sb.Select(x => (string)x));
                var skl = mdl.Skeleton;
                var list = new List<ushort>();
                short idx = 0;
                for (int i = 0; i < skl.bones.Count; i++)
                {
                    var b = (Bfres.Structs.BfresBone)skl.bones[i];
                    b.SmoothMatrixIndex = want.Contains(b.Text) ? idx++ : (short)-1;
                    b.RigidMatrixIndex = -1;
                    if (b.Bone != null) { b.Bone.SmoothMatrixIndex = b.SmoothMatrixIndex; b.Bone.RigidMatrixIndex = -1; }
                    if (b.SmoothMatrixIndex != -1) list.Add((ushort)i);
                }
                foreach (var n in want) if (!skl.bones.Any(x => x.Text == n)) Console.WriteLine("WARN smooth bone missing " + n);
                skl.Node_Array = list.Select(x => (int)x).ToArray();
                skl.node.Skeleton.MatrixToBoneList = list;
                Console.WriteLine($"smooth bones: {list.Count}");
            }

            foreach (JObject ns in (JArray)edit["newShapes"] ?? new JArray())
            {
                var tpl = templates[(string)ns["template"]];
                var mesh = new Bfres.Structs.FSHP();
                mesh.Text = (string)ns["name"];
                Bfres.Structs.FSHPFolder.CreateEmptyMesh(mdl, mesh);
                mesh.Text = (string)ns["name"];
                mesh.vertexAttributes = tpl.vertexAttributes.Select(a => new Bfres.Structs.FSHP.VertexAttribute { Name = a.Name, Format = a.Format, BufferIndex = a.BufferIndex }).ToList();
                mesh.VertexSkinCount = tpl.VertexSkinCount;
                string matName = (string)ns["material"];
                mesh.MaterialIndex = mdl.materials.Keys.ToList().IndexOf(matName);
                if (mesh.MaterialIndex < 0) throw new Exception("no material " + matName);
                mesh.BoneIndex = 0;
                Console.WriteLine($"new shape {mesh.Text} (template {tpl.Text}, material {matName} #{mesh.MaterialIndex}, skin {mesh.VertexSkinCount})");
            }

            foreach (var kv in (JObject)edit["shapeMaterial"] ?? new JObject())
            {
                var fshp = mdl.shapes.First(s => s.Text == kv.Key);
                fshp.MaterialIndex = mdl.materials.Keys.ToList().IndexOf((string)kv.Value);
                if (fshp.MaterialIndex < 0) throw new Exception("no material " + kv.Value);
                Console.WriteLine($"shape {kv.Key} -> material {kv.Value} #{fshp.MaterialIndex}");
            }

            var shapes = (JObject)edit["shapes"] ?? new JObject();
            foreach (var kv in shapes)
            {
                var fshp = mdl.shapes.FirstOrDefault(s => s.Text == kv.Key);
                if (fshp == null) { Console.WriteLine("WARN no shape " + kv.Key); continue; }
                ReplaceShape(mdl, fshp, (JObject)kv.Value);
            }

            foreach (var kv in (JObject)edit["rename"] ?? new JObject())
            {
                var fshp = mdl.shapes.First(s => s.Text == kv.Key);
                fshp.Text = (string)kv.Value;
                Console.WriteLine($"renamed shape {kv.Key} -> {kv.Value}");
            }

            // "renameMaterials": { "old": "new" } — keeps dictionary order so shape MaterialIndex values stay valid.
            // Used to detach materials from the armor's dye texture-pattern anims (Armor_XXXX.anim *_ftp bind by material name).
            if (edit["renameMaterials"] is JObject mr && mr.Count > 0)
            {
                var entries = mdl.materials.ToList();
                foreach (var key in mr.Properties().Select(p => p.Name))
                    if (!mdl.materials.ContainsKey(key)) throw new Exception("no material " + key);
                mdl.materials.Clear();
                foreach (var e in entries)
                {
                    var name = (string)mr[e.Key] ?? e.Key;
                    e.Value.Text = name;
                    if (e.Value.Material != null) e.Value.Material.Name = name;
                    mdl.materials.Add(name, e.Value);
                    if (name != e.Key) Console.WriteLine($"renamed material {e.Key} -> {name}");
                }
            }
        }
    }

    static float[] F(JToken t) => t == null ? null : t.Select(x => (float)x).ToArray();
    static T ParseEnum<T>(T _, string s) where T : struct => (T)Enum.Parse(typeof(T), s);

    static void ReplaceShape(Bfres.Structs.FMDL mdl, Bfres.Structs.FSHP fshp, JObject d)
    {
        var pos = F(d["pos"]); var nrm = F(d["nrm"]); var uv0 = F(d["uv0"]); var uv1 = F(d["uv1"]); var col = F(d["col"]);
        var bones = (JArray)d["bones"]; var weights = (JArray)d["weights"];
        int n = pos.Length / 3;
        var verts = new List<Toolbox.Library.Rendering.Vertex>(n);
        for (int i = 0; i < n; i++)
        {
            var v = new Toolbox.Library.Rendering.Vertex();
            v.pos = new OpenTK.Vector3(pos[i * 3], pos[i * 3 + 1], pos[i * 3 + 2]);
            if (nrm != null) v.nrm = new OpenTK.Vector3(nrm[i * 3], nrm[i * 3 + 1], nrm[i * 3 + 2]);
            if (uv0 != null) v.uv0 = new OpenTK.Vector2(uv0[i * 2], uv0[i * 2 + 1]);
            if (uv1 != null) v.uv1 = new OpenTK.Vector2(uv1[i * 2], uv1[i * 2 + 1]); else v.uv1 = v.uv0;
            v.uv2 = v.uv0;
            if (col != null) v.col = new OpenTK.Vector4(col[i * 4], col[i * 4 + 1], col[i * 4 + 2], col[i * 4 + 3]);
            foreach (var b in (JArray)bones[i]) v.boneNames.Add((string)b);
            foreach (var w in (JArray)weights[i]) v.boneWeights.Add((float)w);
            verts.Add(v);
        }
        var faces = d["faces"].Select(x => (int)x).ToList();

        var obj = new Toolbox.Library.STGenericObject();
        obj.vertices = verts;
        var lod = new Toolbox.Library.STGenericObject.LOD_Mesh();
        lod.PrimativeType = Toolbox.Library.STPrimitiveType.Triangles;
        lod.IndexFormat = n > 65535 ? Toolbox.Library.Rendering.STIndexFormat.UInt32 : Toolbox.Library.Rendering.STIndexFormat.UInt16;
        lod.faces = faces;
        lod.GenerateSubMesh();
        obj.lodMeshes = new List<Toolbox.Library.STGenericObject.LOD_Mesh> { lod };
        obj.HasIndices = false;
        obj.HasWeights = true;

        if (d["skin"] != null)
        {
            int newSkin = (int)d["skin"];
            if (newSkin != fshp.VertexSkinCount)
            {
                Console.WriteLine($"{fshp.Text}: skin {fshp.VertexSkinCount} -> {newSkin}");
                fshp.UpdateVertexSkinCount(newSkin);
            }
        }
        byte force = fshp.VertexSkinCount;
        var originalAttributes = fshp.vertexAttributes;

        fshp.VertexBufferIndex = 0;
        fshp.vertices = obj.vertices;
        fshp.vertexAttributes = originalAttributes;
        obj.VertexSkinCount = force;
        fshp.lodMeshes = obj.lodMeshes;
        var wf = (string)d["weightFormat"];
        var rawW = verts.Select(v => v.boneNames.Zip(v.boneWeights, (b, w) => (b, w)).GroupBy(x => x.b)
                                      .ToDictionary(g => g.Key, g => g.Sum(x => x.w))).ToList();
        fshp.CreateBoneList(obj, mdl, true, force);
        // slot order after CreateBoneList = boneIds (indices into Node_Array, sorted); map back to the raw weights by name
        float[][] rawSlots = null;
        if (wf != null)
            rawSlots = verts.Select((v, i) =>
            {
                var left = new Dictionary<string, float>(rawW[i]);  // each name once; padding slots (id 0, weight 0) get 0
                return v.boneIds.Select(id =>
                {
                    var nm = mdl.Skeleton.bones[mdl.Skeleton.Node_Array[id]].Text;
                    if (!left.TryGetValue(nm, out var w)) return 0f;
                    left.Remove(nm); return w;
                }).ToArray();
            }).ToArray();
        fshp.CreateIndexList(obj, mdl, true, force);
        fshp.BoneIndices = fshp.GetIndices(mdl.Skeleton);

        if (fshp.vertexAttributes.Any(x => x.Name == "_t0"))
        {
            int uvIndex = 0;
            var mat = fshp.GetFMAT();
            if (mat != null && mat.shaderassign.options.ContainsKey("o_texture2_texcoord"))
                int.TryParse(mat.shaderassign.options["o_texture2_texcoord"], out uvIndex);
            fshp.CalculateTangentBitangent(uvIndex);
        }
        fshp.CreateNewBoundingBoxes(mdl);
        fshp.OptmizeAttributeFormats();
        // "weightFormat": e.g. "Format_32_32_32_32_Single" — float skin weights so they can be > 1 or negative
        // (face rig amplifies Link's small eyelid motion; weights still sum to 1). Vanilla is 8_8_8_8_UNorm.
        if (wf != null)
            foreach (var a in fshp.vertexAttributes.Where(x => x.Name.StartsWith("_w")))
                a.Format = ParseEnum(a.Format, wf);
        fshp.SaveShape(false);
        fshp.SaveVertexBuffer(false);
        if (wf != null)
        {
            // SaveVertexBuffer packs weights like 8-bit unorm (x255 truncate, clamp to the remaining 255, last = remainder);
            // put the raw signed floats back, in the _i slot order captured right after CreateBoneList (rawSlots).
            var helper = new Syroot.NintenTools.NSW.Bfres.Helpers.VertexBufferHelper(fshp.VertexBuffer, Syroot.BinaryData.ByteOrder.LittleEndian);
            int sc = fshp.VertexSkinCount;
            foreach (var at in helper.Attributes.Where(x => x.Name.StartsWith("_w")))
            {
                int set = int.Parse(at.Name.Substring(2));
                var data = new Syroot.Maths.Vector4F[n];
                for (int i = 0; i < n; i++)
                {
                    var src = rawSlots[i]; var w = new float[4];
                    for (int k = 0; k < 4; k++) { int j = set * 4 + k; w[k] = j < src.Length && j < sc ? src[j] : 0f; }
                    data[i] = new Syroot.Maths.Vector4F(w[0], w[1], w[2], w[3]);
                }
                at.Data = data;
            }
            var vb = helper.ToVertexBuffer();
            vb.VertexSkinCount = fshp.VertexSkinCount;
            fshp.VertexBuffer = vb;
            Console.WriteLine($"{fshp.Text}: raw float weights written ({wf})");
        }
        Console.WriteLine($"replaced {fshp.Text}: verts {n} tris {faces.Count / 3} skin {force} attrs {string.Join(",", fshp.vertexAttributes.Select(x => x.Name + ":" + x.Format))}");
    }
}
