#!/usr/bin/env python3
"""The manual: MANUAL.md is what manual/build.py writes from manual/ and the instrument's tables.

A change to the prose or to a table the instrument reads (cut-it-map.txt, -controls, -machines,
-factory) that wasn't built into MANUAL.md fails here, so the manual on GitHub can't fall behind
the instrument. The fix is to run python3 manual/build.py, never to edit MANUAL.md.

Needs no Pd: it reads files. -v prints each check's detail.
"""
import importlib.util
import re
import sys
from pathlib import Path

import lib_assert as A

ROOT = Path(__file__).resolve().parent.parent.parent
spec = importlib.util.spec_from_file_location('manual_build', ROOT / 'manual' / 'build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

# A control is named as its surface labels it. One of each kind of name the map uses.
NAMES = {
    'og-knob-1': 'Organelle knob 1',
    'og-key-60': 'Organelle key 1',
    'og-aux': 'Organelle aux',
    'xport-6': 'nanoKONTROL REC',
    'slider-3': 'nanoKONTROL fader 3',
    'btn-b-8': 'nanoKONTROL lower button 8',
    'lp-cc-80': 'Launchpad left column, row 1',
    'lp-cc-19': 'Launchpad right column, row 8',
    'lp-cc-92': 'Launchpad top row 2',
    'lp-cc-108': 'Launchpad upper bottom row 8',
    'lp-cc-8': 'Launchpad lower bottom row 8',
    'pad-71': 'Launchpad pad, row 7, column 1',
}
wrong = {c: (build.control_name(c), want) for c, want in NAMES.items()
         if build.control_name(c) != want}
A.check('%d controls named as their surfaces label them' % len(NAMES), not wrong, wrong)

sections = build.sections()
A.check('every file in manual/ is a section (%d)' % len(sections),
        len(sections) == len(list((ROOT / 'manual').glob('*.md'))) and len(sections) > 0)

text = build.build()
left = re.findall(r'\{\{\w+\}\}', text)
A.check('every table named in the prose is filled in', not left, left)

# Every control the map gives a meaning shows up in the map's tables: a page's 70-odd pads are
# one line, so this counts the map's rows by page and the tables' lines by page.
the_map = build.rows('cut-it-map.txt')
pages = {r[0] for r in the_map}
A.check('the map has rows to list (%d, on %d pages)' % (len(the_map), len(pages)), len(the_map) > 0)
headed = {name for name in build.PAGE_NAMES.values() if f'### {name}' in text}
missing = [p for p in pages if f'### {build.PAGE_NAMES.get(p, p)}' not in text]
A.check('every page of the map has its table (%d)' % len(headed), not missing, missing)

current = (ROOT / 'MANUAL.md').read_text(encoding='utf-8') if (ROOT / 'MANUAL.md').exists() else ''
A.check('MANUAL.md is what manual/build.py writes (%d lines)' % text.count('\n'), current == text,
        'run python3 manual/build.py')

sys.exit(1 if A.report() else 0)
