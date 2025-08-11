from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import json
import time

# Setup Selenium with headless Chrome
options = Options()
options.add_argument('--headless')  # Remove this line to see the browser
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Load the NFL Tender website
driver.get("https://tenders.nfl.co.in/tender_new.php")
time.sleep(3)  # Wait for content to load

# Locate the table rows (excluding header)
rows = driver.find_elements(By.XPATH, "//table//tr[position()>1]")

tenders = []
for row in rows:
    cols = row.find_elements(By.TAG_NAME, "td")
    if len(cols) >= 6:
        # Try to get <a> inside description column (cols[2])
        link_element = cols[2].find_element(By.TAG_NAME, "a")
        link_href = link_element.get_attribute("href") if link_element else ""

        tender = {
            "upload_date": cols[0].text.strip(),
            "tender_no": cols[1].text.strip(),
            "description": cols[2].text.strip(),
            "unit": cols[3].text.strip(),
            "due_date": cols[4].text.strip(),
            "remark": cols[5].text.strip(),
            "link": link_href
        }
        tenders.append(tender)

# Save to JSON file
with open("C:/Users/User/Desktop/Tender Final/nfl tenders/nfl_tenders.json", "w", encoding="utf-8") as f:
    json.dump(tenders, f, indent=4, ensure_ascii=False)

driver.quit()
print(" Scraped successfully and saved to nfl_tenders.json")
