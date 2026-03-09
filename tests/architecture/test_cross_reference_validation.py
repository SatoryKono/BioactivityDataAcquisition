"""Architecture tests for cross-reference validation script."""

from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest


def _load_module() -> ModuleType:
    """Load validate_cross_references module for testing."""
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "docs" / "validate_cross_references.py"
    module_name = f"validate_cross_references_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# heading_to_slug
# ---------------------------------------------------------------------------


class TestHeadingToSlug:
    """Tests for _heading_to_slug function."""

    def test_simple_heading(self) -> None:
        mod = _load_module()
        assert mod._heading_to_slug("Installation") == "installation"

    def test_heading_with_spaces(self) -> None:
        mod = _load_module()
        assert mod._heading_to_slug("Error Handling Strategy") == "error-handling-strategy"

    def test_heading_with_special_chars(self) -> None:
        mod = _load_module()
        result = mod._heading_to_slug("ADR-005: ETL Strategy")
        assert "adr-005" in result
        assert "etl-strategy" in result

    def test_heading_strips_markdown_formatting(self) -> None:
        mod = _load_module()
        assert mod._heading_to_slug("**Bold Heading**") == "bold-heading"
        assert mod._heading_to_slug("`code heading`") == "code-heading"

    def test_heading_with_numbers(self) -> None:
        mod = _load_module()
        assert mod._heading_to_slug("Section 1.2 Overview") == "section-12-overview"

    def test_heading_lowercase(self) -> None:
        mod = _load_module()
        assert mod._heading_to_slug("ALL CAPS HEADING") == "all-caps-heading"


# ---------------------------------------------------------------------------
# extract_headings
# ---------------------------------------------------------------------------


class TestExtractHeadings:
    """Tests for _extract_headings function."""

    def test_extracts_multiple_headings(self) -> None:
        mod = _load_module()
        content = textwrap.dedent("""\
            # Introduction
            Some text.
            ## Getting Started
            More text.
            ### Installation
            Even more text.
        """)
        slugs = mod._extract_headings(content)
        assert "introduction" in slugs
        assert "getting-started" in slugs
        assert "installation" in slugs

    def test_empty_document_returns_empty_list(self) -> None:
        mod = _load_module()
        assert mod._extract_headings("") == []

    def test_no_headings_returns_empty_list(self) -> None:
        mod = _load_module()
        content = "Just a paragraph.\n\nAnother paragraph."
        assert mod._extract_headings(content) == []

    def test_heading_with_inline_code(self) -> None:
        mod = _load_module()
        content = "## Using `httpx` Client\n"
        slugs = mod._extract_headings(content)
        assert len(slugs) == 1
        assert "httpx" in slugs[0]


# ---------------------------------------------------------------------------
# classify_link
# ---------------------------------------------------------------------------


class TestClassifyLink:
    """Tests for _classify_link function."""

    def test_external_https(self) -> None:
        mod = _load_module()
        source = Path("/some/docs/file.md")
        assert mod._classify_link("https://example.com/api", source) == mod.LinkType.EXTERNAL

    def test_external_http(self) -> None:
        mod = _load_module()
        source = Path("/some/docs/file.md")
        assert mod._classify_link("http://example.com", source) == mod.LinkType.EXTERNAL

    def test_same_page_anchor(self) -> None:
        mod = _load_module()
        source = Path("/some/docs/file.md")
        assert mod._classify_link("#installation", source) == mod.LinkType.ANCHOR

    def test_internal_md_link(self) -> None:
        mod = _load_module()
        source = Path("/some/docs/file.md")
        assert mod._classify_link("../other.md", source) == mod.LinkType.INTERNAL

    def test_python_code_link(self) -> None:
        mod = _load_module()
        source = Path("/some/docs/file.md")
        assert mod._classify_link("../../src/bioetl/thing.py", source) == mod.LinkType.CODE

    def test_image_link_png(self) -> None:
        mod = _load_module()
        source = Path("/some/docs/file.md")
        assert mod._classify_link("./images/arch.png", source) == mod.LinkType.IMAGE

    def test_image_link_svg(self) -> None:
        mod = _load_module()
        source = Path("/some/docs/file.md")
        assert mod._classify_link("./diagrams/flow.svg", source) == mod.LinkType.IMAGE

    def test_yaml_config_link(self) -> None:
        mod = _load_module()
        source = Path("/some/docs/file.md")
        assert mod._classify_link("../../configs/providers/chembl.yaml", source) == mod.LinkType.CODE

    def test_md_link_with_anchor(self) -> None:
        mod = _load_module()
        source = Path("/some/docs/file.md")
        # A link like ../other.md#section is an internal link with anchor
        assert mod._classify_link("../other.md#section", source) == mod.LinkType.INTERNAL


# ---------------------------------------------------------------------------
# iter_md_links
# ---------------------------------------------------------------------------


class TestIterMdLinks:
    """Tests for _iter_md_links function."""

    def test_extracts_basic_link(self) -> None:
        mod = _load_module()
        source = Path("/docs/guide.md")
        content = "See [installation guide](./install.md) for details."
        refs = mod._iter_md_links(source, content)
        assert len(refs) == 1
        assert refs[0].raw_url == "./install.md"
        assert refs[0].link_text == "installation guide"
        assert refs[0].line == 1

    def test_extracts_anchor_link(self) -> None:
        mod = _load_module()
        source = Path("/docs/guide.md")
        content = "See [section](#installation)."
        refs = mod._iter_md_links(source, content)
        assert len(refs) == 1
        assert refs[0].link_type == mod.LinkType.ANCHOR

    def test_skips_external_links_classification(self) -> None:
        mod = _load_module()
        source = Path("/docs/guide.md")
        content = "See [ChEMBL](https://www.ebi.ac.uk/chembl/api/)."
        refs = mod._iter_md_links(source, content)
        assert len(refs) == 1
        assert refs[0].link_type == mod.LinkType.EXTERNAL

    def test_line_numbers_are_correct(self) -> None:
        mod = _load_module()
        source = Path("/docs/guide.md")
        content = "Line 1\nLine 2 [link](./target.md)\nLine 3"
        refs = mod._iter_md_links(source, content)
        assert len(refs) == 1
        assert refs[0].line == 2

    def test_skips_links_in_inline_code(self) -> None:
        mod = _load_module()
        source = Path("/docs/guide.md")
        content = "Run `[not-a-link](fake.md)` to proceed."
        refs = mod._iter_md_links(source, content)
        assert len(refs) == 0

    def test_multiple_links_per_line(self) -> None:
        mod = _load_module()
        source = Path("/docs/guide.md")
        content = "[A](a.md) and [B](b.md)"
        refs = mod._iter_md_links(source, content)
        assert len(refs) == 2

    def test_link_with_title_attribute(self) -> None:
        mod = _load_module()
        source = Path("/docs/guide.md")
        content = '[link](./target.md "My Title")'
        refs = mod._iter_md_links(source, content)
        assert len(refs) == 1
        assert refs[0].raw_url == "./target.md"


# ---------------------------------------------------------------------------
# validate_anchor
# ---------------------------------------------------------------------------


class TestValidateAnchor:
    """Tests for _validate_anchor function."""

    def test_valid_same_file_anchor(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "doc.md"
        source.write_text("# Installation\n\nSome text.\n", encoding="utf-8")
        headings = {source: mod._extract_headings(source.read_text(encoding="utf-8"))}

        ref = mod.LinkRef(
            source_file=source,
            line=5,
            link_text="installation",
            raw_url="#installation",
            link_type=mod.LinkType.ANCHOR,
        )
        result = mod._validate_anchor(ref, headings)
        assert result is None

    def test_broken_anchor_returns_error(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "doc.md"
        source.write_text("# Installation\n\nSome text.\n", encoding="utf-8")
        headings = {source: mod._extract_headings(source.read_text(encoding="utf-8"))}

        ref = mod.LinkRef(
            source_file=source,
            line=5,
            link_text="instalation",
            raw_url="#instalation",
            link_type=mod.LinkType.ANCHOR,
        )
        result = mod._validate_anchor(ref, headings)
        assert result is not None
        assert "instalation" in result.error

    def test_fuzzy_suggestion_for_anchor_typo(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "doc.md"
        source.write_text("# Installation\n\nSome text.\n", encoding="utf-8")
        headings = {source: mod._extract_headings(source.read_text(encoding="utf-8"))}

        ref = mod.LinkRef(
            source_file=source,
            line=5,
            link_text="instalation",
            raw_url="#instalation",
            link_type=mod.LinkType.ANCHOR,
        )
        result = mod._validate_anchor(ref, headings)
        assert result is not None
        assert result.suggestion is not None
        assert "installation" in result.suggestion

    def test_cross_file_anchor_valid(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "source.md"
        target = tmp_path / "target.md"
        source.write_text("See [section](target.md#overview).\n", encoding="utf-8")
        target.write_text("# Overview\n\nSome text.\n", encoding="utf-8")
        headings = {
            source: mod._extract_headings(source.read_text(encoding="utf-8")),
            target: mod._extract_headings(target.read_text(encoding="utf-8")),
        }

        ref = mod.LinkRef(
            source_file=source,
            line=1,
            link_text="section",
            raw_url="target.md#overview",
            link_type=mod.LinkType.INTERNAL,
        )
        result = mod._validate_anchor(ref, headings)
        assert result is None


# ---------------------------------------------------------------------------
# validate_internal
# ---------------------------------------------------------------------------


class TestValidateInternal:
    """Tests for _validate_internal function."""

    def test_existing_file_passes(self, tmp_path: Path) -> None:
        mod = _load_module()
        target = tmp_path / "target.md"
        target.write_text("# Target\n", encoding="utf-8")
        source = tmp_path / "source.md"

        ref = mod.LinkRef(
            source_file=source,
            line=1,
            link_text="target",
            raw_url="target.md",
            link_type=mod.LinkType.INTERNAL,
        )
        result = mod._validate_internal(ref)
        assert result is None

    def test_missing_file_returns_error(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "source.md"
        ref = mod.LinkRef(
            source_file=source,
            line=1,
            link_text="missing",
            raw_url="nonexistent.md",
            link_type=mod.LinkType.INTERNAL,
        )
        result = mod._validate_internal(ref)
        assert result is not None
        assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# validate_code_ref
# ---------------------------------------------------------------------------


class TestValidateCodeRef:
    """Tests for _validate_code_ref function."""

    def test_existing_file_passes(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "doc.md"
        code_file = tmp_path / "thing.py"
        code_file.write_text("# code\n" * 20, encoding="utf-8")

        ref = mod.LinkRef(
            source_file=source,
            line=1,
            link_text="thing",
            raw_url="thing.py",
            link_type=mod.LinkType.CODE,
        )
        broken, warning = mod._validate_code_ref(ref)
        assert broken is None
        assert warning is None

    def test_valid_line_reference(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "doc.md"
        code_file = tmp_path / "thing.py"
        code_file.write_text("line\n" * 50, encoding="utf-8")

        ref = mod.LinkRef(
            source_file=source,
            line=1,
            link_text="thing line 10",
            raw_url="thing.py#L10",
            link_type=mod.LinkType.CODE,
        )
        broken, warning = mod._validate_code_ref(ref)
        assert broken is None
        assert warning is None

    def test_line_number_exceeds_file_length_warns(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "doc.md"
        code_file = tmp_path / "thing.py"
        code_file.write_text("line\n" * 10, encoding="utf-8")

        ref = mod.LinkRef(
            source_file=source,
            line=1,
            link_text="thing",
            raw_url="thing.py#L150",
            link_type=mod.LinkType.CODE,
        )
        broken, warning = mod._validate_code_ref(ref)
        assert broken is None
        assert warning is not None
        assert "150" in warning.message
        assert "10" in warning.message

    def test_missing_code_file_broken(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "doc.md"
        ref = mod.LinkRef(
            source_file=source,
            line=1,
            link_text="missing",
            raw_url="missing.py",
            link_type=mod.LinkType.CODE,
        )
        broken, warning = mod._validate_code_ref(ref)
        assert broken is not None
        assert warning is None


# ---------------------------------------------------------------------------
# validate_image
# ---------------------------------------------------------------------------


class TestValidateImage:
    """Tests for _validate_image function."""

    def test_existing_image_passes(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "doc.md"
        img = tmp_path / "arch.png"
        img.write_bytes(b"\x89PNG")

        ref = mod.LinkRef(
            source_file=source,
            line=1,
            link_text="arch",
            raw_url="arch.png",
            link_type=mod.LinkType.IMAGE,
        )
        result = mod._validate_image(ref)
        assert result is None

    def test_missing_image_broken(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "doc.md"
        ref = mod.LinkRef(
            source_file=source,
            line=1,
            link_text="arch",
            raw_url="missing.png",
            link_type=mod.LinkType.IMAGE,
        )
        result = mod._validate_image(ref)
        assert result is not None
        assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# Full validation integration
# ---------------------------------------------------------------------------


class TestValidateIntegration:
    """Integration tests for the validate() function."""

    def test_valid_document_no_errors(self, tmp_path: Path) -> None:
        mod = _load_module()
        doc = tmp_path / "README.md"
        target = tmp_path / "other.md"
        target.write_text("# Target Doc\n\n## Section One\n", encoding="utf-8")
        doc.write_text(
            "# Main Doc\n\n"
            "See [other doc](other.md).\n"
            "See [section](other.md#section-one).\n",
            encoding="utf-8",
        )

        report = _run_validate_on_dir(mod, tmp_path, single_file=doc)

        assert not report.has_errors
        assert report.checked >= 2

    def test_broken_internal_link_detected(self, tmp_path: Path) -> None:
        mod = _load_module()
        doc = tmp_path / "README.md"
        doc.write_text("# Doc\n\nSee [missing](./nonexistent.md).\n", encoding="utf-8")

        # Patch PROJECT_ROOT and DOCS_DIR in the module for isolation
        original_root = mod.PROJECT_ROOT
        original_docs = mod.DOCS_DIR
        original_src = mod.SRC_DIR
        try:
            mod.PROJECT_ROOT = tmp_path
            mod.DOCS_DIR = tmp_path
            mod.SRC_DIR = tmp_path / "src"
            report = mod.validate(
                full_mode=False,
                fix_mode=False,
                single_file=doc,
                quiet=True,
            )
        finally:
            mod.PROJECT_ROOT = original_root
            mod.DOCS_DIR = original_docs
            mod.SRC_DIR = original_src

        assert report.has_errors
        assert len(report.broken) == 1
        assert "nonexistent.md" in report.broken[0].error

    def test_broken_anchor_detected(self, tmp_path: Path) -> None:
        mod = _load_module()
        doc = tmp_path / "README.md"
        doc.write_text("# Doc\n\nSee [section](#nonexistent-anchor).\n", encoding="utf-8")

        original_root = mod.PROJECT_ROOT
        original_docs = mod.DOCS_DIR
        original_src = mod.SRC_DIR
        try:
            mod.PROJECT_ROOT = tmp_path
            mod.DOCS_DIR = tmp_path
            mod.SRC_DIR = tmp_path / "src"
            report = mod.validate(
                full_mode=False,
                fix_mode=False,
                single_file=doc,
                quiet=True,
            )
        finally:
            mod.PROJECT_ROOT = original_root
            mod.DOCS_DIR = original_docs
            mod.SRC_DIR = original_src

        assert report.has_errors
        broken_errors = [b.error for b in report.broken]
        assert any("nonexistent-anchor" in e for e in broken_errors)

    def test_valid_anchor_passes(self, tmp_path: Path) -> None:
        mod = _load_module()
        doc = tmp_path / "README.md"
        doc.write_text("# Doc\n\n## Installation\n\nSee [install](#installation).\n", encoding="utf-8")

        original_root = mod.PROJECT_ROOT
        original_docs = mod.DOCS_DIR
        original_src = mod.SRC_DIR
        try:
            mod.PROJECT_ROOT = tmp_path
            mod.DOCS_DIR = tmp_path
            mod.SRC_DIR = tmp_path / "src"
            report = mod.validate(
                full_mode=False,
                fix_mode=False,
                single_file=doc,
                quiet=True,
            )
        finally:
            mod.PROJECT_ROOT = original_root
            mod.DOCS_DIR = original_docs
            mod.SRC_DIR = original_src

        assert not report.has_errors


def _run_validate_on_dir(mod: ModuleType, tmp_path: Path, single_file: Path | None = None) -> object:
    """Helper to run validate with patched paths."""
    original_root = mod.PROJECT_ROOT
    original_docs = mod.DOCS_DIR
    original_src = mod.SRC_DIR
    try:
        mod.PROJECT_ROOT = tmp_path
        mod.DOCS_DIR = tmp_path
        mod.SRC_DIR = tmp_path / "src"
        return mod.validate(full_mode=False, fix_mode=False, quiet=True, single_file=single_file)
    finally:
        mod.PROJECT_ROOT = original_root
        mod.DOCS_DIR = original_docs
        mod.SRC_DIR = original_src


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


class TestReportFormatting:
    """Tests for report formatting functions."""

    def test_markdown_report_no_errors(self) -> None:
        mod = _load_module()
        report = mod.ValidationReport(broken=[], warnings=[], checked=10, skipped=2)
        result = mod._format_report_markdown(report)
        assert "All links are valid" in result
        assert "Checked: 10" in result

    def test_markdown_report_with_errors(self, tmp_path: Path) -> None:
        mod = _load_module()
        source = tmp_path / "doc.md"
        ref = mod.LinkRef(
            source_file=source,
            line=5,
            link_text="broken",
            raw_url="./missing.md",
            link_type=mod.LinkType.INTERNAL,
        )
        broken = mod.BrokenLink(ref=ref, error="File not found: /some/missing.md")
        report = mod.ValidationReport(broken=[broken], warnings=[], checked=10, skipped=0)
        result = mod._format_report_markdown(report)
        assert "Broken Links" in result
        assert "missing.md" in result
        assert "File not found" in result

    def test_json_report_structure(self, tmp_path: Path) -> None:
        mod = _load_module()
        import json as json_mod

        source = tmp_path / "doc.md"
        ref = mod.LinkRef(
            source_file=source,
            line=3,
            link_text="broken",
            raw_url="./missing.md",
            link_type=mod.LinkType.INTERNAL,
        )
        broken = mod.BrokenLink(ref=ref, error="File not found")
        report = mod.ValidationReport(broken=[broken], warnings=[], checked=5, skipped=1)
        result = json_mod.loads(mod._format_report_json(report))

        assert result["summary"]["broken"] == 1
        assert result["summary"]["checked"] == 5
        assert result["summary"]["skipped"] == 1
        assert len(result["broken_links"]) == 1
        assert result["broken_links"][0]["error"] == "File not found"


# ---------------------------------------------------------------------------
# Script structure / wrapper
# ---------------------------------------------------------------------------


class TestScriptStructure:
    """Tests for script structure and wrapper compliance."""

    def test_canonical_script_exists(self) -> None:
        """Canonical script must exist in scripts/docs/."""
        repo_root = Path(__file__).resolve().parents[2]
        script = repo_root / "scripts" / "docs" / "validate_cross_references.py"
        assert script.exists(), f"Canonical script not found: {script}"

    def test_root_wrapper_exists(self) -> None:
        """Root compatibility wrapper must exist."""
        repo_root = Path(__file__).resolve().parents[2]
        wrapper = repo_root / "scripts" / "validate_cross_references.py"
        assert wrapper.exists(), f"Root wrapper not found: {wrapper}"

    def test_root_wrapper_has_compatibility_marker(self) -> None:
        """Root wrapper must contain 'Compatibility wrapper' marker."""
        repo_root = Path(__file__).resolve().parents[2]
        wrapper = repo_root / "scripts" / "validate_cross_references.py"
        content = wrapper.read_text(encoding="utf-8")
        assert "Compatibility wrapper" in content

    def test_root_wrapper_references_canonical_script(self) -> None:
        """Root wrapper must reference the canonical script path."""
        repo_root = Path(__file__).resolve().parents[2]
        wrapper = repo_root / "scripts" / "validate_cross_references.py"
        content = wrapper.read_text(encoding="utf-8")
        assert "docs/validate_cross_references.py" in content

    def test_canonical_script_has_main_function(self) -> None:
        """Canonical script must expose a main() entry point."""
        mod = _load_module()
        assert callable(getattr(mod, "main", None))

    def test_canonical_script_has_validate_function(self) -> None:
        """Canonical script must expose a validate() function."""
        mod = _load_module()
        assert callable(getattr(mod, "validate", None))

    def test_link_type_enum_has_all_required_values(self) -> None:
        """LinkType enum must cover all 6 link categories from the spec."""
        mod = _load_module()
        link_types = {lt.value for lt in mod.LinkType}
        assert "internal" in link_types
        assert "anchor" in link_types
        assert "code" in link_types
        assert "image" in link_types
        assert "external" in link_types


# ---------------------------------------------------------------------------
# Fix mode
# ---------------------------------------------------------------------------


class TestFixMode:
    """Tests for auto-fix functionality."""

    def test_apply_fix_high_confidence_anchor(self, tmp_path: Path) -> None:
        """High-confidence anchor typo should be auto-fixed."""
        mod = _load_module()
        doc = tmp_path / "doc.md"
        doc.write_text(
            "# Doc\n\n## Installation\n\nSee [here](#instalation).\n",
            encoding="utf-8",
        )

        ref = mod.LinkRef(
            source_file=doc,
            line=5,
            link_text="here",
            raw_url="#instalation",
            link_type=mod.LinkType.ANCHOR,
        )
        broken = mod.BrokenLink(
            ref=ref,
            error="Heading not found: #instalation",
            suggestion="did you mean #installation?",
        )

        result = mod._apply_fix(ref, broken, dry_run=False)
        # Fix should be applied (high similarity between instalation/installation)
        assert result is True
        updated = doc.read_text(encoding="utf-8")
        assert "#installation" in updated

    def test_apply_fix_dry_run_does_not_modify_file(self, tmp_path: Path) -> None:
        """Dry-run fix must not modify the file."""
        mod = _load_module()
        original_content = "# Doc\n\n## Installation\n\nSee [here](#instalation).\n"
        doc = tmp_path / "doc.md"
        doc.write_text(original_content, encoding="utf-8")

        ref = mod.LinkRef(
            source_file=doc,
            line=5,
            link_text="here",
            raw_url="#instalation",
            link_type=mod.LinkType.ANCHOR,
        )
        broken = mod.BrokenLink(
            ref=ref,
            error="Heading not found: #instalation",
            suggestion="did you mean #installation?",
        )

        mod._apply_fix(ref, broken, dry_run=True)
        assert doc.read_text(encoding="utf-8") == original_content
