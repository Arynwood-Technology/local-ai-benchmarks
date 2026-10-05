#!/usr/bin/env python3
"""Run this repository's tests in a temporary, loopback-only Ollama instance.

Copy next to bench.py and tool_calling.py on the target machine. Output contains
hardware and model names, never hostnames, addresses, usernames or model digests.
Existing Ollama services and models are left alone. Downloads use the current
user's model store. Inference uses three threads and a 4096-token context.
"""
import csv
import datetime
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import threading
import time

import bench
import tool_calling

MODELS = ['llama3.2:1b', 'gemma3:1b', 'granite3.3:2b',
          'gemma:2b-instruct-q4_0', 'llama3.2:3b']
HOST = 'http://localhost:11435'
CTX = 4096
THREADS = 3
SWAP_LIMIT_MIB = 256


def memory():
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        values[key] = int(value.split()[0]) * 1024
    return values['MemAvailable'], values['SwapTotal'] - values['SwapFree']


class FlushingWriter(csv.DictWriter):
    def __init__(self, stream, **kwargs):
        super().__init__(stream, **kwargs)
        self.stream = stream

    def writerow(self, row):
        result = super().writerow(row)
        self.stream.flush()
        return result


def main():
    global MODELS
    if os.environ.get('BENCH_MODELS'):
        MODELS = os.environ['BENCH_MODELS'].split(',')
    os.chdir(Path(__file__).resolve().parent)
    baseline_swap = memory()[1]
    stop = threading.Event()
    abort = threading.Event()
    samples = []
    env = {**os.environ, 'OLLAMA_HOST': HOST, 'OLLAMA_NUM_PARALLEL': '1',
           'OLLAMA_MAX_LOADED_MODELS': '1', 'OLLAMA_CONTEXT_LENGTH': str(CTX),
           'OLLAMA_KEEP_ALIVE': '0', 'OLLAMA_MODELS': str(Path.home()/'.ollama/models')}
    # Refuse to take over an existing listener.
    import socket
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(('localhost', 11435))
    process = subprocess.Popen([os.environ.get('BENCH_OLLAMA_BINARY', 'ollama'), 'serve'], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=True, preexec_fn=lambda: os.nice(15))

    def terminate():
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)

    def monitor():
        while not stop.wait(2):
            available, swap = memory()
            samples.append({'available_gib': round(available/1024**3, 3),
                            'swap_growth_mib': round((swap-baseline_swap)/1024**2, 1),
                            'load1': os.getloadavg()[0]})
            if available < 1.5*1024**3 or (
                available < 2*1024**3 and swap-baseline_swap > SWAP_LIMIT_MIB*1024**2
            ):
                abort.set()
                terminate()
                print('STOPPED: memory reserve or swap-growth limit reached', flush=True)
                return

    original_api = bench.api

    def bounded_api(host, path, body=None, timeout=900):
        if abort.is_set():
            raise RuntimeError('Resource limit reached')
        if body is not None and path in ('/api/generate', '/api/chat'):
            body = dict(body)
            body['options'] = {**body.get('options', {}), 'num_ctx': CTX,
                               'num_thread': THREADS, 'num_gpu': 0}
            if body.get('keep_alive') != 0:
                body['keep_alive'] = '5m'
        return original_api(host, path, body, timeout)

    bench.api = bounded_api
    watchdog = threading.Thread(target=monitor, daemon=True)
    watchdog.start()
    summaries = []
    failures = []
    ready = []
    try:
        for _ in range(60):
            try:
                version = bench.api(HOST, '/api/version')['version']
                break
            except Exception:
                if process.poll() is not None:
                    raise RuntimeError('Temporary Ollama exited')
                time.sleep(1)
        else:
            raise RuntimeError('Temporary Ollama failed to start')
        hw = bench.hardware()
        hw['gpu'] = 'none (CPU-only virtual server)'
        machine = {'date': datetime.date.today().isoformat(), **hw, 'ollama_version': version}
        print(json.dumps(machine), flush=True)
        with open('speed.csv', 'w', newline='') as out:
            fields = bench.FIELDS + ['num_ctx', 'num_thread']
            writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
            writer.writeheader()
            out.flush()
            for model in MODELS:
                print('PREPARING', model, flush=True)
                try:
                    if os.environ.get('BENCH_SKIP_PULL') != '1':
                        bench.api(HOST, '/api/pull', {'model': model, 'stream': False})
                    details = bench.api(HOST, '/api/show', {'model': model})
                    speed_models = os.environ.get('BENCH_SPEED_MODELS', '').split(',')
                    if os.environ.get('BENCH_TOOLS_ONLY') == '1' or (
                        os.environ.get('BENCH_SPEED_MODELS') and model not in speed_models
                    ):
                        if 'tools' in details.get('capabilities', []):
                            ready.append(model)
                        continue
                    bench.unload(HOST, model)
                    cold = bench.generate(HOST, model, 'cpu', 200)
                    size, share = bench.loaded_memory(HOST, model)
                    speeds = []
                    for _ in range(3):
                        result = bench.generate(HOST, model, 'cpu', 200)
                        speeds.append(result['eval_count']/result['eval_duration']*1e9)
                    row = {**machine, 'model': model,
                           'quantization': details.get('details', {}).get('quantization_level', ''),
                           'mode': 'cpu', 'warm_tokens_per_s': round(statistics.median(speeds), 1),
                           'cold_seconds': round(cold['total_duration']/1e9, 1),
                           'memory_gb': size, 'gpu_share_pct': share, 'warm_runs': 3,
                           'num_predict': 200, 'num_ctx': CTX, 'num_thread': THREADS}
                    writer.writerow(row)
                    out.flush()
                    print('SPEED', json.dumps(row), flush=True)
                    if 'tools' in details.get('capabilities', []):
                        ready.append(model)
                except Exception as exc:
                    failures.append({'model': model, 'stage': 'speed', 'error_type': type(exc).__name__})
                    print('FAILED', model, type(exc).__name__, flush=True)
                    if abort.is_set():
                        break
                finally:
                    if not abort.is_set():
                        bench.unload(HOST, model)
        if not abort.is_set():
            fields = list(machine) + ['model', 'quantization', 'num_ctx', 'case', 'category',
                                      'run', 'passed', 'tools_called', 'call_format', 'seconds', 'reply']
            with open('tools.csv', 'w', newline='') as out:
                writer = FlushingWriter(out, fieldnames=fields, lineterminator='\n')
                writer.writeheader()
                for model in ready:
                    print('TOOLS', model, flush=True)
                    try:
                        summary = tool_calling.run_model(HOST, model, 3, CTX, 512, machine, writer)
                        summaries.append(summary)
                        print('TOOL_RESULT', json.dumps(summary), flush=True)
                    except Exception as exc:
                        failures.append({'model': model, 'stage': 'tools', 'error_type': type(exc).__name__})
                        print('FAILED', model, type(exc).__name__, flush=True)
                    finally:
                        out.flush()
                        Path('tool-summary.json').write_text(json.dumps(summaries, indent=2)+'\n')
                    if abort.is_set():
                        break
    finally:
        stop.set()
        watchdog.join(timeout=3)
        terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        Path('run-status.json').write_text(json.dumps({
            'aborted': abort.is_set(), 'failures': failures, 'models': MODELS,
            'num_ctx': CTX, 'num_thread': THREADS, 'tool_num_predict': 512,
            'swap_growth_limit_mib': SWAP_LIMIT_MIB,
            'swap_guard_requires_available_below_gib': 2,
            'minimum_available_gib': min((s['available_gib'] for s in samples), default=None),
            'maximum_swap_growth_mib': max((s['swap_growth_mib'] for s in samples), default=None),
            'maximum_load1': max((s['load1'] for s in samples), default=None),
            'temporary_ollama_stopped': process.poll() is not None}, indent=2)+'\n')
        print('FINISHED', flush=True)


if __name__ == '__main__':
    main()
