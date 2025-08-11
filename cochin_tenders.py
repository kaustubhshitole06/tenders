from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import time

# Setup headless Chrome
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Load CSL tender page
driver.get("https://cochinshipyard.in/Tender")

# Wait until table loads
WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
time.sleep(5)  # allow extra time for JS

# Extract tender rows
rows = driver.find_elements(By.XPATH, "//table//tr")
tenders = []

# Parse rows (skip header)
for row in rows[1:]:
    cols = row.find_elements(By.TAG_NAME, "td")
    if len(cols) >= 4:
        # Get PDF link if available
        try:
            pdf_link = cols[1].find_element(By.TAG_NAME, "a").get_attribute("href")
        except:
            pdf_link = ""

        tender = {
            "enquiry_no": cols[0].text.strip(),
            "item_description": cols[1].text.strip(),
            "pdf_link": pdf_link,
            "corrigendum": cols[2].text.strip(),
            "last_date_for_receipt": cols[-2].text.strip(),
            "tender_opening_date": cols[-1].text.strip()
        }
        tenders.append(tender)

driver.quit()

# Save JSON
with open("cochin_tenders.json", "w", encoding="utf-8") as f:
    json.dump({"tenders": tenders}, f, indent=2, ensure_ascii=False)

print(f" Scraped {len(tenders)} tenders and saved to cochin_tenders.json")
