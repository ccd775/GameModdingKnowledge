"""Jolt Physics binary state readers for DS2 PhysicsShapeResource / PhysicsRagdollResource extra data
(port of Odradek's game.ds2.middleware.jolt). Results are plain dicts; values are kept only where cheap."""

SHAPE_SUBTYPES = ['Sphere', 'Box', 'Triangle', 'Capsule', 'TaperedCapsule', 'Cylinder', 'ConvexHull', 'StaticCompound',
                  'MutableCompound', 'RotatedTranslated', 'Scaled', 'OffsetCenterOfMass', 'Mesh', 'HeightField']

TYPE_NAMES = [
    'SkeletalAnimation', 'Skeleton', 'CompoundShapeSettings', 'StaticCompoundShapeSettings',
    'MutableCompoundShapeSettings', 'TriangleShapeSettings', 'SphereShapeSettings', 'BoxShapeSettings',
    'CapsuleShapeSettings', 'TaperedCapsuleShapeSettings', 'CylinderShapeSettings', 'ScaledShapeSettings',
    'MeshShapeSettings', 'ConvexHullShapeSettings', 'HeightFieldShapeSettings', 'RotatedTranslatedShapeSettings',
    'OffsetCenterOfMassShapeSettings', 'RagdollSettings', 'PointConstraintSettings', 'SixDOFConstraintSettings',
    'SliderConstraintSettings', 'SwingTwistConstraintSettings', 'DistanceConstraintSettings',
    'HingeConstraintSettings', 'FixedConstraintSettings', 'ConeConstraintSettings', 'PathConstraintSettings',
    'VehicleConstraintSettings', 'WheeledVehicleControllerSettings', 'PathConstraintPath',
    'PathConstraintPathHermite', 'MotorSettings', 'PhysicsScene', 'PhysicsMaterial', 'PhysicsMaterialSimple',
    'GroupFilter', 'GroupFilterTable',
]


def _type_hash(name):
    h = 0xCBF29CE484222325
    for b in name.encode():
        h = ((h ^ b) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    v = (h ^ (h >> 32)) & 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


HASH_TO_NAME = {_type_hash(n): n for n in TYPE_NAMES}


def _type_name(r):
    h = r.i32()
    if h not in HASH_TO_NAME:
        raise ValueError('unknown Jolt type hash %#010x' % (h & 0xFFFFFFFF))
    return HASH_TO_NAME[h]


def vec3(r):
    return (r.f32(), r.f32(), r.f32())


def vec4(r):
    return (r.f32(), r.f32(), r.f32(), r.f32())


def _count(r):
    return r.i64()


def _bytes(r):
    return r.bytes(_count(r))


# ---------------------------------------------------------------- shapes

def _convex(r, s):
    s['density'] = r.f32()


def _shape_state(r):
    sub = SHAPE_SUBTYPES[r.u8()]
    s = {'type': sub, 'user_data': r.i64()}
    if sub in ('Sphere', 'Box', 'Capsule', 'TaperedCapsule', 'Cylinder', 'ConvexHull'):
        _convex(r, s)
    if sub == 'Sphere':
        s['radius'] = r.f32()
    elif sub == 'Box':
        s['half_extent'] = vec3(r)
        s['convex_radius'] = r.f32()
    elif sub == 'Capsule':
        s['radius'] = r.f32()
        s['half_height'] = r.f32()
    elif sub == 'TaperedCapsule':
        s['center_of_mass'] = vec3(r)
        s['top_radius'], s['bottom_radius'], s['top_center'], s['bottom_center'] = r.f32(), r.f32(), r.f32(), r.f32()
        s['convex_radius'], s['sin_alpha'], s['tan_alpha'] = r.f32(), r.f32(), r.f32()
    elif sub == 'Cylinder':
        s['half_height'], s['radius'], s['convex_radius'] = r.f32(), r.f32(), r.f32()
    elif sub == 'ConvexHull':
        s['center_of_mass'] = vec3(r)
        s['inertia'] = [vec4(r) for _ in range(4)]
        s['bounds'] = (vec3(r), vec3(r))
        pts = []
        for _ in range(_count(r)):
            p = vec4(r)              # aligned Vec3 (w == z)
            n = r.i32()
            faces = [r.i32() for _ in range(3)][:n]
            pts.append((p[:3], faces))
        s['points'] = pts
        s['faces'] = [(r.i16(), r.i16()) for _ in range(_count(r))]
        s['planes'] = [(vec3(r), r.f32()) for _ in range(_count(r))]
        s['vertex_idx'] = _bytes(r)
        s['convex_radius'], s['volume'], s['inner_radius'] = r.f32(), r.f32(), r.f32()
    elif sub == 'Mesh':
        s['tree'] = _bytes(r)
    elif sub == 'HeightField':
        s['offset'], s['scale'] = vec3(r), vec3(r)
        s['sample_count'], s['block_size'] = r.i32(), r.i32()
        s['bits_per_sample'] = r.u8()
        s['min_sample'], s['max_sample'] = r.i16(), r.i16()
        s['range_blocks'] = [r.bytes(16) for _ in range(_count(r))]
        s['height_samples'] = _bytes(r)
        s['active_edges'] = _bytes(r)
        s['material_indices'] = _bytes(r)
        s['bits_per_material_index'] = r.i32()
    elif sub == 'StaticCompound':
        s['center_of_mass'] = vec3(r)
        s['bounds'] = (vec3(r), vec3(r))
        s['inner_radius'] = r.f32()
        s['sub_shapes'] = [dict(user_data=r.i32(), position=vec3(r), rotation=vec3(r)) for _ in range(_count(r))]
        s['nodes'] = [r.bytes(64) for _ in range(_count(r))]
    elif sub in ('RotatedTranslated', 'Scaled', 'OffsetCenterOfMass'):
        if sub == 'RotatedTranslated':
            s['center_of_mass'] = vec3(r)
            s['rotation'] = vec4(r)
        elif sub == 'Scaled':
            s['scale'] = vec3(r)
        else:
            s['offset'] = vec3(r)
    else:
        raise NotImplementedError('Jolt shape subtype %s' % sub)
    return s


def _shape_with_children(r, shape_map):
    """DS2 PhysicsShapeResource layout (Odradek PhysicsShapeResourceCallback): id 0 is the null shape, new ids are
    appended; each new shape is followed by its children and material ids (-1 = none)."""
    shape_id = r.i32()
    if shape_id < len(shape_map):
        return shape_map[shape_id]
    s = _shape_state(r)
    while len(shape_map) < shape_id:
        shape_map.append(None)
    shape_map.append(s)
    s['children'] = [_shape_with_children(r, shape_map) for _ in range(r.i32())]
    s['materials'] = [r.i32() for _ in range(r.i32())]
    return s


def read_physics_shape(r):
    return _shape_with_children(r, [None])


# ---------------------------------------------------------------- ragdolls

def _ref_shape(r, shape_map):
    """Jolt StreamUtils object reference: -1 = null, ids below the map size are earlier shapes."""
    shape_id = r.i32()
    if shape_id == -1:
        return None
    if shape_id < len(shape_map):
        return shape_map[shape_id]
    s = _shape_state(r)
    shape_map.append(s)
    s['children'] = [_ref_shape(r, shape_map) for _ in range(r.i32())]
    s['materials'] = [r.i32() for _ in range(r.i32())]
    return s


def _constraint(r):
    name = _type_name(r)
    c = {'type': name, 'enabled': bool(r.u8()), 'draw_size': r.f32(), 'priority': r.i32(),
         'velocity_steps': r.i32(), 'position_steps': r.i32()}
    motor = lambda: tuple(r.f32() for _ in range(6))
    if name == 'PointConstraintSettings':
        c['common_point'] = vec3(r)
    elif name == 'HingeConstraintSettings':
        c.update(point1=vec3(r), hinge_axis1=vec3(r), normal_axis1=vec3(r),
                 point2=vec3(r), hinge_axis2=vec3(r), normal_axis2=vec3(r))
        c['limits'] = (r.f32(), r.f32())
        c['max_friction_force'] = r.f32()
        c['motor'] = motor()
    elif name == 'SliderConstraintSettings':
        c['slider_axis'] = vec3(r)
        c['limits'] = (r.f32(), r.f32())
        c['max_friction_force'] = r.f32()
        c['motor'] = motor()
    elif name == 'SwingTwistConstraintSettings':
        c.update(position1=vec3(r), twist_axis1=vec3(r), plane_axis1=vec3(r),
                 position2=vec3(r), twist_axis2=vec3(r), plane_axis2=vec3(r))
        c['normal_half_cone'], c['plane_half_cone'] = r.f32(), r.f32()
        c['twist_limits'] = (r.f32(), r.f32())
        c['max_friction_torque'] = r.f32()
        c['swing_motor'], c['twist_motor'] = motor(), motor()
    else:
        raise NotImplementedError('Jolt constraint %s' % name)
    return c


def _body(r, shape_map, filter_map):
    b = dict(position=vec3(r), rotation=vec4(r), linear_velocity=vec3(r), angular_velocity=vec3(r),
             group=(r.i32(), r.i32()), object_layer=r.i16(), motion_type=r.u8(), allow_dynamic_or_kinematic=r.u8(),
             motion_quality=r.u8(), allow_sleeping=r.u8(), friction=r.f32(), restitution=r.f32(),
             linear_damping=r.f32(), angular_damping=r.f32(), max_linear_velocity=r.f32(),
             max_angular_velocity=r.f32(), gravity_factor=r.f32(), override_mass=r.u8(), inertia_multiplier=r.f32(),
             mass=r.f32(), inertia=[vec4(r) for _ in range(4)])
    b['shape'] = _ref_shape(r, shape_map)
    fid = r.i32()
    if fid != -1:
        if fid >= len(filter_map):
            name = _type_name(r)
            if name != 'GroupFilterTable':
                raise NotImplementedError('Jolt group filter %s' % name)
            filter_map.append(dict(num_sub_groups=r.i32(), table=_bytes(r)))
        b['group_filter'] = fid
    return b


def read_ragdoll(r):
    joints = []
    for _ in range(r.i32()):
        name = r.bytes(_count(r)).decode('utf-8', 'replace')
        parent = r.i32()
        parent_name = r.bytes(_count(r)).decode('utf-8', 'replace')
        joints.append((name, parent, parent_name))
    shape_map, filter_map, parts = [], [], []
    for _ in range(r.i32()):
        body = _body(r, shape_map, filter_map)
        constraint = _constraint(r) if r.u8() else None
        parts.append(dict(body=body, constraint=constraint))
    return dict(joints=joints, parts=parts, group_filters=filter_map)
