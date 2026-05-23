"""
Bundle the static dashboard into ./dist for Vercel (or any static host).

Source: output/*.html + data/index.json + data/daily/*.json
Output: dist/ (flat, self-contained — no Python, no .env, no source code,
        no history file).

The HTML index uses `fetch('../data/...')` paths so it works under local
http.server serving from the project root. Inside the dist bundle, data/
is a sibling of index.html, so we rewrite '../data/' -> 'data/' as we copy.

Run after each agent run that should be published:

    python scripts/build_dist.py
    vercel deploy --prod ./dist
"""
import argparse
import shutil
import sys
from pathlib import Path


def build_dist(output_dir: Path, data_dir: Path, dest: Path) -> None:
    if not output_dir.exists():
        sys.exit(f"output dir not found: {output_dir} — run the agent first")

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    (dest / "data" / "daily").mkdir(parents=True)

    html_count = 0
    for html in sorted(output_dir.glob("*.html")):
        text = html.read_text(encoding="utf-8")
        # In the dist bundle, data/ is a sibling of index.html, not one level up.
        text = text.replace("../data/", "data/")
        (dest / html.name).write_text(text, encoding="utf-8")
        html_count += 1

    json_count = 0
    if (data_dir / "index.json").exists():
        shutil.copy(data_dir / "index.json", dest / "data" / "index.json")
        json_count += 1

    daily = data_dir / "daily"
    if daily.exists():
        for f in sorted(daily.glob("*.json")):
            shutil.copy(f, dest / "data" / "daily" / f.name)
            json_count += 1

    # Intentionally not copying data/articles.json — it stores the full extracted
    # body text of every historical article for MinHash dedup. The dashboard does
    # not load it, and publishing it would leak a lot of content and bloat deploys.

    print(f"Built {dest}/")
    print(f"  HTML pages : {html_count}")
    print(f"  Data files : {json_count}")
    print(f"  Size       : {sum(f.stat().st_size for f in dest.rglob('*') if f.is_file()) / 1024:.0f} KB")


def main():
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--output", default="output", help="Source HTML dir (default: output/)")
    p.add_argument("--data", default="data", help="Source data dir (default: data/)")
    p.add_argument("--dest", default="dist", help="Destination bundle dir (default: dist/)")
    args = p.parse_args()
    build_dist(Path(args.output), Path(args.data), Path(args.dest))


if __name__ == "__main__":
    main()
