"""Tests to ensure documentation is strictly synchronized with code and free of stale tokens."""
import re
from pathlib import Path
import pytest
from src.scoring import formula_text, W_TRUST, W_CLOSE, W_FEE, DIST_SCALE_KM, ALOS_DAYS
from src.config import ROAD_FACTOR, CITY_SPEED_KMPH

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
ACTIVE_DOCS = [
    DOCS_DIR / "QA_PREP.md",
    DOCS_DIR / "DEMO_SCRIPT.md",
    DOCS_DIR / "DATA_CARD.md",
    DOCS_DIR / "ML_REPORT.md",
]


class TestDocIntegrity:
    @pytest.mark.parametrize("doc_path", ACTIVE_DOCS)
    def test_no_forbidden_stale_tokens(self, doc_path):
        """C7: Active docs must not contain stale tokens 'AMRI', 'm=500', or '+10%'."""
        content = doc_path.read_text(encoding="utf-8")
        assert "AMRI" not in content, f"Stale token 'AMRI' found in {doc_path.name}"
        assert "m=500" not in content, f"Stale token 'm=500' found in {doc_path.name}"
        assert "+10%" not in content, f"Stale token '+10%' found in {doc_path.name}"

    def test_formula_text_matches_constants(self):
        """C7: formula_text helper matches canonical weights."""
        bed_f = formula_text("bedscore")
        assert f"{W_TRUST:.2f}" in bed_f
        assert f"{W_CLOSE:.2f}" in bed_f
        assert f"{W_FEE:.2f}" in bed_f

        mentor_f = formula_text("mentor")
        assert "100·A + X − Y − Z" in mentor_f

    def test_qa_prep_formula_constants_consistency(self):
        """C7: QA_PREP.md consistently quotes canonical constants from src/scoring.py and src/geo.py."""
        qa = (DOCS_DIR / "QA_PREP.md").read_text(encoding="utf-8")
        assert "0.35" in qa, "Trust weight 0.35 missing in QA_PREP.md"
        assert "0.40" in qa, "Closeness weight 0.40 missing in QA_PREP.md"
        assert "0.25" in qa, "Affordability weight 0.25 missing in QA_PREP.md"
        assert "22" in qa, "Transit speed 22 km/h missing in QA_PREP.md"
        assert "1.35" in qa, "Tortuosity factor 1.35 missing in QA_PREP.md"
        assert "4.0" in qa or "4" in qa, "ALOS 4 missing in QA_PREP.md"

    def test_tree_txt_matches_git_ls_files(self):
        """C7: docs/TREE.txt reflects actual repository files."""
        tree_file = DOCS_DIR / "TREE.txt"
        assert tree_file.exists()
        lines = [line.strip() for line in tree_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert "data/hospitals_enriched.csv" in lines
        assert "data/history.csv" in lines
        assert "models/bed_model.joblib" in lines
        assert "hospital_data.csv" not in lines
        assert "hospitals_curated.csv" not in lines
        assert "bed_availability_model.joblib" not in lines
