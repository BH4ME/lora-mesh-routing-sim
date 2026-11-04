#!/usr/bin/env python3
"""Split a verified archive into <=45MiB Git-compatible parts, retaining whole SHA."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--index',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--out-index',type=Path,required=True);a=p.parse_args()
d=json.loads(a.index.read_text());parts=[];whole=hashlib.sha256();total=0
with a.archive.open('rb') as source:
 while True:
  data=source.read(45*1024*1024)
  if not data:break
  part=Path(str(a.archive)+'.part-'+str(len(parts)+1).zfill(3))
  with part.open('xb') as f:f.write(data)
  part_sha=hashlib.sha256(data).hexdigest()
  assert hashlib.sha256(part.read_bytes()).hexdigest()==part_sha
  parts.append({'name':part.name,'bytes':len(data),'sha256':part_sha});whole.update(data);total+=len(data)
assert whole.hexdigest()==d['sha256'] and total==d['bytes']
d.update(parts=parts,reassembly='Concatenate parts in listed order into archive filename, then verify whole SHA256 and member hashes before restoring.',whole_archive_retained_locally=True)
with a.out_index.open('x') as f:json.dump(d,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({'archive_sha256':d['sha256'],'bytes':total,'parts':parts}))
