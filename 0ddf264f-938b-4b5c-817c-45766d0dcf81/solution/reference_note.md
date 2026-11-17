# Root-cause note: Pagecraft build chain (reference)

Four defects break the chain at three stages: the incremental build manifest, the RSS feed and sitemap (the feed's channel header and the sitemap entries of derived pages), and the link validation in `check`. Each fix goes in the stage that produces the wrong value, not in the stages downstream that consume it. I found no further defect; the upstream suite passes in full after these four fixes.

## D-1: manifest schema key read under the wrong name

Where: `src/pagecraft/builder.py`, `Builder._load_manifest`. The schema guard compares `manifest.get("version")` with `MANIFEST_SCHEMA`. `_save_manifest` writes that value under the key `"schema"`, and there is no `"version"` key, so the guard always fails. A correctly saved manifest is treated as an unknown schema and replaced with an empty one (`{"schema": MANIFEST_SCHEMA, "outputs": {}, "assets": {}}`).

Symptom on example/: run `pagecraft build --full`, change the tag in `posts/incremental-builds.md` from `performance` to `speed`, then run `pagecraft build`. The incremental build reports `files_skipped: 0` and rewrites every output. `removed` is empty, and `_site/tag-performance.html` is left behind even though no post has that tag any more.

Propagation: the empty `previous` map goes into two later steps. `_write_outputs` never finds a matching stored hash, so it skips nothing. `_remove_stale_outputs` computes `previous - outputs` as the empty set, so orphaned tag, category and post pages are never deleted. The new manifest is saved correctly, but the next load throws it away again. The bug repeats on every build and never fixes itself.

Fix: compare `manifest.get("schema")` with `MANIFEST_SCHEMA`. This repairs the stage that generates the bad value. With the real previous manifest loaded, the skip logic and the stale-output logic work without any change, because they were only ever wrong because of their input.

Evidence: the key written by `_save_manifest` (`"schema"`) differs from the key read by `_load_manifest` (`"version"`). The incremental summary shows `files_skipped: 0`, and the stale `tag-performance.html` is still present after the tag edit.

Verification: I ran `pagecraft build --full --project example`, changed the tag in `example/posts/incremental-builds.md` from `performance` to `speed`, and ran `pagecraft build --project example --json`. Before the fix the report showed `files_skipped: 0` and an empty `removed` list. After it, the report shows 8 files written, `files_skipped: 16`, and `tag-performance.html` in `removed`, and `_site/tag-performance.html` is gone. `python -m pytest tests/test_pagecraft.py` also changed: `test_second_build_skips_content_and_changed_source_updates_dependents` (asserts `files_skipped > 0`) and `test_deleting_content_and_assets_removes_stale_output` fail before the fix and pass after it.

## D-2: RSS lastBuildDate ignores `updated`

Where: `src/pagecraft/rss.py`, `build_rss`. `newest` is computed as `max(item["date"] ...)`, so a post's `updated` timestamp never counts.

Symptom on example/: `_site/feed.xml` has `<lastBuildDate>Sat, 15 Aug 2026 00:00:00 GMT`, but `posts/hello-pagecraft.md` was updated on 2026-08-18 and its own item reports `atom:updated` 2026-08-18. The channel date is older than one of its items, so feed readers that poll on lastBuildDate miss the revision.

Propagation: the wrong value is written into the channel header of `_site/feed.xml` and carries on to every feed consumer. A feed reader or aggregator that compares the channel `lastBuildDate` with its last poll sees no change, so it does not pick up the revised post. Item `pubDate` and `atom:updated` are computed separately and are correct, which is why the feed contradicts itself.

Fix: `max((item.get("updated") or item["date"] for item in items), default=datetime.now())`. The channel date becomes the newest updated-or-published timestamp, which is the value that stage is supposed to produce.

Evidence: compare lastBuildDate in feed.xml with the `updated` front matter of `hello-pagecraft.md` and with that item's `atom:updated`.

Verification: I ran `pagecraft build --full --project example` and then `grep -o '<lastBuildDate>[^<]*' example/_site/feed.xml`. Before the fix it printed `Sat, 15 Aug 2026 00:00:00 GMT`. After the fix it prints `Tue, 18 Aug 2026 00:00:00 GMT`, the `updated` date of `hello-pagecraft.md`. The upstream tests only check that feed.xml parses as XML, so they pass both before and after. Only this targeted check of the lastBuildDate value detects the defect.

## D-3: check resolves directory routes as bare paths

Where: `src/pagecraft/builder.py`, `Builder._internal_link_issues`, which `check` uses. An internal link target is mapped to an output path with `target.lstrip("/")` instead of `route_to_output(target)`. File routes such as `/about.html` still resolve. Directory routes such as `/page/2/`, or any `permalink: /x/`, become `page/2/`, which does not match the generated `page/2/index.html`.

Symptom on example/: the example has 4 posts at `per_page: 2`, so it builds `/page/2/`. `pagecraft check --project example` reports `index.html: internal link '/page/2/' does not resolve to generated output or an asset.` and exits non-zero. Meanwhile `build` writes `_site/page/2/index.html` and the link works when served.

Propagation: the validator's wrong path carries into the result of `check`. Every page that links to a directory-style route (pagination nav, custom permalinks) gets a false broken-link report, `check` exits non-zero, and a CI or publish step that gates on `check` fails on a correctly built site.

Fix: `relative = "index.html" if target == "/" else route_to_output(target)`. The validator now resolves routes with the same function the writer uses, so both stages agree on route-to-file mapping.

Evidence: the reported link `/page/2/` exists on disk as `_site/page/2/index.html`. `route_to_output("/page/2/")` returns `page/2/index.html`, but `lstrip` returns `page/2/`.

Verification: I ran `pagecraft check --project example; echo $?`. Before the fix it printed the `/page/2/` issue and exited 1. After the fix it prints `Pagecraft check passed.` and exits 0. In `python -m pytest tests/test_pagecraft.py`, `test_check_reports_valid_site_without_writing_output` fails before the fix and passes after it.

## D-4: sitemap lastmod of derived pages ignores `updated`

Where: `src/pagecraft/builder.py`, `Builder._render_outputs`, in the block that assembles the `sitemap.xml` entries. The derived entries (the home page, every tag and category page, `/tags.html`, `/categories.html`, `/archive.html` and the pagination pages) share one `lastmod`, `latest`, computed as `max(post.date ...)`, so a post's `updated` timestamp never counts. The post and page entries are computed separately from `page.updated or page.date` and are correct.

Symptom on example/: `_site/sitemap.xml` gives the home page, `/archive.html`, `/tags.html`, `/categories.html`, `/page/2/` and every tag and category page `<lastmod>2026-08-15</lastmod>`, but `posts/hello-pagecraft.md` was updated on 2026-08-18 and its own entry says `2026-08-18`. The pages that list the revised post look older than the post itself.

Propagation: the wrong value is written into every derived entry of `_site/sitemap.xml` and carries on to search-engine crawlers, which use `lastmod` to decide which URLs to fetch again. A crawler that compares the `lastmod` of the home, archive, index and term pages with its last visit sees no change, so it does not refresh the listings that show the revised post. The post's own entry is correct, which is why the sitemap contradicts itself.

Fix: `latest = max((post.updated or post.date for post in self.published_posts), default=None)`. The shared `lastmod` becomes the newest updated-or-published timestamp, the rule the post entries already follow, which is the value that stage is supposed to produce.

Evidence: compare the `lastmod` of `/archive.html` in sitemap.xml with the `updated` front matter of `hello-pagecraft.md` and with that post's own sitemap entry.

Verification: I ran `pagecraft build --full --project example` and then `grep -o 'archive.html</loc><lastmod>[^<]*' example/_site/sitemap.xml`. Before the fix it printed `archive.html</loc><lastmod>2026-08-15`. After the fix it prints `archive.html</loc><lastmod>2026-08-18`, the `updated` date of `hello-pagecraft.md`, and the home, index, pagination and term entries carry the same date. The upstream tests only check that sitemap.xml parses as XML, so they pass both before and after. Only this targeted check of the `lastmod` values detects the defect.
