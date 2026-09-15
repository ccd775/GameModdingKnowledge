"""Explicit Z-up neck field. No region selection, file IO or default shortening ratio."""
import math


def neck_point(point, *, neck_z, head_z, shift, head_weight, neck_weight):
    """Return an adjusted point in the input unit; caller audits weights and seams.

    The derivative guard applies only to constant-weight pure-Neck geometry,
    not the full Jacobian of an arbitrary spatially varying skin-weight field.
    """
    if len(point) != 3:
        raise ValueError('Expected an XYZ point')
    values = (*point, neck_z, head_z, shift, head_weight, neck_weight)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Finite coordinates, anchors and weights required')
    span = head_z - neck_z
    if span <= 0 or shift < 0 or 1 - 1.5 * shift / span <= 0:
        raise ValueError('Invalid anchors or potentially folding pure-neck field')
    if not (0 <= head_weight <= 1 and 0 <= neck_weight <= 1
            and head_weight + neck_weight <= 1):
        raise ValueError('Provide audited normalized, nonnegative weights')
    if head_weight == neck_weight == 0:
        return tuple(point)
    t = max(0.0, min(1.0, (point[2] - neck_z) / span))
    s = t*t*(3 - 2*t)
    return (point[0], point[1], point[2] - shift*(head_weight + neck_weight*s))
