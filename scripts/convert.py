#!/usr/bin/env python3
"""
Convert channels.json (HoaDao TV format) to M3U playlist.

JSON structure:
  {
    "name": "...",
    "groups": [
      {
        "id": "live",
        "name": "⚽ Bóng đá",
        "channels": [
          {
            "id": "ch-xxx",
            "name": "Match Name",
            "image": { "url": "..." },
            "labels": [{ "text": "● LIVE" }],
            "sources": [
              {
                "name": "...",
                "contents": [
                  {
                    "name": "Commentary/League",
                    "streams": [
                      {
                        "stream_links": [
                          {
                            "name": "HD",
                            "type": "hls",
                            "url": "https://...",
                            "request_headers": [
                              { "key": "Referer", "value": "..." },
                              { "key": "User-Agent", "value": "Mozilla/5.0" }
                            ]
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ============================================================
# CONFIGURATION
# ============================================================
JSON_URL = os.environ.get(
    "JSON_PLAYLIST_URL",
    "https://raw.githubusercontent.com/winmk2021/nguon/main/channels.json",
)

OUTPUT_FILE = "playlist.m3u"
# Chỉ lấy stream link "default": true hoặc link đầu tiên nếu không có default
PREFER_DEFAULT = True
# Chỉ lấy quality ưu tiên (HD trước, nếu không có thì lấy cái đầu tiên)
PREFER_QUALITY = ["HD", "FHD", "1080p", "720p", "SD", "360p"]
# ============================================================


def fetch_json(url: str) -> dict:
    """Fetch JSON data from a URL."""
    print(f"[INFO] Fetching JSON from:\n       {url}")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PlaylistConverter/1.0)",
            "Accept": "application/json, */*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[ERROR] URL error: {e.reason}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")
        sys.exit(1)


def pick_stream_link(stream_links: list) -> dict | None:
    """
    Pick best stream link:
    1. link có 'default': true + quality ưu tiên cao nhất
    2. link đầu tiên nếu không có default
    """
    if not stream_links:
        return None

    # Thử tìm theo quality ưu tiên với default=true
    for quality in PREFER_QUALITY:
        for lnk in stream_links:
            if PREFER_DEFAULT and not lnk.get("default", False):
                continue
            if lnk.get("name", "").upper() == quality.upper():
                return lnk

    # Lấy link default đầu tiên
    for lnk in stream_links:
        if lnk.get("default", True):  # Coi None/missing là chấp nhận
            return lnk

    # Fallback: link đầu tiên
    return stream_links[0]


def build_extinf(channel_name: str, group_name: str, logo_url: str, quality: str) -> str:
    """Build a single #EXTINF line."""
    display_name = channel_name
    if quality and quality.upper() not in ("STREAM", ""):
        display_name = f"{channel_name} [{quality}]"

    attrs = []
    if group_name:
        attrs.append(f'group-title="{group_name}"')
    if logo_url:
        attrs.append(f'tvg-logo="{logo_url}"')

    attrs_str = " ".join(attrs)
    if attrs_str:
        return f"#EXTINF:-1 {attrs_str},{display_name}"
    return f"#EXTINF:-1,{display_name}"


def headers_to_m3u(request_headers: list) -> str:
    """
    Convert request_headers list to M3U8 header format.
    M3U supports: #EXTVLCOPT:http-referrer=... and #EXTVLCOPT:http-user-agent=...
    Also adds vlcopt for broad compatibility.
    """
    lines = []
    referer = ""
    user_agent = ""
    for h in request_headers:
        key = h.get("key", "").lower()
        val = h.get("value", "")
        if key == "referer":
            referer = val
        elif key == "user-agent":
            user_agent = val

    if referer:
        lines.append(f"#EXTVLCOPT:http-referrer={referer}")
    if user_agent:
        lines.append(f"#EXTVLCOPT:http-user-agent={user_agent}")
    return "\n".join(lines)


def extract_entries(data: dict) -> list[dict]:
    """
    Walk the nested JSON and produce flat list of stream entries.
    Each entry: { name, url, group, logo, quality, headers_str }
    """
    entries = []
    site_name = data.get("name", "")
    groups = data.get("groups", [])

    for group in groups:
        group_name = group.get("name", "")
        channels = group.get("channels", [])

        for channel in channels:
            ch_name = channel.get("name", "Unnamed")
            logo_url = ""
            image = channel.get("image")
            if isinstance(image, dict):
                logo_url = image.get("url", "")

            # Lấy label (ví dụ: "● LIVE", "● Upcoming")
            labels = channel.get("labels", [])
            label_text = labels[0].get("text", "") if labels else ""

            sources = channel.get("sources", [])
            added_urls = set()  # Tránh duplicate URL

            for source in sources:
                contents = source.get("contents", [])
                for content in contents:
                    content_name = content.get("name", "")  # e.g. "French Ligue 1"
                    streams = content.get("streams", [])

                    for stream in streams:
                        stream_links = stream.get("stream_links", [])
                        link = pick_stream_link(stream_links)
                        if not link:
                            continue

                        url = link.get("url", "").strip()
                        if not url or url in added_urls:
                            continue
                        added_urls.add(url)

                        quality = link.get("name", "")
                        request_headers = link.get("request_headers", [])
                        headers_str = headers_to_m3u(request_headers)

                        # Tên hiển thị: thêm content_name nếu là giải đấu
                        display_name = ch_name
                        if content_name and content_name != source.get("name", ""):
                            display_name = f"{ch_name} - {content_name}"

                        entries.append({
                            "name": display_name,
                            "url": url,
                            "group": group_name,
                            "logo": logo_url,
                            "quality": quality,
                            "headers_str": headers_str,
                            "label": label_text,
                        })

    return entries


def build_m3u(entries: list[dict], source_url: str) -> str:
    """Build full M3U content."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "#EXTM3U",
        f"# Auto-generated by PlaylistConverter",
        f"# Source: {source_url}",
        f"# Updated: {now}",
        f"# Total streams: {len(entries)}",
        "",
    ]

    for entry in entries:
        extinf = build_extinf(
            channel_name=entry["name"],
            group_name=entry["group"],
            logo_url=entry["logo"],
            quality=entry["quality"],
        )
        lines.append(extinf)
        if entry["headers_str"]:
            lines.append(entry["headers_str"])
        lines.append(entry["url"])

    return "\n".join(lines) + "\n"


def main():
    print("=" * 55)
    print("  HoaDao JSON → M3U Playlist Converter")
    print("=" * 55)

    # 1. Fetch
    data = fetch_json(JSON_URL)
    site_name = data.get("name", "Unknown Site")
    print(f"[INFO] Site: {site_name}")

    num_groups = len(data.get("groups", []))
    print(f"[INFO] Groups found: {num_groups}")

    # 2. Extract streams
    entries = extract_entries(data)
    print(f"[INFO] Total stream entries extracted: {len(entries)}")

    if not entries:
        print("[ERROR] No stream entries found!")
        sys.exit(1)

    # 3. Build M3U
    m3u_content = build_m3u(entries, JSON_URL)

    # 4. Write output (output to repo root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    output_path = os.path.join(repo_root, OUTPUT_FILE)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(m3u_content)

    size_kb = len(m3u_content) / 1024
    print(f"[SUCCESS] Written: {output_path}")
    print(f"[INFO]    Size: {size_kb:.1f} KB | Streams: {len(entries)}")


if __name__ == "__main__":
    main()
