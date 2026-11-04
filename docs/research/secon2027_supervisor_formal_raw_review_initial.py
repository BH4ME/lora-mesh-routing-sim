#!/usr/bin/env python3
"""Independent read-only complete formal raw audit; no repository imports or simulation. Adapted prospectively from the audited pilot checker; controls are checked by their actual toggles."""
from pathlib import Path
import csv, json, hashlib, collections, math, statistics, sys, datetime
ROOT=Path('/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo')
PLAN=ROOT/'results/secon2027/plans/formal-v1.json'
OUT=Path(__file__).with_suffix('.json')
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def jl(p):
 with p.open() as f:
  for line in f:
   if line.strip():yield json.loads(line)
def close(a,b,tol=1e-7):return a is not None and b is not None and abs(float(a)-float(b))<tol
issues=[];checks=collections.Counter()
def ck(ok,kind,where):
 checks[kind]+=1
 if not ok:issues.append({'kind':kind,'where':where})
def marked_route_bound_s(path, radio, safety_margin_s):
    """Independent 2.1.29 wire/LoRa formula; both DATA and ACK carry marker=1."""
    def toa(size):
        sf, bw = radio['sf'], radio['bw_hz']
        de = int(sf >= 11 and bw <= 125000)
        ih = int(not radio['explicit_header'])
        numerator = 8 * size - 4 * sf + 28 + 16 * int(radio['crc']) - 20 * ih
        symbols = 8 + max(math.ceil(numerator / (4 * (sf - 2 * de))) * (radio['cr'] + 4), 0)
        return (radio['preamble_symbols'] + 4.25 + symbols) * 2**sf / bw
    # kind/TTL/flow/endpoints=10; route count/index and 16-bit IDs; repair marker=1.
    header = 10 + (2 + 2 * len(path) if path else 0) + 1
    return max(1, len(path) - 1) * (toa(header + radio['payload_bytes']) + toa(header)) + safety_margin_s

def audit_norepeat_slots(flows, actions, requests, transmissions, radio, safety_margin_s, cutoff, tag, check):
    """Join nominal slots without treating a future reservation as physical TX.

    Frozen on_transmit writes event.time=start, even if called at an earlier
    commit time. _action_rows preserves it. Exported committed_future_start
    requests retain that start/reserved_tx_id but have no physical TX row.
    """
    initial_q, initial_tx, slots = (collections.defaultdict(list) for _ in range(3))
    recovery_q, recovery_events, recovery_tx = (collections.defaultdict(list) for _ in range(3))
    for q in requests:
        fid = q['flow_id']
        if fid not in flows or q['sender'] != flows[fid]['src']:
            continue
        if (q['packet_kind'] == 'CPR_REQUEST' and q.get('actual_packet_kind') == 'DATA'
                and q.get('repair_index') is None and q['status'] in {'started', 'committed_future_start'}):
            initial_q[fid].append(q)
        if q['packet_kind'] == 'CPR_RECOVERY_REQUEST':
            recovery_q[fid].append(q)
    for t in transmissions:
        fid = t['flow_id']
        if fid not in flows or t['sender'] != flows[fid]['src']:
            continue
        if t['packet_kind'] == 'DATA' and t['repair_index'] is None:
            initial_tx[fid].append(t)
        if t['packet_kind'] == 'FLOOD' and t['repair_index'] == 2:
            recovery_tx[fid].append(t)
    for a in actions:
        if a['event'] == 'repeat-slot-skipped':
            slots[a['flow_id']].append(a)
        elif a['event'] == 'recovery-request':
            recovery_events[a['flow_id']].append(a)
    rows = []
    for fid in sorted(set(initial_q) | set(initial_tx) | set(slots) | set(recovery_q) | set(recovery_events) | set(recovery_tx)):
        where = tag + '/' + str(fid)
        unique = fid in flows and len(initial_q[fid]) == 1 and len(slots[fid]) == 1
        check(unique, 'norepeat-unique-slot-initial-request', where)
        if not unique:
            continue
        q, event = initial_q[fid][0], slots[fid][0]
        physical = q['status'] == 'started'
        if physical:
            joined = [t for t in initial_tx[fid] if t['tx_id'] == q['tx_id'] and t['tx_request_id'] == q['tx_request_id']]
            valid = len(initial_tx[fid]) == len(joined) == 1
            check(valid, 'norepeat-slot-physical-initial-join', where)
            if not valid:
                continue
            initial = joined[0]
            check(initial['start'] <= cutoff and close(initial['start'], q['start']) and initial['path'] == q['path'],
                  'norepeat-slot-physical-initial-time', where)
        else:
            initial = q
            check(q['tx_id'] is None and q.get('reserved_tx_id') is not None and q['start'] > cutoff
                  and not initial_tx[fid] and q['requested_at'] <= cutoff,
                  'norepeat-slot-future-reservation-only', where)
            check(not recovery_q[fid] and not recovery_events[fid] and not recovery_tx[fid],
                  'norepeat-future-initial-no-recovery', where)
        start, path = initial['start'], initial['path']
        bound = marked_route_bound_s(path, radio, safety_margin_s)
        slot_end = start + 2 * bound
        check(event.get('src') == flows[fid]['src'] and close(event.get('time'), start),
              'norepeat-slot-event-start', where)
        check(close(event.get('route_bound_s'), bound), 'norepeat-slot-marked-route-bound', where)
        check(close(event.get('slot_ends_at'), slot_end), 'norepeat-slot-nominal-end', where)
        check(len(recovery_q[fid]) == len(recovery_events[fid]) <= 1,
              'norepeat-recovery-request-event-count', where)
        if len(recovery_q[fid]) == len(recovery_events[fid]) == 1:
            rq, ra = recovery_q[fid][0], recovery_events[fid][0]
            check(ra.get('repair_index') == 2 and close(ra.get('time'), rq['requested_at']),
                  'norepeat-recovery-request-event-join', where)
        for rq in recovery_q[fid]:
            check(rq['requested_at'] + 1e-7 >= slot_end and rq['requested_at'] <= cutoff,
                  'norepeat-recovery-request-after-slot', where)
        for ra in recovery_events[fid]:
            check(ra['time'] + 1e-7 >= slot_end and ra['time'] <= cutoff,
                  'norepeat-recovery-event-after-slot', where)
        for tx in recovery_tx[fid]:
            check(tx['start'] + 1e-7 >= slot_end and tx['start'] <= cutoff,
                  'norepeat-recovery-physical-TX-after-slot', where)
            check(any(rq['status'] == 'started' and rq['tx_id'] == tx['tx_id']
                      and rq['tx_request_id'] == tx['tx_request_id'] for rq in recovery_q[fid]),
                  'norepeat-recovery-physical-request-join', where)
        rows.append({'flow_id': fid, 'initial_kind': 'physical-TX' if physical else 'future-reservation',
                     'initial_start': start, 'marked_route_bound_s': bound, 'slot_ends_at': slot_end,
                     'recovery_requests': len(recovery_q[fid]), 'physical_recovery_TX': len(recovery_tx[fid])})
    return rows

p=read(PLAN);states=[];attempts={}
for s in p['runs']:
 ds=sorted((ROOT/'results/secon2027/runs'/s['run_key']).glob('attempt-*'));done=[d for d in ds if (d/'completion.json').exists()];failed=[d for d in ds if (d/'failure.json').exists()]
 states.append({'run_key':s['run_key'],'case':s['case_id'],'arm':s['arm_id'],'seed':s['seed'],'attempts':[d.name for d in ds],'completed':len(done),'failed':len(failed)})
 if len(done)==1:attempts[s['run_key']]=done[0]
if len(attempts)!=760 or any(s['failed'] for s in states):
 print(json.dumps({'status':'pending-or-failed','complete':len(attempts),'states':states},indent=2));sys.exit(3)
snap=ROOT/p['snapshot_path'];desc=read(snap/'snapshot.json')
ck(digest({k:v for k,v in p.items() if k!='plan_sha256'})==p['plan_sha256'],'plan-hash','plan')
ck(digest(p['matrix'])==p['matrix_sha256'],'matrix-hash','matrix')
ck(digest(desc['files'])==p['source_snapshot']==desc['snapshot_id'],'snapshot-hash','snapshot')
for f,meta in desc['files'].items():
 q=snap/'source'/f;ck(q.is_file() and q.stat().st_size==meta['bytes'] and sha(q)==meta['sha256'],'snapshot-file',f)
ck({x.relative_to(snap/'source').as_posix() for x in (snap/'source').rglob('*') if x.is_file() and '__pycache__' not in x.parts}==set(desc['files']),'snapshot-exact-inventory','source')
ck(sha(snap/'source'/p['matrix']['contract_path'])==p['contract_sha256'],'contract-hash','contract')
ck((snap/'source/VERSION').read_text().strip()==p['tested_version']==desc['tested_version'],'version','snapshot')
expected={(c['id'],a,s) for c in p['matrix']['cases'] for a in c['arms'] for s in p['matrix']['seeds']}
ck(len(p['runs'])==760 and len({r['run_key'] for r in p['runs']})==760 and {(r['case_id'],r['arm_id'],r['seed']) for r in p['runs']}==expected,'planned-coverage','760')
ck(p['matrix']['stage']=='validation' and p['matrix']['seeds']==list(range(2027100,2027120)),'formal-identity','plan')
required={'started.json','worker_runtime.json','stdout.log','stderr.log','worker_audit.json','evidence.lock'}|{'evidence.'+s for s in ['runs.csv','paired.csv','summary.csv','flows.jsonl','actions.jsonl','requests.jsonl','transmissions.jsonl','rx_attempts.jsonl','acks.jsonl','identities.json','manifest.json']}
identities={};runs=[];empty=[];totals=collections.Counter();pair_results=[]
for si,s in enumerate(p['runs']):
 key=s['run_key'];cid=s['case_id'];arm=s['arm_id'];protocol=s['arm']['protocol'];seed=s['seed'];tag=f'{cid}/{arm}/{seed}';d=attempts[key]
 c=read(d/'completion.json');m=read(d/'evidence.manifest.json');ident=read(d/'evidence.identities.json')[str(seed)];identities[(cid,arm,seed)]=ident
 ck(digest({k:s[k] for k in ['cohort_id','config_sha256','source_snapshot','case_id','arm_id','seed']})==key,'run-key',tag)
 ck(c['status']=='completed' and m['status']=='completed' and c['run_key']==key and c['plan_sha256']==p['plan_sha256'] and c['source_snapshot']==p['source_snapshot'] and c['tested_version']==p['tested_version'],'completion-binding',tag)
 ck(read(d/'started.json')['spec']==s,'started-spec',tag)
 ck(required<=set(c['files']),'required-files',tag)
 for name,h in c['files'].items():
  f=d/name;ck(f.is_file() and sha(f)==h,'completion-file-sha',tag+'/'+name)
  if f.is_file() and f.stat().st_size==0:empty.append(tag+'/'+name)
 for name,h in m['source_sha256'].items():ck(name in desc['files'] and desc['files'][name]['sha256']==h,'manifest-source-sha',tag+'/'+name)
 ck(m['contract_sha256']==p['contract_sha256'] and m['sim_version']==p['tested_version'] and m['seeds']==[seed] and m['protocols']==[protocol],'manifest-identity',tag)
 rows=list(csv.DictReader((d/'evidence.runs.csv').open()));ck(len(rows)==1,'run-row-count',tag);row=rows[0]
 raw={n:list(jl(d/f'evidence.{n}.jsonl')) for n in ['flows','actions','requests','transmissions','rx_attempts','acks']}
 for name,rr in raw.items():
  label='tx' if name=='transmissions' else name
  ck(len(rr)==m['artifacts'][label]['records'],'manifest-record-count',tag+'/'+name)
  ck(sha(d/f'evidence.{name}.jsonl')==m['artifacts'][label]['sha256'],'manifest-file-sha',tag+'/'+name)
  ck(all(x['protocol']==protocol and x['seed']==seed and x['case']==s['case']['case']['key'] for x in rr),'raw-row-identity',tag+'/'+name)
 flows=raw['flows'];acts=raw['actions'];req=raw['requests'];txs=raw['transmissions'];rxs=raw['rx_attempts'];acks=raw['acks'];trace=ident['application_trace'];cutoff=s['case']['case']['duration_s']+s['case']['deadline_s']
 ck(ident['protocol']==protocol and ident['seed']==seed,'identity-binding',tag)
 fi={x['flow_id']:x for x in flows};qi={x['tx_request_id']:x for x in req};ti={x['tx_id']:x for x in txs};xi={x['rx_attempt_id']:x for x in rxs}
 for name,rr,k in [('flow',flows,'flow_id'),('trace',trace,'flow_id'),('request',req,'tx_request_id'),('tx',txs,'tx_id'),('rx',rxs,'rx_attempt_id'),('ack',acks,'ack_event_id'),('action',acts,'action_ordinal')]:ck(len(rr)==len({x[k] for x in rr}),'unique-ids',tag+'/'+name)
 ck(set(fi)=={x['flow_id'] for x in trace},'scheduled-N',tag)
 pairs=s['case']['environment']['endpoint_pairs']
 ck(all(t['flow_id']==i+1 and t['ordinal']==i+1 and [t['src'],t['dst']]==pairs[i%len(pairs)] and 1<=t['time']<s['case']['case']['duration_s'] and (i==0 or trace[i-1]['time']<t['time']) for i,t in enumerate(trace)) and trace[0]['time']==1.,'trace-shape',tag)
 for obj,field in [(trace,'trace_sha256'),(ident['nodes'],'topology_sha256'),(ident['radio'],'radio_sha256'),(ident['pairs'],'pair_pool_sha256')]:ck(digest(obj)==ident[field],'identity-content-sha',tag+'/'+field)
 ck(digest(m['case'])==m['case_sha256']==ident['case_sha256'],'case-content-sha',tag)
 ck(all(m['case'][k]==v for k,v in s['case']['case'].items()) and m['common_environment']==s['case']['environment'],'plan-case-environment',tag)
 for k,ik in [('scheduled_trace_sha256','trace_sha256'),('topology_sha256','topology_sha256'),('radio_sha256','radio_sha256'),('pair_pool_sha256','pair_pool_sha256'),('environment_sha256','environment_sha256')]:ck(row[k]==ident[ik],'row-identity-sha',tag+'/'+k)
 qr=collections.defaultdict(list);tr=collections.defaultdict(list);ar=collections.defaultdict(list);rx_by_tx=collections.defaultdict(list);delivery_candidates=collections.defaultdict(list)
 for q in req:qr[q['flow_id']].append(q)
 for t in txs:tr[t['flow_id']].append(t)
 for a in acks:ar[a['flow_id']].append(a)
 rx_reasons=collections.Counter();designated_reasons=collections.Counter();designated_kind_reason=collections.Counter()
 for x in rxs:
  t=ti.get(x['tx_id']);ck(t is not None,'rx-tx-exists',tag)
  if t is None:continue
  rx_by_tx[t['tx_id']].append(x);rx_reasons[x['reason']]+=1
  ck(all(x[k]==t[k] for k in ['flow_id','tx_request_id','sender','packet_kind','path','path_index','repair_index']) and close(x['start'],t['start']) and close(x['end'],t['end']),'rx-tx-join',tag)
  ck(x['decoded']==(x['reason']=='success'),'rx-reason-decode',tag)
  ck(all(v in ti for v in x['interference_tx_ids']),'interference-tx-reference',tag)
  path=t['path'];idx=t['path_index'];designated=None
  if t['packet_kind']=='ACK' and 0<=idx<len(path):designated=path[idx]
  elif t['packet_kind'] in {'DATA','RREP'} and idx+1<len(path):designated=path[idx+1]
  if designated==x['receiver']:
   designated_reasons[x['reason']]+=1;designated_kind_reason[(t['packet_kind'],x['reason'])]+=1
  f=fi[x['flow_id']]
  if x['decoded'] and x['receiver']==f['dst'] and t['packet_kind'] in {'DATA','FLOOD','FALLBACK'} and t['origin']==f['src'] and t['final_dst']==f['dst']:
   valid=bool(path) and path[0]==f['src'];directed=t['packet_kind']=='DATA' and protocol!='meshtastic'
   if directed:valid=valid and path[-1]==f['dst'] and idx+1==len(path)-1 and path[idx]==t['sender']
   else:valid=valid and path[-1]==t['sender'] and f['dst'] not in path
   if valid:delivery_candidates[f['flow_id']].append((x['end'],len(path)-1 if directed else len(path),t['tx_id']))
 airtime=0.;kindstats=collections.defaultdict(lambda:[0,0.]);source_stages=collections.Counter();source_counts=collections.Counter();source_stage_by_flow=collections.defaultdict(dict);looped=0
 for t in txs:
  q=qi.get(t['tx_request_id']);ck(q is not None,'tx-request-exists',tag)
  if q:ck(q['status']=='started' and q['tx_id']==t['tx_id'] and all(q[k]==t[k] for k in ['flow_id','sender','path','path_index','repair_index','actual_packet_kind','origin','final_dst']) and close(q['start'],t['start']) and close(q['end'],t['end']) and close(q['toa_s'],t['toa_s']),'tx-request-join',tag)
  ck(t['start']<=cutoff and t['toa_s']>0 and close(t['end']-t['start'],t['toa_s']),'physical-tx-airtime',tag)
  rr=rx_by_tx[t['tx_id']]
  if t['end']<=cutoff:ck(len(rr)==20 and {x['receiver'] for x in rr}==set(range(20)),'rx-completeness',tag)
  else:ck(len(rr)==0,'inflight-no-completed-rx',tag)
  looped+=len(t['path'])!=len(set(t['path']));airtime+=t['toa_s'];kindstats[t['packet_kind']][0]+=1;kindstats[t['packet_kind']][1]+=t['toa_s']
  if protocol.startswith('meshecho-cpr') and t['sender']==fi[t['flow_id']]['src'] and t['packet_kind'] in {'DATA','FLOOD','FALLBACK'}:
   st=('R_INITIAL' if t['packet_kind']=='DATA' else 'F_INITIAL') if t['repair_index'] is None else ('R_REPEAT' if t['packet_kind']=='DATA' and t['repair_index']==1 else 'F_RECOVERY' if t['packet_kind']=='FLOOD' and t['repair_index']==2 else 'UNEXPECTED')
   source_stages[st]+=1;source_counts[t['flow_id']]+=1
   ck(st not in source_stage_by_flow[t['flow_id']] and st!='UNEXPECTED','cpr-single-stage',tag+'/'+str(t['flow_id']))
   source_stage_by_flow[t['flow_id']][st]=t['start']
 ck(looped==0,'loopless-tx-paths',tag)
 if protocol.startswith('meshecho-cpr'):
  ck(max(source_counts.values(),default=0)<=3,'cpr-source-max-three',tag)
  for fid,st in source_stage_by_flow.items():
   if 'R_REPEAT'in st:ck('R_INITIAL'in st and st['R_INITIAL']<=st['R_REPEAT'],'repeat-after-initial',tag+'/'+str(fid))
   if 'F_RECOVERY'in st:
    prior='R_INITIAL' if protocol=='meshecho-cpr-norepeat' else 'R_REPEAT'
    ck(prior in st and st[prior]<=st['F_RECOVERY'],'recovery-after-allowed-prior-stage',tag+'/'+str(fid))
   if protocol=='meshecho-cpr-norepeat':ck('R_REPEAT' not in st and len(st)<=2,'repeat-disabled',tag+'/'+str(fid))
   if protocol=='meshecho-cpr-norecovery':ck('F_RECOVERY' not in st and len(st)<=2,'recovery-disabled',tag+'/'+str(fid))
 norepeat_slots=[]
 if protocol=='meshecho-cpr-norepeat':
  margin=ident['protocol_parameters']['safety_margin_s']
  ck(close(margin,m['case']['safety_margin_s']),'norepeat-slot-safety-margin',tag)
  norepeat_slots=audit_norepeat_slots(fi,acts,req,txs,ident['radio'],margin,cutoff,tag,ck)
 for q in req:
  ck((q['tx_id'] in ti and ti[q['tx_id']]['tx_request_id']==q['tx_request_id']) if q['status']=='started' else q['tx_id'] is None,'request-tx-bijection',tag)
 for a in acks:
  x=xi.get(a['ack_rx_attempt_id']);t=ti.get(a['ack_tx_id']);f=fi[a['flow_id']]
  ck(x is not None and t is not None,'ack-physical-provenance',tag)
  if not(x and t):continue
  ck(t['packet_kind']=='ACK' and t['flow_id']==a['flow_id']==x['flow_id'] and a['ack_tx_id']==x['tx_id'] and a['ack_tx_request_id']==x['tx_request_id']==t['tx_request_id'] and x['decoded'] and close(a['ack_rx_at'],x['end']),'ack-rx-tx-join',tag)
  if a['accepted']:
   ck(a['source']==a['receiver']==f['src']==x['receiver'] and a['destination']==f['dst'] and close(a['accepted_at'],x['end']) and a['reverse_path']==t['path'] and t['path'][0]==f['src'] and t['path'][-1]==f['dst'] and a['reverse_hop']==t['path_index']==0 and t['sender']==t['path'][1],'accepted-ack-eligibility',tag)
 cancels=0;evictions=0;evict_pending=0
 for a in acts:
  if a['event'] in {'cpr-cancel','cpr-cancel-check'}:
   x=xi.get(a['ack_rx_attempt_id']);ck(x is not None and x['decoded'] and x['packet_kind']=='ACK' and x['flow_id']==a['flow_id'] and close(x['end'],a['time']) and x['receiver']==a.get('node',a.get('relay')),'cancel-physical-ACK',tag)
  if a['event']=='cpr-cancel':
   cancels+=1;qs=[q for q in qr[a['flow_id']] if q['sender']==a['relay'] and q['repair_index']==a['repair_index'] and q['packet_kind']=='FLOOD' and q['requested_at']<=a['time']+1e-8 and a['time']<=q['status_at']+1e-8]
   ck(len(qs)==1 and qs[0]['status']=='canceled' and qs[0]['tx_id'] is None,'cancel-retained-no-tx-request',tag)
  if a['event']=='state-eviction':evictions+=1;evict_pending+=bool(a.get('pending_canceled'))
 ck(sum(a['event']=='cpr-cancel-check' and a['canceled'] for a in acts)==cancels,'cancel-check-success-count',tag)
 if protocol=='meshecho-cpr-noackcancel':ck(cancels==0,'ack-cancel-disabled',tag)
 n=len(trace);an=dn=0;hops=collections.Counter();ackhops=collections.Counter();first_modes=collections.Counter();lat=[];bad=[];latea=lated=0;initial_source_paths=[]
 for t in trace:
  f=fi[t['flow_id']];fid=f['flow_id'];deadline=t['time']+s['case']['deadline_s'];qf=qr[fid]
  ck(f['src']==t['src'] and f['dst']==t['dst'] and close(f['enqueued_at'],t['time']) and close(f['deadline_at'],deadline),'flow-scheduled-trace',tag)
  ck(f['request_count']==len(qf) and f['started_request_count']==sum(q['status']=='started' for q in qf) and f['no_start_count']==sum(q['status']!='started' for q in qf),'flow-request-counts',tag)
  accepted=[a for a in ar[fid] if a['accepted']];at=accepted[0]['accepted_at'] if accepted else None
  ck(len(accepted)<=1 and ((at is None and f['accepted_ack_at'] is None) or close(at,f['accepted_ack_at'])),'flow-ack-reconstruction',tag)
  delivered=min(delivery_candidates[fid]) if delivery_candidates[fid] else None;dt=delivered[0] if delivered else None
  ck((dt is None and f['first_delivery_at'] is None) or close(dt,f['first_delivery_at']),'flow-delivery-RX-reconstruction',tag+'/'+str(fid))
  aa=at is not None and at<=deadline;dd=dt is not None and dt<=deadline;an+=aa;dn+=dd;latea+=at is not None and not aa;lated+=dt is not None and not dd
  ck(f['ack_by_deadline']==aa and f['delivery_by_deadline']==dd,'flow-deadline',tag)
  if delivered:hops[str(delivered[1])]+=1
  if accepted:ackhops[str(len(accepted[0]['reverse_path'])-1)]+=1
  if aa:lat.append(at-t['time'])
  if not aa or not dd:bad.append({'flow_id':fid,'ack':aa,'delivery':dd})
  first_modes[str(f['initial_action'])]+=1
 for field,value in [('scheduled_unicast_flows',n),('unicast_flows',n),('flows',n),('ack_by_deadline',an),('delivery_by_deadline',dn),('ack_pdr_deadline',an/n),('delivery_pdr_deadline',dn/n),('tx_count',len(txs)),('started_request_count',len(txs)),('request_count',len(req)),('no_start_count',len(req)-len(txs)),('total_airtime_s',airtime),('tx_ledger_airtime_s',airtime),('accepted_ack_count',sum(a['accepted'] for a in acks)),('rx_attempt_count',len(rxs)),('protocol_action_count',len(acts))]:ck(close(row[field],value),'csv-recomputed',tag+'/'+field)
 ck((row['airtime_per_deadline_delivery_s']=='') if dn==0 else close(row['airtime_per_deadline_delivery_s'],airtime/dn),'airtime-per-delivery',tag)
 for field,value in [('data_tx',sum(t['packet_kind'] in {'DATA','FLOOD','FALLBACK'} for t in txs)),('control_tx',sum(t['packet_kind'] not in {'DATA','FLOOD','FALLBACK'} for t in txs)),('ack_tx',sum(t['packet_kind']=='ACK' for t in txs))]:ck(close(row[field],value),'physical-packet-partition',tag+'/'+field)
 for field,value in [('scheduled_flows',n),('transmissions',len(txs)),('requests',len(req)),('accepted_acks',len(acks)),('rx_attempts',len(rxs))]:ck(m['counts'][field]==value,'manifest-count',tag+'/'+field)
 wait=[q['queue_wait_s'] for q in req if q.get('queue_wait_s') is not None];statuses=collections.Counter(q['status'] for q in req);noreasons=collections.Counter(str(q.get('no_start_reason')) for q in req if q['status']!='started');decision_reasons=collections.Counter(a.get('reason') for a in acts if a['event']=='decision');event_counts=collections.Counter(a['event'] for a in acts)
 run={'case':cid,'scenario':s['case']['scenario'],'configuration':s['case']['configuration'],'arm':arm,'protocol':protocol,'seed':seed,'run_key':key,'completion_sha256':sha(d/'completion.json'),'N':n,'ack_deadline':an,'delivery_deadline':dn,'ack_pdr':an/n,'delivery_pdr':dn/n,'tx':len(txs),'airtime_s':airtime,'requests':len(req),'rx':len(rxs),'packet_kind':dict(kindstats),'source_stage_TX':dict(source_stages),'initial_actions':dict(first_modes),'delivery_hops':dict(hops),'accepted_ack_hops':dict(ackhops),'events':dict(event_counts),'decision_reasons':dict(decision_reasons),'request_statuses':dict(statuses),'no_start_reasons':dict(noreasons),'request_wait_count':len(wait),'request_wait_positive_count':sum(x>1e-9 for x in wait),'request_wait_mean_s':statistics.fmean(wait) if wait else None,'request_wait_max_s':max(wait,default=0),'rx_reasons':dict(rx_reasons),'designated_rx_reasons':dict(designated_reasons),'designated_kind_reason':[{'kind':k[0],'reason':k[1],'count':v} for k,v in designated_kind_reason.items()],'ACK_cancel_success':cancels,'capacity_evictions':evictions,'capacity_pending_canceled':evict_pending,'late_ACK':latea,'late_delivery':lated,'cache_hits_exported':int(row['route_cache_hits']),'cache_misses_exported':int(row['route_cache_misses']),'inflight_at_cutoff':int(row['in_flight_at_cutoff_count']),'future_committed':int(row['committed_future_start_count']),'bad_flows':bad,'wall_seconds':c['wall_seconds']}
 run['norepeat_slots']=norepeat_slots
 runs.append(run)
 for k,v in [('N',n),('ACK',an),('delivery',dn),('TX',len(txs)),('airtime_s',airtime),('requests',len(req)),('RX',len(rxs)),('actions',len(acts)),('accepted_ACK_records',sum(a['accepted'] for a in acks)),('rejected_ACK_records',sum(not a['accepted'] for a in acks))]:totals[k]+=v
 if (si+1)%50==0 or si+1==len(p['runs']):print(f'checked {si+1}/{len(p["runs"])} {tag}',flush=True)
for case in p['matrix']['cases']:
 for seed in p['matrix']['seeds']:
  ids=[identities[(case['id'],a,seed)] for a in case['arms']];fields=['application_trace','nodes','pairs','radio','static_shadowing_db','common_environment','case_sha256','trace_sha256','topology_sha256','radio_sha256','pair_pool_sha256','environment_sha256']
  for other in ids[1:]:
   for field in fields:ck(ids[0][field]==other[field],'four-arm-common-inputs',case['id']+'/'+str(seed)+'/'+field)
  pair_results.append({'case':case['id'],'seed':seed,'content_sha256':{field:digest(ids[0][field]) for field in ['application_trace','nodes','pairs','radio','static_shadowing_db','common_environment']}})
for scenario in ['S1','S2','S3']:
 for seed in p['matrix']['seeds']:
  for proto in ['meshecho-cpr','meshecho','meshtastic','meshcore']:
   a=identities[(scenario+'-default',proto,seed)];b=identities[(scenario+'-matched',proto+'-matched',seed)]
   for f in ['application_trace','nodes','pairs','radio','static_shadowing_db','common_environment']:ck(a[f]==b[f],'default-matched-common-inputs',scenario+'/'+proto+'/'+str(seed)+'/'+f)
   pars=dict(a['protocol_parameters']);pars.update(next(x['parameters'] for x in p['matrix']['arms'] if x['id']==proto+'-matched'))
   ck(pars==b['protocol_parameters'],'matched-effective-parameters',scenario+'/'+proto+'/'+str(seed))
for cid in ['S2-matched','S3-matched']:
 for seed in p['matrix']['seeds']:
  full=identities[(cid,'meshecho-cpr-matched',seed)]['protocol_parameters']
  for arm,toggle in [('meshecho-cpr-noackcancel','cancel_on_ack'),('meshecho-cpr-norepeat','enable_repeat'),('meshecho-cpr-norecovery','enable_recovery')]:
   control=identities[(cid,arm,seed)]['protocol_parameters']
   differences={k for k in set(full)|set(control) if (k in full)!=(k in control) or full.get(k)!=control.get(k)}
   ck(differences<={'name',toggle} and full.get(toggle) is True and control.get(toggle) is False,'clean-control-parameters',cid+'/'+arm+'/'+str(seed))
record={'status':'passed' if not issues else 'discrepancies','audited_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'plan_file_sha256':sha(PLAN),'plan_sha256':p['plan_sha256'],'matrix_sha256':p['matrix_sha256'],'snapshot':p['source_snapshot'],'snapshot_descriptor_sha256':sha(snap/'snapshot.json'),'snapshot_files':len(desc['files']),'contract_sha256':p['contract_sha256'],'tested_version':p['tested_version'],'script_sha256':sha(Path(__file__)),'runs_complete':len(runs),'plan_states':states,'checks':dict(checks),'issues':issues,'totals':dict(totals),'runs':runs,'common_inputs':pair_results,'empty_files':empty}
OUT.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'status':record['status'],'totals':record['totals'],'issues':issues,'out':str(OUT)},indent=2))
