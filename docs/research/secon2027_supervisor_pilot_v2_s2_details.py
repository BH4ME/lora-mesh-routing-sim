from pathlib import Path
import json,csv,hashlib,collections,math,datetime
ROOT=Path('/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo')
OUT=Path('/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2/docs/research/secon2027_supervisor_pilot_v2_s2_details.json')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def close(a,b):return a is not None and b is not None and abs(float(a)-float(b))<1e-8
def edges(path):return {tuple(sorted(e)) for e in zip(path,path[1:])}
planpath=ROOT/'results/secon2027/plans/development-pilot-v2.json';plan=read(planpath);runs=[];issues=[];checks=collections.Counter();total=collections.Counter();warm=[]
def check(b,k,detail):
 checks[k]+=1
 if not b:issues.append({'kind':k,'detail':detail})
check(digest({k:v for k,v in plan.items() if k!='plan_sha256'})==plan['plan_sha256'],'plan-hash','plan')
for spec in [s for s in plan['runs'] if s['case']['scenario']=='S2']:
 tag=f"{spec['case_id']}/{spec['arm_id']}/{spec['seed']}";base=ROOT/'results/secon2027/runs'/spec['run_key'];done=[d for d in base.glob('attempt-*') if (d/'completion.json').is_file()]
 if len(done)!=1:
  issues.append({'kind':'completion','detail':tag});continue
 d=done[0];completion=read(d/'completion.json');check(completion['status']=='completed' and completion['plan_sha256']==plan['plan_sha256'] and completion['source_snapshot']==plan['source_snapshot'],'completion-identity',tag)
 for name,h in completion['files'].items():check((d/name).is_file() and sha(d/name)==h,'artifact-hash',tag+'/'+name)
 def raw(name):return [json.loads(s) for s in (d/f'evidence.{name}.jsonl').read_text().splitlines()]
 flows=raw('flows');acts=raw('actions');txs=raw('transmissions');acks=raw('acks');reqs=raw('requests');rxs=raw('rx_attempts');identity=read(d/'evidence.identities.json')[str(spec['seed'])];row=next(csv.DictReader((d/'evidence.runs.csv').open()))
 fs={x['flow_id']:x for x in flows};ts={x['tx_id']:x for x in txs};rs={x['tx_request_id']:x for x in reqs};xs={x['rx_attempt_id']:x for x in rxs}
 check(len(fs)==len(flows)==len(identity['application_trace']),'flow-unique-denominator',tag);check(len(ts)==len(txs) and len(rs)==len(reqs) and len(xs)==len(rxs),'event-unique-ids',tag)
 proto=spec['arm']['protocol'];fault=spec['case']['environment']['faults'][0];start,end=fault['start_s'],fault['end_s'];bad={tuple(sorted(e)) for e in fault['edges']}
 def during(t):return start<=t<end
 tx_byflow=collections.defaultdict(list);rx_bytx=collections.defaultdict(list);ack_byflow=collections.defaultdict(list);act_byflow=collections.defaultdict(list);accepted=[]
 for t in txs:
  tx_byflow[t['flow_id']].append(t);q=rs.get(t['tx_request_id']);check(q is not None and q['status']=='started' and q['tx_id']==t['tx_id'] and q['flow_id']==t['flow_id'] and close(q['start'],t['start']) and close(q['end'],t['end']),'tx-request-join',tag)
 for x in rxs:
  t=ts.get(x['tx_id']);rx_bytx[x['tx_id']].append(x);check(t is not None and x['flow_id']==t['flow_id'] and x['tx_request_id']==t['tx_request_id'] and x['sender']==t['sender'] and x['path']==t['path'] and close(x['end'],t['end']),'rx-tx-join',tag)
 for a in acks:
  if not a['accepted']:continue
  accepted.append(a);ack_byflow[a['flow_id']].append(a);x=xs.get(a['ack_rx_attempt_id']);t=ts.get(a['ack_tx_id']);f=fs[a['flow_id']]
  check(x is not None and t is not None and x['decoded'] and x['receiver']==f['src']==a['source'] and a['destination']==f['dst'] and x['flow_id']==a['flow_id']==t['flow_id'] and x['tx_id']==t['tx_id'] and a['ack_tx_request_id']==x['tx_request_id']==t['tx_request_id'] and close(a['accepted_at'],x['end']),'ack-physical-join',tag)
 for a in acts:act_byflow[a['flow_id']].append(a)
 if proto=='meshecho-cpr':
  for a in accepted:
   check(any(x['event']=='ack-accept' and close(x['time'],a['accepted_at']) and x['path']==a['reverse_path'] and x['cache_update']==a.get('cache_update') and x['route_generation_after']==a.get('route_generation_after') for x in act_byflow[a['flow_id']]),'ack-cache-action-join',tag)
 source_initial={};flow_details=[];designated_fault=[];broadcast_fault=[];warm_acks=[a for a in accepted if a['accepted_at']<start];pre_paths=[]
 for a in warm_acks:
  pre_paths.append({'flow_id':a['flow_id'],'src':a['source'],'dst':a['destination'],'accepted_at':a['accepted_at'],'path':a['reverse_path'],'hops':len(a['reverse_path'])-1,'fault_edge_intersection':[list(e) for e in sorted(edges(a['reverse_path'])&bad)],'cache_update':a.get('cache_update'),'generation_after':a.get('route_generation_after')})
 for t in txs:
  if not during(t['start']):continue
  path=t['path'];index=t['path_index'];nxt=None
  if t['packet_kind']=='ACK' and 0<=index<len(path):nxt=path[index]
  if t['packet_kind'] in {'DATA','RREP'} and 0<=index<len(path)-1:nxt=path[index+1]
  if nxt is not None and tuple(sorted((t['sender'],nxt))) in bad:
   rr=[x for x in rx_bytx[t['tx_id']] if x['receiver']==nxt];check(len(rr)==1,'fault-next-hop-unique-rx',tag)
   if rr:
    x=rr[0];designated_fault.append({'flow_id':t['flow_id'],'tx_id':t['tx_id'],'request_id':t['tx_request_id'],'rx_attempt_id':x['rx_attempt_id'],'kind':t['packet_kind'],'marker':t['repair_index'],'edge':[t['sender'],nxt],'start':t['start'],'decoded':x['decoded'],'reason':x['reason'],'path':path,'rx_power_dbm':x['rx_power_dbm'],'sinr_db':x['sinr_db']})
  if nxt is None and t['packet_kind'] in {'FLOOD','FALLBACK','RREQ','DATA'}:
   for x in rx_bytx[t['tx_id']]:
    if tuple(sorted((t['sender'],x['receiver']))) in bad:broadcast_fault.append({'flow_id':t['flow_id'],'tx_id':t['tx_id'],'kind':t['packet_kind'],'decoded':x['decoded'],'reason':x['reason'],'edge':[t['sender'],x['receiver']]})
 for f in flows:
  fid=f['flow_id'];source=[t for t in tx_byflow[fid] if t['sender']==f['src'] and t['packet_kind'] in {'DATA','FLOOD','FALLBACK'}];initial=min(source,key=lambda t:t['start']) if source else None;source_initial[fid]=initial
  a=ack_byflow[fid];check(len(a)<=1 and ((not a and f['accepted_ack_at'] is None) or (a and close(a[0]['accepted_at'],f['accepted_ack_at']))),'flow-ack',tag+'/'+str(fid))
  if proto=='meshecho-cpr':
   decisions=[x for x in act_byflow[fid] if x['event']=='decision'];check(bool(decisions) and decisions[0]['action']==f['initial_action'],'flow-action',tag+'/'+str(fid))
   for t in source:
    label='R_REPEAT' if t['repair_index']==1 else 'F_RECOVERY' if t['repair_index']==2 else 'R_INITIAL' if t['packet_kind']=='DATA' else 'F_INITIAL'
    check(any(x['action']==label and close(x['time'],t['start']) for x in decisions),'physical-stage-decision',tag+'/'+str(fid))
  fullpath=initial['path'] if initial and initial['packet_kind']=='DATA' and initial['path'] and initial['path'][-1]==f['dst'] else None
  prior_pre=[a for a in warm_acks if a['source']==f['src'] and a['destination']==f['dst'] and a['accepted_at']<initial['start'] and a['reverse_path']==fullpath] if initial and fullpath else []
  cross=sorted(edges(fullpath)&bad) if fullpath else []
  decision=next((x for x in act_byflow[fid] if x['event']=='decision'),None)
  confirmed_generation=[a for a in prior_pre if a.get('route_generation_after')==(decision or {}).get('route_generation')] if proto=='meshecho-cpr' else []
  cand=[]
  for t in tx_byflow[fid]:
   if t['packet_kind'] not in {'DATA','FLOOD','FALLBACK'} or t['origin']!=f['src'] or t['final_dst']!=f['dst']:continue
   path=t['path'];idx=t['path_index'];directed=t['packet_kind']=='DATA' and proto!='meshtastic'
   valid=bool(path) and path[0]==f['src']
   valid=valid and (path[-1]==f['dst'] and idx+1==len(path)-1 and path[idx]==t['sender'] if directed else path[-1]==t['sender'] and f['dst'] not in path)
   if not valid:continue
   for x in rx_bytx[t['tx_id']]:
    if x['receiver']==f['dst'] and x['decoded']:cand.append((x['end'],t['tx_id'],path if directed else path+[f['dst']],t['repair_index'],x['rx_attempt_id']))
  delivery=min(cand) if cand else None
  hop_chain=[]
  if delivery:
   prev=f['enqueued_at']
   for hi,(u,v) in enumerate(zip(delivery[2],delivery[2][1:])):
    options=[]
    for t in tx_byflow[fid]:
     if t['sender']!=u or t['packet_kind'] not in {'DATA','FLOOD','FALLBACK'} or t['repair_index']!=delivery[3] or t['origin']!=f['src'] or t['final_dst']!=f['dst'] or t['start']<prev-1e-8:continue
     directed=t['packet_kind']=='DATA' and proto!='meshtastic'
     if t['path']!=(delivery[2] if directed else delivery[2][:hi+1]):continue
     for xx in rx_bytx[t['tx_id']]:
      if xx['decoded'] and xx['receiver']==v and xx['end']<=delivery[0]+1e-8:options.append((xx['end'],t['tx_id'],xx['rx_attempt_id']))
    if not options:break
    chosen=min(options);prev=chosen[0];hop_chain.append({'from':u,'to':v,'end':chosen[0],'tx_id':chosen[1],'rx_attempt_id':chosen[2]})
   check(len(hop_chain)==len(delivery[2])-1,'delivery-all-hops-physical-chain',tag+'/'+str(fid))
  check((delivery is None and f['first_delivery_at'] is None) or (delivery is not None and close(delivery[0],f['first_delivery_at'])),'physical-first-delivery',tag+'/'+str(fid))
  cutoff=float(row['drain_until_s']);active_end=min(f['deadline_at'],f['accepted_ack_at'] if f['accepted_ack_at'] is not None else math.inf,cutoff)
  failed=[x for x in designated_fault if x['flow_id']==fid and not x['decoded']];recovery=[t for t in source if t['packet_kind']=='FLOOD' and t['repair_index']==2];repeat=[t for t in source if t['packet_kind']=='DATA' and t['repair_index']==1]
  detour=bool(delivery and during(delivery[0]) and len(delivery[2])-1==6 and not(edges(delivery[2])&bad))
  fd={'flow_id':fid,'src':f['src'],'dst':f['dst'],'enqueued_at':f['enqueued_at'],'enqueued_during_fault':during(f['enqueued_at']),'active_during_fault':max(f['enqueued_at'],start)<min(active_end,end),'initial_tx_id':initial['tx_id'] if initial else None,'initial_at':initial['start'] if initial else None,'initial_kind':initial['packet_kind'] if initial else None,'initial_action':f['initial_action'],'initial_full_data_path':fullpath,'initial_during_fault':bool(initial and during(initial['start'])),'initial_fault_edge_intersection':[list(x) for x in cross],'initial_during_fault_path_cross':bool(initial and during(initial['start']) and cross),'pre_fault_ack_matching_initial_path_flow_ids':[a['flow_id'] for a in prior_pre],'initial_route_generation':decision.get('route_generation') if decision else None,'pre_fault_ack_matching_initial_generation_flow_ids':[a['flow_id'] for a in confirmed_generation],'repeat_tx_ids':[t['tx_id'] for t in repeat],'recovery_tx_ids':[t['tx_id'] for t in recovery],'repeat_during_fault':sum(during(t['start']) for t in repeat),'recovery_during_fault':sum(during(t['start']) for t in recovery),'actual_fault_designated_failures':failed,'delivery_at':delivery[0] if delivery else None,'delivery_tx_id':delivery[1] if delivery else None,'delivery_path':delivery[2] if delivery else None,'delivery_hop_chain':hop_chain,'delivery_marker':delivery[3] if delivery else None,'delivery_rx_attempt_id':delivery[4] if delivery else None,'six_hop_detour_delivery_during_fault':detour,'detour_after_fault_failure_and_recovery':bool(detour and failed and recovery and delivery[3]==2 and any(ts[x['tx_id']]['end']<=rec['start']<=delivery[0] for x in failed for rec in recovery)),'ack_at':f['accepted_ack_at'],'ack_deadline':f['ack_by_deadline'],'delivery_deadline':f['delivery_by_deadline']}
  flow_details.append(fd)
 counters={'N':len(flows),'pre_fault_enqueued':sum(f['enqueued_at']<start for f in flows),'fault_enqueued':sum(x['enqueued_during_fault'] for x in flow_details),'fault_active':sum(x['active_during_fault'] for x in flow_details),'pre_fault_accepted_acks':len(warm_acks),'pre_fault_ack_paths_cross_fault_edges':sum(bool(x['fault_edge_intersection']) for x in pre_paths),'pre_fault_ack_endpoint_pairs':len({(a['source'],a['destination']) for a in warm_acks}),'initial_full_data_during_fault':sum(x['initial_during_fault'] and x['initial_full_data_path'] is not None for x in flow_details),'initial_full_data_cross_fault_edges':sum(x['initial_during_fault_path_cross'] for x in flow_details),'crossing_initial_with_pre_fault_ack_same_path':sum(x['initial_during_fault_path_cross'] and bool(x['pre_fault_ack_matching_initial_path_flow_ids']) for x in flow_details),'cpr_crossing_initial_with_pre_fault_ack_same_generation':sum(x['initial_during_fault_path_cross'] and bool(x['pre_fault_ack_matching_initial_generation_flow_ids']) for x in flow_details),'fault_designated_rx':len(designated_fault),'fault_designated_rx_failed':sum(not x['decoded'] for x in designated_fault),'fault_designated_rx_decoded':sum(x['decoded'] for x in designated_fault),'fault_broadcast_neighbor_rx':len(broadcast_fault),'fault_broadcast_neighbor_rx_failed':sum(not x['decoded'] for x in broadcast_fault),'repeat_physical':sum(len(x['repeat_tx_ids']) for x in flow_details),'recovery_physical':sum(len(x['recovery_tx_ids']) for x in flow_details),'repeat_during_fault':sum(x['repeat_during_fault'] for x in flow_details),'recovery_during_fault':sum(x['recovery_during_fault'] for x in flow_details),'six_hop_detour_delivery_during_fault':sum(x['six_hop_detour_delivery_during_fault'] for x in flow_details),'detour_after_fault_failure_and_recovery':sum(x['detour_after_fault_failure_and_recovery'] for x in flow_details),'ack_deadline':sum(x['ack_deadline'] for x in flow_details),'delivery_deadline':sum(x['delivery_deadline'] for x in flow_details),'tx':len(txs),'rx':len(rxs)}
 for k,v in counters.items():total[k]+=v
 check(counters['ack_deadline']==int(row['ack_by_deadline']) and counters['delivery_deadline']==int(row['delivery_by_deadline']),'summary-deadline',tag)
 runs.append({'case_id':spec['case_id'],'arm_id':spec['arm_id'],'protocol':proto,'seed':spec['seed'],'run_key':spec['run_key'],'completion_sha256':sha(d/'completion.json'),'counters':counters,'pre_fault_accepted_paths':pre_paths,'designated_fault_rx':designated_fault,'broadcast_fault_rx_counts':dict(collections.Counter((x['kind']+':'+x['reason']) for x in broadcast_fault)),'flows':flow_details})
result={'reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'S2 only; independent raw joins; no simulator import/run/RNG; no execution-workspace mutation','plan_path':str(planpath),'plan_file_sha256':sha(planpath),'plan_sha256':plan['plan_sha256'],'snapshot':plan['source_snapshot'],'tested_version':plan['tested_version'],'expected_runs':24,'completed_runs':len(runs),'script_sha256':sha(Path(__file__)),'checks':dict(checks),'issues':issues,'totals_counting_default_and_matched_separately':dict(total),'runs':runs}
OUT.write_text(json.dumps(result,indent=2)+'\n');print('ISSUES',issues);print('TOTAL',dict(total))
for r in runs: print(r['case_id'],r['arm_id'],r['seed'],r['counters'])
print('OUTPUT',OUT)
