The fulfillment_policy_api contains a complex set of data types.  The section "Docs for compound data types in fulfillment" explains where to find detailed dcoumenation on how these Data Types are composed.  **CRITICAL ** Pay close attention to the "Request fields" section in the "top level explaintatino" url for fulfillment_policy_api, this will list primitive data types, EnumData types which are dockemtned in the "Docs for Enums" section, and Compound Data Types.  The Compound Data Types will decompose into primative datatypes.  All should be modeled pydantically.


## fulfillment_policy_api:
   ### top level explanation of: fulfillment_policy and what is required
       - https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[1]-h2-fulfillment_policy
   ### end points to implement for  fulfillment_policy
       - create_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/createFulfillmentPolicy
       - delete_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/deleteFulfillmentPolicy
       - get_fulfillment_policies: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/getFulfillmentPolicies
       - get_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/getFulfillmentPolicy
       - get_fulfillment_policy_by_name: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/getFulfillmentPolicyByName
       - update_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/updateFulfillmentPolicy

## Docs for compound data types in fulfillment
       - ShippingOption: https://developer.ebay.com/api-docs/sell/account/types/api:ShippingOption
       - ShippingService: https://developer.ebay.com/api-docs/sell/account/types/api:ShippingService

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
   
