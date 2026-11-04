#!/usr/bin/env python3
"""Create and verify an exclusive recoverable plan archive; never runs simulations."""
import argparse,hashlib,json,tarfile,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',required=True);p.add_argument('--name',required=True);p.add_argument('--include',action='append',default=[]);args=p.parse_args()
r=args.root.resolve();plan=json.loads((r/args.plan).read_text());out=r/'artifacts/secon2027'/args.name
archive=Path(str(out)+'.tar.gz');index=Path(str(out)+'.index.json')
if archive.exists() or index.exists():raise FileExistsError(out)
paths=[r/args.plan,r/plan['snapshot_path'],r/plan['registry_path'],r/plan['matrix']['contract_path']]
paths.extend(r/'results/secon2027/runs'/run['run_key'] for run in plan['runs'])
paths.extend(r/rel for rel in args.include)
files=sorted({f for path in paths for f in ([path] if path.is_file() else path.rglob('*')) if f.is_file() and '__pycache__' not in f.parts and '.pytest_cache' not in f.parts})
def sha(f):
 h=hashlib.sha256()
 with f.open('rb') as s:
  for b in iter(lambda:s.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
expected={f.relative_to(r).as_posix():{'sha256':sha(f),'bytes':f.stat().st_size} for f in files}
out.parent.mkdir(parents=True,exist_ok=True)
with tarfile.open(archive,'x:gz',compresslevel=6) as tf:
 for f in files:tf.add(f,arcname=f.relative_to(r).as_posix(),recursive=False)
with tarfile.open(archive,'r:gz') as tf:
 for member in tf:
  data=tf.extractfile(member).read();record=expected[member.name]
  assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256'],member.name
report={'archive':archive.relative_to(r).as_posix(),'sha256':sha(archive),'bytes':archive.stat().st_size,'file_count':len(files),'files':expected,'plan_sha256':plan['plan_sha256'],'source_snapshot':plan['source_snapshot'],'all_members_verified':True,'created_at_epoch':time.time()}
with index.open('x') as s:json.dump(report,s,indent=2,sort_keys=True);s.write('\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'}))
