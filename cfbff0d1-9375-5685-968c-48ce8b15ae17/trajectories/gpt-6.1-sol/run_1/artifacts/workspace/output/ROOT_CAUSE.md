# RegExp semantic repairs

## 1. Causes and specification rules

The reference is `/workspace/spec/ecma262-2025.html`. These are distinct causes found by reading the parser/compiler/interpreter and exercising the repairs. The examples below use byte ranges, as required by the crate's string API; the specification describes input indices instead.

| Cause | Violated rule and distinguishing check | Repair |
|---|---|---|
| Entering a nested quantifier overwrote its iteration count without an undo record. When an earlier invocation resumed, it could see the later invocation's count. | 22.2.2.3.1, RepeatMatcher: recursive continuations retain their own `min`, `max`, and starting MatchState. With optimizations disabled, `^(?:(?:a?)*)*ab$` on `aaab` must match `0..4`. Restoring just the old loop-entry code made this exhaust 1,000,000 backtracks; saving the state produces the match. | Push the old LoopData before resetting the counter on entry. Existing undo machinery restores it during backtracking. |
| A reference to duplicate names was compiled as alternatives of individual references. An undefined capture succeeds empty, so this introduced an empty alternative even when another capture participated. | 22.2.2.7.2, BackreferenceMatcher, steps 1.e–g: select the defined capture; succeed empty only if none is defined. `^(?:(?<x>a)|(?<x>b))\k<x>$` must reject `b` and accept `bb`, with captures `[undefined, 0..1]`. | Concatenate the references. The early-error rule permits at most one participating capture; every other reference consumes empty. |
| Duplicate-name conflict checks identified enclosing disjunctions by nesting depth. Separate sibling disjunctions at the same depth could therefore be mistaken for one disjunction. | 22.2.1.1 and 22.2.1.4, MightBothParticipate: only different alternatives of a shared enclosing Disjunction establish mutual exclusion. `(?:(?<x>a)|b)(?:c|(?<x>d))` is an error. | Assign each enclosing disjunction a distinct identity and compare alternative indices only for shared identities. |
| Capture-name metadata followed compiler traversal order. Lookbehind reverses concatenations, so traversal order can differ from capture numbering. Also, `named_group` selected only the first occurrence of a duplicate name. | 22.2.2.7, CompileAtom's capturing-group case, associates captures with their syntactic numbers; named references use the matching GroupSpecifiers. In `(?<=(?<a>a)(?<b>b))(?<c>c)` on `abc`, `a` is `0..1`, `b` is `1..2`; in `(?<x>a)|(?<x>b)` on `b`, named `x` is `0..1`. The latter is also a consistency check between the crate's two named-capture accessors. | Store names by capture ID; named lookup searches for the participating capture. |
| `v` enabled class-set parsing without consistently enabling Unicode grammar, literal folding, boundary handling, or input handling. | UnicodeMode is enabled by either `u` or `v`; Canonicalize and WordCharacters use Unicode case semantics in that mode. Both `ui` and `vi` must match `k` against Kelvin sign, and `\b\w\b` against long s. Under `v`, `\a`, `(?=a)*`, and malformed Unicode escapes must be rejected. | Normalize the internal Unicode-mode flag at parser entry for `v`, retaining the UnicodeSets flag separately. Reject simultaneous `u` and `v`. |
| Class-set operations compared raw characters/strings, then expanded case equivalents only at the end. Complements also used the same order for `u` and `v`. | 22.2.2.9, CompileToCharSet, MaybeSimpleCaseFolding, and CharacterComplement: `v` set operands are canonicalized before intersection/subtraction/complement. `[a--A]/vi` is empty; `[a&&A]/vi` contains `a` and `A`. `\P{Lowercase_Letter}/vi` rejects `a`, whereas `/ui` accepts it. | Normalize operands before set algebra. Code-point operands are represented as complete equivalence classes; strings use folded code points. Complement the closed positive set for `v`. Preserve complement-before-expansion for `u` property escapes. |
| One-code-point `\q` strings and ordinary code points occupied separate representations during set operations. Some operations compared only corresponding representations. | CharSets contain strings, including strings of length one; their intersection is independent of which grammar production supplied the member. `[\q{a}&&a]/v` must match `a`. | Move all length-one strings into the code-point set before operations. Deduplicate string operands. |
| Empty `\q` alternatives were discarded. The implementation also lacked structural MayContainStrings propagation for negated classes. | ClassString permits empty; 22.2.1.8 defines MayContainStrings structurally, with OR for union, AND for intersection, and the left operand for subtraction. 22.2.1.1 rejects negation when that value is true. `[\q{}]/v` matches empty; `[^\q{}]/v` is invalid; `[^\q{ab}&&a]/v` is valid; `[^\q{ab}--\q{ab}]/v` remains invalid despite an empty resulting set. | Retain empty strings, try them after nonempty members, and carry the structural boolean independently of actual set contents. |
| Class-set parsing lost the first operand before a single `&`, confused different reserved punctuation with doubled punctuation, and did not consistently enforce operator lookaheads. Class-set `\b` produced letter `b`. | ClassUnion/ClassIntersection/ClassSubtraction and ClassSetCharacter grammar: `[a&]/v` includes `a`; `[!#]/v` is valid; `[ab&&c]/v`, `[a&&&]/v`, and mixed operators without nesting are invalid. CharacterValue of class `\b` is U+0008. | Parse one operator family per expression, enforce operand/range and operator lookaheads, compare doubled punctuation for equality, and produce backspace. |
| String-set emission ignored matching direction, and property-string alternatives outside brackets were not sorted by length. | CompileToCharSet and CharacterSetMatcher try strings in descending length and consume them in the specified direction. `(?<=[\q{ab}])c/v` matches `2..3` on `abc`; `\p{RGI_Emoji}/v` consumes the whole family emoji `👨‍👩‍👧`. | Reverse the order of emitted pieces in lookbehind while preserving the physical order of byte sequences; reverse code-point emission for UTF-16. Sort property alternatives through the same longest-first path as `\q`. |
| Word-boundary assertions were allowed to take quantifiers; brace Unicode escapes were parsed outside UnicodeMode; Rust's radix parser could admit a leading sign; failed surrogate pairing restored the cursor after the second `\u` rather than before it; saturated quantifier bounds could lose their ordering. | Term permits Assertion or Atom Quantifier, not quantified word assertions. CharacterEscape/RegExpUnicodeEscapeSequence require the specified hex digits and UnicodeMode for brace escapes. QuantifierPrefix early errors compare mathematical decimal values. Checks: reject `\b+`, `\u{+61}/u`, `(?<a\u003ex)`, and reversed enormous bounds; `[\uD800\u0061]/u` must match `a`. Outside UnicodeMode, `^\u{61}$` matches 61 `u` characters under the legacy grammar, not `a`. | Mark word assertions nonquantifiable; gate brace escapes; validate hex characters; preserve the second escape on failed pairing; distinguish escaped identifier characters from the name terminator; compare decimal spellings before saturating execution counts. |

## 2. Why existing tests did not expose these causes

The source tests contain substantial coverage, but their assertions do not distinguish all these cases. For example, the duplicate-reference tests try `xx`, `yy`, `xy`, and `yx`; the erroneous empty alternative does not change those anchored results. Testing the one-character input distinguishes the bug. Existing named-group tests use `named_groups`, which already searches duplicate occurrences; that does not test `named_group`. Existing class-set tests mostly exercise operations without the case-folding, empty-string, and representation combinations above.

There is direct evidence of an incorrect oracle as well: `run_regexp_unicode_escape`, `test_escapes_folding`, and `test_high_folds` expect brace Unicode escapes to work without `u` or `v`. Those three tests now fail. Their source was not changed. I did not run an untouched original checkout, and do not claim an original full-suite baseline measurement.

## 3. Other affected patterns

These are families, not special cases tied to the witnesses: nested quantifiers revisited by backtracking; any duplicate-name reference with a participating and an undefined occurrence; duplicate names in separate sibling groups; named captures reordered by lookbehind; Unicode-sensitive syntax and folding throughout `v` patterns; case-equivalent operands under every class-set operator; singleton strings crossing representation boundaries; nullable class strings; negation after string operations; property strings with prefix relationships; backward string matching; and malformed escapes or numeric bounds sharing the parser paths described above.

## 4. Engine changes

Changes are confined to `src`: parser normalization, early-error checks and class-set algebra; reversible loop entry; capture-name emission and lookup; directional string emission; property-string ordering; and specification regression tests in `src/spec_tests.rs`. Public types and method signatures remain unchanged. No dependency or build configuration changes are needed.

## 5. Behaviours retained

The engine still uses ordered backtracking, greedy/lazy continuation order, per-iteration capture resets, empty success for an undefined individual backreference, and byte ranges for UTF-8 API results. `u` and `v` property-complement semantics remain distinct. Existing budget accounting and the BudgetExhausted API remain in place; genuinely expensive searches can still exhaust the budget. The existing exponential-pattern budget tests still pass. The repair removes accidental exhaustion caused by corrupted loop state; it does not establish a universal million-backtrack bound.

## 6. How expected results were determined

Expected results were derived from the local specification, not from an unavailable network service or another JavaScript engine. RepeatMatcher fixes continuation order and capture clearing; BackreferenceMatcher selects the defined duplicate; MightBothParticipate fixes syntax acceptance; CompileToCharSet, MayContainStrings, CharacterComplement, Canonicalize, and CharacterSetMatcher determine set membership, syntax errors, string order, and direction. Match indices for non-ASCII witnesses were converted to UTF-8 byte offsets for assertions.

The loop cause was additionally checked by controlled intervention: build with the save, build after removing only that save, then restore the repaired source. A generated matrix covered eight bodies and eight choices for each of two nested quantifiers, on nine inputs, with optimizations disabled. All 4,608 repaired searches completed. In a snapshot of the first 115 old-code results, 100 differed; the old run was stopped rather than being represented as a completed matrix. The `aaab` witness above is among the differing cases. This comparison attributes those differences to loop entry, not to the simultaneous parser repairs.

## 7. Detecting regressions

`src/spec_tests.rs` asserts ranges, captures, named lookup, and syntax errors for the distinguishing examples above, including million-backtrack searches. Matching checks run with optimizations enabled and disabled. This detects the causes independently of the crate's broad positive-test coverage. The generated loop experiment is supplementary evidence, not a replacement for the retained small regression.

Validation performed:

- New specification tests: all three test functions pass, containing many independent assertions.
- Same tests with the `utf16` feature: pass.
- Existing class-set suite: 147 pass.
- Existing general suite with the three conflicting legacy-escape tests filtered: 55 pass.
- Full existing test run: three failures described in section 2; the preceding test binaries passed. The full command stopped at that failed binary. The class-set binary was run separately afterward.
- `cargo check --offline --no-default-features --features alloc`: passes.

`cargo fmt` was unavailable in the installed toolchain. Compilation reports an unused `CodePointSet::clear` method after removal of the old set-algebra implementation.

## 8. Interactions

Unicode-mode propagation determines both grammar acceptance and the folding applied to strings emitted later. Folding must precede set algebra, and singleton normalization must precede comparisons across string/code-point representations. Retaining empty strings requires both longest-first matching and the RepeatMatcher empty-progress rule. Duplicate-reference concatenation relies on correct duplicate-name early errors and per-iteration capture clearing. Lookbehind independently affects instruction order and name metadata, so correcting only one would leave the other observable error. The isolated loop experiment separates loop-state causality from these parser interactions.

## 9. One behaviour not established

This evidence does not establish conformance for every Unicode property member or every pattern/input, nor that every specification result can be obtained within a fixed operational backtracking budget. In particular, the engine deliberately still reports BudgetExhausted on the existing large exponential-pattern test. A universal conformance and budget guarantee would exceed what these measurements demonstrate.

## 10. Limits of causal claims

The table identifies source-level causes and checks that distinguish their semantics. Except for the isolated loop intervention, validation was performed on the combined repair, so individual before/after measurements are not claimed for every row. Passing tests are evidence for their assertions, not proof of exhaustive ECMAScript 2025 conformance. The three incompatible existing expectations are reported explicitly rather than counted as successes or silently changed.
