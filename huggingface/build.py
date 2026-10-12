#!/usr/bin/env python3
"""Build the Hugging Face mirror of this dataset in huggingface/dist/.

Every CSV under results/ and machine-tests/ is copied unchanged to raw/, and the per-row files
are merged by kind into data/*.csv (one Hugging Face "config" each) with a source_file column,
so the dataset viewer shows one table per kind. The dataset card is generated from the data.

    python3 huggingface/build.py
"""
import csv
import shutil
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "huggingface/dist"
SOURCES = ["results", "machine-tests"]

KINDS = {
    "speed": "Generation speed: warm tokens per second and cold first-answer time, one row per model and mode",
    "tool_calling": "Tool calling: one row per test case and run, with the tools called and the reply",
    "decision_routing": "Decision routing: one row per routing case and run for small decision models",
    "app_evals": "Arynwood MCP live evals: one row per eval test",
}


def kind(header):
    h = set(header)
    if "warm_tokens_per_s" in h:
        return "speed"
    if {"case", "tools_called"} <= h:
        return "tool_calling"
    if {"case", "variant", "state", "answer"} <= h:
        return "decision_routing"
    if {"suite", "test", "outcome"} <= h:
        return "app_evals"
    return None


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "data").mkdir(parents=True)
    tables = {k: [] for k in KINDS}
    cols = {k: [] for k in KINDS}
    for src in SOURCES:
        for path in sorted((ROOT / src).rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            rel = path.relative_to(ROOT)
            dest = DIST / "raw" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            if path.suffix != ".csv":
                continue
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                k = kind(reader.fieldnames or [])
                if not k:
                    continue
                for c in reader.fieldnames:
                    if c not in cols[k]:
                        cols[k].append(c)
                for r in reader:
                    r["source_file"] = str(rel)
                    tables[k].append(r)
    for k, rows in tables.items():
        with open(DIST / "data" / f"{k}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols[k] + ["source_file"], restval="")
            w.writeheader()
            w.writerows(rows)
    for name in ["CITATION.cff", "LICENSE"]:
        shutil.copy2(ROOT / name, DIST / name)
    (DIST / "README.md").write_text(card(tables))
    print(", ".join(f"{k}: {len(v)} rows" for k, v in tables.items()), f"-> {DIST}")


def glance(rows):
    """One line per machine, model, mode and Ollama version, with the warm median."""
    seen, out = set(), []
    for r in rows:
        key = (r["cpu"], r["gpu"], r["os"], r["model"], r["mode"], r["ollama_version"])
        if key in seen:
            continue
        seen.add(key)
        same = [float(x["warm_tokens_per_s"]) for x in rows
                if (x["cpu"], x["gpu"], x["os"], x["model"], x["mode"], x["ollama_version"]) == key]
        cpu = short(r["cpu"]) + (" (virtual server)" if "virtual" in r["gpu"] else "")
        os_name = "Windows 10" if r["os"].startswith("Windows-10") else r["os"].split(",")[0]
        out.append((r["date"], cpu, os_name, r["model"], r["quantization"], r["mode"],
                    statistics.median(same), r["ollama_version"]))
    out.sort(key=lambda x: (x[1], x[5], -x[6]))
    lines = ["| Date | CPU | OS | Model | Quant | Mode | Warm tok/s | Ollama |", "|---|---|---|---|---|---|---:|---|"]
    lines += [f"| {d} | {c} | {o} | {m} | {q} | {mo} | {t:.1f} | {v} |" for d, c, o, m, q, mo, t, v in out]
    return "\n".join(lines)


def short(cpu):
    cpu = cpu.replace("(R)", "").replace("(TM)", "").replace("Intel Core", "Intel").replace("CPU ", "")
    return cpu.split(",")[0].split(" @")[0].split(" (")[0].strip()


def speed(rows, cpu, model, mode, os_prefix="", date=""):
    """The warm rate for one machine, model and mode; the card's claims are read from here."""
    hits = {float(r["warm_tokens_per_s"]) for r in rows
            if cpu in r["cpu"] and r["model"] == model and r["mode"] == mode and r["os"].startswith(os_prefix)
            and r["date"].startswith(date)}
    assert len(hits) == 1, (cpu, model, mode, os_prefix, hits)
    return hits.pop()


def card(tables):
    s = tables["speed"]
    win = speed(s, "i3-5005U", "tinyllama", "cpu", "Windows")
    mint = speed(s, "i3-5005U", "tinyllama", "cpu", "Linux Mint")
    l3_cpu = speed(s, "E5-2665", "llama3.2:3b", "cpu", date="2026-09-22")
    l3_gpu = speed(s, "E5-2665", "llama3.2:3b", "gpu", date="2026-09-22")
    q7_cpu = speed(s, "E5-2665", "qwen2.5:7b-instruct", "cpu", date="2026-09-22")
    assert round((mint / win - 1) * 100) == 37 and round(l3_gpu / l3_cpu, 1) == 6.1
    configs = "\n".join(f"- config_name: {k}\n  data_files: data/{k}.csv" + ("\n  default: true" if k == "speed" else "")
                        for k in KINDS if tables[k])
    kinds = "\n".join(f"- `{k}` ({len(tables[k])} rows): {d}" for k, d in KINDS.items() if tables[k])
    return f"""---
license: cc-by-4.0
pretty_name: Local AI benchmarks (Ollama speed and tool calling on CPU and GPU)
language:
- en
tags:
- ollama
- llm
- benchmark
- local-ai
- cpu
- gpu
- linux
- tool-calling
- llama.cpp
size_categories:
- 1K<n<10K
configs:
{configs}
---

# Local AI benchmarks: how fast do local language models run on ordinary hardware?

Measured [Ollama](https://ollama.com) generation speeds on real machines, CPU only and on a GPU, plus
tool-calling and decision-routing tests for local agents. Every row comes from a recorded run of the
open [`bench.py`](https://github.com/Arynwood-Technology/local-ai-benchmarks) scripts by
[Arynwood Technology](https://arynwood.com/).

**Short answers from this data**

- On a 2015 laptop (Intel i3-5005U, 6 GB RAM), TinyLlama ran at {mint} tokens/s on Linux Mint 22.3 and
  {win} tokens/s on Windows 10, same Ollama 0.11.4 and model digest: {round((mint / win - 1) * 100)}% higher on Mint for this setup.
  [Write-up](https://arynwood.com/ollama-linux-vs-windows/), DOI [10.5281/zenodo.23290682](https://doi.org/10.5281/zenodo.23290682).
- An RTX 3060 12 GB ran Llama 3.2 3B at {l3_gpu} tokens/s against {l3_cpu} on the 2012 Xeon CPU of the same
  machine ({l3_gpu / l3_cpu:.1f}x). Models up to 14B fit on the card. [What can an RTX 3060 12GB run?](https://arynwood.com/rtx-3060-12gb-local-llm/)
- Without a GPU, that 2012 Xeon ran Llama 3.2 3B at {l3_cpu} tokens/s and Qwen2.5 7B at {q7_cpu}; most people
  read about 5 tokens/s. [Local AI without a GPU](https://arynwood.com/local-ai-cpu-only.html)

## Speed at a glance

Warm generation speed is the median `eval_count / eval_duration` of three warm runs answering the same
prompt with a 200-token cap, temperature 0 and a fixed seed.

{glance(tables["speed"])}

## Tables in this dataset

{kinds}

`raw/` holds every original file unchanged, with the per-machine reports. Pick a table in the viewer
above or load one:

```python
from datasets import load_dataset
speed = load_dataset("Arynwood/local-ai-benchmarks", "speed", split="train")
```

## Add your machine

Run the script and open a results issue; accepted results land here automatically.

```bash
curl -O https://raw.githubusercontent.com/Arynwood-Technology/local-ai-benchmarks/main/bench.py
python3 bench.py llama3.2:3b --csv my-results.csv     # add --modes cpu without an NVIDIA GPU
```

[Submit your results](https://github.com/Arynwood-Technology/local-ai-benchmarks/issues/new?template=submit-results.yml)

## Method and limits

- Prompt: "Explain in about 150 words why someone might run a language model locally."
- One cold request with the model unloaded, then warm requests. Cold time includes model load.
- CPU-only runs set `num_gpu` to 0. `gpu_share_pct` is how much of the loaded model sat on the GPU.
- One machine is one data point. Instruction sets, memory bandwidth, background work, power settings and
  runtime versions all change speed. Each source file's report in `raw/` lists its conditions.

## License and citation

Data: CC BY 4.0. Credit "Arynwood" and link to https://arynwood.com/local-ai-cpu-only.html.
Scripts: MIT, in the [GitHub repository](https://github.com/Arynwood-Technology/local-ai-benchmarks).
Citation details are in `CITATION.cff`. This mirror is rebuilt from GitHub on every new result.

Want local AI set up on your own machine? See [Arynwood MCP](https://arynwood.com/mcp/) and
[local AI setup services](https://arynwood.com/#services).
"""


if __name__ == "__main__":
    main()
