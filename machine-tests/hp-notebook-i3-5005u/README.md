# HP Notebook: Windows vs Linux Mint Cinnamon

This machine-specific run compares local Ollama generation speed on the same HP Notebook before and after replacing Windows with Linux Mint Cinnamon. It uses the existing benchmark method and is intended as a practical whole-system comparison, not a claim that the operating systems alone caused every difference.

## Machine

| Component | Recorded hardware |
|---|---|
| CPU | Intel Core i3-5005U, 2 cores / 4 threads, 2.00 GHz |
| Memory | 6 GB installed |
| Graphics | Intel HD Graphics 5500 integrated graphics; no NVIDIA GPU |
| Storage | 1 TB Toshiba SATA hard drive |

The computer name and any hardware serial numbers are intentionally omitted. Keep the AC adapter connected for both runs. Leave each desktop idle for two minutes after login, close other applications, and keep each OS's normal default power profile; record any deviation here.

## Fixed workload

- Ollama **0.11.4** on both operating systems
- `tinyllama` (`Q4_0`) on both operating systems; record the full Ollama model digest after pulling it
- CPU-only (`num_gpu: 0`), because this machine has no supported discrete GPU
- Same prompt, seed, 200-token output cap, one cold run, and median of three warm runs (the repository's `bench.py` defaults)
- Run from the local disk after model download; do not count download time

Before each run, verify the Ollama version and model digest. The digest must match across operating systems; if the model tag has changed, retain the old digest or mark the results incomparable.

## Results

| OS | Ollama | Model digest | Warm median (tokens/s) | Cold first answer (s) | Power profile / notes |
|---|---:|---|---:|---:|---|
| Windows 10 Home 22H2 (build 19045) | 0.11.4 | `2644915ede352ea7bdfaff0bfac0be74c719d5d5202acb63a6fb095b52f394a4` | 9.4 | 229.8 | Balanced; AC connected; Ollama app running in tray |
| Linux Mint Cinnamon | pending | pending | pending | pending | Record Mint/Cinnamon version and power profile |

Raw CSV files will be stored alongside this page as `windows.csv` and `linux-mint-cinnamon.csv`. Add the exact `tinyllama` digest and Ollama version to each CSV's accompanying notes. Report speed-up as `Linux warm tokens/s ÷ Windows warm tokens/s`; a value above 1 means Mint was faster for this run.

The Windows cold time includes Ollama runner startup: the runner took about 167 seconds to become ready on this hard-drive laptop, and the first answer completed in 229.8 seconds total. The cold time is therefore startup-plus-first-answer, as defined in the repository method. During this exploratory baseline, other desktop processes were already open and the Windows Ollama tray app remained running; repeat with a clean idle desktop on Mint and note the state before drawing a strong OS comparison.

## Run procedure

Use the same command from the repository root on each OS:

```sh
python bench.py tinyllama --modes cpu --runs 3 --num-predict 200 \
  --csv machine-tests/hp-notebook-i3-5005u/windows.csv
```

On Mint, change the output path to `machine-tests/hp-notebook-i3-5005u/linux-mint-cinnamon.csv`. Install the official Ollama **0.11.4** release, pull `tinyllama`, and check the resolved model with `ollama show tinyllama` and `ollama list` before benchmarking. Compare the full digest shown by `ollama list`; the model tag alone is not enough to establish identical weights. `bench.py` unloads the model for the cold run and between CPU/GPU modes, then records the warm-run median.

Official pinned release assets: [Windows installer](https://github.com/ollama/ollama/releases/download/v0.11.4/OllamaSetup.exe) and [Linux x86-64 archive](https://github.com/ollama/ollama/releases/download/v0.11.4/ollama-linux-amd64.tgz). Install the Windows build on the first OS and use Ollama's Linux install procedure with `OLLAMA_VERSION=0.11.4` on Mint. Confirm `ollama --version` reports `0.11.4` before each run.

## Capture log

| Date | OS / Cinnamon | Ollama | Digest | AC connected | Background load / notes |
|---|---|---|---|---|---|
| 2026-09-29 | Windows 10 Home 22H2, build 19045 | 0.11.4 | `2644915ede352ea7bdfaff0bfac0be74c719d5d5202acb63a6fb095b52f394a4` | Yes (battery 100%) | Balanced plan; desktop apps already open; Ollama tray app running |
| pending | Linux Mint Cinnamon | pending | pending | pending | pending |
