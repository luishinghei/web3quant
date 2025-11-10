from dataclasses import dataclass
from quanttrading.binance_fetcher import BinanceFetcher


# 'MIRA/USD': {
#     'Coin': 'MIRA',
#     'CoinFullName': 'MIRA',
#     'Unit': 'USD',
#     'UnitFullName': 'US Dollar',
#     'CanTrade': True,
#     'PricePrecision': 4,
#     'AmountPrecision': 1,
#     'MiniOrder': 1
# }

@dataclass(frozen=True)
class SymbolInfo:
    coin: str
    coin_full_name: str
    unit: str
    unit_full_name: str
    can_trade: bool
    price_precision: int
    amount_precision: int
    mini_order: int
    anchor_price: float


def build_symbols_info(exchange_info: dict, symbol_names: list[str], binance_fetcher: BinanceFetcher) -> dict[str, SymbolInfo]:
    symbols_info = {}
    
    for _, symbol_info in exchange_info['TradePairs'].items():
        coin = symbol_info['Coin']
        if coin not in symbol_names:
            continue
        coin_full_name = symbol_info['CoinFullName']
        unit = symbol_info['Unit']
        unit_full_name = symbol_info['UnitFullName']
        can_trade = symbol_info['CanTrade']
        price_precision = symbol_info['PricePrecision']
        amount_precision = symbol_info['AmountPrecision']
        mini_order = symbol_info['MiniOrder']
        start = '2025-11-09 00:00:00'
        anchor_price = binance_fetcher.fetch_anchor_close_price(coin + '/' + unit, start)

        symbols_info[coin] = SymbolInfo(
            coin=coin,
            coin_full_name=coin_full_name,
            unit=unit,
            unit_full_name=unit_full_name,
            can_trade=can_trade,
            price_precision=price_precision,
            amount_precision=amount_precision,
            mini_order=mini_order,
            anchor_price=anchor_price
        )
    return symbols_info