from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import json
import time

def get_driver():
    options = Options()
    options.add_experimental_option("debuggerAddress", "localhost:9222")
    driver = webdriver.Chrome(options=options)
    return driver

def scrape_goa_shipyard():
    driver = get_driver()
    driver.get("https://goashipyard.in/notice-board/tender/open-tenders/")
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    sections = soup.find_all("div", class_="w-tabs-section")

    final_data = {}

    for section in sections:
        title_tag = section.find("h5", class_="w-tabs-section-title")
        if not title_tag:
            continue
        section_name = title_tag.get_text(strip=True)

        table = section.find("table")
        if not table:
            continue

        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        body_rows = table.find_all("tr")[1:]
        section_data = []

        for row in body_rows:
            cells = row.find_all("td")
            if not cells:
                continue
            row_data = {}
            for i, cell in enumerate(cells):
                text = cell.get_text(" ", strip=True)
                link = cell.find("a")
                if link and link.has_attr("href"):
                    text += f" ({link['href']})"
                row_data[headers[i]] = text
            section_data.append(row_data)

        if section_data:
            final_data[section_name] = section_data

    driver.quit()

    with open("C:/Users/User/Desktop/Tender Final/goa shipyard tenders/goa_shipyard_tenders.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print("Scraping complete. Data saved in 'goa_shipyard_tenders.json'.")

scrape_goa_shipyard()
