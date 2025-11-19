import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product

app = FastAPI(title="The Arcane Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "The Arcane Lab backend draait"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response

# --------- Product endpoints (shop focus) ---------

class ProductCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
    image_url: Optional[str] = None
    tags: List[str] = []
    featured: bool = False

@app.post("/api/products")
def create_product(payload: ProductCreate):
    try:
        product = Product(**payload.model_dump())
        inserted_id = create_document("product", product)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/products")
def list_products(q: Optional[str] = None, category: Optional[str] = None, featured: Optional[bool] = None):
    filter_query = {}
    if category:
        filter_query["category"] = category
    if featured is not None:
        filter_query["featured"] = featured
    if q:
        # Basic text search on title/description/tags
        filter_query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"tags": {"$elemMatch": {"$regex": q, "$options": "i"}}}
        ]
    docs = get_documents("product", filter_query)
    # Convert ObjectId to string
    for d in docs:
        d["id"] = str(d.get("_id"))
        d.pop("_id", None)
    return {"items": docs}

@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    from pymongo.errors import InvalidId
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")

    doc = db["product"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return doc

# ------------- SEO config endpoint --------------
@app.get("/api/site")
def site_meta():
    return {
        "brand": "The Arcane Lab",
        "tagline": "Creativiteit tastbaar maken: props, accessoires en decor geïnspireerd door fantasy, games en anime.",
        "description": "Unieke props en decor, handgemaakt met 3D-print, EVA-foam en vakmanschap. Bestel kant-en-klaar of vraag maatwerk aan.",
        "socials": {
            "instagram": "https://instagram.com/",
            "tiktok": "https://tiktok.com/@",
            "email": "info@thearcanelab.nl"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
