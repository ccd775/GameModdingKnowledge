import struct,sys,zlib,os,argparse
def rs(f):
    n=struct.unpack('<i',f.read(4))[0]
    if n<0: return f.read(-n*2).decode('utf-16le').rstrip('\0')
    return f.read(n).decode('latin1').rstrip('\0')
ap=argparse.ArgumentParser(description='Extract every entry of a UE 4.11 pak (version 3, zlib or stored) to <out>/<entry path>.')
ap.add_argument('pak'); ap.add_argument('out'); args=ap.parse_args()
p,out=args.pak,args.out
f=open(p,'rb'); f.seek(0,2); n=f.tell(); f.seek(n-44)
magic,ver,io,isz=struct.unpack('<IIqq',f.read(24))
f.seek(io); mp=rs(f); cnt=struct.unpack('<i',f.read(4))[0]
ents=[]
for i in range(cnt):
    name=rs(f)
    off,sz,usz,comp=struct.unpack('<qqqi',f.read(28)); f.read(20)
    blocks=[]
    if comp:
        bc=struct.unpack('<i',f.read(4))[0]
        blocks=[struct.unpack('<qq',f.read(16)) for _ in range(bc)]
    enc=f.read(1)[0]; bs=struct.unpack('<I',f.read(4))[0]
    ents.append((name,off,sz,usz,comp,blocks,enc))
for name,off,sz,usz,comp,blocks,enc in ents:
    dst=os.path.join(out,name); os.makedirs(os.path.dirname(dst),exist_ok=True)
    if comp==0:
        # data after inline entry header
        f.seek(off); 
        data=b''
        if usz:
            # inline header size: 8*3+4+20+5 (+4 if comp blocks) ; v3 uncompressed: 53
            f.seek(off+53); data=f.read(usz)
    else:
        data=b''
        for s,e in blocks:
            f.seek(s); data+=zlib.decompress(f.read(e-s))
    assert len(data)==usz,(name,len(data),usz)
    open(dst,'wb').write(data)
print('ok',len(ents))
