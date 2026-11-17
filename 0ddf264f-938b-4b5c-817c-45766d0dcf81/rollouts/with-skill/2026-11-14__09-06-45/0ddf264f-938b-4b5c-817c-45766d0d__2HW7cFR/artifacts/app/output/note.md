# Pagecraft build-chain root causes and verification

The repair changes generating code in `src/pagecraft/builder.py`, `assets.py`, and `rss.py`. No files under `tests/`, pytest settings, or `LICENSE` were changed. The example outputs and manifest were regenerated with Pagecraft commands.

## Chain and baseline evidence

`build` loads configuration and the manifest, loads/normalizes Markdown metadata, filters publishing state, assigns routes, renders HTML and collection artifacts, removes obsolete paths, synchronizes assets, writes changed output, saves hashes, and reports those operations. `check` shares the rendering and collision stages, then validates local links without writing output. `clean` removes output and cache. Watch and serve use the same builder.

README's publishing contract says to render the complete public site, write only changed files, and remove stale files. `route_to_output()` maps directory routes to `index.html`. Metadata distinguishes publication `date` from `updated`; pagination has two posts per page in the example.

Before changes, `python -m pytest` reported **3 failed, 19 passed**: unchanged builds skipped nothing, deleted content remained, and check rejected a valid paginated site. Two consecutive example CLI builds each generated all **24** files and skipped **0**. Example check exited **1**, reporting `/page/2/` as unresolved despite `page/2/index.html` existing.

The example's `hello-pagecraft.md` says `date: 2026-08-15` and `updated: 2026-08-18`. Its article sitemap entry already said August 18, but home/collection entries said August 15 and RSS `lastBuildDate` said `Sat, 15 Aug 2026 00:00:00 GMT`. The HTML-only tag was also assigned August 15 even though its sole post was dated August 4.

## 1. Saved manifests were rejected when loaded

**Location:** `builder.py`, `Builder._load_manifest()` (line 104) and `_save_manifest()` (line 117).

**Symptom and propagation:** The writer stored `schema: 2`; the reader checked `version`. Every subsequent builder discarded valid output and asset hashes. No-op builds rewrote everything, and stale cleanup had no previous paths to remove. Obsolete articles, taxonomies, pagination and assets could remain even after current feeds and listings stopped referencing them.

**Fix:** Read the same `schema` field the writer emits. This restores the state consumed by both output synchronization and asset cleanup, rather than treating each stale artifact separately.

**Evidence and verification:** The mismatched keys explain the baseline failures above. After the fix, the unchanged example build generates **0**, skips **24**, and reports no removals. The integration probe renames an article to `/writing/welcome/` and confirms the old file is removed. Deleting three other posts and one asset removes **11** stale files, including page 2, an unused category, an unused tag, articles and the asset. All remaining file hashes match a subsequent full build.

## 2. Skip decisions trusted manifest hashes without checking destination bytes

**Location:** `builder.py`, `_write_outputs()` (line 447); `assets.py`, `sync_assets()` (line 14, skip comparison at line 33).

**Symptom and propagation:** With a valid manifest, the old comparisons required only an unchanged desired/source hash and an existing destination. A damaged generated file or copied asset could therefore be reported as unchanged forever. The manifest described intended content while disk content differed; check renders from source, so its success could not detect or repair that disk difference. The manifest bug initially masked this second defect by forcing rewrites.

**Fix:** Both skip paths now require an actual file whose byte hash matches the desired/source hash. Missing files are regenerated or recopied as before. Fixing both writers prevents HTML/feed and asset synchronization from applying contradictory rules.

**Evidence and verification:** The old predicates checked `exists()` without hashing the destination. In a temporary example copy, the probe deliberately corrupts the built feed and copied asset and removes the stylesheet. The next build regenerates **2** outputs, recopies **1** asset, skips **22** outputs, and restores exactly the original file-hash map. Those deliberate corruptions are test stimuli; all repairs are performed by the generator.

**Tradeoff:** Skipping now reads destination bytes, adding I/O in exchange for checking the actual output state.

## 3. The checker used a different route-to-file rule

**Location:** `builder.py`, `_internal_link_issues()` (line 391); shared mapping in `content.py`, `route_to_output()`.

**Symptom and propagation:** Generation mapped `/page/2/` to `page/2/index.html`. Validation stripped the leading slash and looked for `page/2/`. Correct generated pagination therefore caused `check` to exit 1. Custom directory permalinks had the same mismatch.

**Fix:** After resolving relative URLs and extracting the path, use `route_to_output()` for validation too. Unsafe paths become validation issues. This repairs the checker at the stage that computes its lookup key.

**Evidence and verification:** The baseline example check named precisely `/page/2/`. The repaired example check exits **0**, with `valid: true` and no issues. The probe also checks a directory permalink, a directory URL with query and fragment, and a genuinely broken relative `notes/missing.html` link. Only the broken link is reported; check exits **1** for it and leaves all output hashes unchanged.

## 4. Sitemap collections used publication dates and unrelated members

**Location:** `builder.py`, `_render_outputs()` sitemap-entry construction (line 351). `discovery.py` only serializes the supplied entries.

**Symptom and propagation:** One global `max(post.date)` was copied to every collection. Updates disappeared, and narrow tag/category pages or older pagination pages inherited dates from posts they did not contain. The serializer faithfully emitted those wrong inputs; changing XML formatting would not fix them.

**Fix:** Compute each post's change date as `updated or date`, consistent with individual entries. Home and pagination use their displayed slices; tag/category pages use their own members; taxonomy indexes and archive use the published collection. Keep publication ordering, article dates, and omission of dates for timeless pages intact.

**Evidence and verification:** Derived directly from shipped content: home is **August 18**, HTML tag is **August 4**, Tooling category is **August 12**, and page 2 is **August 9**. XML assertions verify each. A separating probe updates the older August 4 post to August 20: its tag, Tooling category, page 2, archive and taxonomy indexes advance to **August 20**, while home remains **August 18**. This distinguishes collection membership from a global maximum and publication from modification time.

## 5. RSS channel dates ignored revisions and the feed limit

**Location:** `rss.py`, `build_rss()` (line 14).

**Symptom and propagation:** Channel `lastBuildDate` used maximum publication date across all input posts. An updated item could carry August 18 in `atom:updated` while the channel still claimed August 15. Posts excluded by `posts_limit` could also affect the channel date. Feed clients consumed inconsistent freshness metadata even though item publication dates were correct.

**Fix:** Slice the feed items first and compute the channel maximum from `updated or date` over those emitted items. Item `pubDate` remains the original publication time. The correction belongs in the feed generator, which owns both the selected items and channel metadata.

**Evidence and verification:** The shipped date/updated pair and parsed baseline feed expose the discrepancy. The probe confirms an older post updated August 20 moves channel `lastBuildDate` to August 20 while its `pubDate` remains August 4. Reducing the feed to one item excludes that post and yields **Tue, 18 Aug 2026 00:00:00 GMT**.

## 6. RSS UTC conversion failed for aware non-UTC callers

**Location:** `rss.py`, `_as_utc()` (line 10), used by channel, publication and Atom update serialization.

**Symptom and propagation:** The helper returned any aware datetime unchanged. Direct `build_rss()` callers with a non-UTC offset could trigger `format_datetime(..., usegmt=True)` failure, and Atom updates could retain a non-UTC offset. The normal Markdown loader already normalizes offsets; this is an additional shared-rule defect found while tracing date serialization, not a failure caused by the shipped date-only examples.

**Fix:** Convert aware values with `astimezone(timezone.utc)`; continue treating naive values as UTC. All three serializers now receive UTC values.

**Evidence and verification:** A direct feed-generation probe supplies publication and update values at 09:30 +05:30. Parsed channel and item dates are **04:00:00 GMT**, and Atom updated is **2026-08-18T04:00:00Z**. The existing offset-normalization regression also passes.

## 7. Feed reporting described availability rather than a write

**Location:** `builder.py`, `build()` report construction (line 487).

**Symptom and propagation:** `feed_generated` was based on membership in the in-memory outputs dictionary. Once incremental skipping works, a build can report zero generated files but still say the feed was generated. JSON consumers receive conflicting operation counts.

**Fix:** Derive the flag from the feed path's membership in the actual `generated` list, after synchronization. The report now reflects the producing stage's actions.

**Evidence and verification:** The old predicate tested `outputs`, which always contains an enabled nonempty feed. Clean builds and repaired/edited feeds report **true**; unchanged builds report **false**, including the final unchanged build with **14** skipped files after deletions. The existing disabled-feed test still passes.

## 8. Reusing a Builder retained earlier operation state

**Location:** `builder.py`, `build()` entry (line 468).

**Symptom and propagation:** Generated/skipped/removed lists were initialized only in the constructor, and the in-memory manifest was not refreshed after writes. Repeated use of one Builder accumulated historical operations and compared against old state, corrupting incremental decisions and reports even after the manifest loader was repaired.

**Fix:** Reset operation lists and reload the current manifest at each build. Each invocation reports and compares its own state.

**Evidence and verification:** Constructor-only initialization and absence of refresh exposed the defect. The integration probe calls `build()` twice on one Builder against unchanged output; both generate nothing, and the second skipped list has exactly one entry per current output, without accumulation.

## Commands and retained evidence

Final validation completed successfully:

- `python -m pytest`: **22 passed**; no tests disabled or modified.
- `PYTHONPATH=src python -m pagecraft.cli clean --project example`
- `PYTHONPATH=src python -m pagecraft.cli build --project example --json`: **24 generated**.
- The same build again: **0 generated, 24 skipped, feed_generated false**.
- `PYTHONPATH=src python -m pagecraft.cli check --project example --json`: exit **0**, valid, no issues.
- `python /app/output/verify_chain.py`: all clean/incremental/edit/rename/delete/full-build/disk-repair/date/link/reuse assertions pass on temporary copies of the shipped example.

Raw example reports are in `/app/output/example-clean-build.json`, `example-unchanged-build.json`, and `example-check.json`. Reproducible integration assertions are in `/app/output/verify_chain.py`, with results and sitemap date maps in `/app/output/verification.json`. The repository's example Markdown and configuration were left unchanged. The extra asset and separating content variants existed only in temporary copies.
