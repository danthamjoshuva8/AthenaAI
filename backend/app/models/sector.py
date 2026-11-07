
from enum import Enum


class Sector(str, Enum):
    """
    Defines the supported market sectors for stock classification.
    """

    AUTO = "AUTO"                       # Automobile and automobile components.
    BANKING = "BANKING"                 # Banking and banking services.
    FINANCIAL = "FINANCIAL"             # Financial services and institutions.
    FMCG = "FMCG"                       # Fast-moving consumer goods.
    HEALTHCARE = "HEALTHCARE"           # Healthcare services and equipment.
    IT = "IT"                           # Information technology and software.
    METAL = "METAL"                     # Metal and mining industries.
    OIL_GAS = "OIL_GAS"                 # Oil, gas and energy exploration.
    PHARMA = "PHARMA"                   # Pharmaceutical companies.
    POWER = "POWER"                     # Power generation and distribution.
    REALTY = "REALTY"                   # Real estate and property development.
    TELECOM = "TELECOM"                 # Telecommunications services.
    MEDIA = "MEDIA"                     # Media and entertainment.
    CAPITAL_GOODS = "CAPITAL_GOODS"     # Industrial and capital goods.
    CHEMICAL = "CHEMICAL"               # Chemical manufacturing.
    TEXTILE = "TEXTILE"                 # Textile and apparel industries.
    UNKNOWN = "UNKNOWN"                 # Sector not identified or classified.
