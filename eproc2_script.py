from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time

# Setup Chrome with debugging port
options = webdriver.ChromeOptions()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=options)

# Hardcoded settings
tab_name = "Latest Tenders"
tab_id = "#latestTenders"
table_selector = (By.CSS_SELECTOR, "#latestTenders table")
target_count = 15

print(f" Scraping '{tab_name}' tab... Target: {target_count} tenders")

def load_more_tenders(driver):
    try:
        more_button = driver.find_element(By.CSS_SELECTOR, 'a[ng-click="clickForMoreTender()"]')
        if more_button and more_button.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView(true);", more_button)
            time.sleep(1)
            more_button.click()
            print("  Clicked 'More...' button to load additional tenders")
            time.sleep(3)
            return True
    except NoSuchElementException:
        print("  No 'More...' button found - no more tenders to load")
    except Exception as e:
        print(f" Error clicking 'More...' button: {e}")
    return False

def get_current_tender_count(driver, tab_id):
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, f"{tab_id} table tbody tr")
        return len(rows)
    except:
        return 0

try:
    driver.get("https://eproc2.bihar.gov.in/EPSV2Web/openarea/tenderListingPage.action")
    time.sleep(3)

    tab_element = driver.find_element(By.CSS_SELECTOR, f"a[href='{tab_id}']")
    tab_element.click()
    time.sleep(10)

    WebDriverWait(driver, 15).until(EC.presence_of_element_located(table_selector))

    tenders = []
    processed_count = 0

    while processed_count < target_count:
        rows = driver.find_elements(By.CSS_SELECTOR, f"{tab_id} table tbody tr")
        current_total = len(rows)

        print(f"Currently loaded: {current_total} tenders, Target: {target_count}, Processed: {processed_count}")

        if current_total <= processed_count:
            print(" Need more tenders, clicking 'More...' button...")
            if not load_more_tenders(driver):
                print(" Cannot load more tenders, processing available ones...")
                break
            continue

        start_index = processed_count
        end_index = min(current_total, target_count)

        for index in range(start_index, end_index):
            if index >= len(rows):
                print(f" Row index {index} out of range, refreshing row list...")
                rows = driver.find_elements(By.CSS_SELECTOR, f"{tab_id} table tbody tr")
                if index >= len(rows):
                    break

            row = rows[index]
            print(f"\n Processing tender {index + 1}/{target_count}...")

            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 6:
                tender = {
                    "SL No.": cols[0].text.strip(),
                    "Tender ID": cols[1].text.strip(),
                    "Description": cols[2].text.strip(),
                    "Reference No.": cols[3].text.strip(),
                    "Department": cols[4].text.strip(),
                    "End Date": cols[5].text.strip(),
                }

                print(f" Extracted basic info for tender {index + 1}")
                tenders.append(tender)
                processed_count += 1
                time.sleep(1)

                if processed_count >= target_count:
                    break

        if processed_count < target_count and processed_count >= current_total:
            print(" Processed all current tenders, trying to load more...")
            if not load_more_tenders(driver):
                print(" No more tenders available")
                break

    with open("C:/Users/User/Desktop/Tender Final/eproc2 tenders/tenders_output.json", "w", encoding='utf-8') as f:
        json.dump(tenders, f, indent=4, ensure_ascii=False)

    print(f"\n {len(tenders)} tenders scraped and saved to 'tenders_output.json'.")

except Exception as e:
    print(f"\nError scraping tenders: {e}")
finally:
    pass
    # driver.quit()
