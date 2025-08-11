import requests
from bs4 import BeautifulSoup
import json

URL = "https://www.gmdcltd.com/current-tenders/"
response = requests.get(URL)
soup = BeautifulSoup(response.content, "html.parser")

tender_divs = soup.find_all("div", class_="col-lg-12 tender-box")

all_tenders = []

for tender in tender_divs:
    tender_data = {
        "tender_no": "",
        "details": "",
        "last_date_of_submission": "",
        "pre_bid_meeting": "",
        "meeting_id": "",
        "passcode": "",
        "documents": []
    }

    # Step through all <h3> tags
    h3_tags = tender.find_all("h3")
    for h3 in h3_tags:
        label = h3.get_text(strip=True).lower()
        p_tag = h3.find_next_sibling("p")
        value = p_tag.get_text(strip=True) if p_tag else ""

        if "tender no" in label or "rfp no" in label:
            tender_data["tender_no"] = value
        elif "details" in label:
            tender_data["details"] = value
        elif "last date" in label:
            tender_data["last_date_of_submission"] = value
        elif "pre bid" in label:
            tender_data["pre_bid_meeting"] = value
        elif "meeting id" in label:
            tender_data["meeting_id"] = value
        elif "passcode" in label:
            tender_data["passcode"] = value

    # PDF/document links
    for a in tender.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith((".pdf", ".docx", ".doc")):
            name = a.get_text(strip=True)
            if not name:
                # Try to find document name inside nested divs
                nested_name = a.find("div", class_="report-margin-zero")
                name = nested_name.get_text(strip=True) if nested_name else "Document"
            if not href.startswith("http"):
                href = "https://www.gmdcltd.com" + href
            tender_data["documents"].append({
                "name": name,
                "url": href
            })

    all_tenders.append(tender_data)

# Save to JSON
with open("C:/Users/User/Desktop/Tender Final/gmdc tenders/gmdc_tenders.json", "w", encoding="utf-8") as f:
    json.dump(all_tenders, f, ensure_ascii=False, indent=4)

print("Tenders data saved to gmdc_tenders.json")
