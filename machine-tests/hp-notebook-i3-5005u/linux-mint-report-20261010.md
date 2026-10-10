# HP Notebook: Linux Mint vs Windows 10

Linux Mint measured **12.9 tokens/s**, compared with **9.4 tokens/s** on Windows: **37.2% higher warm generation throughput (1.37×)**. This is a paired hardware comparison with matching Ollama and model versions, but differing desktop and startup conditions; it does not isolate the operating system as the cause.

## Results and raw data

| Measurement | Windows 10 | Linux Mint 22.3 |
|---|---:|---:|
| Date | 2026-09-29 | 2026-10-10 |
| Warm median, three runs (tokens/s) | 9.4 | 12.9 |
| Cold full-answer completion (s) | 229.8 | 19.8 |
| Ollama-reported loaded model memory (decimal GB) | 0.7 | 0.7 |
| GPU memory share (%) | 0 | 0 |

Raw aggregate CSVs: [Windows](windows.csv) and [Mint](linux-mint-cinnamon-20261010-144025.csv). Baseline context: [machine record](README.md). Original records and the benchmark script were preserved.

Calculations from the rounded CSV values:

- Throughput difference: `12.9 - 9.4 = 3.5 tokens/s`.
- Throughput ratio: `12.9 / 9.4 = 1.3723`.
- Throughput change: `(12.9 / 9.4 - 1) * 100 = +37.2%`.
- Cold completion difference: `19.8 - 229.8 = -210.0 seconds`, or `91.4%` shorter. This particularly large change includes runner startup differences and cannot be attributed solely to generation speed.

## Hardware and fixed workload

- Intel Core i3-5005U, 2 cores / 4 threads, nominal 2.00 GHz; AVX, AVX2, FMA, SSE4.1/4.2 supported.
- 6 GB installed RAM; Linux reports approximately 5.7 GiB usable. Before initial preparation, available memory was approximately 2.9 GiB; this was not an inference-time measurement.
- Intel HD Graphics 5500; inference requested `num_gpu: 0`, and the CSV reports 0% GPU memory share.
- Linux Mint 22.3 (Zena), Cinnamon 6.6.4, kernel `6.14.0-37-generic`.
- Ollama server 0.11.4 on both systems, verified on Mint through `/api/version` before the benchmark.
- `tinyllama` / `tinyllama:latest`, Q4_0. Mint's full model digest, verified through `/api/tags` before inference, matches the recorded Windows digest: `2644915ede352ea7bdfaff0bfac0be74c719d5d5202acb63a6fb095b52f394a4`.
- Prompt: `Explain in about 150 words why someone might run a language model locally.`
- Temperature 0, seed 42, `num_predict: 200`; this is an output cap, not a guarantee of exactly 200 tokens.
- One cold request after unloading the model, then three warm requests. Warm rate is the median of `eval_count / eval_duration * 1e9`.
- Context size, thread count, and other unspecified options use runtime/model defaults; they were not explicitly pinned or captured by the script.
- Checkout inspected for this report: `491c71a76f524c1a704e90a6ae2526fee522fdfe`. `bench.py` has no local modifications.

## Reproduction

Use Ollama 0.11.4 and the matching model digest; model downloads are excluded from timings. Keep AC connected, close other applications, use the normal default desktop power profile, and allow two minutes of idle time before starting.

From the repository root:

```bash
curl -s http://localhost:11434/api/version
curl -s http://localhost:11434/api/tags
result="machine-tests/hp-notebook-i3-5005u/linux-mint-cinnamon-$(date +%Y%m%d-%H%M%S).csv"
test ! -e "$result" && python3 bench.py tinyllama --modes cpu --runs 3 --num-predict 200 --csv "$result"
```

The measured run used the same Python command and saved `linux-mint-cinnamon-20261010-144025.csv`. It ran in the user's normal terminal because the agent session could not access the host Ollama API. The saved CSV was subsequently read and checked against the supplied console output.

## Conditions and limitations

AC was connected during preparation and the post-run check. The post-run CPU governor was `schedutil`; the desktop power profile and governor during inference were not captured. The operator was instructed to close applications and idle for two minutes, but compliance and exact background activity were not recorded. Windows used the Balanced plan with desktop applications already open and Ollama running in the tray.

The Windows record describes about 167 seconds of runner startup within its 229.8-second cold completion. The benchmark unloads model weights but does not clear filesystem caches or reboot; its cold result measures Ollama's reported total duration for startup/load plus the entire first answer. It does **not** measure time to first token: requests use `stream: false`.

The 0.7 GB memory value comes from Ollama's `/api/ps` after the cold request. It is not peak resident memory, total system memory use, or a time series. CPU utilization and inference-time available memory were not measured. A post-run check found approximately 2.8 GiB available and 2.8 MiB swap used; this does not establish peak inference usage or swapping during generation.

The unchanged script retains only the rounded warm median and cold completion time, not individual warm-run rates, responses, or raw API timing records. Three warm requests establish a small within-session sample; variability, confidence intervals, and between-session repeatability cannot be calculated from the saved CSV. An independent repeat session has not been performed.

For broader context, the repository's Xeon E5-2665 CPU-only TinyLlama result is 27.1 tokens/s (see the root README). Mint's 12.9 tokens/s is 47.6% of that figure, but this cross-machine comparison is descriptive: hardware and run conditions differ.

These observations support higher measured throughput on this Mint configuration. Background processes, power behavior, filesystem caching, and runner startup prevent a claim that Mint alone caused the difference.
