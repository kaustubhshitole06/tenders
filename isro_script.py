import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Set up Selenium WebDriver options
options = Options()
options.add_argument('--headless')  # Run in headless mode
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')

# Initialize WebDriver
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

# Hardcoded tender count
target_count = 10
print(f"\n Target: {target_count} tenders")

def get_tender_rows(driver):
    try:
        wait.until(EC.presence_of_element_located((By.ID, "tenderListTable")))
        time.sleep(2)
        return driver.find_elements(By.CSS_SELECTOR, "#tenderListTable tbody tr")
    except:
        return []

def extract_tender_data(row):
    try:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 6:
            tender_data = {
                "Tender_ID": cols[0].text.strip(),
                "Department": cols[1].text.strip(),
                "Description": cols[2].text.strip(),
                "Submission_Deadline": cols[3].text.strip(),
                "Opening_Date": cols[4].text.strip(),
            }

            if len(cols) > 5:
                actions_cell = cols[5]
                try:
                    pdf_link = actions_cell.find_element(By.CSS_SELECTOR, "a[href*='/viewDocumentPT']")
                    tender_data["Tender_Document_Link"] = pdf_link.get_attribute("href")
                    tender_data["Tender_Document_Text"] = pdf_link.text.strip()
                except:
                    tender_data["Tender_Document_Link"] = ""
                    tender_data["Tender_Document_Text"] = ""

                try:
                    view_link = actions_cell.find_element(By.CSS_SELECTOR, "a[href*='/homeTenderView']")
                    tender_data["Tender_View_Link"] = view_link.get_attribute("href")
                    tender_data["Tender_View_Text"] = view_link.text.strip()
                except:
                    tender_data["Tender_View_Link"] = ""
                    tender_data["Tender_View_Text"] = ""

                try:
                    all_links = actions_cell.find_elements(By.TAG_NAME, "a")
                    tender_data["All_Action_Links"] = [{
                        "href": link.get_attribute("href"),
                        "text": link.text.strip(),
                        "title": link.get_attribute("title") or "",
                        "target": link.get_attribute("target") or ""
                    } for link in all_links]
                except:
                    tender_data["All_Action_Links"] = []

            for i, col in enumerate(cols[6:], start=6):
                tender_data[f"Additional_Column_{i+1}"] = col.text.strip()

            return tender_data
    except Exception as e:
        print(f"    Error extracting tender data: {e}")
        return None

    return None

def go_to_next_page(driver):
    try:
        active_page = driver.find_element(By.CSS_SELECTOR, "a.current")
        current_page_num = int(active_page.text.strip())
        next_page_num = current_page_num + 1

        next_page_link = driver.find_element(By.CSS_SELECTOR, f"a[data-dt-idx='{next_page_num}']")
        if next_page_link and next_page_link.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView(true);", next_page_link)
            time.sleep(1)
            next_page_link.click()
            print(f"    Clicked page {next_page_num}")
            time.sleep(3)
            return True
    except NoSuchElementException:
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "a.next:not(.disabled)")
            if next_button and next_button.is_displayed():
                next_button.click()
                print("  Clicked 'Next' button")
                time.sleep(3)
                return True
        except:
            pass

        print("  No next page available")
        return False
    except Exception as e:
        print(f" Error navigating to next page: {e}")
        return False

    return False

# Open the ISRO eProcurement website
driver.get("https://eproc.isro.gov.in/home.html")
time.sleep(5)

# Try navigating to tender section
try:
    tender_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Tender")
    tender_link.click()
    time.sleep(3)
except:
    print(" Could not find tender link, continuing with current page...")

scraped_tenders = []
scraped_count = 0
current_page = 1

while scraped_count < target_count:
    print(f"\n Processing page {current_page}...")
    tender_rows = get_tender_rows(driver)
    page_tender_count = len(tender_rows)
    print(f"Found {page_tender_count} tenders on page {current_page}")

    if page_tender_count == 0:
        print(" No tenders found on this page, stopping...")
        break

    tenders_to_process = min(page_tender_count, target_count - scraped_count)

    for i in range(tenders_to_process):
        print(f"\n Processing tender {scraped_count + 1}/{target_count} (Page {current_page}, Item {i + 1})...")
        tender_rows = get_tender_rows(driver)

        if i >= len(tender_rows):
            print(f" Tender index {i} out of range, breaking...")
            break

        tender_data = extract_tender_data(tender_rows[i])

        if tender_data:
            scraped_tenders.append(tender_data)
            scraped_count += 1
            print(f" Scraped {scraped_count}/{target_count}: {tender_data.get('Tender_ID', 'No ID')} - {tender_data.get('Description', '')[:50]}...")
        else:
            print(f" Could not extract data for tender {i + 1}")

        if scraped_count >= target_count:
            break

    if scraped_count < target_count:
        print(f"\n Scraped {scraped_count}/{target_count} tenders. Need more, trying next page...")
        if go_to_next_page(driver):
            current_page += 1
            time.sleep(2)
        else:
            print(" No more pages available, stopping...")
            break
    else:
        print(f"\n Target of {target_count} tenders reached!")
        break

# Save scraped tenders
output_path = 'C:/Users/User/Desktop/Tender Final/isro tenders/isro_eproc_links.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(scraped_tenders, f, ensure_ascii=False, indent=2)

print(f"\n Done! Scraped {len(scraped_tenders)} tenders and saved to '{output_path}'")

# Close browser
driver.quit()
