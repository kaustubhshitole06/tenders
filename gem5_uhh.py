import requests
import json
import time
import datetime
import fitz  # PyMuPDF
import os
import re
import pandas as pd
from difflib import get_close_matches # Will not be used for exact matching, but keep for now if other parts might hypothetically use it
import random # For jitter in backoff
from typing import List, Dict, Any, Optional, Set # For type hinting

# --- Configuration & Constants ---
PDF_DOWNLOAD_TIMEOUT = 60  # PDF download timeout
API_REQUEST_TIMEOUT = 90   # API request timeout
MAX_RETRIES = 3            # Number of retries for network operations
INITIAL_BACKOFF_SECONDS = 2.0 # Initial wait time for retries

# Load the district list CSV
try:
    districts_df = pd.read_excel("C:/Users/User/Desktop/Tender Final/gem tenders/indian_districts_cleaned_final.xlsx")
    DISTRICTS: List[str] = districts_df['District'].tolist()
    LOWERCASE_DISTRICTS: List[str] = [d.lower() for d in DISTRICTS]
except FileNotFoundError:
    print(" Error: 'indian_districts_cleaned_final.xlsx' not found. District matching will be unavailable.")
    DISTRICTS = []
    LOWERCASE_DISTRICTS = []
except KeyError:
    print(" Error: 'District' column not found in 'indian_districts_cleaned_final.xlsx'. District matching will be unavailable.")
    DISTRICTS = []
    LOWERCASE_DISTRICTS = []


# Replace these before running
csrf_token = "sda" # Placeholder - REPLACE WITH YOUR ACTUAL TOKEN
ci_session = "sdb" # Placeholder - REPLACE WITH YOUR ACTUAL TOKEN

# --- Helper Functions ---

def generate_download_url(bid_number: str, bid_id: str) -> Optional[str]:
    if bid_id and bid_number and "/R/" in bid_number:
        return f"https://bidplus.gem.gov.in/showradocumentPdf/{bid_id}"
    elif bid_id:
        return f"https://bidplus.gem.gov.in/showbidDocument/{bid_id}"
    return None

def extract_bid_data(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    docs = api_response.get('response', {}).get('response', {}).get('docs', [])
    extracted_data: List[Dict[str, Any]] = []
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    for bid in docs:
        bid_id_list = bid.get("b_id", [])
        bid_id = bid_id_list[0] if bid_id_list else None
        
        bid_number_list = bid.get("b_bid_number", [])
        bid_number = bid_number_list[0] if bid_number_list else ""

        end_date_raw_list = bid.get("final_end_date_sort", [])
        end_date_raw = end_date_raw_list[0] if end_date_raw_list else None

        if bid_id and end_date_raw and isinstance(end_date_raw, str):
            try:
                if end_date_raw.endswith('Z'):
                    bid_end_datetime = datetime.datetime.fromisoformat(end_date_raw[:-1] + '+00:00')
                else:
                    # print(f" Skipping bid {bid_id} due to unexpected date format: {end_date_raw}")
                    continue
                
                if bid_end_datetime < now_utc:
                    continue

                category_list = bid.get("b_category_name", [])
                quantity_list = bid.get("b_total_quantity", [])
                start_date_list = bid.get("final_start_date_sort", [])
                ministry_list = bid.get("ba_official_details_minName", [])
                department_list = bid.get("ba_official_details_deptName", [])

                bid_info = {
                    "bid_id": bid_id,
                    "bid_number": bid_number,
                    "category": category_list[0] if category_list else None,
                    "quantity": quantity_list[0] if quantity_list else None,
                    "start_date": start_date_list[0] if start_date_list else None,
                    "end_date": end_date_raw,
                    "ministry": ministry_list[0] if ministry_list else None,
                    "department": department_list[0] if department_list else None,
                    "bid_url": f"https://bidplus.gem.gov.in/bidlists?bid_no={bid_number}" if bid_number else None,
                    "download_url": generate_download_url(bid_number, bid_id)
                }
                extracted_data.append(bid_info)
            except ValueError:
                # print(f" Skipping bid {bid_id} due to date parsing error for: {end_date_raw}")
                continue
            except Exception as e: 
                # print(f" Error processing bid {bid_id}: {e}")
                continue
    return extracted_data

def download_pdf_with_retries(url: str, 
                              filename: str, 
                              timeout: int = PDF_DOWNLOAD_TIMEOUT, 
                              max_retries: int = MAX_RETRIES, 
                              initial_backoff: float = INITIAL_BACKOFF_SECONDS) -> Optional[str]:
    """
    Downloads a PDF from a given URL with retries and exponential backoff.
    Returns the filename if successful, None otherwise.
    """
    if not url:
        print("Download URL is empty. Cannot download.")
        return None
        
    file_directory = os.path.dirname(filename)
    if file_directory: 
        os.makedirs(file_directory, exist_ok=True)

    for attempt in range(max_retries):
        try:
            print(f" Attempt {attempt + 1}/{max_retries} to download: {url}")
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f" Successfully downloaded {url} to {filename}")
            return filename
            
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed for {url} due to: {type(e).__name__} - {e}")
            if attempt + 1 == max_retries:
                print(f" Max retries reached for {url}. Download ultimately failed.")
            else:
                wait_time = initial_backoff * (2 ** attempt) + random.uniform(0, 0.1 * initial_backoff * (2**attempt))
                print(f"   Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        except requests.exceptions.RequestException as e: 
            print(f" Failed to download {url} (RequestException): {e}. This error will not be retried.")
            break 
        except IOError as e:
            print(f" Failed to write PDF {filename} for {url} (IOError): {e}")
            break 
        except Exception as e: 
            print(f" An unexpected error occurred during download/write for {url} on attempt {attempt + 1}: {e}")
            break 

    if os.path.exists(filename):
        try:
            os.remove(filename)
        except OSError as e_remove:
            print(f" Failed to remove file {filename} after failed attempts: {e_remove}")
    return None

def extract_structured_pdf_data(pdf_path: str) -> Dict[str, List[Any]]:
    structured_text_data: List[Dict[str, Any]] = []
    all_hyperlinks: List[Dict[str, Any]] = []
    try:
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc, start=1):
                blocks = page.get_text("dict").get("blocks", [])
                page_lines: List[str] = []
                for block in blocks:
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            line_text = " ".join([span.get("text", "") for span in line.get("spans", [])]).strip()
                            if line_text:
                                page_lines.append(line_text)
                if page_lines:
                    structured_text_data.append({"page": page_num, "content": page_lines})

                links = page.get_links()
                for link in links:
                    uri = link.get("uri")
                    if uri:
                        all_hyperlinks.append({"page": page_num, "uri": uri})
        return {"structured_text": structured_text_data, "hyperlinks": all_hyperlinks}
    except RuntimeError as e: # Catching common PyMuPDF errors
        print(f" Failed to parse PDF {pdf_path} (PyMuPDF RuntimeError): {e}")
    except Exception as e:
        print(f" Failed to parse PDF {pdf_path} (Unexpected Error): {e}")
    return {"structured_text": [], "hyperlinks": []}

def extract_address_from_showbid_pdf(url: str, temp_filename: str, timeout: int = PDF_DOWNLOAD_TIMEOUT) -> Dict[str, Any]:
    print(f"\n Preparing to extract address details from PDF: {url}")
    
    downloaded_pdf_path = download_pdf_with_retries(url, temp_filename, timeout=timeout)

    if not downloaded_pdf_path:
        return {
            "matched_city": "Failed to download PDF for district extraction",
            "hyperlinks": []
        }
    
    path_to_clean = downloaded_pdf_path 
    
    try:
        found_city: Optional[str] = None
        all_extracted_links: List[Dict[str, Any]] = []
        valid_label_keywords: Set[str] = {"document", "specification", "details", "file", "certificate", "drawing", "report"}

        with fitz.open(downloaded_pdf_path) as doc:
            full_text = ""
            print(f" Scanning {len(doc)} pages in {downloaded_pdf_path}...")

            for page_num, page in enumerate(doc, start=1):
                full_text += page.get_text() + "\n"
                blocks = page.get_text("dict").get("blocks", [])
                text_blocks_with_bbox: List[Dict[str, Any]] = []
                for block_item in blocks:
                    if block_item.get("type") == 0:
                        for line_item in block_item.get("lines", []):
                            for span_item in line_item.get("spans", []):
                                text_blocks_with_bbox.append({
                                    "text": span_item.get("text", "").strip(),
                                    "bbox": span_item.get("bbox")
                                })
                page_links = page.get_links()
                for link_info in page_links:
                    uri = link_info.get("uri")
                    rect = link_info.get("from")
                    if uri and rect:
                        link_text_from_rect = page.get_textbox(rect).strip()
                        label_text = ""
                        x0_link, y0_link, _, _ = rect
                        for tb_block in text_blocks_with_bbox:
                            if tb_block.get("bbox"):
                                _, by0_text, bx1_text, _ = tb_block["bbox"]
                                if abs(by0_text - y0_link) < 10 and bx1_text < x0_link:
                                    label_text = tb_block["text"]
                                    break
                        label_text_lower = label_text.lower()
                        is_valid = any(kw in label_text_lower for kw in valid_label_keywords)
                        all_extracted_links.append({
                            "page": page_num, "uri": uri,
                            "text": label_text if is_valid else link_text_from_rect
                        })
        
        # --- City Matching (Changed to Exact Match) ---
        if DISTRICTS and LOWERCASE_DISTRICTS: 
            print(" Starting token-based exact district matching in PDF content...")
            for line_text in full_text.splitlines():
                tokens = re.findall(r'\b[a-zA-Z]{3,}\b', line_text)
                for token in tokens:
                    token_lower = token.lower()
                    if token_lower in LOWERCASE_DISTRICTS: # Direct check for exact match
                        matched_idx = LOWERCASE_DISTRICTS.index(token_lower)
                        found_city = DISTRICTS[matched_idx] 
                        print(f" Exact match found in PDF content: '{token}' '{found_city}'")
                        break 
                if found_city:
                    break 
        else:
            print(" District lists (DISTRICTS/LOWERCASE_DISTRICTS) not available for matching.")
            
        return {
            "matched_city": found_city if found_city else "District not found (Exact Match)",
            "hyperlinks": all_extracted_links
        }

    except RuntimeError as e: 
        print(f" Error parsing PDF {downloaded_pdf_path} (PyMuPDF RuntimeError): {e}")
    except Exception as e:
        print(f" Error extracting data from PDF {url} (processing stage of {downloaded_pdf_path}): {e}")
    finally:
        if path_to_clean and os.path.exists(path_to_clean):
            try:
                os.remove(path_to_clean)
            except OSError as e_remove:
                print(f" Failed to remove temporary address PDF {path_to_clean}: {e_remove}")
    
    return {
        "matched_city": "Failed to extract district from PDF content",
        "hyperlinks": []
    }

def fetch_and_scrape_top_bids(target_bid_count: int = 20, 
                              stop_bid_id: Optional[str] = None, 
                              stop_bid_number: Optional[str] = None):
    api_url = "https://bidplus.gem.gov.in/all-bids-data"
    headers = {
        "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://bidplus.gem.gov.in", "Referer": "https://bidplus.gem.gov.in/all-bids",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    cookies = {"csrf_gem_cookie": csrf_token, "ci_session": ci_session}

    scraped_data: List[Dict[str, Any]] = []
    current_page = 1
    pdf_dir = "pdfs"
    os.makedirs(pdf_dir, exist_ok=True)
    print(f"\n Collecting up to {target_bid_count} active bids...\n")

    while len(scraped_data) < target_bid_count:
        print(f" Fetching page {current_page} for bid listings...")
        payload_data = {
            "page": current_page, "param": {"searchBid": "", "searchType": "fullText"},
            "filter": {"bidStatusType": "ongoing_bids", "byType": "all", "sort": "Bid-Start-Date-Latest"}
        }
        json_payload = {"payload": json.dumps(payload_data), "csrf_bd_gem_nk": csrf_token}

        api_response_content = None
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(api_url, headers=headers, cookies=cookies, data=json_payload, timeout=API_REQUEST_TIMEOUT)
                response.raise_for_status()
                api_response_content = response.json()
                break 
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                print(f" API Call Attempt {attempt + 1}/{MAX_RETRIES} failed for page {current_page}: {type(e).__name__} - {e}")
                if attempt + 1 == MAX_RETRIES:
                    print(f" Max retries reached for API call on page {current_page}. Stopping.")
                else:
                    wait_time = INITIAL_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0,1) 
                    print(f"   Retrying API call in {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
            except requests.exceptions.RequestException as e:
                print(f" API Call Error for page {current_page} (RequestException): {e}. Not retrying this.")
                break 
            except json.JSONDecodeError as e:
                print(f"API Call Error: Failed to decode JSON response from page {current_page}: {e}")
                print(f"   Response text (first 200 chars): {response.text[:200] if response else 'No response'}")
                break
            except Exception as e:
                print(f" Unexpected error during API call for page {current_page}: {e}")
                break
        
        if api_response_content is None: 
            print(f" Could not fetch data for page {current_page} after all attempts. Halting further page fetches.")
            break 

        bids_on_page = extract_bid_data(api_response_content)
        if not bids_on_page and current_page > 1:
            print(f" No more bids found on page {current_page}. Assuming end of bid list.")
            break
        if not bids_on_page and current_page == 1:
            print(f" No bids found on the very first page. Check filters or site status.")
            break

        for bid_item in bids_on_page:
            if (stop_bid_id and str(bid_item.get("bid_id")) == str(stop_bid_id)) or \
               (stop_bid_number and bid_item.get("bid_number") == stop_bid_number):
                print(f"\n Stop bid reached → {bid_item.get('bid_number')} (id {bid_item.get('bid_id')}).")
                print(f"   Exiting data collection.")
                with open("scraped_bids_with_city.json", "w", encoding="utf-8") as f_out:
                    json.dump(scraped_data, f_out, indent=2, ensure_ascii=False)
                print(f"\nPartial results (up to stop bid) saved to 'scraped_bids_with_city.json'.")
                return 

            if len(scraped_data) >= target_bid_count:
                break 

            primary_pdf_url = bid_item.get("download_url")
            safe_bid_id_for_file = str(bid_item.get("bid_id", "unknown_bid_id"))
            temp_primary_pdf_filename = os.path.join(pdf_dir, f"primary_{safe_bid_id_for_file}_{len(scraped_data) + 1}.pdf")
            
            print(f"\n[{len(scraped_data) + 1}/{target_bid_count}] Processing bid: {bid_item.get('bid_number')}")
            
            downloaded_primary_pdf_path = None
            if primary_pdf_url:
                 downloaded_primary_pdf_path = download_pdf_with_retries(primary_pdf_url, temp_primary_pdf_filename)
            
            bid_item["Reverse Auction"] = None 
            bid_item["Bid_doc"] = None      
            bid_item["extra_docs"] = {}     
            bid_item["matched_city_info"] = {"matched_city": "Not Processed", "hyperlinks": []} 

            if downloaded_primary_pdf_path:
                if primary_pdf_url and "showradocumentPdf" in primary_pdf_url: 
                    bid_item["Reverse Auction"] = primary_pdf_url
                elif primary_pdf_url and "showbidDocument" in primary_pdf_url: 
                    bid_item["Bid_doc"] = primary_pdf_url
                
                pdf_content_data = extract_structured_pdf_data(downloaded_primary_pdf_path)
                for link_data in pdf_content_data.get("hyperlinks", []):
                    uri = link_data.get("uri", "")
                    if "showbidDocument" in uri:
                        bid_item["Bid_doc"] = uri
                    elif uri.endswith(".pdf"):
                        name_hint = uri.split("/")[-1].split(".")[0].replace("-", "_").lower()
                        bid_item["extra_docs"][name_hint] = uri
                
                city_info_dict = None
                if bid_item["Bid_doc"]:
                    temp_addr_pdf_filename = os.path.join(pdf_dir, f"addr_{safe_bid_id_for_file}_{len(scraped_data) + 1}.pdf")
                    city_info_dict = extract_address_from_showbid_pdf(bid_item["Bid_doc"], temp_addr_pdf_filename)
                
                bid_item["matched_city_info"] = city_info_dict if city_info_dict else {"matched_city": "Bid Doc Not Found or Process Failed", "hyperlinks": []}
                
                try: 
                    os.remove(downloaded_primary_pdf_path)
                except OSError as e:
                    print(f" Warning: Could not remove primary PDF {downloaded_primary_pdf_path}: {e}")
            else: 
                bid_item["matched_city_info"] = {"matched_city": "Primary PDF Download Failed" if primary_pdf_url else "No Primary PDF URL", "hyperlinks": []}
                if primary_pdf_url:
                    print(f" Skipping PDF processing for bid {bid_item.get('bid_number')} as primary PDF download failed.")
                else:
                    print(f"No primary download URL for bid {bid_item.get('bid_number')}. No PDF processing done.")
            
            scraped_data.append(bid_item) 
        
        if len(scraped_data) >= target_bid_count:
            print(f"\n Target bid count of {target_bid_count} reached.")
            break
        current_page += 1
        time.sleep(random.uniform(1, 3)) 

    output_filename = "scraped_bids_with_city.json"
    with open(output_filename, "w", encoding="utf-8") as f_out:
        json.dump(scraped_data, f_out, indent=2, ensure_ascii=False)
    print(f"\n Done. Collected {len(scraped_data)} bids and saved to '{output_filename}'.")

if __name__ == "__main__":
    if csrf_token == "a" or ci_session == "b" or csrf_token.startswith("your_"): # Basic check for placeholder tokens
        print(" Error: Placeholder CSRF/session tokens (csrf_token, ci_session) are not set.")
        print("   Please replace 'a' and 'b' (or 'your_...' placeholders) at the top of the script with your actual tokens.")
    elif not DISTRICTS: # Check if district data loaded
        print("Error: District list could not be loaded. Please check 'indian_districts_cleaned_final.xlsx'.")
    else:
        fetch_and_scrape_top_bids(
            target_bid_count=50, # Example target count
            stop_bid_id=7800791, 
            stop_bid_number=None 
        )