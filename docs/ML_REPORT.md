# ML Evaluation and Calibration Report (BedFinder Odisha v2.3)

> **Evaluation Date:** 2026-10-11  
> **Dataset:** `data/history.csv` (69,120 hourly snapshots, 90 days, anchored to mentor snapshot)  
> **Model:** HistGradientBoostingClassifier with balanced class weighting  
> **Evaluation Protocol:** 80/20 time split with 6h horizon gap across 5 random seeds against Persistence Baseline  

---

## 1. Executive Summary & Honest Wording

The machine learning classification model achieves a mean Macro-F1 of **0.7711 ± 0.0006** across 5 independent seeds.
In comparison, the simple **persistence baseline** (predicting that the hospital's availability class stays unchanged over the travel horizon) achieves a mean Macro-F1 of **0.7626 ± 0.0000**.

**Honest Assessment:** ML is comparable overall, slightly worse at +1h (0.8576 vs 0.8636), and better at +4h to +6h (0.6947 vs 0.6610). Short-term occupancy is dominated by strong inertia, making persistence a strong benchmark for immediate triage.

---

## 2. Five-Seed Cross-Evaluation

| Seed | Model Macro-F1 | Model Accuracy | Persistence Macro-F1 | Persistence Accuracy | Model Brier Score |
|---|---|---|---|---|---|
| 42 | 0.7703 | 0.7726 | 0.7626 | 0.7637 | 0.0654 |
| 101 | 0.7715 | 0.7740 | 0.7626 | 0.7637 | 0.0655 |
| 2024 | 0.7708 | 0.7732 | 0.7626 | 0.7637 | 0.0655 |
| 777 | 0.7717 | 0.7739 | 0.7626 | 0.7637 | 0.0654 |
| 999 | 0.7709 | 0.7733 | 0.7626 | 0.7637 | 0.0655 |
| **Mean ± Std** | **0.7711 ± 0.0006** | **0.7734 ± 0.0006** | **0.7626 ± 0.0000** | **0.7637 ± 0.0000** | **0.0655** |

---

## 3. Confusion Matrix (Averaged across 5 seeds)

Classes: `0 = Full (<5% free)`, `1 = Limited (5–15% free)`, `2 = Available (>15% free)`

```
Predicted ->      Full (0)     Limited (1)   Available (2)
Actual
Full (0)           22566.8        4052.2         276.0
Limited (1)         4808.0       19669.8        4142.2
Available (2)        154.6        1968.6       10329.8
```

---

## 4. Horizon-Specific Breakdown

| Horizon (Hours) | Model Macro-F1 | Model Accuracy | Persistence Macro-F1 | Persistence Accuracy |
|---|---|---|---|---|
| +1h | 0.8576 | 0.8590 | 0.8636 | 0.8648 |
| +2h | 0.8058 | 0.8074 | 0.8052 | 0.8060 |
| +3h | 0.7648 | 0.7671 | 0.7596 | 0.7609 |
| +4h | 0.7310 | 0.7339 | 0.7223 | 0.7235 |
| +6h | 0.6947 | 0.6979 | 0.6610 | 0.6620 |

**Horizon Analysis:**
- At **+1h**, persistence is slightly superior (0.8636 vs 0.8576 Macro-F1) because occupancy rarely shifts across class boundaries within 60 minutes.
- At **+4h to +6h**, the ML model demonstrates superiority (0.6947 vs 0.6610 Macro-F1 at +6h) as diurnal discharge patterns and admissions overtake simple persistence.

---

## 5. Arrival Probability: Physics Queue Model vs ML

### Clarification of Metrics & Implementation
- **Which Model Drives `p_bed_arrival`:** `src/scoring.py` strictly uses the **Physics Queue Model (`p_bed`)** derived from Poisson birth-death queue dynamics:
  $$P = \Phi\left(\frac{\text{free} - 0.5}{\sigma}\right), \quad \sigma = \sqrt{2 \cdot \frac{\text{occupied}}{\text{ALOS} \times 24} \cdot \text{ETA}_h}$$
- **Why Physics is Used for Trip Arrival:**
  1. Guaranteed strict monotonicity: fewer beds or longer transit times strictly decrease arrival probability.
  2. Instantaneous responsiveness: reacts immediately to live bed updates and "What-If" simulation without retraining.
  3. No historical distribution shift vulnerability.
- **What the Brier Score (0.0654 vs 0.1256) Measures:**
  The Brier score measures the probabilistic calibration of the **3-class ML classifier** (`Available`, `Limited`, `Full`) across future horizons. It is **not** used to compute or justify the physics arrival probability `p_bed`.

---

## 6. ETA Sensitivity on Tight Capacity Hospitals

To demonstrate genuine queue risk decay, we evaluate arrival probability $P$ across forced free beds (1, 2, 3, 5, 10) at ETAs of 10, 30, 60, and 120 minutes for three representative hospital sizes:

| Hospital | Total Beds | Free Beds | P (10 min) | P (30 min) | P (60 min) | P (120 min) |
|---|---|---|---|---|---|---|
| Neelachal Hospital Pvt. Ltd. | 47 | 1 | 0.8945 | 0.7649 | 0.6952 | 0.6410 |
| Neelachal Hospital Pvt. Ltd. | 47 | 2 | 0.9999 | 0.9858 | 0.9393 | 0.8633 |
| Neelachal Hospital Pvt. Ltd. | 47 | 3 | 1.0000 | 0.9999 | 0.9955 | 0.9676 |
| Neelachal Hospital Pvt. Ltd. | 47 | 5 | 1.0000 | 1.0000 | 1.0000 | 0.9997 |
| Neelachal Hospital Pvt. Ltd. | 47 | 10 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| Apollo Hospitals Bhubaneswar | 300 | 1 | 0.6882 | 0.6115 | 0.5794 | 0.5563 |
| Apollo Hospitals Bhubaneswar | 300 | 2 | 0.9298 | 0.8027 | 0.7264 | 0.6648 |
| Apollo Hospitals Bhubaneswar | 300 | 3 | 0.9931 | 0.9224 | 0.8426 | 0.7614 |
| Apollo Hospitals Bhubaneswar | 300 | 5 | 1.0000 | 0.9949 | 0.9653 | 0.9003 |
| Apollo Hospitals Bhubaneswar | 300 | 10 | 1.0000 | 1.0000 | 0.9999 | 0.9969 |
| PGIMER & Capital Hospital | 720 | 1 | 0.6242 | 0.5725 | 0.5514 | 0.5364 |
| PGIMER & Capital Hospital | 720 | 2 | 0.8289 | 0.7083 | 0.6509 | 0.6081 |
| PGIMER & Capital Hospital | 720 | 3 | 0.9435 | 0.8198 | 0.7411 | 0.6763 |
| PGIMER & Capital Hospital | 720 | 5 | 0.9979 | 0.9504 | 0.8782 | 0.7952 |
| PGIMER & Capital Hospital | 720 | 10 | 1.0000 | 0.9998 | 0.9932 | 0.9596 |

### Key Finding on ETA Decay
- For **ample beds (10 free beds)**, arrival probability remains near 1.000 across urban trip durations.
- For **tight beds (1–2 free beds)**, arrival probability shows pronounced, realistic decay as travel time increases (e.g. for Apollo at 1 free bed, $P$ falls from 0.6882 at 10 min to 0.5563 at 120 min; for Neelachal at 1 free bed, $P$ drops from 0.8945 at 10 min to 0.6410 at 120 min).
