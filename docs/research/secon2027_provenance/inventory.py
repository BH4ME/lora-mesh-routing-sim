#!/usr/bin/env python3
"""Read-only historical seed inventory. Does not import/run simulation code."""
import ast
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path('/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2')
OUT = Path(__file__).resolve().parent
numeric_seed = re.compile(rb'"(?:seed|topology_seed|traffic_seed|channel_seed|protocol_seed)"\s*:\s*(-?\d+)')
seed_range = re.compile(r'(?<!\d)(\d{1,7})\s*(?:--|\.\.|–|—|-)\s*(\d{1,7})(?!\d)')
seed_wildcard = re.compile(r'(?<![A-Za-z0-9])(\d{2,5})([xX]{2,3})(?![A-Za-z0-9])')
records = []
errors = []
all_artifact_seeds = set()
evidence_paths = set()

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def extract_json(obj, found, key=''):
    if isinstance(obj, dict):
        for k,v in obj.items():
            if k in ('seed','seeds','development_seeds','holdout_seeds','smoke_seeds','exploratory_seeds'):
                vals = v if isinstance(v,list) else [v]
                for val in vals:
                    if isinstance(val,int) and not isinstance(val,bool): found.add(val)
            extract_json(v, found, k)
    elif isinstance(obj,list):
        for item in obj: extract_json(item, found, key)

paths = sorted((ROOT/'results').rglob('*'))
for path in paths:
    if not path.is_file() or path.suffix not in ('.json','.jsonl','.csv'): continue
    found=set()
    rel=str(path.relative_to(ROOT))
    try:
        if path.suffix=='.json':
            extract_json(json.loads(path.read_text()), found)
        elif path.suffix=='.jsonl':
            with path.open('rb') as f:
                for line in f:
                    found.update(int(x) for x in numeric_seed.findall(line))
        else:
            with path.open(newline='') as f:
                reader=csv.DictReader(f)
                fields=[k for k in (reader.fieldnames or []) if k=='seed' or k.endswith('_seed')]
                if fields:
                    for row in reader:
                        for k in fields:
                            if row.get(k) and re.fullmatch(r'-?\d+', row[k]): found.add(int(row[k]))
        if found:
            all_artifact_seeds.update(found)
            records.append({'path':rel,'sha256':sha(path),'size_bytes':path.stat().st_size,'seeds':sorted(found),'status':'exposed','invalidated_artifact':'invalid_' in rel})
            if path.name.endswith(('.manifest.json','.authorization.json')) or path.suffix=='.csv': evidence_paths.add(rel)
    except Exception as exc:
        errors.append({'path':rel,'error':str(exc)})

mentions=[]
text_paths = sorted(set(list((ROOT/'docs').rglob('*.md')) + list((ROOT/'docs').rglob('*.authorization.json')) + [ROOT/x for x in ('task_plan.md','findings.md','progress.md')]))
for path in text_paths:
    text=path.read_text(errors='replace')
    lines=text.splitlines()
    for n,line in enumerate(lines):
        context=' '.join(lines[max(0,n-2):min(len(lines),n+3)])
        if not re.search('seed|cohort|种子|保留|unopened|sealed',context,re.I): continue
        intervals=[]
        for match in seed_range.finditer(line):
            low,high=map(int,match.groups())
            if high>=low and high-low<=10000: intervals.append([low,high])
        for match in seed_wildcard.finditer(line):
            base=int(match.group(1))*10**len(match.group(2))
            intervals.append([base,base+10**len(match.group(2))-1])
        if intervals:
            rel=str(path.relative_to(ROOT))
            mentions.append({'path':rel,'line':n+1,'ranges':intervals,'text':line.strip()[:700],
                             'reservation_language':bool(re.search('unopened|sealed|closed|reserved|reserve|untouched|保留|关闭',context,re.I))})
            evidence_paths.add(rel)

def compress(vals):
    ranges=[]
    for x in sorted(vals):
        if ranges and x==ranges[-1][1]+1: ranges[-1][1]=x
        else:ranges.append([x,x])
    return ranges

result={
  'schema':'secon2027-historical-seed-inventory-v1',
  'source_root':str(ROOT),
  'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  'method':'Read every result JSON/JSONL/CSV seed field; extract seed-context numeric ranges and wildcards from docs and root logs. No simulator imported or executed. Artifact existence takes precedence over old untouched labels.',
  'artifact_count':len(records),'artifact_seed_count':len(all_artifact_seeds),
  'artifact_exposed_ranges':compress(all_artifact_seeds),
  'artifacts':records,'document_mentions':mentions,'scan_errors':errors,
  'proposed_conservative_exclusion':{'start':0,'end':999999,'status':'retired_for_secon2027','reason':'Namespace fence avoids all historical low-number cohorts including reserved, partially exposed, invalidated and ambiguous labels; does not assert every integer was run.'},
  'proposed_development_seeds':[2027000,2027001,2027002],
  'proposal_only':True,
  'new_development_overlap_with_artifacts': sorted({2027000,2027001,2027002}&all_artifact_seeds),
  'new_development_overlap_with_mentions': [m for m in mentions if any(a<=s<=b for a,b in m['ranges'] for s in [2027000,2027001,2027002])],
  'preserve_evidence':[{'path':p,'sha256':sha(ROOT/p),'size_bytes':(ROOT/p).stat().st_size} for p in sorted(evidence_paths)],
}
(OUT/'historical_seed_inventory.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:result[k] for k in ('artifact_count','artifact_seed_count','artifact_exposed_ranges','scan_errors','new_development_overlap_with_artifacts','new_development_overlap_with_mentions')},indent=2))

# Static local import dependency closure for experiment entrypoints.
pending=['tools/run_cpr_experiment.py','tools/run_cpr_external_comparison.py','tools/audit_cpr_population.py']
closure=set()
while pending:
    rel=pending.pop()
    if rel in closure:continue
    closure.add(rel)
    tree=ast.parse((ROOT/rel).read_text())
    for node in ast.walk(tree):
        names=[]
        if isinstance(node,ast.Import): names=[n.name for n in node.names]
        elif isinstance(node,ast.ImportFrom):
            if node.module:names=[node.module]+[node.module+'.'+n.name for n in node.names]
        for name in names:
            mod=name.replace('.','/')
            for candidate in (mod+'.py',mod+'/__init__.py'):
                if (ROOT/candidate).is_file() and candidate not in closure:pending.append(candidate)
(OUT/'dependency_closure.json').write_text(json.dumps({'entrypoints':['tools/run_cpr_experiment.py','tools/run_cpr_external_comparison.py','tools/audit_cpr_population.py'],'local_python_dependencies':[{'path':p,'sha256':sha(ROOT/p)} for p in sorted(closure)]},indent=2)+'\n')
