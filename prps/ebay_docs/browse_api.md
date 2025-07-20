# The file browse_api.py is the top level MCP tool entry point and needs to surface an indepth docstring to enable the LLMs to know how to use it correctly.

## @mcp.tool search_items
  - This utilizes the eBay REST endpoint: https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search
  ### I want to support only the following query parameters:
    - q 
    - category_ids
    - filter
    - sort
    - limit
    - offset
  ### Where to get the fields for filter and sort query parameters and supporting documents for them
    #### https://developer.ebay.com/api-docs/buy/static/ref-buy-browse-filters.html
    #### https://developer.ebay.com/api-docs/buy/browse/types/cos:FilterField
    #### https://developer.ebay.com/api-docs/buy/browse/types/cos:SortField
    #### https://developer.ebay.com/api-docs/buy/browse/types/cos:RangeValue
      - these should be an enum and well documented in the docstring and ultimatly surfaced to the LLM in the search_itmes docstring
      - the sort query parameter uses the "filter name" column form the ref-buy-browse-filters document
      - pay close attention to the column "syntax" when implementing the filter query parameter
 

## @mcp.tool get_item_details
   - This utilizes the eBay REST endpoint: https://developer.ebay.com/api-docs/buy/browse/resources/item/methods/getItem
   ### The the pydantic model ItemDetailsInput needs to only have an itemId nd legacyItemId fields with a detailed docstring on how to submit and tell the difference between the two, so the LLM MCP can make a correct choice an which one to populate.
     #### itemId
       - https://developer.ebay.com/api-docs/buy/browse/resources/item/methods/getItem
       - only support the item_id query parameter
       -  do not set the query parameters fieldgroup or quantity_for_shipping_estimate and do not make them part of the ItemDetailsInput model
     #### legacyItemId 
       - https://developer.ebay.com/api-docs/buy/browse/resources/item/methods/getItemByLegacyId
       - only implement the legacy_item_id query parameter


## If the search_items is correctly and robustly implemented we can get rid of get_items_by_category and CategoryBrowseInput
     
