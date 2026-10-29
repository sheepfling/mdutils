"""Verify typing against a wheel installed outside the source tree."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import zipfile

import pytest


ROOT = Path(__file__).resolve().parent.parent


def run(*args, **kwargs):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True, **kwargs)


def test_installed_distribution_typing(tmp_path):
    pytest.importorskip("build")
    pytest.importorskip("mypy")
    source = tmp_path / "source"
    shutil.copytree(str(ROOT), str(source), ignore=shutil.ignore_patterns(
        ".git", "__pycache__", "*.egg-info", ".pytest_cache", "build", "dist"))
    dist = tmp_path / "dist"
    run(sys.executable, "-m", "build", "--no-isolation", "--outdir", str(dist),
        cwd=str(source))
    wheel = next(dist.glob("*.whl"))
    sdist = next(dist.glob("*.tar.gz"))
    with zipfile.ZipFile(str(wheel)) as archive:
        assert "mdutils/py.typed" in archive.namelist()
    with tarfile.open(str(sdist)) as archive:
        assert any(name.endswith("/mdutils/py.typed") for name in archive.getnames())

    venv = tmp_path / "venv"
    run(sys.executable, "-m", "venv", str(venv))
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run(str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel), cwd=str(tmp_path))
    # The clean venv contains only the distribution under test, not mdutils-stubs.
    run(str(python), "-c", "import pathlib, sysconfig; "
        "site = pathlib.Path(sysconfig.get_paths()['purelib']); "
        "assert not list(site.glob('mdutils-stubs*')); "
        "import mdutils; assert site in pathlib.Path(mdutils.__file__).parents", cwd=str(tmp_path))
    consumer = tmp_path / "consumer.py"
    consumer.write_text(
        "from typing import List\n"
        "from pathlib import Path\n"
        "from mdutils.mdutils import MdUtils\n"
        "from mdutils.tools.MDList import MDList\n"
        "from mdutils.tools.Table import Table\n"
        "from mdutils.tools.TableOfContents import TableOfContents\n"
        "from mdutils.tools.Html import Html, SizeBadFormat\n"
        "from mdutils.tools.Header import Header, HeaderStyle, AtxHeaderLevel\n"
        "from mdutils.tools.Image import Image\n"
        "from mdutils.tools.Link import Inline, Reference\n"
        "from mdutils.fileutils.fileutils import MarkDownFile\n"
        "doc = MdUtils('example')\n"
        "flat: List[str] = ['one', 'two']\n"
        "nested: List[List[str]] = [['nested']]\n"
        "deep: List[List[List[str]]] = [[['deep']]]\n"
        "doc.new_list(flat)\n"
        "doc.new_list(nested)\n"
        "doc.new_list(deep)\n"
        "doc.new_list(item for item in flat)\n"
        "doc.new_checkbox_list(nested)\n"
        "doc.new_checkbox_list(deep)\n"
        "doc.new_checkbox_list(item for item in flat)\n"
        "doc.new_list(['one', ['nested', ['deeper']]])\n"
        "doc.new_list(['one', ['two', ['three', ['four']]]])\n"
        "doc.new_checkbox_list(['one', ['two', ['three', ['four']]]])\n"
        "MDList(['one', ['two', ['three', ['four']]]])\n"
        "Table().create_table(2, 1, (1, None), iter(['left', 'right']))\n"
        "Table().create_table_array(((1, 2), (3,)))\n"
        "TableOfContents().create_table_of_contents(('root', ['nested']), depth=2)\n"
        "MDList(iter(['root', ['nested']]))\n"
        "SizeBadFormat(123)\n"
        "Header(1, 'Title', HeaderStyle.ATX, header_id=None)\n"
        "Header.atx(AtxHeaderLevel.TITLE, 'Title', header_id=None)\n"
        "Header.header_anchor('Title', link=None)\n"
        "Html.paragraph('text', align=None)\n"
        "Html.image('p', size=None, align=None)\n"
        "Image.new_inline_image('alt', 'p', tooltip=None)\n"
        "Image(Reference()).new_reference_image('alt', 'p', reference_tag=None, tooltip=None)\n"
        "Inline.new_link('url', text=None, tooltip=None)\n"
        "Reference().new_link('url', 'text', reference_tag=None, tooltip=None)\n"
        "MarkDownFile('example', dirname=Path('directory'))\n"
        "doc.new_table(2, 1, ['header', 42], text_align=['left', None])\n"
        "doc.new_table_array([['header', object()], [1, None]], text_align=None)\n"
        "Table().create_table(2, 1, ['header', object()], text_align=(a for a in ['left', 'right']))\n"
        "reveal_type(doc.new_inline_link('https://example.com', text=None))\n"
        "reveal_type(doc.new_table_array([[object()]], text_align=None))\n"
        "reveal_type(doc.new_header(1, 'Title'))\n"
        "reveal_type(doc.new_list(flat))\n"
        "reveal_type(MDList(nested).get_md())\n"
    )
    env = os.environ.copy()
    env.pop("MYPYPATH", None)
    env.pop("PYTHONPATH", None)
    command = [sys.executable, "-m", "mypy", "--no-incremental",
               "--follow-imports=normal", "--python-executable", str(python)]
    result = subprocess.run(command + [str(consumer)], cwd=str(tmp_path), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True)
    assert result.returncode == 0, result.stdout
    assert (result.stdout.count('Revealed type is "builtins.str"') +
            result.stdout.count('Revealed type is "str"')) == 4, result.stdout
    assert 'Revealed type is "None"' in result.stdout, result.stdout

    consumer.write_text(
        "from mdutils.mdutils import MdUtils\n"
        "doc = MdUtils('example')\n"
        "doc.new_list(['one', [123]])\n"
    )
    result = subprocess.run(command + [str(consumer)], cwd=str(tmp_path), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True)
    assert result.returncode != 0, result.stdout
    assert "Found 1 error" in result.stdout, result.stdout
    assert "[list-item]" in result.stdout, result.stdout
