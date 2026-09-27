#!/usr/bin/env python3
"""Development-only benchmark; no agent calls or dependencies beyond Python stdlib."""
import json
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import sys
import tempfile
import time

root = Path(__file__).resolve().parents[1]
native = Path(sys.argv[1]).resolve()
engines = {'python': [sys.executable, str(root / 'bin/sumi')], 'rust': [str(native)]}
repetitions = 30
result = {'machine': platform.platform(), 'architecture': platform.machine(),
          'python': sys.version.split()[0], 'rust': subprocess.check_output(['rustc', '--version'], text=True).strip(),
          'build': 'cargo --release, LTO, stripped', 'repetitions': repetitions,
          'method': '2 warmups then 30 sequential subprocess runs; warm filesystem cache; median and nearest-rank p95 wall time in ms. Idle RSS/%CPU: ten ps samples 200ms apart after 1s settle. %CPU is the OS ps lifetime estimate, not instantaneous.',
          'binary_bytes': native.stat().st_size, 'engines': {}}
with tempfile.TemporaryDirectory(prefix='sumi benchmark ') as tmp:
    project = Path(tmp)
    for name, engine in engines.items():
        results = result['engines'][name] = {}
        def measure(args):
            timings = []
            for i in range(repetitions + 2):
                start = time.perf_counter()
                subprocess.run(engine + args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if i >= 2: timings.append((time.perf_counter() - start) * 1000)
            return {'median_ms': round(statistics.median(timings), 3), 'p95_ms': round(sorted(timings)[28], 3)}
        results['help'] = measure(['--help'])
        results['empty_list'] = measure(['--root', tmp, 'schedule', 'list'])
        # Fill 1,000 valid completed records using one real execution as the template.
        subprocess.run(engine + ['--root', tmp, 'schedule', 'add', 'bench', '--every', '1d', '--', '/bin/echo', 'bench'], check=True, stdout=subprocess.DEVNULL)
        run = json.loads(subprocess.check_output(engine + ['--root', tmp, 'schedule', 'run', 'bench'], text=True))
        runtime = project / '.sumi/schedule-runs'
        import shutil
        shutil.rmtree(runtime)
        for n in range(1000):
            record = dict(run, run_id=f'{n:032x}', started=run['started'] + n, ended=run['ended'] + n)
            directory = runtime / record['run_id']; directory.mkdir(parents=True)
            (directory / 'run.json').write_text(json.dumps(record))
        results['list_1000_records'] = measure(['--root', tmp, 'schedule', 'list'])
        # Idle sampling uses an empty project, without benchmarking repeated history scans.
        shutil.rmtree(project / '.sumi')
        p = subprocess.Popen(engine + ['--root', tmp, 'schedule', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            time.sleep(1)
            rss, cpu = [], []
            for _ in range(10):
                values = subprocess.check_output(['ps', '-p', str(p.pid), '-o', 'rss=', '-o', '%cpu='], text=True).split()
                rss.append(int(values[0])); cpu.append(float(values[1])); time.sleep(.2)
            results['idle_median_rss_kib'] = statistics.median(rss)
            results['idle_median_cpu_percent'] = statistics.median(cpu)
        finally:
            p.send_signal(signal.SIGINT); p.communicate(timeout=6)
        shutil.rmtree(project / '.sumi')
print(json.dumps(result, indent=2))
