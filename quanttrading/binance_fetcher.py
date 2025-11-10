import pandas as pd
import os
from dotenv import load_dotenv
import requests
from quanttrading.log import init_logger
from quanttrading import tg
from quanttrading.helper import is_last_bar_closed, is_data_latest
import time

load_dotenv()
logger = init_logger('binance')


class BinanceFetcher:
    def __init__(self, folder: str = 'user_data') -> None:
        self.user_data_folder = folder
        self.csv_folder = f'{folder}/data'
        os.makedirs(self.csv_folder, exist_ok=True)
        self.remote_base_url = os.getenv('DO_FETCHER_BASE_URL', '').rstrip('/')
        self.remote_api_key = os.getenv('DO_FETCHER_API_KEY', '')

    def _load_series(
        self,
        symbol: str,
        timeframe: str,
        filename_prefix: str,
        fetcher_fn,
        update_msg_title: str,
    ) -> pd.DataFrame:
        symbol_short = symbol.split('/')[0]
        filepath = f'{self.csv_folder}/{filename_prefix}_{symbol_short}_{timeframe}.csv'
        df_csv: pd.DataFrame | None = None
        if os.path.exists(filepath):
            df_csv = pd.read_csv(filepath)
            df_csv.set_index('ts', inplace=True)
            df_csv.index = pd.to_datetime(df_csv.index)
            df_csv.sort_index(ascending=True, inplace=True)
            df_since = df_csv.index.min()
            df_until = df_csv.index.max()
            logger.info(f'{len(df_csv)} rows of data from {df_since.strftime("%Y-%m-%d %H:%M:%S")} to {df_until.strftime("%Y-%m-%d %H:%M:%S")} loaded from {filepath}')
            if is_data_latest(df_csv, timeframe):
                logger.info('Data is latest, returning cached data')
                return df_csv
        else:
            raise FileNotFoundError(f'File {filepath} not found')

        since_dt = pd.to_datetime('now') - pd.Timedelta(days=30)
        since = int(since_dt.timestamp() * 1000 + 60)
        logger.info(f'Fetching {filename_prefix} data for {symbol} {timeframe} since {since_dt.strftime("%Y-%m-%d %H:%M:%S")}')
        df = fetcher_fn(symbol, timeframe, since)
        if df.empty:
            return df_csv if df_csv is not None else pd.DataFrame()
        if not is_last_bar_closed(df, timeframe):
            logger.info('Last bar is not closed, removing last bar')
            df = df[:-1].copy()
        df_since = df.index.min()
        df_until = df.index.max()
        logger.info(f'{len(df)} rows of data from {df_since.strftime("%Y-%m-%d %H:%M:%S")} to {df_until.strftime("%Y-%m-%d %H:%M:%S")}')

        df_all = pd.concat([df_csv, df]) if df_csv is not None else df
        df_all = df_all.sort_values(by='t', ascending=True)
        df_all = df_all.drop_duplicates(subset=['t'], keep='last')

        logger.info(f'Concatenated {len(df_all)} rows of data from {df_since.strftime("%Y-%m-%d %H:%M:%S")} to {df_until.strftime("%Y-%m-%d %H:%M:%S")}')

        last_timestamp = df_all.index.max()
        last_value = df_all.iloc[-1]['value']

        if update_msg_title is not None:
            msg = f'{update_msg_title}\n'
            msg += f'{symbol} {timeframe}\n'
            msg += f'Last timestamp: {last_timestamp} \n'
            msg += f'Last value: {last_value}'
            tg.send_message(msg)

        df_all.to_csv(filepath)
        logger.info(f'Saved {len(df_all)} rows of data to {filepath}')
        return df_all


    def load_oi_data(self, symbol: str, timeframe: str = '1h') -> pd.DataFrame:
        return self._load_series(
            symbol=symbol,
            timeframe=timeframe,
            filename_prefix='oi',
            fetcher_fn=self._fetch_oi_data,
            update_msg_title=None,
        )
    
    
    def load_g_ls_data(self, symbol: str, timeframe: str = '1h') -> pd.DataFrame:
        return self._load_series(
            symbol=symbol,
            timeframe=timeframe,
            filename_prefix='g_ls',
            fetcher_fn=self._fetch_g_ls_data,
            update_msg_title=None,
        )
    
    
    def load_t_ls_data(self, symbol: str, timeframe: str = '1h') -> pd.DataFrame:
        return self._load_series(
            symbol=symbol,
            timeframe=timeframe,
            filename_prefix='t_ls',
            fetcher_fn=self._fetch_t_ls_data,
            update_msg_title=None,
        )
    
    
    def load_ttp_data(self, symbol: str, timeframe: str = '1h') -> pd.DataFrame:
        return self._load_series(
            symbol=symbol,
            timeframe=timeframe,
            filename_prefix='ttp',
            fetcher_fn=self._fetch_ttp_data,
            update_msg_title=None,
        )
        
    def load_tsl_data(self, symbol: str, timeframe: str = '1h') -> pd.DataFrame:
        return self._load_series(
            symbol=symbol,
            timeframe=timeframe,
            filename_prefix='tsl',
            fetcher_fn=self._fetch_tsl_data,
            update_msg_title=None,
        )
    
    def load_tbl_data(self, symbol: str, timeframe: str = '1h') -> pd.DataFrame:
        return self._load_series(
            symbol=symbol,
            timeframe=timeframe,
            filename_prefix='tbl',
            fetcher_fn=self._fetch_tbl_data,
            update_msg_title=None,
        )

    def _fetch_series_remote(self, endpoint: str, params: dict, alert_prefix: str) -> pd.DataFrame:
        try:
            url = f'{self.remote_base_url}{endpoint}'
            headers = {'X-API-Key': self.remote_api_key}
            response = requests.get(url, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()  # [{t, value}]
            if not data:
                logger.error(f'Failed to fetch {alert_prefix} data from remote fetcher')
                tg.send_message(f'Failed to fetch {alert_prefix} data from remote fetcher')
                return pd.DataFrame()
            df = pd.DataFrame(data)
            if 't' not in df or 'value' not in df:
                logger.error(f'Remote {alert_prefix} payload missing required fields')
                return pd.DataFrame()
            df['ts'] = pd.to_datetime(df['t'], unit='s')
            df['t'] = df['t'].astype(int)
            df['value'] = df['value'].astype(float)
            df.set_index('ts', inplace=True)
            df.sort_index(ascending=True, inplace=True)
            if df.isna().any().any():
                logger.error(f'NaN values found in remote {alert_prefix} data')
                return pd.DataFrame()
            return df
        except Exception as e:
            logger.error(f'Remote {alert_prefix} fetch error: {e}')
            tg.send_message(f'Remote {alert_prefix} fetch error: {e}')
            return pd.DataFrame()

    def _fetch_oi_data(self, symbol: str, timeframe: str = '1h', since: int | None = None) -> pd.DataFrame:
        base = symbol.split('/')[0].strip()
        params = {'symbol': base, 'timeframe': timeframe}
        if since is not None:
            params['since_ms'] = since
        return self._fetch_series_remote(endpoint='/oi', params=params, alert_prefix='oi')
        
    
    def _fetch_g_ls_data(self, symbol: str, timeframe: str = '1h', since: int | None = None) -> pd.DataFrame:
        base = symbol.split('/')[0].strip()
        params = {'symbol': base, 'timeframe': timeframe}
        if since is not None:
            params['since_ms'] = since
        return self._fetch_series_remote(endpoint='/g-ls', params=params, alert_prefix='g_ls')
    
    
    def _fetch_t_ls_data(self, symbol: str, timeframe: str = '1h', since: int | None = None) -> pd.DataFrame:
        base = symbol.split('/')[0].strip()
        params = {'symbol': base, 'timeframe': timeframe}
        if since is not None:
            params['since_ms'] = since
        return self._fetch_series_remote(endpoint='/t-ls', params=params, alert_prefix='t_ls')
    
    
    def _fetch_ttp_data(self, symbol: str, timeframe: str = '1h', since: int | None = None) -> pd.DataFrame:
        base = symbol.split('/')[0].strip()
        params = {'symbol': base, 'timeframe': timeframe}
        if since is not None:
            params['since_ms'] = since
        return self._fetch_series_remote(endpoint='/ttp', params=params, alert_prefix='ttp')


    def _fetch_tsl_data(self, symbol: str, timeframe: str = '1h', since: int | None = None) -> pd.DataFrame:
        base = symbol.split('/')[0].strip()
        params = {'symbol': base, 'timeframe': timeframe}
        if since is not None:
            params['since_ms'] = since
        return self._fetch_series_remote(endpoint='/tsl', params=params, alert_prefix='tsl')


    def _fetch_tbl_data(self, symbol: str, timeframe: str = '1h', since: int | None = None) -> pd.DataFrame:
        base = symbol.split('/')[0].strip()
        params = {'symbol': base, 'timeframe': timeframe}
        if since is not None:
            params['since_ms'] = since
        return self._fetch_series_remote(endpoint='/tbl', params=params, alert_prefix='tbl')
        
    def fetch_anchor_close_price(self, symbol: str, start: str) -> float:
        since = int(pd.to_datetime(start).timestamp() * 1000)
        timeframe = '1h'
        try:
            base = symbol.split('/')[0].strip()
            params = {'symbol': base, 'timeframe': timeframe, 'since_ms': since}
            url = f'{self.remote_base_url}/ohlcv-close'
            headers = {'X-API-Key': self.remote_api_key}
            logger.info(f'Fetching anchor close via remote {url} params={params}')
            response = requests.get(url, params=params, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()  # {'close': float}
            if 'close' not in data:
                raise ValueError('Remote close payload missing "close"')
            return float(data['close'])
        except Exception as e:
            logger.error(f'Error fetching anchor close via remote for {symbol}: {e}')
            raise
        

    def fetch_last_price(self, symbol: str) -> float:
        try:
            base = symbol.split('/')[0].strip()
            params = {'symbol': base}
            url = f'{self.remote_base_url}/last-price'
            headers = {'X-API-Key': self.remote_api_key}
            logger.info(f'Fetching last price via remote {url} params={params}')
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()  # {'last': float}
            if 'last' not in data:
                raise ValueError('Remote last payload missing "last"')
            return float(data['last'])
        except Exception as e:
            logger.error(f'Error fetching last price via remote for {symbol}: {e}')
            raise
    
    def fetch_all_last_prices(self, symbols_info: dict) -> dict[str, float]:
        """
        Fetch last prices for all symbols in symbols_info.
        On success: saves to CSV with timestamp.
        On failure: loads from CSV fallback with age validation.
        
        Returns: dict mapping symbol -> price
        Raises: Exception if fetching fails and CSV fallback is unavailable or too old
        """
        csv_path = f'{self.user_data_folder}/last_prices.csv'
        max_age_seconds = 30 * 60  # 30 minutes
        
        last_prices = {}
        fetch_success = True
        
        # Try to fetch all prices
        try:
            logger.info(f'Fetching last prices for {len(symbols_info)} symbols')
            for symbol in symbols_info.keys():
                try:
                    price = self.fetch_last_price(symbol)
                    last_prices[symbol] = price
                except Exception as e:
                    logger.error(f'Failed to fetch price for {symbol}: {e}')
                    fetch_success = False
                    break
            
            if fetch_success:
                # Save to CSV with timestamp
                now = int(time.time())
                df = pd.DataFrame([
                    {'symbol': symbol, 'price': price, 'timestamp': now}
                    for symbol, price in last_prices.items()
                ])
                df.to_csv(csv_path, index=False)
                logger.info(f'Saved {len(last_prices)} prices to {csv_path}')
                return last_prices
        except Exception as e:
            logger.error(f'Error in fetch_all_last_prices: {e}')
            fetch_success = False
        
        # If fetch failed, try CSV fallback
        if not fetch_success:
            logger.warning('Price fetch failed, attempting CSV fallback')
            tg.send_message('⚠️ ALERT: Price fetch failed, using CSV fallback')
            
            if not os.path.exists(csv_path):
                error_msg = 'CSV fallback unavailable: file does not exist'
                logger.error(error_msg)
                tg.send_message(f'❌ ERROR: {error_msg}')
                raise Exception(error_msg)
            
            try:
                df = pd.read_csv(csv_path)
                if df.empty or 'symbol' not in df or 'price' not in df or 'timestamp' not in df:
                    raise ValueError('CSV file is empty or missing required columns')
                
                # Check age of data
                csv_timestamp = int(df['timestamp'].iloc[0])
                age_seconds = int(time.time()) - csv_timestamp
                
                if age_seconds > max_age_seconds:
                    error_msg = f'CSV fallback data too old: {age_seconds/60:.1f} minutes (max {max_age_seconds/60:.0f} minutes)'
                    logger.error(error_msg)
                    tg.send_message(f'❌ ERROR: {error_msg}')
                    raise Exception(error_msg)
                
                # Load prices from CSV
                fallback_prices = dict(zip(df['symbol'], df['price']))
                logger.warning(f'Using fallback prices from CSV (age: {age_seconds/60:.1f} minutes)')
                tg.send_message(f'Using fallback prices (age: {age_seconds/60:.1f} min)')
                return fallback_prices
                
            except Exception as e:
                error_msg = f'Failed to load CSV fallback: {e}'
                logger.error(error_msg)
                tg.send_message(f'❌ ERROR: {error_msg}')
                raise
        