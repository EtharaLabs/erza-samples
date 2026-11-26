# RegExp investigation

This report distinguishes source-level causes from demonstrated outcomes. It is not evidence of exhaustive ECMAScript 2025 conformance. The implementation changes and regression checks are under `src/`.

## 1. Causes and specification rules

* Duplicate-name references were lowered to alternatives of numeric references. An unmatched capture succeeds without consuming input, so that lowering could bypass the participating capture. Section 22.2.2, CompileSubpattern for `AtomEscape :: k GroupName`, selects the participating capture from GroupSpecifiersThatMatch; it does not choose an unmatched capture as an alternative. `(?:(?<x>a)|(?<x>b))\k<x>` must match `bb`, and must not match `b`.
* `Match::named_group` returned only the first capture slot with the requested name. This lost a later participating capture. The specification's named-group result construction uses the participating capture for a duplicate name.
* Duplicate-name validation identified disjunctions by nesting depth. Separate sibling disjunctions can have different alternative numbers without making their captures mutually exclusive. The GroupSpecifier early error in 22.2.1 requires the same-name occurrences to be separated by alternatives of a common Disjunction. `(?:(?<x>a)|b)(?:c|(?<x>d))` therefore is an error.
* EnterLoop reset its iteration count without preserving the prior invocation's state. Backtracking through a nested invocation could therefore observe overwritten loop state. RepeatMatcher (22.2.2.3) passes repetition state to continuations; a later invocation cannot overwrite an earlier continuation's state. The repair saves the complete loop data before initialization. This is a source-level state-restoration finding; the added nested-loop example alone does not prove that it triggered the original defect.
* Class-set intersection and subtraction operated on raw operands before case closure. Under `iv`, CompileToCharSet and MaybeSimpleCaseFolding require case-equivalent operands to compare equally. For example `[a&&A]` contains `a` and `A`, while `[a--A]` contains neither.
* Class-set single-character strings and code points were stored separately, and the string-disjunction intersection branch discarded cross-representation matches. CompileToCharSet treats a one-character string as the corresponding character set element. `[\q{a}&&a]` contains `a`.
* Empty ClassString alternatives were discarded. The grammar explicitly permits an empty ClassString, whose compiled value is the empty string. `[\q{}]` must match an empty range. Empty alternatives also have to follow character alternatives: `[a\q{}]` matches `a` before considering the empty string, as required by the character-class matcher’s descending-length iteration.
* Negated classes lacked compositional MayContainStrings validation. The CharacterClass and NestedClass early errors in 22.2.1 reject a negated ClassContents whose MayContainStrings (22.2.1.8) is true. This is syntactic metadata, not a test of whether subtraction happened to remove all strings. Intersection combines metadata with AND; union uses OR; subtraction keeps its left operand's metadata.
* `\W` and `\P` operands in `iv` complemented before closing the positive operand. Under `v`, complement must be formed in the case-folded universe. Closing the positive operand before complementing prevents excluded equivalents from being reintroduced. `[\W]/iv` excludes long s.
* The first single ampersand in a union discarded the preceding operand. ClassUnion includes both characters in `[a&]`.
* ClassSetReservedDoublePunctuator checking rejected any adjacent members of the reserved-punctuation family, rather than identical pairs. The grammar lists doubled punctuation, not arbitrary mixed pairs.
* ClassSetCharacter's `\b` path returned the letter b instead of U+0008, violating CharacterEscape's ControlEscape value, including inside `\q` strings.
* Unicode hexadecimal parsing delegated digit validation to Rust integer parsing, which accepts a leading plus. Hex4Digits and HexDigits permit hexadecimal digits only. `\u{+41}` and `\u+041` are errors under `u`.

These are the causes identified in this investigation, not a substantiated claim that no other causes exist.

## 2. Why existing tests passed

The existing suite passed after these repairs. Its continued success establishes compatibility for its assertions; it does not establish historical coverage of each defect. The offending code paths require combinations such as duplicate-name references, sibling disjunctions, empty class strings, or folding before set subtraction. Source inspection shows why simpler examples need not exercise those paths. I did not measure the historical suite's branch coverage.

## 3. Other affected patterns

The mechanisms generalize to arbitrary duplicate names and sibling disjunctions; nested reentry of quantified bodies; case-equivalent operands such as Kelvin sign and k; nested set operators; one-character `\q` alternatives; empty strings embedded in larger unions; syntactically string-bearing operands inside negated sets; mixed reserved punctuation; and escaped backspace in strings. These are mechanism-based families, not an exhaustive enumeration of accepted patterns.

## 4. Repair

Named references now concatenate references to mutually exclusive capture slots: all undefined slots consume nothing, while the participating slot supplies the required text. Name lookup searches for a participating slot. The preliminary scanner assigns each disjunction a distinct identity and compares shared identities when validating duplicates. Loop initialization pushes restoration data.

Set operands share a normalized representation; singleton strings become code points. Case closure precedes set algebra and positive operands are closed before complement. MayContainStrings is retained separately from the computed set. Empty strings are retained and ordered after nonempty matches. The punctuation, ampersand, backspace, and hexadecimal grammar paths are corrected. Public signatures are unchanged.

## 5. Unchanged behavior

The API's coordinate conventions, input indexers, capture numbering, greedy/lazy ordering, and budget accounting are unchanged. The repair does not replace Unicode tables or add dependencies. Existing tests exercise substantial unchanged behavior, but cannot establish that every previously correct pattern remains correct.

## 6. Oracle and validation

The oracle was the local `/workspace/spec/ecma262-2025.html`, particularly the pattern grammar and early errors, MayContainStrings, RepeatMatcher, named-reference compilation, Canonicalize, CompileToCharSet, and character-class string ordering. Expected results in `ecma2025_regressions` were derived directly from these rules. Tests call find_from_budgeted with 1,000,000 steps and treat exhaustion as a failure. The Kelvin-sign check uses UTF-8 byte range 0..3. The utf16-specific check matches k after an astral character and asserts code-unit range 2..3 and the same named capture for both UTF-16 APIs.

The default and utf16 crate suites were run; final command outcomes are recorded in the task response. No external JavaScript implementation or network oracle was used.

## 7. Detection checks

The source regression module checks duplicate references on both `bb` and `b`, later duplicate-name lookup, sibling-name rejection, a nested quantified body, folded intersection and subtraction, singleton-string intersection, empty-string matching, empty/character precedence, negated-string rejection, ampersand union, backspace, Unicode folding and hexadecimal errors. The utf16 module checks both code-unit APIs. Additional focused checks should cover `[!#]/v` versus `[!!]/v`, `[\q{\b}]/v`, nested property complements, and nested-loop rollback with capture assertions. Those additional cases were not all executed here.

## 8. Interactions

Allowing duplicate names safely depends on mutual-exclusion validation; concatenating references relies on that invariant. Singleton normalization must preserve MayContainStrings before removing the original string representation. Empty strings need both syntax metadata and length priority. Folding must happen before complement and set algebra, and nested sets must retain these invariants. Loop rollback and capture rollback coexist on the same backtracking stack.

## 9. Not established

This evidence does not establish complete section 22.2 conformance or that every valid pattern can finish within 1,000,000 backtracks. In particular, quantifier bounds beyond machine integer capacity remain saturated by the parser, and this investigation has not repaired or validated arbitrary-precision bound comparisons. General catastrophic backtracking is also not eliminated.

## 10. Causal scope

Claims above are limited to inspected transformations and the specified checks. Passing examples are not a proof of all pattern semantics. Consequently the user's universal repair requirement remains unestablished; this note deliberately does not label the patch an exhaustive repair.
