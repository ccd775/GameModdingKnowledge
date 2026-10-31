"""RigLogic runtime state reader for DS2 FacialRigSettingWithLODResource extra data (port of Odradek's
game.ds2.middleware.riglogic). The blob is big-endian; arrays are kept as numpy arrays."""
import struct

import numpy as np


class _BE:
    def __init__(self, r):
        self.r = r

    def _unpack(self, fmt, size):
        v = struct.unpack_from(fmt, self.r.buf, self.r.pos)[0]
        self.r.pos += size
        return v

    def i32(self):
        return self._unpack('>i', 4)

    def i16(self):
        return self._unpack('>h', 2)

    def b(self):
        return self._unpack('>B', 1) != 0

    def arr(self, dtype):
        n = self.i32()
        a = np.frombuffer(self.r.buf, dtype=dtype, count=n, offset=self.r.pos).copy()
        self.r.pos += n * a.itemsize
        return a

    def shorts(self):
        return self.arr('>i2')

    def floats(self):
        return self.arr('>f4')


def _conditional_table(be):
    return dict(intervals_remaining=be.shorts(), input_indices=be.shorts(), output_indices=be.shorts(),
                from_values=be.floats(), to_values=be.floats(), slope_values=be.floats(), cut_values=be.floats(),
                input_count=be.i16(), output_count=be.i16())


def read(r):
    be = _BE(r)
    config = dict(calculation_type=be.i32(), load_joints=be.b(), load_blend_shapes=be.b(),
                  load_animated_maps=be.b(), load_ml_behavior=be.b())
    metrics = dict(zip(('lod_count', 'gui_control_count', 'raw_control_count', 'psd_control_count',
                        'ml_control_count', 'joint_attribute_count', 'blend_shape_count', 'animated_map_count'),
                       (be.i16() for _ in range(8))))
    controls = dict(gui_to_raw=_conditional_table(be),
                    psds=dict(distinct=be.i16(), rows=be.shorts(), cols=be.shorts(), values=be.floats()))
    joints = {}
    if config['load_joints']:
        joints['storage'] = dict(
            values=be.shorts(), input_indices=be.shorts(), output_indices=be.shorts(),
            lod_regions=[(be.i32(), be.i32(), be.i32()) for _ in range(be.i32())],
            joint_groups=[tuple(be.i32() for _ in range(8)) for _ in range(be.i32())])
    joints['neutral_values'] = be.floats()
    joints['variable_attribute_indices'] = [be.shorts() for _ in range(be.i32())]
    joints['joint_group_count'] = be.i16()
    blend_shapes = None
    if config['load_blend_shapes']:
        blend_shapes = dict(lods=be.shorts(), input_indices=be.shorts(), output_indices=be.shorts())
    animated_maps = None
    if config['load_animated_maps']:
        animated_maps = dict(lods=be.shorts(), conditionals=_conditional_table(be))
    return dict(config=config, metrics=metrics, controls=controls, joints=joints, blend_shapes=blend_shapes,
                animated_maps=animated_maps)
