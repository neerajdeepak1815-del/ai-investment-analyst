"""Shared 50-stock large-cap screening universe and sector ETF list."""

SCREEN_UNIVERSE: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "LLY", "JPM", "V",
    "UNH", "XOM", "MA", "JNJ", "PG", "HD", "MRK", "AVGO", "CVX", "ABBV",
    "KO", "PEP", "COST", "WMT", "BAC", "MCD", "CRM", "ACN", "LIN", "TMO",
    "ABT", "CSCO", "DHR", "NEE", "TXN", "VZ", "INTC", "ADBE", "NFLX", "CMCSA",
    "PM", "RTX", "HON", "UPS", "AMGN", "IBM", "GS", "CAT", "BA", "MMM",
]

# Static metadata avoids slow/rate-limited per-ticker info() calls on cloud hosts.
TICKER_META: dict[str, dict[str, str]] = {
    "AAPL": {"name": "Apple Inc.", "sector": "Technology"},
    "MSFT": {"name": "Microsoft Corp.", "sector": "Technology"},
    "GOOGL": {"name": "Alphabet Inc.", "sector": "Communication Services"},
    "AMZN": {"name": "Amazon.com Inc.", "sector": "Consumer Discretionary"},
    "NVDA": {"name": "NVIDIA Corp.", "sector": "Technology"},
    "META": {"name": "Meta Platforms Inc.", "sector": "Communication Services"},
    "BRK-B": {"name": "Berkshire Hathaway Inc.", "sector": "Financials"},
    "LLY": {"name": "Eli Lilly and Co.", "sector": "Health Care"},
    "JPM": {"name": "JPMorgan Chase & Co.", "sector": "Financials"},
    "V": {"name": "Visa Inc.", "sector": "Financials"},
    "UNH": {"name": "UnitedHealth Group Inc.", "sector": "Health Care"},
    "XOM": {"name": "Exxon Mobil Corp.", "sector": "Energy"},
    "MA": {"name": "Mastercard Inc.", "sector": "Financials"},
    "JNJ": {"name": "Johnson & Johnson", "sector": "Health Care"},
    "PG": {"name": "Procter & Gamble Co.", "sector": "Consumer Staples"},
    "HD": {"name": "Home Depot Inc.", "sector": "Consumer Discretionary"},
    "MRK": {"name": "Merck & Co. Inc.", "sector": "Health Care"},
    "AVGO": {"name": "Broadcom Inc.", "sector": "Technology"},
    "CVX": {"name": "Chevron Corp.", "sector": "Energy"},
    "ABBV": {"name": "AbbVie Inc.", "sector": "Health Care"},
    "KO": {"name": "Coca-Cola Co.", "sector": "Consumer Staples"},
    "PEP": {"name": "PepsiCo Inc.", "sector": "Consumer Staples"},
    "COST": {"name": "Costco Wholesale Corp.", "sector": "Consumer Staples"},
    "WMT": {"name": "Walmart Inc.", "sector": "Consumer Staples"},
    "BAC": {"name": "Bank of America Corp.", "sector": "Financials"},
    "MCD": {"name": "McDonald's Corp.", "sector": "Consumer Discretionary"},
    "CRM": {"name": "Salesforce Inc.", "sector": "Technology"},
    "ACN": {"name": "Accenture plc", "sector": "Technology"},
    "LIN": {"name": "Linde plc", "sector": "Materials"},
    "TMO": {"name": "Thermo Fisher Scientific Inc.", "sector": "Health Care"},
    "ABT": {"name": "Abbott Laboratories", "sector": "Health Care"},
    "CSCO": {"name": "Cisco Systems Inc.", "sector": "Technology"},
    "DHR": {"name": "Danaher Corp.", "sector": "Health Care"},
    "NEE": {"name": "NextEra Energy Inc.", "sector": "Utilities"},
    "TXN": {"name": "Texas Instruments Inc.", "sector": "Technology"},
    "VZ": {"name": "Verizon Communications Inc.", "sector": "Communication Services"},
    "INTC": {"name": "Intel Corp.", "sector": "Technology"},
    "ADBE": {"name": "Adobe Inc.", "sector": "Technology"},
    "NFLX": {"name": "Netflix Inc.", "sector": "Communication Services"},
    "CMCSA": {"name": "Comcast Corp.", "sector": "Communication Services"},
    "PM": {"name": "Philip Morris International Inc.", "sector": "Consumer Staples"},
    "RTX": {"name": "RTX Corp.", "sector": "Industrials"},
    "HON": {"name": "Honeywell International Inc.", "sector": "Industrials"},
    "UPS": {"name": "United Parcel Service Inc.", "sector": "Industrials"},
    "AMGN": {"name": "Amgen Inc.", "sector": "Health Care"},
    "IBM": {"name": "International Business Machines Corp.", "sector": "Technology"},
    "GS": {"name": "Goldman Sachs Group Inc.", "sector": "Financials"},
    "CAT": {"name": "Caterpillar Inc.", "sector": "Industrials"},
    "BA": {"name": "Boeing Co.", "sector": "Industrials"},
    "MMM": {"name": "3M Co.", "sector": "Industrials"},
}


def ticker_meta(ticker: str) -> dict[str, str]:
    return TICKER_META.get(ticker.upper(), {"name": ticker.upper(), "sector": ""})


SECTOR_ETFS: dict[str, str] = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLC": "Communication Services",
}
