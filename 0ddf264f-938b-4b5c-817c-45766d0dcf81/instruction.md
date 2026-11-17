The Pagecraft static site generator in `/app/repo` gives wrong or inconsistent results across its build chain when it runs on the site content shipped in `/app/repo/example`. Incremental rebuilds, the generated outputs and the check command do not agree with each other or with what the content says they should produce.

Repair the generating code so the whole chain behaves correctly from start to finish.

Then write a root-cause note to `/app/output/note.md`. For each problem you find, cover:

- where it is in the code
- the symptom you can observe
- how it carries through to later stages of the chain
- the fix, and why it repairs the stage that generates the bad output
- the evidence you used
- how you verified the fix

Rules:

- Do not modify anything under `tests/` or the vendored `LICENSE`.
- Do not disable, skip, xfail, delete or deselect any test, and do not change pytest configuration to do any of that.
- Do not hand-write or patch generated output (the built site, the build manifest or the build report) in place of fixing the code that generates it.
