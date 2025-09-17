from pathlib import Path
path = Path(server/utils/scraper.ts)
lines = path.read_text().splitlines()
for i, line in enumerate(lines):
 if Bing links collected in line:
 for offset in range(-4, 6):
 j = i + offset
 if 0 <= j < len(lines):
 print(f{j+1:04}: {lines[j]})
 print()
