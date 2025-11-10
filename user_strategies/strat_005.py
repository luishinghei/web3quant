import pandas as pd
import numpy as np
from quanttrading.strategies import BaseStrat
from quanttrading.config_manager import StratConfig
from quanttrading.binance_fetcher import BinanceFetcher


class VolBM(BaseStrat):
    def __init__(self, config: StratConfig, binance_fetcher: BinanceFetcher) -> None:
        self.binance_fetcher = binance_fetcher
        super().__init__(config)
    
    def fetch_alpha(self) -> pd.DataFrame:
        return self.binance_fetcher.load_tbl_data(self.symbol, self.timeframe)

    def calculate_signal_df(self, df: pd.DataFrame, params: dict, model: str) -> pd.DataFrame:
        window1 = params['param_1']
        window2 = params['param_2']
        threshold = params['param_3']

        if model == 'B':
            return self.b(df, window1, window2, threshold)
        elif model == 'R':
            return self.r(df, window1, window2, threshold)
        else:
            raise ValueError(f'Invalid model: {model}')

    def b(self, df: pd.DataFrame, window1: int, window2: int, threshold: float) -> pd.DataFrame:
        df['ma'] = df['value'].rolling(window1).mean()
        df['std'] = df['value'].rolling(window2).std()
        df['z'] = (df['value'] - df['ma']) / df['std']
        df['signal'] = np.where(df['z'] > threshold, 1, 0)
        return df
    
    def r(self, df: pd.DataFrame, window1: int, window2: int, threshold: float) -> pd.DataFrame:
        df['ma'] = df['value'].rolling(window1).mean()
        df['rank'] = df['ma'].rolling(window2).rank(pct=True)
        df['signal'] = np.where(df['rank'] > threshold, 1, 0)
        return df
