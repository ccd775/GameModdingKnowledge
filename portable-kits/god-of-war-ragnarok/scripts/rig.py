import struct
import numpy as np
def parse_rig(b):
    n = struct.unpack_from('<H', b, 0x10)[0]
    parents = [struct.unpack_from('<h', b, 0x1E + 8*i)[0] for i in range(n)]
    mo = (0x18 + n*32 + 15) & ~15
    mo += 0x50
    mats = np.frombuffer(b, dtype='<f4', count=16*n, offset=mo).reshape(n,4,4).copy()
    ibm = np.frombuffer(b, dtype='<f4', count=16*n, offset=mo+64*n).reshape(n,4,4).copy()
    return n, parents, mats, ibm, mo
