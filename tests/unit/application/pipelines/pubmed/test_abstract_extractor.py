# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for AbstractExtractor."""

from __future__ import annotations

import pytest

import xml.etree.ElementTree as ET

from bioetl.application.pipelines.pubmed.extractors.abstract import AbstractExtractor


pytestmark = pytest.mark.unit


class TestExtractAbstract:
    """Tests for extract_abstract method."""

    def test_simple_abstract(self):
        """Test extracting a simple abstract."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText>This is a simple abstract text.</AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert abstract == "This is a simple abstract text."

    def test_structured_abstract(self):
        """Test extracting a structured abstract with labeled sections."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText Label="BACKGROUND">This is the background.</AbstractText>
                <AbstractText Label="METHODS">These are the methods.</AbstractText>
                <AbstractText Label="RESULTS">These are the results.</AbstractText>
                <AbstractText Label="CONCLUSION">This is the conclusion.</AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        expected = (
            "BACKGROUND: This is the background. "
            "METHODS: These are the methods. "
            "RESULTS: These are the results. "
            "CONCLUSION: This is the conclusion."
        )
        assert abstract == expected

    def test_abstract_with_inline_elements(self):
        """Test abstract with inline elements like <i>, <b>."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText>This has <i>italic</i> and <b>bold</b> text.</AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert abstract == "This has italic and bold text."

    def test_mixed_labeled_and_unlabeled(self):
        """Test abstract with both labeled and unlabeled sections."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText Label="OBJECTIVE">Main objective.</AbstractText>
                <AbstractText>Additional unlabeled text.</AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert abstract == "OBJECTIVE: Main objective. Additional unlabeled text."

    def test_empty_abstract(self):
        """Test empty Abstract element."""
        xml = """
        <Article>
            <Abstract>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert abstract is None

    def test_no_abstract_element(self):
        """Test missing Abstract element."""
        xml = "<Article></Article>"
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert abstract is None

    def test_none_article_returns_none(self):
        """Test that None article returns None."""
        abstract = AbstractExtractor.extract_abstract(None)
        assert abstract is None

    def test_abstract_with_whitespace_stripped(self):
        """Test that abstract text whitespace is stripped."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText>  Text with extra spaces.  </AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert abstract == "Text with extra spaces."

    def test_empty_abstract_text_ignored(self):
        """Test that empty AbstractText elements are ignored."""
        xml = """
        <Article>
            <Abstract>
                <AbstractText Label="METHODS"></AbstractText>
                <AbstractText>Actual content here.</AbstractText>
                <AbstractText Label="RESULTS">  </AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert abstract == "Actual content here."

    def test_abstract_nested_in_article(self):
        """Test abstract nested deeper in article structure."""
        xml = """
        <Article>
            <ArticleTitle>Test Title</ArticleTitle>
            <Abstract>
                <AbstractText>Nested abstract content.</AbstractText>
            </Abstract>
        </Article>
        """
        node = ET.fromstring(xml)
        abstract = AbstractExtractor.extract_abstract(node)
        assert abstract == "Nested abstract content."
