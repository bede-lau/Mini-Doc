"""Chunker behaviour: size, overlap, page/section preservation, no cross-doc."""
from packages.core.chunking import Chunker
from packages.core.config import Settings
from packages.core.parsers.base import PageElement, ParseResult
from packages.core.schemas.document import DocumentMeta


def _doc(doc_id="d1", parser="docling"):
    return DocumentMeta(
        document_id=doc_id, filename=f"{doc_id}.pdf", domain="finance",
        document_type="reg", parser=parser, source_url="http://e",
    )


def _result(elements, page_count, doc=None):
    return ParseResult(document=doc or _doc(), elements=elements, page_count=page_count)


def test_single_small_element_is_one_chunk():
    el = PageElement(page=1, element_type="paragraph", text="One short sentence.", section_heading="S")
    chunks = Chunker(Settings(chunk_size=700, chunk_overlap=120)).chunk(_result([el], 1))
    assert len(chunks) == 1
    assert chunks[0].section_heading == "S"
    assert chunks[0].page_start == 1 == chunks[0].page_end


def test_oversized_element_splits_with_overlap():
    text = " ".join(f"Sentence number {i} about risk controls." for i in range(60))
    el = PageElement(page=3, element_type="paragraph", text=text, section_heading="Risk")
    chunks = Chunker(Settings(chunk_size=40, chunk_overlap=12)).chunk(_result([el], 3))
    assert len(chunks) > 1
    # overlap: the first sentence of chunk[1] must appear in chunk[0]
    assert chunks[1].chunk_text.split(".")[0].strip() in chunks[0].chunk_text


def test_table_kept_whole_when_it_fits():
    el = PageElement(
        page=2, element_type="table",
        text="A | B\n1 | 2\n3 | 4", section_heading="T",
    )
    chunks = Chunker(Settings(chunk_size=700, chunk_overlap=120)).chunk(_result([el], 2))
    assert len(chunks) == 1
    assert chunks[0].chunk_type == "table"
    assert "A | B" in chunks[0].chunk_text


def test_never_combines_across_documents():
    el1 = PageElement(page=1, element_type="paragraph", text="doc one content here.", section_heading="A")
    el2 = PageElement(page=1, element_type="paragraph", text="doc two content here.", section_heading="B")
    ch = Chunker(Settings(chunk_size=700, chunk_overlap=120))
    c1 = ch.chunk(_result([el1], 1, doc=_doc("d1")))
    c2 = ch.chunk(_result([el2], 1, doc=_doc("d2")))
    assert all(c.document_id == "d1" for c in c1)
    assert all(c.document_id == "d2" for c in c2)


def test_chunk_type_and_token_count_propagate():
    el = PageElement(page=1, element_type="list", text="first item second item third item", section_heading=None)
    chunks = Chunker(Settings(chunk_size=700, chunk_overlap=120)).chunk(_result([el], 1))
    assert chunks[0].chunk_type == "list"
    assert chunks[0].token_count > 0
