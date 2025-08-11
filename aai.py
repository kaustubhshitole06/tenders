from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import time
import re

BASE_URL = "https://www.aai.aero"

def get_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "localhost:9222")
    return webdriver.Chrome(options=chrome_options)

def extract_corrigendum_link(onclick_value):
    if not onclick_value:
        return None
    match = re.search(r"aai_get_tender_corrigendum\((\d+)", onclick_value)
    if match:
        corr_id = match.group(1)
        return f"{BASE_URL}/tender/corrigendum/{corr_id}"
    return None

def get_full_url(href):
    if not href:
        return None
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href

def extract_tender_details(tender_div):
    data = {}
    title_div = tender_div.select_one(".tender-name .col-md-10")
    data["title"] = title_div.get_text(strip=True) if title_div else None

    info_divs = tender_div.select(".general-info .col-md-4")
    for div in info_divs:
        span = div.find("span")
        if not span:
            continue
        label = span.text.strip().lower()
        value = div.get_text(strip=True).replace(span.text, "").strip()
        if "airport" in label:
            data["airport"] = value
        elif "last sale" in label:
            data["last_sale_date"] = value
        elif "department" in label:
            data["department"] = value

    tender_info_fields = {
        "tender type": "tender_type",
        "tender is": "tender_is",
        "estimated cost": "estimated_cost",
        "bid type": "bid_type",
        "e-bid no": "ebid_no",
        "status": "status"
    }
    tender_info_divs = tender_div.select(".tender-info .col-md-4")
    for div in tender_info_divs:
        span = div.find("span")
        if not span:
            continue
        label = span.text.strip().lower().replace(":", "")
        value = div.get_text(strip=True).replace(span.text, "").strip()
        for key in tender_info_fields:
            if key in label:
                data[tender_info_fields[key]] = value
                break

    desc_div = tender_div.select_one(".tednder_description")
    data["description"] = desc_div.get_text(strip=True) if desc_div else None

    corr_link = None
    for a in tender_div.find_all("a", onclick=True):
        onclick_val = a["onclick"]
        if "aai_get_tender_corrigendum" in onclick_val:
            corr_link = extract_corrigendum_link(onclick_val)
            break
    data["corrigendum_link"] = corr_link

    download_link = None
    for a in tender_div.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        if href.lower().endswith(".pdf") or "download" in text or "tender document" in text:
            download_link = get_full_url(href)
            break
    data["download_link"] = download_link

    return data

def extract_all_tenders(driver, target_count):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    tender_divs = soup.select("div.aai-tender")
    tenders = []

    for tender_div in tender_divs:
        if len(tenders) >= target_count:
            break
        tender_data = extract_tender_details(tender_div)
        tenders.append(tender_data)

    return tenders

def get_next_page_url(driver):
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        pagination_links = soup.select("a[title*='Go to page']")
        current_url = driver.current_url
        current_page = 0

        if "page=" in current_url:
            import urllib.parse
            parsed_url = urllib.parse.urlparse(current_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if 'page' in query_params:
                current_page = int(query_params['page'][0])

        next_page = current_page + 1
        for link in pagination_links:
            if f"page={next_page}" in link.get('href', ''):
                next_url = link['href']
                if next_url.startswith('/'):
                    return BASE_URL + next_url
                return next_url
        return None
    except Exception as e:
        print(f" Error finding next page: {e}")
        return None

def scrape_tenders_with_pagination(driver, target_count):
    all_tenders = []
    page_num = 1
    print(f" Target: {target_count} tenders")

    while len(all_tenders) < target_count:
        print(f" Scraping page {page_num}...")

        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "aai-tender")))
            time.sleep(3)
        except:
            print(f" No tenders found on page {page_num}")
            break

        remaining_count = target_count - len(all_tenders)
        page_tenders = extract_all_tenders(driver, remaining_count)

        if not page_tenders:
            print(f" No more tenders found on page {page_num}")
            break

        for i, tender in enumerate(page_tenders):
            tender["Tender"] = len(all_tenders) + i + 1

        all_tenders.extend(page_tenders)
        print(f" Found {len(page_tenders)} tenders on page {page_num}. Total: {len(all_tenders)}")

        if len(all_tenders) >= target_count:
            break

        next_page_url = get_next_page_url(driver)
        if not next_page_url:
            print(" No more pages available")
            break

        print(f" Going to next page: {next_page_url}")
        driver.get(next_page_url)
        page_num += 1
        time.sleep(2)

    return all_tenders[:target_count]

def main():
    driver = get_driver()
    driver.get(f"{BASE_URL}/en/tender/tender-search")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "edit-submit-tender")))

    # No keyword search
    driver.find_element(By.ID, "edit-submit-tender").click()

    # Scrape tenders
    tenders = scrape_tenders_with_pagination(driver, target_count=20)

    # Save to JSON
    with open("aai_final_tenders.json", "w", encoding="utf-8") as f:
        json.dump(tenders, f, indent=2, ensure_ascii=False)

    print(f" {len(tenders)} tender(s) saved to 'aai_final_tenders.json'")
    driver.quit()

if __name__ == "__main__":
    main()
