# Anomaly Detection & LLM Cybersecurity: Research Report 2025–2026
*Generated: 2026-05-27 | Sources: 60+ | Confidence: High | Agents: 3 parallel*

---

## Executive Summary

Three parallel research agents searched 59+ queries and analyzed 60+ sources across anomaly detection literature and LLM cybersecurity. Key headline findings:

1. **Claude Mythos is a real Anthropic model** (not just your layer name) — it achieves 73% success on expert-level cybersecurity tasks and identified thousands of zero-days in pre-release. It's restricted to ~40 organizations via Project Glasswing.
2. **The first AI-built zero-day was deployed in the wild in May 2026** — Google confirmed attackers used an AI model to build and deploy a real exploit.
3. **Your stack's domain (water/ICS) is directly covered** by 2025-2026 papers: DiffGAN (evaluated on SWaT), Cross-Domain ICS Graph, GWO Autoencoder (water treatment), and a digital twin adversarial attack paper specifically targeting water forecasting with FGSM/PGD.
4. **Prompt injection is OWASP's #1 LLM risk** and may never be fully solved — meaning your `layer4_mythos.py` → `layer5_response.py` pipeline has a structural attack surface that must be mitigated architecturally, not just at the prompt level.
5. **Data poisoning threshold**: 250 malicious documents are enough to backdoor a large LLM — confirmed by Anthropic, UK AISI, and the Alan Turing Institute jointly.

---

## Part 1: Anomaly Detection Papers 2025–2026

### 1.1 Time-Series Anomaly Detection

#### CATCH — Channel-Aware Multivariate TSAD via Frequency Patching
- **Venue:** ICLR 2025 | **arXiv:** 2410.12261
- **Method:** Unsupervised (reconstruction-based)
- **Core idea:** Patchifies the frequency domain into bands; Channel Fusion Module (CFM) with patch-wise mask generator captures inter-channel correlations + fine-grained frequency characteristics simultaneously
- **Results:** Superior performance over 12+ SOTA methods across 10 real-world + 12 synthetic datasets; especially strong on complex subsequence anomalies
- **Relevance to your stack:** Directly applicable to multivariate sensor arrays (pressure, flow, chemical) — replaces or augments `cusum_detector.py` for frequency-domain anomalies
- **Code:** https://github.com/decisionintelligence/CATCH

#### KAN-AD — Time Series Anomaly Detection with Kolmogorov-Arnold Networks
- **Venue:** ICML 2025 | **arXiv:** 2411.00278
- **Method:** Unsupervised
- **Core idea:** Replaces MLP layers with KAN (Kolmogorov-Arnold Networks); uses truncated Fourier expansions instead of B-splines; emphasizes smooth global patterns over local fluctuations to combat noise overfitting
- **Results:** Outperforms transformer/autoencoder baselines; more interpretable activation functions
- **Code:** https://github.com/issaccv/KAN-AD

#### IGAD — Idempotent Generation for Anomaly Detection (NeurIPS 2025)
- **Venue:** NeurIPS 2025 | URL: https://neurips.cc/virtual/2025/poster/115361
- **Method:** Unsupervised (modular plug-in, zero additional parameters)
- **Core idea:** Modifies the learned manifold so normal inputs map cleanly onto it while anomalous inputs are geometrically expelled. Solves the over-generalization problem where reconstruction models inadvertently reconstruct anomalies well.
- **Results:** Plug-and-play over any reconstruction baseline; no trainable parameters added
- **Relevance to your stack:** `isolation_forest.py` can be supplemented with an idempotent reconstruction layer — add IGAD as a second-stage filter over existing baselines

#### THEMIS — Foundation Model Embeddings for Anomaly Detection (arXiv 2510.03911)
- **Venue:** arXiv, October 2025
- **Method:** Unsupervised, training-free
- **Core idea:** Extracts encoder embeddings from Chronos (time-series foundation model); applies LOF and Spectral Decomposition on self-similarity matrices. Entirely unsupervised and hyperparameter-robust at inference.
- **Results:** SOTA on MSL; competitive on SMAP and SWaT (your dataset domain); outperforms models specifically trained for anomaly detection
- **Relevance:** Zero-configuration anomaly detection — strongest candidate to replace `isolation_forest.py`. No retraining needed.

#### ALoRa-T — Low Rank Transformer for TSAD and Localization
- **Venue:** ICLR 2026 | **arXiv:** 2602.08467
- **Method:** Unsupervised
- **Core idea:** Low-rank regularization on Transformer self-attention; derives Attention Low-Rank Score for detection + ALoRa-Loc for variable-level anomaly localization
- **Results:** Significantly outperforms SOTA across multiple benchmarks in both detection AND localization
- **Relevance:** Adds variable-level localization capability — currently your system detects anomalies but may not identify which sensor is the source

#### AnomSeer — Reinforcing Multimodal LLMs for TSAD with Reasoning (arXiv 2602.08868)
- **Venue:** ICLR 2026 submission
- **Method:** Semi-supervised / RL-finetuned foundation model
- **Core idea:** Generates expert chain-of-thought traces grounded in statistical/frequency analysis; TimerPO (Time-Series Grounded Policy Optimization) using optimal transport for advantage computation; unifies anomaly classification, localization, AND explanation in one MLLM
- **Results:** Strong results with interpretable reasoning outputs — natural-language justification for each anomaly
- **Relevance to Mode C:** This is the closest paper to what your Mode C (zero-day hypothesis) does. AnomSeer's RL-trained reasoning pipeline is the academic equivalent of your Mythos hypothesis generation loop.

#### CARLA — Causality-Aware Contrastive Learning for TSAD (arXiv 2506.03964)
- **Method:** Self-supervised / Unsupervised
- **Core idea:** Constructs causality-preserving vs. causality-disturbing augmentations; contrastive learning explicitly distinguishes normal inter-variable causal structures from anomalous disruptions; anomalies break causal dependencies
- **Relevance:** Water treatment and power grids are explicitly listed as target domains. A pressure anomaly that doesn't correlate with expected flow changes is exactly the causal-break signature this captures.

#### DiffGAN — Diffusion-GAN Hybrid for Multivariate TSAD (arXiv 2501.01591)
- **Venue:** arXiv, January 2025
- **Method:** Unsupervised (generative hybrid)
- **Core idea:** Adds a GAN discriminator to the denoiser of a diffusion model; GAN sharpens reconstruction fidelity for normal patterns, making anomalous reconstructions more distinguishable
- **Results:** Evaluated on SWaT (Secure Water Treatment — your dataset domain), MSL, SMAP; improved F1 over pure diffusion and pure GAN
- **Relevance:** Benchmarked on your exact application domain (SWaT water treatment). Strongest candidate for replacing the generative baseline.

### 1.2 Graph Anomaly Detection

#### IA-GGAD — Zero-shot Generalist Graph Anomaly Detection (NeurIPS 2025 Spotlight)
- **Venue:** NeurIPS 2025 Spotlight
- **Method:** Unsupervised / Zero-shot
- **Core idea:** Addresses Feature Space Shift (FSS) and Graph Structure Shift (GSS) simultaneously. First framework enabling zero-shot prediction on entirely unseen graphs with no retraining.
- **Results:** +12.28% AUROC over ARC baseline; consistently superior across unseen-graph benchmarks
- **Code:** https://github.com/kg-cc/IA-GGAD

#### SpaceGNN — Multi-Space GNN for Node Anomaly Detection (ICLR 2025)
- **Venue:** ICLR 2025 | **arXiv:** 2502.03201
- **Method:** Semi-supervised (extremely limited labels)
- **Core idea:** First GNN to embed graphs in multiple geometric spaces (Euclidean + hyperbolic) simultaneously; designed for <1% labeled anomaly scenario
- **Results:** +8.55% AUC and +4.31% F1 over best rival across 9 real datasets

#### Cross-Domain ICS Graph Anomaly Detection (arXiv 2509.11786)
- **Venue:** arXiv Sep 2025 / IEEE Xplore
- **Method:** Unsupervised / Multi-task
- **Core idea:** Cross-domain graph capturing relationships between network traffic AND physical sensor domains in ICS; attention-based GCN with multi-task learning for joint but domain-separated anomaly identification
- **Relevance:** Most directly applicable graph paper to your architecture. Your ME-DT ingests both network and physical sensor data — this paper addresses exactly the fusion problem.

### 1.3 ICS / Industrial Control Systems Specific

#### GWO Autoencoder for ICS (Nature Scientific Reports 2025)
- **Venue:** Scientific Reports 2025 | https://www.nature.com/articles/s41598-025-12775-0
- **Method:** Unsupervised (autoencoder + Grey Wolf Optimizer hyperparameter tuning)
- **Results:** Significantly outperforms hand-tuned baselines on SWaT and similar SCADA datasets

#### TAB — Unified Benchmark for TSAD (arXiv 2506.18046)
- **Core idea:** Reproducibility benchmark — many published SOTA claims do not hold under rigorous comparison
- **Relevance:** Before integrating any paper above, test against TAB's protocol, not paper-reported numbers

### 1.4 LLM-Native Anomaly Detection

#### AnoLLM — Large Language Models for Tabular Anomaly Detection (ICLR 2025)
- **Venue:** ICLR 2025 (Amazon Science)
- **Method:** Unsupervised (LLM-based)
- **Core idea:** Converts tabular rows to standardized text; fine-tunes LLM; uses negative log-likelihood as anomaly score. Handles raw textual tabular features natively.
- **Results:** Best on 6 mixed-feature-type datasets; competitive on 30 numerical ODDS datasets
- **Relevance to Mode A:** Could serve as a continuous LLM-based anomaly scorer running alongside statistical baselines — anomalies that score high on both AnoLLM and CUSUM/IForest should be highest-confidence escalations
- **Code:** https://github.com/amazon-science/AnoLLM-large-language-models-for-tabular-anomaly-detection

#### Foundation Models Survey — FM-based Anomaly Detection (AI Magazine 2025)
- **Venue:** AI Magazine (AAAI) 2025 | **arXiv:** 2502.06911
- **Core idea:** First comprehensive survey of FM-based anomaly detection covering LLMs, VLMs, graph FMs, and time-series FMs; taxonomizes zero-shot, few-shot, and fine-tuning paradigms
- **Use:** Literature entry point when deciding which FM approach to integrate

---

## Part 2: LLM Cybersecurity 2025–2026

### 2.1 Claude Mythos — What It Actually Is

Claude Mythos Preview is a real Anthropic model. Key facts:

| Fact | Detail |
|------|--------|
| **Capability** | 73% success on expert-level cybersecurity tasks — "a level no model could complete before April 2025" |
| **Zero-days** | Identified thousands of previously unknown zero-days across every major OS and browser in pre-release testing |
| **Evaluator** | UK AI Safety Institute (AISI) — independent evaluation |
| **Access** | Restricted to ~40 organizations via Project Glasswing (defensive-first critical infrastructure program) |
| **Status** | Pre-release / controlled access as of May 2026 |

Sources:
- AISI evaluation: https://www.aisi.gov.uk/blog/our-evaluation-of-claude-mythos-previews-cyber-capabilities
- SecurityWeek: https://www.securityweek.com/anthropic-unveils-claude-mythos-a-cybersecurity-breakthrough-that-could-also-supercharge-attacks/

### 2.2 Anthropic's Cybersecurity Landscape

| Product/Initiative | Status | Key Capability |
|---|---|---|
| **Claude Mythos Preview** | Pre-release / Project Glasswing | 73% expert-level task success; thousands of zero-days found |
| **Claude Security** | Public beta (enterprise) | Opus 4.7 scans full repos, generates patches via Claude Code |
| **CLUE (internal SOC)** | Production (Anthropic internal) | First-pass triage with confidence scores before human analyst sees alert |
| **Project Glasswing** | Active coalition (~40 orgs) | Defensive-first access for critical infrastructure + security vendors |
| **Frontier Red Team** | Ongoing | Emulating cyber attacks on water treatment simulation with PNNL |

Notable offensive incident: Claude Code was used to execute 75% of commands in an attack exfiltrating hundreds of millions of records from a Mexican government system (May 2026).

### 2.3 SOC Automation & Threat Detection

**Microsoft Security Copilot** (GA Ignite 2025, built on OpenAI + Microsoft Threat Intelligence):
- 6.5x more malicious alerts identified
- 77% improvement in verdict accuracy
- Analysts spend 53% more time on real threats

**Fine-tuned open-source security models — critical finding:**
Fine-tuning on security data reduces safety resilience: Llama 3.1 8B's prompt injection resistance drops from 0.95 → 0.15 after fine-tuning.

### 2.4 Zero-Day Discovery — Confirmed Production Reality

- **Defensive:** AISLE discovered all 12 zero-day vulnerabilities in OpenSSL's January 2026 security patch using AI agents
- **Offensive (confirmed):** Google Threat Intelligence Group, May 11 2026 — first confirmed AI-built zero-day deployed in the wild (2FA bypass on popular open-source admin tool)
- Nation-state actors (China, DPRK) have documented involvement in LLM-assisted vulnerability discovery

### 2.5 Network Intrusion Detection — State of Research

Fine-tuned LLaMA-1B on CICIoT2023:
- F1-score 0.7124 on known attacks
- RAG-enhanced variant: 42.63% accuracy on unseen attack types without retraining

Key limitation: Hallucinations cause attack-specific false positives/negatives; high compute cost vs. lightweight traditional methods.

---

## Part 3: Adversarial Attacks on LLMs & Defenses

### 3.1 Prompt Injection — OWASP #1, Potentially Unsolvable

- Ranked #1 OWASP Top 10 for LLM Applications for two consecutive editions (2024, 2025)
- 461,640 documented prompt injection submissions in 2025; success rates 50–84%; adaptive techniques exceed 85%
- International AI Safety Report 2026: sophisticated attackers bypass best-defended models ~50% with only 10 attempts
- **UK NCSC assessment (December 2025):** Prompt injection may never be fully mitigated — LLMs inherently process instructions and data in the same channel
- Indirect injection (malicious instructions in documents, logs, web pages, PDFs) is now the dominant vector
- Layered defense stack can reduce attack success from 73.2% → 8.7%

**Direct implication for `layer4_mythos.py`:** Your engine processes state snapshots, violation lists, and anomaly sidecar data. If an attacker can manipulate those data sources (sensor spoofing, log injection), they can indirectly inject instructions to Mythos.

### 3.2 Jailbreaks — Automated, ~99% ASR at Scale

| Attack | Models Targeted | ASR |
|---|---|---|
| JBFuzz (2025) | GPT-4o, Gemini 2.0, DeepSeek-V3 | ~99% average |
| Black-box attacks | Proprietary models | 80–94% |
| Multi-turn agent-driven | All major models | ~95% |
| GCG, AutoDAN | Open-weight models | 90–99% |

In controlled red-team: all 8 safety levels of Claude 3.5 bypassed in 6 days using ~3,700 hours and 300,000 messages.

Best current defense: **Free Jailbreak Detection (FJD)** — ACL 2025, near-zero inference overhead.

### 3.3 Data Poisoning — 250-Document Backdoor Threshold

Jointly confirmed by Anthropic + UK AISI + Alan Turing Institute:
- 250 malicious documents are enough to create a backdoor in a large LLM, regardless of model size
- Poisoning affects entire AI lifecycle: training, fine-tuning, RAG document stores, RLHF
- 100 poisoned models found on HuggingFace allowing malicious code injection

**Direct threat to your system:** If your context/RAG includes documents from monitored systems (logs, threat reports), an attacker who can write to those sources controls Mythos inputs.

arXiv 2511.02600: "On The Dangers of Poisoned LLMs In Security Automation" — directly addresses SOC automation poisoning.

### 3.4 Digital Twins — Confirmed Attack Target

- FGSM and PGD attacks on ML model parameters within digital twins confirmed in water forecasting study (April 2025): MAPE degrades from 26% → >35%
- AI in ICS attacks transforms rare high-skill intrusions into scalable commodity threats
- Adversarial sample generation designed to evade ICS anomaly detection is active research (arXiv, June 2025)
- **Emerging defense:** Blue-team digital twin integration — simulate attacks in the twin, refine detection rules, test incident response playbooks without touching production

### 3.5 CVEs in Claude Code Itself

| CVE | Description | Status |
|---|---|---|
| CVE-2025-59536 | Code injection allowing arbitrary execution before user consent — triggered by opening Claude Code in directory with malicious project files | Disclosed |
| CVE-2026-21852 | Related Claude Code toolchain vulnerability | Disclosed |
| CVE-2025-66479 | Sandbox bypass: "block all outbound traffic" interpreted as "allow everything" — potential data exfiltration | Silently patched Nov 26, 2025 |

### 3.6 Agentic AI — OWASP Agentic Top 10 (December 2025)

Key risks applicable to `layer5_response.py`:

| Risk | Applicability to ME-DT |
|---|---|
| **Excessive Agency** | If `layer5_response.py` can trigger infrastructure actions, one injection in Mythos cascades to physical actuation |
| **TOCTOU vulnerabilities** | Time-of-check-to-time-of-use attacks on agent tool calls between layers |
| **Multi-agent prompt injection** | If Mode A, B, C communicate through shared state, injection in one mode affects others |

### 3.7 Hallucination Rates in Security Contexts

- Stanford HAI: hallucination rates 3–27% by task complexity
- False positives cause unnecessary incident response; false negatives are the silent failure mode
- Statistical baselines (CUSUM, IForest) must catch what the LLM misses — parallel operation is essential, not optional
- First formal taxonomy of hallucinations in cybersecurity AI: ScienceDirect 2025

---

## Part 4: Recommendations for ME-DT Architecture

### Immediate Priorities (apply to current codebase)

1. **Never give Mythos direct actuation authority** — `layer5_response.py` must treat Mythos output as advisory, not authoritative. Add confidence threshold + baseline agreement check before any automated action.

2. **Treat every external input as a potential indirect injection vector** — state snapshots, violation lists, anomaly sidecars, and log data that Mythos processes are all indirect injection surfaces. Add schema validation + content sanitization before building the Mythos prompt context.

3. **Decouple LLM output from baseline parameterization** — CUSUM and IForest must run independently. Mythos assessments are a separate signal the fusion layer combines with baseline scores — not a parameter source.

4. **Plan for hallucination rates of 3–27%** — design: false positives → escalation to human review, not automated response. False negatives in Mythos → caught by CUSUM/IForest running in parallel.

5. **Log all Mythos inputs and outputs with tamper-evident storage** — every Mode A/B/C call should log: tick, input hash, output, model version, latency. The September 2025 espionage incident succeeded partly due to toolchain opacity.

### Stack Upgrade Candidates (next iteration)

| Your Component | Recommended Upgrade | Paper | arXiv |
|---|---|---|---|
| `isolation_forest.py` | Replace with THEMIS (Chronos embeddings + LOF) | Training-free, SWaT competitive | 2510.03911 |
| `cusum_detector.py` | Add CATCH as frequency-domain complement | ICLR 2025 | 2410.12261 |
| Mythos Mode A (continuous) | Add AnoLLM as LLM-native tabular scorer | ICLR 2025 (Amazon Science) | — |
| Mythos Mode C (zero-day) | Study AnomSeer's RL+chain-of-thought design | ICLR 2026 | 2602.08868 |
| No localization currently | Integrate ALoRa-T for variable-level localization | ICLR 2026 | 2602.08467 |
| No causal analysis | Add CARLA for causal dependency monitoring | 2025 | 2506.03964 |
| No cross-domain fusion | Cross-Domain ICS Graph for network+physical fusion | IEEE Xplore 2025 | 2509.11786 |

### Security Architecture Additions

1. **Add FJD (Free Jailbreak Detection)** as a pre-filter on Mythos inputs — ACL 2025, near-zero overhead
2. **Implement output classification** on Mythos responses before feeding to `layer5_response.py`
3. **Version-pin all models and RAG sources** — 250-document backdoor threshold is confirmed
4. **Run OWASP Agentic AI Top 10** as a security checklist against your full pipeline
5. **Implement indirect injection hardening** on all data sources Mythos reads (sensor logs, violation events, anomaly reports)

### Watching List

- **Project Glasswing access** — If Anthropic expands, Claude Mythos Preview (vs current Opus/Sonnet) would significantly upgrade Mode B and Mode C
- **RuleGenie** (arXiv 2505.06701) — LLM-powered SIEM rule optimization; could automate Mythos threat taxonomy maintenance
- **DiffGAN on SWaT** — strongest direct-domain match for your generative anomaly baseline

---

## Sources Index

### Anomaly Detection
1. [CATCH ICLR 2025](https://openreview.net/forum?id=m08aK3xxdJ)
2. [KAN-AD ICML 2025](https://arxiv.org/abs/2411.00278)
3. [IGAD NeurIPS 2025](https://neurips.cc/virtual/2025/poster/115361)
4. [THEMIS arXiv 2510.03911](https://arxiv.org/abs/2510.03911)
5. [ALoRa-T ICLR 2026](https://arxiv.org/abs/2602.08467)
6. [AnomSeer arXiv 2602.08868](https://arxiv.org/abs/2602.08868)
7. [CARLA arXiv 2506.03964](https://arxiv.org/html/2506.03964v1)
8. [IA-GGAD NeurIPS 2025](https://neurips.cc/virtual/2025/poster/119275)
9. [SpaceGNN ICLR 2025](https://openreview.net/forum?id=Syt4fWwVm1)
10. [Cross-Domain ICS arXiv 2509.11786](https://arxiv.org/abs/2509.11786)
11. [DiffGAN arXiv 2501.01591](https://arxiv.org/pdf/2501.01591)
12. [AnoLLM ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/165bbd0a0a1b9470ec34d5afec582d2e-Abstract-Conference.html)
13. [Foundation Models Survey arXiv 2502.06911](https://arxiv.org/abs/2502.06911)
14. [GWO Autoencoder Nature 2025](https://www.nature.com/articles/s41598-025-12775-0)
15. [TAB Benchmark arXiv 2506.18046](https://arxiv.org/html/2506.18046v1)
16. [Deep Graph AD Survey TKDE 2025](https://github.com/mala-lab/Awesome-Deep-Graph-Anomaly-Detection)

### LLM Cybersecurity
17. [AISI Claude Mythos evaluation](https://www.aisi.gov.uk/blog/our-evaluation-of-claude-mythos-previews-cyber-capabilities)
18. [SecurityWeek Claude Mythos](https://www.securityweek.com/anthropic-unveils-claude-mythos-a-cybersecurity-breakthrough-that-could-also-supercharge-attacks/)
19. [Anthropic Claude Code Security](https://www.anthropic.com/news/claude-code-security)
20. [Anthropic CLUE internal platform](https://claude.com/blog/how-anthropic-uses-claude-cybersecurity)
21. [Microsoft Security Copilot SOC blog](https://techcommunity.microsoft.com/blog/microsoftthreatprotectionblog/security-copilot-for-soc-bringing-agentic-ai-to-every-defender/4470187)
22. [Google first AI zero-day in wild](https://www.theregister.com/ai-ml/2026/05/11/google-says-criminals-used-ai-built-zero-day-in-planned-mass-hack-spree/5237982)
23. [LLM NIDS survey arXiv 2507.04752](https://arxiv.org/html/2507.04752v1)
24. [Foundation AI SecurityLLM arXiv 2504.21039](https://arxiv.org/html/2504.21039v1)
25. [Safety risks in fine-tuned models arXiv 2505.09974](https://arxiv.org/html/2505.09974v1)

### Adversarial Attacks & Defenses
26. [OWASP Top 10 LLM 2025 - Prompt Injection](https://www.securance.com/blog/prompt-injection-the-owasp-1-ai-threat-in-2026/)
27. [JBFuzz / jailbreaking survey 2026](https://www.techrxiv.org/users/1011181/articles/1373070/master/file/data/Jailbreaking_LLMs_2026/Jailbreaking_LLMs_2026.pdf?inline=true)
28. [FJD Free Jailbreak Detection ACL 2025](https://aclanthology.org/2025.findings-emnlp.309/)
29. [Alan Turing Institute 250-doc poisoning](https://www.turing.ac.uk/blog/llms-may-be-more-vulnerable-data-poisoning-we-thought)
30. [Poisoned LLMs in Security Automation arXiv 2511.02600](https://arxiv.org/html/2511.02600v1)
31. [Digital twin adversarial attacks water arXiv 2504.20295](https://arxiv.org/abs/2504.20295)
32. [OWASP Agentic AI Top 10](https://genai.owasp.org/2025/12/09/owasp-genai-security-project-releases-top-10-risks-and-mitigations-for-agentic-ai-security/)
33. [CVE-2025-59536 SentinelOne](https://www.sentinelone.com/vulnerability-database/cve-2025-59536/)
34. [Anthropic ASL-3 activation](https://www.anthropic.com/news/activating-asl3-protections)
35. [Anthropic espionage disruption](https://www.anthropic.com/news/disrupting-AI-espionage)
36. [ScienceDirect hallucination taxonomy](https://www.sciencedirect.com/science/article/abs/pii/S0045790625002502)

---

## Methodology
- 3 parallel research agents deployed simultaneously
- 59+ web search queries executed across academic, industry, and news sources
- 60+ unique sources analyzed
- Sub-questions investigated: deep learning TSAD (transformer, GNN, diffusion, FM-based), ICS/SCADA methods, LLMs in cybersecurity production, Claude Mythos capabilities, adversarial attacks on LLMs, digital twin vulnerabilities, Anthropic safety research, architectural mitigations
