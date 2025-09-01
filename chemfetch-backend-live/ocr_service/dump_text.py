#!/usr/bin/env python3
from pathlib import Path
import re
import sys

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
except Exception:
    pdfminer_extract = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None


def extract_text(path: Path) -> str:
    text = ''
    if pdfplumber is not None:
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ''
            if text.strip():
                return text
        except Exception:
            pass
    if pdfminer_extract is not None:
        try:
            return pdfminer_extract(str(path)) or ''
        except Exception:
            pass
    return text


def main():
    if len(sys.argv) < 2:
        print('Usage: dump_text.py [--full] <pdf>')
        sys.exit(1)
    args = sys.argv[1:]
    full = False
    if args and args[0] == '--full':
        full = True
        args = args[1:]
    p = Path(args[0])
    t = extract_text(p)
    if full:
        print(t)
    else:
        print('LEN', len(t))
        # Print lines with likely German/English labels of interest
        pat = re.compile(r'(Hersteller|Lieferant|Verwendung|Verwendungszweck|Anwendung|Klasse|Gefahrklasse|Verpackungsgruppe|UN\s*Nr|UN-Nummer|Abschnitt\s*1|SECTION\s*1|Section\s*1|Identifikation|Identifizierung|Supplier|Manufacturer|Recommended use|Use of the)', re.IGNORECASE)
        for line in t.splitlines():
            if pat.search(line):
                print(line)


if __name__ == '__main__':
    main()
