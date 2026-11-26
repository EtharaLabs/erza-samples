# Pagecraft root-cause note

Repaired two defects in `src/pagecraft/builder.py`. The fixes act at the faulty manifest-loading and validation stages; no generated HTML, manifest, or report was hand-edited. Nothing under `tests/`, the pytest configuration, or `LICENSE` was changed.

## 1. The manifest reader rejected the manifest produced by the writer

**Location:** `Builder._load_manifest`, line 111; producer: `_save_manifest`, lines 117–127. Downstream consumers: `_remove_stale_outputs`, `_write_outputs`, and `sync_assets` called by `build`.

**Root cause and observable symptom:** The writer emits `"schema": 2`, but the reader tested `manifest.get("version")`. Consequently, every newly constructed builder replaced a valid manifest with empty `outputs` and `assets` dictionaries. An unchanged build rewrote every generated file and reported zero skipped files. Deleting a post or asset left its old output behind.

**Propagation:** Empty prior output hashes prevent `_write_outputs` from recognizing unchanged content. Empty prior output names prevent `_remove_stale_outputs` from finding deleted articles, obsolete term pages, or surplus pagination pages. Empty prior asset hashes likewise prevent asset skipping and stale asset removal. Rendering still produces the current collections, feed, and sitemap, so these can omit a deleted article while its old HTML remains publicly accessible. The next saved manifest records only current output, losing ownership of the stale files. The report reflects the faulty synchronization decisions: excessive generation and missing removals. This explains why current content, current discovery files, the manifest, and the actual directory could disagree.

**Fix and why it belongs here:** Read the same `schema` key that the writer emits, retaining the existing schema-version check. The valid previous output and asset maps now reach all synchronization stages. This restores both skipping and stale-file removal at their shared source rather than compensating in reports or editing output files.

**Evidence:** Before the fix, the unchanged-build test reported `files_skipped == 0`; the deletion test found `third.html` still on disk. Source inspection showed the reader/writer key mismatch directly. The baseline suite finished with 3 failures and 19 passes, including these two failures.

**Verification:** After the fix, the example's unchanged CLI build reports 24 skipped files, zero generated files, and zero removals. Temporary-copy checks confirm unchanged output mtimes, manifest SHA-256 hashes matching actual bytes, correct body changes in article HTML and RSS, renamed article cleanup, obsolete tag cleanup, pagination shrinking from two pages to one, and asset copy/skip/update/removal. After each source-change scenario, the incremental output file set and bytes match a fresh full build of the same sources.

## 2. Link validation used a different route-to-file mapping from generation

**Location:** `Builder._internal_link_issues`, lines 385–395. The existing shared mapping is `content.route_to_output`; generation already uses it in `_render_outputs`, including line 299 for pagination.

**Root cause and observable symptom:** Validation special-cased `/` as `index.html` and otherwise merely removed the leading slash. It therefore looked for `page/2/` in a set containing `page/2/index.html`. The shipped example has four posts and `pagination.per_page: 2`, so its correctly generated homepage necessarily links to `/page/2/`. Before the fix, `check --project example --json` returned `valid: false` with `index.html: internal link '/page/2/' does not resolve to generated output or an asset.`

**Propagation:** Content collection and rendering correctly generate the second page and its navigation URL. The checker then misinterprets that URL at the final validation stage, producing an incorrect issue and nonzero CLI exit status. Custom directory permalinks suffer the same false rejection. Changing the templates or removing pagination would only conceal the validator's mapping error.

**Fix and why it belongs here:** After the existing URL parsing and relative-link resolution, pass the target path through `route_to_output`. Generation and checking now agree that `/` maps to `index.html` and `/directory/` maps to `directory/index.html`. Invalid routes remain unresolved issues through a `ContentError` handler. Missing files still produce diagnostics; the check is not bypassed or weakened.

**Evidence:** The actual example build produced `page/2/index.html`, while its checker reported `/page/2/` missing. The baseline valid-site check test failed for exactly the same reason. The existing shared helper already specifies and tests the directory-index behavior.

**Verification:** The example CLI check now returns `{"valid": true, "issues": []}`. Checks also pass on a temporary example with `/about/` as a page permalink and links to `./?view=all#content` and `../`. An intentionally broken `missing/` relative link still yields exactly one diagnostic. Snapshots before and after checking confirm no files are written, including when output and cache do not yet exist.

## Reproducible verification

From `/app/repo`:

```sh
python -m pytest
PYTHONPATH=src python -m pagecraft.cli build --project example --json
PYTHONPATH=src python -m pagecraft.cli check --project example --json
python /app/output/verify.py
```

Results: **22 tests passed**, with no skips or deselection; example rebuild skipped all **24** unchanged outputs; example check passed. `/app/output/verify.py` contains the additional end-to-end assertions and uses temporary copies of the shipped example, leaving its source content untouched. It checks all generated-file and asset hashes against the manifest, report counts against report lists, fresh-build parity, four correctly ordered RSS items with body HTML and summaries, the 20 sitemap entries, and the robots sitemap reference, as well as the mutation and link scenarios described above. Generated artifacts were created exclusively by the build code.
