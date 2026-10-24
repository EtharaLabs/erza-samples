<p align="center"><img src="images/hero.svg" alt="Erza" width="720"></p>

# Erza: samples

<p align="center"><b>The samples lane: 5 of 5 Harbor task bundles.</b></p>

<p align="center"><a href="#summary"><img src="https://img.shields.io/badge/bundles-5_of_5-845EF7" alt="bundles: 5 of 5"></a> <a href="#evidence-status"><img src="https://img.shields.io/badge/sealed-0-845EF7" alt="sealed: 0"></a> <a href="#difficulty-tiers"><img src="https://img.shields.io/badge/difficulty-measured-845EF7" alt="difficulty: measured"></a></p>

<p align="center"><sub><a href="#abstract">Abstract</a> | <a href="#summary">Summary</a> | <a href="#difficulty-tiers">Difficulty tiers</a> | <a href="#evidence-status">Evidence status</a> | <a href="#coverage">Coverage</a> | <a href="#dataset-structure">Dataset structure</a> | <a href="#verification-and-quality-assurance">Verification and quality assurance</a> | <a href="#reproduction">Reproduction</a> | <a href="#cite">Cite</a> | <a href="#license">License</a> | <a href="#contact">Contact</a></sub></p>

## Abstract

The curated lane of this corpus: at most 5 Harbor task bundles, every anchor seated first and every other bundle in seal order. Bundles past that ceiling live in `delivery/`.

Each bundle is one Harbor task in a directory named by its content-derived uuid5, so the name doubles as an integrity check. This page is rendered from the resident bundles on every reconcile; a value a bundle does not carry reads `absent`, and the page never fills one in.

## Summary

| Property | Value |
| --- | --- |
| Bundles | 5 of 5 |
| Sealed | 0 of 5 |
| Registrations | unregistered (5) |
| Audit verdicts | none (5) |
| Harbor schema | 1.3 (2), 2.0 (3) |

## Difficulty tiers

Difficulty is measured by the signed pilot alone and never declared in a bundle, so this page states no tier a bundle claims.

## Evidence status

The verdict is the audit outcome recorded at the sealed digest, and `none` means no verdict has landed for that digest yet. Only an authoring run removes a bundle from this lane, so removal waits for the next one.

| uuid | Verdict | Sealed digest | Stream |
| --- | --- | --- | --- |
| 20840ce0-eeb4-5848-afda-c600b281a77a | none | absent | none |
| 446e76fe-be48-51d8-8739-07a721a141df | none | absent | none |
| aec90ff1-0265-5d75-8e0e-49786360d336 | none | absent | none |
| c7faca71-82cd-5ad3-9dc5-c161793ddb25 | none | absent | none |
| ebdbad6e-5ef8-51c8-9d52-ddf100ee1aea | none | absent | none |

## Coverage

| Keyword | Bundles |
| --- | --- |
| 30-360 | 1 |
| accrued-interest | 1 |
| act-act-icma | 1 |
| act-act-isda | 1 |
| air-carrier | 1 |
| bond-math | 1 |
| btu-conversion | 1 |
| byte-exact-output | 1 |
| constraint-checking | 1 |
| conventions | 1 |
| crew-scheduling | 1 |
| day-count | 1 |
| duty-time | 1 |
| earthquake | 1 |
| energy-accounting | 1 |
| fixed-income | 1 |
| fuel-ledger | 1 |
| information-returns | 1 |
| instrument-response | 1 |
| isda-2006 | 1 |
| local-magnitude | 1 |
| miniseed | 1 |
| obspy | 1 |
| payee-detail-record | 1 |
| positional-layout | 1 |
| regulatory-compliance | 1 |
| regulatory-transmission | 1 |
| roster-audit | 1 |
| seismology | 1 |
| unit-harmonisation | 1 |
| wood-anderson | 1 |

## Dataset structure

| Bundle | Task | Keywords | Registration | Sealed at | Tier |
| --- | --- | --- | --- | --- | --- |
| [`20840ce0-eeb4-5848-afda-c600b281a77a`](20840ce0-eeb4-5848-afda-c600b281a77a/) | `Information Return Brecord Emission` | byte-exact-output, information-returns, payee-detail-record, positional-layout, regulatory-transmission | unregistered | unsealed | - |
| [`446e76fe-be48-51d8-8739-07a721a141df`](446e76fe-be48-51d8-8739-07a721a141df/) | `Local Magnitude Seismology` | earthquake, instrument-response, local-magnitude, miniseed, obspy, seismology, wood-anderson | unregistered | unsealed | - |
| [`aec90ff1-0265-5d75-8e0e-49786360d336`](aec90ff1-0265-5d75-8e0e-49786360d336/) | `Erza Day Count Accrued` | 30-360, accrued-interest, act-act-icma, act-act-isda, bond-math, conventions, day-count, fixed-income, isda-2006 | unregistered | unsealed | - |
| [`c7faca71-82cd-5ad3-9dc5-c161793ddb25`](c7faca71-82cd-5ad3-9dc5-c161793ddb25/) | `Flight Duty Period Legality` | air-carrier, constraint-checking, crew-scheduling, duty-time, regulatory-compliance, roster-audit | unregistered | unsealed | - |
| [`ebdbad6e-5ef8-51c8-9d52-ddf100ee1aea`](ebdbad6e-5ef8-51c8-9d52-ddf100ee1aea/) | `Energy Sector Heat Content` | btu-conversion, energy-accounting, fuel-ledger, unit-harmonisation | unregistered | unsealed | - |

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#131a33","primaryTextColor":"#e8ecff","primaryBorderColor":"#845EF7","lineColor":"#22d3ee","fontFamily":"monospace"}}}%%
flowchart LR
    bundle["&lt;uuid&gt;/"]
    bundle --> n0["task.toml<br/>runner manifest"]
    bundle --> n1["instruction.md<br/>objective the agent reads"]
    bundle --> n2["environment/<br/>agent sandbox image"]
    bundle --> n3["tests/<br/>verifier, hidden from the agent"]
    bundle --> n4["TRUTH.md"]
    bundle --> n5["oracle/"]
    bundle --> n6["trajectories/"]
```

```mermaid
%%{init: {"theme":"base","themeVariables":{"primaryColor":"#131a33","primaryTextColor":"#e8ecff","primaryBorderColor":"#845EF7","lineColor":"#22d3ee","fontFamily":"monospace"}}}%%
flowchart LR
    staging["staging/"]
    staging --> samples["samples/<br/>5 of 5"]
    samples --> delivery["delivery/<br/>5 of 10000"]
    delivery --> stock["stock/<br/>0 of 10000"]
```

## Verification and quality assurance

Each bundle's signed provenance carrier holds its screening roots, screening instant, and absolute expiry. Placement moves that carrier into the private derivation set, which this page never reads, so reconcile lists no root it cannot verify here.

## Reproduction

Each bundle directory is a complete Harbor task: `task.toml` is the runner manifest, `instruction.md` the objective, `environment/` the sandbox image, and `tests/` the verifier. Point a Harbor runner at one bundle directory to reproduce it; `solution/` stays private.

## Cite

```bibtex
@misc{erza2026,
  title        = {Erza: A Paired-Evaluation Benchmark for Agent Skill Efficacy},
  author       = {{Ethara.AI}},
  year         = {2026},
  howpublished = {\url{https://github.com/EtharaOrion/erza}},
  note         = {See the Evidence status section for what is measured}
}
```

## License

Released under the MIT License; see [LICENSE](LICENSE) for the full text. Benchmarks, datasets, and task bundles produced through this project retain their own original licences.

## Contact

Erza is built by [Ethara.AI](https://github.com/Ethara-Ai). For contribution routes see [CONTRIBUTING.md](CONTRIBUTING.md), and for vulnerability or benchmark-integrity disclosure see [SECURITY.md](SECURITY.md), which carries the private reporting address and the coordinated-disclosure terms. For the reading path through the full documentation spine, start at [INDEX.md](INDEX.md).
