from __future__ import annotations

import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PhaseZeroScaffoldTests(unittest.TestCase):
    def test_required_tooling_files_exist(self) -> None:
        for relative_path in ("pyproject.toml", "Makefile", ".gitignore", ".env.example"):
            self.assertTrue((PROJECT_ROOT / relative_path).is_file(), relative_path)

    def test_development_workflow_documents_all_check_command(self) -> None:
        text = (PROJECT_ROOT / "docs" / "development.md").read_text(encoding="utf-8")

        self.assertIn("make check", text)

    def test_all_required_adrs_exist(self) -> None:
        adr_directory = PROJECT_ROOT / "docs" / "adr"
        expected = {
            "0001-service-boundaries.md",
            "0002-kafka-workflow.md",
            "0003-postgresql-system-of-record.md",
            "0004-milvus-rag.md",
            "0005-model-provider-strategy.md",
        }

        self.assertTrue(expected.issubset({path.name for path in adr_directory.iterdir()}))

    def test_environment_template_has_no_populated_provider_secrets(self) -> None:
        text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertNotIn("OPENAI_API_KEY=sk-", text)
        self.assertNotIn("GOOGLE_API_KEY=AIza", text)
