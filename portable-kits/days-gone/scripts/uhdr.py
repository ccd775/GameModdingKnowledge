import struct,sys,argparse
def rs(f):
    n=struct.unpack('<i',f.read(4))[0]
    if n<0: return f.read(-n*2).decode('utf-16le').rstrip('\0')
    return f.read(n).decode('latin1').rstrip('\0')
ap=argparse.ArgumentParser(description='Print the summary, custom versions and name table of a UE4 package (.uasset).')
ap.add_argument('package'); ap.add_argument('all',nargs='*',help='any extra argument: print every name (default: the first 400)')
args=ap.parse_args()
p=args.package; showall=len(args.all)>0
f=open(p,'rb')
tag,leg=struct.unpack('<Ii',f.read(8))
ue3=struct.unpack('<i',f.read(4))[0] if leg!=-4 else None
fv,lic=struct.unpack('<ii',f.read(8))
cvc=struct.unpack('<i',f.read(4))[0]
cvs=[]
for i in range(cvc):
    if leg<=-3 and leg>-6:
        # enum-based? for -3..-5 FGuid custom
        g=f.read(16); v=struct.unpack('<i',f.read(4))[0]; nm=rs(f) if leg==-4 or leg==-5 else ''
        cvs.append((g.hex(),v,nm))
    else:
        g=f.read(16); v=struct.unpack('<i',f.read(4))[0]; cvs.append((g.hex(),v))
ths=struct.unpack('<i',f.read(4))[0]; folder=rs(f); flags=struct.unpack('<I',f.read(4))[0]
nc,no=struct.unpack('<ii',f.read(8))
gc,go=struct.unpack('<ii',f.read(8))
ec,eo,ic,io=struct.unpack('<iiii',f.read(16))
print(f'tag {tag:x} legacy {leg} ue3 {ue3} fileVer {fv} licensee {lic} customVers {cvc} hdr {ths} flags {flags:x} names {nc}@{no} exports {ec}@{eo} imports {ic}@{io}')
for c in cvs: print('  cv',c)
f.seek(no)
names=[]
for i in range(nc):
    s=rs(f); h=f.read(4) if fv>=504 else b''
    names.append(s)
print('names:',len(names))
if showall: print('\n'.join(names))
else: print(names[:400])
