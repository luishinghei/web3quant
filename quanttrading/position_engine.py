from quanttrading.binance_fetcher import BinanceFetcher
from quanttrading.strategies import BaseStrat
from quanttrading.symbol_manager import SymbolInfo
from quanttrading.log import init_logger
from quanttrading import position_engine


logger = init_logger('pos')


def calculate_signals(strats: list[BaseStrat]) -> dict[tuple, float]:
    signals = {}
    for strat in strats:
        signal = strat.generate_signal()
        signals[strat.strat_key] = signal
    return signals


def _calculate_target_amount(signal: float, symbol: str, balance: float, final_weight: float, symbols_info: dict[str, SymbolInfo]) -> float:
    symbol_info = symbols_info[symbol]
    anchor_price = symbol_info.anchor_price
    amount_precision = symbol_info.amount_precision
    target_usd = signal * balance * final_weight
    target_amount = float(round(target_usd / anchor_price, amount_precision))
    return target_amount


def calculate_target_amount_by_strat(strats: list[BaseStrat], signals: dict[tuple, float], balance: float, symbols_info: dict[str, SymbolInfo]) -> float:
    target_amount_by_strat = {}
    for strat in strats:
        # target_amount = calculate_target_amount(strat, balance, symbols_info)
        signal = signals[strat.strat_key]
        target_amount = _calculate_target_amount(signal, strat.symbol, balance, strat.final_weight, symbols_info)
        target_amount_by_strat[strat.strat_key] = target_amount
    return target_amount_by_strat


def aggregate_target_amount_by_symbol(target_amount_by_strat: dict[tuple, float]) -> dict[str, float]:
    target_amount_by_symbol = {}
    for strat_key, target_amount in target_amount_by_strat.items():
        symbol = strat_key[2]
        target_amount_by_symbol[symbol] = target_amount_by_symbol.get(symbol, 0.0) + target_amount
    return target_amount_by_symbol


def calculate_notional_value(target_amount_by_symbol: dict[str, float], binance_fetcher: BinanceFetcher, last_prices: dict[str, float] | None = None) -> float:
    notional_value = 0.0
    for symbol, target_amount in target_amount_by_symbol.items():
        if last_prices is not None and symbol in last_prices:
            last_price = last_prices[symbol]
        else:
            last_price = binance_fetcher.fetch_last_price(f'{symbol}/USDT:USDT')
        notional_value += target_amount * last_price
        # logger.info(f'{symbol} notional value: {notional_value}')
    # logger.info(f'total notional value: {notional_value}')
    return notional_value


def calculate_notional_value_symbols_info(target_amount_by_symbol: dict[str, float], symbols_info: dict[str, SymbolInfo]) -> dict[str, float]:
    notional_value = 0.0
    for symbol, target_amount in target_amount_by_symbol.items():
        symbol_info = symbols_info[symbol]
        anchor_price = symbol_info.anchor_price
        notional_value += target_amount * anchor_price
        # logger.info(f'{symbol} notional value: {notional_value}')
    # logger.info(f'total notional value: {notional_value}')
    return notional_value


def calculate_delta_amount(target_amount_by_symbol: dict[str, float], current_positions: dict[str, float]) -> dict[str, float]:
    """Calculates the order deltas needed to reach target amounts.

    Includes symbols that have an existing position but no target amount,
    in which case the delta will close the position (e.g., current 0.2 -> delta -0.2).
    """
    delta_amount_dict = {}

    # Use the union of symbols so we also handle closing out symbols not present in targets
    symbols = set(target_amount_by_symbol.keys()) | set(current_positions.keys())

    for symbol in symbols:
        target_amount = target_amount_by_symbol.get(symbol, 0.0)
        current_position = current_positions.get(symbol, 0.0)
        delta_amount = target_amount - current_position
        delta_amount_dict[symbol] = delta_amount

    return delta_amount_dict


def calculate_leverage_real(target_amount_by_symbol: dict[str, float], binance_fetcher: BinanceFetcher, balance: float, last_prices: dict[str, float] | None = None) -> dict[str, float]:
    notional_value = position_engine.calculate_notional_value(target_amount_by_symbol, binance_fetcher, last_prices)
    return notional_value / balance


def calculate_leverage_ref(target_amount_by_symbol: dict[str, float], symbols_info: dict[str, SymbolInfo], balance: float) -> dict[str, float]:
    notional_value = position_engine.calculate_notional_value_symbols_info(target_amount_by_symbol, symbols_info)
    return notional_value / balance


def deleverage(target_amount_by_symbol: dict[str, float], leverage: float, max_leverage: float, symbols_info: dict[str, SymbolInfo]) -> dict[str, float]:
    """Deleverages and rounds the target amount by symbol.

    Amounts are rounded using each symbol's amount_precision from symbols_info.
    """
    factor = max_leverage / leverage
    deleveraged = {}
    for symbol, target_amount in target_amount_by_symbol.items():
        symbol_info = symbols_info.get(symbol)
        if symbol_info is None:
            # Fallback without rounding if symbol info is unavailable
            deleveraged[symbol] = target_amount * factor
            continue
        amount_precision = symbol_info.amount_precision
        deleveraged_target_amount = float(round(target_amount * factor, amount_precision))
        deleveraged[symbol] = deleveraged_target_amount
    return deleveraged
