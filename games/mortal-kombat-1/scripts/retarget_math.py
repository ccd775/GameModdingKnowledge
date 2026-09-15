"""Pure geometry helpers. All input points must share one coordinate frame/unit.

No Blender/game imports, hidden constants, bone names, or file writes. These
functions support a retargeter; they do not make an arbitrary avatar game-ready.
"""
import math


def _point(value):
    if len(value) != 3 or not all(math.isfinite(x) for x in value):
        raise ValueError('Three finite coordinates required')
    return tuple(value)


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _unit(v):
    n = math.sqrt(_dot(v, v))
    if not math.isfinite(n) or n < 1e-10:
        raise ValueError('A finite, nonzero bone segment is required')
    return tuple(x/n for x in v), n


def _rotation(a, b):
    c = max(-1.0, min(1.0, _dot(a, b)))
    if c < -1.0+1e-9:
        basis = tuple(1.0 if j == min(range(3), key=lambda i: abs(a[i])) else 0.0 for j in range(3))
        axis, _ = _unit(_cross(a, basis))
        return [[2*axis[i]*axis[j]-(i == j) for j in range(3)] for i in range(3)]
    v = _cross(a, b)
    k = [[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]
    return [[float(i == j)+k[i][j]+sum(k[i][q]*k[q][j] for q in range(3))/(1+c)
             for j in range(3)] for i in range(3)]


def _affine(linear, source_anchor, target_anchor):
    return [list(row)+[target_anchor[i]-_dot(row, source_anchor)] for i, row in enumerate(linear)]+[[0, 0, 0, 1]]


def fit_segment(source_start, source_end, target_start, target_end, transverse_scale):
    """Fit axial joint spacing while preserving an explicitly chosen body width.

    M = T(target_start) R [s_perp I + (s_axis-s_perp) uu^T] T(-source_start).
    Supply the SAME transverse policy to skin and overlapping clothing.
    """
    source_start,source_end,target_start,target_end = map(_point,(source_start,source_end,target_start,target_end))
    if not math.isfinite(transverse_scale) or transverse_scale <= 0:
        raise ValueError('Positive explicit transverse scale required')
    u, slen = _unit(_sub(source_end, source_start))
    v, tlen = _unit(_sub(target_end, target_start))
    axial = tlen/slen
    stretch = [[transverse_scale*(i == j)+(axial-transverse_scale)*u[i]*u[j] for j in range(3)] for i in range(3)]
    rotation = _rotation(u, v)
    linear = [[sum(rotation[i][k]*stretch[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return _affine(linear, source_start, target_start)


def fit_terminal(source_anchor, target_anchor, scale):
    """Head/terminal similarity with REQUIRED scale; there is no identity fallback."""
    source_anchor,target_anchor=map(_point,(source_anchor,target_anchor))
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Positive explicit terminal scale required')
    return _affine([[scale*(i == j) for j in range(3)] for i in range(3)], source_anchor, target_anchor)


def transform(matrix, point):
    return tuple(_dot(row[:3], point)+row[3] for row in matrix[:3])


def smooth01(t):
    t = max(0.0, min(1.0, t))
    return t*t*(3-2*t)


def pelvis_weight(height, bounds, eligible_mass=1.0):
    """C1 blend: lower start/full, upper full/end in SOURCE height coordinates."""
    low, full, upper, end = bounds
    if not all(math.isfinite(x) for x in (height,low,full,upper,end,eligible_mass)):
        raise ValueError('Finite height, bounds and mass required')
    if not low < full <= upper < end or not 0 <= eligible_mass <= 1:
        raise ValueError('Ordered blend bounds and normalized eligible mass required')
    return smooth01((height-low)/(full-low))*(1-smooth01((height-upper)/(end-upper)))*eligible_mass


def pelvis_point(point, source_mid, target_mid, source_half_width, target_half_width,
                 vertical_scale, transverse_scale):
    """Shared core field, X across hips and Z up. Do NOT anchor it to Hips alone.

    Call identically for skin, shorts, belt and upper thigh vertices. Outside
    the core, blend by pelvis_weight against the usual joint-fitted position.
    """
    point,source_mid,target_mid=map(_point,(point,source_mid,target_mid))
    values=(source_half_width, target_half_width, vertical_scale, transverse_scale)
    if not all(math.isfinite(x) and x > 0 for x in values):
        raise ValueError('Finite positive hip widths/scales required')
    spread = target_half_width-transverse_scale*source_half_width
    # smooth01'(t) peaks at 1.5. Reject a narrowing that folds the core field.
    if min(transverse_scale, transverse_scale+1.5*spread/source_half_width) <= 0:
        raise ValueError('Hip-width fit would fold the pelvis; revise the mapping')
    delta = _sub(point, source_mid)
    lateral = spread*smooth01(abs(delta[0])/source_half_width)*(1 if delta[0] >= 0 else -1)
    return (target_mid[0]+delta[0]*transverse_scale+lateral,
            target_mid[1]+delta[1]*transverse_scale,
            target_mid[2]+delta[2]*vertical_scale)


def atlas_pixel_rect(uv_rect, resolution):
    """Lower-left UV (u,v,w,h) -> top-left PNG (x,y,width,height)."""
    u,v,w,h=uv_rect
    if not isinstance(resolution,int) or resolution <= 0 or not all(math.isfinite(x) for x in uv_rect):
        raise ValueError('Finite rectangle and positive integer resolution required')
    if u < 0 or v < 0 or w <= 0 or h <= 0 or u+w > 1 or v+h > 1:
        raise ValueError('UV rectangle must be inside the atlas')
    values=(u*resolution,(1-v-h)*resolution,w*resolution,h*resolution)
    if any(abs(x-round(x)) > 1e-6 for x in values):
        raise ValueError('UV rectangle edges must align with pixel boundaries')
    return tuple(round(x) for x in values)
