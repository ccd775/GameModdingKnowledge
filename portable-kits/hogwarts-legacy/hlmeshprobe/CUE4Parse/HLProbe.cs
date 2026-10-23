namespace CUE4Parse;
public static class HLProbe
{
    public static readonly System.Collections.Generic.List<(long Pos, long AbsPos, uint Next, short Mat, int Tris)> Sections = new();
    public static (long Pos, long Valid) End;
    public static long MatHashPos = -1;
    public static long RefPosePos = -1;
    public static readonly System.Collections.Generic.List<(int Max, int Verts, int Bones)> Infl = new();
}
