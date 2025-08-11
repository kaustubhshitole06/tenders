import time
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

unit_map = {
    "Corporate Office": 1,
    "Tandur": 2,
    "Rajban": 3,
    "Bokajan": 4,
    "Zonal Office Hyderabad": 5
}

def start_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_tender_from_row(row, driver):
    cols = row.find_all("td")
    if len(cols) < 6:
        return None

    tender_info = {
        "subject": cols[0].get_text(strip=True),
        "sale_open_date": cols[1].get_text(strip=True),
        "sale_close_date": cols[2].get_text(strip=True),
        "last_submission": cols[3].get_text(strip=True),
        "tender_open_date": cols[4].get_text(strip=True),
        "view_link": None,
        "attachments": []
    }

    view_tag = cols[5].find("a")
    if view_tag and view_tag.get("href"):
        view_link = "https://cciltd.in/" + view_tag["href"].lstrip("./")
        tender_info["view_link"] = view_link

        # Open detail page in new tab safely
        current_tabs = driver.window_handles
        driver.execute_script(f"window.open('{view_link}', '_blank');")
        time.sleep(1)

        new_tabs = driver.window_handles
        if len(new_tabs) <= len(current_tabs):
            print("Failed to open new tab for detail page.")
            return tender_info

        driver.switch_to.window(new_tabs[-1])
        driver.get(view_link)
        time.sleep(2)

        detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
        attachment_links = []

        for a in detail_soup.select("a[href$='.pdf'], a[href$='.zip'], a[href$='.doc'], a[href$='.docx']"):
            href = a.get("href")
            if href and not href.startswith("http"):
                href = "https://cciltd.in/" + href.lstrip("./")
            attachment_links.append(href)

        tender_info["attachments"] = attachment_links

        driver.close()
        driver.switch_to.window(current_tabs[0])

    return tender_info

def scrape_tenders_with_pagination(driver, unit_id, target_count):
    tenders = []
    page = 1

    while len(tenders) < target_count:
        url = f"https://cciltd.in/tender_table.php?unit={unit_id}&tender_type=open"
        print(f" Scraping page {page}...\n🔗 URL: {url}")
        driver.get(url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find("table", {"class": "table table-bordered table-striped table-hover"})
        if not table:
            print(" No tender table found.")
            break

        rows = table.find_all("tr")[1:]  # Skip header
        if not rows:
            print(" No tenders found on this page.")
            break

        for row in rows:
            if len(tenders) >= target_count:
                break
            tender = extract_tender_from_row(row, driver)
            if tender:
                tenders.append(tender)

        page += 1

    return tenders

def save_tenders_to_json(tenders, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(tenders, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    print("Target: 20 tenders")
    unit_name = "Tandur"
    unit_id = unit_map[unit_name]
    target_count = 20

    driver = start_browser()
    try:
        tenders = scrape_tenders_with_pagination(driver, unit_id, target_count)
        save_tenders_to_json(tenders, "cci_tenders.json")
        print(f"\n Scraped {len(tenders)} tenders and saved to cci_tenders.json")
    finally:
        driver.quit()
