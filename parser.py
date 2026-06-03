import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import random

H = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BASE = "https://krisha.kz/prodazha/kvartiry/astana/"


def get_page(url, page=1):
    params = {"page": page} if page > 1 else {}
    try:
        response = requests.get(url, headers=H, params=params, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"Error loading page {page}: {e}")
        return None


def parse_price(text):
    digits = re.sub(r"[^\d]", "", text)
    return float(digits) if digits else None


def parse_card(card):
    try:
        data = {}
        price_tag = card.select_one(".a-card__price")
        if not price_tag:
            return None
        data["price"] = parse_price(price_tag.get_text())

        title_tag = card.select_one(".a-card__title")
        title = title_tag.get_text(separator=" ", strip=True) if title_tag else ""

        rooms_match = re.search(r"(\d+)-комнатная", title)
        data["rooms"] = int(rooms_match.group(1)) if rooms_match else None

        area_match = re.search(r"([\d.]+)\s*м²", title)
        data["area"] = float(area_match.group(1)) if area_match else None

        floor_match = re.search(r"(\d+)/(\d+)\s*этаж", title)
        if floor_match:
            data["floor"] = int(floor_match.group(1))
            data["total_floors"] = int(floor_match.group(2))
        else:
            data["floor"] = None
            data["total_floors"] = None

        addr_tag = card.select_one(".a-card__subtitle")
        data["address"] = addr_tag.get_text(strip=True) if addr_tag else None

        desc_tag = card.select_one(".a-card__description")
        desc = desc_tag.get_text(separator=" ", strip=True) if desc_tag else ""

        year_match = re.search(r"(\d{4})\s*г\.?п\.?", desc)
        data["year_built"] = int(year_match.group(1)) if year_match else None

        if "монолит" in desc.lower():
            data["house_type"] = "монолитный"
        elif "кирпич" in desc.lower():
            data["house_type"] = "кирпичный"
        elif "панельный" in desc.lower():
            data["house_type"] = "панельный"
        else:
            data["house_type"] = None

        if "мебелирована полностью" in desc.lower():
            data["furnished"] = "yes"
        elif "мебелирована частично" in desc.lower():
            data["furnished"] = "partial"
        elif "без мебели" in desc.lower():
            data["furnished"] = "no"
        else:
            data["furnished"] = None

        link_tag = card.select_one("a.a-card__url")
        data["url"] = "https://krisha.kz" + link_tag["href"] if link_tag else None

        return data
    except Exception as e:
        print(f"Error parsing card: {e}")
        return None


def scrape(max_pages=50, delay=2.0):
    all_items = []

    for page in range(1, max_pages + 1):
        print(f"Page {page}/{max_pages}...", end=" ")
        soup = get_page(BASE, page)

        if soup is None:
            print("skipped")
            continue

        cards = soup.select(".a-card")
        if not cards:
            print("no listings found, stopping")
            break

        page_items = []
        for card in cards:
            listing = parse_card(card)
            if listing and listing.get("price"):
                page_items.append(listing)

        all_items.extend(page_items)
        print(f"collected {len(page_items)} listings (total: {len(all_items)})")

        time.sleep(delay + random.uniform(0, 1))

    df = pd.DataFrame(all_items)

    if not df.empty:
        df.drop_duplicates(subset=["url"], inplace=True)
        df = df[df["price"] > 1_000_000]
        df = df[df["price"] < 1_000_000_000]
        df.reset_index(drop=True, inplace=True)
        df.to_csv("astana_housing.csv", index=False, encoding="utf-8-sig")
        print(f"\nDone. Collected {len(df)} listings -> astana_housing.csv")
    else:
        print("\nNo data collected")

    return df


if __name__ == "__main__":
    df = scrape(max_pages=50, delay=2.0)
    print(df.head())
    print(df.info())