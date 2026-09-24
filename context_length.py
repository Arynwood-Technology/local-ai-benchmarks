"""Memory Ollama reserves for one model at different context lengths (num_ctx). Usage: python3 context_length.py [model]"""
import csv, subprocess, sys, time
import bench
HOST = 'http://localhost:11434'
MODEL = sys.argv[1] if len(sys.argv) > 1 else 'qwen2.5:7b-instruct'
rows = []
for ctx in (2048, 4096, 8192, 16384, 32768):
    bench.unload(HOST, MODEL); time.sleep(4)
    bench.api(HOST, '/api/generate', {'model': MODEL, 'prompt': 'Say OK.', 'stream': False,
                                      'options': {'num_ctx': ctx, 'num_predict': 5, 'temperature': 0}})
    m = [x for x in bench.api(HOST, '/api/ps')['models'] if x['name'] == MODEL][0]
    ps = subprocess.run(['ollama', 'ps'], capture_output=True, text=True).stdout
    line = [l for l in ps.splitlines() if l.startswith(MODEL)][0]
    proc = '100% GPU' if '100% GPU' in line else ('100% CPU' if '100% CPU' in line else line.split('GB')[1].strip().split('   ')[0].strip())
    rows.append({'num_ctx': ctx, 'total_gb': round(m['size'] / 1e9, 1), 'vram_gb': round(m['size_vram'] / 1e9, 1), 'processor': proc})
    print(rows[-1], flush=True)
bench.unload(HOST, MODEL)
with open('context-length.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print('Saved to context-length.csv')
