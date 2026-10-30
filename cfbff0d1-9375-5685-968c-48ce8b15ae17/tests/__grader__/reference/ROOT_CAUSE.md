# Root cause: six faults across the class-set parser, backreference lowering, and the backtracker

## 1. The cause of each failure

- F1, a single `&` in a class set. The union loop in `parse.rs` treats a lone `&` as the start of an operator, keeps `&` and drops the operand before it, and rejects `&` as a range endpoint. In the 22.2.1 grammar only `&&` is an operator (ClassIntersection); a single `&` is a ClassSetCharacter. Examples under `v`: `[x&]` must match `x` and `&`; `[x&-z]` is a valid range.
- F2, negated classes with strings. A negated class complements only its code points, ignores its `\q{}` strings, drops empty `\q{}` alternatives, and never computes MayContainStrings. The 22.2.1.1 early errors make `[^` ClassContents `]` a SyntaxError when MayContainStrings of ClassContents is true, and 22.2.2.9 (ClassStringDisjunction, CompileCharacterClass) makes `\q{x}` the set `{x}`. Examples under `v`: `[^\q{x}]` must not match `x`; `[^\q{xy}]` must be a SyntaxError; `^[\q{}]$` must match the empty string.
- F3, case folding and complement under `v` and `i`. A nested negated class is inverted before case closure, so the enclosing class adds back case variants of the excluded characters. Section 22.2.2.9 (CompileToCharSet for NestedClass `[^` ClassContents `]`) applies MaybeSimpleCaseFolding and then CharacterComplement over AllCharacters, which under `v` and `i` holds only code points whose simple case folding is themselves. Examples under `iv`: `[[^k]]` must not match `K` or `k`; `[[^a]x]` must not match `A`.
- F4, duplicate-name backreferences. A backreference to a name shared by several groups is lowered to an alternation of backreferences, so the group that did not participate matches the empty string first. BackreferenceMatcher (22.2.2.7.2) uses the one defined group of the name. Example: `(?:(?<d>xy)|(?<d>xz))\k<d>` on `xzxz` must match `0..4`.
- F5, loop iteration state. `EnterLoop` resets the inner loop's iteration count without saving it, so backtracking into an earlier iteration of an enclosing loop restores the wrong count; the same lost count disables the empty-iteration check. RepeatMatcher (22.2.2.3.1) keeps each expansion's own state on backtrack and fails an empty iteration once min is reached. Examples: `(?:(?:b+)+){2}` on `bb` must match; `(?:(?:c?)*)*d` on `c` must end with no match, not exhaust the budget; `^(?:(?:y(?:z??))+)+$` must match `yz`.
- F6, capture undo on backtrack. `EndCaptureGroup` writes a group's end without pushing an undo entry, so after backtracking to another alternative a backreference sees the range written on the abandoned path. In 22.2.2 captures are part of the matcher state passed to the continuation, so an abandoned path leaves no trace. Examples: `(b|b\1)d` on `bbd` must match `1..3` with group 1 at `1..2`; the same shape inside lookbehind, such as `(?<=(b)(b|\1a|a\2))\1` on `baab`, must not match.

## 2. Why the crate's own tests passed

The tests in `tests/unicodesets.rs` covered single-level complements, strings outside negated classes, and `&&` but never a single `&`; the duplicate-name tests checked named group ranges, and the backreference case was a commented-out TODO; the loop and backreference tests never backtracked into an earlier outer iteration or across a group end.

## 3. Other affected patterns

F3: any negated nested class or `\P{...}` under `v` and `i` whose complement should exclude case variants. F2: every negated class with `\q{}` strings, empty `\q{}` alternatives, and the MayContainStrings early errors, including the subtraction rule that takes MayContainStrings from the first operand. F1: a single `&` anywhere in a class set, including range endpoints. F4: every backreference to a duplicated name, inside quantifiers and lookbehind. F5: nested quantifiers whose match needs backtracking into an earlier outer iteration, and nested quantifiers over bodies that can match empty. F6: every backreference evaluated after backtracking across the end of the group, forward or inside lookbehind.

## 4. What the repair changes

- F1: only `&&` starts an intersection; a single `&` is parsed as a class set character in the union loop.
- F2: the class-set tracks MayContainStrings per operand and expression (union: any; intersection: both; subtraction: first), raises the early error for a negated class that may contain strings, folds single-code-point strings into the code point set before complementing, and keeps the empty alternative after the single code points.
- F3: under `i`, the nested set is closed under case before it is inverted.
- F4: the backreference to a duplicated name is lowered to a concatenation of the backreferences, so the unset ones match empty and the set one matches.
- F5: entering a loop restores, on backtrack, the loop state it overwrites (upstream passes the iteration explicitly and reuses the SetLoopData entry).
- F6: ending a capture group pushes the group's old value onto the backtrack stack before writing the end.

## 5. Behaviours left unchanged

Patterns without `v` class sets, duplicate names, nested quantifiers, or backreferences after a group end; the UTF-16 and UCS-2 entry points; the budget API; the public API; and the existing tests.

## 6. How the correct results were determined for the patterns tested

For every pattern tested, from section 22.2 of the shipped specification: the grammar and early errors for syntax, CompileToCharSet with MaybeSimpleCaseFolding, CharacterComplement, and AllCharacters for class sets, and the Matcher, RepeatMatcher, and BackreferenceMatcher algorithms, applied by hand or by an executable transcription.

## 7. A check for each cause

Compare the engine with a transcription of the cited section 22.2 algorithms on generated patterns of each shape: nested complements under `iv`; negated classes with `\q{}` and the early errors; single `&` in class sets; duplicate-name backreferences; nested quantifiers that backtrack into earlier iterations or match empty, under a backtrack budget; backreferences after backtracking across a group end, forward and in lookbehind.

## 8. Interactions

F5 and F6 share the backtracking undo log: both are writes to matcher state without an undo entry, and a pattern can need both. F4 depends on unset backreferences matching empty, the same rule F6 restores. F2 and F3 both act on the complement step of a negated class set.

## 9. Not established

Whether `&&` and `--` under `i` and `v`, the Kelvin sign with `\b` under `iv`, and `i` without `u` or `v` on U+017F follow the specification.

## Grading reference

### Accepted causes

- F3: a nested negated class (or complement) under `v` and `i` is inverted before case folding or case closure, so case variants of excluded characters are readmitted; tied to CompileToCharSet, MaybeSimpleCaseFolding, CharacterComplement, or AllCharacters.
- F2: negated classes ignore or mishandle `\q{}` strings, and the MayContainStrings early error is missing; tied to the early errors for `[^ ClassContents ]` or to ClassStringDisjunction.
- F1: a single `&` is treated as an operator or drops the preceding operand; tied to the ClassSetCharacter or ClassIntersection grammar.
- F4: the duplicate-name backreference is lowered to an alternation, so an unset group's empty match wins; tied to BackreferenceMatcher or the duplicate named groups semantics.
- F5: the inner loop's iteration state is reset or lost on entry and not restored on backtrack; the hang is the empty-iteration check failing because of that lost count; tied to RepeatMatcher.
- F6: the capture group's end is written without being restored on backtrack, so a backreference sees a stale capture; tied to the matcher state and continuations of 22.2.2 or BackreferenceMatcher.
- J01 passes only when the note identifies all six causes F1 to F6.

### Accepted reasons the tests passed

- the tests did not exercise these shapes (single `&`, strings in negated classes, nested complements under `iv`, duplicate-name backreferences, backtracking into earlier outer iterations, backreferences after a group end), or encoded no expectation for them, or carried the duplicate-name case as a disabled TODO

### Accepted affected-pattern classes

- the classes listed in section 3 above; a note passes when, for each cause it identifies, it names at least one other pattern or pattern class of that cause beyond the patterns it reports as failing

### Accepted repair statements

- for every cause F1 to F6, a repair with the effect listed in section 4, by any mechanism; F5 may be repaired by saving the full loop state before entering, by passing the iteration count, or by another means that restores the state on backtrack; F3 may close under case before inverting or complement over AllCharacters; F6 may push an undo entry or otherwise restore the capture on backtrack
- a statement that leaves any cause unrepaired does not pass; a cap on loop iterations or on empty iterations, a larger budget, or a timeout does not repair F5

### Accepted unchanged set

- at least one of: patterns outside the faulty shapes, the UTF-16 or UCS-2 entry points, the budget API, the public API, the existing tests

### Accepted method classes

- reading the cited section 22.2 algorithms, grammar, or early errors and applying them by hand or in a transcription
- comparing against V8 RegExp through code mode, together with the cited section 22.2 steps
- a method that takes Python `re`, PCRE, or another engine as the authority without the cited section 22.2 steps does not pass

### Accepted check classes

- differential comparison with a section 22.2 transcription or with hand-derived results on patterns of the cause's shape; a regression test of the cause's shape; for F5, a check under the backtrack budget

### Accepted interaction statements

- F5 and F6 both omit undo-log entries for matcher state; F4 relies on unset backreferences matching empty; F2 and F3 both act at the complement of a negated class; or a statement that a specific pair does not interact, with a reason

### Accepted limitation classes

- `&&` and `--` under `i` and `v`; the Kelvin sign with `\b` under `iv`; `i` without `u` or `v` on non-ASCII characters; Unicode version differences in case folding or properties; lastIndex, flags, or other RegExp object behaviour outside section 22.2's pattern semantics; performance

### Rejected claim classes

- Python `re`, PCRE, or another engine's result is the correct result for these patterns (for example, that a backreference to a group that did not participate must fail)
- the budget is too small, or the hang is a performance problem that a larger budget, a cap, or a timeout fixes
- `[^\q{xy}]` should compile, or `[x&]` should be a syntax error, or `&` alone is an operator
- the duplicate-name result is correct because the first-declared group is always used
- case folding should be applied once to the whole outer class, or the complement should be taken over all code points under `v` and `i`
- the faults come from the Unicode tables, the UTF-8 decoder, or the optimizer
