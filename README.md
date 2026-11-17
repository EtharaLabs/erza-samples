<p align="center"><img src="images/hero.svg" alt="Erza" width="720"></p>

# Erza SkillsBench: samples

<p align="center"><b>Five sample tasks from Erza SkillsBench, a Harbor benchmark that measures whether curated Agent Skills improve an autonomous agent.</b></p>

<p align="center"><a href="#summary"><img src="https://img.shields.io/badge/tasks-5-845EF7" alt="tasks: 5"></a> <a href="#summary"><img src="https://img.shields.io/badge/harbor_schema-1.4-845EF7" alt="harbor schema: 1.4"></a> <a href="#trials"><img src="https://img.shields.io/badge/skills_uplift-%2B0.2093-845EF7" alt="skills uplift: +0.2093"></a></p>

<p align="center"><sub><a href="#abstract">Abstract</a> | <a href="#summary">Summary</a> | <a href="#tasks">Tasks</a> | <a href="#trials">Trials</a> | <a href="#coverage">Coverage</a> | <a href="#dataset-structure">Dataset structure</a> | <a href="#reproduction">Reproduction</a> | <a href="#cite">Cite</a> | <a href="#contact">Contact</a></sub></p>

## Abstract

Erza SkillsBench is a benchmark of agentic tasks in [Harbor](https://github.com/laude-institute/harbor) format, built to measure whether curated Agent Skills improve an autonomous agent. It targets [SkillsBench](https://arxiv.org/abs/2602.12670) (arXiv:2602.12670). Each task ships one or two Skills, `SKILL.md` packages of procedural knowledge, and is run twice under identical conditions: once with its Skills and once without. The paired reward difference shows what the Skills add.

Every task runs in an offline container and carries a reference solution, deterministic tests, an LLM-judged rubric, and a continuous reward from 0 to 1. The full benchmark spans software engineering and other expert domains, including cybersecurity, natural science, mathematics and operations research, finance and economics, industrial and physical systems, office work, and media production.

This repository holds the five-task sample. All five are software engineering tasks: the agent repairs seeded faults in a real upstream open source project against a written specification, and documents the root causes it found. The sample covers Python, Go, C++, and Rust. Task images hold no upstream version history, package caches, or reference copies of the code under repair, and agent web search is disabled, so the upstream code is not the answer.

## Summary

| Property | Value |
| --- | --- |
| Tasks | 5 |
| Domain | Software engineering (specification-driven debugging and repair) |
| Languages | Python, Go, C++, Rust |
| Format | Harbor task, schema 1.4 |
| Platforms | linux/amd64, linux/arm64 |
| Skills per task | 1 or 2 |
| Average handling time (AHT) | 780 minutes per task |
| Agent | Codex CLI 0.166.0 with `gpt-6.1-sol` |
| Judge | Claude Fable 5.1 |
| Runs per condition | 1 per task |
| Mean reward, no Skills | 0.5561 |
| Mean reward, with Skills | 0.7654 |
| Mean uplift | +0.2093 |

## Tasks

| Task | Project | Language | Objective | Skills |
| --- | --- | --- | --- | --- |
| [`0ddf264f`](0ddf264f-938b-4b5c-817c-45766d0dcf81/) | Pagecraft 0.2.0 | Python | Repair the Pagecraft static site generator so incremental rebuilds, generated outputs, and the check command agree on the shipped example site, and write a root-cause note. | build-chain-triage |
| [`7b7c2a4e`](7b7c2a4e-6d0f-4d55-9a1e-3f2c8b6e5d41/) | etcd raft (`go.etcd.io/raft/v3`) | Go | Bring the Raft library into conformance with Raft's safety properties under crashes, message loss and reordering, partitions, and asynchronous storage, and write a repair report. | persistence-ordering-audit, raft-safety-simulation |
| [`f9336b92`](f9336b92-872f-4ef0-a6a2-719434aa04a4/) | python-dateutil 4.0.0 | Python | Make recurrence expansion conform to RFC 5545 sections 3.3.5, 3.3.10, and 3.8.5.3 through the public `rrule` API, with a regression test per repaired cause and a root-cause note. | rfc5545-recurrence-derivation |
| [`fdc50914`](fdc50914-fdba-4675-a017-31f808f4cf2a/) | regress 0.12.0 | Rust | Repair the ECMAScript regular-expression engine so class sets, case-insensitive matching, duplicate named groups, backreferences, and quantifier backtracking follow ECMA-262 2025 section 22.2, and write a root-cause note. | backtracking-engine-testing, ecma262-algorithm-reading |
| [`fe87d052`](fe87d052-22ef-4406-a429-b2ad5b747881/) | fast_float 8.3.3 | C++ | Bring the decimal-to-binary parser into conformance with round-to-nearest, ties-to-even and its `from_chars` contract for `float` and `double`, and write a repair report. | correctly-rounded-decimal-parsing |

## Trials

Each task was run once without Skills (`no-skill`) and once with its Skills mounted (`with-skill`), under identical conditions, using Codex CLI 0.166.0 with `gpt-6.1-sol`, and scored by the task's own verifier. Trials are stored in each task's `trials/gpt-6.1-sol/<arm>/<job>/<trial>/`.

| Task | Reward<br/>no-skill | Reward<br/>with-skill | Uplift | Cost (USD)<br/>no-skill / with-skill | Agent time<br/>no-skill / with-skill |
| --- | ---: | ---: | ---: | ---: | ---: |
| [`0ddf264f-938b-4b5c-817c-45766d0dcf81`](0ddf264f-938b-4b5c-817c-45766d0dcf81/trials/gpt-6.1-sol/) | 0.6364 | 0.9752 | +0.3388 | 0.20 / 0.22 | 3m 27s / 4m 36s |
| [`7b7c2a4e-6d0f-4d55-9a1e-3f2c8b6e5d41`](7b7c2a4e-6d0f-4d55-9a1e-3f2c8b6e5d41/trials/gpt-6.1-sol/) | 0.3143 | 0.6857 | +0.3714 | 0.48 / 0.67 | 10m 51s / 13m 5s |
| [`f9336b92-872f-4ef0-a6a2-719434aa04a4`](f9336b92-872f-4ef0-a6a2-719434aa04a4/trials/gpt-6.1-sol/) | 0.5192 | 0.5577 | +0.0385 | 0.06 / 0.06 | 1m 17s / 1m 20s |
| [`fdc50914-fdba-4675-a017-31f808f4cf2a`](fdc50914-fdba-4675-a017-31f808f4cf2a/trials/gpt-6.1-sol/) | 0.6316 | 0.7544 | +0.1228 | 0.28 / 0.58 | 5m 35s / 10m 6s |
| [`fe87d052-22ef-4406-a429-b2ad5b747881`](fe87d052-22ef-4406-a429-b2ad5b747881/trials/gpt-6.1-sol/) | 0.6788 | 0.8540 | +0.1752 | 0.17 / 0.22 | 3m 43s / 5m 57s |
| **mean** | **0.5561** | **0.7654** | **+0.2093** | **0.24 / 0.35** | **4m 59s / 7m 1s** |

The Skills mounted in each task's `with-skill` arm are listed in the [Tasks](#tasks) table.

Each trial folder is Harbor's trial output:

| Path | Contents |
| --- | --- |
| `config.json`, `lock.json` | Trial configuration and resolved run settings |
| `result.json` | Agent, model, token usage, cost, timings, and verifier reward |
| `agent/` | Agent trajectory (`trajectory.json`), Codex session transcript (`sessions/`), and agent output (`codex.txt`) |
| `verifier/` | `reward.json`, `reward.txt`, `reward-details.json`, and test output |
| `artifacts/` | Files the agent produced, collected from the paths declared in `task.toml` |

## Coverage

| Keyword | Tasks |
| --- | --- |
| backtracking | 1 |
| build-chain | 1 |
| consensus | 1 |
| cpp | 1 |
| debugging | 5 |
| distributed-systems | 1 |
| ecmascript | 1 |
| fault-tolerance | 1 |
| floating-point | 1 |
| go | 1 |
| icalendar | 1 |
| ieee-754 | 1 |
| number-parsing | 1 |
| python | 2 |
| raft | 1 |
| recurrence | 1 |
| regex | 1 |
| rewardkit | 1 |
| rfc5545 | 1 |
| root-cause-analysis | 1 |
| rust | 1 |
| specification-conformance | 3 |
| static-site-generator | 1 |

## Dataset structure

Each task is one Harbor task in a directory named by its uuid.

| Task | Keywords |
| --- | --- |
| [`0ddf264f-938b-4b5c-817c-45766d0dcf81`](0ddf264f-938b-4b5c-817c-45766d0dcf81/) | build-chain, debugging, python, root-cause-analysis, static-site-generator |
| [`7b7c2a4e-6d0f-4d55-9a1e-3f2c8b6e5d41`](7b7c2a4e-6d0f-4d55-9a1e-3f2c8b6e5d41/) | consensus, debugging, distributed-systems, fault-tolerance, go, raft |
| [`f9336b92-872f-4ef0-a6a2-719434aa04a4`](f9336b92-872f-4ef0-a6a2-719434aa04a4/) | debugging, icalendar, python, recurrence, rewardkit, rfc5545, specification-conformance |
| [`fdc50914-fdba-4675-a017-31f808f4cf2a`](fdc50914-fdba-4675-a017-31f808f4cf2a/) | backtracking, debugging, ecmascript, regex, rust, specification-conformance |
| [`fe87d052-22ef-4406-a429-b2ad5b747881`](fe87d052-22ef-4406-a429-b2ad5b747881/) | cpp, debugging, floating-point, ieee-754, number-parsing, specification-conformance |

```
<uuid>/
├── task.toml         runner manifest
├── instruction.md    objective the agent reads
├── environment/      sandbox image, with the task's Skills in skills/
├── tests/            verifier, hidden from the agent
├── solution/         reference solution
└── trials/
    └── gpt-6.1-sol/      agent model
        ├── no-skill/     <job>/<trial>/ run without Skills
        └── with-skill/   <job>/<trial>/ run with Skills
```

## Reproduction

Each task directory is a complete Harbor task: `task.toml` is the runner manifest, `instruction.md` the objective, `environment/` the sandbox image with the task's Skills under `environment/skills/`, `tests/` the verifier, and `solution/` the reference solution. The trials above were produced with:

```bash
harbor run -a codex -m openai/gpt-6.1-sol
```

Run each task once without Skills and once with the Skills in `environment/skills/` to reproduce the paired comparison. The verifier's LLM-judged rubric uses `ANTHROPIC_API_KEY` (Claude Fable 5.1) or, when only `OPENAI_API_KEY` is set, an OpenAI judge.

## Cite

```bibtex
@misc{erza2026,
  title        = {Erza: A Paired-Evaluation Benchmark for Agent Skill Efficacy},
  author       = {{Ethara.AI}},
  year         = {2026}
}
```

## Contact

Erza SkillsBench is built by [Ethara.AI](https://github.com/Ethara-Ai). For questions about the benchmark or dataset, contact [research@ethara.ai](mailto:research@ethara.ai).

Copyright (c) 2026 Green Rider Technology LLP (Ethara AI). All rights reserved.
