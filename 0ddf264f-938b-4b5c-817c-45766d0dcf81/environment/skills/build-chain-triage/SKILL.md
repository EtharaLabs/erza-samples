---
name: build-chain-triage
description: "Method for repairing a multi-stage site build chain whose incremental rebuild, generated artifacts and validator disagree with each other or with the content, and for reporting the repair. USE FOR: mapping the stages of a build chain, localizing a wrong value to the stage that produces it, finding the other sites of a shared rule, deriving the expected value from content and documented behaviour, verifying through the tool's own commands."
---

# build-chain-triage

A site build chain runs in stages: it reads content, assigns routes, renders pages, derives
collection artifacts such as listings, archives, feeds and discovery files, decides from a build
manifest what to write or skip, and validates the result. Every stage consumes what an earlier
stage produced, so a single wrong value usually shows up in several artifacts at once, and the
place where you notice it is rarely the place that computes it. This skill is a method, not an
answer for any one repository.

## Map the chain before editing

Read the code path of each verb the tool exposes and write down, per stage, what it consumes and
what it produces. Do the same for the content: the fields each item carries and which of them the
documentation says the output depends on. Disagreements then have an address: a stage whose
output contradicts its input.

## Repair the producing stage

For each disagreement, find the stage that computes the value, not a later stage that copies it.
Patching a consumer makes one artifact right and leaves every other consumer of the same value
wrong, and it usually leaves the chain inconsistent in a new way. Prefer the change that makes
the producing stage compute the documented value for any input over a change that corrects the
output you happen to be looking at.

## Find the other sites of the rule

One rule is often applied in more than one place: a date rule in each artifact that carries
dates, a route rule in each writer, a staleness rule in each thing that gets removed. When you
find a rule applied wrongly, grep for the rule's other applications before concluding, and
compare sibling code that already handles the same question correctly. A repair that fixes one
site of a shared rule leaves the chain self-contradictory.

## Derive the expected value, do not read it off

Decide what each value should be from the content plus the documented or standardised behaviour,
then compare the output against that. Deriving the expectation from current output only restates
the defect. Be wary of sample content in which two candidate rules give the same answer: such a
sample cannot tell the rules apart, so choose the rule the content fields and the documentation
state, not the one that happens to match the sample, and test the rule against an input that
separates them.

## Separate a wrong value from a value never written

A missing or stale artifact has two different causes: the value was computed wrongly, or the
write was skipped. Incremental machinery decides to write, skip or remove by comparing recorded
state against current state, so read that comparison before suspecting the renderer, and check
what happens when the recorded state and the files on disk disagree. A report that says it
skipped everything is a claim about the comparison, not evidence that the output is correct.

## Verify with the tool's own commands

Run the chain end to end rather than inspecting one artifact: build from a clean state, edit or
delete content and rebuild, build again without changes, and run the validator. Compare the file
tree, the machine-readable report counts and the exit codes across those runs, and keep the
project's own test suite passing throughout. A command that exits zero has not told you the
output is right; check the artifact.

## Report only what you verified

For each problem, state where the wrong value is produced, what it looks like from outside, what
it reaches downstream, the repair and why it belongs at that stage, and the observation and the
command that back it. Keep claims to what you actually ran. If you suspect more than you
checked, say what you checked and what you did not.
