"""W3 mimic pose (track) -> Karin shape keys.

Each entry: pose name -> list of (shape key, weight, side) where side is 'L', 'R' or None.
Side splits a symmetric key to one half of the face (character's left = +x in Karin's source space, -x in W3).
W3 track names use the character's own left/right. Keys already split in Karin (blink_L, mayu_up_R, ...) keep
side None. Missing poses stay at the rest pose.
"""

POSE_MAP = {
    'jaw_open_a': [('kuchi_A', 1.0, None)],
    'jaw_open_o': [('kuchi_O', 1.0, None)],
    'jaw_chew': [('kuchi_A', 0.35, None)],
    'corner_right_tight': [('kuchi_narrow', 0.6, 'R')],
    'corner_left_tight': [('kuchi_narrow', 0.6, 'L')],
    'corner_right_spread': [('kuchi_wide', 1.0, 'R')],
    'corner_left_spread': [('kuchi_wide', 1.0, 'L')],
    'corner_right_out': [('kuchi_wide', 0.6, 'R')],
    'corner_left_out': [('kuchi_wide', 0.6, 'L')],
    'corner_right_in': [('kuchi_narrow', 1.0, 'R')],
    'corner_left_in': [('kuchi_narrow', 1.0, 'L')],
    'corner_right_up': [('kuchi_smile_1_R', 1.0, None)],
    'corner_left_up': [('kuchi_smile_1_L', 1.0, None)],
    'corner_right_down': [('kuchi_angry_1_R', 1.0, None)],
    'corner_left_down': [('kuchi_angry_1_L', 1.0, None)],
    'lips_in': [('kuchi_U', 0.4, None)],
    'lips_out': [('kuchi_U', 1.0, None)],
    'lips_blow': [('kuchi_U', 0.7, None)],
    'lip_upper_center_up': [('kuchi_up', 0.6, None)],
    'lip_upper_right_up': [('kuchi_up', 0.6, 'R')],
    'lip_upper_left_up': [('kuchi_up', 0.6, 'L')],
    'lip_lower_center_down': [('kuchi_down', 0.6, None)],
    'lip_lower_right_down': [('kuchi_down', 0.6, 'R')],
    'lip_lower_left_down': [('kuchi_down', 0.6, 'L')],
    'cheek_right_up': [('smile', 0.25, 'R')],
    'cheek_left_up': [('smile', 0.25, 'L')],
    'brow_right_up': [('mayu_up_R', 1.0, None)],
    'brow_left_up': [('mayu_up_L', 1.0, None)],
    'brow_right_down': [('mayu_down_R', 1.0, None)],
    'brow_left_down': [('mayu_down_L', 1.0, None)],
    'brow_right_in': [('mayu_angry_1_R', 0.8, None)],
    'brow_left_in': [('mayu_angry_1_L', 0.8, None)],
    'brow_inner_right_up': [('mayu_sad_1_R', 1.0, None)],
    'brow_inner_left_up': [('mayu_sad_1_L', 1.0, None)],
    'brow_middle_right_up': [('mayu_up_R', 0.5, None)],
    'brow_middle_left_up': [('mayu_up_L', 0.5, None)],
    'brow_outer_right_up': [('mayu_up_R', 0.4, None)],
    'brow_outer_left_up': [('mayu_up_L', 0.4, None)],
    # eye direction: W3 'eye_<which eye>_<direction>' in the character's frame
    'eye_right_right': [('LookRight', 1.0, 'R')],
    'eye_left_right': [('LookRight', 1.0, 'L')],
    'eye_right_left': [('LookLeft', 1.0, 'R')],
    'eye_left_left': [('LookLeft', 1.0, 'L')],
    'eye_right_up': [('LookUp', 1.0, 'R')],
    'eye_left_up': [('LookUp', 1.0, 'L')],
    'eye_right_down': [('LookDown', 1.0, 'R')],
    'eye_left_down': [('LookDown', 1.0, 'L')],
    'iris_wide': [('hitomi_big', 1.0, None)],
    'iris_narrow': [('hitomi_small', 0.6, None)],
    'eyelids_upper_right_down': [('blink_R', 1.0, None)],
    'eyelids_upper_left_down': [('blink_L', 1.0, None)],
    'eyelids_upper_right_up': [('surprise_R', 1.0, None)],
    'eyelids_upper_left_up': [('surprise_L', 1.0, None)],
    'eyelids_lower_right_up': [('LowerEyelid_up_R', 1.0, None)],
    'eyelids_lower_left_up': [('LowerEyelid_up_L', 1.0, None)],
    'eyelids_lower_right_down': [('LowerEyelid_down_R', 1.0, None)],
    'eyelids_lower_left_down': [('LowerEyelid_down_L', 1.0, None)],
    'eyelid_upper_inner_left_down': [('blink_L', 0.3, None)],
    'eyelid_upper_inner_right_down': [('blink_R', 0.3, None)],
    'eyelid_upper_center_left_down': [('blink_L', 0.35, None)],
    'eyelid_upper_center_right_down': [('blink_R', 0.35, None)],
    'eyelid_upper_outer_left_down': [('blink_L', 0.3, None)],
    'eyelid_upper_outer_right_down': [('blink_R', 0.3, None)],
    'eyelid_lower_center_left_up': [('LowerEyelid_up_L', 0.5, None)],
    'eyelid_lower_center_right_up': [('LowerEyelid_up_R', 0.5, None)],
    'tongue_front': [('bero_be-', 0.5, None)],
}


# Post-solve amplitude per pose (make_w3fac.py): W3 lip-sync drives the jaw at partial weights, so Karin's mouth
# opened too little in v0.1.0.
POSE_GAIN = {
    'jaw_open_a': 1.3, 'jaw_open_o': 1.3, 'jaw_chew': 1.3,
    'lip_upper_center_up': 1.2, 'lip_upper_right_up': 1.2, 'lip_upper_left_up': 1.2,
    'lip_lower_center_down': 1.2, 'lip_lower_right_down': 1.2, 'lip_lower_left_down': 1.2,
}


def needed_keys():
    out = set()
    for lst in POSE_MAP.values():
        for k, _w, _s in lst:
            out.add(k)
    return sorted(out)
