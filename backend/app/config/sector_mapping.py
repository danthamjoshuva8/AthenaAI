from app.models.sector import Sector

YAHOO_TO_SECTOR = {

    "Technology": Sector.IT,

    "Financial Services": Sector.FINANCIAL,

    "Healthcare": Sector.HEALTHCARE,

    "Energy": Sector.OIL_GAS,

    "Real Estate": Sector.REALTY,

    "Utilities": Sector.POWER,

    "Communication Services": Sector.TELECOM,

    "Consumer Defensive": Sector.FMCG,

    "Consumer Cyclical": Sector.AUTO,

    "Basic Materials": Sector.METAL,

    "Industrials": Sector.CAPITAL_GOODS
}