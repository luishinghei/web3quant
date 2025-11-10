import json
from dataclasses import dataclass
import pandas as pd
from quanttrading.log import init_logger
import ast
from quanttrading import tg


logger = init_logger('config')

@dataclass(frozen=True)
class StratParams:
    strategy_id: str
    model: str
    param: list[float | int]


@dataclass(frozen=True)
class StratConfig:
    id: int
    name: str
    type: str
    symbol: str
    timeframe: str
    side: str
    final_weight: float
    params: list[StratParams]
    order_type: str
    mdd_limit: float


def compute_weights(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    total_weight = df.groupby('factor_id', sort=False)['weight'].mean().sum()
    df['final_weight'] = df['weight'] / total_weight
    return df


def get_weights(df: pd.DataFrame) -> dict[tuple, float]:
    df = df.copy()
    df = compute_weights(df)
    weights = df.groupby('factor_id', sort=False)['final_weight'].mean().to_dict()
    return weights


def send_weights(weights: dict[tuple, float]) -> None:
    msg = f'Weights:\n'
    for key, weight in weights.items():
        msg += f'{key}: {weight}\n'
    tg.send_message(msg)


def create_config_from_df(df: pd.DataFrame) -> list[StratConfig]:
    df = compute_weights(df)
    strategies: list[StratConfig] = []
    grouped = df.groupby(['factor_id'], dropna=False, sort=False)

    for gid, group in grouped:
        try:
            first = group.iloc[0]
            # check if only has 1 unique final_weight
            if group['final_weight'].nunique() != 1:
                raise ValueError(f"Invalid final_weight: {group['final_weight']}")
            final_weight = float(first['final_weight'])
            strat_id = len(strategies) + 1
            strat_name = str(first['factor_id']).strip()
            if first['dir'] == 'R':
                strat_type = 'reversal'
            elif first['dir'] == 'M':
                strat_type = 'momentum'
            else:
                raise ValueError(f"Invalid direction: {first['dir']}")
            symbol = str(first['sym']).strip().upper()
            timeframe = str(first['res']).strip()
            side = 'long'
            order_type = 'limit'
            mdd_limit = 0.3

            params_list_group: list[StratParams] = []

            for _, row in group.iterrows():
                raw_params = row['p']
                values: list[float | int] = []
                if isinstance(raw_params, (list, tuple)):
                    values = list(raw_params)
                elif isinstance(raw_params, str) and raw_params:
                    try:
                        values = ast.literal_eval(raw_params)
                    except Exception:
                        try:
                            values = json.loads(raw_params)
                        except Exception:
                            values = []

                cleaned_values: list[float | int] = []
                for v in values:
                    if isinstance(v, (int, float)):
                        cleaned_values.append(v)
                    else:
                        try:
                            cast_v = float(v)
                            cleaned_values.append(int(cast_v) if cast_v.is_integer() else cast_v)
                        except Exception:
                            continue

                params_list_group.append(StratParams(strategy_id=row['strategy'], model=row['m'], param=cleaned_values))

            strategies.append(
                StratConfig(
                    id=strat_id,
                    name=strat_name,
                    type=strat_type,
                    symbol=symbol,
                    timeframe=timeframe,
                    side=side,
                    final_weight=final_weight,
                    params=params_list_group,
                    order_type=order_type,
                    mdd_limit=mdd_limit,
                )
            )
        except Exception as e:
            logger.error(f"Failed to convert group '{gid}' to StratConfig: {e}")
            continue

    return strategies
