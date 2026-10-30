# RegExp investigation

## 1. Causes, rules, and distinguishing checks

The reference is the supplied ECMAScript 2025 HTML, section 22.2. Match offsets below are the crate's UTF-8 byte offsets. These are implementation causes found by inspection and targeted execution, not a claim that a finite test suite proves full conformance.

| Cause | Rule violated and a detecting check | Repair and affected family |
| --- | --- | --- |
| Entering a general loop reset its iteration count without a backtracking record for the previous activation. Re-entering an inner loop could destroy state needed when returning to an earlier outer iteration. | 22.2.2.3.1 `RepeatMatcher`: recursive calls have their own `min`, `max`, and entry state; its continuation rejects empty optional iterations. `^((a?)*)*ab$` on `ab` must match 0..2 with both captures undefined. | Save loop state before resetting the count. Affects nested repetitions whose earlier activations can be revisited, especially nullable inner repetitions. |
| Closing a capture changed its end (or start backwards) without recording the open capture state. Backtracking to an alternative inside the group could see a completed capture from the abandoned alternative. | 22.2.2.7 `CompileAtom` for a capturing group constructs a new capture state in its continuation; 22.2.2.7.2 `BackreferenceMatcher` sees undefined for a still-open group. `^(a|a\1)b$` on `aab` must fail. | Record capture state at group exit as well as entry. Affects alternatives, continuations, repetitions, and references inside groups that have previously completed on an abandoned path. |
| A duplicate-name reference was compiled as alternation over numbered references. An undefined alternative succeeds empty and can bypass the actual participating capture. | 22.2.2.7.2 scans all indices, selects the defined capture, and only succeeds empty if none is defined. `^(?:(?<x>a)|(?<x>b))\k<x>$` must match `aa` and reject `a`. | Concatenate the numbered references: undefined groups consume nothing and the participating one consumes its capture. This relies on the grammar's exclusivity invariant and repetition capture reset. |
| Duplicate-name validation identified disjunctions by nesting depth, confusing different sibling groups. | 22.2.1.1 uses `MightBothParticipate` (22.2.1.4), which requires an actual common enclosing disjunction separating the groups. `(?:(?<x>a)|b)(?:c|(?<x>d))` is a syntax error. | Give each enclosing disjunction a unique identity. Affects duplicate names in separate sibling or more deeply nested groups. |
| `named_group()` returned the first occurrence of a name even if a later duplicate participated. | 22.2.7.2 `RegExpBuiltinExec` constructs the named result from the participating capture. Matching `(?:(?<x>a)|(?<x>b))+` on `ab` leaves group 1 undefined, group 2 and name `x` at 1..2. | Search equal names for a defined capture. The named-groups iterator already did this. |
| `v` selected class-set parsing but did not activate Unicode grammar, canonicalization, or input folding. | `HasEitherUnicodeFlag`, 22.2.2.7.3 `Canonicalize`, and the UnicodeMode grammar parameter. `/k/iv` matches Kelvin sign; `/\a/v` is invalid. | Normalize the internal Unicode-mode flag before parsing and compilation. This reaches literals, boundaries, references, escapes, optimization, and execution. Reject simultaneous `u` and `v`. |
| Set algebra operated on raw operands and folded only the final result; negative word classes inside brackets complemented the unexpanded word set. | 22.2.2.9 `CompileToCharSet` applies `MaybeSimpleCaseFolding` to operands before v intersection/subtraction and complements folded sets. In contrast u property complements are canonicalized after complement. `[a&&A]` under `iv` matches `a`; `[a--A]` does not. `[\W]` under `iu` or `iv` rejects Kelvin sign. `\P{Lowercase_Letter}` rejects `a` under `iv` but accepts it under `iu`. | Normalize each operand before algebra; fold string elements; unify singleton strings with code points; expand positive word/property operands before v complement. Use legacy uppercase equivalence for legacy brackets and restrict Unicode word expansion to Unicode mode. Affects ranges, nested classes, strings, negative properties, and combinations of operators. |
| Empty `\q` alternatives were discarded; the string branch was always preferred to the character branch, even when empty. | `ClassString :: [empty]` is permitted; 22.2.2.8 and 22.2.2.10 try class strings by descending length. `[\q{a|}]` on `z` must match 0..0; `[a\q{}]` on `a` must match 0..1. | Preserve empty strings, normalize singleton strings, and emit longer strings, characters, then empty. Sort all emitted string sets by length, including standalone string properties. Affects empty disjunction arms, set algebra with empty strings, and quantification of these classes. |
| Negation did not implement syntactic `MayContainStrings`. | 22.2.1.1 and 22.2.1.8: `[^\q{ab}]` and `[^\q{}]` are errors, but `[^\q{ab}&&a]` is valid because intersection's flag is the conjunction of its operands' flags. | Track the static flag separately from the evaluated set: union OR, intersection AND, subtraction left operand. Validate at each negated class. This also covers strings eliminated by set operations. |
| Class-set parsing lost the first operand before a single `&`, treated any two reserved punctuators as a forbidden pair, decoded `\b` as `b`, omitted bracket syntax restrictions in string characters, and admitted malformed operator operands. | `ClassUnion`, `ClassIntersection`, `ClassSubtraction`, `ClassSetCharacter`, `ClassSetReservedDoublePunctuator`, and `ClassEscape :: b`. `[a&]` contains `a`; `[!#]` is valid; `[\b]` matches backspace; `[a&&&b]`, `[a&&b--c]`, `[a-b&&c]`, `[\q{[}]`, and `[\q{]}]` are errors. | Parse one consistent operator form, enforce range endpoints, preserve every union operand, compare identical doubled punctuators, and decode backspace correctly. Affects nested sets and q strings using the same character parser. |
| String-set sequences were emitted in forward code-point order inside lookbehind. | 22.2.2.8 compiles class-set matching with the requested direction. `(?<=[\q{ab}])c` on `abc` matches 2..3. | Emit string elements from right to left when in lookbehind, retaining each UTF-8 character's byte order. Affects all multi-character q strings and string properties in backward matching. |
| Unicode escapes used numeric parsing that accepted a leading plus; braced Unicode escapes were interpreted without Unicode mode; failed surrogate pairing consumed the second `\u` prefix; escaped `>` could terminate a group name. | `RegExpUnicodeEscapeSequence`, `Hex4Digits`, `GroupName`, and `RegExpIdentifierPart` in 22.2.1. `\u{+61}`, `\u+061`, and `(?<x\u003E>a)` under u are invalid. Without u/v, `\u{61}` means identity `u` repeated 61 times under the legacy grammar. | Require hex digits, gate braced/pair escapes on Unicode mode, roll back the entire attempted second escape, and distinguish escaped name characters from delimiters. Group names themselves always use Unicode identifier decoding. |
| Decimal quantifier bounds saturated to machine integers before ordering validation, concealing reversed bounds when both overflowed. | 22.2.1.1 compares the mathematical values of `{DecimalDigits,DecimalDigits}`. `a{99999999999999999999999999999,88888888888888888888888888888}` is invalid. | Compare normalized decimal digit sequences as well as retaining bounded machine counters for execution. Affects reversed very large finite quantifiers. |

## 2. Why existing tests passed

Before changes, `cargo test --offline -q` passed the crate's tests. They did not establish coverage of the distinguishing examples above. Inspection shows duplicate-name tests using the named iterator (which already preferred defined captures), and backreference examples that did not force rejection of an empty reference alternative. Existing class-set tests cover many positive strings and operators, but those passing cases did not establish correct empty strings, static string-negation analysis, or all operator/case combinations. The budget tests establish exhaustion for genuine exponential searches, not correct restoration across nested nullable loop activations.

Three existing tests actually encode an incompatible expectation: `run_regexp_unicode_escape`, `test_escapes_folding`, and `test_high_folds` expect braced Unicode escapes without Unicode flags. They fail after correcting that interpretation. Their files were not changed.

## 3. Scope beyond the examples

The last column of the table identifies the affected pattern families. Repairs are at shared state-transition, parsing, set-normalization, and emission boundaries; they do not special-case example patterns or inputs. The table's checks are retained in `src/lib.rs` where applicable, with matching checks run both with and without optimization.

## 4. Engine changes

Changes are in `parse.rs`, `classicalbacktrack.rs`, `emit.rs`, `unicode.rs`, `api.rs`, and unit tests in `lib.rs`. They restore backtracking state, implement duplicate-name selection and structural validation, normalize Unicode mode and set operands, retain empty strings, enforce the relevant grammar/early errors, and emit strings in matching direction. Public API signatures and dependencies are unchanged.

## 5. Preserved behavior

Greedy/lazy branch preference, repetition capture clearing, atomic lookaround behavior, numbered capture ordering, UTF-8 byte ranges, search-start semantics, and the budget API remain in place. Existing budget tests still require genuine exponential work to report `BudgetExhausted`. Ordinary successful matches and syntax cases covered by the passing existing suite remain covered. This is a statement about the implementation strategy and observed checks, not an assertion that every untouched behavior was exhaustively tested.

## 6. Deriving expected results and validation

Expected values were derived from the supplied grammar and algorithms, without a network oracle. For the nullable nested-loop example, each optional empty iteration must fail its repetition continuation, allowing the outer repetition to stop and the literal `ab` to consume the input. For self-references, the enclosing capture is undefined until its closing continuation. For duplicate references, only the participating capture supplies text. For v sets, evaluate normalized operands before algebra; for early errors, compute the static syntax flags independently of set membership.

A controlled experiment disabled only the newly added loop-entry save while retaining the other repairs. A generated nested-quantifier probe then reported budget exhaustion for `^((?:(a?))*)*ab$` on `ab`, `aab`, and longer short inputs with budget 1,000,000. With the save enabled the probe completed and returned the expected matches/captures. The slow disabled-save experiment was stopped after obtaining these counterexamples; the source was restored and the permanent focused checks rerun. This isolates that loop-state cause from the other repairs.

Validation completed:

- Original full suite passed before changes.
- New focused regression tests pass, including optimization enabled and disabled and the 1,000,000 budget.
- Existing suite passes when excluding the three incompatible Unicode-escape tests named above: 635 tests plus 15 passing doctests; one doctest remains ignored.
- All 147 existing Unicode-set tests pass; all 262 property-escape tests pass in the broader run.
- Focused tests pass with the `utf16` feature.
- `cargo check --offline --no-default-features --features alloc -q` passes.
- No forbidden source inclusion macros, source symlinks, or `.cargo` directories were found. No manifest, lockfile, dependency, or build-script changes were made.

`cargo fmt` was unavailable in this environment; it was not installed or fetched.

## 7. Detecting recurrence

Each row in the table provides a distinguishing check. Use assertions on syntax rejection and, for matches, both full ranges and participating/undefined captures. The retained tests cover the nested-loop budget result, capture rollback, duplicate references and lookup, structural name conflicts, u/v case behavior, set algebra, empty strings, string negation, character grammar, backward strings, escape errors, and overflowing bound order. For broader future coverage, generate nested repetitions and nested set expressions and derive expected results with an independent implementation of the cited algorithms. Comparing only optimized and unoptimized execution cannot detect a bug shared by both.

## 8. Interactions

Loop/capture restoration affects which capture a reference sees. Correct duplicate-name references rely on early-error validation and clearing all enclosed captures on repetition, so that at most one candidate is defined. Enabling Unicode mode for v changes escape grammar, literal folding, input folding, and word boundaries simultaneously. Operand folding must precede complement and algebra; normalizing singleton strings into the code-point domain prevents string/character representation differences from changing intersections. Empty class strings also exercise repetition's empty-progress rule. Backward string emission shares the lookbehind direction used by captures and references.

## 9. Not established

These tests do not establish that every pattern/input with a specified result finishes within a fixed budget of 1,000,000. Genuine exponential backtracking remains possible, and the API deliberately reports exhaustion (the existing exponential-budget tests still pass). Nor does this investigation establish complete section-22.2 conformance for all sizes, encodings, Unicode database entries, or resource limits; for example, existing parser depth and capture-count limits remain. Full universal conformance under the stated finite budget is therefore not a result demonstrated by this repair.

## 10. Accuracy boundary

The causes above are grounded in the source transitions and the cited specification rules; executed checks and the single-variable loop experiment are distinguished from inspection-based conclusions. Passing tests are not used as proof of universal correctness. No claim is made about the user's undisclosed patterns, and no evidence is inferred from an unavailable JavaScript runtime. The three incompatible legacy tests and the remaining budget/resource limitations are reported explicitly.
