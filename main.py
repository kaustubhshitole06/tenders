from passlib.context import CryptContext
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pymongo import MongoClient
from typing import List, Dict, Any
import json

app = FastAPI(title="Tender Dashboard API", 
             description="API for fetching tender data from MongoDB and user authentication",
             version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500","http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = "mongodb://tenderUser1:7xXkDMKM9i%24bdAKq@13.126.119.166:27017/tenderDB?authSource=tenderDB"
DATABASE_NAME = "tenderDB"


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User collection name
USER_COLLECTION = "users"

def get_user(email: str):
    return db[USER_COLLECTION].find_one({"email": email})

def create_user(email: str, password: str):
    hashed_password = pwd_context.hash(password)
    db[USER_COLLECTION].insert_one({"email": email, "password": hashed_password})

def authenticate_user(email: str, password: str):
    user = get_user(email)
    if not user:
        return False
    if not pwd_context.verify(password, user["password"]):
        return False
    return True

# Register endpoint
@app.post("/api/register")
async def register(request: Request):
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    if get_user(email):
        raise HTTPException(status_code=400, detail="Email already registered")
    create_user(email, password)
    return {"success": True, "message": "User registered successfully."}

# Login endpoint
@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    if not authenticate_user(email, password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"success": True, "message": "Login successful."}



# Mount static files (for serving index.html)
app.mount("/static", StaticFiles(directory="."), name="static")

# Initialize MongoDB client
try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print(f"❌ Error connecting to MongoDB: {e}")
    raise

@app.get("/")
async def read_root():
    """Serve the frontend HTML page"""
    return FileResponse("index.html")

@app.get("/api/collections")
async def get_collections() -> List[Dict[str, Any]]:
    """Get list of all collections and their counts"""
    try:
        collections = []
        for collection_name in db.list_collection_names():
            count = db[collection_name].count_documents({})
            collections.append({
                "name": collection_name,
                "count": count
            })
        return collections
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tenders/{collection_name}")
async def get_tenders(collection_name: str) -> List[Dict[str, Any]]:
    """Get all tenders from a specific collection"""
    try:
        if collection_name not in db.list_collection_names():
            raise HTTPException(status_code=404, detail=f"Collection {collection_name} not found")
        
        collection = db[collection_name]
        tenders = list(collection.find({}, {'_id': 0}))  # Exclude MongoDB _id field
        return tenders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search_tenders(query: str) -> List[Dict[str, Any]]:
    """Search across all collections"""
    try:
        results = []
        for collection_name in db.list_collection_names():
            collection = db[collection_name]
            # Search in all string fields
            matches = list(collection.find({
                "$or": [
                    {field: {"$regex": query, "$options": "i"}}
                    for field in collection.find_one({}).keys()
                    if isinstance(collection.find_one({})[field], str)
                ]
            }, {'_id': 0}))
            
            # Add collection name to each result
            for match in matches:
                match['source_collection'] = collection_name
                results.append(match)
                
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
