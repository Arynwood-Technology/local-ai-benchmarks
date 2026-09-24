#!/usr/bin/env python3
"""Measure Ollama generation speed on your own machine, CPU-only and on the GPU.

Method (the one behind https://arynwood.com/local-ai-cpu-only.html):
same prompt, temperature 0, a fixed seed and answers capped at 200 tokens.
Each model gets one cold run (model not loaded) and then warm runs; the warm
speed reported is the median. CPU-only runs set num_gpu to 0, which puts no
model layers on the GPU. The model is unloaded between modes.

Needs Python 3.8+ and a running Ollama (http://localhost:11434). No other
dependencies. Pull the models first, for example: ollama pull llama3.2:3b

    python3 bench.py llama3.2:3b
    python3 bench.py tinyllama llama3.2:3b qwen2.5:7b-instruct --modes cpu,gpu --runs 3
    python3 bench.py llama3.2:3b --csv my-results.csv
"""
import argparse
import csv
import datetime
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import urllib.error
import urllib.request

PROMPT = 'Explain in about 150 words why someone might run a language model locally.'
SEED = 42  # fixes the answer text; it has no effect on speed
FIELDS = ['date', 'cpu', 'ram_gb', 'gpu', 'os', 'ollama_version', 'model', 'quantization', 'mode',
          'warm_tokens_per_s', 'cold_seconds', 'memory_gb', 'gpu_share_pct', 'warm_runs', 'num_predict']


def api(host, path, body=None, timeout=900):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(host + path, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def unload(host, model):
    api(host, '/api/generate', {'model': model, 'keep_alive': 0})


def generate(host, model, mode, num_predict):
    options = {'temperature': 0, 'seed': SEED, 'num_predict': num_predict}
    if mode == 'cpu':
        options['num_gpu'] = 0
    return api(host, '/api/generate', {'model': model, 'prompt': PROMPT, 'stream': False, 'options': options})


def loaded_memory(host, model):
    """Total memory Ollama reports for the loaded model (GB) and the share of it on the GPU (%)."""
    wanted = {model, model if ':' in model else model + ':latest'}
    for m in api(host, '/api/ps').get('models', []):
        if m.get('name') in wanted or m.get('model') in wanted:
            size = m.get('size', 0)
            return round(size / 1e9, 1), (round(100 * m.get('size_vram', 0) / size) if size else 0)
    return '', ''


def read_first(path, pattern):
    try:
        with open(path) as f:
            for line in f:
                m = re.match(pattern, line)
                if m:
                    return m.group(1).strip()
    except OSError:
        pass
    return ''


def hardware():
    cpu = read_first('/proc/cpuinfo', r'model name\s*:\s*(.*)') or platform.processor() or platform.machine()
    mem_kb = read_first('/proc/meminfo', r'MemTotal:\s*(\d+)')
    ram = round(int(mem_kb) / 1024 / 1024) if mem_kb else ''
    gpu = ''
    if shutil.which('nvidia-smi'):
        try:
            out = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                                 capture_output=True, text=True, timeout=10).stdout.strip().splitlines()
            gpu = out[0] if out else ''
        except (OSError, subprocess.SubprocessError):
            pass
    os_name = read_first('/etc/os-release', r'PRETTY_NAME="?([^"\n]*)') or f'{platform.system()} {platform.release()}'
    return {'cpu': re.sub(r'\s+', ' ', cpu), 'ram_gb': ram, 'gpu': gpu, 'os': os_name}


def quantization(host, model):
    try:
        return api(host, '/api/show', {'model': model}).get('details', {}).get('quantization_level', '')
    except urllib.error.HTTPError:
        return ''


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('models', nargs='+', help='Ollama model names, already pulled')
    ap.add_argument('--modes', default='cpu,gpu', help='cpu, gpu or cpu,gpu (default cpu,gpu)')
    ap.add_argument('--runs', type=int, default=3, help='warm runs per model and mode (default 3)')
    ap.add_argument('--num-predict', type=int, default=200, help='answer length cap in tokens (default 200)')
    ap.add_argument('--host', default=os.environ.get('OLLAMA_HOST', 'http://localhost:11434'))
    ap.add_argument('--csv', help='append results to this CSV file')
    args = ap.parse_args()
    host = args.host if args.host.startswith('http') else 'http://' + args.host
    modes = [m.strip() for m in args.modes.split(',') if m.strip() in ('cpu', 'gpu')]

    try:
        version = api(host, '/api/version').get('version', '')
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f'Could not reach Ollama at {host}: {e}. Is it running?')
    hw = hardware()
    if 'gpu' in modes and not hw['gpu']:
        print('No NVIDIA GPU found with nvidia-smi; GPU-mode numbers may be CPU speed.', file=sys.stderr)
    print(f"{hw['cpu']} · {hw['ram_gb']} GB RAM · {hw['gpu'] or 'no NVIDIA GPU'} · {hw['os']} · Ollama {version}\n")

    rows = []
    for model in args.models:
        quant = quantization(host, model)
        for mode in modes:
            unload(host, model)
            cold = generate(host, model, mode, args.num_predict)
            cold_s = round(cold['total_duration'] / 1e9, 1)
            memory, share = loaded_memory(host, model)
            speeds = []
            for _ in range(args.runs):
                r = generate(host, model, mode, args.num_predict)
                speeds.append(r['eval_count'] / r['eval_duration'] * 1e9)
            warm = round(statistics.median(speeds), 1)
            rows.append({'date': datetime.date.today().isoformat(), **hw, 'ollama_version': version, 'model': model,
                         'quantization': quant, 'mode': mode, 'warm_tokens_per_s': warm, 'cold_seconds': cold_s,
                         'memory_gb': memory, 'gpu_share_pct': share, 'warm_runs': args.runs, 'num_predict': args.num_predict})
            where = '' if mode == 'cpu' or share in ('', 100) else f'   ({100 - share}% CPU / {share}% GPU)'
            print(f'{model:28} {mode:3}  {warm:6} tokens/s warm   {cold_s:5} s cold   {memory} GB{where}')
        unload(host, model)

    if args.csv:
        new = not os.path.exists(args.csv)
        with open(args.csv, 'a', newline='') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerows(rows)
        print(f'\nSaved to {args.csv}')
    print('\nShare your results: https://github.com/Arynwood-Technology/local-ai-benchmarks/issues/new?template=submit-results.yml')


if __name__ == '__main__':
    main()
