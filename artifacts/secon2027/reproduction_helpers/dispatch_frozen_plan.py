#!/usr/bin/env python3
"""Launch only frozen keys using the tested runner; stop new submissions on error."""
import argparse,concurrent.futures,json,os,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--plan',required=True);p.add_argument('--gate',required=True);p.add_argument('--python',default='/usr/bin/python3');a=p.parse_args()
r=a.root.resolve();plan=json.loads((r/a.plan).read_text());gate=r/a.gate;gate.mkdir(parents=True,exist_ok=True)
workers=plan['matrix']['budget']['concurrency'];assert isinstance(workers,int) and 1<=workers<=4
log=(gate/'dispatch.jsonl').open('x',buffering=1)
log.write(json.dumps({'event':'started','pid':os.getpid(),'at_epoch':time.time(),'plan_sha256':plan['plan_sha256'],'concurrency':workers,'keys':len(plan['runs'])})+'\n')
def run(spec):
 key=spec['run_key'];cmd=[a.python,'tools/secon2027_experiment.py','run','--plan',a.plan,'--run-key',key]
 started=time.monotonic()
 with (gate/(key+'.log')).open('x') as f:proc=subprocess.run(cmd,cwd=r,stdout=f,stderr=subprocess.STDOUT)
 return {'run_key':key,'exit_code':proc.returncode,'wall_seconds':time.monotonic()-started,'command':cmd,'at_epoch':time.time()}
remaining=iter(plan['runs']);failed=False;count=0
with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
 active={pool.submit(run,next(remaining)) for _ in range(min(workers,len(plan['runs'])))}
 while active:
  done,active=concurrent.futures.wait(active,return_when=concurrent.futures.FIRST_COMPLETED)
  for future in done:
   item=future.result();count+=1;item['progress']=[count,len(plan['runs'])];log.write(json.dumps(item)+'\n');print(json.dumps(item),flush=True)
   if item['exit_code']:failed=True
  if not failed:
   for _ in done:
    spec=next(remaining,None)
    if spec is not None:active.add(pool.submit(run,spec))
log.write(json.dumps({'event':'finished','at_epoch':time.time(),'completed_launches':count,'failed':failed})+'\n');log.close()
raise SystemExit(1 if failed else 0)
