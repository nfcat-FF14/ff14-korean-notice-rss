
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from urllib.parse import urljoin
import re
import html
import os

BASE_URL = "https://www.ff14.co.kr"
NOTICE_URL = "https://www.ff14.co.kr/news/notice"
OUTPUT_FILE = "feed.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FF14RSSBot/1.0)"
}

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

def extract_date(text):
    text = clean_text(text)

    patterns = [
        r"(20\d{2})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})",
        r"(\d{2})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            y, m, d = map(int, match.groups())
            if y < 100:
                y += 2000
            try:
                return datetime(y, m, d, tzinfo=timezone.utc)
            except ValueError:
                pass

    return None

def main():
    response = requests.get(
        NOTICE_URL,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    items = []
    seen = set()

    for a in soup.select("a[href]"):
        href = a.get("href", "")

        if "/news/notice/view/" not in href:
            continue

        link = urljoin(BASE_URL, href)
        title = clean_text(a.get_text(" ", strip=True))

        if not title or link in seen:
            continue

        seen.add(link)

        # 게시글 주변 텍스트에서 날짜 추출
        parent = a
        surrounding_text = title

        for _ in range(5):
            if parent.parent:
                parent = parent.parent
                surrounding_text += " " + parent.get_text(" ", strip=True)

        published = extract_date(surrounding_text)

        items.append({
            "title": title,
            "link": link,
            "date": published
        })

    # 날짜가 확인되는 게시물을 최신순으로 정렬
    items.sort(
        key=lambda x: x["date"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True
    )

    items = items[:30]

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = "파이널판타지14 한국 공식 공지사항"
    SubElement(channel, "link").text = NOTICE_URL
    SubElement(channel, "description").text = "FF14 공식 공지사항 RSS"
    SubElement(channel, "language").text = "ko-KR"
    SubElement(channel, "lastBuildDate").text = format_datetime(
        datetime.now(timezone.utc)
    )

    for post in items:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = post["title"]
        SubElement(item, "link").text = post["link"]
        SubElement(item, "guid", isPermaLink="true").text = post["link"]

        if post["date"]:
            SubElement(item, "pubDate").text = format_datetime(post["date"])

    xml_data = tostring(rss, encoding="utf-8", xml_declaration=True)

    os.makedirs("public", exist_ok=True)

    with open(os.path.join("public", OUTPUT_FILE), "wb") as f:
        f.write(xml_data)

    print(f"RSS 생성 완료: {len(items)}개 게시물")

if __name__ == "__main__":
    main()
