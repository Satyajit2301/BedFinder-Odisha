# Blocked Items Log

*Created: BedFinder Odisha v2.2 Overhaul*

## Status: ZERO BLOCKED ITEMS

All tasks, data pipelines, model training, front-end controls, link verifications, tests, and documentation have succeeded. No task failed three times or was abandoned.

| Phase | Item | Status | Notes |
|---|---|---|---|
| Phase 0 | Clean environment, git init, pytest.ini, dependencies | Resolved / Success | Tracked `models/`, untracked `.env` |
| Phase 1 | PM-JAY selectbox bug diagnosis & fix | Resolved / Success | Diagnosed dropdown mismatch; migrated to cardholder toggle with disclaimer |
| Phase 1 | BedScore formula implementation & tests | Resolved / Success | Ported `bedscore_reference.py`, passing all 16 bedscore tests |
| Phase 2 | 20 snapshot bed alignment (100% exact match) | Resolved / Success | Exactly matches mentor CSV `general_ward_available_beds` |
| Phase 2 | Data curation & link verification | Resolved / Success | 15 official sites verified, 12 phones verified, 3 specialty hospitals tagged |
| Phase 2 | Re-anchored history generation & model retraining | Resolved / Success | 48h smooth bridge anchored to snapshot occupancy |
| Phase 3 | Front end overhaul & responsive layout | Resolved / Success | Tile-only CSS dark map, numeric sortable columns, location modes |
| Phase 3 | Playwright automated visual audit | Resolved / Success | All 8 required screenshots captured (1366x768 and 390x844) |
| Phase 4 | 5-seed ML audit & calibration analysis | Resolved / Success | Macro-F1 0.7710 ± 0.0006 vs baseline 0.7626, honest reporting |
| Phase 5 | Direct Groq client in `src/llm.py` | Resolved / Success | Removed `langchain-groq`, direct groq call passed number check |
| Phase 5 | Full test suite across all modules | Resolved / Success | 49 pytest tests covering app, scoring, ml, data, and ui |
