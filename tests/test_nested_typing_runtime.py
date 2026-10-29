from mdutils.mdutils import MdUtils
from mdutils.tools.MDList import MDList, MDCheckbox


def test_nested_lists_render_and_mutate_document():
    items = ["one", ["nested", ["deeper"]]]
    assert MDList(items).get_md() == "- one\n    - nested\n        - deeper\n"
    assert MDCheckbox(items).get_md() == "- [ ] one\n    - [ ] nested\n        - [ ] deeper\n"
    deep = ["one", ["two", ["three", ["four"]]]]
    assert MDList(deep).get_md() == (
        "- one\n    - two\n        - three\n            - four\n"
    )
    assert MDList([[["deep"]]]).get_md() == "        - deep\n"
    document = MdUtils("example")
    assert document.new_list(items) is None
    assert "        - deeper" in document.get_md_text()
    assert document.new_checkbox_list(items, checked=True) is None
    assert "        - [x] deeper" in document.get_md_text()


def test_table_objects_alignments_and_optional_link():
    from mdutils.tools.Table import Table

    class Cell:
        def __str__(self):
            return "cell"

    table = Table().create_table(2, 1, [Cell(), 42],
                                 text_align=(a for a in ["left", "right"]))
    assert "|cell|42|" in table
    assert ":--- |" in table and "---: |" in table
    document = MdUtils("example")
    rendered = document.new_table_array([[Cell(), None], [1]], text_align=None)
    assert "|cell|None|" in rendered and "|1||" in rendered
    assert document.new_inline_link("https://example.com", text=None) == (
        "[https://example.com](https://example.com)"
    )


def test_tuple_iterator_and_path_inputs(tmp_path):
    from pathlib import Path
    from mdutils.fileutils.fileutils import MarkDownFile
    from mdutils.tools.Html import SizeBadFormat
    from mdutils.tools.Table import Table
    from mdutils.tools.TableOfContents import TableOfContents

    rendered = Table().create_table(2, 1, (1, None), iter(["left", "right"]))
    assert "|1|None|" in rendered and ":--- |" in rendered and "---: |" in rendered
    assert "|3||" in Table().create_table_array(((1, 2), (3,)))
    assert "[nested](#nested)" in TableOfContents().create_table_of_contents(
        ("root", ["nested"]), depth=2
    )
    assert MDList(iter(["root", ["nested"]])).get_md() == "- root\n    - nested\n"
    assert "123" in str(SizeBadFormat(123))
    file = MarkDownFile("example", dirname=Path(str(tmp_path)))
    assert Path(file.file_name) == tmp_path / "example.md"
    assert Path(file.file_name).is_file()


def test_explicit_none_options_for_helpers():
    from mdutils.tools.Header import AtxHeaderLevel, Header, HeaderStyle
    from mdutils.tools.Html import Html
    from mdutils.tools.Image import Image
    from mdutils.tools.Link import Inline, Reference

    assert str(Header(1, "Title", HeaderStyle.ATX, header_id=None)) == "\n# Title\n"
    assert Header.atx(AtxHeaderLevel.TITLE, "Title", header_id=None) == "\n# Title\n"
    assert Header.header_anchor("Title", link=None) == "[Title](#title)"
    assert Html.paragraph("text", align=None) == "<p>\n    text\n</p>"
    assert Html.image("p", size=None, align=None) == '<img src="p" />'
    assert Image.new_inline_image("alt", "p", tooltip=None) == "![alt](p)"
    assert Image(Reference()).new_reference_image(
        "alt", "p", reference_tag=None, tooltip=None
    ) == "![alt]"
    assert Inline.new_link("url", text=None, tooltip=None) == "<url>"
    assert Reference().new_link("url", "text", reference_tag=None, tooltip=None) == "[text]"
