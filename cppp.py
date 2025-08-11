import requests
from bs4 import BeautifulSoup
import json
import time
import random

def scrape_eprocure_latest_mmp(limit=15):  # 🔧 Hardcoded limit to 15
    base_url = "https://eprocure.gov.in/cppp/latestactivetendersnew/cpppdata"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    all_tenders = []
    failed_pages = []
    page = 1

    while len(all_tenders) < limit:
        print(f"Fetching page {page}...")

        try:
            response = requests.get(base_url + str(page), headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f" Error fetching page {page}: {e}")
            failed_pages.append(page)
            print(" Waiting for 5 seconds and moving to next page...")
            time.sleep(5)
            page += 1
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.find_all("tr", style=lambda value: value and "border-bottom" in value)

        if not rows:
            print(f" No more tenders found on page {page}. Ending.")
            break

        for row in rows:
            if len(all_tenders) >= limit:
                break

            cols = row.find_all("td")

            serial_no = cols[0].get_text(strip=True) if len(cols) > 0 else None
            start_date = cols[1].get_text(strip=True) if len(cols) > 1 else None
            end_date = cols[2].get_text(strip=True) if len(cols) > 2 else None
            open_date = cols[3].get_text(strip=True) if len(cols) > 3 else None

            title_text = None
            link = None
            if len(cols) > 4:
                title_cell = cols[4]
                title_link = title_cell.find("a")
                title_text = title_link.get_text(strip=True) if title_link else title_cell.get_text(strip=True)
                link = title_link['href'] if title_link else None

            location = cols[5].get_text(strip=True) if len(cols) > 5 else None
            department = cols[6].get_text(strip=True) if len(cols) > 6 else None

            tender = {
                "serial_no": serial_no,
                "start_date": start_date,
                "end_date": end_date,
                "open_date": open_date,
                "title": title_text,
                "link": link,
                "location": location,
                "department": department
            }

            all_tenders.append(tender)

        page += 1
        time.sleep(random.uniform(1, 2))

    # Save limited tenders
    with open("C:/Users/User/Desktop/Tender Final/cppp tenders/cppp.json", "w", encoding="utf-8") as f:
        json.dump(all_tenders, f, indent=2, ensure_ascii=False)

    print(f"\n Scraped {len(all_tenders)} tenders and saved to 'cppp.json'.")

    if failed_pages:
        with open("C:/Users/User/Desktop/Tender Final/cppp tenders/failed_pages.json", "w", encoding="utf-8") as f:
            json.dump(failed_pages, f, indent=2)
        print(f" Saved {len(failed_pages)} failed pages to 'failed_pages.json'.")
    else:
        print(" No failed pages. All good!")

if __name__ == "__main__":
    print(" Starting to scrape 15 tenders from CPPP portal...")
    scrape_eprocure_latest_mmp()
