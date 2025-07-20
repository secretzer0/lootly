"""
Shipping service enums for eBay fulfillment policies.

This module contains enums for all valid eBay shipping services extracted from
GeteBayDetails API response. Services are split into domestic and international
categories for type safety and better organization.

Generated from eBay API response where ValidForSellingFlow=true
Last updated: 2025-07-20
"""
from typing import Dict
from .enums import BaseEbayEnum


class DomesticShippingServiceEnum(BaseEbayEnum):
    """
    Valid domestic shipping service codes for eBay US marketplace.
    
    These codes must be used when creating domestic shipping options in fulfillment policies.
    Only services with ValidForSellingFlow=true are included.
    """
    
    # ========== Generic Domestic Services ==========
    ShippingMethodStandard = "ShippingMethodStandard"  # Standard Shipping
    StandardShippingWithAdultSignature = "StandardShippingWithAdultSignature"  # Standard Shipping with Adult Signature Required
    ShippingMethodExpress = "ShippingMethodExpress"  # Expedited Shipping
    ExpeditedShippingWithAdultSignature = "ExpeditedShippingWithAdultSignature"  # Expedited Shipping with Adult Signature Required
    Other = "Other"  # Economy Shipping
    EconomyShippingWithAdultSignature = "EconomyShippingWithAdultSignature"  # Economy Shipping with Adult Signature Required
    ShippingMethodOvernight = "ShippingMethodOvernight"  # Overnight shipping
    
    # ========== Freight Services ==========
    Freight = "Freight"  # Freight
    FlatRateFreight = "FlatRateFreight"  # Flat Rate Freight
    
    # ========== Local Pickup ==========
    Pickup = "Pickup"  # Local Pickup
    
    # ========== USPS Domestic Services ==========
    USPSParcel = "USPSParcel"  # USPS Ground Advantage
    USPSFirstClass = "USPSFirstClass"  # USPS First Class
    USPSFirstClassLetter = "USPSFirstClassLetter"  # USPS First Class Letter
    USPSFirstClassLargeEnvelop = "USPSFirstClassLargeEnvelop"  # USPS First Class Large Envelope
    USPSPriority = "USPSPriority"  # USPS Priority Mail
    USPSPriorityFlatRateEnvelope = "USPSPriorityFlatRateEnvelope"  # USPS Priority Mail Flat Rate Envelope
    USPSPriorityMailSmallFlatRateBox = "USPSPriorityMailSmallFlatRateBox"  # USPS Priority Mail Small Flat Rate Box
    USPSPriorityFlatRateBox = "USPSPriorityFlatRateBox"  # USPS Priority Mail Medium Flat Rate Box
    USPSPriorityMailLargeFlatRateBox = "USPSPriorityMailLargeFlatRateBox"  # USPS Priority Mail Large Flat Rate Box
    USPSPriorityMailPaddedFlatRateEnvelope = "USPSPriorityMailPaddedFlatRateEnvelope"  # USPS Priority Mail Padded Flat Rate Envelope
    USPSPriorityMailLegalFlatRateEnvelope = "USPSPriorityMailLegalFlatRateEnvelope"  # USPS Priority Mail Legal Flat Rate Envelope
    USPSExpressMail = "USPSExpressMail"  # USPS Priority Mail Express
    USPSExpressFlatRateEnvelope = "USPSExpressFlatRateEnvelope"  # USPS Priority Mail Express Flat Rate Envelope
    USPSExpressMailLegalFlatRateEnvelope = "USPSExpressMailLegalFlatRateEnvelope"  # USPS Priority Mail Express Legal Flat Rate Envelope
    USPSMedia = "USPSMedia"  # USPS Media Mail
    
    # ========== UPS Domestic Services ==========
    UPSGround = "UPSGround"  # UPS Ground
    US_UPSSurePost = "US_UPSSurePost"  # UPS Ground Saver
    UPS2ndDay = "UPS2ndDay"  # UPS 2nd Day Air
    UPS3rdDay = "UPS3rdDay"  # UPS 3 Day Select
    UPSNextDayAir = "UPSNextDayAir"  # UPS Next Day Air
    UPSNextDay = "UPSNextDay"  # UPS Next Day Air Saver
    
    # ========== FedEx Domestic Services ==========
    FedExHomeDelivery = "FedExHomeDelivery"  # FedEx Ground or FedEx Home Delivery
    FedExSmartPost = "FedExSmartPost"  # FedEx Ground Economy
    FedEx2Day = "FedEx2Day"  # FedEx 2Day
    FedExExpressSaver = "FedExExpressSaver"  # FedEx Express Saver
    FedExPriorityOvernight = "FedExPriorityOvernight"  # FedEx Priority Overnight
    FedExStandardOvernight = "FedExStandardOvernight"  # FedEx Standard Overnight
    FedEx2DayOneRatePak = "FedEx2DayOneRatePak"  # FedEx 2Day One Rate Pak
    FedEx2DayOneRateSmallBox = "FedEx2DayOneRateSmallBox"  # FedEx 2Day One Rate Small Box
    FedEx2DayOneRateMediumBox = "FedEx2DayOneRateMediumBox"  # FedEx 2Day One Rate Medium Box
    FedEx2DayOneRateLargeBox = "FedEx2DayOneRateLargeBox"  # FedEx 2Day One Rate Large Box
    FedEx2DayOneRateExtraLargeBox = "FedEx2DayOneRateExtraLargeBox"  # FedEx 2Day One Rate Extra Large Box
    
    # ========== eBay Services ==========
    US_eBayStandardEnvelope = "US_eBayStandardEnvelope"  # eBay Standard Envelope for eligible items up to $20
    US_EconomySppedPAK = "US_EconomySppedPAK"  # eBay SpeedPAK Economy
    US_StandardSppedPAK = "US_StandardSppedPAK"  # eBay SpeedPAK Standard
    US_ExpeditedSppedPAK = "US_ExpeditedSppedPAK"  # eBay SpeedPAK Expedited
    US_ExpressSpeedPAK = "US_ExpressSpeedPAK"  # eBay SpeedPAK Express
    
    # ========== Shipping from Outside US (but still domestic) ==========
    EconomyShippingFromOutsideUS = "EconomyShippingFromOutsideUS"  # Economy Shipping from outside US
    StandardShippingFromOutsideUS = "StandardShippingFromOutsideUS"  # Standard Shipping from outside US
    ExpeditedShippingFromOutsideUS = "ExpeditedShippingFromOutsideUS"  # Expedited Shipping from outside US
    
    # ========== Shipping from Canada ==========
    US_EconomyShippingFromCA = "US_EconomyShippingFromCA"  # Economy Shipping from Canada
    US_StandardShippingFromCA = "US_StandardShippingFromCA"  # Standard Shipping from Canada
    US_ExpeditedShippingFromCA = "US_ExpeditedShippingFromCA"  # Expedited Shipping from Canada
    
    # ========== Shipping from Greater China ==========
    US_EconomyShippingFromGC = "US_EconomyShippingFromGC"  # Economy Shipping from Greater China
    US_StandardShippingFromGC = "US_StandardShippingFromGC"  # Standard Shipping from Greater China
    US_ExpeditedShippingFromGC = "US_ExpeditedShippingFromGC"  # Expedited Shipping from Greater China
    
    # ========== Shipping from India ==========
    US_EconomyShippingFromIN = "US_EconomyShippingFromIN"  # Economy Shipping from India
    US_StandardShippingFromIN = "US_StandardShippingFromIN"  # Standard Shipping from India
    US_ExpeditedShippingFromIN = "US_ExpeditedShippingFromIN"  # Expedited Shipping from India
    US_MailServiceFromIndia = "US_MailServiceFromIndia"  # Mail Service from India
    
    # ========== International Carriers Shipping to US ==========
    US_FedExIntlEconomy = "US_FedExIntlEconomy"  # FedEx International Economy from Abroad
    ePacketChina = "ePacketChina"  # ePacket delivery from China
    ePacketHongKong = "ePacketHongKong"  # ePacket delivery from Hong Kong
    
    # ========== UPS Services from Asia ==========
    US_UPSSurePostFromHK = "US_UPSSurePostFromHK"  # UPS SurePost from Hong Kong
    US_UPSSurePostFromCN = "US_UPSSurePostFromCN"  # UPS SurePost from China
    US_UPSSurePostFromTW = "US_UPSSurePostFromTW"  # UPS SurePost from Taiwan
    
    # ========== DHL Services from Asia ==========
    US_DHLExpressFromHK = "US_DHLExpressFromHK"  # DHL Express from Hong Kong
    US_DHLExpressFromCN = "US_DHLExpressFromCN"  # DHL Express from China
    US_DHLExpressFromTW = "US_DHLExpressFromTW"  # DHL Express from Taiwan
    US_DHLEconomyFromHK = "US_DHLEconomyFromHK"  # DHL Economy from Hong Kong
    US_DHLEconomyFromCN = "US_DHLEconomyFromCN"  # DHL Economy from China
    US_DHLEconomyFromTW = "US_DHLEconomyFromTW"  # DHL Economy from Taiwan
    
    # ========== DGM Services from Asia ==========
    US_DGMSmartMailExpeditedFromHK = "US_DGMSmartMailExpeditedFromHK"  # DGM SmartMail Expedited from Hong Kong
    US_DGMSmartMailExpeditedFromCN = "US_DGMSmartMailExpeditedFromCN"  # DGM SmartMail Expedited from China
    US_DGMSmartMailExpeditedFromTW = "US_DGMSmartMailExpeditedFromTW"  # DGM SmartMail Expedited from Taiwan
    US_DGMSmartMailGroundFromHK = "US_DGMSmartMailGroundFromHK"  # DGM SmartMail Ground from Hong Kong
    US_DGMSmartMailGroundFromCN = "US_DGMSmartMailGroundFromCN"  # DGM SmartMail Ground from China
    US_DGMSmartMailGroundFromTW = "US_DGMSmartMailGroundFromTW"  # DGM SmartMail Ground from Taiwan
    
    # ========== Other International Carriers to US ==========
    US_AMZL = "US_AMZL"  # Amazon Shipping
    US_AMZLUK = "US_AMZLUK"  # Amazon Shipping UK
    US_IntlPriorityExpressGM = "US_IntlPriorityExpressGM"  # International Priority Express GlobalMail from Abroad
    US_IntlStandardGM = "US_IntlStandardGM"  # International Standard GlobalMail from Abroad
    US_IntlExpressFromAbroad = "US_IntlExpressFromAbroad"  # International Express from Abroad
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            # Generic Services
            "ShippingMethodStandard": "Standard Shipping (5+ days)",
            "StandardShippingWithAdultSignature": "Standard Shipping with Adult Signature Required",
            "ShippingMethodExpress": "Expedited Shipping (1-3 days)",
            "ExpeditedShippingWithAdultSignature": "Expedited Shipping with Adult Signature Required",
            "Other": "Economy Shipping (5-10 days)",
            "EconomyShippingWithAdultSignature": "Economy Shipping with Adult Signature Required",
            "ShippingMethodOvernight": "Overnight shipping",
            
            # USPS Services
            "USPSParcel": "USPS Ground Advantage - Reliable ground shipping",
            "USPSPriority": "USPS Priority Mail - 1-3 business days",
            "USPSExpressMail": "USPS Priority Mail Express - Overnight to 2 days",
            "USPSMedia": "USPS Media Mail - Economical for books/media",
            
            # UPS Services
            "UPSGround": "UPS Ground - Reliable ground shipping",
            "US_UPSSurePost": "UPS Ground Saver - Economy ground option",
            "UPS2ndDay": "UPS 2nd Day Air - 2 business days",
            "UPS3rdDay": "UPS 3 Day Select - 3 business days",
            "UPSNextDayAir": "UPS Next Day Air - Next business day",
            
            # FedEx Services
            "FedExHomeDelivery": "FedEx Ground or Home Delivery",
            "FedExSmartPost": "FedEx Ground Economy",
            "FedEx2Day": "FedEx 2Day - 2 business days",
            "FedExPriorityOvernight": "FedEx Priority Overnight - Next business day by 10:30am",
            "FedExStandardOvernight": "FedEx Standard Overnight - Next business day by 3pm",
        }


class InternationalShippingServiceEnum(BaseEbayEnum):
    """
    Valid international shipping service codes for eBay US marketplace.
    
    These codes must be used when creating international shipping options in fulfillment policies.
    Only services with ValidForSellingFlow=true and InternationalService=true are included.
    """
    
    # ========== Generic International Services ==========
    StandardInternational = "StandardInternational"  # Standard International Shipping
    ExpeditedInternational = "ExpeditedInternational"  # Expedited International Shipping
    OtherInternational = "OtherInternational"  # Economy International Shipping
    FreightShippingInternational = "FreightShippingInternational"  # Freight Shipping
    
    # ========== USPS International Services ==========
    USPSPriorityMailInternational = "USPSPriorityMailInternational"  # USPS Priority Mail International
    USPSPriorityMailInternationalFlatRateEnvelope = "USPSPriorityMailInternationalFlatRateEnvelope"  # USPS Priority Mail International Flat Rate Envelope
    USPSPriorityMailInternationalSmallFlatRateBox = "USPSPriorityMailInternationalSmallFlatRateBox"  # USPS Priority Mail International Small Flat Rate Box
    USPSPriorityMailInternationalFlatRateBox = "USPSPriorityMailInternationalFlatRateBox"  # USPS Priority Mail International Medium Flat Rate Box
    USPSPriorityMailInternationalLargeFlatRateBox = "USPSPriorityMailInternationalLargeFlatRateBox"  # USPS Priority Mail International Large Flat Rate Box
    USPSPriorityMailInternationalPaddedFlatRateEnvelope = "USPSPriorityMailInternationalPaddedFlatRateEnvelope"  # USPS Priority Mail International Padded Flat Rate Envelope
    USPSPriorityMailInternationalLegalFlatRateEnvelope = "USPSPriorityMailInternationalLegalFlatRateEnvelope"  # USPS Priority Mail International Legal Flat Rate Envelope
    USPSExpressMailInternational = "USPSExpressMailInternational"  # USPS Priority Mail Express International
    USPSExpressMailInternationalFlatRateEnvelope = "USPSExpressMailInternationalFlatRateEnvelope"  # USPS Priority Mail Express International Flat Rate Envelope
    USPSExpressMailInternationalLegalFlatRateEnvelope = "USPSExpressMailInternationalLegalFlatRateEnvelope"  # USPS Priority Mail Express International Legal Flat Rate Envelope
    USPSFirstClassMailInternationalParcel = "USPSFirstClassMailInternationalParcel"  # USPS First Class Package International
    
    # ========== UPS International Services ==========
    UPSWorldWideExpressPlus = "UPSWorldWideExpressPlus"  # UPS Worldwide Express Plus
    UPSWorldWideExpress = "UPSWorldWideExpress"  # UPS Worldwide Express
    UPSWorldWideExpedited = "UPSWorldWideExpedited"  # UPS Worldwide Expedited
    UPSWorldwideSaver = "UPSWorldwideSaver"  # UPS Worldwide Saver
    UPSStandardToCanada = "UPSStandardToCanada"  # UPS Standard to Canada
    
    # ========== FedEx International Services ==========
    FedExInternationalEconomy = "FedExInternationalEconomy"  # FedEx International Economy
    FedExInternationalPriority = "FedExInternationalPriority"  # FedEx International Priority
    FedExGroundInternationalToCanada = "FedExGroundInternationalToCanada"  # FedEx Ground International to Canada
    
    # ========== eBay SpeedPAK International Services ==========
    US_IntlEconomySppedPAK = "US_IntlEconomySppedPAK"  # eBay SpeedPAK Economy
    US_IntlStandardSppedPAK = "US_IntlStandardSppedPAK"  # eBay SpeedPAK Standard
    US_IntlExpeditedSppedPAK = "US_IntlExpeditedSppedPAK"  # eBay SpeedPAK Expedited
    US_IntlExpressSpeedPAK = "US_IntlExpressSpeedPAK"  # eBay SpeedPAK Express
    US_SPEEDPAK_EU_DDU = "US_SPEEDPAK_EU_DDU"  # SpeedPAK DDU Shipping Service
    
    # ========== Shipping from Greater China International ==========
    US_IntlEconomyShippingFromGC = "US_IntlEconomyShippingFromGC"  # Economy Shipping from Greater China to worldwide
    US_IntlStandardShippingFromGC = "US_IntlStandardShippingFromGC"  # Standard Shipping from Greater China to worldwide
    US_IntlExpeditedShippingFromGC = "US_IntlExpeditedShippingFromGC"  # Expedited Shipping from Greater China to worldwide
    
    # ========== Other International Services ==========
    ExpeditedDeliveryToRussia = "ExpeditedDeliveryToRussia"  # Expedited International Courier Delivery to Russia
    US_RUTrackedFromChina = "US_RUTrackedFromChina"  # RU Tracked Packet from China
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            # Generic International
            "StandardInternational": "Standard International Shipping (11-20 days)",
            "ExpeditedInternational": "Expedited International Shipping (7-15 days)",
            "OtherInternational": "Economy International Shipping (13-23 days)",
            "FreightShippingInternational": "International Freight Shipping",
            
            # USPS International
            "USPSPriorityMailInternational": "USPS Priority Mail International (6-10 days)",
            "USPSExpressMailInternational": "USPS Priority Mail Express International (3-5 days)",
            "USPSFirstClassMailInternationalParcel": "USPS First Class Package International (7-21 days)",
            
            # UPS International
            "UPSWorldWideExpressPlus": "UPS Worldwide Express Plus - Fastest international",
            "UPSWorldWideExpress": "UPS Worldwide Express - 1-3 business days",
            "UPSWorldWideExpedited": "UPS Worldwide Expedited - 2-5 business days",
            "UPSWorldwideSaver": "UPS Worldwide Saver - End of next business day",
            "UPSStandardToCanada": "UPS Standard to Canada - Economical to Canada",
            
            # FedEx International
            "FedExInternationalEconomy": "FedEx International Economy - 4-6 business days",
            "FedExInternationalPriority": "FedEx International Priority - 1-3 business days",
            "FedExGroundInternationalToCanada": "FedEx Ground to Canada - Economical to Canada",
            
            # eBay SpeedPAK
            "US_IntlEconomySppedPAK": "eBay SpeedPAK Economy - Tracked economy service",
            "US_IntlStandardSppedPAK": "eBay SpeedPAK Standard - Tracked standard service",
            "US_IntlExpeditedSppedPAK": "eBay SpeedPAK Expedited - Tracked expedited service",
            "US_IntlExpressSpeedPAK": "eBay SpeedPAK Express - Tracked express service",
        }