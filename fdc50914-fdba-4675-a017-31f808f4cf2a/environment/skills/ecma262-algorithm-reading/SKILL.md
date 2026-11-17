---
name: ecma262-algorithm-reading
description: How to read ECMA-262 algorithm notation (abstract operations, records, Matchers and continuations, static semantics and early errors) and turn a section into an executable reference for test cases. Use when a task asks code to follow an ECMAScript specification section exactly.
---

# Reading ECMA-262 algorithms

## Contracts and invariants
- The specification is the authority. Where an engine, a library you remember, or another language's regex flavour disagrees with the text, the text decides.
- Grammar productions, lookahead restrictions (`[lookahead ≠ …]`), and early errors decide what is a syntax error; check each one, including the ones that only apply under a particular flag.
- Static semantics (functions defined per production) are evaluated on the parse tree; read every production's case, not just the common one.
- Runtime algorithms are step lists. Steps with "Assert" state invariants; steps that "return failure" or call a continuation define control flow exactly.
- Abstract operations take a record of flags or state as an argument; the same operation can behave differently for each flag combination.

## Diagnostic method
1. Find the governing clauses with the browser's or a text search on the specification file; follow every linked abstract operation to its definition.
2. Write the algorithm down as code, one function per abstract operation, keeping the step structure and names. Keep closures as closures when the text returns a function.
3. Test the transcription on the examples and notes in the specification before trusting it.
4. Generate small cases over a tiny alphabet and compare the implementation with the transcription; reduce every difference to the smallest pattern and input.
5. When the transcription and the implementation disagree, re-read the clause before deciding which one is wrong.

## Pitfalls
- Do not use another engine's output as the expected result.
- Do not skip a clause because it looks like an edge case; edge cases are where the semantics differ.
- Character sets and sets of strings, code points and code units, and case folding and case mapping are distinct concepts in the text.
