from quanttrading import config_manager
from quanttrading import roostoo
import pandas as pd
from rich import print
from quanttrading import symbol_manager
from user_strategies.strat_001 import Strat001
from user_strategies.strat_002 import TtpR
from user_strategies.strat_003 import GlsR
from user_strategies.strat_004 import TtaR
from user_strategies.strat_005 import VolBM
from user_strategies.strat_006 import VolMS
from quanttrading.binance_fetcher import BinanceFetcher
from quanttrading.monitor import Monitor
from quanttrading import position_engine
import time
from datetime import datetime, timezone


BALANCE = 100000
MAX_LEVERAGE = 0.99
FILE_NAME = 'user_data/data/df_final.csv'



df = pd.read_csv(FILE_NAME)
configs = config_manager.create_config_from_df(df)

weights = config_manager.get_weights(df)
print(weights)

binance_fetcher = BinanceFetcher()
monitor = Monitor()

exchange_info = roostoo.get_exchange_info()

symbol_names = df['sym'].unique().tolist()
symbols_info = symbol_manager.build_symbols_info(exchange_info, symbol_names, binance_fetcher)

print(symbols_info)

# 0 to 13
strat0 = TtpR(configs[0], binance_fetcher)
strat1 = TtpR(configs[1], binance_fetcher)
strat2 = TtpR(configs[2], binance_fetcher)
strat3 = TtpR(configs[3], binance_fetcher)
strat4 = TtpR(configs[4], binance_fetcher)
strat5 = TtpR(configs[5], binance_fetcher)
strat6 = TtpR(configs[6], binance_fetcher)
strat7 = TtpR(configs[7], binance_fetcher)
strat8 = TtpR(configs[8], binance_fetcher)
strat9 = TtpR(configs[9], binance_fetcher)
strat10 = TtpR(configs[10], binance_fetcher)
strat11 = TtpR(configs[11], binance_fetcher)
strat12 = TtpR(configs[12], binance_fetcher)
strat13 = TtpR(configs[13], binance_fetcher)

# 14 to 28
strat14 = GlsR(configs[14], binance_fetcher)
strat15 = GlsR(configs[15], binance_fetcher)
strat16 = GlsR(configs[16], binance_fetcher)
strat17 = GlsR(configs[17], binance_fetcher)
strat18 = GlsR(configs[18], binance_fetcher)
strat19 = GlsR(configs[19], binance_fetcher)
strat20 = GlsR(configs[20], binance_fetcher)
strat21 = GlsR(configs[21], binance_fetcher)
strat22 = GlsR(configs[22], binance_fetcher)
strat23 = GlsR(configs[23], binance_fetcher)
strat24 = GlsR(configs[24], binance_fetcher)
strat25 = GlsR(configs[25], binance_fetcher)
strat26 = GlsR(configs[26], binance_fetcher)
strat27 = GlsR(configs[27], binance_fetcher)
strat28 = GlsR(configs[28], binance_fetcher)

# 29 to 41
strat29 = TtaR(configs[29], binance_fetcher)
strat30 = TtaR(configs[30], binance_fetcher)
strat31 = TtaR(configs[31], binance_fetcher)
strat32 = TtaR(configs[32], binance_fetcher)
strat33 = TtaR(configs[33], binance_fetcher)
strat34 = TtaR(configs[34], binance_fetcher)
strat35 = TtaR(configs[35], binance_fetcher)
strat36 = TtaR(configs[36], binance_fetcher)
strat37 = TtaR(configs[37], binance_fetcher)
strat38 = TtaR(configs[38], binance_fetcher)
strat39 = TtaR(configs[39], binance_fetcher)
strat40 = TtaR(configs[40], binance_fetcher)
strat41 = TtaR(configs[41], binance_fetcher)

# 42 to 45
strat42 = Strat001(configs[42], binance_fetcher)
strat43 = Strat001(configs[43], binance_fetcher)
strat44 = Strat001(configs[44], binance_fetcher)
strat45 = Strat001(configs[45], binance_fetcher)

# 46 to 50
strat46 = VolBM(configs[46], binance_fetcher)
strat47 = VolBM(configs[47], binance_fetcher)
strat48 = VolBM(configs[48], binance_fetcher)
strat49 = VolBM(configs[49], binance_fetcher)
strat50 = VolBM(configs[50], binance_fetcher)

# 51 to 53
strat51 = VolMS(configs[51], binance_fetcher)
strat52 = VolMS(configs[52], binance_fetcher)
strat53 = VolMS(configs[53], binance_fetcher)


strats = [
    strat0,
    strat1,
    strat2,
    strat3,
    strat4,    
    strat5,
    strat6,
    strat7,
    strat8,
    strat9,
    strat10,
    strat11,
    strat12,
    strat13,
    
    strat14,
    strat15,
    strat16,
    strat17,
    strat18,
    strat19,
    strat20,
    strat21,
    strat22,
    strat23,
    strat24,
    strat25,
    strat26,
    strat27,
    strat28,
    
    strat29,
    strat30,
    strat31,
    strat32,
    strat33,
    strat34,
    strat35,
    strat36,
    strat37,
    strat38,
    strat39,
    strat40,
    strat41,
    
    strat42,
    strat43,
    strat44,
    strat45,
    
    strat46,
    strat47,
    strat48,
    strat49,
    strat50,
    
    strat51,
    strat52,
    strat53,
]

while True:
    now = int(datetime.now(timezone.utc).timestamp())
    
    signals = position_engine.calculate_signals(strats)
    updated = monitor.log_signals(signals, now=now)
    monitor.send_weighted_by_strategy(signals, strats)
    monitor.send_weighted_by_symbol(signals, strats)
    print(f'Signals: {signals}')

    
    target_amount_by_strat = position_engine.calculate_target_amount_by_strat(strats, signals, BALANCE, symbols_info)
    monitor.log_target_amount_by_strat(target_amount_by_strat, now=now)
    print(f'Target amount by strat: {target_amount_by_strat}')

    target_amount_by_symbol = position_engine.aggregate_target_amount_by_symbol(target_amount_by_strat)
    monitor.log_target_amount_by_symbol(target_amount_by_symbol, now=now)
    print(f'Target amount by symbol: {target_amount_by_symbol}')
    
    # Fetch all last prices once for the entire loop
    last_prices = binance_fetcher.fetch_all_last_prices(symbols_info)
    print(f'Last prices fetched: {len(last_prices)} symbols')
    
    leverage_real = position_engine.calculate_leverage_real(target_amount_by_symbol, binance_fetcher, BALANCE, last_prices)
    print(f'Leverage real: {leverage_real}')

    leverage_ref = position_engine.calculate_leverage_ref(target_amount_by_symbol, symbols_info, BALANCE)
    print(f'Leverage ref: {leverage_ref}')

    if leverage_ref > MAX_LEVERAGE:
        deleveraged = position_engine.deleverage(target_amount_by_symbol, leverage_ref, MAX_LEVERAGE, symbols_info)
        print(f'Deleveraged: {deleveraged}')
    else:
        deleveraged = leverage_ref
        
    monitor.log_leverage(leverage_real, leverage_ref, deleveraged, now=now)
    print(f'Leverage: {leverage_real}, {leverage_ref}, {deleveraged}')

    current_positions = roostoo.get_current_postions()
    print(f'Current positions: {current_positions}')

    delta_amounts = position_engine.calculate_delta_amount(target_amount_by_symbol, current_positions)
    monitor.log_delta_amounts(delta_amounts, now=now)
    print(f'Delta amounts: {delta_amounts}')

    success_trades, error_trades = roostoo.trade(delta_amounts, binance_fetcher, last_prices)
    monitor.log_success_trades(success_trades, now=now)
    monitor.log_error_trades(error_trades, now=now)
    
    current_positions = roostoo.get_current_postions()
    monitor.log_current_positions(current_positions, now=now)
    monitor.log_current_balance(current_positions, binance_fetcher, now=now, last_prices=last_prices)
    
    for i in range(300):
        print('.', end='', flush=True)
        time.sleep(1)
