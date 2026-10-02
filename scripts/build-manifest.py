from pathlib import Path
import json

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

manifest = {
    "novels": files_under("content/novels", ".json"),
    "chapters": files_under("content/chapters", ".md"),
}

out = ROOT / "content" / "manifest.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print(f"Wrote {out.relative_to(ROOT)} with {len(manifest['novels'])} novels and {len(manifest['chapters'])} chapters.")
