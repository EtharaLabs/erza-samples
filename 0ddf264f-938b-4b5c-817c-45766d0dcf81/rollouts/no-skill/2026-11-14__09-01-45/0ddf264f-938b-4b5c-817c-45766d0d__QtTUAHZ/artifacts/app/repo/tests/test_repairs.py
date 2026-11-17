"""Regression coverage for Pagecraft's body text, build report, asset, date, term and link-check behavior."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pagecraft.builder import BuildError, Builder  # noqa: E402
from pagecraft.content import coerce_datetime  # noqa: E402
from pagecraft.renderer import render_markdown  # noqa: E402
from test_pagecraft import make_site, write  # noqa: E402

NOW = datetime(2026, 8, 19)


def test_leading_key_value_line_is_body_text():
    html = render_markdown("Update: revised after review.\n\nBody text.\n")
    assert "Update: revised after review." in html


def test_report_says_no_feed_when_feed_is_disabled(tmp_path):
    site = make_site(tmp_path)
    config = site / "site.yaml"
    config.write_text(config.read_text().replace("feed:\n  enabled: true", "feed:\n  enabled: false"))
    report = Builder(str(site), now=NOW).build()
    assert report["feed_generated"] is False
    assert not (site / "_site" / "feed.xml").exists()


def test_asset_that_shadows_generated_output_is_a_route_collision(tmp_path):
    site = make_site(tmp_path)
    write(site / "assets" / "style.css", "body { color: red; }\n")
    with pytest.raises(BuildError, match="Route collision"):
        Builder(str(site), now=NOW).build()


def test_utc_offset_is_converted_not_dropped():
    assert coerce_datetime("2026-08-15T09:30:00+05:30", "post.md") == datetime(2026, 8, 15, 4, 0)


def test_case_variant_tags_across_posts_share_one_page(tmp_path):
    site = make_site(tmp_path)
    write(site / "posts" / "fourth.md", "---\ntitle: Fourth post\ndate: 2026-08-13\ntags: [Pagecraft]\n---\nBody.\n")
    Builder(str(site), now=NOW).build()
    assert (site / "_site" / "tag-pagecraft.html").read_text().count("<article") == 3


def test_check_reports_broken_relative_link(tmp_path):
    site = make_site(tmp_path)
    post = site / "posts" / "first.md"
    post.write_text(post.read_text() + "\nSee [the note](notes/none.html).\n")
    issues = Builder(str(site), now=NOW).check()
    assert any("'notes/none.html'" in issue for issue in issues)
