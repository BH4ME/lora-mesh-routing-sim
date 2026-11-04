"""Targeted recovery-branch fixture. Never dispatches a simulator event loop.
Uses the existing five-node test_secon_cpr_correctness fixture (seed 23).
"""
from pathlib import Path
import sys, json, hashlib, traceback
root=Path(sys.argv[1]).resolve(); expected=sys.argv[2]; output=Path(sys.argv[3])
sys.dont_write_bytecode=True
sys.path.insert(0,str(root))
from lora_mesh_sim import MeshEchoCPR, Simulator, Node, RadioConfig
from meshecho_drc import RoutePhase

def forbidden_run(*args,**kwargs):
    raise AssertionError('Simulator.run is forbidden in this fixture')
Simulator.run=forbidden_run

def setup():
    # Exact established fixture construction; no application schedule or channel RX.
    protocol=MeshEchoCPR()
    sim=Simulator([Node(i,float(i),0.0) for i in range(5)],
                  RadioConfig(sf=7,shadow_sigma_db=0.0),protocol,
                  seed=23,max_hops=4,independent_random_streams=True)
    state=protocol._state(0)
    state.install_route(4,(0,4),now=0.0,ttl_s=100.0)
    sim.now=1.0
    protocol.send_app(0,4,1)
    flow=protocol.cpr_flows[1]
    sim.begin_transmission(0,protocol._cpr_placeholder(flow,'CPR_REQUEST'),protocol.cpr_initial_pending[1])
    sim.now=2.0
    protocol._cpr_arm_repeat(1)
    sim.begin_transmission(0,protocol._cpr_placeholder(flow,'CPR_REPEAT_REQUEST'),protocol.cpr_repeat_pending[1])
    sim.now=3.0
    protocol._cpr_arm_recovery(1)
    return protocol,sim,state,flow,protocol.cpr_recovery_pending[1]

results=[]
for case in ['missing','quarantined','new-generation','expired','ready']:
    protocol,sim,state,flow,pending=setup()
    if case=='missing':state.routes.pop(4)
    if case=='quarantined':state.record_in_deadline_miss(4,flow.route_generation)
    if case=='new-generation':state.install_route(4,(0,2,4),now=2.5,ttl_s=100.)
    if case=='expired':state.routes[4].expires_at=3.0
    before_count=sim.metrics.tx_count
    before_airtime=sim.metrics.total_airtime_s
    before_transmissions=list(sim.transmissions)
    before_requests=len(sim.tx_requests)
    expected_new_route=state.routes.get(4)
    exc=None
    try:
        sim.begin_transmission(0,protocol._cpr_placeholder(flow,'CPR_RECOVERY_REQUEST'),pending)
    except Exception as e:
        exc={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()}
    if case!='ready' and expected=='nameerror':
        assert exc and exc['type']=='NameError' and 'CprDecision' in exc['message'],(case,exc)
    else:
        assert exc is None,(case,exc)
    request=sim._request_records[pending.request_id]
    if case!='ready' and expected=='fixed':
        assert sim.metrics.tx_count==before_count==2
        assert sim.metrics.total_airtime_s==before_airtime
        assert sim.transmissions==before_transmissions
        assert len(sim.tx_requests)==before_requests==3
        assert request['status']=='protocol-no-start' and request['no_start_reason']=='protocol-hook'
        assert request['tx_id'] is None and request['end'] is None and request.get('toa_s') is None
        assert not pending.committed
        assert flow.recovery_requested and flow.recovery_started_at is None and flow.acked_at is None
        assert flow.recovery_route_epoch is None
        assert protocol.flow_actions[1]=='R_REPEAT'
        decision=protocol.action_events[-1]
        assert decision['event']=='decision' and decision['reason']=='stale-route-generation'
        assert decision['action']=='DROP_DEADLINE_INFEASIBLE'
        assert 1 in sim.metrics.flows and sim.metrics.flows[1].acked_at is None
        before_request=dict(request)
        sim.now=flow.deadline
        protocol._cpr_expire_deadline(1)
        sim.finalize_request_ledger(flow.deadline)
        assert request==before_request
        assert 1 in sim.metrics.flows and 1 in protocol.retired_flows
        assert sim.metrics.flows[1].acked_at is None and sim.metrics.flows[1].delivered_at is None
        if case=='new-generation':
            assert state.routes[4] is expected_new_route and state.routes[4].path==(0,2,4)
            assert state.routes[4].phase is RoutePhase.READY and state.routes[4].miss_streak==0
    if case=='ready':
        assert sim.metrics.tx_count==3 and len(sim.transmissions)==3
        assert flow.recovery_started_at==3.0 and pending.committed
        assert request['status']=='started' and request['tx_id']==sim.transmissions[-1].tx_id
        assert sim.transmissions[-1].packet.kind=='FLOOD' and sim.transmissions[-1].packet.repair_index==2
    results.append({'case':case,'exception':exc,'request_status':request['status'],
                    'request_retained':request in sim.tx_requests,'tx_id':request['tx_id'],
                    'physical_tx_count':sim.metrics.tx_count,'total_airtime_s':sim.metrics.total_airtime_s,
                    'recovery_started_at':flow.recovery_started_at,
                    'metric_flow_retained':1 in sim.metrics.flows,
                    'last_action':protocol.action_events[-1]})
record={'source_root':str(root),'expected':expected,'existing_fixture_seed':23,'simulator_run_calls':0,
        'sha256':{f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in ['lora_mesh_sim.py','meshecho_cpr.py','meshecho_drc.py']},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'results':results,'status':'passed'}
output.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='results'},indent=2))
print(json.dumps([{k:v for k,v in x.items() if k not in {'exception','last_action'}} for x in results],indent=2))
