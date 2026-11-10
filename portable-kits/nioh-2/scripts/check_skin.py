"""Offline check: skin the built host buffers with the fa3 frame's real matrices (merged palette rebuilt in python
exactly like merge_a.hlsl) and overlay on the vanilla character skinned the same way.
usage: check_skin.py [mod dir] [--png out.png]   (fa3/ and build1/build_report.json from N2_BUILD; the mod dir
defaults to <N2_BUILD>/out/KarinN2, the image to <N2_BUILD>/build1/skin_check.png)"""
import argparse, os
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('mod', nargs='?', help='the built mod folder (meshes/ inside)'); ap.add_argument('--png', help='output image')
args = ap.parse_args()
if not os.environ.get('N2_BUILD'):
    raise SystemExit('N2_BUILD is not set: point it at the build directory (fa3/, build1/, ...)')
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.abspath(args.mod) if args.mod else 'out/KarinN2'
PNG = os.path.abspath(args.png) if args.png else 'build1/skin_check.png'
os.chdir(os.environ['N2_BUILD'])
import sys, json, glob, numpy as np
sys.path.insert(0, HERE)
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from fa_mesh import load_draw
from bones import skin_arrays
FA='fa3/FrameAnalysis-2026-11-07-205515'
fa={d['draw']:d for d in json.load(open('fa3/fa3.json'))}
rep=json.load(open('build1/build_report.json'))
def cb(d):
    f=glob.glob(f'{FA}/{d:06d}-vs-cb0=*.buf')[0]; return np.fromfile(f,'<f4').reshape(-1,4).astype(float)
SRC={'greaveL':15,'gauntL':16,'hakama':19,'chest':21,'scarfL':22,'scarfR':24,'greaveR':29,'gauntR':31}
pal=[]
for tok,(src,e) in rep['palette_A'].items():
    c=cb(SRC[src]); pal.append(c[5+3*e:8+3*e])
pal=np.array(pal)
vb=np.fromfile(os.path.join(MOD,'meshes','karinA.vb'),np.uint8).reshape(-1,48)
P=vb[:,0:12].copy().view('<f4').reshape(-1,3).astype(float)
W=vb[:,12:20].copy().view('<f2').reshape(-1,4).astype(float); I=vb[:,20:24].astype(int)//3
W[:,3]=1-W[:,:3].sum(1)
Ph=np.c_[P,np.ones(len(P))]
S=np.zeros_like(P)
for k in range(4): S+=W[:,k:k+1]*np.einsum('nij,nj->ni',pal[I[:,k]],Ph)
# face host
v0=np.fromfile(os.path.join(MOD,'meshes','karinB.vb0'),np.uint8).reshape(-1,24); v1=np.fromfile(os.path.join(MOD,'meshes','karinB.vb1'),np.uint8).reshape(-1,144)
Pf=v0[:,0:12].copy().view('<f4').reshape(-1,3).astype(float)
Wf=v1[:,0:16].copy().view('<f2').reshape(-1,8).astype(float); If=v1[:,16:32].copy().view('<i2').reshape(-1,8).astype(int)//3
Wf[:,7]=1-Wf[:,:7].sum(1)
cf=cb(39); palf=np.array([cf[5+3*e:8+3*e] for e in range(128)])
Sf=np.zeros_like(Pf); Pfh=np.c_[Pf,np.ones(len(Pf))]
for k in range(8): Sf+=Wf[:,k:k+1]*np.einsum('nij,nj->ni',palf[If[:,k]],Pfh)
# vanilla skinned
G=[]
for d in (15,16,19,21,22,24,29,31,39,42,47,43,45,44,46):
    m=load_draw(FA,fa[d]); Pg=m['POSITION0'][:,:3].astype(float); idx,w=skin_arrays(m); c=cb(d)
    n=(len(c)-5)//3; pg=c[5:5+3*n].reshape(n,3,4); used=np.unique(m['tris'])
    Pgh=np.c_[Pg,np.ones(len(Pg))]; s=np.zeros_like(Pg)
    for k in range(idx.shape[1]): s+=w[:,k:k+1]*np.einsum('nij,nj->ni',pg[np.clip(idx[:,k],0,n-1)],Pgh)
    G.append(s[used])
G=np.concatenate(G)
o=G.mean(0)
fig,ax=plt.subplots(1,2,figsize=(14,10))
for a,(i,j) in zip(ax,((0,1),(2,1))):
    a.scatter(G[:,i]-o[i],G[:,j]-o[j],s=0.2,c='gray',alpha=0.3)
    a.scatter(S[:,i]-o[i],S[:,j]-o[j],s=0.2,c='m',alpha=0.3)
    a.scatter(Sf[:,i]-o[i],Sf[:,j]-o[j],s=0.2,c='r',alpha=0.4)
    a.set_aspect('equal'); a.grid(True)
plt.savefig(PNG,dpi=70)
print('karin bbox', np.round(S.min(0)-o,1), np.round(S.max(0)-o,1), 'face bbox', np.round(Sf.min(0)-o,1), np.round(Sf.max(0)-o,1))
print('vanilla bbox', np.round(G.min(0)-o,1), np.round(G.max(0)-o,1))
