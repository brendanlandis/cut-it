<!--
The parking spot, and it must be EMPTY before the documentation refactor is
called done. `test/gate/docs-check.py` asserts that (HTML comments like this one do
not count as content).

WHAT IT IS FOR. The page schemas -- module, rules, freeform -- are a hypothesis
about what this project's knowledge looks like, drawn from six device pages.
They will be wrong somewhere. Several of the most valuable passages in this repo
are narrative: HOW a wrong conclusion was reached, not what the fact is. A
skeleton of What it is / Facts / Traps / Open has no obvious slot for that.

WHEN A PASSAGE DOES NOT FIT, DO NOT CRAM IT INTO THE NEAREST SECTION AND DO NOT
DROP IT.

  1. Move it here VERBATIM. Nothing is lost while the question is open, and the
     passage stays intact rather than being paraphrased down to fit.
  2. Work out what shape it actually wants -- a new `##` section in the module
     schema, a new schema beside the three, or a page of its own -- and what
     else in the repo would belong in it. One instance is an exception; three
     are a missing section.
  3. Ask, WITH the proposal. Not "where does this go?" but "here is the passage,
     here is the shape I think it wants, here is what else would move into it."

Cramming is how the documentation got into the state this refactor exists to
fix: every session added to whichever file it was already in, and nobody decided
the Launchpad should live in four of them.
-->

