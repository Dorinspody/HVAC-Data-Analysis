import time
from urllib.parse import urljoin, urlsplit

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


#data loading
BASE_URL = "https://daikincomfort.com/products"
OUTPUT_CSV = "product_specification_sheets2.csv"
MAX_CATEGORY_LEVELS = 4
HEADERS = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1


# DISCOVER TOP-LEVEL CATEGORY / SECTION LINKS

def get_category_urls(base_url):
    print("\n" + "=" * 100)
    print("STAGE 1: DISCOVERING CATEGORY LINKS FROM", base_url)
    print("=" * 100)

    response = requests.get(base_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    urls = set()
    for link in soup.find_all("a", href=True):
        full_url = urljoin(base_url, link["href"])
        full_url = full_url.split("?")[0].split("#")[0]
        if "/products/" not in full_url:
            continue
        urls.add(full_url.rstrip("/"))
    print(f"Found {len(urls)} category link(s)")
    return sorted(urls)

#EXPAND EACH CATEGORY INTO PRODUCT PAGE URLS
def get_product_urls_for_category(driver, category_url):
    try:
        driver.set_page_load_timeout(30)
        driver.get(category_url)
    except Exception as e:
        print("  SKIPPED: PAGE COULD NOT BE LOADED")
        print(" ", e)
        return set()

    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Scroll to the bottom repeatedly until the page stops growing
    last_height = 0
    while True:
        current_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, arguments[0]);", current_height)
        time.sleep(2)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break

        last_height = new_height

    time.sleep(3)  # let any lingering JS settle

    links = driver.find_elements(By.CSS_SELECTOR, "a[href]")

    category_path = category_url.rstrip("/") + "/"

    product_urls = set()

    for link in links:
        href = link.get_attribute("href")
        if not href:
            continue
        href = urljoin(category_url, href)
        href = href.split("?")[0].split("#")[0]
        href = href.rstrip("/")
        if href == category_url.rstrip("/"):
            continue
        if href.startswith(category_path):
            product_urls.add(href)
    if not product_urls:
        print("  No child products found -- treating this URL as a product page itself")
        return {category_url.rstrip("/")}
    print(f"  Found {len(product_urls)} product(s)")
    return product_urls

def get_all_product_urls(category_urls):
    print("\n" + "=" * 100)
    print("STAGE 2: EXPANDING CATEGORIES INTO PRODUCT PAGES")
    print("=" * 100)
    driver = webdriver.Firefox()
    all_product_urls = set()
    try:
        for category_url in category_urls:
            print("\nPROCESSING:", category_url)

            product_urls = get_product_urls_for_category(driver, category_url)

            all_product_urls.update(product_urls)

    finally:
        driver.quit()
    print(f"\nTOTAL UNIQUE PRODUCT PAGES: {len(all_product_urls)}")
    return sorted(all_product_urls)


#PARSE CATEGORY / PRODUCT SLUG FROM THE URL
def parse_category_and_slug(product_url):
    path = urlsplit(product_url).path.strip("/")
    parts = path.split("/")
    if "products" in parts:
        parts = parts[parts.index("products") + 1:]
    if not parts:
        return [], ""
    product_slug = parts[-1]
    categories = parts[:-1]
    return categories, product_slug

def slug_to_title(slug):
    """Fallback human-readable name built from a URL slug."""

    text = slug.replace("---", " ").replace("-", " ").strip()

    return text.title()

# SCRAPE PRODUCT NAME + SPECIFICATION SHEET URL

def get_product_details(product_url):

    try:
        response = requests.get(product_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)

        print(f"Status code: {response.status_code} | {product_url}")

        if response.status_code != 200:
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")

        # PRODUCT NAME

        product_name = None
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            product_name = h1.get_text(" ", strip=True)

        elif soup.title and soup.title.get_text(strip=True):
            title_text = soup.title.get_text(strip=True)
            # Strip a common " | Daikin" / " - Daikin" site suffix if present
            product_name = title_text.split("|")[0].split(" - Daikin")[0].strip()

        # SPECIFICATION SHEET PDF LINK

        specification_sheet_url = None
        documents_section = soup.find("div", id="product-warranty-documents")
        if documents_section:
            heading = documents_section.find(
                lambda tag: tag.name == "h2"
                and tag.get_text(strip=True) == "Specification Sheet")
            if heading:
                link = heading.find_next("a", href=True)
                if link:
                    specification_sheet_url = urljoin(product_url, link["href"])

        return product_name, specification_sheet_url
    except Exception as e:
        print(f"ERROR: {product_url}")
        print(e)
        return None, None

# MAIN PIPELINE
def main():
    category_urls = get_category_urls(BASE_URL)
    product_urls = get_all_product_urls(category_urls)
    print("\n" + "=" * 100)
    print("STAGE 3: SCRAPING PRODUCT NAMES + SPECIFICATION SHEET LINKS")
    print("=" * 100)
    rows = []
    for product_url in product_urls:

        categories, product_slug = parse_category_and_slug(product_url)

        product_name, specification_sheet_url = get_product_details(product_url)

        if not product_name:
            product_name = slug_to_title(product_slug)
        row = {}

        for level in range(MAX_CATEGORY_LEVELS):
            column_name = f"category_level_{level + 1}"
            row[column_name] = categories[level] if level < len(categories) else ""

        row["product_slug"] = product_slug
        row["product_name"] = product_name
        row["product_url"] = product_url
        row["specification_sheet_url"] = specification_sheet_url

        rows.append(row)
        time.sleep(REQUEST_DELAY)

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print("\n" + "=" * 100)
    print("DONE")
    print(f"Saved file: {OUTPUT_CSV}")
    print(f"Total products: {len(df)}")
    print(f"Specification sheets found: {df['specification_sheet_url'].notna().sum()}")
    print("=" * 100)


if __name__ == "__main__":
    main()
