import pandas as pd
import os

from abc import ABC, abstractmethod

from quanttrading.config_manager import StratConfig
from quanttrading.log import init_logger
from quanttrading import tg


logger = init_logger('strats')


class BaseStrat(ABC):
    def __init__(self, config: StratConfig) -> None:
        self.config = config
        
        self.id = config.id
        self.name = config.name
        self.symbol = config.symbol.split('/')[0]
        self.timeframe = config.timeframe
        self.order_type = config.order_type
        self.final_weight = config.final_weight
        self.param_sets = config.params  # list[StratParams]

        self.strat_name = f'{self.id:03d}-{self.name}'
        self.csv_folder = f'user_data/data'
        self.strat_key = self._generate_key()
    
    
    def _generate_key(self) -> tuple:
        return (self.id, self.name, self.symbol, self.timeframe)


    def calculate_agg_signal_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculates the aggregated signals for multiple parameter sets and adds them to DataFrame."""
        df = df.copy()
        signals_df = pd.DataFrame(index=df.index)
        
        for _, p in enumerate(self.param_sets):
            param_dict = {f'param_{i+1}': v for i, v in enumerate(p.param)}

            df_temp = self.calculate_signal_df(df, param_dict, p.model)
            signal = df_temp['signal'].iloc[-1]
            logger.info(f'{self.id:03d} {self.symbol} {self.timeframe} {param_dict} Signal: {signal}')
            
            col_name = f"{p.model}_" + '-'.join(f'{v}' for v in param_dict.values())
            signals_df[col_name] = df_temp['signal']
            
        signals_df['signal'] = signals_df.mean(axis=1)
        signal = signals_df['signal'].iloc[-1]
        logger.info(f'{self.id:03d} {self.symbol} {self.timeframe} Signal(agg): {signal}')
        
        file_path = self.get_signal_csv_path(self.strat_name)
        if os.path.exists(file_path):
            df_csv = pd.read_csv(file_path, index_col=0, parse_dates=True)
            csv_last_timestamp = df_csv.index.max()
        else:
            csv_last_timestamp = None
            
        last_timestamp = signals_df.index.max()
        if last_timestamp != csv_last_timestamp:
            msg = f'SIGNAL UPDATED\n'
            msg += f'{self.strat_name}\n'
            msg += f'Last timestamp: {last_timestamp} \n'
            msg += f'Last signal: {signal}'
            tg.send_message(msg)
        
        self.to_signal_csv(signals_df, self.strat_name)
        
        return signals_df
    
    def get_signal_csv_path(self, strat_name: str) -> str:
        return f'{self.csv_folder}/{strat_name}.csv'
    
    def to_signal_csv(self, df: pd.DataFrame, strat_name: str) -> None:
        file_path = self.get_signal_csv_path(strat_name)
        
        if df is None or df.empty:
            logger.debug(f'No data to save for {strat_name} strategy')
            df =pd.DataFrame()
            
        df.to_csv(file_path)
        logger.debug(f'Saved {len(df)} rows for {strat_name} strategy')


    def generate_signal(self) -> float:
        df_alpha = self.fetch_alpha()
        df = self.calculate_agg_signal_df(df_alpha)
        
        return df['signal'].iloc[-1]
    

    @abstractmethod
    def fetch_alpha(self) -> pd.DataFrame:
        pass
    
    @abstractmethod
    def calculate_signal_df(self, df: pd.DataFrame, params: dict, model: str) -> pd.DataFrame:
        pass

    def __repr__(self):
        return f'Strategy({self.strat_name})'
