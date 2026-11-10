# Offline checks of the skirt weights and the chain physics (build 5)

Python 3 + numpy, scipy, Pillow. The scripts chdir to the build directory `N2_BUILD` (the project's `_build`)
and import `n2_build.py` from the folder above this one. Every command takes `--help`.

- `python rest_check.py`: skirt at rest on synthetic poses (stance, walk, run, sprint, side, back kick, crouch).
  Compares the build-4 rest skinning with the build-3 weight field and counts skin vertices outside the skirt.
- `python anim5.py`: Python port of `sim_a.hlsl` (`simpy.py`) driven by an eased run (70 / 30 deg strides), a stop,
  a 120 deg turn or a sideways dodge. Reports the max swing per chain group and frames with skin outside the skirt.
- `anim.py`, `anim2.py`: the same with a symmetric gait, harsher than any real run cycle.
- `python tailtune.py`: fox tail (chain TA) tip swing on run / stop / turn and depth into the thigh capsules for a
  few tunings. Build 5's tail tuning was picked with an 8 deg hip yaw / 4 deg roll sway added to the run.

Keep `simpy.py` in step with `write_sim_shader` in `../n2_build.py` by hand.
