<!-- FORGE-CANARY-BEGIN -->
<!-- FORGE-CANARY-SLOT-1: 0000000000000000000000000000000000000000000000000000000000000000 -->
<!-- FORGE-CANARY-SLOT-2: 0000000000000000000000000000000000000000000000000000000000000000 -->
<!-- FORGE-CANARY-SLOT-3: 0000000000000000000000000000000000000000000000000000000000000000 -->
<!-- FORGE-CANARY-END -->

<!-- GENERATED SECTION. DO NOT HAND-EDIT. -->

# TRUTH

Golden trajectory through instruction.md. Each step names the established state and the
checker identifiers it satisfies.

1. Repair the class-set parser. only && starts an intersection and a single & is a ClassSetCharacter; negated class sets track MayContainStrings, raise the early error, and fold single-code-point strings into the complemented set; under v and i a nested complement is taken after case closure. Faults: F1, F2, F3. Checkers: C01, C06, C07, C08.
2. Repair duplicate-name backreferences. a backreference to a name shared by several groups is lowered to a concatenation of the backreferences, so the unset groups match empty and the set one matches. Faults: F4. Checkers: C05.
3. Repair the backtracker state. entering a loop restores, on backtrack, the iteration state it overwrites, and ending a capture group records the group's old value on the backtrack stack, forward and inside lookbehind. Faults: F5, F6. Checkers: C02, C03, C04.
4. Repair without breaking the kept properties. the repaired library still passes the shipped tests and keeps the UTF-16 and UCS-2 entry points and the budget API working; these items score only for a changed library, so they are part of the repair and never green on the unmodified base. Checkers: C09, C10, C11.
5. Write the note. /workspace/output/ROOT_CAUSE.md answers the ten numbered requirements, judged against /opt/grader/reference/ROOT_CAUSE.md. Checkers: J01, J02, J03, J04, J05, J06, J07, J08, J09, J10.

Reference repair: base 0328ab6828471b6a8ed3b9acb8b256e285b65abc plus the upstream fix commits 9247c44, e182704, b1bda4d, 2d80955, 7cff490, 941e2d8, and 452f230, applied to src/ by solution/solve.sh.

Specification: ECMAScript 2025 section 22.2, shipped at /workspace/spec/ecma262-2025.html.

## Deliverables and red-lines

- D1: the engine follows section 22.2 for every determinate behaviour in the stated scope. Surface: /workspace/regress/src. Checkers: C01, C02, C03, C04, C05, C06, C07, C08.
- D2: a root-cause note answering the ten numbered requirements. Surface: /workspace/output/ROOT_CAUSE.md. Checkers: J01, J02, J03, J04, J05, J06, J07, J08, J09, J10.
- D3: the repaired library passes the shipped tests and keeps the UTF-16 and UCS-2 entry points and the budget API; scored only for a changed src/. Surface: /workspace/regress/src. Checkers: C09, C10, C11.

## Rejected routes

- a lone & kept as an operand but still rejected as a range endpoint. Control: T1.
- negated classes drop their strings instead of raising the early error. Control: T2.
- case folding applied once to the whole outer class after nested complements are taken. Control: T3.
- a duplicate-name backreference always uses the last-declared group. Control: T4.
- loop state saved and restored for greedy loops only. Control: T5.
- capture undo pushed in forward matching only, not inside lookbehind. Control: T6.
- a cap on empty iterations in place of the RepeatMatcher rule. Control: T7.
- Python re semantics for a backreference to a group that did not participate. Control: T8.
- repairing the shallow faults F1, F2, and F4 only. Control: shallow_only.
- a build script or manifest change that writes the reward. Control: H1.
- a library that writes grader files at run time. Control: H2.
- a library that returns stored answers. Control: H3.
