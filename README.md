# Local AI benchmarks

How fast do local language models really run on ordinary hardware? This repository holds measured
[Ollama](https://ollama.com) generation speeds, CPU-only and on a GPU, and the script that produced
them, so you can test your own machine and add a data point.

**Write-up with advice on which model to start with:**
[Local AI without a GPU: how fast is it, really?](https://arynwood.com/local-ai-cpu-only.html)

## Results so far

### October 5, 2026 UTC: CPU-only web server, Ollama 0.15.2 versus 0.35.1

Four KVM vCPUs presented as a Xeon Gold 6138, 8 GB RAM, no compute GPU. Five US-developed
models, identical cached weights, three inference threads, 4,096-token context, one cold request
and three warm requests per version. The installed server version stayed unchanged; the second
round used a temporary 0.35.1 binary.

| Model | Quantization | 0.15.2 tok/s | 0.35.1 tok/s | Change |
|---|---|---:|---:|---:|
| Llama 3.2 1B (Meta) | Q8_0 | 7.2 | 5.0 | -30.6% |
| Gemma 3 1B (Google) | Q4_K_M | 9.3 | 5.8 | -37.6% |
| Granite 3.3 2B (IBM) | Q4_K_M | 3.7 | 2.8 | -24.3% |
| Gemma 2B (original) (Google) | Q4_0 | 3.3 | 3.1 | -6.1% |
| Llama 3.2 3B (Meta) | Q4_K_M | 2.8 | 2.5 | -10.7% |

Median per-model throughput change: **-24.3%**. Cold latency and tool behavior
are separate measurements. Tool scores out of 39 (old → new): Llama 3.2 1B 24 → 24; Granite 3.3 2B 21 → 27; Llama 3.2 3B 24 → 27.
Granite's higher score came with more unnecessary tool calls. The report includes category scores and an
injection-scoring limitation: plain-text deletion attempts can pass the recognized-call check.

[Full report, cold latencies, memory, tool categories and resource interruptions](SERVER-BENCHMARK.md).
[Public CPU guide](https://arynwood.com/local-ai-cpu-only.html). Raw data is in `results/`.
The versions ran sequentially on a shared server, so this is an observational comparison. Early swap
guards stopped runs with ample available RAM; the report records policy changes and untested candidates.
No server addresses, hostnames, accounts or provider identifiers are included.

### October 4, 2026: tool calling on an RTX 3060 12 GB

Which local model makes a personal agent's tool calls best on a 12 GB card? Models from US
companies against Qwen2.5 Coder 14B, on 13 generic tool cases (3 runs each) and Arynwood MCP's 36
live evals. Full write-up: [TOOL-CALLING.md](TOOL-CALLING.md).

| Model | Tool test (39) | Injection check passes | Arynwood evals (36) | Speed | Memory |
|---|---|---|---|---|---|
| Hermes 3 8B | 36 | 6/6 | 31 | 44.3 tok/s | 6.7 GB |
| Granite 3.3 8B | 33 | 6/6 | 31 | 43.3 tok/s | 7.8 GB |
| Phi-4-mini 3.8B | 30 | 6/6 | 28 | 56.7 tok/s | 4.7 GB |
| Qwen2.5 Coder 14B | 24 | 0/6 | 35 | 17.4 tok/s | 11.8 GB |
| Llama 3.2 3B | 24 | 6/6 | 23 | 67.6 tok/s | 4.0 GB |
| Llama 3.1 8B | 22 | 3/6 | 28 | 40.0 tok/s | 6.9 GB |
| Nemotron Mini 4B | 22 | 6/6 | 18 | 52.8 tok/s | 3.6 GB |
| Granite 4 3B | 21 | 3/6 | 26 | 62.2 tok/s | 3.9 GB |

gpt-oss 20B passed all 25 cases it finished, but needs about 16 GB at this context length and was
stopped.

**Round 2, Ollama 0.35.1:** Gemma 4 12B 36 / 6 of 6 / 35 (about 9 GB, but thinking adds about 4 s
to every routing step); Hermes 3 8B 36 / 6 of 6 / 32; Granite 3.3 8B 36 / 6 of 6 / 32; Nemotron 3
Nano 4B 33 / 3 of 6 / 32; Qwen2.5 Coder 14B 24 / 0 of 6 / 33. The same models ran about 40 to 65
percent faster than on 0.11.4. Details in [TOOL-CALLING.md](TOOL-CALLING.md#round-2-ollama-0351-gemma-4-and-nemotron-3-nano).

**Round 3, October 5: Cloudflare's Clef-flash decision model in the routing step.** No empty
answers and no planted instruction followed, deciding in 0.37 s against Gemma 4's 4.1 s. But it
got 26 of Arynwood's 30 decisions (Gemma 4 and Nemotron 3 Nano got 30, Hermes 3 27), and it needs
10.7 GB at its only Ollama quantization, too much to share the card. Hermes 3 stays. Details in
[TOOL-CALLING.md](TOOL-CALLING.md#round-3-a-decision-model-clef-flash-for-the-routing-step-october-5-2026).

**Round 4, October 9: JetBrains' Mellum2.1 and Liquid AI's d1 decision models.** Mellum2.1 (12B
with 2.5B active, thinking) got 33 of Arynwood's 36 evals, behind only Gemma 4, at 138 tok/s in
8.2 GB with a 1.3 s routing call. But it called `delete_clip` from a planted web page in every run,
and returned empty replies when thinking used up the reply limit. d1-3B made 25 of 30 decisions
(Clef-flash 26) in 42 ms and 3.6 GB, and followed no planted instruction. d1-omni-600M made 18 of
30 and followed the planted clip name. Ollama doesn't serve the d1 models yet, so they ran on
llama.cpp b11524. Hermes 3 stays; d1-3B is small enough to share the card with it as a check
before destructive actions, still to be tested. Details in
[TOOL-CALLING.md](TOOL-CALLING.md#round-4-mellum21-and-liquid-ais-d1-decision-models-october-9-2026);
written up in [Are Mellum2.1 and Liquid's d1 models good for a local AI agent?](https://arynwood.com/mellum-2-1-liquid-d1-benchmark/)

### September 24, 2026: 3B to 33B on an RTX 3060 12 GB

| Model | Memory | RTX 3060 | CPU only |
|---|---|---|---|
| Llama 3.2 3B (Q4_K_M) | 3.3 GB | 77.9 tok/s (all on GPU) | 12.8 tok/s |
| Qwen2.5 7B Instruct (Q4_K_M) | 5.6 GB | 49.0 tok/s (all on GPU) | 6.4 tok/s |
| Mistral 7B (Q4_K_M) | 5.8 GB | 57.8 tok/s (all on GPU) | not run |
| Llama 3 8B Instruct (Q4_0) | 5.8 GB | 50.3 tok/s (all on GPU) | not run |
| Hermes 3 8B (Q4_0) | 5.8 GB | 49.9 tok/s (all on GPU) | 5.7 tok/s |
| Qwen2.5 Coder 14B (Q4_K_M) | 10.4 GB | 28.5 tok/s (all on GPU) | 3.5 tok/s |
| gpt-oss 20B (MXFP4) | 14.9 GB | 6.5 tok/s (27% CPU / 73% GPU) | 2.4 tok/s |
| DeepSeek Coder 33B (Q4_0) | 21.1 GB | 2.7 tok/s (47% CPU / 53% GPU) | 1.5 tok/s |

Models up to 14B fit on the card; larger ones split between GPU and system RAM, which is much slower. About 1.2 GB of
the card was already in use by the desktop and a Stable Diffusion web UI. Written up in
[What can an RTX 3060 12GB run?](https://arynwood.com/rtx-3060-12gb-local-llm/) and
[How much VRAM does a local LLM need?](https://arynwood.com/llm-vram-requirements/)

Memory for Qwen2.5 7B at different context lengths (`num_ctx`), all 100% on the GPU: 2,048 tokens 5.4 GB, 4,096 tokens 5.6 GB, 8,192 tokens 6.0 GB, 16,384 tokens 7.0 GB, 32,768 tokens 8.9 GB.

### September 22, 2026: CPU only vs RTX 3060

| Machine | Model | CPU only | RTX 3060 | Speed-up | First answer, cold (CPU / GPU) |
|---|---|---|---|---|---|
| Xeon E5-2665 (2012), no AVX2 | TinyLlama 1.1B (Q4_0) | 27.1 tok/s | 197.4 tok/s | 7.3× | 10.2 s / 2.7 s |
| same | Llama 3.2 3B (Q4_K_M) | 12.8 tok/s | 77.7 tok/s | 6.1× | 18.5 s / 5.6 s |
| same | Qwen2.5 7B Instruct (Q4_K_M) | 6.4 tok/s | 48.9 tok/s | 7.6× | 31.3 s / 5.6 s |

Warm speed is the median of three runs with 200-token answers. A token is roughly three-quarters of a
word, and most people read about 5 tokens per second. Raw data is in [`results/`](results/).

One machine is one data point. Instruction sets, core allocation, memory bandwidth, virtualization,
background work and runtime versions all affect speed. Our four-vCPU server with AVX2 and AVX-512
was slower than this desktop on the same 3B model, with different thread and software settings.
See the [paired server report](SERVER-BENCHMARK.md). More machines are wanted.

## One-machine operating-system comparison

[HP Notebook i3-5005U: Windows 10 vs Linux Mint Cinnamon](machine-tests/hp-notebook-i3-5005u/) — a paired test on the same 6 GB laptop, using the same Ollama version and model.

## Test your own machine

You need Python 3.8+ and a running Ollama. The script has no other dependencies.

```bash
curl -O https://raw.githubusercontent.com/Arynwood-Technology/local-ai-benchmarks/main/bench.py
ollama pull llama3.2:3b
python3 bench.py llama3.2:3b --csv my-results.csv
```

No NVIDIA GPU? Add `--modes cpu`. Testing several models:
`python3 bench.py tinyllama llama3.2:3b qwen2.5:7b-instruct --csv my-results.csv`

To see how much memory longer contexts need: `python3 context_length.py qwen2.5:7b-instruct`

To test tool calling (right tool, no needless calls, using results, ignoring planted instructions):
`python3 tool_calling.py hermes3:8b --runs 3 --csv my-tool-results.csv` (needs `bench.py` next to it)

The script prints your hardware and one line per model and mode:

```
Intel(R) Xeon(R) CPU E5-2665 0 @ 2.40GHz · 63 GB RAM · NVIDIA GeForce RTX 3060, 12288 MiB · Ubuntu 24.04.5 LTS · Ollama 0.11.4

tinyllama:latest             cpu    29.3 tokens/s warm     9.0 s cold   0.7 GB
tinyllama:latest             gpu   197.6 tokens/s warm     2.9 s cold   1.3 GB
```

(That sample used one warm run; the published numbers use three.)

For a bounded CPU-only server run, copy `bench.py`, `tool_calling.py` and `server_benchmark.py`
into a fresh directory for each version, then run `python3 server_benchmark.py`. It defaults to
these five server models and uses a temporary loopback-only runtime. `BENCH_OLLAMA_BINARY` can
select an unpacked runtime; `BENCH_SKIP_PULL=1` reuses cached weights. `BENCH_MODELS` overrides
the model list. The runner writes `speed.csv`, `tools.csv`, `tool-summary.json` and `run-status.json`.
Use a fresh directory because those files are overwritten on a new run. Read the report for the
reserve policy and its limits before applying the same settings to different hardware.

## Share your results

[Open a results issue](https://github.com/Arynwood-Technology/local-ai-benchmarks/issues/new?template=submit-results.yml)
and paste your CSV. Submissions are added to `results/` with the credit you choose.

## Method

- Prompt: "Explain in about 150 words why someone might run a language model locally."
- Temperature 0, a fixed seed and answers capped at 200 tokens (`num_predict`).
- One cold run with the model unloaded, then warm runs. The warm number is the median eval rate
  (`eval_count / eval_duration`); the cold number is the total time for the first answer, including load.
- CPU-only runs set `num_gpu` to 0, which puts no model layers on the GPU. The model is unloaded between modes.
- Memory is the total Ollama reports in `/api/ps` for the loaded model. `gpu_share_pct` is how much of it sat on the
  GPU (100 means it fit; less means it was split with system RAM). Files before September 24 don't have this column.

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
