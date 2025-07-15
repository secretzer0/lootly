"""eBay categories resource.

Provides eBay category hierarchy and metadata. Works with or without API credentials,
using cached data when credentials are not available.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from data_types import MCPResourceData
from lootly_server import mcp


# Static category data as fallback when API is not available
STATIC_CATEGORIES = {
    "major_categories": {
        "1": {"name": "Collectibles", "level": 1, "leaf": False},
        "267": {"name": "Books, Movies & Music", "level": 1, "leaf": False},
        "11450": {"name": "Clothing, Shoes & Accessories", "level": 1, "leaf": False},
        "58058": {"name": "Computers/Tablets & Networking", "level": 1, "leaf": False},
        "293": {"name": "Consumer Electronics", "level": 1, "leaf": False},
        "14339": {"name": "Crafts", "level": 1, "leaf": False},
        "237": {"name": "Dolls & Bears", "level": 1, "leaf": False},
        "11700": {"name": "Home & Garden", "level": 1, "leaf": False},
        "281": {"name": "Jewelry & Watches", "level": 1, "leaf": False},
        "11232": {"name": "Movies & TV", "level": 1, "leaf": False},
        "619": {"name": "Musical Instruments & Gear", "level": 1, "leaf": False},
        "1281": {"name": "Pet Supplies", "level": 1, "leaf": False},
        "5197": {"name": "Real Estate", "level": 1, "leaf": False},
        "888": {"name": "Sporting Goods", "level": 1, "leaf": False},
        "1305": {"name": "Tickets & Experiences", "level": 1, "leaf": False},
        "220": {"name": "Toys & Hobbies", "level": 1, "leaf": False},
        "3252": {"name": "Travel", "level": 1, "leaf": False},
        "131090": {"name": "Video Games & Consoles", "level": 1, "leaf": False}
    },
    "popular_categories": [
        {"id": "267", "name": "Books, Movies & Music", "reason": "Entertainment essentials"},
        {"id": "11450", "name": "Clothing, Shoes & Accessories", "reason": "Fashion staples"},
        {"id": "293", "name": "Consumer Electronics", "reason": "Tech gadgets"},
        {"id": "11700", "name": "Home & Garden", "reason": "Home improvement"},
        {"id": "131090", "name": "Video Games & Consoles", "reason": "Gaming"}
    ],
    "category_search_tips": {
        "267": ["author", "ISBN", "edition", "genre", "format (hardcover, paperback)"],
        "11450": ["brand", "size", "color", "material", "condition"],
        "293": ["brand", "model number", "specifications", "generation"],
        "58058": ["processor", "RAM", "storage", "graphics card", "brand"],
        "131090": ["platform", "game title", "edition", "region", "condition"],
        "281": ["metal type", "gemstone", "brand", "style", "size"],
        "220": ["age range", "brand", "character", "series", "condition"],
        "888": ["sport type", "brand", "size", "skill level", "condition"]
    }
}

# Sample subcategories for demonstration
STATIC_SUBCATEGORIES = {
    "267": {
        "267": {"name": "Books", "level": 2, "leaf": False},
        "11232": {"name": "Movies & TV", "level": 2, "leaf": False},
        "11233": {"name": "Music", "level": 2, "leaf": False},
        "45110": {"name": "Audiobooks", "level": 2, "leaf": True}
    },
    "293": {
        "3270": {"name": "Audio Equipment", "level": 2, "leaf": False},
        "175672": {"name": "Cameras & Photo", "level": 2, "leaf": False},
        "32852": {"name": "Headphones", "level": 2, "leaf": False},
        "15052": {"name": "Televisions", "level": 2, "leaf": False}
    }
}


def parse_category_uri(uri: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse category URI to extract components.
    
    Returns:
        Tuple of (category_id, operation, param)
    """
    parts = uri.replace("ebay://categories", "").strip("/").split("/")
    
    if not parts[0]:  # ebay://categories
        return None, None, None
    
    category_id = parts[0]
    operation = parts[1] if len(parts) > 1 else None
    param = parts[2] if len(parts) > 2 else None
    
    return category_id, operation, param


async def get_categories_from_api(category_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Try to get categories from eBay API.
    
    Returns None if API is not available or credentials are missing.
    """
    # API implementation would go here
    # For now, return None to simulate no credentials
    return None


@mcp.resource("ebay://categories")
async def ebay_all_categories_resource(ctx: Context) -> str:
    """Get all major eBay categories."""
    try:
        # Try to get live data from API
        api_data = await get_categories_from_api(None)
        has_api_access = api_data is not None
        
        # Build category hierarchy
        categories = []
        if has_api_access and api_data:
            # Use API data
            for cat in api_data.get("categories", []):
                categories.append({
                    "id": cat["id"],
                    "name": cat["name"],
                    "level": cat.get("level", 1),
                    "has_children": not cat.get("leaf", True)
                })
        else:
            # Use static data
            for cat_id, cat_info in STATIC_CATEGORIES["major_categories"].items():
                categories.append({
                    "id": cat_id,
                    "name": cat_info["name"],
                    "level": cat_info["level"],
                    "has_children": not cat_info["leaf"]
                })
        
        return MCPResourceData(
            data={
                "categories": categories,
                "total_count": len(categories),
                "data_source": "live_api" if has_api_access else "static_cache",
                "note": "Major eBay marketplace categories"
            },
            metadata={
                "cache_ttl": 3600,  # 1 hour
                "api_available": has_api_access
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


@mcp.resource("ebay://categories/popular")
async def ebay_popular_categories_resource(ctx: Context) -> str:
    """Get popular eBay categories."""
    try:
        # Try to get live data from API
        api_data = await get_categories_from_api("popular")
        has_api_access = api_data is not None
        
        if has_api_access and api_data:
            # Use API data for popular categories
            popular = api_data.get("popular_categories", [])
        else:
            # Use static popular categories
            popular = STATIC_CATEGORIES["popular_categories"]
        
        return MCPResourceData(
            data={
                "popular_categories": popular,
                "data_source": "live_api" if has_api_access else "static_recommendations",
                "note": "Most popular categories based on marketplace activity"
            },
            metadata={
                "cache_ttl": 1800,  # 30 minutes
                "api_available": has_api_access
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


@mcp.resource("ebay://categories/{category_id}")
async def ebay_category_details_resource(category_id: str, ctx: Context) -> str:
    """Get details for a specific eBay category."""
    try:
        # Try to get live data from API
        api_data = await get_categories_from_api(category_id)
        has_api_access = api_data is not None
        
        # Get category info
        if has_api_access and api_data:
            # Use API data
            category_info = api_data
        else:
            # Look up in static data
            category_info = STATIC_CATEGORIES["major_categories"].get(category_id)
            if not category_info:
                return MCPResourceData(
                    error=f"Category {category_id} not found",
                    metadata={"category_id": category_id}
                ).to_json_string()
            
            # Add ID to the info
            category_info = {
                "id": category_id,
                **category_info
            }
        
        # Get search tips if available
        search_tips = STATIC_CATEGORIES["category_search_tips"].get(category_id, [])
        
        # Get subcategories if available
        subcategories = []
        if category_id in STATIC_SUBCATEGORIES:
            for sub_id, sub_info in STATIC_SUBCATEGORIES[category_id].items():
                subcategories.append({
                    "id": sub_id,
                    "name": sub_info["name"],
                    "level": sub_info["level"],
                    "has_children": not sub_info["leaf"]
                })
        
        return MCPResourceData(
            data={
                "category": category_info,
                "search_tips": search_tips,
                "subcategories": subcategories,
                "data_source": "live_api" if has_api_access else "static_cache"
            },
            metadata={
                "cache_ttl": 3600,  # 1 hour
                "api_available": has_api_access,
                "has_subcategories": len(subcategories) > 0,
                "has_search_tips": len(search_tips) > 0
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


@mcp.resource("ebay://categories/{category_id}/children")
async def ebay_category_children_resource(category_id: str, ctx: Context) -> str:
    """Get subcategories for a specific category."""
    try:
        # Try to get live data from API
        api_data = await get_categories_from_api(category_id)
        has_api_access = api_data is not None
        
        subcategories = []
        if has_api_access and api_data:
            # Use API data
            for sub in api_data.get("subcategories", []):
                subcategories.append({
                    "id": sub["id"],
                    "name": sub["name"],
                    "level": sub.get("level", 2),
                    "has_children": not sub.get("leaf", True)
                })
        else:
            # Use static data
            if category_id in STATIC_SUBCATEGORIES:
                for sub_id, sub_info in STATIC_SUBCATEGORIES[category_id].items():
                    subcategories.append({
                        "id": sub_id,
                        "name": sub_info["name"],
                        "level": sub_info["level"],
                        "has_children": not sub_info["leaf"]
                    })
        
        return MCPResourceData(
            data={
                "parent_category_id": category_id,
                "subcategories": subcategories,
                "total_count": len(subcategories),
                "data_source": "live_api" if has_api_access else "static_cache"
            },
            metadata={
                "cache_ttl": 3600,  # 1 hour
                "api_available": has_api_access
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


@mcp.resource("ebay://categories/{category_id}/search_tips")
async def ebay_category_search_tips_resource(category_id: str, ctx: Context) -> str:
    """Get search tips for a specific category."""
    try:
        # Get search tips
        search_tips = STATIC_CATEGORIES["category_search_tips"].get(category_id, [])
        
        if not search_tips:
            # Provide generic tips
            search_tips = [
                "Use specific brand names",
                "Include model numbers when applicable",
                "Specify condition (new, used, refurbished)",
                "Add relevant keywords from the title",
                "Use filters to narrow results"
            ]
        
        return MCPResourceData(
            data={
                "category_id": category_id,
                "search_tips": search_tips,
                "tip_count": len(search_tips)
            },
            metadata={
                "cache_ttl": 86400,  # 24 hours (tips don't change often)
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()