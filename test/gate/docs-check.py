#!/usr/bin/env python3
"""The documentation gate. No Pd, no device, ~200 ms.

    python3 test/gate/docs-check.py           check, exit non-zero on any failure
    python3 test/gate/docs-check.py -v        and list every check that passed

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
              comments and `tools/` scripts -- must exist. Both journals were
              named from eight files that are NOT documentation and both have
              since been deleted; without this check every one of those
              references rots in silence.

  shape       every page in `ref/` declares a schema on line 1 and keeps to it.
              The cheapest checks here, because a heading structure is already a
              parse tree -- and the two that matter most are the ones that make
              a DECISION PERMANENT rather than a one-time sweep:

                no ⬜ outside an `Open` section, so open work keeps exactly one
                home. Three documents pointed at `plan-v04.md` §4 for months
                while that section did not exist.

                no ✅ in any heading. An evidence marker never rots; a
                COMPLETION marker silently becomes false. The old conventions doc
                asserted `u_map` used no lookup table right up until Phase 9
                contradicted it.

              Scoped to `ref/` only. The root documents predate all of this and
              are dissolved rather than corrected.

⛔ A CHECK THAT CANNOT FIND WHAT IT IS CHECKING MUST FAIL, NOT PASS. An anchor
naming a table that is not there, or an array that is not in the patch, is a
FAILURE here. the old phase 6 gate asserted only that its rewrite count was
non-zero and its own comment drifted from five boxes to six with nothing
noticing; a gate that passes vacuously is worse than no gate, because it is
BELIEVED. Every lookup below raises rather than returning empty.
"""
import pathlib
import re
import sys

# ⛔ THE REPO ROOT, AND IT IS ASSERTED. Every check below globs from here, so a
# ROOT one level off finds nothing, reports nothing and exits ok -- the fourth
# way a gate passes vacuously, and the one this file has already been bitten by
# (globbing ref/*.md stopped seeing seven of nine pages when subdirectories
# appeared, and the run still said ok). Moving this file changes the depth, so
# the depth is checked rather than trusted.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if not (ROOT / 'CLAUDE.md').exists():
    sys.exit(f'docs-check: {ROOT} is not the repo root -- has this file moved? '
             'Every check globs from there and would silently find nothing.')

ANCHOR = re.compile(r'<!--\s*check:\s*(.+?)\s*-->')
SPEC = re.compile(r'^(pd-text|pd-route|sh-aconnect)\s+"([^"]+)"\s+(\S+)$')
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


def pd_route(path, first):
    """The arguments of a `route` box, identified by its FIRST argument.

    Named by its first argument rather than by position, because C-10 makes box
    indices move: appending anything to the patch renumbers nothing here, but a
    check keyed to "the fourth route box" would rot the first time one is added.
    """
    src = (ROOT / path)
    if not src.exists():
        raise CheckFailed(f'{path} does not exist')
    want = re.compile(r'^#X obj -?\d+ -?\d+ route ('
                      + re.escape(first) + r'(?: [^;]*)?);$')
    found = [m.group(1).split()
             for m in (want.match(ln)
                       for ln in src.read_text(encoding='utf-8').splitlines())
             if m]
    if not found:
        raise CheckFailed(f'no [route {first} ...] in {path}')
    if len(found) > 1:
        raise CheckFailed(f'{len(found)} [route {first} ...] boxes in {path} '
                          f'-- the anchor cannot say which')
    return found[0]


def sh_aconnect(path, which):
    """The `aconnect` calls in a shell script, as (source, destination) pairs.

    `which` is `connect` or `disconnect` -- wire.sh does both, and they mean
    opposite things: the connects are the rig, the disconnects UNDO mother's own
    autoconnect. A check that lumped them would pass with the rig unwired.
    """
    if which not in ('connect', 'disconnect'):
        raise CheckFailed(f'sh-aconnect takes connect or disconnect, not {which}')
    src = (ROOT / path)
    if not src.exists():
        raise CheckFailed(f'{path} does not exist')
    flag = r'-d ' if which == 'disconnect' else r''
    want = re.compile(r'^\s*aconnect ' + flag + r'"([^"]+)":(\d+)\s+"([^"]+)":(\d+)')
    found = [(f'{m.group(1)}:{m.group(2)}', f'{m.group(3)}:{m.group(4)}')
             for m in (want.match(ln)
                       for ln in src.read_text(encoding='utf-8').splitlines())
             if m]
    if not found:
        raise CheckFailed(f'no aconnect {which} lines in {path}')
    return found


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


def check_pd_route(doc, lineno, rows, path, first):
    """Compare a table's first column against a `route` box's arguments, in order.

    This is the ALLOWLIST GUARD read from the other side. `map-assert.py`
    proves every row of `cut-it-map.txt` names a destination on the route; this
    proves the DOCUMENTED set is that same set. A destination added to the patch
    and not to the page makes the page quietly incomplete, which nothing else
    would say.
    """
    have = pd_route(path, first)
    want = [r[0].strip().strip('`') for r in rows]
    if want == have:
        return []
    out = [f'{doc}:{lineno}  table vs [route {first} ...] in {path}']
    for d in have:
        if d not in want:
            out.append(f'    {d}: on the route, absent from the table')
    for d in want:
        if d not in have:
            out.append(f'    {d}: in the table, NOT on the route -- a row naming '
                       f'it would go to err as unknown-dest')
    if sorted(want) == sorted(have):
        out.append(f'    same set, different order -- doc has {" ".join(want)}')
    return out


def check_sh_aconnect(doc, lineno, rows, path, which):
    """Compare a table's first two columns against a script's `aconnect` calls.

    The ALSA wiring is restated in wire.sh, main.pd, u_root.pd and here, and it
    is the fact most likely to be edited in one place -- a port number moves the
    whole channel block that the m_ layers test against.
    """
    have = sh_aconnect(path, which)
    want = [(r[0].strip().strip('`'), r[1].strip().strip('`')) for r in rows]
    if want == have:
        return []
    out = [f'{doc}:{lineno}  table vs the aconnect {which} lines in {path}']
    for pair in have:
        if pair not in want:
            out.append(f'    {pair[0]} -> {pair[1]}: in {path}, absent from the table')
    for pair in want:
        if pair not in have:
            out.append(f'    {pair[0]} -> {pair[1]}: in the table, NOT in {path}')
    if sorted(want) == sorted(have):
        out.append('    same set, different order')
    return out


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
            # plan-v04.md documents this gate and contains one; reading it as live
            # made the gate fail on its own documentation.
            if fenced:
                continue
            m = ANCHOR.search(ln)
            if not m:
                continue
            rel = doc.relative_to(ROOT)
            # anchors carry a KIND. `index` is verified by check_index, not here.
            if m.group(1).strip() == 'index':
                continue
            seen += 1
            spec = SPEC.match(m.group(1))
            if not spec:
                out.append(f'{rel}:{i + 1}  unreadable check spec: {m.group(1)}')
                continue
            kind = {'pd-text': check_pd_text, 'pd-route': check_pd_route,
                    'sh-aconnect': check_sh_aconnect}[spec.group(1)]
            try:
                rows = md_table(lines, i + 1)
                out += kind(rel, i + 1, rows, spec.group(2), spec.group(3))
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

    ⛔ That second rule is the one that matters. The two journals were named
    from eight files that are NOT documentation -- u_level.pd, u_net.pd,
    u_root.pd, g_grid.pd, bench-gen.py, fetch-errors.sh, fetch-state.sh,
    display-assert.py -- and both journals have since been deleted. Every one of
    those references was repointed at a bare item number in the same commit.
    Without this check they would have rotted in silence, which is the exact
    failure the whole refactor exists to stop.
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

    # ⛔ rglob, NOT glob. When ref/ gained device/ and module/ subdirectories a
    # plain glob stopped seeing seven of the nine pages, and the run still said
    # "ok" -- coverage vanished with no failure, which is the worst shape a gate
    # can take. The count printed under -v is the guard: watch it go UP.
    for doc in sorted(refdir.rglob('*.md')):
        if doc.name == '_unfiled.md':
            continue
        pages += 1
        rel = doc.relative_to(ROOT)
        # the directory IS the kind, so it can be asserted
        if doc.parent.name in ('device', 'module'):
            first = doc.read_text(encoding='utf-8').split('\n', 1)[0]
            if 'schema: module' not in first:
                out.append(f'{rel}  lives in {doc.parent.name}/ but is not '
                           f'schema:module. Those directories hold module pages only')
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

        # ⛔ EVERY SCHEMA, NOT JUST module. This rule sat inside the module branch
        # below for its whole life, so conventions.md, architecture.md, rig.md and
        # device-os.md were unpoliced -- which is how device-os.md came to carry
        # FIVE live open items with no Open section at all, one of them buried in a
        # table cell. A freeform page has no enforced skeleton, so the rule is
        # stated in terms of the section rather than the skeleton: a page with any
        # ⬜ must have a ## Open, and every ⬜ must be inside it. A page with no ⬜
        # needs no Open.
        out += _check_open_items(rel, marked)

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
                    out.append(f'{rel}  **Files:**/**Gate:**/**Bench:** names {p}, '
                               f'which does not exist')
            # ⛔ A GATE AND A BENCH ARE DIFFERENT ORACLES, so a page must declare
            # both. A gate's verdict comes from a program and runs unattended; a
            # bench's comes from a person's eyes with the rig plugged in. Naming
            # only one leaves the other kind of coverage invisible -- and five
            # pages claimed the old phase 6 gate while nothing said which of them a
            # bench had ever touched. `none` is a legitimate answer to either.
            for field in ('**Gate:**', '**Bench:**'):
                if field not in decl:
                    out.append(f'{rel}  the **Files:** line declares no {field} '
                               f'-- say `none` if there is not one')

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

    if verbose and pages:
        print(f'  {pages} ref/ page(s) matched their schema')
    return out


def _is_marker_gloss(line):
    """A ⬜ that is DEFINING the glyph rather than using it.

    ⛔ Count STRUCTURE, not characters. CLAUDE.md's marker table and the `docs`
    skill's both have a row whose whole job is to say what ⬜ means, and a
    substring blacklist of those exact lines would rot the moment either was
    reworded. The structural fact is what makes them different: a gloss row is a
    two-cell table row whose FIRST cell is the bare glyph and nothing else.

        | ⬜ | Unknown or unverified |     <- a definition, not an open item
        | 45 | ⬜ AP link quality    |     <- an open item in a table cell
    """
    if not line.lstrip().startswith('|'):
        return False
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    return len(cells) == 2 and cells[0] == '⬜'


def _check_open_items(rel, marked):
    """Every ⬜ must sit under a `## Open`, whatever the page's schema.

    ⚠️ Stated in terms of the SECTION, not the module skeleton, because a
    freeform page has no enforced skeleton to hang it off. A page with no ⬜
    needs no Open section at all.
    """
    out = []
    marks = [i for i, (ln, f) in enumerate(marked)
             if not f and '⬜' in ln and not _is_marker_gloss(ln)]
    if not marks:
        return out

    start = next((i for i, (ln, f) in enumerate(marked)
                  if not f and ln.strip() == '## Open'), None)
    if start is None:
        out.append(f'{rel}  has {len(marks)} ⬜ but no "## Open" section. An open '
                   f'item outside Open is invisible -- that is how ref/device-os.md '
                   f'came to carry five of them')
        return out
    end = next((i for i, (ln, f) in enumerate(marked[start + 1:], start=start + 1)
                if not f and ln.startswith('## ')), len(marked))

    for i in marks:
        if not (start < i < end):
            out.append(f'{rel}:{i + 1}  ⬜ outside the Open section. Uncertainty is '
                       f'recorded there; what to DO about it lives in plan-v04 §3')
        elif 'plan-v04.md' not in marked[i][0] and not any(
                'plan-v04.md' in marked[j][0] for j in range(i, min(i + 4, end))):
            out.append(f'{rel}:{i + 1}  ⬜ in Open with no link to plan-v04.md')
    return out


RULE_ID = re.compile(r'(?<![\w-])(C-\d+)(?![\w-])')


def check_index(verbose):
    """ref/README.md's index must list exactly the pages that exist.

    Same two-copies-and-compare idea as everything else here: the index is
    written by hand and would otherwise rot the first time a page is added.
    """
    out = []
    readme = ROOT / 'ref' / 'README.md'
    refdir = ROOT / 'ref'
    if not readme.exists():
        return out
    body = readme.read_text(encoding='utf-8')
    if '<!-- check: index -->' not in body:
        return ['ref/README.md has no <!-- check: index --> anchor, so its index '
                'is not being verified against what exists']
    # ⚠️ [A-Za-z], not [a-z]: the index lists `README` and a lowercase-only class
    # silently failed to see it the moment the top level started being checked.
    listed = set(re.findall(r'`([A-Za-z0-9_-]+)`', body[body.index('<!-- check: index -->'):]
                            .split('## The page schema')[0]))
    for sub in ('device', 'module'):
        actual = {f.stem for f in (refdir / sub).glob('*.md')} if (refdir / sub).is_dir() else set()
        for name in sorted(actual - listed):
            out.append(f'ref/{sub}/{name}.md exists but ref/README.md\'s index does not list it')
    # ⛔ AND THE TOP LEVEL, which this check could not see for its whole life. Only
    # device/ and module/ were compared, so ref/workflow.md and ref/wifi.md were
    # both added and the index still reported "matches what exists" -- the two
    # pages it could not see were exactly the two being added. Cross-cutting pages
    # are the rarest kind and therefore the ones a hand-maintained index forgets.
    top = {f.stem for f in refdir.glob('*.md')} - {'_unfiled'}
    for name in sorted(top - listed):
        out.append(f'ref/{name}.md exists but ref/README.md\'s index does not list it')
    if verbose and not out:
        print('  the ref/ index matches what exists')
    return out


SKILLS = '.claude/skills'
# ⛔ EVERY DIRECTORY THIS PROJECT KEEPS CODE IN HAS TO BE LISTED HERE. A path in a
# directory the regex does not name is not "unchecked" -- it is INVISIBLE, and it
# stays green while it rots. test/ was added when the gates and benches moved out
# of tools/; the count printed at the end of this check is what proves the list is
# still complete, and it must go UP as the repo grows, never down.
DIRS = ('tools/', 'test/', 'Cut It/', 'device/', 'mac-stubs/', r'\.claude/')
PATHREF = re.compile(
    r'(?<![\w.-])\.?/?((?:' + '|'.join(DIRS) + r')[\w /.-]*?'
    r'\.(?:sh|py|pd|txt))(?![\w.-])')


def check_dangling_paths(verbose):
    """Scripts and patches named anywhere must exist.

    ⛔ THE SKILLS ARE THE REASON THIS EXISTS. A skill is procedure -- every path
    in one is an instruction to run or read something -- and the `gate` skill
    names the old phase 6 gate, state-assert.sh and map-assert.py, all of which
    the coming test refactor renames onto a module axis. Without this, three
    skills quietly start instructing people to run files that are gone.

    ⚠️ UNLIKE check_dangling_docs, THIS CHECKS EVERY FILE TYPE INCLUDING .md.
    That rule is looser for documents because prose legitimately names a doc
    that is gone -- "the v0.2 plan was dissolved" is history, not a broken
    pointer. A SCRIPT is different: naming one is nearly always a live
    instruction to run or read it, and a doc describing a renamed tool is
    simply wrong. Measured before widening: including .md cost exactly one
    false positive across the whole repo.

    Renaming test/gate/state-assert.sh goes red in six places -- the conventions,
    tools/README.md, bench-gen.py, run.sh, state-bench.pd and the script
    itself. That is the point: the test refactor renames every gate onto a
    module axis, and this is what makes those renames impossible to half-finish.

    ⚠️ A path containing a capital placeholder -- phaseN-bench.pd -- is a
    pattern, not a reference, and is skipped.
    """
    out, seen = [], 0
    for f in sorted(ROOT.rglob('*')):
        if not f.is_file() or f.suffix not in ('.md', '.pd', '.sh', '.py'):
            continue
        rel = f.relative_to(ROOT)
        if any(p in SKIP_DIRS for p in rel.parts):
            continue
        is_skill = rel.as_posix().startswith(SKILLS)
        try:
            body = f.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        found = set(PATHREF.findall(body))
        for p in sorted(found):
            if re.search(r'[A-Z]', pathlib.PurePath(p).name):
                continue                  # a placeholder like phaseN-bench.pd
            seen += 1
            if not (ROOT / p).exists():
                out.append(f'{rel}  names {p}, which does not exist'
                           + ('  -- a skill instructs, so this is a live pointer'
                              if is_skill else ''))
    if verbose:
        print(f'  {seen} script/patch path(s) resolved')
    return out


def check_skill_rules(verbose):
    """The pd skill's rule table must match ref/conventions.md.

    ⛔ A SKILL THAT RESTATES A DOC IS THE DUPLICATION THIS REFACTOR EXISTS TO
    REMOVE. The skill carries the rule table because a link cannot be followed
    from inside a loaded skill any more than from a Pd comment -- so the copy is
    justified, but only if it cannot drift. Same two-copies-and-compare as the
    pad map: both are markdown tables, so parse both and compare.

    Compares the ID set and the rule text, ignoring emphasis and the trailing
    link column that only the doc has.
    """
    out = []
    skill = ROOT / '.claude' / 'skills' / 'pd' / 'SKILL.md'
    conv = ROOT / 'ref' / 'conventions.md'
    if not skill.exists() or not conv.exists():
        return out

    def rules(path, strip_link):
        found = {}
        for ln in path.read_text(encoding='utf-8').splitlines():
            m = re.match(r'^\|\s*\*{0,2}(C-\d+)\*{0,2}\s*\|(.+)$', ln)
            if not m:
                continue
            body = m.group(2).split('|')
            if strip_link and len(body) > 1:
                body = body[:-2] if body[-1].strip() == '' else body[:-1]
            text = '|'.join(body)
            found[m.group(1)] = re.sub(r'[*`\s]+', ' ', text).strip().strip('|').strip()
        return found

    a, b = rules(skill, False), rules(conv, True)
    for rid in sorted(set(b) - set(a), key=lambda r: int(r[2:])):
        out.append(f'.claude/skills/pd/SKILL.md is missing {rid}, which ref/conventions.md defines')
    for rid in sorted(set(a) - set(b), key=lambda r: int(r[2:])):
        out.append(f'.claude/skills/pd/SKILL.md defines {rid}, which ref/conventions.md does not')
    for rid in sorted(set(a) & set(b), key=lambda r: int(r[2:])):
        if a[rid] != b[rid]:
            out.append(f'{rid} differs between the pd skill and ref/conventions.md:\n'
                       f'    skill: {a[rid][:70]}\n'
                       f'    doc:   {b[rid][:70]}')
    if verbose and not out:
        print(f'  the pd skill\'s {len(a)} rules match ref/conventions.md')
    return out


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


CLOSER = re.compile(r'plan-v0[34](?:\.\d)?\.md|\bv0\.[4-9]\b')


def check_closers(verbose):
    """⬜ --strict ONLY, AND DELIBERATELY NOT WIRED YET.

    Every remaining ⬜ should name the plan or the version that closes it, so an
    open item cannot sit in the tree with nobody owning it. That is the rule this
    whole batch exists to make stick.

    ⛔ IT DOES NOT RUN BY DEFAULT, AND THAT IS THE POINT. The v0.3.5 batch has not
    landed, so a large minority of today's items legitimately have no closer -- and
    **a gate that stays red for two weeks is a gate that gets ignored**, which would
    cost more than the rule buys. Run it with --strict to see the backlog.

    ⚠️ TO LAND IT: delete the flag so main() always calls this, after the LAST of
    the three v0.3.5 plans ships. Its landing checklist says so and names the file.

    ⛔ AND IT IS NOT ONLY A FLAG DELETION, which that checklist spells out. Two
    things here are wrong for the plan names that now exist:

      CLOSER  has ONE decimal group, so it stops one level short and matches none
              of plan-v03.5.0.md / .1.md / .2.md. Every open item citing one of
              the three fails this check as written.
      DOCNAME cannot see those names AT ALL -- its class is [a-zA-Z0-9_-]+ with no
              dot, and the lookbehind rejects the one inside v03.5. So a bare
              plan-v03.5.N.md in a .pd/.sh/.py is invisible to
              check_dangling_docs while a bare plan-v04.md is caught. That is why
              this batch's Pd-comment references had to be found by grep.

    SCOPE IS EVERY .md, REPO-WIDE -- not just ref/. Open items live in CLAUDE.md,
    tools/README.md and test/README.md too. ⛔ A ⬜ in a .pd or .sh comment is
    deliberately NOT covered: forcing a plan citation into a Pd comment is exactly
    the write-twice trap this batch removed.
    """
    out, checked = [], 0
    for f in sorted(ROOT.rglob('*.md')):
        rel = f.relative_to(ROOT)
        if any(p in SKIP_DIRS for p in rel.parts):
            continue
        try:
            lines = f.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError:
            continue
        marked = _strip_fences(lines)
        for i, (ln, fenced) in enumerate(marked):
            if fenced or '⬜' not in ln or _is_marker_gloss(ln):
                continue
            checked += 1
            window = ' '.join(marked[j][0] for j in range(i, min(i + 4, len(marked))))
            if not CLOSER.search(window):
                out.append(f'{rel}:{i + 1}  ⬜ names no plan or version that closes it')
    if verbose:
        print(f'  {checked} open item(s) checked for a closer')
    return out


def main():
    verbose = '-v' in sys.argv
    problems = (check_anchors(verbose) + check_dangling_docs(verbose)
                + check_shape(verbose) + check_index(verbose)
                + check_rule_ids(verbose) + check_skill_rules(verbose)
                + check_dangling_paths(verbose))
    if '--strict' in sys.argv:
        problems += check_closers(verbose)
    if problems:
        print('\n'.join(problems))
        print(f'\n{len(problems)} problem(s).')
        return 1
    if verbose:
        print('docs-check: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
