import re
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Connect to existing Chrome
def connect_to_existing_chrome():
    options = Options()
    options.debugger_address = "localhost:9222"
    return webdriver.Chrome(options=options)

# Parse rows from tender table
def parse_tender_rows(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    return soup.find_all("tr", height="20")

# Extract tender detail link
def extract_onclick_url(col):
    link_tag = col.find("a")
    if link_tag:
        onclick = link_tag.get("onclick", "")
        if "postRequestNewWindow" in onclick:
            start = onclick.find("('") + 2
            end = onclick.find("'", start)
            return "https://www.ireps.gov.in" + onclick[start:end]
    return None

# Wait for URL to change
def wait_for_page_load(driver, timeout=10):
    old_url = driver.current_url
    try:
        WebDriverWait(driver, timeout).until(lambda d: d.current_url != old_url)
    except:
        pass

# Wait until tender details appear
def wait_for_detail_content(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "//td[contains(text(), 'Tender No.')]"))
        )
    except:
        pass

# Safe text extraction
def safe_get_text(driver, by, value):
    try:
        return driver.find_element(by, value).text.strip()
    except:
        return ""

# Extract all tender fields
def extract_tender_details(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    details = {}

    try:
        top_table = soup.select_one("table.advSearch")
        rows = top_table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 6:
                details["Tender No."] = cols[1].text.strip()
                details["Dept/Rly"] = cols[3].text.strip()
                details["Closing Date/Time"] = cols[5].text.strip()
            elif len(cols) >= 4 and "Tender Title:" in cols[0].text:
                details["Tender Title"] = cols[1].text.strip()
                details["Tender Type"] = cols[3].text.strip()
    except Exception as e:
        print(f" Top fields error: {e}")

    details["Tender Status"] = safe_get_text(driver, By.XPATH, "//td[contains(text(), 'Tender Status')]/following-sibling::td")

    # Attached documents
    documents = []
    try:
        attach_table = soup.find('table', id="attach_docs")
        if attach_table:
            doc_rows = attach_table.find_all('tr')[1:]
            for r in doc_rows:
                cols = r.find_all('td')
                if len(cols) >= 3:
                    file_name = cols[1].text.strip()
                    desc = cols[2].text.strip()
                    link_tag = cols[1].find('a')
                    pdf_link = ""
                    if link_tag:
                        onclick = link_tag.get('onclick', '')
                        start = onclick.find("('") + 2
                        end = onclick.find("')", start)
                        pdf_link = "https://www.ireps.gov.in" + onclick[start:end]
                    documents.append({
                        "File Name": file_name,
                        "Description": desc,
                        "PDF Link": pdf_link
                    })
    except Exception as e:
        print(f"⚠ Document extraction error: {e}")
    details["Documents Attached"] = documents

    # Corrigenda
    corrigenda = []
    try:
        corri_table = soup.find('table', id="tempTable")
        if corri_table:
            corr_rows = corri_table.find_all('tr')[1:]
            for r in corr_rows:
                cols = r.find_all('td')
                if len(cols) >= 3:
                    name = cols[1].text.strip()
                    date = cols[2].text.strip()
                    corrigenda.append({
                        "Name": name,
                        "Date/Time": date
                    })
    except Exception as e:
        print(f" Corrigenda error: {e}")
    details["Corrigenda"] = corrigenda

    # Main Tender PDF
    try:
        scripts = soup.find_all("script")
        for script in scripts:
            if "downloadtenderDoc" in script.text:
                match = re.search(r"var\s+url\s*=\s*'([^']+)'", script.text)
                if match:
                    main_pdf_url = "https://www.ireps.gov.in" + match.group(1)
                    details["Main Tender PDF"] = main_pdf_url
                    break
    except Exception as e:
        print(f" Main PDF error: {e}")

    return details

# Scraper for current tender page
def scrape_current_page_tenders(driver, failed_tenders, max_count=10):
    tenders = []
    rows = parse_tender_rows(driver)
    for row in rows:
        if len(tenders) >= max_count:
            break
        cols = row.find_all("td")
        if len(cols) < 8:
            continue

        department = cols[0].get_text(strip=True)
        tender_id = cols[1].get_text(strip=True)
        description = cols[2].get_text(strip=True)
        status = cols[3].get_text(strip=True)
        due_date = cols[5].get_text(strip=True)
        published_on = cols[6].get_text(strip=True)
        detail_url = extract_onclick_url(cols[7])

        tender_data = {
            "department": department,
            "tender_id": tender_id,
            "description": description,
            "status": status,
            "due_date": due_date,
            "published_on": published_on,
            "link": detail_url
        }

        if detail_url:
            try:
                driver.get(detail_url)
                wait_for_page_load(driver)
                wait_for_detail_content(driver)
                time.sleep(1)

                tender_details = extract_tender_details(driver)
                tender_data.update(tender_details)

                if (not tender_details.get("Tender No.") or
                    not tender_details.get("Dept/Rly") or
                    not tender_details.get("Closing Date/Time")):
                    failed_tenders.append(tender_id)

                driver.back()
                wait_for_page_load(driver)
                time.sleep(2)

            except Exception as e:
                print(f" Failed tender {tender_id}: {e}")
                failed_tenders.append(tender_id)

        tenders.append(tender_data)
    return tenders

# Main runner
def main():
    driver = connect_to_existing_chrome()

    #  Comment out these lines if you're already manually on the "All Active Tenders" page
    # driver.get("https://www.ireps.gov.in/epsn/anonymSearch.do")
    # WebDriverWait(driver, 10).until(
    #     EC.element_to_be_clickable((By.ID, "activeTenderId"))
    # ).click()
    # time.sleep(5)

    all_tenders = []
    failed_tenders = []

    print(" Scraping up tenders from current page...")
    tenders_page1 = scrape_current_page_tenders(driver, failed_tenders, max_count=10)
    all_tenders.extend(tenders_page1)

    with open("C:/Users/User/Desktop/Tender Final/ireps tenders/tenders_ireps_full_pages.json", "w", encoding="utf-8") as f:
        json.dump(all_tenders, f, indent=2, ensure_ascii=False)

    if failed_tenders:
        with open("C:/Users/User/Desktop/Tender Final/ireps tenders/failed_tenders.json", "w", encoding="utf-8") as f:
            json.dump(failed_tenders, f, indent=2)
        print(f" {len(failed_tenders)} tenders had missing fields.")
    else:
        print(" All tenders extracted successfully!")

    print(f"Done. Total {len(all_tenders)} tenders saved.")

main()