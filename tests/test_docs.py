"""Tests to ensure documentation is strictly synchronized with code and free of stale tokens."""
import re
from pathlib import Path
import pytest
from src.scoring import formula_text, W_TRUST, W_CLOSE, W_FEE, DIST_SCALE_KM, ALOS_DAYS
from src.config import ROAD_FACTOR, CITY_SPEED_KMPH, A_WEIGHT

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
ACTIVE_DOCS = [
    DOCS_DIR / "QA_PREP.md",
    DOCS_DIR / "DEMO_SCRIPT.md",
    DOCS_DIR / "DATA_CARD.md",
    DOCS_DIR / "ML_REPORT.md",
]


FORBIDDEN_TOKENS = [
    "hospital_data.csv",
    "verified hospital registries",
    "only confirmed official domains",
    "Verified directory",
    "domain verified manually",
    "AMRI",
    "+10%",
    "m=500",
    "never flip",
]


class TestDocIntegrity:
    @pytest.mark.parametrize("doc_path", ACTIVE_DOCS)
    def test_no_forbidden_stale_tokens(self, doc_path):
        """D6: Active docs must not contain stale or ungrounded forbidden tokens."""
        content = doc_path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            assert token not in content, f"Forbidden token '{token}' found in {doc_path.name}"

    def test_demo_script_toggle_matches_config(self):
        """D6: Toggle label in DEMO_SCRIPT matches SCHEME_TOGGLE_LABEL from src/config.py."""
        from src.config import SCHEME_TOGGLE_LABEL
        demo_text = (DOCS_DIR / "DEMO_SCRIPT.md").read_text(encoding="utf-8")
        assert SCHEME_TOGGLE_LABEL in demo_text, f"Label '{SCHEME_TOGGLE_LABEL}' not found in DEMO_SCRIPT.md"

    def test_formula_text_matches_constants(self):
        """C7: formula_text helper matches canonical weights."""
        bed_f = formula_text("formula2")
        assert f"{W_TRUST:.2f}" in bed_f
        assert f"{W_CLOSE:.2f}" in bed_f
        assert f"{W_FEE:.2f}" in bed_f

        f1_f = formula_text("formula1")
        assert f"{int(A_WEIGHT)}·A + X/1000 − 100·Y − Z/10" in f1_f

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

    def test_no_version_strings_in_doc_titles(self):
        """G5: Doc titles must not contain version strings like v2.3 or v2.4."""
        doc_files = [
            Path(__file__).resolve().parent.parent / "README.md",
            DOCS_DIR / "DEMO_SCRIPT.md",
            DOCS_DIR / "QA_PREP.md",
            DOCS_DIR / "DATA_CARD.md",
            DOCS_DIR / "BLOCKED.md",
            DOCS_DIR / "ML_REPORT.md",
            DOCS_DIR / "VERIFICATION.md",
        ]
        for doc in doc_files:
            if doc.exists():
                first_lines = doc.read_text(encoding="utf-8").splitlines()[:5]
                for line in first_lines:
                    if line.startswith("#"):
                        assert not re.search(r"v2\.\d", line), f"Version string found in title of {doc.name}: '{line}'"

    def test_doc_numbers_match_numbers_json(self):
        """G5: Numbers in README / DEMO_SCRIPT / QA_PREP / DATA_CARD / BLOCKED must match docs/numbers.json."""
        import json
        numbers_path = DOCS_DIR / "numbers.json"
        assert numbers_path.exists(), "docs/numbers.json does not exist"
        data = json.loads(numbers_path.read_text(encoding="utf-8"))

        m_f1_str = f"{data['macro_f1_model']:.4f}"
        b_f1_str = f"{data['macro_f1_baseline']:.4f}"
        tot_hosp = str(data["total_hospitals"])
        mentor_hosp = str(data["mentor_hospitals"])
        added_hosp = str(data["added_hospitals"])
        tot_pairs = str(data["total_pairs"])
        flippable = str(data["flippable_pairs"])

        stale_numbers = ["0.7710", "0.7626"]

        readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
        assert m_f1_str in readme
        assert b_f1_str in readme
        assert tot_hosp in readme
        for sn in stale_numbers:
            assert sn not in readme

        demo = (DOCS_DIR / "DEMO_SCRIPT.md").read_text(encoding="utf-8")
        assert m_f1_str in demo
        assert b_f1_str in demo
        assert tot_hosp in demo
        for sn in stale_numbers:
            assert sn not in demo

        qa = (DOCS_DIR / "QA_PREP.md").read_text(encoding="utf-8")
        assert m_f1_str in qa
        assert b_f1_str in qa
        assert tot_pairs in qa
        assert flippable in qa
        for sn in stale_numbers:
            assert sn not in qa

        datacard = (DOCS_DIR / "DATA_CARD.md").read_text(encoding="utf-8")
        assert tot_hosp in datacard
        assert mentor_hosp in datacard
        assert added_hosp in datacard
        for sn in stale_numbers:
            assert sn not in datacard

        blocked = (DOCS_DIR / "BLOCKED.md").read_text(encoding="utf-8")
        assert mentor_hosp in blocked
        assert added_hosp in blocked
        for sn in stale_numbers:
            assert sn not in blocked

    def test_verification_md_passed_count_equals_pytest_output(self):
        """G6: Passed count in VERIFICATION.md equals the count in docs/evidence/pytest_output.txt."""
        pytest_out = DOCS_DIR / "evidence" / "pytest_output.txt"
        assert pytest_out.exists(), "docs/evidence/pytest_output.txt missing"
        pytest_text = pytest_out.read_text(encoding="utf-8")
        m_pytest = re.search(r"(\d+)\s+passed", pytest_text)
        assert m_pytest, "Could not find passed count in pytest_output.txt"
        pytest_count = int(m_pytest.group(1))

        verif_file = DOCS_DIR / "VERIFICATION.md"
        assert verif_file.exists(), "docs/VERIFICATION.md missing"
        verif_text = verif_file.read_text(encoding="utf-8")
        m_verif = re.search(r"(\d+)\s+passed", verif_text)
        assert m_verif, "Could not find passed count in VERIFICATION.md"
        verif_count = int(m_verif.group(1))

        assert verif_count == pytest_count, f"VERIFICATION.md count ({verif_count}) != pytest_output.txt count ({pytest_count})"

    def test_ml_accuracy_numbers_match_numbers_json(self):
        """V4: audit_ml.py writes ML numbers to numbers.json, and on-screen accuracy expander reflects it."""
        import json
        from streamlit.testing.v1 import AppTest
        numbers_path = DOCS_DIR / "numbers.json"
        data = json.loads(numbers_path.read_text(encoding="utf-8"))
        at = AppTest.from_file("app.py", default_timeout=30).run()
        assert not at.exception
        # Check rendered markdown in app for macro F1 and Brier
        found_f1 = False
        m_f1_str = f"{data['macro_f1_model']:.4f}"
        b_f1_str = f"{data['macro_f1_baseline']:.4f}"
        brier_str = f"{data['brier_model']:.4f}"
        for md in at.markdown:
            val = str(md.value)
            if m_f1_str in val and b_f1_str in val and brier_str in val:
                found_f1 = True
                break
        assert found_f1, f"ML metrics ({m_f1_str}, {b_f1_str}, {brier_str}) not found in rendered app markdown"

