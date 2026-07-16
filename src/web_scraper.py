import json
import logging
import os
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify

# ===================================
# CONFIGURACIÓN
# ===================================

MAX_PAGES = 200
MAX_DEPTH = 2

MIN_TEXT_LENGTH = 300
MAX_TEXT_LENGTH = 50000

DELAY = 1

OUTPUT_FOLDER = "corpus"

USER_AGENT = "AgroRAG-Corpus/1.0"

HEADERS = {
    "User-Agent": USER_AGENT
}

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ===================================
# UTILIDADES
# ===================================

def clean_filename(url: str) -> str:
    name = urlparse(url).path.strip("/")

    if not name:
        name = "index"

    name = name.replace("/", "_")

    return name[:120]


def save_markdown(category, source, url, markdown):

    folder = os.path.join(
        OUTPUT_FOLDER,
        category
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    filename = clean_filename(url)

    path = os.path.join(
        folder,
        f"{filename}.md"
    )

    with open(
        path,
        "w",
        encoding="utf8"
    ) as f:

        f.write(
f"""---
source: {source}
url: {url}
category: {category}
---

{markdown}
"""
        )

    logger.info(f"Guardado -> {path}")


def extract_links(html, base_url):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    urls = []

    for a in soup.find_all("a", href=True):

        href = urljoin(
            base_url,
            a["href"]
        )

        href = href.split("#")[0]

        urls.append(href)

    return urls


def same_domain(url, domain):

    return urlparse(url).netloc == domain


# ===================================
# CRAWLER
# ===================================

def crawl(source):

    domain = urlparse(
        source["url"]
    ).netloc

    visited = set()

    queue = deque()

    queue.append(
        (
            source["url"],
            0
        )
    )

    pages = 0

    while queue and pages < MAX_PAGES:
        url, depth = queue.popleft()
        if depth > MAX_DEPTH:
            continue
        if url in visited:
            continue
        visited.add(url)

        try:

            logger.info(f"Visitando {url}")

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=30
            )

            if response.status_code != 200:
                continue

            html = response.text
            text = trafilatura.extract(
                html,
                include_tables=True,
                include_links=False
            )

            if text:
                if len(text) >= MIN_TEXT_LENGTH:
                    markdown = markdownify(
                        text,
                        heading_style="ATX"
                    )
                    markdown = markdown[
                        :MAX_TEXT_LENGTH
                    ]
                    save_markdown(
                        source["category"],
                        source["name"],
                        url,
                        markdown
                    )
                    pages += 1

            if depth < MAX_DEPTH:
                for link in extract_links(
                    html,
                    url
                ):

                    if same_domain(
                        link,
                        domain
                    ):

                        queue.append(
                            (
                                link,
                                depth + 1
                            )
                        )
            time.sleep(DELAY)
        except Exception as e:
            logger.warning(f"{url} -> {e}")

def main():

    with open(
        "sources.json",
        encoding="utf8"
    ) as f:
        sources = json.load(f)

    for source in sources:
        logger.info("=" * 60)
        logger.info(source["name"])
        logger.info("=" * 60)
        crawl(source)


if __name__ == "__main__":
    main()