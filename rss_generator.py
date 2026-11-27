
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from urllib.parse import urljoin
import re
import os
import shutil

BASE_URL = "https://www.ff14.co.kr"

# RSS로 만들 페이지 설정
FEEDS = [
    {
        "url": "https://www.ff14.co.kr/news/notice",
        "file": "feed.xml",
        "title": "파이널판타지14 한국 공식 공지사항",
        "description": "FF14 공식 공지사항 RSS",
        "item_path": "/news/notice/view/",
        "use_date": True
    },
    {
        "url": "https://www.ff14.co.kr/news/notice?category=3",
        "file": "patchnotes.xml",
        "title": "파이널판타지14 한국 공식 패치노트",
        "description": "FF14 공식 패치노트 RSS",
        "item_path": "/news/notice/view/",
        "use_date": True
    },
    {
        "url": "https://www.ff14.co.kr/news/event",
        "file": "events.xml",
        "title": "파이널판타지14 한국 공식 이벤트",
        "description": "FF14 공식 이벤트 RSS",
        "item_path": "/news/event/view/",
        "use_date": False
    }
]

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

def generate_feed(feed_config):
    page_url = feed_config["url"]

    response = requests.get(
        page_url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    items = []
    seen = set()

    for a in soup.select("a[href]"):
        href = a.get("href", "")

        if feed_config["item_path"] not in href:
            continue

        link = urljoin(BASE_URL, href)
        title = clean_text(a.get_text(" ", strip=True))

        if not title or link in seen:
            continue

        seen.add(link)

        published = None

        # 게시글 주변 텍스트에서 날짜 추출
        if feed_config.get("use_date", True):
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

    # 날짜가 있는 게시물은 최신순으로 정렬
    if feed_config.get("use_date", True):
        items.sort(
            key=lambda x: x["date"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )

    items = items[:30]

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = feed_config["title"]
    SubElement(channel, "link").text = page_url
    SubElement(channel, "description").text = feed_config["description"]
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

    output_path = os.path.join("public", feed_config["file"])

    with open(output_path, "wb") as f:
        f.write(xml_data)

    print(
        f"{feed_config['file']} 생성 완료: {len(items)}개 게시물"
    )

    shutil.copyfile("test.xml", os.path.join("public", "test.xml"))
    print("test.xml 생성 완료")


def main():
    for feed_config in FEEDS:
        generate_feed(feed_config)

if __name__ == "__main__":
    main()
