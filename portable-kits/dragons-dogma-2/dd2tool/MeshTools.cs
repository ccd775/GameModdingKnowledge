using System.Text.Json;
using System.Text.Json.Nodes;
using ReeLib;
using ReeLib.Mesh;
using ReeLib.via;

namespace DD2Tool;

internal static class MeshTools
{
    public static MeshFile Load(string path)
    {
        var fh = new FileHandler(path);
        var mesh = new MeshFile(fh);
        if (!mesh.Read()) throw new Exception("mesh read failed: " + path);
        return mesh;
    }

    static JsonArray Mat(mat4 m) => new JsonArray(m.m00, m.m01, m.m02, m.m03, m.m10, m.m11, m.m12, m.m13, m.m20, m.m21, m.m22, m.m23, m.m30, m.m31, m.m32, m.m33);

    public static int MeshInfo(string path, string outJson)
    {
        using var mesh = Load(path);
        var root = new JsonObject {
            ["path"] = path,
            ["fileVersion"] = mesh.FileHandler.FileVersion,
            ["internalVersion"] = mesh.Header.version,
            ["versionConfig"] = mesh.CurrentVersionConfig,
            
            ["flags"] = mesh.Header.flags.ToString(),
            ["bufferCount"] = mesh.Header.BufferCount,
            ["streamingBuffers"] = mesh.StreamingBuffers?.Count ?? 0,
            ["totalVerts"] = mesh.TotalVertexCount,
            ["totalTris"] = mesh.TotalTriangleCount,
            ["hasShadow"] = mesh.ShadowMesh != null,
            ["hasOccluder"] = mesh.OccluderMesh != null,
            ["hasBlendShapes"] = mesh.BlendShapes != null,
            ["hasNormalRecalc"] = mesh.NormalRecalcData != null,
            ["hashCount"] = mesh.Hashes?.Count ?? 0,
        };
        var mats = new JsonArray();
        foreach (var m in mesh.MaterialNames) mats.Add(m);
        root["materials"] = mats;
        var lods = new JsonArray();
        if (mesh.MeshData != null) {
            foreach (var lod in mesh.MeshData.LODs) {
                var groups = new JsonArray();
                foreach (var g in lod.MeshGroups) {
                    var subs = new JsonArray();
                    foreach (var sm in g.Submeshes) {
                        subs.Add(new JsonObject {
                            ["material"] = sm.materialIndex < mesh.MaterialNames.Count ? mesh.MaterialNames[sm.materialIndex] : sm.materialIndex.ToString(),
                            ["buffer"] = sm.bufferIndex, ["verts"] = sm.vertCount, ["indices"] = sm.indicesCount,
                        });
                    }
                    groups.Add(new JsonObject { ["groupId"] = g.groupId, ["verts"] = g.vertexCount, ["indices"] = g.indicesCount, ["submeshes"] = subs });
                }
                lods.Add(new JsonObject { ["groups"] = groups });
            }
        }
        root["lods"] = lods;
        if (mesh.MeshBuffer != null) {
            var b = mesh.MeshBuffer;
            root["buffer"] = new JsonObject {
                ["positions"] = b.Positions?.Length ?? 0,
                ["uv1"] = b.UV1?.Length ?? 0,
                ["uv2"] = b.UV2?.Length ?? 0,
                ["colors"] = b.Colors?.Length ?? 0,
                ["weights"] = b.Weights?.Length ?? 0,
                ["extraWeights"] = b.ExtraWeights?.Length ?? 0,
                ["shapeKeyWeights"] = b.ShapeKeyWeights?.Length ?? 0,
            };
        }
        if (mesh.BlendShapes != null) {
            var shapes = new JsonArray();
            foreach (var sh in mesh.BlendShapes.Shapes) {
                shapes.Add(new JsonObject { ["targets"] = sh.Targets.Count, ["blank"] = sh.BlankTargets.Count, ["flag"] = sh.flag, ["shapeVerts"] = sh.totalShapeVertexCount });
            }
            root["blendShapes"] = shapes;
        }
        var bones = new JsonArray();
        if (mesh.BoneData != null) {
            foreach (var bn in mesh.BoneData.Bones) {
                bones.Add(new JsonObject {
                    ["i"] = bn.index, ["name"] = bn.name, ["parent"] = bn.parentIndex >= 0 && bn.parentIndex < mesh.BoneData.Bones.Count ? mesh.BoneData.Bones[bn.parentIndex].name : null,
                    ["sym"] = bn.symmetryIndex, ["secondary"] = bn.useSecondaryWeight, ["remap"] = bn.remapIndex,
                    ["local"] = Mat(bn.localTransform), ["global"] = Mat(bn.globalTransform),
                });
            }
        }
        root["boneCount"] = mesh.BoneData?.Bones.Count ?? 0;
        root["deformBoneCount"] = mesh.BoneData?.DeformBones.Count ?? 0;
        root["bones"] = bones;
        File.WriteAllText(outJson, root.ToJsonString(new JsonSerializerOptions { WriteIndented = true, TypeInfoResolver = new System.Text.Json.Serialization.Metadata.DefaultJsonTypeInfoResolver() }));
        Console.WriteLine($"{Path.GetFileName(path)}: cfg={mesh.CurrentVersionConfig} verts={mesh.TotalVertexCount} tris={mesh.TotalTriangleCount} bones={mesh.BoneData?.Bones.Count} deform={mesh.BoneData?.DeformBones.Count} mats={mesh.MaterialNames.Count} lods={mesh.MeshData?.LODs.Count} blend={(mesh.BlendShapes != null)} streaming={mesh.StreamingBuffers?.Count ?? 0}");
        return 0;
    }

    public static int MeshConv(string input, string output, string config)
    {
        using var mesh = Load(input);
        var from = mesh.CurrentVersionConfig;
        mesh.ChangeVersion(config);
        var outFh = new FileHandler(new MemoryStream(), output) { FileVersion = mesh.FileHandler.FileVersion };
        mesh.FileHandler = outFh;
        if (!mesh.Write()) throw new Exception("mesh write failed");
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output))!);
        File.WriteAllBytes(output, ((MemoryStream)outFh.Stream).ToArray());
        Console.WriteLine($"converted {from} -> {config}: {output}");
        return 0;
    }
}

internal static class MeshDiag
{
    static void Dump(object? o, string prefix, System.Text.StringBuilder sb, int depth = 0)
    {
        if (o == null) { sb.AppendLine($"{prefix} = null"); return; }
        var t = o.GetType();
        foreach (var f in t.GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)) {
            var v = f.GetValue(o);
            if (v is System.Array a) { sb.AppendLine($"{prefix}.{f.Name} = array[{a.Length}] {f.FieldType.GetElementType()?.Name}"); continue; }
            if (v is System.Collections.ICollection c) { sb.AppendLine($"{prefix}.{f.Name} = coll[{c.Count}]"); continue; }
            if (v == null || f.FieldType.IsPrimitive || f.FieldType.IsEnum || v is string) { sb.AppendLine($"{prefix}.{f.Name} = {v}"); continue; }
            if (depth < 2 && f.FieldType.IsClass) Dump(v, prefix + "." + f.Name, sb, depth + 1);
            else sb.AppendLine($"{prefix}.{f.Name} = {v}");
        }
    }

    public static int Run(string path, string outTxt)
    {
        using var mesh = new ReeLib.MeshFile(new ReeLib.FileHandler(path));
        mesh.Read();
        var sb = new System.Text.StringBuilder();
        Dump(mesh.Header, "Header", sb);
        Dump(mesh.MeshBuffer, "MeshBuffer", sb);
        if (mesh.MeshBuffer != null) {
            int i = 0;
            foreach (var h in mesh.MeshBuffer.Headers.BufferHeaders) Dump(h, $"Elem[{i++}]", sb);
            i = 0;
            foreach (var ab in mesh.MeshBuffer.AdditionalBuffers) {
                int j = 0;
                foreach (var h in ab.Headers.BufferHeaders) Dump(h, $"Add[{i}].Elem[{j++}]", sb);
                i++;
            }
        }
        if (mesh.MeshData != null) {
            Dump(mesh.MeshData, "MeshData", sb);
            int li = 0;
            foreach (var lod in mesh.MeshData.LODs) {
                Dump(lod, $"LOD[{li}]", sb);
                int gi = 0;
                foreach (var g in lod.MeshGroups) {
                    Dump(g, $"LOD[{li}].G[{gi}]", sb);
                    int si = 0;
                    foreach (var s in g.Submeshes) Dump(s, $"LOD[{li}].G[{gi}].S[{si++}]", sb);
                    gi++;
                }
                li++;
            }
        }
        Dump(mesh.ShadowMesh, "Shadow", sb);
        Dump(mesh.BoneData, "BoneData", sb);
        File.WriteAllText(outTxt, sb.ToString());
        Console.WriteLine($"meshdiag -> {outTxt}");
        return 0;
    }
}

internal static class MeshReorder
{
    // Reorder bones so every bone that exists in the reference mesh gets the reference's index (engine systems cache joint
    // indices of the native skeleton); remaining bones keep their relative order after them. Weights reference the deform
    // (remap) list, whose order is unchanged.
    public static int Run(string meshPath, string refPath, string outPath)
    {
        using var mesh = new ReeLib.MeshFile(new ReeLib.FileHandler(meshPath));
        if (!mesh.Read()) throw new Exception("read failed " + meshPath);
        using var refm = new ReeLib.MeshFile(new ReeLib.FileHandler(refPath));
        if (!refm.Read()) throw new Exception("read failed " + refPath);
        var bd = mesh.BoneData ?? throw new Exception("no bones");
        var refNames = refm.BoneData!.Bones.Select(b => b.name).ToList();
        var byName = bd.Bones.ToDictionary(b => b.name);
        foreach (var n in refNames) if (!byName.ContainsKey(n)) throw new Exception("reference bone missing in mesh: " + n);
        var order = refNames.Select(n => byName[n]).ToList();
        var refSet = new HashSet<string>(refNames);
        order.AddRange(bd.Bones.Where(b => !refSet.Contains(b.name)));
        var oldToNew = new Dictionary<int, int>();
        for (int i = 0; i < order.Count; i++) oldToNew[order[i].index] = i;
        foreach (var b in order) {
            var oldIdx = b.index;
            b.index = oldToNew[oldIdx];
            b.parentIndex = b.parentIndex < 0 ? -1 : oldToNew[b.parentIndex];
            b.symmetryIndex = b.symmetryIndex < 0 ? -1 : oldToNew[b.symmetryIndex];
        }
        // parents must precede children
        foreach (var b in order) if (b.parentIndex >= b.index) throw new Exception($"parent after child: {b.name}");
        // rebuild child / sibling links from the new order
        foreach (var b in order) { b.childIndex = -1; b.nextSibling = -1; }
        var kids = order.GroupBy(b => b.parentIndex).ToDictionary(g => g.Key, g => g.OrderBy(x => x.index).ToList());
        foreach (var (p, list) in kids) {
            if (p >= 0) order[p].childIndex = list[0].index;
            for (int i = 0; i + 1 < list.Count; i++) list[i].nextSibling = list[i + 1].index;
        }
        bd.Bones.Clear();
        bd.Bones.AddRange(order);
        var ms = new MemoryStream();
        var fh = new ReeLib.FileHandler(ms, outPath) { FileVersion = mesh.FileHandler.FileVersion };
        mesh.FileHandler = fh;
        if (!mesh.Write()) throw new Exception("write failed");
        File.WriteAllBytes(outPath, ms.ToArray());
        using var chk = new ReeLib.MeshFile(new ReeLib.FileHandler(outPath));
        if (!chk.Read()) throw new Exception("readback failed");
        int same = 0;
        for (int i = 0; i < refNames.Count; i++) if (chk.BoneData!.Bones[i].name == refNames[i]) same++;
        Console.WriteLine($"meshreorder -> {outPath}: bones={chk.BoneData!.Bones.Count} reference-order match {same}/{refNames.Count}");
        return 0;
    }
}
