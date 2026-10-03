from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]

def files_under(relative_dir, suffix):
    base = ROOT / relative_dir
    if not base.exists():
        return []
    return [
        p.relative_to(ROOT).as_posix()
        for p in sorted(base.glob(f"*{suffix}"))
        if p.is_file()
    ]

def chapter_metadata(relative_path):
    path = ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n([\s\S]*?)\n---", text)
    if not match:
        return None

    meta = {}
    for line in match.group(1).splitlines():
        field = re.match(r"^([^:\s][^:]*):\s*(.*)$", line)
        if not field:
            continue
        key = field.group(1).strip()
        value = field.group(2).strip().strip("\"'")
        if value == "true":
            value = True
        elif value == "false":
            value = False
        elif value.isdigit():
            value = int(value)
        meta[key] = value

    required = ("title", "novel", "chapter_number", "date")
    if not all(key in meta for key in required):
        print(f"Skipping {relative_path}: missing required chapter metadata.")
        return None

    return {
        "path": relative_path,
        "title": meta["title"],
        "novel": meta["novel"],
        "chapter_number": meta["chapter_number"],
        "date": meta["date"],
        "draft": bool(meta.get("draft", False)),
    }

chapter_paths = files_under("content/chapters", ".md")
chapters = [chapter_metadata(path) for path in chapter_paths]
chapters = [chapter for chapter in chapters if chapter is not None]

manifest = {
    "novels": files_under("content/novels", ".json"),
    "chapters": chapters,
}

out = ROOT / "content" / "manifest.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print(f"Wrote {out.relative_to(ROOT)} with {len(manifest['novels'])} novels and {len(manifest['chapters'])} chapter records.")
