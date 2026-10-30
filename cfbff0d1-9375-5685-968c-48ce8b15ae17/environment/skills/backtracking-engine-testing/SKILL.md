---
name: backtracking-engine-testing
description: Testing and debugging backtracking matchers and parsers - differential testing against a reference, step budgets instead of timeouts, state restoration on backtrack, and case reduction. Use when a backtracking engine gives wrong matches, wrong captures, or appears to hang.
---

# Testing backtracking engines

## Contracts and invariants
- Every write to matcher state that a later backtrack may need to undo must be undoable: positions, capture ranges, loop counters, and any other per-path state.
- A path that is abandoned leaves no trace on the path tried next.
- A search that cannot terminate in a bounded number of steps is a correctness fault until shown otherwise; budgets report it deterministically.

## Diagnostic method
1. Reproduce with the engine's step budget, never with wall-clock time.
2. Build or obtain an independent reference for the semantics, and compare on many small generated patterns and inputs.
3. Reduce each disagreement: remove alternatives, quantifiers, and characters while the disagreement persists.
4. Trace the backtrack stack for the reduced case: record each push and pop, and look for state written without a matching undo entry.
5. Fix the general cause, then rerun the whole comparison, the existing tests, and every entry point.

## Pitfalls
- Raising the budget, capping iterations, or adding a timeout hides a fault instead of fixing it.
- A fix that handles only the shape of one failing case often breaks the opposite direction (lookbehind), the other greediness, or counted repetition.
- Passing the existing tests says nothing about shapes the tests never contain.
