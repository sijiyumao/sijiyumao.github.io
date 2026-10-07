# Generates the content manifest and public RSS feed.
from pathlib import Path
import json
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]

SITE_URL = "https://sijiyumao.github.io/"

TORONTO = ZoneInfo("America/Toronto")
NOW = datetime.now(timezone.utc)

def release_time(value):
    if not value:
        return None
    local = datetime.strptime(str(value), "%Y-%m-%d %H:%M")
    aware = local.replace(tzinfo=TORONTO, fold=0)
    # Reject nonexistent times during the spring DST transition.
    if aware.astimezone(timezone.utc).astimezone(TORONTO).replace(tzinfo=None) != local:
        raise ValueError("This Toronto time does not exist due to daylight saving time.")
    return aware.astimezone(timezone.utc)

def build_rss(chapters, novel_paths):
    novels = {}
    for relative_path in novel_paths:
        try:
            data = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
            if data.get("id"):
                novels[data["id"]] = data
        except Exception as exc:
            print(f"Skipping RSS novel metadata {relative_path}: {exc}")

    public = [ch for ch in chapters if not ch.get("draft")]
    public.sort(key=lambda ch: (str(ch.get("date", "")), int(ch.get("chapter_number", 0))), reverse=True)

    items = []
    for ch in public:
        novel = novels.get(ch["novel"], {})
        novel_title = str(novel.get("title", ch["novel"]))
        number = ch["chapter_number"]
        chapter_title = str(ch["title"])
        title = f"{novel_title} — Chapter {number}: {chapter_title}"
        link = f"{SITE_URL}#read/{ch['novel']}/{number}"
        try:
            dt = datetime.fromisoformat(ch["release_at"]) if ch.get("release_at") else datetime.strptime(str(ch["date"]), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            pub_date = format_datetime(dt)
        except ValueError:
            pub_date = format_datetime(datetime.now(timezone.utc))
        items.append(
            "    <item>\n"
            f"      <title>{escape(title)}</title>\n"
            f"      <link>{escape(link)}</link>\n"
            f"      <guid isPermaLink=\"true\">{escape(link)}</guid>\n"
            f"      <pubDate>{escape(pub_date)}</pubDate>\n"
            "    </item>"
        )

    rss = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<rss version=\"2.0\">\n"
        "  <channel>\n"
        "    <title>Yumao Novels — New Chapters</title>\n"
        f"    <link>{SITE_URL}</link>\n"
        "    <description>New chapter releases from Yumao Novels.</description>\n"
        "    <language>en</language>\n"
        + ("\n".join(items) + "\n" if items else "")
        + "  </channel>\n"
        "</rss>\n"
    )
    feed = ROOT / "feed.xml"
    feed.write_text(rss, encoding="utf-8")
    print(f"Wrote {feed.relative_to(ROOT)} with {len(items)} public chapter items.")


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

    try:
        due = release_time(meta.get("release_at"))
    except ValueError as exc:
        print(f"Keeping {relative_path} hidden: invalid scheduled release ({exc})")
        return None
    if due and due > NOW:
        return None

    return {
        "release_at": due.isoformat() if due else None,
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

build_rss(chapters, manifest["novels"])
