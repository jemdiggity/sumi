#!/usr/bin/env python3
"""Bounded disposable JJ/Codex concurrency probe; no third-party Python modules."""
import argparse, concurrent.futures, hashlib, json, os, shutil, signal, subprocess, time
from pathlib import Path
from datetime import datetime, timezone

def stamp(): return datetime.now(timezone.utc).isoformat()
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix('.tmp');t.write_text(json.dumps(d,indent=2)+'\n');os.replace(t,p)
def cmd(args,cwd):return subprocess.check_output(args,cwd=cwd,text=True,stderr=subprocess.STDOUT).strip()
def jj(args,cwd):return cmd(['jj','--config','user.name="Sumi pilot"','--config','user.email="pilot@localhost"',*args],cwd)
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--registry',type=Path,required=True);p.add_argument('--arms',default='3,1,6');p.add_argument('--limit',type=int,default=300);a=p.parse_args()
 root=a.output.resolve();root.mkdir(exist_ok=False);source=a.source.read_text();fixtures=json.loads(Path(__file__).with_name('fixtures.json').read_text());write(root/'fixtures.json',fixtures)
 repo=root/'repo';jj(['git','init','--no-colocate',str(repo)],root)
 (repo/'index.html').write_text('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Sumi pool pilot</title><style>body{margin:24px;font-family:system-ui}#sumi-workspace{max-width:1240px;margin:auto}</style></head><body>'+source+'</body></html>')
 (repo/'AGENTS.md').write_text('Disposable parallel UI feedback worker. Edit only index.html in this workspace. Do not run git/jj mutations, install packages, access network, read other workspaces, or start other agents. Implement only the assigned feedback. Preserve existing mockup behavior. No actual merges or task launches occur in the mockup. Leave changes for coordinator snapshot and review.\n')
 jj(['describe','-m','Frozen mockup for concurrency pilot'],repo);base=jj(['log','-r','@','--no-graph','-T','commit_id'],repo)
 metadata=dict(started_at=stamp(),baseline=base,source_sha256=hashlib.sha256(source.encode()).hexdigest(),model='gpt-6-luna',effort='medium',jj=cmd(['jj','--version'],root),codex=cmd(['codex','--version'],root),arms=[]);write(root/'experiment.json',metadata)
 for slots in map(int,a.arms.split(',')):
  arm=root/f'pool-{slots}';arm.mkdir();jobs=[]
  for f in fixtures:
   ws=arm/f['id'];jj(['workspace','add','--name',f'p{slots}-{f["id"]}','-r',base,str(ws)],repo)
   jobs.append((f,ws))
  started=time.monotonic();epoch=stamp()
  def work(job):
   f,ws=job;runid=f'pool-{root.name}-{slots}-{f["id"]}';d=a.registry.resolve()/runid;d.mkdir(parents=True,exist_ok=False)
   prompt=f"Implement this synthetic review comment in index.html.\n{f['comment']}\nAcceptance: {f['criteria']}\nKeep the quiet visual style. Do not implement other features. Perform lightweight relevant checks using available tools; do not install dependencies. Finish with a brief change/verification report.\n"
   (d/'prompt.md').write_text(prompt)
   record=dict(id=runid,task_id='LF-29',agent='codex',model='gpt-6-luna',effort='medium',state='running',workspace_session='sumi-zellij',created_at=stamp(),pid=os.getpid(),worktree=str(ws),directory=str(d),started_at=stamp(),queue_seconds=round(time.monotonic()-started,3),fixture=f['id'])
   args=['codex','-a','never','exec','--ignore-user-config','--skip-git-repo-check','-s','workspace-write','--json','--model','gpt-6-luna','-c','model_reasoning_effort="medium"','-c','features.multi_agent=false','-o',str(d/'result.md'),'-'];record['command']=args;write(d/'run.json',record)
   env=dict(os.environ)
   for k in ['ZELLIJ','ZELLIJ_SESSION_NAME','ZELLIJ_PANE_ID','TMUX','TMUX_PANE']:env.pop(k,None)
   t=time.monotonic()
   with (d/'events.jsonl').open('w') as out,(d/'stderr.log').open('w') as err:
    proc=subprocess.Popen(args,cwd=ws,env=env,stdin=subprocess.PIPE,stdout=out,stderr=err,text=True,start_new_session=True);record['child_pid']=proc.pid;write(d/'run.json',record)
    try:proc.communicate(prompt,timeout=a.limit)
    except subprocess.TimeoutExpired:
     record['timed_out']=True;os.killpg(proc.pid,signal.SIGTERM)
     try:proc.wait(timeout=3)
     except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   for line in (d/'events.jsonl').read_text().splitlines():
    try:e=json.loads(line)
    except ValueError:continue
    if e.get('type')=='thread.started':record['session_id']=e['thread_id']
    if e.get('type')=='turn.completed':record['usage_cumulative']=e.get('usage')
   record.update(exit_code=proc.returncode,state='exited' if proc.returncode==0 else 'failed',finished_at=stamp(),elapsed_seconds=round(time.monotonic()-t,3),completion_seconds=round(time.monotonic()-started,3));write(d/'run.json',record)
   print(json.dumps({k:record.get(k) for k in ['id','state','elapsed_seconds','completion_seconds','usage_cumulative']}),flush=True);return record
  with concurrent.futures.ThreadPoolExecutor(max_workers=slots) as pool:records=list(pool.map(work,jobs))
  elapsed=round(time.monotonic()-started,3)
  # Serialize repo mutations; each worker edits a distinct working copy.
  changes=[]
  for f,ws in jobs:
   jj(['describe','-m',f"Pool {slots}: {f['id']} {f['comment']}"],ws)
   changes.append(jj(['log','-r','@','--no-graph','-T','commit_id'],ws))
  combined=arm/'combined';jj(['workspace','add','--name',f'p{slots}-combined',*[x for c in changes for x in ['-r',c]],str(combined)],repo)
  conflicts=jj(['resolve','--list'],combined)
  result=dict(slots=slots,started_at=epoch,elapsed_seconds=elapsed,runs=records,changes=changes,combined=str(combined),conflicts=conflicts)
  write(arm/'results.json',result);metadata['arms'].append(result);write(root/'experiment.json',metadata)
  print(f'POOL {slots} COMPLETE: {elapsed}s; conflicts: {conflicts or "none"}',flush=True)
 metadata['finished_at']=stamp();write(root/'experiment.json',metadata)
if __name__=='__main__':main()
