from pathlib import Path

from packages.core.parsers.base import PageElement, ParseResult
from packages.core.parsers.docling_parser import DoclingParser
from packages.core.parsers.hybrid import merge_results
from packages.core.schemas.document import DocumentMeta


def _doc() -> DocumentMeta:
    return DocumentMeta(
        document_id="d1",
        filename="sample.pdf",
        domain="test",
        document_type="guidance",
    )


def _result(elements: list[PageElement], page_count: int = 2) -> ParseResult:
    return ParseResult(document=_doc(), elements=elements, page_count=page_count)


def test_hybrid_uses_docling_structure_and_baseline_table_when_richer():
    docling = _result(
        [
            PageElement(page=1, element_type="paragraph", text="Section A"),
            PageElement(
                page=1,
                element_type="paragraph",
                text="Docling preserves the correct reading order for this page.",
                section_heading="Section A",
            ),
            PageElement(page=1, element_type="table", text="A | B"),
        ],
        page_count=1,
    )
    baseline = _result(
        [
            PageElement(page=1, element_type="table", text="A | B\n1 | 2\n3 | 4"),
            PageElement(page=1, element_type="paragraph", text="Baseline duplicated body text."),
        ],
        page_count=1,
    )

    merged, errors = merge_results(docling, baseline)

    assert [el.element_type for el in merged] == ["paragraph", "paragraph", "table"]
    assert merged[-1].text == "A | B\n1 | 2\n3 | 4"
    assert merged[-1].source_parser == "baseline"
    assert merged[-1].fallback_reason == "richer baseline table"
    assert merged[1].source_parser == "docling"
    assert any("richer baseline table" in e for e in errors)


def test_hybrid_falls_back_to_baseline_for_weak_docling_page():
    docling = _result(
        [PageElement(page=2, element_type="paragraph", text="Full docling page")],
        page_count=2,
    )
    baseline = _result(
        [
            PageElement(page=1, element_type="paragraph", text="Recovered baseline-only page"),
            PageElement(page=2, element_type="paragraph", text="Baseline page two"),
        ],
        page_count=2,
    )

    merged, errors = merge_results(docling, baseline)

    assert merged[0].page == 1
    assert merged[0].text == "Recovered baseline-only page"
    assert merged[0].source_parser == "baseline"
    assert merged[0].fallback_reason == "docling output was weak/empty"
    assert any("page 1" in e and "weak/empty" in e for e in errors)


def test_hybrid_keeps_docling_table_only_page_when_table_is_richer():
    docling = _result(
        [PageElement(page=1, element_type="table", text="A | B\n1 | 2\n3 | 4")],
        page_count=1,
    )
    baseline = _result(
        [
            PageElement(page=1, element_type="table", text="A | B"),
            PageElement(page=1, element_type="paragraph", text="Short baseline text."),
        ],
        page_count=1,
    )

    merged, errors = merge_results(docling, baseline)

    assert len(merged) == 1
    assert merged[0].text == "A | B\n1 | 2\n3 | 4"
    assert merged[0].source_parser == "docling"
    assert not errors


def test_hybrid_clean_run_routes_audit_and_reports_success():
    """A hybrid run with only baseline-fallback pages must report ``success``.

    The per-page merge messages ("used baseline because ...") are an audit trail,
    not errors: they go to ``result.audit`` and must not flip parse_status.
    """
    from packages.core.parsers.hybrid import HybridParser

    parser = HybridParser()
    # Stub sub-parsers so no real PDF/docling is needed.
    parser.baseline = type(
        "StubBaseline", (),
        {"run": lambda self, p, d: ParseResult(
            document=d,
            elements=[PageElement(page=1, element_type="paragraph",
                                  text="baseline recovered the body text for this page")],
            page_count=1,
        )},
    )()
    parser.docling = type(
        "StubDocling", (),
        {"run": lambda self, p, d: ParseResult(document=d, elements=[], page_count=1)},
    )()

    result = parser.run(Path("dummy.pdf"), _doc())

    assert result.errors == []                       # no real errors
    assert any("weak/empty" in a for a in result.audit)  # merge trail in audit
    assert result.document.parse_status == "success"
    assert result.empty_pages == 0


def test_docling_conversion_failure_can_backfill_with_baseline(monkeypatch, tmp_path):
    parser = DoclingParser(backfill_with_baseline=True)
    monkeypatch.setattr(parser, "_converter_obj", lambda: type("C", (), {"convert": lambda *_: (_ for _ in ()).throw(RuntimeError("std::bad_alloc"))})())

    def fake_baseline(_pdf_path: Path, document: DocumentMeta, reason: str) -> ParseResult:
        return ParseResult(
            document=document,
            elements=[PageElement(page=1, element_type="paragraph", text="baseline recovery")],
            page_count=1,
            errors=[f"docling fallback: {reason}"],
        )

    monkeypatch.setattr(parser, "_baseline_result", fake_baseline)

    result = parser.parse(tmp_path / "sample.pdf", _doc())

    assert result.elements[0].text == "baseline recovery"
    assert "std::bad_alloc" in result.errors[0]


# --- Windowed docling conversion ---------------------------------------------------------

class _FakeItem:
    def __init__(self, label: str, page: int, text: str):
        self.label = label
        self.prov = [type("Prov", (), {"page_no": page, "page": page})()]
        self._text = text

    def export_to_markdown(self):
        return self._text


class _FakeDoc:
    def __init__(self, items):
        self._items = items

    def iterate_items(self):
        return iter(self._items)


class _FakeResult:
    def __init__(self, doc):
        self.document = doc


class _WindowFakeConverter:
    """Converts a sub-PDF path back into a doc whose pages come from `start`."""

    def convert(self, path):
        name = Path(path).name.replace(".pdf", "")  # pages_XXXX_YYYY
        _, start_s, end_s = name.split("_")
        start, end = int(start_s), int(end_s)
        n = end - start + 1
        items = [
            _FakeItem("paragraph", i + 1, f"window@{start} local-page-{i + 1}")
            for i in range(n)
        ]
        return _FakeResult(_FakeDoc(items))


def test_docling_windowed_offsets_pages_and_covers_all_windows(monkeypatch, tmp_path):
    parser = DoclingParser(window_size=2)  # 5 pages -> windows [1-2],[3-4],[5-5]
    monkeypatch.setattr(parser, "_pdf_page_count", lambda _p: 5)
    monkeypatch.setattr(parser, "_build_converter", lambda: _WindowFakeConverter())

    def fake_split(_pdf_path, start, end, tmp_dir):
        p = tmp_dir / f"pages_{start:04d}_{end:04d}.pdf"
        p.write_bytes(b"%PDF-1.4 fake")
        return p

    monkeypatch.setattr(parser, "_split_pdf_window", fake_split)

    result = parser.parse(tmp_path / "sample.pdf", _doc())

    # Each window's local pages are shifted back into document space, and the
    # odd tail window ([5-5]) emits only its single page.
    pages = sorted(el.page for el in result.elements)
    assert pages == [1, 2, 3, 4, 5]
    assert result.page_count == 5
    # Window [5-5] is offset by 4 -> local page 1 lands on document page 5.
    assert any(el.text == "window@5 local-page-1" and el.page == 5 for el in result.elements)
    assert not result.errors


def test_docling_windowed_skips_failed_window_without_losing_document(monkeypatch, tmp_path):
    """A window that throws std::bad_alloc is recorded; other windows still convert."""
    parser = DoclingParser(window_size=2)
    monkeypatch.setattr(parser, "_pdf_page_count", lambda _p: 4)

    class FlakyConverter:
        def __init__(self):
            self.calls = 0

        def convert(self, path):
            self.calls += 1
            name = Path(path).name.replace(".pdf", "")
            start = int(name.split("_")[1])
            if start == 3:  # second window dies like the prod std::bad_alloc case
                raise RuntimeError("std::bad_alloc")
            return _FakeResult(_FakeDoc([_FakeItem("paragraph", 1, f"ok@{start}")]))

    state = {"converter": FlakyConverter()}
    monkeypatch.setattr(parser, "_build_converter", lambda: state["converter"])

    def fake_split(_pdf_path, start, end, tmp_dir):
        p = tmp_dir / f"pages_{start:04d}_{end:04d}.pdf"
        p.write_bytes(b"%PDF-1.4 fake")
        return p

    monkeypatch.setattr(parser, "_split_pdf_window", fake_split)

    result = parser.parse(tmp_path / "sample.pdf", _doc())

    # Windows [1-2] and [5-...] never happen (only 4 pages -> [1-2],[3-4]);
    # window [3-4] failed, so only window [1-2] yielded elements.
    assert [el.text for el in result.elements] == ["ok@1"]
    assert any("window 3-4 failed" in e and "std::bad_alloc" in e for e in result.errors)
    assert result.page_count == 4

