from datetime import datetime, timezone
import pandas as pd
import logging

logger = logging.getLogger('helper')


def is_last_bar_closed(df: pd.DataFrame, resolution: str, t_col: str = 't') -> bool:
    resolution_sec_map = {
        '1d': 86400,
        '24h': 86400,
        '12h': 43200,
        '8h': 28800,
        '6h': 21600,
        '4h': 14400,
        '2h': 7200,
        '1h': 3600,
        '30m': 1800,
        '15m': 900,
        '10m': 600,
        '5m': 300,
        '3m': 180,
        '1m': 60,
    }
    
    last_timestamp = df[t_col].iloc[-1]
    last_time = datetime.fromtimestamp(last_timestamp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - last_time
    
    resolution_seconds = resolution_sec_map.get(resolution, 0)
    if resolution_seconds == 0:
        raise ValueError(f"Unsupported resolution: {resolution}")
    
    is_closed = diff.total_seconds() >= resolution_seconds
    
    last_timestamp_readable = datetime.fromtimestamp(last_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    now_readable = now.strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"is_last_bar_closed: {is_closed}, Last timestamp: {last_timestamp_readable}, Now: {now_readable}, Difference: {diff}, Resolution: {resolution}")
    
    return is_closed


def is_data_latest(df: pd.DataFrame, resolution: str, t_col: str = 't', print_info: bool = True) -> bool:
    df = df.copy()
    
    # is_closed = is_last_bar_closed(df, resolution, t_col)
    # if not is_closed:
    #     if print_info:
    #         print(f"Last bar is not closed. Cannot check if data is latest.")
    #     return False
    
    resolution_sec_map = {
        '1d': 86400,
        '24h': 86400,
        '12h': 43200,
        '8h': 28800,
        '6h': 21600,
        '4h': 14400,
        '2h': 7200,
        '1h': 3600,
        '30m': 1800,
        '15m': 900,
        '10m': 600,
        '5m': 300,
        '3m': 180,
        '1m': 60,
    }
    
    last_timestamp = df[t_col].iloc[-1]
    last_time = datetime.fromtimestamp(last_timestamp, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - last_time
    
    resolution_seconds = resolution_sec_map.get(resolution, 0) * 2
    if resolution_seconds == 0:
        raise ValueError(f"Unsupported resolution: {resolution}")
    
    is_latest = diff.total_seconds() < resolution_seconds
    
    last_timestamp_readable = datetime.fromtimestamp(last_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    now_readable = now.strftime('%Y-%m-%d %H:%M:%S')
    if print_info:
        print(f"UTILS:is_data_latest: {is_latest}, Last timestamp: {last_timestamp_readable}, Now: {now_readable}, Difference: {diff}, Resolution: {resolution}")

    return is_latest
