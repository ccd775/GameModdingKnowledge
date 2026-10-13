# Extra workbench views: blender --background <run>/build.blend --python render_views.py -- <run_dir> name:x,y,z:rx,ry,rz:ortho ...
import bpy, sys, os, math
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1:]
RUN = os.path.abspath(argv[0]); OUT = os.path.join(RUN, "preview"); os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 900, 900
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"
for spec in argv[1:]:
    name, loc, rot, ortho = spec.split(":")
    cam.location = Vector([float(x) for x in loc.split(",")])
    cam.rotation_euler = [math.radians(float(x)) for x in rot.split(",")]
    cam.data.ortho_scale = float(ortho)
    sc.render.filepath = os.path.join(OUT, name + ".png"); bpy.ops.render.render(write_still=True)
print("VIEWS_OK")
