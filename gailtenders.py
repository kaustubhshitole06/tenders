import os
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

# Hardcoded settings
NUM_TENDERS = 10
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "gail_tenders.json")

# Setup Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 10)

print(f"\nTarget: {NUM_TENDERS} tenders\n")

# Directly load the correct page with actual data
driver.get("https://gailtenders.in/Gailtenders/Home.asp")
time.sleep(3)  # Allow JavaScript to fully render content

tenders = []
page = 1

while len(tenders) < NUM_TENDERS:
    print(f" Processing page {page}...")

    soup = BeautifulSoup(driver.page_source, "html.parser")
    links = soup.select("a.textbox2link")

    if not links:
        print(" No tenders found on this page, stopping...\n")
        break

    for link in links:
        if len(tenders) >= NUM_TENDERS:
            break

        tender = {
            "title": link.text.strip(),
            "url": "https://gailtenders.in/Gailtenders/Home.asp" + link.get("href", "").strip()
        }
        tenders.append(tender)

    # Check for next page
    next_link = soup.find("a", string="Next >>")
    if next_link:
        next_url = "https://gailtenders.in/Gailtenders/Home.asp" + next_link.get("href")
        driver.get(next_url)
        page += 1
        time.sleep(2)
    else:
        break

driver.quit()

# Save results
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(tenders, f, indent=2)

print(f" Scraped {len(tenders)} tenders and saved to {os.path.basename(OUTPUT_FILE)} ")
