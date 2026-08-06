#!/usr/bin/env python3
"""The documentation gate. No Pd, no device, ~200 ms.

    python3 tools/docs-check.py           check, exit non-zero on any failure
    python3 tools/docs-check.py -v        and list every check that passed

WHAT IT IS FOR. This project's documentation restates the same fact in up to ten
files -- `47 + n` was in eight, `pgmout` is 1-based in seven -- and every copy
was written by an agent that had no way to know the others existed. Nothing
connects them, so a correction lands in one file and the other seven quietly go
stale. That is not fixable by discipline; the copies have to be MECHANICALLY
tied together, which is what this does.

The idea is small: THE SAME FACT ALREADY EXISTS TWICE IN MACHINE-READABLE FORM.
A markdown table is parseable. A Pd `#A set` line is parseable. Nobody was
reading either. This parses both and compares them.

THE CHECKS

  pd-text     a markdown table must equal the contents of a `text define` in a
              patch. Anchored by an HTML comment, which does not render:

                  <!-- check: pd-text "Cut It/m_404.pd" $0-pad -->

                  | Pad | Note | Evidence | Item |
                  |-----|------|----------|------|
                  | 1   | 48   | verified | 190  |

              The table's first N columns are compared against the N atoms on
              each line of the text; later columns are documentation and are
              ignored. Reintroduce `47 + n` and this goes red AT PAD 5 and stays
              green on pads 1-4 -- the exact shape that let that bug survive in
              this repo's own docs for months.

  no-dangling-doc
              every `*.md` named anywhere in the repo -- including inside `.pd`
              comments and `tools/` scripts -- must exist. `plan-tests.md` is
              named from eight files that are NOT documentation, and it is being
              dissolved; without this check every one of them rots in silence.

  shape       every page in `ref/` declares a schema on line 1 and keeps to it.
              The cheapest checks here, because a heading structure is already a
              parse tree -- and the two that matter most are the ones that make
              a DECISION PERMANENT rather than a one-time sweep:

                no ⬜ outside an `Open` section, so open work keeps exactly one
                home. Three documents pointed at `plan-v03.md` §4 for months
                while that section did not exist.

                no ✅ in any heading. An evidence marker never rots; a
                COMPLETION marker silently becomes false. `ref-conventions.md`
                asserted `u_map` used no lookup table right up until Phase 9
                contradicted it.

              Scoped to `ref/` only. The root documents predate all of this and
              are dissolved rather than corrected.

⛔ A CHECK THAT CANNOT FIND WHAT IT IS CHECKING MUST FAIL, NOT PASS. An anchor
naming a table that is not there, or an array that is not in the patch, is a
FAILURE here. `phase6-assert.sh` asserted only that its rewrite count was
non-zero and its own comment drifted from five boxes to six with nothing
noticing; a gate that passes vacuously is worse than no gate, because it is
BELIEVED. Every lookup below raises rather than returning empty.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

ANCHOR = re.compile(r'<!--\s*check:\s*(.+?)\s*-->')
SPEC = re.compile(r'^pd-text\s+"([^"]+)"\s+(\S+)$')
# Only names that look like this project's own docs. A bare "README.md" inside a
# URL or a shell heredoc is not worth a false positive.
DOCNAME = re.compile(r'(?<![\w/.-])((?:[a-z0-9_-]+/)?[a-zA-Z0-9_-]+\.md)\b')
# A markdown link target. The angle-bracket form carries paths containing
# spaces -- `[README.md](<! v0.1 plans/README.md>)` -- which this repo uses.
MDLINK = re.compile(r'\]\(<?([^)>#]+\.md)(?:#[^)>]*)?>?\)')

TEXT_SUFFIXES = ('.md', '.pd', '.sh', '.py', '.txt')
SKIP_DIRS = {'.git', '__pycache__', 'device-state', 'node_modules'}


class CheckFailed(Exception):
    """A check could not be completed. Always a failure, never a skip."""


# --- parsing ---------------------------------------------------------------

def md_table(lines, start):
    """Rows of the first markdown table at or after `start`, as lists of cells.

    The header and its `|---|` separator are dropped. Stops at the first line
    that is not a table row, so two tables under one anchor never merge.
    """
    i = start
    while i < len(lines) and not lines[i].lstrip().startswith('|'):
        if lines[i].strip() and not lines[i].lstrip().startswith('<!--'):
            break                      # prose intervened -- the anchor is orphaned
        i += 1
    rows = []
    while i < len(lines) and lines[i].lstrip().startswith('|'):
        cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
        if not all(set(c) <= set('-: ') for c in cells):     # the separator row
            rows.append(cells)
        i += 1
    if len(rows) < 2:
        raise CheckFailed('no markdown table follows the anchor')
    return rows[1:]                    # drop the header


def pd_text(path, name):
    """The lines of a `text define <name>`, as lists of atoms.

    Pd saves the contents as a `#A set` record on the line after the object,
    with `\\;` between lines and a bare `;` closing the record.
    """
    src = (ROOT / path)
    if not src.exists():
        raise CheckFailed(f'{path} does not exist')
    lines = src.read_text(encoding='utf-8').splitlines()
    want = re.compile(r'^#X obj \d+ \d+ text define .*' + re.escape(name) + r';$')
    for i, ln in enumerate(lines):
        if want.match(ln):
            for data in lines[i + 1:]:
                if data.startswith('#A set '):
                    body = data[len('#A set '):].rstrip()
                    if body.endswith(';'):
                        body = body[:-1]
                    return [chunk.split() for chunk in body.split(r'\;') if chunk.split()]
                if data.startswith('#X '):
                    break              # the next object -- this define has no data
            raise CheckFailed(f'[text define {name}] in {path} holds no #A data')
    raise CheckFailed(f'no [text define {name}] in {path}')


# --- the checks ------------------------------------------------------------

def check_pd_text(doc, lineno, rows, path, name):
    """Compare a table against a patch's text array, row by row."""
    have = pd_text(path, name)
    arity = len(have[0])
    by_key = {tuple(r[:1]): r for r in have}
    problems = []
    for cells in rows:
        key = tuple(cells[:1])
        want = [c for c in cells[:arity]]
        got = by_key.get(key)
        if got is None:
            problems.append(f'{want[0]}: in the table, absent from [{name}]')
        elif got[:arity] != want:
            problems.append(f'{want[0]}: doc says {" ".join(want[1:])}, '
                            f'patch says {" ".join(got[1:arity])}')
    table_keys = {tuple(r[:1]) for r in rows}
    for key in by_key:
        if key not in table_keys:
            problems.append(f'{key[0]}: in [{name}], absent from the table')
    if problems:
        head = f'{doc}:{lineno}  table vs [text define {name}] in {path}'
        return [head] + [f'    {p}' for p in problems]
    return []


def check_anchors(verbose):
    """Every `<!-- check: ... -->` anchor in every markdown file."""
    out, seen = [], 0
    for doc in sorted(ROOT.rglob('*.md')):
        if any(p in SKIP_DIRS for p in doc.relative_to(ROOT).parts):
            continue
        lines = doc.read_text(encoding='utf-8').splitlines()
        fenced = False
        for i, ln in enumerate(lines):
            if ln.lstrip().startswith(('```', '~~~')):
                fenced = not fenced
                continue
            # ⛔ An anchor inside a fence is an EXAMPLE of the syntax, not a check.
            # plan-v03.md documents this gate and contains one; reading it as live
            # made the gate fail on its own documentation.
            if fenced:
                continue
            m = ANCHOR.search(ln)
            if not m:
                continue
            seen += 1
            rel = doc.relative_to(ROOT)
            spec = SPEC.match(m.group(1))
            if not spec:
                out.append(f'{rel}:{i + 1}  unreadable check spec: {m.group(1)}')
                continue
            try:
                rows = md_table(lines, i + 1)
                out += check_pd_text(rel, i + 1, rows, spec.group(1), spec.group(2))
            except CheckFailed as e:
                out.append(f'{rel}:{i + 1}  {e}')
    if not seen:
        out.append('no <!-- check: --> anchors found anywhere -- this gate is '
                   'asserting nothing at all')
    elif verbose:
        print(f'  {seen} anchored table(s) checked')
    return out


def check_dangling_docs(verbose):
    """Every pointer to a *.md must resolve. What counts as a pointer differs by
    file type, and the distinction is the whole reason this check is usable:

      .md            only a markdown LINK, `](target)`. A bare mention is prose,
                     and prose legitimately names files that no longer exist.
                     Two files say the v0.2 plan "was dissolved when the last
                     phase landed" -- accurate history, not a broken pointer.
      .pd .sh .py    EVERY name mentioned. There is no link syntax in a Pd
                     comment, so a bare name IS the pointer, and no comment has
                     a narrative reason to name a document that is gone.

    ⛔ That second rule is the one that matters. `plan-tests.md` is named from
    eight files that are not documentation and is being dissolved; without this
    they would each keep pointing at nothing, in silence.
    """
    out, seen = [], 0
    known = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*.md')}
    basenames = {pathlib.PurePath(n).name for n in known}
    for src in sorted(ROOT.rglob('*')):
        if not src.is_file() or src.suffix not in TEXT_SUFFIXES:
            continue
        if any(p in SKIP_DIRS for p in src.relative_to(ROOT).parts):
            continue
        try:
            body = src.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        if src.suffix == '.md':
            names = set(MDLINK.findall(body))
        else:
            names = set(DOCNAME.findall(body))
        for name in sorted(names):
            seen += 1
            if (ROOT / name).exists() or (src.parent / name).exists():
                continue
            if pathlib.PurePath(name).name in basenames:
                continue     # quoted from another directory -- resolves in the tree
            out.append(f'{src.relative_to(ROOT)}  points at {name}, which does not exist')
    if verbose:
        print(f'  {seen} document pointer(s) resolved')
    return out


# What it is / Facts / Traps are about the DEVICE. Design is about us -- how Cut
# It chooses to use it and why -- which is neither a measured fact nor something
# that will bite you, and had no home until two pages in a row needed one.
MODULE_SKELETON = ['What it is', 'Facts', 'Traps', 'Design', 'Open']
SCHEMAS = ('module', 'rules', 'freeform')
SCHEMA_LINE = re.compile(r'^<!--\s*schema:\s*(\w+)\s*-->\s*$')
PATHS = re.compile(r'`([^`]+)`')


def _strip_fences(lines):
    """(line, is_fenced) for every line, so a ## inside a code block is not a heading."""
    fenced, out = False, []
    for ln in lines:
        if ln.lstrip().startswith(('```', '~~~')):
            fenced = not fenced
            out.append((ln, True))
            continue
        out.append((ln, fenced))
    return out


def check_shape(verbose):
    """Every page in ref/ declares a schema and keeps to it."""
    out, pages = [], 0
    refdir = ROOT / 'ref'
    if not refdir.is_dir():
        return out

    # The parking spot for material that does not fit any schema. It explains
    # itself in an HTML comment, so the emptiness test ignores those -- anything
    # a person actually parks there is real content and trips the check.
    unfiled = refdir / '_unfiled.md'
    if unfiled.exists():
        body = re.sub(r'<!--.*?-->', '', unfiled.read_text(encoding='utf-8'), flags=re.S)
        if body.strip():
            out.append('ref/_unfiled.md is not empty -- material is parked there awaiting '
                       'a shape decision, so the refactor is not done. Propose a shape for '
                       'it and ask; do not cram it into the nearest section')

    for doc in sorted(refdir.glob('*.md')):
        if doc.name == '_unfiled.md':
            continue
        pages += 1
        rel = doc.relative_to(ROOT)
        lines = doc.read_text(encoding='utf-8').splitlines()
        marked = _strip_fences(lines)

        m = SCHEMA_LINE.match(lines[0]) if lines else None
        if not m:
            out.append(f'{rel}:1  no <!-- schema: ... --> on line 1')
            continue
        schema = m.group(1)
        if schema not in SCHEMAS:
            out.append(f'{rel}:1  unknown schema "{schema}" -- expected one of '
                       f'{", ".join(SCHEMAS)}')
            continue

        # ⛔ A completion marker silently becomes false; an evidence marker never does.
        for i, (ln, fenced) in enumerate(marked):
            if not fenced and ln.startswith('#') and '✅' in ln:
                out.append(f'{rel}:{i + 1}  ✅ in a heading. It reads as "built", which rots. '
                           f'Evidence belongs in an Evidence column or in prose')

        if schema != 'module':
            continue

        heads = [(i, ln[3:].strip()) for i, (ln, f) in enumerate(marked)
                 if not f and ln.startswith('## ')]
        if [h for _, h in heads] != MODULE_SKELETON:
            out.append(f'{rel}  schema:module wants exactly {MODULE_SKELETON}, '
                       f'found {[h for _, h in heads]}')
            continue

        # Files: and Gate: must name paths that exist, so a page cannot outlive
        # the abstraction it documents.
        decl = next((ln for ln, f in marked[:6] if not f and '**Files:**' in ln), None)
        if decl is None:
            out.append(f'{rel}  no **Files:** line in the first six lines')
        else:
            for p in PATHS.findall(decl):
                if p != 'none' and not (ROOT / p).exists():
                    out.append(f'{rel}  **Files:**/**Gate:** names {p}, which does not exist')

        bounds = {h: heads[n][0] for n, (_, h) in enumerate(heads)}
        ends = {h: (heads[n + 1][0] if n + 1 < len(heads) else len(marked))
                for n, (_, h) in enumerate(heads)}

        facts = [(i, ln) for i, (ln, f) in enumerate(marked)
                 if not f and bounds['Facts'] < i < ends['Facts']]
        # A header is a row whose NEXT line is the |---| separator.
        # ⛔ The separator test must require a dash. `set('') <= set('-:| ')` is
        # True, so a blank line after a table's LAST row read as a separator and
        # every table reported its final row as a header.
        def _is_sep(s):
            s = s.strip()
            return '-' in s and set(s.strip('|')) <= set('-:| ')

        headers = [ln for i, ln in facts
                   if ln.lstrip().startswith('|')
                   and i + 1 < len(marked)
                   and _is_sep(marked[i + 1][0])]
        if not headers:
            out.append(f'{rel}  the Facts section holds no table -- facts stated only '
                       f'in prose cannot be checked against anything')
        for h in headers:
            cells = [c.strip() for c in h.strip().strip('|').split('|')]
            missing = [c for c in ('Evidence', 'Item') if c not in cells]
            if missing:
                out.append(f'{rel}  a Facts table is missing the {" and ".join(missing)} '
                           f'column(s): {h.strip()[:60]}')

        for i, (ln, f) in enumerate(marked):
            if f or '⬜' not in ln:
                continue
            if not (bounds['Open'] < i < ends['Open']):
                out.append(f'{rel}:{i + 1}  ⬜ outside the Open section. Uncertainty is '
                           f'recorded here; what to DO about it lives in plan-v03 §4')
            elif 'plan-v03.md' not in ln and not any(
                    'plan-v03.md' in marked[j][0] for j in range(i, min(i + 4, ends['Open']))):
                out.append(f'{rel}:{i + 1}  ⬜ in Open with no link to plan-v03.md')

    if verbose and pages:
        print(f'  {pages} ref/ page(s) matched their schema')
    return out


RULE_ID = re.compile(r'(?<![\w-])(C-\d+)(?![\w-])')


def check_rule_ids(verbose):
    """Every C-NN cited anywhere must be a rule that exists.

    ⛔ This is what makes a `.pd` comment able to cite the conventions at all. A
    comment is the only documentation visible while editing in Pd and it has no
    link syntax, so the citation is a bare ID -- and a bare ID that resolves to
    nothing is exactly the rot this gate exists to stop.
    """
    out = []
    src = ROOT / 'ref' / 'conventions.md'
    if not src.exists():
        return out
    defined = set(RULE_ID.findall(src.read_text(encoding='utf-8')))
    if not defined:
        return ['ref/conventions.md defines no C-NN rules, so every citation is dangling']
    cited = 0
    for f in sorted(ROOT.rglob('*')):
        if not f.is_file() or f.suffix not in TEXT_SUFFIXES:
            continue
        if any(p in SKIP_DIRS for p in f.relative_to(ROOT).parts):
            continue
        try:
            body = f.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for rid in sorted(set(RULE_ID.findall(body))):
            cited += 1
            if rid not in defined:
                out.append(f'{f.relative_to(ROOT)}  cites {rid}, which is not a rule '
                           f'in ref/conventions.md')
    if verbose:
        print(f'  {len(defined)} rule(s) defined, {cited} citation(s) resolved')
    return out


def main():
    verbose = '-v' in sys.argv
    problems = (check_anchors(verbose) + check_dangling_docs(verbose)
                + check_shape(verbose) + check_rule_ids(verbose))
    if problems:
        print('\n'.join(problems))
        print(f'\n{len(problems)} problem(s).')
        return 1
    if verbose:
        print('docs-check: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
