import struct,sys,argparse
def rs(f):
    n=struct.unpack('<i',f.read(4))[0]
    if n<0: return f.read(-n*2).decode('utf-16le').rstrip('\0')
    return f.read(n).decode('latin1').rstrip('\0')
ap=argparse.ArgumentParser(description='List a UE 4.11 pak (version 3): footer, mount point, then size, stored size, compression and path per entry.')
ap.add_argument('pak')
p=ap.parse_args().pak
f=open(p,'rb'); f.seek(0,2); n=f.tell(); f.seek(n-44)
magic,ver,io,isz=struct.unpack('<IIqq',f.read(24))
print('magic',hex(magic),'ver',ver,'idx',io,isz)
f.seek(io); mp=rs(f); cnt=struct.unpack('<i',f.read(4))[0]
print('mount',mp,'count',cnt)
for i in range(cnt):
    name=rs(f)
    off,sz,usz,comp=struct.unpack('<qqqi',f.read(28)); f.read(20)
    blocks=[]
    if ver>=3:
        if comp:
            bc=struct.unpack('<i',f.read(4))[0]; f.read(16*bc)
        enc=f.read(1)[0]; bs=struct.unpack('<I',f.read(4))[0]
    print(f'{usz:>10} {sz:>10} c{comp} {name}')
