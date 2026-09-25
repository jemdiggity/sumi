#!/usr/bin/env python3
"""Recheck each frozen candidate and summarize measured queue behavior."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('experiment',type=Path);p.add_argument('--dom-module',type=Path,required=True);a=p.parse_args()
data=json.loads((a.experiment/'experiment.json').read_text());summary=[]
for arm in data['arms']:
 checks=[]
 for run in arm['runs']:
  process=subprocess.run(['node',str(Path(__file__).with_name('check.mjs')),str(a.dom_module.resolve()),str(Path(run['worktree'])/'index.html'),run['fixture']],capture_output=True,text=True)
  try:results=json.loads(process.stdout)
  except ValueError:results=[{'pass':False,'error':process.stderr or process.stdout}]
  checks.append({'fixture':run['fixture'],'checks':results,'completed_at_seconds':run['completion_seconds']})
 usage={k:sum(r.get('usage_cumulative',{}).get(k,0) for r in arm['runs']) for k in ['input_tokens','cached_input_tokens','output_tokens','reasoning_output_tokens']}
 valid=[c['completed_at_seconds'] for c in checks if all(x['pass'] for x in c['checks'])]
 summary.append(dict(slots=arm['slots'],batch_seconds=arm['elapsed_seconds'],first_worker_seconds=min(r['completion_seconds'] for r in arm['runs']),first_passing_candidate_seconds=min(valid) if valid else None,passing_candidates=len(valid),usage=usage,initial_conflicts=arm['conflicts'],checks=checks))
(a.experiment/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
