# Create new file: app/api/v1/public/routes_cached.py
"""
Cached public routes for better performance with remote database
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import DBSession
from app.models.hostel import Hostel, HostelStatus
from app.models.room import Room
import asyncio

router = APIRouter()

# Simple in-memory cache
_cache = {}
_cache_timestamp = {}


def get_cache(key: str, ttl: int = 60):
    """Get cached value if not expired"""
    if key in _cache and key in _cache_timestamp:
        import time
        if time.time() - _cache_timestamp[key] < ttl:
            return _cache[key]
    return None


def set_cache(key: str, value):
    """Set cache value"""
    import time
    _cache[key] = value
    _cache_timestamp[key] = time.time()


@router.get("/hostels-fast")
async def list_hostels_fast(
    db: DBSession,
    city: str | None = None,
    page: int = 1,
    per_page: int = 10,
):
    """
    Fast hostel listing - minimal data, optimized for remote DB
    """
    cache_key = f"hostels_{city}_{page}_{per_page}"
    
    # Try cache first
    cached = get_cache(cache_key, ttl=30)  # 30 second cache
    if cached:
        return cached
    
    try:
        # Simple query - no joins
        query = select(
            Hostel.id,
            Hostel.name,
            Hostel.slug,
            Hostel.city,
            Hostel.state,
            Hostel.hostel_type,
            Hostel.description,
            Hostel.is_featured,
            Hostel.created_at
        ).where(
            Hostel.is_public.is_(True),
            Hostel.status == HostelStatus.ACTIVE
        )
        
        if city:
            query = query.where(Hostel.city.ilike(f"%{city}%"))
        
        # Get total count
        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = int(count_result.scalar() or 0)
        
        # Pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        result = await db.execute(query)
        rows = result.all()
        
        # Build response
        items = []
        for row in rows:
            items.append({
                "id": str(row.id),
                "name": row.name,
                "slug": row.slug,
                "city": row.city,
                "state": row.state,
                "hostel_type": row.hostel_type.value if hasattr(row.hostel_type, 'value') else str(row.hostel_type),
                "description": (row.description[:150] + "...") if row.description and len(row.description) > 150 else row.description,
                "is_featured": row.is_featured,
                "starting_price": 0,  # Will be filled separately if needed
                "rating": 0,
                "available_beds": 0,
            })
        
        response = {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page
        }
        
        # Cache the response
        set_cache(cache_key, response)
        
        return response
        
    except Exception as e:
        print(f"Error in fast hostels endpoint: {e}")
        return {
            "items": [],
            "total": 0,
            "page": page,
            "per_page": per_page
        }


@router.get("/health")
async def health_check():
    """Simple health check that doesn't hit the database"""
    return {"status": "ok", "timestamp": __import__("time").time()}