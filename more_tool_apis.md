## account_privileges_api:
   ### top level explanation of: account_privileges_api and what is required
       - https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[4]-h2-privilege
   ### end points to implement for  account_privileges_api
       - get_privileges: https://developer.ebay.com/api-docs/sell/account/resources/privilege/methods/getPrivileges

## account_programs_api:
   ### top level explanation of: account_programs_api  and what is required 
       - https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[5]-h2-program
   ### end points to implement for account_programs_api
       - get_opted_in_programs: https://developer.ebay.com/api-docs/sell/account/resources/program/methods/getOptedInPrograms
       - opt_in_to_program: https://developer.ebay.com/api-docs/sell/account/resources/program/methods/optInToProgram
       - opt_out_of_program: https://developer.ebay.com/api-docs/sell/account/resources/program/methods/optOutOfProgram

## taxonomy_api:
   ### top level explanation of: taxonomy_api and what is required
       - https://developer.ebay.com/api-docs/commerce/taxonomy/resources/methods
   ### end points to implement for taxonommy_api
       - get_default_category_tree_id: https://developer.ebay.com/api-docs/commerce/taxonomy/resources/category_tree/methods/getDefaultCategoryTreeId : **NOTE** marketplace_id should use the MarketplaceIdEnum
       - get_category_tree: https://developer.ebay.com/api-docs/commerce/taxonomy/resources/category_tree/methods/getCategoryTree
       - get_category_tree_subtree: https://developer.ebay.com/api-docs/commerce/taxonomy/resources/category_tree/methods/getCategorySubtree
       - get_category_suggestions: https://developer.ebay.com/api-docs/commerce/taxonomy/resources/category_tree/methods/getCategorySuggestions
       - get_expired_categories: https://developer.ebay.com/api-docs/commerce/taxonomy/resources/category_tree/methods/getExpiredCategories

## Docs for Enums
   - AvailabilityTypeEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:AvailabilityTypeEnum
   - CategoryTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:CategoryTypeEnum
   - ConditionEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:ConditionEnum
   - CurrencyCodeEnum: https://developer.ebay.com/api-docs/sell/account/types/ba:CurrencyCodeEnum
   - LocaleEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:LocaleEnum
   - LengthUnitOfMeasureEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:LengthUnitOfMeasureEnum
   - MarketplaceIdEnum: https://developer.ebay.com/api-docs/sell/account/types/ba:MarketplaceIdEnum
   - PackageTypeEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:PackageTypeEnum
   - PaymentInstrumentBrandEnum: https://developer.ebay.com/api-docs/sell/account/types/api:PaymentInstrumentBrandEnum
   - PaymentMethodTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:PaymentMethodTypeEnum
   - RecipientAccountReferenceTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:RecipientAccountReferenceTypeEnum
   - RefundMethodEnum: https://developer.ebay.com/api-docs/sell/account/types/api:RefundMethodEnum
   - ReturnMethodEnum: https://developer.ebay.com/api-docs/sell/account/types/api:ReturnMethodEnum
   - ReturnShippingCostPayerEnum: https://developer.ebay.com/api-docs/sell/account/types/api:ReturnShippingCostPayerEnum
   - RegionTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/ba:RegionTypeEnum
   - ShippingCostTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:ShippingCostTypeEnum
   - ShippingOptionTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:ShippingOptionTypeEnum
   - TimeDurationUnitEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:TimeDurationUnitEnum
   - WeightUnitOfMeasureEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:WeightUnitOfMeasureEnum
   - ProgramTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:ProgramTypeEnum
   
