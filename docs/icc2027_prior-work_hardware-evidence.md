# ICC Prior-Work Hardware-Evidence Audit

This note supports the MeshEcho ICC 2027 submission decision about physical
validation. It is a traceable practice sample, not a systematic census of all
ICC acceptances. The sample was collected on 2026-09-19 from DOI metadata and
abstract records exposed by Crossref/OpenAlex, then checked against the paper
titles and ICC proceedings metadata. An abstract can miss details in the full
paper, so the labels below are deliberately conservative.

## Venue requirement

The [ICC 2027 submission guidelines](https://icc2027.ieee-icc.org/submission-guidelines)
specify English, IEEE 10-point conference format, a maximum of six printed
pages for initial review, PDF/EDAS submission, originality, and exact title and
author-list consistency. They do not state that every paper must include a
physical prototype, testbed, or hardware measurement. Registration and author
presentation are required after acceptance for proceedings/Xplore publication;
that is a publication condition, not a hardware-evidence condition.

## ICC sample

| Year | Paper | DOI | Evidence visible in abstract | Classification |
| --- | --- | --- | --- | --- |
| 2018 | To et al., *Simulation of LoRa in NS-3: Improving LoRa Performance with CSMA* | [10.1109/icc.2018.8422800](https://doi.org/10.1109/icc.2018.8422800) | NS-3 module compared with measurements from a real-world testbed; simulator then evaluates CSMA. | Simulation + testbed validation |
| 2019 | Benkhelifa et al., *Minimum Throughput Maximization in LoRa Networks Powered by Ambient Energy Harvesting* | [10.1109/icc.2019.8761478](https://doi.org/10.1109/icc.2019.8761478) | Collision expressions, SF/energy-harvesting optimization, and algorithmic comparisons; no physical testbed claim in abstract. | Analysis + numerical/algorithmic evaluation |
| 2019 | Amichi et al., *Spreading Factor Allocation Strategy for LoRa Networks Under Imperfect Orthogonality* | [10.1109/icc.2019.8761235](https://doi.org/10.1109/icc.2019.8761235) | Matching-based SF allocation with numerical results against baselines. | Analysis + numerical evaluation |
| 2020 | Georgiou et al., *Coverage Scalability Analysis of Multi-Cell LoRa Networks* | [10.1109/icc40277.2020.9149081](https://doi.org/10.1109/icc40277.2020.9149081) | Stochastic-geometry model and mathematical coverage analysis; no hardware claim in abstract. | Analytical |
| 2020 | Rochester et al., *Lightweight Carrier Sensing in LoRa: Implementation and Performance Evaluation* | [10.1109/icc40277.2020.9149103](https://doi.org/10.1109/icc40277.2020.9149103) | Real-world LoRa measurement results plus a custom simulator for energy/scalability. | Simulation + measurements |
| 2020 | Hamdi et al., *Dynamic Spreading Factor Assignment in LoRa Wireless Networks* | [10.1109/icc40277.2020.9149243](https://doi.org/10.1109/icc40277.2020.9149243) | Proposed assignment evaluated in terms of symbol-error rate via numerical simulations. | Simulation-only in abstract |
| 2020 | Afisiadis et al., *Coded LoRa Frame Error Rate Analysis* | [10.1109/icc40277.2020.9148806](https://doi.org/10.1109/icc40277.2020.9148806) | Analytical FER expressions compared with Monte Carlo simulations. | Analysis + Monte Carlo |
| 2020 | Tu et al., *A New Closed-Form Expression of the Coverage Probability for Different QoS in LoRa Networks* | [10.1109/icc40277.2020.9148720](https://doi.org/10.1109/icc40277.2020.9148720) | Closed-form coverage/ASE framework verified with Monte Carlo simulations. | Analysis + Monte Carlo |
| 2017 | Farnham et al., *Proactive Wireless Sensor Network for Industrial IoT* | [10.1109/icc.2017.7997158](https://doi.org/10.1109/icc.2017.7997158) | Adaptive frequency hopping and proactive routing are described as an industrial-IoT method; abstract does not establish a required physical testbed. | Method paper; hardware status not established from abstract |
| 2022 | Shaafi et al., *Wireless Body Sensor Networks for Sign Language Recognition with Real-time Data Analysis* | [10.1109/icc45855.2022.9838474](https://doi.org/10.1109/icc45855.2022.9838474) | Acquired inertial and muscular data and experimental classifier comparisons. | Application/data experiment |

## Interpretation for MeshEcho

The sample contains ICC papers whose abstracts are explicitly analytical or
simulation-based, alongside papers that add measurements or testbed validation.
Therefore, a physical demonstration is not a universal ICC submission gate.
The stronger and more defensible standard for a simulation-only MeshEcho paper
is:

1. define the channel, propagation, collision/capture, routing, and airtime
   model precisely;
2. use shared topologies, traffic, seeds, and reception randomness across
   protocols;
3. report baselines, ablations, uncertainty, quality gates, and negative or
   stress cases;
4. release code, raw results, summaries, and an exact reproduction command;
5. state what simulation cannot establish, especially radio sensitivity,
   waveform interference, timing, duty-cycle enforcement, queue behavior, and
   hardware variation.

Hardware or hardware-in-the-loop validation would materially strengthen
external validity and is a sensible follow-up for MeshEcho, but the current
paper must not imply that the SX126x/SX127x firmware prototype has been used to
produce the reported results. The manuscript therefore labels the evidence as
simulation-only and lists physical validation as future work.

## Retrieval notes

- Crossref was used to verify DOI, title, year, and ICC proceedings metadata.
- OpenAlex abstract records were used to identify explicit terms such as
  ``testbed'', ``measurements'', ``real-world'', ``numerical simulations'', and
  ``Monte Carlo''.
- The sample is intended to document venue precedent and method diversity; it
  should not be presented as an acceptance-rate estimate or as proof that any
  individual paper was accepted solely because it lacked hardware.
