#!/usr/bin/env python3
"""Cut It's manual as one file, MANUAL.md at the repo's top, read on GitHub (Brendan, 2026-11-11).

The prose is here in manual/, one Markdown file a section, in filename order, each section's title
its first heading. Its tables are made from the files the instrument itself reads, so a control
can't go unlisted: a section names one on a line of its own as {{machines}}, {{factory}},
{{controls}} or {{map}}.

    python3 manual/build.py            writes MANUAL.md
    python3 manual/build.py --check    says whether MANUAL.md is what it would write (exit 1 if not)

test/gate/manual-check.py runs the check, so a change to the prose or to the tables that isn't
built into MANUAL.md fails the gates. Until 2026-11-11 Back Office drew the manual at /cut-it.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUAL = ROOT / 'manual'
PATCH = ROOT / 'Cut It'
OUT = ROOT / 'MANUAL.md'

TITLE = 'Cut It manual'
NOTE = ('<!-- Written by manual/build.py from manual/ and the instrument\'s own tables in Cut It/. '
        'Edit those, then run it. -->')


def rows(name):
    """A table file's rows, each split on spaces, without its # comments and blank lines."""
    path = PATCH / name
    text = path.read_text(encoding='utf-8') if path.exists() else ''
    return [line.split() for line in text.splitlines()
            if line.strip() and not line.strip().startswith('#')]


def grouped(pairs):
    """{first: [second, ...]} in the order the firsts first appear."""
    by = {}
    for first, second in pairs:
        by.setdefault(first, []).append(second)
    return by


MACHINE_NAMES = {
    'fm': 'FM (Volca)',
    'strings': 'strings (Streichfett)',
    'sine': 'sine',
    'saw': 'saw',
    'square': 'square',
}


def machines_table():
    by = grouped((r[0], r[1]) for r in rows('cut-it-machines.txt'))
    lines = ["## Each machine's parameters", '', '| Machine | Parameters |', '|---|---|']
    lines += [f'| {MACHINE_NAMES.get(m, m)} | {", ".join(ps)} |' for m, ps in by.items()]
    return '\n'.join(lines)


def factory_table():
    by = grouped((r[0], r[1]) for r in rows('cut-it-factory.txt'))
    lines = ['## Factory patches', '', '| Machine | Patches |', '|---|---|']
    lines += [f'| {MACHINE_NAMES.get(m, m)} | {", ".join(ns)} |' for m, ns in by.items()]
    return '\n'.join(lines)


HARMONY = {'chord-lock', 'smooth', 'tension', 'home', 'span', 'chords', 'on-h', 'bass', 'style',
           'roll-chords', 'roll-rhythm'}


def part_of(dest, arg):
    if dest == 'melody':
        return 'harmony' if arg in HARMONY else 'melody'
    if dest == 'drums':
        return 'drums'
    return 'master'


def controls_table():
    lines = ['## What can be taken into play', '',
             "Besides these, every parameter of a voice's machine.", '',
             '| Control | Part | Kind |', '|---|---|---|']
    for dest, arg, kind, label in (r[:4] for r in rows('cut-it-controls.txt')):
        lines.append(f'| {label} | {part_of(dest, arg)} | {kind} |')
    return '\n'.join(lines)


TRANSPORT = ['REW', 'PLAY', 'FF', 'LOOP', 'STOP', 'REC']


def control_name(c):
    """A control's name on its surface, from the name the instrument gives it."""
    if m := re.fullmatch(r'og-knob-(\d)', c):
        return f'Organelle knob {m[1]}'
    if m := re.fullmatch(r'og-key-(\d+)', c):
        return f'Organelle key {int(m[1]) - 59}'
    if c == 'og-aux':
        return 'Organelle aux'
    if m := re.fullmatch(r'xport-(\d)', c):
        return f'nanoKONTROL {TRANSPORT[int(m[1]) - 1]}'
    if m := re.fullmatch(r'slider-(\d)', c):
        return f'nanoKONTROL fader {m[1]}'
    if m := re.fullmatch(r'knob-(\d)', c):
        return f'nanoKONTROL knob {m[1]}'
    if m := re.fullmatch(r'btn-a-(\d)', c):
        return f'nanoKONTROL upper button {m[1]}'
    if m := re.fullmatch(r'btn-b-(\d)', c):
        return f'nanoKONTROL lower button {m[1]}'
    if c == 'lp-setup':
        return 'Launchpad Setup'
    if c == 'pad-*':
        return "Launchpad's pads"
    if m := re.fullmatch(r'pad-(\d)(\d)', c):
        return f'Launchpad pad, row {m[1]}, column {m[2]}'
    if m := re.fullmatch(r'lp-cc-(\d+)', c):
        n = int(m[1])
        if n == 90:
            return 'Launchpad top-left corner'
        if 91 <= n <= 98:
            return f'Launchpad top row {n - 90}'
        if 101 <= n <= 108:
            return f'Launchpad upper bottom row {n - 100}'
        if 1 <= n <= 8:
            return f'Launchpad lower bottom row {n}'
        if n % 10 == 0:
            return f'Launchpad left column, row {(90 - n) // 10}'
        if n % 10 == 9:
            return f'Launchpad right column, row {(99 - n) // 10}'
    return c


MEANS = {
    'tempo 0': 'tempo',
    'drums last': 'the global last step',
    'drums track-last': "the selected track's last step",
    'rush 0': 'rush',
    'start 0': 'PLAY',
    'stop 0': 'STOP',
    'arrangement 21': 'tap tempo',
    'perform arm': 'arm: take a control into play',
    'recover 0': 'recover',
    'voices setup': 'the diagnostics page',
    'voices aux': 'the songs and sections page',
    'save 0': 'save',
    'revert 0': 'revert',
    'section 1': 'back a section',
    'section 2': 'forward a section, or the next song',
    'melody on-h': 'on',
    'melody on-m': 'on',
    'melody roll-chords': 'roll chords',
    'melody roll-melody': 'roll the melody',
    'melody roll-rhythm': 'roll the rhythm',
    'melody pins-clear': 'clear pins',
    'melody bass': 'bass only',
    'melody style': 'modal or functional',
    'diag 0': 'the diagnostic screen',
    'test-mode 0': 'test mode',
    'melody h': 'chords on the top row, the rhythm below',
    'melody m': "32 steps above, the mode's notes below",
    'perform pad-': 'tap a column to set its fader',
    'machine p': 'parameters above, patches on row 2, notes on row 1',
}


def meaning(dest, arg):
    known = MEANS.get(f'{dest} {arg}')
    if known:
        return known
    if dest == 'section':
        return 'the section it shows'
    if dest == 'song':
        return 'that song of the setlist'
    if dest == 'voices':
        if m := re.fullmatch(r'(left|right)-(\d)', arg):
            return f"that row's {'behavior' if m[1] == 'left' else 'setup'}"
    if dest == 'perform':
        return 'whatever this section has in play'
    if dest == 'drum-page':
        return 'the drum page'
    return f'{dest} {arg}'


PAGE_NAMES = {
    'all': 'On every page',
    'perform': 'On the performance page',
    'drums': 'On the drum page',
    'harmony': 'On the harmony page',
    'melody': 'On the melody page',
    'sound': "On a voice's setup page",
    'diag': 'On the diagnostics page',
}


def map_tables():
    the_map = rows('cut-it-map.txt')
    pages = list(PAGE_NAMES)
    for r in the_map:
        if r[0] not in pages:
            pages.append(r[0])
    out = []
    for page in pages:
        these = [r for r in the_map if r[0] == page]
        if not these:
            continue
        # A drum page's 70-odd pads say the same thing: one line for them all.
        by = grouped((meaning(r[2], r[3]), control_name(r[1])) for r in these)
        out += [f'## {PAGE_NAMES.get(page, page)}', '', '| Control | Does |', '|---|---|']
        for means, controls in by.items():
            shown = (f'{controls[0]} to {controls[-1]}' if len(controls) > 4
                     else ', '.join(controls))
            out.append(f'| {shown} | {means} |')
        out.append('')
    return '\n'.join(out)


TABLES = {
    'machines': machines_table,
    'factory': factory_table,
    'controls': controls_table,
    'map': map_tables,
}


def sections():
    """(title, body) for each section, its tables filled in, its own title taken off."""
    out = []
    for path in sorted(MANUAL.glob('*.md')):
        text = path.read_text(encoding='utf-8')
        m = re.search(r'^#\s+(.+)$', text, re.M)
        title = m[1].strip() if m else path.stem
        body = re.sub(r'^#\s+.+\n+', '', text, count=1)
        for name, make in TABLES.items():
            body = body.replace('{{' + name + '}}', make())
        out.append((title, body))
    return out


def demoted(body):
    """Every heading one level down, so a section's own headings sit under its title."""
    lines, fenced = [], False
    for line in body.splitlines():
        if line.startswith('```'):
            fenced = not fenced
        lines.append('#' + line if not fenced and re.match(r'#+\s', line) else line)
    return '\n'.join(lines)


def anchor(heading, seen):
    """GitHub's anchor for a heading: lowercased, punctuation dropped, spaces to hyphens, and a
    -1, -2 on a repeat."""
    slug = re.sub(r'[^\w\- ]', '', heading.strip().lower()).replace(' ', '-')
    n = seen.get(slug, 0)
    seen[slug] = n + 1
    return slug if n == 0 else f'{slug}-{n}'


def build():
    parts = sections()
    # The contents list links each section by the anchor GitHub gives it, counted in the order
    # GitHub meets every heading, so a section title that repeats one above it still resolves.
    seen = {}
    anchor(TITLE, seen)
    links = []
    for title, body in parts:
        links.append(f'- [{title}](#{anchor(title, seen)})')
        for h in re.findall(r'^#+\s+(.+)$', demoted(body), re.M):
            anchor(h, seen)
    text = '\n\n'.join([f'# {TITLE}', NOTE, '\n'.join(links)]
                       + [f'## {t}\n\n{demoted(b).strip()}' for t, b in parts])
    return re.sub(r'\n{3,}', '\n\n', text).strip() + '\n'


def main(argv):
    text = build()
    if '--check' in argv:
        if OUT.exists() and OUT.read_text(encoding='utf-8') == text:
            print('MANUAL.md is current')
            return 0
        print('MANUAL.md is not what manual/build.py writes: run python3 manual/build.py')
        return 1
    OUT.write_text(text, encoding='utf-8')
    print(f'wrote MANUAL.md: {len(sections())} sections, {text.count(chr(10))} lines')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
