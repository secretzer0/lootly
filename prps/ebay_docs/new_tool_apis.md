## fullfilment_policy_api:
   ### top level explanation of: fulfillment_policy and what is required
       - https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[1]-h2-fulfillment_policy
   ### end points to implement for  fulfillment_policy
       - create_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/createFulfillmentPolicy
       - delete_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/deleteFulfillmentPolicy
       - get_fulfillment_policies: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/getFulfillmentPolicies
       - get_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/getFulfillmentPolicy
       - get_fulfillment_policy_by_name: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/getFulfillmentPolicyByName
       - update_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/updateFulfillmentPolicy

## payment_policy_api:
   ### top level explanation of: payment_policy endpoints  and what is required 
       - https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[2]-h2-payment_policy
   ### end points to implement for payment_policy
       - create_payment_policy: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/createPaymentPolicy
       - delete_payment_policy: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/deletePaymentPolicy
       - get_payment_policies: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/getPaymentPolicies
       - get_payment_policy: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/getPaymentPolicy
       - get_payment_policy_by_name: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/getPaymentPolicyByName
       - update_payment_policy: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/updatePaymentPolicy 

## return_policy_api:
   ### top level explanation of: return_policy endpoints  and what is required 
       - https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[7]-h2-return_policy
   ### end points to implement for return_policy
       - create_return_policy: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/createReturnPolicy
       - delete_teturn_policy: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/deleteReturnPolicy
       - get_return_policies: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/getReturnPolicies
       - get_return_policy: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/getReturnPolicy
       - get_return_policy_by_name: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/getReturnPolicyByName
       - update_return_policy: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/updateReturnPolicy

## inventory_item_api:
   ### top level explanation of: inventory_item endpoints  and what is required 
       - https://developer.ebay.com/api-docs/sell/inventory/resources/methods
   ### end points to implement for inventory_item:
       - bulk_create_or_replace_inventory_item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/bulkCreateOrReplaceInventoryItem
       - bulk_get_inventory_item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/bulkGetInventoryItem
       - bulk_update_price_quantity: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/bulkUpdatePriceQuantity
       - add_inventory_item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/createOrReplaceInventoryItem
       - delete_inventory_item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/deleteInventoryItem
       - get_inventory_item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/getInventoryItem
       - get_inventory_items: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/getInventoryItems

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
   
