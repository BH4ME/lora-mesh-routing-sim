#!/usr/bin/env python3
"""Restore a trusted indexed evidence archive into a new directory, with hashes."""
import argparse,hashlib,json,tarfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--index',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
d=json.loads(a.index.read_text())
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
assert sha(a.archive)==d['sha256'] and a.archive.stat().st_size==d['bytes']
a.out.mkdir(parents=True,exist_ok=False);seen=set()
with tarfile.open(a.archive,'r:gz') as tf:
 for m in tf:
  rel=Path(m.name)
  if not m.isfile() or rel.is_absolute() or '..' in rel.parts or m.name in seen:raise ValueError('Unsafe archive member')
  expected=d['files'][m.name];data=tf.extractfile(m).read()
  assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],m.name
  target=a.out/rel;target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(data)
  seen.add(m.name)
assert seen==set(d['files'])
print(json.dumps({'restored_files':len(seen),'archive_sha256':d['sha256'],'destination':str(a.out.resolve())}))
