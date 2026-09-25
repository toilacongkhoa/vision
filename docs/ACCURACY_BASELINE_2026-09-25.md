# Retrieval accuracy baseline — 2026-09-25

## Scope

This is an offline baseline for the labeled dataset at `docs/answerAndQuestion.jsonl`. It is diagnostic evidence, not an official DRES score. No query text was sent to an external translation service, and no live DRES endpoint was contacted.

| Item | Value |
|---|---|
| Dataset | 57 cases: 39 KIS, 16 Q&A, 2 TRAKE; KIS does not distinguish Textual from Video KIS. |
| Dataset SHA-256 | `7ca63442281c84cdcba01200e8df705504db3a2d655aa1c6afcdc05a0db5a208` |
| Data | SQLite index: 177,321 keyframes; vectors: `(177321, 512)` float32; local data manifest verified. |
| Data manifest SHA-256 | `314765820edc3b87ce515570868aeeeaf84d70c7e9f66e54aaea373fa8d4de62` |
| Runtime | Windows, Python 3.12.5 x64, CPU OpenCLIP `ViT-B-32/openai`, Torch 2.14.0+cpu. |
| OpenCLIP checkpoint SHA-256 | `e6d1bd7789aa45192b3bf90570a789b478bae1b74ebcce7eddd908e83a2b7c31` (605,143,284 bytes) |
| Source baseline | HEAD `29ae0774bac5f7521e328b013b7d14be8ab98114`; retrieval source unchanged in this run. |
| Translation | Offline translator model absent; local cache translated 1/55 non-TRAKE queries. Online translation disabled. |
| Candidate count | top-k 50. Metrics count one target per KIS/Q&A and four ordered targets per TRAKE. |

## Results

`R@k` and MRR are over 63 labeled event locations. “Case correct” requires the benchmark's full case rule, including Q&A answer evidence and complete ordered TRAKE sequence.

| Mode | Time window | Case correct | R@1 | R@5 | R@10 | R@50 | MRR | Warm latency p50/p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Semantic | 0 s (exact frame) | 0/57 | 0/63 | 0/63 | 0/63 | 0/63 | 0.0000 | 238/432 ms |
| Semantic | 5 s (diagnostic) | 0/57 | 0/63 | 0/63 | 0/63 | 0/63 | 0.0000 | 224/452 ms |
| OCR | 150 s (wide diagnostic) | 0/57 | 0/63 | 0/63 | 0/63 | 0/63 | 0.0000 | 566/1,210 ms |
| ASR | 5 s (diagnostic) | 1/57 | 1/63 | 1/63 | 1/63 | 1/63 | 0.0159 | 1,259/3,901 ms |
| Hybrid semantic+ASR | 5 s (diagnostic) | 1/57 | 0/63 | 1/63 | 1/63 | 1/63 | 0.0079 | 1,600/3,573 ms |
| Semantic | 150 s (wide diagnostic) | 2/57 | 0/63 | 0/63 | 2/63 | 2/63 | 0.0079 | 269/517 ms |
| ASR | 150 s (wide diagnostic) | 7/57 | 2/63 | 2/63 | 3/63 | 7/63 | 0.0358 | 705/1,099 ms |
| Hybrid semantic+ASR | 150 s (wide diagnostic) | 8/57 | 0/63 | 3/63 | 4/63 | 8/63 | 0.0232 | 1,032/1,916 ms |

The 150-second window is included only to show sensitivity to temporal tolerance. It is not treated as competition policy. Results are poor even under this wide window. The 5-second rows are also exploratory because the accepted tolerance has not been confirmed.

## Current workstation rerun

On 2026-09-25, `tools/benchmark_multimodal.py --json --limit 57` was rerun locally with the QuickGELU default, top-k 50, diagnostic 150-second temporal window, and online translation disabled. The local translation cache reported 99 entries. Counts below report full-case correctness plus event-location recall. They are diagnostic because the temporal window is unconfirmed and the labeled queries are mostly untranslated.

| Mode | Case correct | R@5 | R@10 | R@50 | MRR | Search latency p50/p95 |
|---|---:|---:|---:|---:|---:|---:|
| Semantic | 2/57 | 2/63 | 2/63 | 2/63 | 0.0132 | 249/442 ms |
| OCR | 0/57 | 0/63 | 0/63 | 0/63 | 0.0000 | 575/755 ms |
| ASR | 7/57 | 2/63 | 3/63 | 7/63 | 0.0358 | 658/870 ms |
| Hybrid | 7/57 | 4/63 | 4/63 | 8/63 | 0.0265 | 1,077/1,952 ms |

This first run met the proposed 5-second text-search p95 on the current CPU. It does not establish performance on another machine. The later repeat below shows material latency variation and an ASR threshold miss. The benchmark output and temporary report were not added to Git; this table records aggregate metrics only.

### Repeat on the same workstation

The local-only command `tools/benchmark_multimodal.py --limit 57 --top-k 50 --tolerance-seconds 150` was rerun on 2026-09-25 with the same dataset, model, cache-only translation setting and diagnostic window. All four strategies completed with zero errors. Event recall and full-case correctness were unchanged from the preceding current-workstation run, while latency was higher under the load present during this repeat.

| Mode | Case correct | R@1 | R@5 | R@10 | R@50 | MRR | Search latency p50/p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Semantic | 2/57 | 0/63 | 2/63 | 2/63 | 2/63 | 0.0132 | 924/1,805 ms |
| OCR | 0/57 | 0/63 | 0/63 | 0/63 | 0/63 | 0.0000 | 2,128/4,621 ms |
| ASR | 7/57 | 2/63 | 2/63 | 3/63 | 7/63 | 0.0358 | 2,322/5,900 ms |
| Hybrid | 7/57 | 0/63 | 4/63 | 4/63 | 8/63 | 0.0265 | 1,975/3,520 ms |

Across recorded runs, p95 spans 442–1,805 ms for semantic, 755–4,621 ms for OCR, 870–5,900 ms for ASR, and 1,952–3,520 ms for hybrid. ASR exceeded the proposed 5-second p95 target in this repeat; the prior run met it. Keep the target open until repeated runs under recorded, comparable load confirm it. The 57 labeled cases still do not distinguish Textual/Video KIS, and this retrospective split is not a new holdout.

## Initial tuning experiment

The dataset IDs provide a provisional split: `query-p2-*` for tuning (27 cases, 30 targets) and `query-p3-*` for holdout (30 cases, 33 targets). `tools/benchmark_sentence_fusion.py` compared the current semantic splitter with splitting on sentence-ending punctuation, using the same local-only translator setting and a diagnostic 5-second window.

| Split | Variant | R@50 | MRR | Latency p50/p95 |
|---|---|---:|---:|---:|
| p2 tuning | Current splitter | 0/30 | 0.0000 | 183/340 ms |
| p2 tuning | Sentence split | 0/30 | 0.0000 | 224/424 ms |
| p3 holdout | Current splitter | 0/33 | 0.0000 | 228/526 ms |
| p3 holdout | Sentence split | 0/33 | 0.0000 | 242/503 ms |

No runtime change was accepted: sentence splitting did not recover a labeled target on either split and increased median latency. This result is limited by untranslated Vietnamese queries; it does not disprove sentence decomposition after approved local translation is available.

## Data and interpretation checks

- All 63 labeled locations refer to videos present in the index. Fifty target frames exactly match indexed keyframes. The other 13 are KIS targets whose nearest indexed frame is within 3 seconds; all Q&A and TRAKE target frames match exactly.
- This DB has no `ocr_fts` or `asr_fts` table. It contains nonempty OCR text on 69,160 rows and ASR text on 159,256 rows, so the current implementation uses its LIKE fallback over the keyframe table for both modes.
- The benchmark's `p2`/`p3` prefixes support a retrospective split, not a pre-registered one. Both p2 and p3 have now been used in the sentence-split and QuickGELU comparisons; p3 is no longer an untouched holdout for future tuning.
- Semantic results are not representative of the configured online-translation path: only 1/55 local/cache translations was available, and the offline translation model is missing. External translation was deliberately left off because it would transmit the labeled query text.
- Baseline HEAD emitted a QuickGELU mismatch warning (`quick_gelu=False` model config vs `quick_gelu=True` pretrained tag). The matched QuickGELU model variant was then tested separately on both provisional splits before changing the default.
- The current benchmark helper now discovers the dataset under `docs/` by default. Run `python tools/benchmark.py --tolerance-seconds 0` for exact-frame diagnostics, and specify a reviewed time window explicitly for other comparisons.

## Next P2 work

### QuickGELU alignment experiment

The baseline used `ViT-B-32`, which emits the warning above. The same checkpoint was also run as `ViT-B-32-quickgelu`, which matches the pretrained tag. With the diagnostic 150-second window, p2 remained 1/27 correct and p3 remained 1/30; R@50 did not fall (p2 1/30, p3 1/33). The matched variant moved the p2 hit from rank 3 to 2 and the p3 Q&A hit from rank 6 to 3, increasing MRR from 0.0111 to 0.0167 on p2 and 0.0051 to 0.0101 on p3. At 5 seconds, both variants had 0/30 p2 and 0/33 p3 target hits. The matched model's p95 remained below 0.7 seconds in these slices. The default is now `ViT-B-32-quickgelu`; the held-out change improves rank without reducing recall, but this remains a small, untranslated dataset and must be rechecked on every machine.

Next install the approved offline translation model or provide approved translated query variants. Before further tuning, create a new untouched holdout set; the current p3 cases have already been inspected in two experiments. Add Video KIS and larger TRAKE samples with valid descriptions and complete ordered labels. Compare query decomposition and semantic–OCR/ASR fusion; accept a change only if holdout quality does not fall and latency remains within the budget.
