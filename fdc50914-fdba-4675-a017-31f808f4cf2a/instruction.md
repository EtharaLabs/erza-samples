# Our JavaScript patterns don't follow the spec in regress

The Rust regex engine in `/workspace/regress` runs patterns we wrote for JavaScript, and we need it to follow ECMAScript 2025, section 22.2, "RegExp (Regular Expression) Objects", whose pattern semantics are given in `/workspace/spec/ecma262-2025.html`. We depend on five behaviours: quantifiers with backtracking; named groups, duplicate names included, and backreferences; case-insensitive matching when `i` is combined with `u` or `v`; class sets under the `v` flag, with their operators and `\q{...}` strings; and the pattern grammar together with its early errors.

When we call `find_from_budgeted` with a budget of 1,000,000, some of our patterns in these areas break section 22.2: they produce matches the specification rules out, they never produce matches it requires, they report wrong capture groups, they are accepted where section 22.2 makes them syntax errors, and they run out of budget where section 22.2 determines a result.

Work out the reason and repair the engine. The repair must also build and pass with the crate's `utf16` feature enabled, and the crate's own tests must still pass. Match ranges, capture groups, and syntax errors must equal what section 22.2 determines, also on patterns and inputs other than the ones you try, with each range read in the convention the API reports it in: UTF-8 byte offsets from `find_from_budgeted`, and UTF-16 code-unit offsets from `find_from_utf16` and `find_from_ucs2`.

Keep the crate's public API unchanged and edit only files under `/workspace/regress/src/`. You have no network access. Edits elsewhere, under `tests/` among other places, have no effect, and these are not allowed at all: any change to `Cargo.toml`, `Cargo.lock`, the dependencies, or a build script; a `.cargo/` directory anywhere in `/workspace/regress`; a symbolic link under `src/`; and a `.rs` file under `src/` that uses `include!`, `include_str!`, `include_bytes!`, `#[path`, `#![path`, `env!`, or `option_env!`.

## Root-cause note

From the evidence you gathered, write a Markdown note to `/workspace/output/ROOT_CAUSE.md` that answers each of the numbered requirements below.

1. The cause of every failure in these behaviours, not only the failures you found, with the section 22.2 grammar production, early error, or algorithm step it violates.
2. Why the crate's own tests passed with these causes present.
3. Which other patterns the same causes affect.
4. What your repair changes in the engine.
5. Which behaviours your repair leaves unchanged.
6. How you determined the correct result for the patterns you tested.
7. A check that would detect each cause.
8. Whether any of the causes interact, and how.
9. One behaviour your evidence does not establish.
10. Make only causal claims your evidence supports.
