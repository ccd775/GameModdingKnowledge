import json, numpy as np
def qmat(q):
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
def glob(bones):
    G=[]
    for b in bones:
        M=np.eye(4); M[:3,:3]=qmat(b['r'])*np.array(b['s']); M[:3,3]=b['t']
        G.append(M if b['parent']<0 else G[b['parent']]@M)
    return G
def load(fn):
    d=json.load(open(fn)); B=d['bones']; G=glob(B); idx={b['name']:i for i,b in enumerate(B)}
    return d,B,G,idx
