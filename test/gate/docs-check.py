#!/usr/bin/env python3
"""The documentation gate. No Pd, no device, ~200 ms.

    python3 test/gate/docs-check.py           check, exit non-zero on any failure
    python3 test/gate/docs-check.py -v        and list every check that passed

Where a fact exists twice in machine-readable form -- a markdown table and a
patch's `text define`, `route` box or wire.sh's aconnect lines -- it parses both
and compares them. It resolves every pointer the repo makes: *.md names, script
and patch paths, C-NN rule IDs, `cut-it/<slug>` refs and Reference pages. And it
holds each ref/ page to its schema and each ⬜ to an Open section and an owner.
The anchor syntax and the schemas are the `docs` skill's. A ⬜ must sit in an
`Open` section, so open work keeps exactly one home: three documents pointed at
`plan-v04.md` §4 for months while that section did not exist.

A check that cannot find what it is checking fails: an anchor naming a table or
an array that is not there is a failure, so every lookup raises rather than
returning empty.
"""
import pathlib
import pwd
import os
import re
import sys

import lib_pd

# Asserted: every check globs from here, and a root one level off would find
# nothing and pass.
ROOT = pathlib.Path(__file__).resolve().parents[2]
if not (ROOT / 'AGENTS.md').exists():
    sys.exit(f'docs-check: {ROOT} is not the repo root -- has this file moved? '
             'Every check globs from there and would silently find nothing.')

ANCHOR = re.compile(r'<!--\s*check:\s*(.+?)\s*-->')
SPEC = re.compile(r'^(pd-text|pd-route|sh-aconnect)\s+"([^"]+)"\s+(\S+)$')
# Only names that look like this project's own docs. A bare "README.md" inside a
# URL or a shell heredoc is not worth a false positive.
# ⛔ THE NAME CLASS CARRIES DOTS, and it did not until 2026-08-12. Without one a
# bare three-part plan name in a .pd, .sh or .py was invisible to
# check_dangling_docs while a bare `plan-v04.md` was caught: the match started at
# the `plan-vNN` part, needed `.md` next, failed -- and every later start position
# was refused by the lookbehind, which sees the dot inside the version.
# That plan is deleted and this check reads this file too, so its name is not
# spelled out here.
# The directory group repeats, so a two-level path (ref/module/*.md) is matched.
DOCNAME = re.compile(r'(?<![\w/.!-])((?:[a-z0-9_-]+/)*[a-zA-Z0-9_.-]+\.md)\b')
# A markdown link target, including the angle-bracket form for paths with spaces.
MDLINK = re.compile(r'\]\(<?([^)>#]+\.md)(?:#[^)>]*)?>?\)')

TEXT_SUFFIXES = ('.md', '.pd', '.sh', '.py', '.txt')
# The plans (two folders, and plan-v04.md until Brendan's move of it lands) are
# archives he is converting into !projects by hand (2026-11-02), and they go when
# he's done: their names for retired files are history. Matched by name, as a
# directory or a file.
SKIP_DIRS = {'.git', '__pycache__', 'device-state', 'node_modules',
             '! v0.1 plans', '! v0.2 plans', 'plan-v04.md'}

# Open work lives in !projects and Reference pages in !reference, both in
# ~/Sites beside this repo. A missing directory fails the check rather than
# finding nothing. From a worktree elsewhere the repo's parent is not ~/Sites,
# so fall back to the account's home from the password database, not $HOME:
# test/runner/gates.py runs every gate with HOME pointed at an empty directory.
SITES = (ROOT.parent if (ROOT.parent / '!projects').is_dir()
         else pathlib.Path(pwd.getpwuid(os.getuid()).pw_dir) / 'Sites')
PROJECTS = SITES / '!projects' / 'cut-it'
PROJ_REF = re.compile(r'(?<![\w/.-])cut-it/([a-z0-9-]+)(?:#[a-z0-9-]+)?\b')

REFERENCE = SITES / '!reference'
REF_PAGE = re.compile(r'!reference/([a-z0-9-]+)\.md')


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
    lines = lib_pd.read(src)
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
    """The arguments of a `route` box, identified by its first argument
    rather than by position, since box indices move (C-10)."""
    src = (ROOT / path)
    if not src.exists():
        raise CheckFailed(f'{path} does not exist')
    want = re.compile(r'^#X obj -?\d+ -?\d+ route ('
                      + re.escape(first) + r'(?: [^;]*)?);$')
    found = [m.group(1).split()
             for m in (want.match(ln) for ln in lib_pd.read(src))
             if m]
    if not found:
        raise CheckFailed(f'no [route {first} ...] in {path}')
    if len(found) > 1:
        raise CheckFailed(f'{len(found)} [route {first} ...] boxes in {path} '
                          f'-- the anchor cannot say which')
    return found[0]


def sh_aconnect(path, which):
    """The `aconnect` calls in a shell script, as (source, destination) pairs.

    `which` is `connect` or `disconnect`, kept apart because they mean
    opposite things: the connects are the rig, the disconnects undo mother's
    autoconnect. Lumped together, they would pass with the rig unwired.
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

    The allowlist guard from the other side: map-assert.py proves every map
    row names a destination on the route, and this proves the documented set is
    the same set.
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
    """Compare a table's first two columns against a script's `aconnect` calls."""
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
            # `index` is verified by check_index, not here.
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
    file type:

      .md            only a markdown LINK, `](target)`. A bare mention is prose,
                     and prose legitimately names files that no longer exist.
      .pd .sh .py    every name mentioned. A comment has no link syntax, so a
                     bare name is the pointer.
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


# What each section holds is the `docs` skill's.
MODULE_SKELETON = ['What it is', 'Facts', 'Traps', 'Design', 'Open']
# A device page is only how Cut It uses the device (Brendan, 2026-11-02); the
# rest is on its Reference page.
DEVICE_SKELETON = ['Design', 'Open']
SKELETONS = {'module': MODULE_SKELETON, 'device': DEVICE_SKELETON}
# The directory is the kind, so it names the schema a page in it must declare.
DIR_SCHEMA = {'module': 'module', 'device': 'device'}
SCHEMAS = ('module', 'device', 'rules', 'freeform')
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

    # rglob, not glob, or the subdirectories' pages go unseen; the -v count is
    # the guard.
    for doc in sorted(refdir.rglob('*.md')):
        if doc.name == '_unfiled.md':
            continue
        pages += 1
        rel = doc.relative_to(ROOT)
        # the directory IS the kind, so it can be asserted
        want = DIR_SCHEMA.get(doc.parent.name)
        if want:
            first = doc.read_text(encoding='utf-8').split('\n', 1)[0]
            if f'schema: {want}' not in first:
                out.append(f'{rel}  lives in {doc.parent.name}/ but is not '
                           f'schema:{want}. That directory holds {want} pages only')
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

        # A completion marker silently becomes false; an evidence marker never does.
        for i, (ln, fenced) in enumerate(marked):
            if not fenced and ln.startswith('#') and '✅' in ln:
                out.append(f'{rel}:{i + 1}  ✅ in a heading. It reads as "built", which rots. '
                           f'Evidence belongs in an Evidence column or in prose')

        # Every schema, not just module. A freeform page has no skeleton, so the
        # rule is by section: a page with any ⬜ has a ## Open holding all of them.
        out += _check_open_items(rel, marked)

        skeleton = SKELETONS.get(schema)
        if skeleton is None:
            continue

        heads = [(i, ln[3:].strip()) for i, (ln, f) in enumerate(marked)
                 if not f and ln.startswith('## ')]
        if [h for _, h in heads] != skeleton:
            out.append(f'{rel}  schema:{schema} wants exactly {skeleton}, '
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
            # A gate and a bench are different oracles, so a page declares both;
            # `none` is an answer to either.
            for field in ('**Gate:**', '**Bench:**'):
                if field not in decl:
                    out.append(f'{rel}  the **Files:** line declares no {field} '
                               f'-- say `none` if there is not one')

        # A device page has no Facts section.
        if schema != 'module':
            continue

        bounds = {h: heads[n][0] for n, (_, h) in enumerate(heads)}
        ends = {h: (heads[n + 1][0] if n + 1 < len(heads) else len(marked))
                for n, (_, h) in enumerate(heads)}

        facts = [(i, ln) for i, (ln, f) in enumerate(marked)
                 if not f and bounds['Facts'] < i < ends['Facts']]
        # A header is a row whose NEXT line is the |---| separator.
        # The separator must contain a dash: set('') <= set('-:| ') is True, so
        # a blank line after the last row would read as one.
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
        # Evidence only: item numbers are frozen (Brendan, 2026-11-02), so an
        # Item column is optional.
        for h in headers:
            cells = [c.strip() for c in h.strip().strip('|').split('|')]
            if 'Evidence' not in cells:
                out.append(f'{rel}  a Facts table is missing the Evidence '
                           f'column: {h.strip()[:60]}')

    if verbose and pages:
        print(f'  {pages} ref/ page(s) matched their schema')
    return out


def _is_marker_gloss(line):
    """A ⬜ that is defining the glyph rather than using it: a two-cell table
    row whose first cell is the bare glyph, like the marker tables in AGENTS.md
    and the `docs` skill. By structure, so rewording those rows cannot break it.

        | ⬜ | Unknown or unverified |     <- a definition, not an open item
        | 45 | ⬜ AP link quality    |     <- an open item in a table cell
    """
    if not line.lstrip().startswith('|'):
        return False
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    return len(cells) == 2 and cells[0] == '⬜'


# Whatever a line opens with before its content: list bullets, heading hashes,
# an ordered-list number, a table cell wall.
_ORNAMENT = '-*#0123456789. |'


def is_open_item(line, in_open=False):
    """A ⬜ that is an open item, rather than prose about the marker: an open
    item leads with the glyph, prose names it mid-sentence.

        ⬜ **Why nothing answers a DISCOVER after a roam.**   <- an open item
        - ⬜ Whether the dongle's draw contributes                <- an open item
        ### ⬜ Nothing measures the OUTPUT side                 <- an open item
        | 45 | ⬜ AP link quality |                             <- an open item
        so read that checklist before adding a ⬜ anywhere.    <- prose

    Measured on 2026-08-12: of 42 non-gloss marks, all seven that did not lead
    with the glyph were prose about the marker. Inside an `## Open` section
    (`in_open`) the lead test is dropped, so an item written mid-sentence is
    still caught where items are written.
    """
    if '⬜' not in line or _is_marker_gloss(line):
        return False
    if in_open:
        return True
    return line.lstrip().lstrip(_ORNAMENT).lstrip().startswith('⬜')


def open_span(marked):
    """(first, last) line indices of the `## Open` section, or None. Shared so
    `_check_open_items` and `check_closers` agree on what is inside one."""
    start = next((i for i, (ln, f) in enumerate(marked)
                  if not f and ln.strip() == '## Open'), None)
    if start is None:
        return None
    end = next((i for i, (ln, f) in enumerate(marked[start + 1:], start=start + 1)
                if not f and ln.startswith('## ')), len(marked))
    return start, end


# An owner is a plan file, a `!projects` ref (see PROJ_REF), or the literal
# escape hatch. The ref is resolved by check_project_refs; here it only has
# to be named.
OWNER = re.compile(r'\bplan-v[0-9.]+\.md|\bcut-it/[a-z0-9-]+|\bNO PLAN OWNS THIS\b')


def _check_open_items(rel, marked):
    """Every ⬜ must sit under a `## Open` and NAME AN OWNER, whatever the schema.

    ⚠️ Stated in terms of the SECTION, not the module skeleton, because a
    freeform page has no enforced skeleton to hang it off. A page with no ⬜
    needs no Open section at all.

    ⛔ THE OWNER USED TO BE HARD-CODED TO plan-v04.md, AND THAT PUSHED CONTENT
    BACK INTO PLANS THAT DID NOT WANT IT. When plan-v04 was the only standing
    plan the two were the same thing. They are not any more: a scoped plan can
    own an item, and a `ref/` page can own its own follow-up -- ref/wifi.md
    carries an `If it recurs` section that says what to try and when to stop,
    which is a better home for it than a plan that gets deleted. Requiring the
    plan-v04 link forced a wifi section to exist in plan-v04.md purely to be
    linked at, which is duplication the rest of this gate exists to prevent.

    ⛔ SO AN OWNER IS EITHER A plan-*.md LINK OR THE LITERAL `NO PLAN OWNS THIS`.
    The escape hatch is deliberately loud and greppable rather than silent: an
    item nobody owns is a real state -- a recorded unknown with nothing queued --
    and the honest way to record it is to say so where it can be found, not to
    point at a plan as a dumping ground. `grep -rn "NO PLAN OWNS THIS"` is the
    inventory.
    """
    out = []
    span = open_span(marked)
    marks = [i for i, (ln, f) in enumerate(marked)
             if not f and is_open_item(ln, span is not None and span[0] < i < span[1])]
    if not marks:
        return out

    start = span[0] if span else None
    if start is None:
        out.append(f'{rel}  has {len(marks)} ⬜ but no "## Open" section. An open '
                   f'item outside Open is invisible -- that is how ref/device-os.md '
                   f'came to carry five of them')
        return out
    end = span[1]

    for i in marks:
        if not (start < i < end):
            out.append(f'{rel}:{i + 1}  ⬜ outside the Open section. Uncertainty is '
                       f'recorded there; what to DO about it lives with its owner')
        elif not any(OWNER.search(marked[j][0])
                     for j in range(i, min(i + 4, end))):
            out.append(f'{rel}:{i + 1}  ⬜ in Open names no owner -- link the '
                       f'plan-*.md or cut-it/<slug> that closes it, or say NO PLAN OWNS THIS')
    return out


RULE_ID = re.compile(r'(?<![\w-])(C-\d+)(?![\w-])')


def check_index(verbose):
    """ref/README.md's index must list exactly the pages that exist."""
    out = []
    readme = ROOT / 'ref' / 'README.md'
    refdir = ROOT / 'ref'
    if not readme.exists():
        return out
    body = readme.read_text(encoding='utf-8')
    if '<!-- check: index -->' not in body:
        return ['ref/README.md has no <!-- check: index --> anchor, so its index '
                'is not being verified against what exists']
    # [A-Za-z]: the index lists `README`.
    listed = set(re.findall(r'`([A-Za-z0-9_-]+)`', body[body.index('<!-- check: index -->'):]
                            .split('## The page schema')[0]))
    for sub in ('device', 'module'):
        actual = {f.stem for f in (refdir / sub).glob('*.md')} if (refdir / sub).is_dir() else set()
        for name in sorted(actual - listed):
            out.append(f'ref/{sub}/{name}.md exists but ref/README.md\'s index does not list it')
    # And the top level, whose pages are the rarest and the easiest to forget.
    top = {f.stem for f in refdir.glob('*.md')} - {'_unfiled'}
    for name in sorted(top - listed):
        out.append(f'ref/{name}.md exists but ref/README.md\'s index does not list it')
    if verbose and not out:
        print('  the ref/ index matches what exists')
    return out


SKILLS = '.claude/skills'
# Every directory the project keeps code in must be listed: a path in one that
# is not is invisible, not unchecked. The -v count should only go up.
DIRS = ('tools/', 'test/', 'Cut It/', 'Cut It Debug/', 'device/', 'mac-stubs/',
        r'\.claude/')
PATHREF = re.compile(
    r'(?<![\w.-])\.?/?((?:' + '|'.join(DIRS) + r')[\w /.-]*?'
    r'\.(?:sh|py|pd|txt))(?![\w.-])')


def check_dangling_paths(verbose):
    """Scripts and patches named anywhere must exist, in every file type
    including .md: naming a script is nearly always an instruction to run or
    read it, and in a skill always. A name with a capital letter in it
    (phaseN-bench.pd) is a pattern, not a reference, and is skipped.
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

    The skill carries a copy because a loaded skill cannot follow a link; this
    keeps the copy from drifting. Compares the ID set and the rule text,
    ignoring emphasis and the link column only the doc has.
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
    """Every C-NN cited anywhere must be a rule that exists. A Pd comment
    cites the conventions by bare ID, having no link syntax."""
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


# ⛔ A CLOSER IS AN OWNER OR A VERSION, and the owner half is OWNER itself rather
# than a second copy of the same idea. This used to be `plan-v0[34](?:\.\d)?\.md`
# -- one decimal group, so it matched plan-v04.md but not a three-part name like
# the v0.3.5 batch's, and every item citing one of those failed a check that was
# meant to reward them. ⚠️ THAT SENTENCE USED TO NAME THE TWO FILES and it is
# written this way on purpose: they are deleted now, and with DOCNAME widened
# below a bare mention here is a dangling pointer this gate reports against
# itself. Sharing OWNER also means `NO PLAN OWNS THIS` counts here,
# which it must: _check_open_items documents that escape hatch as a legitimate
# answer, and a closer check that rejected it would make the hatch unusable and
# push three honestly-parked items into a plan as a dumping ground.
CLOSER = re.compile(OWNER.pattern + r'|\bv0\.[4-9]\b')


def check_closers(verbose):
    """Every open ⬜ names the plan, the owner or the version that closes it.

    So an open item cannot sit in the tree with nobody accountable for it. It ran
    behind --strict for as long as the v0.3.5 batch was in flight, because a large
    minority of items legitimately had no closer until those plans landed and **a
    gate that stays red for two weeks is a gate that gets ignored.** The batch has
    landed, so it runs unconditionally.

    ⛔ A ⬜ INSIDE A plan- FILE IS OWNED BY THAT FILE, and is skipped. A plan is
    the document that says what is open; requiring each of its items to name a
    plan means requiring plan-v04.md to cite plan-v04.md, which is satisfiable
    only by writing something tautological into every entry. The FILE is the
    owner, and deleting it is what closes them -- which is exactly what happened
    to section 3's laptop-free debugging item.

    SCOPE IS EVERY OTHER .md, REPO-WIDE -- not just ref/. Open items live in
    AGENTS.md, tools/README.md and test/README.md too. ⛔ A ⬜ in a .pd or .sh
    comment is deliberately NOT covered: forcing a plan citation into a Pd comment
    is exactly the write-twice trap this batch removed.
    """
    out, checked = [], 0
    for f in sorted(ROOT.rglob('*.md')):
        rel = f.relative_to(ROOT)
        if any(p in SKIP_DIRS for p in rel.parts):
            continue
        if rel.name.startswith('plan-'):
            continue
        try:
            lines = f.read_text(encoding='utf-8').splitlines()
        except UnicodeDecodeError:
            continue
        marked = _strip_fences(lines)
        span = open_span(marked)
        for i, (ln, fenced) in enumerate(marked):
            if fenced or not is_open_item(
                    ln, span is not None and span[0] < i < span[1]):
                continue
            checked += 1
            window = ' '.join(marked[j][0] for j in range(i, min(i + 4, len(marked))))
            if not CLOSER.search(window):
                out.append(f'{rel}:{i + 1}  ⬜ names no plan, owner or version that '
                           f'closes it. Link the plan-*.md or cut-it/<slug>, or say NO PLAN OWNS THIS')
    if verbose:
        print(f'  {checked} open item(s) checked for a closer')
    return out


def check_project_refs(verbose):
    """Every `cut-it/<slug>` named anywhere resolves to a file in `!projects`.

    Same walk and same rule as check_dangling_docs: in a .pd, .sh or .py a bare
    mention IS the pointer, and in .md too, since the ref form has no link
    syntax of its own. A slug resolves to active/<slug>.md or done/<slug>.md;
    `inbox` is the loosie file, and resolves while that file exists.

    Fails if `!projects` is not there: a ref that could not be looked up did
    not resolve.
    """
    if not PROJECTS.is_dir():
        return [f'{PROJECTS} is not a directory -- the !projects repo must sit '
                f'beside this one for cut-it/<slug> refs to resolve']
    out, seen = [], 0
    for src in sorted(ROOT.rglob('*')):
        if not src.is_file() or src.suffix not in TEXT_SUFFIXES:
            continue
        if any(p in SKIP_DIRS for p in src.relative_to(ROOT).parts):
            continue
        try:
            body = src.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for slug in sorted(set(PROJ_REF.findall(body))):
            seen += 1
            if slug == 'inbox' and (PROJECTS / slug).with_suffix('.md').exists():
                continue
            if any((PROJECTS / d / f'{slug}.md').exists() for d in ('active', 'done')):
                continue
            out.append(f'{src.relative_to(ROOT)}  cites cut-it/{slug}, which is not '
                       f'in {PROJECTS}/active or done')
    if verbose:
        print(f'  {seen} project ref(s) resolved against {PROJECTS.name}/')
    return out


def check_reference_refs(verbose):
    """Every `!reference/<slug>.md` named anywhere is a page that exists.

    Same walk as check_project_refs, and it fails the same way when the
    directory isn't there: a pointer that could not be looked up did not resolve.
    """
    if not REFERENCE.is_dir():
        return [f'{REFERENCE} is not a directory -- the !reference folder must sit '
                f'beside this repo for its pages to resolve']
    out, seen = [], 0
    for src in sorted(ROOT.rglob('*')):
        if not src.is_file() or src.suffix not in TEXT_SUFFIXES:
            continue
        if any(p in SKIP_DIRS for p in src.relative_to(ROOT).parts):
            continue
        try:
            body = src.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for slug in sorted(set(REF_PAGE.findall(body))):
            seen += 1
            if not (REFERENCE / f'{slug}.md').exists():
                out.append(f'{src.relative_to(ROOT)}  points at !reference/{slug}.md, '
                           f'which is not a Reference page')
    if verbose:
        print(f'  {seen} Reference page(s) resolved')
    return out


def main():
    verbose = '-v' in sys.argv
    problems = (check_anchors(verbose) + check_dangling_docs(verbose)
                + check_shape(verbose) + check_index(verbose)
                + check_rule_ids(verbose) + check_skill_rules(verbose)
                + check_dangling_paths(verbose) + check_closers(verbose)
                + check_project_refs(verbose) + check_reference_refs(verbose))
    if problems:
        print('\n'.join(problems))
        print(f'\n{len(problems)} problem(s).')
        return 1
    if verbose:
        print('docs-check: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
