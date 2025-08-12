import os
import json
from pymongo import MongoClient

# MongoDB connection details
MONGO_URI = "mongodb://tenderUser1:7xXkDMKM9i%24bdAKq@13.126.119.166:27017/tenderDB?authSource=tenderDB"
DATABASE_NAME = "tenderDB"

# Mapping of full paths to each JSON file
json_files = [
    r"C:\Users\User\Desktop\Tender Final\aai_final_tenders.json",
    r"C:\Users\User\Desktop\Tender Final\cci tenders\tenders.json",
    r"C:\Users\User\Desktop\Tender Final\cochin_tenders.json",
    r"C:\Users\User\Desktop\Tender Final\cppp tenders\cppp.json",
    r"C:\Users\User\Desktop\Tender Final\eproc2 tenders\tenders_output.json",
    r"C:\Users\User\Desktop\Tender Final\gail tenders\gail_tenders.json",
    r"C:\Users\User\Desktop\Tender Final\scraped_bids_with_city.json",
    r"C:\Users\User\Desktop\Tender Final\gmdc tenders\gmdc_tenders.json",
    r"C:\Users\User\Desktop\Tender Final\goa shipyard tenders\goa_shipyard_tenders.json",
    r"C:\Users\User\Desktop\Tender Final\irel tenders\irel_all_pages_tenders.json",
    r"C:\Users\User\Desktop\Tender Final\ireps tenders\tenders_ireps_full_pages.json",
    r"C:\Users\User\Desktop\Tender Final\isro tenders\isro_eproc_links.json",
    r"C:\Users\User\Desktop\Tender Final\nfl tenders\nfl_tenders.json",
    r"C:\Users\User\Desktop\Tender Final\telangana tenders\tenders_full.json",
    #r"C:\Users\User\rajasthan\rajasthan\tenders_with_zip_9222.json"
]

def sanitize_collection_name(folder_path):
    return os.path.basename(os.path.dirname(folder_path)).replace(" ", "_").lower()

def main():
    print("🚀 Script started")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=20000)
        db = client[DATABASE_NAME]
        client.server_info()
        print("✅ Connected to MongoDB")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return

    for file_path in json_files:
        if not os.path.exists(file_path):
            print(f"⚠️ File not found: {file_path}")
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = [data]
            elif not isinstance(data, list):
                raise ValueError("JSON root is not a list or dict")

            collection_name = sanitize_collection_name(file_path)
            collection = db[collection_name]
            result = collection.insert_many(data)
            print(f"✅ Uploaded {len(result.inserted_ids)} records to '{collection_name}'")

        except Exception as e:
            print(f"❌ Error uploading {file_path}: {e}")

    print("🏁 Script completed")

if __name__ == "__main__":
    main()
