<p align="center"><img src="images/hero.svg" alt="Erza" width="720"></p>

# Erza: samples

<p align="center"><b>The samples lane: 10 of 10 Harbor task bundles.</b></p>

<p align="center"><a href="#summary"><img src="https://img.shields.io/badge/bundles-10_of_10-845EF7" alt="bundles: 10 of 10"></a> <a href="#evidence-status"><img src="https://img.shields.io/badge/sealed-0-845EF7" alt="sealed: 0"></a> <a href="#difficulty-tiers"><img src="https://img.shields.io/badge/difficulty-measured-845EF7" alt="difficulty: measured"></a></p>

<p align="center"><sub><a href="#abstract">Abstract</a> | <a href="#summary">Summary</a> | <a href="#difficulty-tiers">Difficulty tiers</a> | <a href="#evidence-status">Evidence status</a> | <a href="#coverage">Coverage</a> | <a href="#dataset-structure">Dataset structure</a> | <a href="#verification-and-quality-assurance">Verification and quality assurance</a> | <a href="#reproduction">Reproduction</a> | <a href="#cite">Cite</a> | <a href="#license">License</a> | <a href="#contact">Contact</a></sub></p>

## Abstract

The curated lane of this corpus: at most 10 Harbor task bundles, every anchor seated first and every other bundle in seal order. Bundles past that ceiling live in `delivery/`.

Each bundle is one Harbor task in a directory named by its content-derived uuid5, so the name doubles as an integrity check. This page is rendered from the resident bundles on every reconcile; a value a bundle does not carry reads `absent`, and the page never fills one in.

## Summary

| Property | Value |
| --- | --- |
| Bundles | 10 of 10 |
| Sealed | 0 of 10 |
| Registrations | unregistered (10) |
| Audit verdicts | none (10) |
| Harbor schema | 1.3 (2), 2.0 (8) |

## Difficulty tiers

Difficulty is measured by the signed pilot alone and never declared in a bundle, so this page states no tier a bundle claims.

## Evidence status

The verdict is the audit outcome recorded at the sealed digest, and `none` means no verdict has landed for that digest yet. Only an authoring run removes a bundle from this lane, so removal waits for the next one.

| uuid | Verdict | Sealed digest | Stream |
| --- | --- | --- | --- |
| 20840ce0-eeb4-5848-afda-c600b281a77a | none | absent | none |
| 446e76fe-be48-51d8-8739-07a721a141df | none | absent | none |
| 51853948-6010-57ef-9a57-f234a3616506 | none | absent | none |
| 6f76812f-83f9-5f56-9b63-38a56548fc24 | none | absent | none |
| aec90ff1-0265-5d75-8e0e-49786360d336 | none | absent | none |
| c59f8b2a-0606-5f02-bed5-52937e5ab468 | none | absent | none |
| c7faca71-82cd-5ad3-9dc5-c161793ddb25 | none | absent | none |
| d427488f-59b7-505a-bd03-bed97d147e38 | none | absent | none |
| e9474235-0323-5e54-9171-c5b80089ad7e | none | absent | none |
| ebdbad6e-5ef8-51c8-9d52-ddf100ee1aea | none | absent | none |

## Coverage

| Keyword | Bundles |
| --- | --- |
| geodesy | 2 |
| gnss | 2 |
| time-series | 2 |
| 30-360 | 1 |
| accrued-interest | 1 |
| act-act-icma | 1 |
| act-act-isda | 1 |
| air-carrier | 1 |
| algorithm-a | 1 |
| antenna-calibration | 1 |
| antex | 1 |
| bond-math | 1 |
| btu-conversion | 1 |
| byte-exact-output | 1 |
| code-bias | 1 |
| consensus | 1 |
| constraint-checking | 1 |
| conventions | 1 |
| crew-scheduling | 1 |
| day-count | 1 |
| discharge | 1 |
| duty-time | 1 |
| earthquake | 1 |
| energy-accounting | 1 |
| fixed-income | 1 |
| fuel-ledger | 1 |
| gauging | 1 |
| geophysics | 1 |
| harmonic-analysis | 1 |
| hydrology | 1 |
| information-returns | 1 |
| instrument-response | 1 |
| interlaboratory | 1 |
| ionosphere | 1 |
| isda-2006 | 1 |
| local-magnitude | 1 |
| metrology | 1 |
| miniseed | 1 |
| obspy | 1 |
| oceanography | 1 |
| payee-detail-record | 1 |
| phase-centre | 1 |
| positional-layout | 1 |
| positioning | 1 |
| proficiency-testing | 1 |
| pseudorange | 1 |
| rating-curve | 1 |
| regulatory-compliance | 1 |
| regulatory-transmission | 1 |
| robust-statistics | 1 |
| roster-audit | 1 |
| seismology | 1 |
| streamflow | 1 |
| tidal-prediction | 1 |
| tides | 1 |
| total-electron-content | 1 |
| uncertainty | 1 |
| unit-harmonisation | 1 |
| wood-anderson | 1 |
| zeta-score | 1 |

## Dataset structure

| Bundle | Task | Keywords | Registration | Sealed at | Tier |
| --- | --- | --- | --- | --- | --- |
| [`20840ce0-eeb4-5848-afda-c600b281a77a`](20840ce0-eeb4-5848-afda-c600b281a77a/) | `Information Return Brecord Emission` | byte-exact-output, information-returns, payee-detail-record, positional-layout, regulatory-transmission | unregistered | unsealed | - |
| [`446e76fe-be48-51d8-8739-07a721a141df`](446e76fe-be48-51d8-8739-07a721a141df/) | `Local Magnitude Seismology` | earthquake, instrument-response, local-magnitude, miniseed, obspy, seismology, wood-anderson | unregistered | unsealed | - |
| [`51853948-6010-57ef-9a57-f234a3616506`](51853948-6010-57ef-9a57-f234a3616506/) | `Gauge Rating Block Discharge V3` | discharge, gauging, hydrology, rating-curve, streamflow, time-series | unregistered | unsealed | - |
| [`6f76812f-83f9-5f56-9b63-38a56548fc24`](6f76812f-83f9-5f56-9b63-38a56548fc24/) | `Ionosphere Arc Vtec Calibration` | code-bias, geodesy, gnss, ionosphere, pseudorange, total-electron-content | unregistered | unsealed | - |
| [`aec90ff1-0265-5d75-8e0e-49786360d336`](aec90ff1-0265-5d75-8e0e-49786360d336/) | `Erza Day Count Accrued` | 30-360, accrued-interest, act-act-icma, act-act-isda, bond-math, conventions, day-count, fixed-income, isda-2006 | unregistered | unsealed | - |
| [`c59f8b2a-0606-5f02-bed5-52937e5ab468`](c59f8b2a-0606-5f02-bed5-52937e5ab468/) | `Antenna Phase Centre Correction` | antenna-calibration, antex, geodesy, gnss, phase-centre, positioning | unregistered | unsealed | - |
| [`c7faca71-82cd-5ad3-9dc5-c161793ddb25`](c7faca71-82cd-5ad3-9dc5-c161793ddb25/) | `Flight Duty Period Legality` | air-carrier, constraint-checking, crew-scheduling, duty-time, regulatory-compliance, roster-audit | unregistered | unsealed | - |
| [`d427488f-59b7-505a-bd03-bed97d147e38`](d427488f-59b7-505a-bd03-bed97d147e38/) | `D427488F 59B7 505A Bd03 Bed97D147E38` | algorithm-a, consensus, interlaboratory, metrology, proficiency-testing, robust-statistics, uncertainty, zeta-score | unregistered | unsealed | - |
| [`e9474235-0323-5e54-9171-c5b80089ad7e`](e9474235-0323-5e54-9171-c5b80089ad7e/) | `Tidal Harmonic Prediction` | geophysics, harmonic-analysis, oceanography, tidal-prediction, tides, time-series | unregistered | unsealed | - |
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
    staging --> samples["samples/<br/>10 of 10"]
    samples --> delivery["delivery/<br/>0 of 10000"]
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
