"""Docling adapter compatibility helpers."""

from enum import Enum

from packages.core.parsers.docling_parser import _label_value, _page_count, _unwrap_item


class FakeLabel(Enum):
    SECTION_HEADER = "section_header"


class FakeItem:
    label = FakeLabel.SECTION_HEADER


def test_docling_iterate_items_tuple_shape_is_unwrapped():
    item = FakeItem()

    assert _unwrap_item((item, 1)) is item
    assert _label_value(item) == "section_header"


def test_docling_page_count_accepts_callable_num_pages():
    class FakeDoc:
        def num_pages(self):
            return 38

    assert _page_count(FakeDoc(), {1, 2}) == 38

