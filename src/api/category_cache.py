"""
Simple eBay Category JSON Cache

Just stores raw eBay JSON in cache with TTL. No complex objects or parsing.
"""
import logging
from typing import Dict, Any, Optional

from api.cache import get_cache_manager, CacheTTL
from api.oauth import OAuthManager
from api.rest_client import EbayRestClient

logger = logging.getLogger(__name__)


async def get_category_tree_json(
    oauth_manager: OAuthManager,
    rest_client: EbayRestClient,
    category_tree_id: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Get raw eBay category tree JSON from cache or API.
    
    Returns the complete raw JSON response from eBay's category tree API.
    Uses simple cache with 24-hour TTL.
    
    Args:
        oauth_manager: OAuth manager instance
        rest_client: eBay REST client instance
        category_tree_id: The category tree ID (e.g., "0" for US marketplace)
        force_refresh: Force refresh from API, bypassing cache
        
    Returns:
        Complete category tree JSON from eBay API
    """
    cache_manager = get_cache_manager()
    cache_key = f"CATEGORY_LIST_{category_tree_id}"
    
    # Try cache first
    if not force_refresh and cache_manager:
        cached_data = await cache_manager.get(cache_key)
        if cached_data:
            logger.debug(f"Using cached category tree JSON for tree ID {category_tree_id}")
            return cached_data
    
    # Fetch from eBay API
    logger.info(f"Fetching fresh category tree from eBay API for tree ID {category_tree_id}")
    
    # Get complete tree - this is the raw JSON we want
    response = await rest_client.get(
        f"/commerce/taxonomy/v1/category_tree/{category_tree_id}",
        params={}
    )
    category_tree_json = response["body"]
    
    # Cache the raw JSON for 24 hours
    if cache_manager:
        await cache_manager.set(cache_key, category_tree_json, CacheTTL.CATEGORIES)
        logger.info(f"Cached category tree JSON for tree ID {category_tree_id}")
    
    return category_tree_json


def find_category_subtree(category_tree_json: Dict[str, Any], category_id: str) -> Optional[Dict[str, Any]]:
    """
    Find a specific category and its subtree in the raw JSON.
    
    Simple recursive search through the JSON structure.
    """
    def search_node(node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Check if this is the category we're looking for
        category_info = node.get("category", {})
        if category_info.get("categoryId") == category_id:
            return node
        
        # Search children
        for child in node.get("childCategoryTreeNodes", []):
            result = search_node(child)
            if result:
                return result
        
        return None
    
    # Start search from root
    root_node = category_tree_json.get("rootCategoryNode", {})
    return search_node(root_node)