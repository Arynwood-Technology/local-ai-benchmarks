# Local AI benchmarks

How fast do local language models really run on ordinary hardware? This repository holds measured
[Ollama](https://ollama.com) generation speeds, CPU-only and on a GPU, and the script that produced
them, so you can test your own machine and add a data point.

**Write-up with advice on which model to start with:**
[Local AI without a GPU: how fast is it, really?](https://arynwood.com/local-ai-cpu-only.html)

## Results so far

| Machine | Model | CPU only | RTX 3060 | Speed-up | First answer, cold (CPU / GPU) |
|---|---|---|---|---|---|
| Xeon E5-2665 (2012), no AVX2 | TinyLlama 1.1B (Q4_0) | 27.1 tok/s | 197.4 tok/s | 7.3× | 10.2 s / 2.7 s |
| same | Llama 3.2 3B (Q4_K_M) | 12.8 tok/s | 77.7 tok/s | 6.1× | 18.5 s / 5.6 s |
| same | Qwen2.5 7B Instruct (Q4_K_M) | 6.4 tok/s | 48.9 tok/s | 7.6× | 31.3 s / 5.6 s |

Warm speed is the median of three runs with 200-token answers. A token is roughly three-quarters of a
word, and most people read about 5 tokens per second. Raw data is in [`results/`](results/).

One machine is one data point. A modern CPU with AVX2 or AVX-512 and faster memory will beat these CPU
numbers, often by a wide margin. That's why more machines are wanted.

## Test your own machine

You need Python 3.8+ and a running Ollama. The script has no other dependencies.

```bash
curl -O https://raw.githubusercontent.com/Arynwood-Technology/local-ai-benchmarks/main/bench.py
ollama pull llama3.2:3b
python3 bench.py llama3.2:3b --csv my-results.csv
```

No NVIDIA GPU? Add `--modes cpu`. Testing several models:
`python3 bench.py tinyllama llama3.2:3b qwen2.5:7b-instruct --csv my-results.csv`

The script prints your hardware and one line per model and mode:

```
Intel(R) Xeon(R) CPU E5-2665 0 @ 2.40GHz · 63 GB RAM · NVIDIA GeForce RTX 3060, 12288 MiB · Ubuntu 24.04.5 LTS · Ollama 0.11.4

tinyllama:latest             cpu    29.3 tokens/s warm     9.0 s cold   0.7 GB
tinyllama:latest             gpu   197.6 tokens/s warm     2.9 s cold   1.3 GB
```

(That sample used one warm run; the published numbers use three.)

## Share your results

[Open a results issue](https://github.com/Arynwood-Technology/local-ai-benchmarks/issues/new?template=submit-results.yml)
and paste your CSV. Submissions are added to `results/` with the credit you choose.

## Method

- Prompt: "Explain in about 150 words why someone might run a language model locally."
- Temperature 0, a fixed seed and answers capped at 200 tokens (`num_predict`).
- One cold run with the model unloaded, then warm runs. The warm number is the median eval rate
  (`eval_count / eval_duration`); the cold number is the total time for the first answer, including load.
- CPU-only runs set `num_gpu` to 0, which puts no model layers on the GPU. The model is unloaded between modes.
- Memory is what Ollama reports in `/api/ps`: RAM in CPU mode, VRAM in GPU mode.

Longer prompts and longer conversations are slower, because the model processes everything already in
the context. These numbers are for short answers to a short prompt.

## Licenses and citing

- **Results data** (`results/`): [CC BY 4.0](results/LICENSE). Credit "Arynwood" and link to
  https://arynwood.com/local-ai-cpu-only.html.
- **bench.py**: [MIT](LICENSE).
- Citation details are in [CITATION.cff](CITATION.cff).

---

From [Arynwood Technology](https://arynwood.com/). Want local AI set up on your own machine?
See [Arynwood MCP](https://arynwood.com/mcp/) and [local AI setup services](https://arynwood.com/#services).
