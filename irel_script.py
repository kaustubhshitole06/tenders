from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

# Setup Chrome remote debugging
options = Options()
options.debugger_address = "127.0.0.1:9222"
driver = webdriver.Chrome(service=Service(), options=options)

url = "https://www.irel.co.in/tender-information"
driver.get(url)

wait = WebDriverWait(driver, 20)
data = []

def scrape_current_page():
    table = wait.until(EC.presence_of_element_located((By.ID, "new-tender")))
    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 8:
            try:
                tender = {
                    "Tender Reference Number": cols[1].text.strip(),
                    "Tender Title": cols[2].text.strip(),
                    "Unit Name": cols[3].text.strip(),
                    "Tender Description": cols[4].text.strip(),
                    "Start Date": cols[5].text.strip(),
                    "End Date": cols[6].text.strip(),
                    "View Link": cols[7].find_element(By.TAG_NAME, "a").get_attribute("href") if cols[7].find_elements(By.TAG_NAME, "a") else None
                }
                data.append(tender)
            except Exception as e:
                print(f" Error parsing row: {e}")

# Start pagination scraping
page = 1
while True:
    print(f" Scraping page {page}...")
    scrape_current_page()

    try:
        # Scroll pagination into view before clicking
        pagination = wait.until(EC.presence_of_element_located((By.ID, "new-tender_paginate")))
        driver.execute_script("arguments[0].scrollIntoView(true);", pagination)
        time.sleep(1)

        # Get the Next button
        next_button = pagination.find_element(By.LINK_TEXT, "Next")
        class_attr = next_button.get_attribute("class")

        if "disabled" in class_attr:
            print(" Reached last page.")
            break

        # Use JavaScript click to avoid interception
        driver.execute_script("arguments[0].click();", next_button)
        time.sleep(2)
        page += 1

    except Exception as e:
        print(" Pagination failed or last page reached:", e)
        break

# Save the results to a JSON file
with open("C:/Users/User/Desktop/Tender Final/irel tenders/irel_all_pages_tenders.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"\n Done. {len(data)} tenders saved to 'irel_all_pages_tenders.json'.")
# driver.quit()  # optional
