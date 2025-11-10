from quanttrading.log import init_logger
import os
import pandas as pd
from datetime import datetime, timezone
import numpy as np
from quanttrading.strategies import BaseStrat
from quanttrading import tg
from quanttrading.binance_fetcher import BinanceFetcher


logger = init_logger('monitor')

class Monitor:
    def __init__(self) -> None:
        self.user_data_folder = 'user_data'
        self.csv_folder = f'{self.user_data_folder}/monitor'
        os.makedirs(self.csv_folder, exist_ok=True)
        
    def _log_to_csv(self, df: pd.DataFrame, file_path: str) -> bool:
        if not os.path.exists(file_path):
            df.to_csv(file_path)
            return True
        else:
            old_df = pd.read_csv(file_path, index_col=0)
            if not old_df.empty:
                # Align columns and compare last row (ignore index)
                all_cols = sorted(set(old_df.columns) | set(df.columns))
                last_old = old_df.tail(1).reindex(columns=all_cols)
                new_row = df.tail(1).reindex(columns=all_cols)
                try:
                    old_vals = last_old.to_numpy(dtype=float)
                    new_vals = new_row.to_numpy(dtype=float)
                    if np.allclose(old_vals, new_vals, rtol=1e-9, atol=1e-12, equal_nan=True):
                        return False
                except Exception:
                    if last_old.equals(new_row):
                        return False
            combined_df = pd.concat([old_df, df])
            combined_df.to_csv(file_path)
            return True
            
    def _flatten_signals(self, signals: dict[tuple, float]) -> dict[str, float]:
        return {
            ("_".join(map(str, k)) if isinstance(k, tuple) else str(k)):
                (float(v) if hasattr(v, "item") else v)
            for k, v in signals.items()
        }

    def _flatten_record_for_csv(self, record: dict[str, object], parent_key: str = "", sep: str = "_") -> dict[str, object]:
        flattened: dict[str, object] = {}
        for key, value in record.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
            if isinstance(value, dict):
                flattened.update(self._flatten_record_for_csv(value, new_key, sep))
            elif isinstance(value, (list, tuple)):
                try:
                    import json
                    flattened[new_key] = json.dumps(value)
                except Exception:
                    flattened[new_key] = str(value)
            else:
                if hasattr(value, "item"):
                    try:
                        value = float(value)  # type: ignore[assignment]
                    except Exception:
                        pass
                flattened[new_key] = value
        return flattened
        
    def _now_str(self, now: int) -> str:
        now_dt = datetime.fromtimestamp(now, tz=timezone.utc)
        return now_dt.strftime('%Y-%m-%d %H:%M:%S')
        
    def log_signals(self, signals: dict[tuple, float], now: int) -> bool:
        now_str = self._now_str(now)
        flat_signals: dict[str, float] = self._flatten_signals(signals)

        df = pd.DataFrame([flat_signals], index=[now_str])
        
        file_path = f'{self.csv_folder}/signals.csv'
        return self._log_to_csv(df, file_path)
            
    def log_target_amount_by_strat(self, target_amount_by_strat: dict[tuple, float], now: int) -> None:
        now_str = self._now_str(now)
        flat_target_amount_by_strat: dict[str, float] = self._flatten_signals(target_amount_by_strat)
        
        df = pd.DataFrame(flat_target_amount_by_strat, index=[now_str])

        file_path = f'{self.csv_folder}/target_amount_by_strat.csv'
        self._log_to_csv(df, file_path)
    
    
    def log_target_amount_by_symbol(self, target_amount_by_symbol: dict[str, float], now: int) -> None:
        now_str = self._now_str(now)
        flat_target_amount_by_symbol: dict[str, float] = self._flatten_signals(target_amount_by_symbol)
        
        df = pd.DataFrame(flat_target_amount_by_symbol, index=[now_str])

        file_path = f'{self.csv_folder}/target_amount_by_symbol.csv'
        self._log_to_csv(df, file_path)
        
    
    def log_leverage(
        self,
        leverage_real: float,
        leverage_ref: float,
        deleveraged: float,
        now: int
    ) -> None:
        now_str = self._now_str(now)
        df = pd.DataFrame({
            'leverage_real': [leverage_real],
            'leverage_ref': [leverage_ref],
            'deleveraged': [deleveraged]
        }, index=[now_str])
        
        file_path = f'{self.csv_folder}/leverage.csv'
        self._log_to_csv(df, file_path)
        
    
    def log_current_positions(self, current_positions: dict[str, float], now: int) -> None:
        now_str = self._now_str(now)
        flat_current_positions: dict[str, float] = self._flatten_signals(current_positions)
        df = pd.DataFrame(flat_current_positions, index=[now_str])
        
        file_path = f'{self.csv_folder}/current_positions.csv'
        self._log_to_csv(df, file_path)
    
    
    def log_current_balance(self, current_positions: dict[str, float], binance_fetcher: BinanceFetcher, now: int, last_prices: dict[str, float] | None = None) -> None:
        now_str = self._now_str(now)
        
        # Convert positions to USD values
        balance_in_usd: dict[str, float] = {}
        for symbol, amount in current_positions.items():
            try:
                # Use provided last_prices if available, otherwise fetch
                if symbol == 'USD':
                    last_price = 1.0
                elif last_prices is not None and symbol in last_prices:
                    last_price = last_prices[symbol]
                else:
                    last_price = binance_fetcher.fetch_last_price(symbol)
                balance_in_usd[symbol] = amount * last_price
                logger.info(f'{symbol}: {amount} * {last_price} = ${balance_in_usd[symbol]:.2f}')
            except Exception as e:
                logger.error(f'Error fetching price for {symbol}: {e}')
                balance_in_usd[symbol] = 0.0
        
        # Add total column
        total = sum(balance_in_usd.values())
        balance_in_usd['total'] = total
        logger.info(f'Total balance: ${total:.2f}')
        
        flat_balance: dict[str, float] = self._flatten_signals(balance_in_usd)
        df = pd.DataFrame(flat_balance, index=[now_str])
        
        file_path = f'{self.csv_folder}/current_balance.csv'
        self._log_to_csv(df, file_path)
        
    
    def log_delta_amounts(self, delta_amounts: dict[str, float], now: int) -> None:
        now_str = self._now_str(now)
        flat_delta_amounts: dict[str, float] = self._flatten_signals(delta_amounts)
        df = pd.DataFrame(flat_delta_amounts, index=[now_str])
        
        file_path = f'{self.csv_folder}/delta_amounts.csv'
        self._log_to_csv(df, file_path)
        
    
    def log_success_trades(self, success_trades: list[dict], now: int) -> None:
        if not success_trades:
            return
        
        now_str = self._now_str(now)
        flat_records = [self._flatten_record_for_csv(rec) for rec in success_trades]
        df = pd.DataFrame(flat_records)
        df.index = [now_str] * len(df)
        
        file_path = f'{self.csv_folder}/success_trades.csv'
        self._log_to_csv(df, file_path)
    
    
    def log_error_trades(self, error_trades: list[dict], now: int) -> None:
        if not error_trades:
            return
        
        now_str = self._now_str(now)
        flat_records = [self._flatten_record_for_csv(rec) for rec in error_trades]
        df = pd.DataFrame(flat_records)
        df.index = [now_str] * len(df)
        
        file_path = f'{self.csv_folder}/error_trades.csv'
        self._log_to_csv(df, file_path)

    # ========== Weighted position computations and messaging ==========
    def compute_weighted_by_strategy(self, signals: dict[tuple, float], strats: list[BaseStrat]) -> dict[str, dict[str, float]]:
        grouped: dict[str, dict[str, float]] = {}
        for strat in strats:
            key = strat.strat_key
            if key not in signals:
                continue
            name = strat.name
            signal = float(signals[key])
            weight = float(strat.final_weight)

            if name not in grouped:
                grouped[name] = {"numerator": 0.0, "denominator": 0.0, "percent": 0.0}
            grouped[name]["numerator"] += signal * weight
            grouped[name]["denominator"] += weight

        for name, vals in grouped.items():
            denom = vals["denominator"]
            vals["percent"] = (vals["numerator"] / denom) if denom != 0 else 0.0
        return grouped

    def compute_weighted_by_symbol(self, signals: dict[tuple, float], strats: list[BaseStrat]) -> dict[str, dict[str, float]]:
        grouped: dict[str, dict[str, float]] = {}
        for strat in strats:
            key = strat.strat_key
            if key not in signals:
                continue
            symbol = strat.symbol
            signal = float(signals[key])
            weight = float(strat.final_weight)

            if symbol not in grouped:
                grouped[symbol] = {"numerator": 0.0, "denominator": 0.0, "percent": 0.0}
            grouped[symbol]["numerator"] += signal * weight
            grouped[symbol]["denominator"] += weight

        for symbol, vals in grouped.items():
            denom = vals["denominator"]
            vals["percent"] = (vals["numerator"] / denom) if denom != 0 else 0.0
        return grouped

    def _format_grouped_report(self, title: str, grouped: dict[str, dict[str, float]]) -> str:
        def emoji_for(value: float) -> str:
            eps = 1e-9
            if abs(value) < eps:
                return '⚪️'
            return '🟢' if value > 0 else '🔴'

        rows = []
        for name, vals in grouped.items():
            numerator = vals["numerator"]
            denominator = vals["denominator"]
            percent = vals["percent"]
            rows.append((name, numerator, denominator, percent))

        # Sort by absolute percent descending for readability
        rows.sort(key=lambda r: abs(r[3]), reverse=True)

        lines: list[str] = [f'{title}:']
        net = 0.0
        for name, numerator, denominator, percent in rows:
            emo = emoji_for(numerator)
            lines.append(f'{name}:{emo}{numerator:7.3f}/{denominator:7.3f}={percent*100:6.2f}%')
            net += numerator
        lines.append('-----------')
        lines.append(f'Net: {emoji_for(net)} {net:7.3f}')
        return '\n'.join(lines)

    def _send_tg_message_chunked(self, message: str, max_len: int = 4000) -> None:
        if len(message) <= max_len:
            tg.send_message(message)
            return
        # Split by lines and build chunks
        lines = message.split('\n')
        chunk = ''
        for line in lines:
            # +1 for newline when re-joining
            to_add = (line + '\n')
            if len(chunk) + len(to_add) > max_len:
                if chunk:
                    tg.send_message(chunk.rstrip('\n'))
                    chunk = ''
                # If single line itself is longer than max, hard-split
                if len(to_add) > max_len:
                    start = 0
                    while start < len(to_add):
                        part = to_add[start:start+max_len]
                        tg.send_message(part.rstrip('\n'))
                        start += max_len
                else:
                    chunk = to_add
            else:
                chunk += to_add
        if chunk:
            tg.send_message(chunk.rstrip('\n'))

    def send_weighted_by_strategy(self, signals: dict[tuple, float], strats: list[BaseStrat]) -> None:
        grouped = self.compute_weighted_by_strategy(signals, strats)
        if not grouped:
            return
        msg = self._format_grouped_report('Group by strategy', grouped)
        self._send_tg_message_chunked(msg)

    def send_weighted_by_symbol(self, signals: dict[tuple, float], strats: list[BaseStrat]) -> None:
        grouped = self.compute_weighted_by_symbol(signals, strats)
        if not grouped:
            return
        msg = self._format_grouped_report('Group by symbol', grouped)
        self._send_tg_message_chunked(msg)