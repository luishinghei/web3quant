# Web3 Quant Trading Bot

A quantitative trading system for cryptocurrency markets built for the HK University Web3 Quant Trading Hackathon Competition. This autonomous bot generates trading signals from derivatives positioning and volume data, then executes spot trades on the Roostoo Mock Exchange.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Data Sources and Rationale](#data-sources-and-rationale)
3. [Backtesting and Strategy Selection](#backtesting-and-strategy-selection)
4. [Signal Modeling: Momentum, Reversion, and Dispersal](#signal-modeling-momentum-reversion-and-dispersal)
5. [Portfolio Construction and Risk Management](#portfolio-construction-and-risk-management)
6. [Execution Pipeline and Error Handling](#execution-pipeline-and-error-handling)
7. [Monitoring and Logging](#monitoring-and-logging)

---

## Project Structure

```
web3_quant/
├── trade.py                    # Main live trading loop
├── quanttrading/               # Core trading infrastructure
│   ├── config_manager.py       # Strategy configuration and weight management
│   ├── strategies.py           # Base strategy interface (BaseStrat)
│   ├── binance_fetcher.py      # Factor data loading and remote API integration
│   ├── position_engine.py      # Signal-to-position calculation and leverage control
│   ├── roostoo.py              # Roostoo Mock Exchange API client
│   ├── monitor.py              # Logging and Telegram alerting
│   ├── symbol_manager.py       # Symbol info and precision handling
│   └── helper.py, log.py, tg.py
├── user_strategies/            # Concrete strategy implementations
│   ├── strat_001.py            # Open Interest (OI) strategies
│   ├── strat_002.py            # Derivatives positioning strategies
│   ├── strat_003.py            # Market sentiment strategies
│   ├── strat_004.py            # Positioning flow strategies
│   ├── strat_005.py            # Volume-based strategies
│   └── strat_006.py            # Market microstructure strategies
├── user_data/
│   ├── data/                   # Standardized factor CSVs and configurations
│   ├── logs/                   # Runtime logs
│   └── monitor/                # CSV logs for signals, positions, trades
├── df_final.csv                # Final strategy configuration
└── requirements.txt            # Python dependencies
```

### Key Components

- **`trade.py`**: The main entry point that wires together all strategies, the position engine, the monitor, and the Roostoo client. Runs the live trading loop every ~5 minutes.
- **`quanttrading/`**: Core infrastructure modules handling configuration, signal generation, position sizing, leverage control, API communication, and monitoring.
- **`user_strategies/`**: Six strategy classes implementing factor-specific signal logic for derivatives positioning, market sentiment, and flow dynamics.
- **`user_data/data/`**: Standardized time-series CSVs for each factor in normalized `{t, ts, value}` format, plus the final strategy configuration `df_final.csv`.
- **`df_final.csv`**: Final strategy configuration output from offline research/backtesting, including optimized factor weights and selected parameter sets.

---

## Data Sources and Rationale

Our system uses **hourly derivatives and market microstructure data** as predictive factors. All factors are normalized into a standard `{t, ts, value}` schema and cached locally in `user_data/data/`.

### Factor Philosophy

We employ a multi-factor approach combining:

1. **Futures Open Interest (OI)**
   - **Source**: Derivatives market open interest data
   - **Rationale**: Open interest reflects aggregate leverage and conviction in the derivatives market. Sudden changes can signal positioning imbalances or crowding, which often precede spot price reversals. When OI drops significantly while price remains stable, it suggests deleveraging that may create mean-reversion opportunities.
   - **Application**: Primary factor for detecting positioning extremes and market structure shifts.

2. **Derivatives Positioning Metrics**
   - **Source**: Various derivatives market positioning indicators
   - **Rationale**: Captures institutional and informed trader positioning dynamics. Extreme positioning levels (whether long or short biased) often precede mean-reversion as crowded trades unwind. These metrics provide insight into market sentiment and potential inflection points.
   - **Application**: Complementary signals for detecting sentiment extremes and positioning crowding.

3. **Market Microstructure Signals**
   - **Source**: Volume flow and order book dynamics
   - **Rationale**: Short-horizon flow patterns can indicate directional conviction and momentum shifts. Unusual volume patterns often precede price movements as they reflect changing supply/demand dynamics.
   - **Application**: Used for both momentum-following and contrarian strategies depending on the specific signal characteristics.

### Data Pipeline

- **Data ingestion**: Factor time series are collected from proprietary data sources and processed into standardized format.
- **Normalization**: Each factor CSV contains `{t, ts, value}` columns, where `t` is Unix epoch, `ts` is ISO timestamp, and `value` is the factor reading.
- **Runtime updates**: `BinanceFetcher._load_series` loads cached CSVs, checks freshness, and fetches recent data from a remote API service to keep factors up-to-date.

---

## Backtesting and Strategy Selection

Offline research and backtesting were conducted to select robust strategies and parameter sets. The research process mirrors the production code path to ensure consistency.

### Backtesting Methodology

1. **Factor extraction**: For each factor, we extract the historical time series from the standardized CSVs.

2. **Parameter grid search**: For each factor, we grid-search over:
   - `short_window`: rolling window for the moving average
   - `long_window`: rolling window for standard deviation or rank calculation
   - `threshold`: the dispersal parameter controlling signal intensity (see [Signal Modeling](#signal-modeling-momentum-reversion-and-dispersal))

3. **Signal simulation**: We apply the exact same signal equations used in `user_strategies/` (z-score or rank-based rules) to generate exposure signals.

4. **Performance metrics**: We simulate trades against the underlying coin's hourly returns and compute:
   - **Sharpe Ratio**: risk-adjusted return
   - **Sortino Ratio**: downside risk-adjusted return
   - **Calmar Ratio**: return/max drawdown
   - **Max Drawdown**: peak-to-trough decline
   - **Turnover**: signal change frequency

5. **Robust selection**: Rather than choosing a single best parameter set (which risks overfitting), we select a **diversified ensemble** of parameterizations per factor that show stable performance across different time periods. This ensemble approach is encoded in `df_final.csv`, where each row represents one parameter set for one factor-coin pair.

### Configuration File: `df_final.csv`

The final strategy configuration contains columns:

- `strategy`: unique identifier (e.g., `bttp_bnb_001`)
- `weight`: PyPortfolioOpt-derived factor weight (see [Portfolio Construction](#portfolio-construction-and-risk-management))
- `sym`: target coin (e.g., `BNB`, `BTC`)
- `dir`: direction type—`R` for **reversion** strategies, `M` for **momentum** strategies
- `m`: model type—`B` for z-score, `R` for rank-based
- `res`: resolution (e.g., `1h`)
- `factor_id`: factor family
- `p`: parameter list `[short_window, long_window, threshold]`

Multiple rows with the same `factor_id` represent the ensemble of parameter sets for that factor. At runtime, these are grouped into one `StratConfig` per factor, and signals are averaged across parameter sets to produce a robust aggregate signal.

---

## Signal Modeling: Momentum, Reversion, and Dispersal

All strategies inherit from `BaseStrat` (`quanttrading/strategies.py`), which provides a unified interface for signal generation.

### BaseStrat Workflow

1. **Load factor data**: `fetch_alpha()` calls `BinanceFetcher` to load the relevant factor time series.
2. **Compute signals per parameter set**: For each parameter set in `StratConfig.params`, call `calculate_signal_df(df, params, model)` to generate a signal column.
3. **Aggregate signals**: Average all parameter-specific signals to produce a robust aggregate signal (range: 0 to 1).
4. **Persist and alert**: Save signal history to `user_data/data/{id-name}.csv` and send Telegram updates when signals change.

### Signal Models

We implement two complementary statistical models for generating signals from factor time series:

#### 1. Statistical Standardization Model

- Normalizes factor values using rolling statistics
- Generates signals based on deviation from recent mean behavior
- Applied for both reversion strategies (fade extremes) and momentum strategies (follow extremes)
- Uses configurable lookback windows to capture different time horizons

#### 2. Rank-Based Model

- Computes percentile rankings over rolling historical windows
- Identifies tail events in the factor distribution
- Provides robustness to outliers and non-stationary factor dynamics
- Complementary to standardization approach for signal diversification

### Dispersal Parameter

The **dispersal parameter** (threshold) controls signal sensitivity and conviction level:

- **Higher thresholds**: Fewer, higher-conviction signals triggered only by extreme factor readings
- **Lower thresholds**: More frequent signals capturing moderate factor movements
- **Ensemble approach**: We use multiple threshold values per factor to diversify signal timing and reduce overfitting to a single parameterization

Each strategy configuration in `df_final.csv` specifies `[short_window, long_window, threshold]` parameters that were selected through robust backtesting.

### Strategy Classes

| Class | Type | Description |
|-------|------|-------------|
| `Strat001` | OI Reversion | Open interest reversion: buy when OI is anomalously low (log-transformed) |
| `Strat002` | Positioning Reversion | Derivatives positioning reversion based on crowd positioning |
| `Strat003` | Sentiment Reversion | Market sentiment reversion using positioning ratios |
| `Strat004` | Flow Reversion | Positioning flow reversion strategies |
| `Strat005` | Flow Momentum | Market flow momentum strategies |
| `Strat006` | Microstructure | Market microstructure-based signals |

---

## Portfolio Construction and Risk Management

We use a multi-stage process to convert factor signals into dollar positions with strict risk controls.

### From Signals to Positions

1. **Strategy configuration** (`config_manager.create_config_from_df`):
   - Rows in `df_final.csv` are grouped by `factor_id` into one `StratConfig` per factor.
   - Each `StratConfig` holds:
     - `final_weight`: normalized weight (sum across all factors = 1)
     - `params`: list of parameter sets to ensemble
     - `symbol`: target coin
     - `type`: reversion or momentum

2. **Target sizing** (`position_engine._calculate_target_amount`):
   ```python
   target_usd = signal * BALANCE * final_weight
   target_amount = target_usd / anchor_price
   ```
   - `signal` ∈ [0, 1] from the strategy's `generate_signal()` method
   - `BALANCE = 150,000` USD (hackathon starting capital)
   - `final_weight` is the factor's portfolio weight
   - `anchor_price` is a reference price from `symbol_manager`

3. **Aggregation by symbol** (`position_engine.aggregate_target_amount_by_symbol`):
   - Multiple strategies may target the same coin.
   - We sum all per-strategy targets to get a net target per coin.

4. **Leverage control**:
   - Calculate total notional exposure: `leverage = sum(target_amount * last_price) / BALANCE`
   - If `leverage > MAX_LEVERAGE = 0.99`, scale down all positions proportionally via `position_engine.deleverage`.
   - The deleverage function respects each symbol's precision constraints (rounding to correct decimal places).

### PyPortfolioOpt Weighting (Research Stage)

To determine `final_weight` for each factor, we used **[PyPortfolioOpt](https://github.com/PyPortfolio/PyPortfolioOpt)** during the research phase:

1. **Factor return matrix**: Construct a matrix of hourly returns for each factor strategy (rows = timestamps, columns = factors).

2. **Mean-variance optimization**: Use `pypfopt.EfficientFrontier` or similar to solve:
   ```
   maximize  expected_return - λ * variance
   subject to:
     - long-only: weights ≥ 0
     - budget: sum(weights) = 1
     - box constraints: 0 ≤ weight_i ≤ max_weight
     - L2 regularization to avoid concentration
   ```

3. **Output**: Optimal factor weights are computed and saved as the `weight` column in the strategy configuration.

4. **Normalization**: `config_manager.compute_weights` normalizes these weights into `final_weight` so they sum to 1 when loaded into runtime configs.

### Risk Controls

- **Global leverage cap**: `MAX_LEVERAGE = 0.99` ensures we never exceed ~1x notional exposure.
- **Minimum order size**: `MIN_ORDER_USD = 2.0` in `roostoo.trade` prevents dust orders and excessive turnover.
- **Long-only constraint**: All signals are ∈ [0, 1], representing long exposure only (no shorting).
- **Automatic flattening**: When a strategy's signal drops to zero, `position_engine.calculate_delta_amount` computes a sell order to close the position.
- **Precision rounding**: All order quantities are rounded to the exchange's `amount_precision` to avoid rejection.

---

## Execution Pipeline and Error Handling

### Live Trading Loop (`trade.py`)

The main loop runs every ~5 minutes (300 seconds) and executes the following steps:

1. **Load configuration**:
   ```python
   df = pd.read_csv('user_data/data/df_final.csv')
   configs = config_manager.create_config_from_df(df)
   weights = config_manager.get_weights(df)
   ```

2. **Instantiate strategies**:
   - Create 54 strategy objects (one per factor-coin-param ensemble) with a shared `BinanceFetcher` and `Monitor`.

3. **Generate signals**:
   ```python
   signals = position_engine.calculate_signals(strats)
   ```
   - Each strategy fetches its factor data, computes the aggregate signal, and returns a value ∈ [0, 1].
   - Signals are logged to `user_data/monitor/signals.csv` and sent to Telegram.

4. **Compute target positions**:
   ```python
   target_amount_by_strat = position_engine.calculate_target_amount_by_strat(
       strats, signals, BALANCE, symbols_info
   )
   target_amount_by_symbol = position_engine.aggregate_target_amount_by_symbol(
       target_amount_by_strat
   )
   ```

5. **Check and enforce leverage**:
   ```python
   leverage_ref = position_engine.calculate_leverage_ref(
       target_amount_by_symbol, symbols_info, BALANCE
   )
   if leverage_ref > MAX_LEVERAGE:
       target_amount_by_symbol = position_engine.deleverage(
           target_amount_by_symbol, leverage_ref, MAX_LEVERAGE, symbols_info
       )
   ```

6. **Fetch current positions**:
   ```python
   current_positions = roostoo.get_current_postions()
   ```

7. **Calculate deltas and trade**:
   ```python
   delta_amounts = position_engine.calculate_delta_amount(
       target_amount_by_symbol, current_positions
   )
   success_trades, error_trades = roostoo.trade(
       delta_amounts, binance_fetcher, last_prices
   )
   ```

8. **Log results**:
   - All signals, targets, leverage, deltas, positions, and trades are logged to CSV and Telegram.

9. **Sleep**:
   - Wait 300 seconds (5 minutes) before the next iteration, respecting the hackathon's low-frequency constraint.

### Roostoo API Client (`quanttrading/roostoo.py`)

The base Roostoo API wrapper (provided by competition organizers) handles HMAC-SHA256 authentication and standard endpoints. We've implemented a custom `trade()` function that adds intelligent execution logic:

#### Custom Trade Function Logic

```python
def trade(amount_by_symbol: dict[str, float], binance_fetcher: BinanceFetcher, 
          last_prices: dict[str, float] | None = None) -> tuple[list[dict], list[dict]]
```

**Key features of our implementation:**

1. **Smart order pre-filtering**:
   - Fetch real-time prices for all symbols (using cached `last_prices` when available to reduce API calls)
   - Calculate USD notional value: `usd_value = abs(amount) * last_price`
   - Skip orders below `MIN_ORDER_USD = $2.0` threshold to avoid:
     - Dust trades with high relative transaction costs
     - Excessive turnover from small rebalances
     - API rejection for minimum order size violations

2. **Delta-based execution**:
   - Positive delta → `place_order(symbol, 'BUY', amount)`
   - Negative delta → `place_order(symbol, 'SELL', abs(amount))`
   - Zero delta → skip (no rebalancing needed)
   - Automatically handles position flattening when signals go to zero

3. **Comprehensive error handling**:
   - Separate tracking of `success_trades` and `error_trades`
   - Each trade result logged to CSV and sent to Telegram with full details:
     - Success: status, symbol, amount, side, type, filled price
     - Error: error message for debugging
   - Continues trading other symbols even if one order fails

4. **Post-trade validation**:
   - After all orders executed, call `get_pending_count()` to verify no orders remain pending
   - Alert via Telegram if any orders stuck (indicates API issues or configuration problems)
   - Ensures all deltas resolved before next loop iteration

5. **Rate limiting compliance**:
   - 2-second sleep between orders to respect API rate limits
   - Total execution time scales with number of active positions
   - Well within competition's 1 trade/minute maximum constraint

This implementation ensures robust execution with minimal slippage, proper error recovery, and full observability for live trading.

### Data Fetcher Error Handling (`quanttrading/binance_fetcher.py`)

The `BinanceFetcher` manages external data dependencies with fallback mechanisms:

#### Normal Operation

1. **Load cached CSV**: Read local factor CSV from `user_data/data/`.
2. **Check freshness**: Use `helper.is_data_latest()` to verify the last timestamp is recent.
3. **Fetch updates**: If stale, call remote API service to fetch last 30 days of data.
4. **Validate and merge**: Ensure last bar is closed, concatenate with cache, deduplicate, and resave.

#### Price Fetch Fallback

The critical `fetch_all_last_prices()` method has a robust fallback:

1. **Primary path**: Fetch current prices from remote API for all symbols.
2. **On success**: Save to `user_data/last_prices.csv` with timestamp.
3. **On failure**:
   - Load fallback CSV.
   - Check age: if older than 30 minutes, abort and alert.
   - Use fallback prices and send Telegram warning.

This ensures the bot can survive temporary API outages without placing orders at stale prices.

---

## Monitoring and Logging

The `Monitor` class (`quanttrading/monitor.py`) provides comprehensive observability:

### CSV Logs (`user_data/monitor/`)

Every loop iteration, the monitor writes timestamped rows to:

- `signals.csv`: Raw signal values for all 54 strategies
- `target_amount_by_strat.csv`: Target coin amounts per strategy
- `target_amount_by_symbol.csv`: Aggregated target amounts per symbol
- `leverage.csv`: Real, reference, and deleveraged leverage values
- `delta_amounts.csv`: Order deltas (buy/sell amounts)
- `current_positions.csv`: Positions held on Roostoo after trades
- `current_balance.csv`: USD value of each position + total balance
- `success_trades.csv`: Successfully filled orders
- `error_trades.csv`: Failed orders

These logs provide a complete audit trail for ex-post analysis.

### Telegram Alerts

The monitor sends real-time alerts for:

- **Signal updates**: When a strategy's signal changes (new factor reading crossed a threshold)
- **Weighted exposures by strategy**: Grouped view of net exposure per factor (emoji-coded: 🟢 long, 🔴 short, ⚪ flat)
- **Weighted exposures by symbol**: Grouped view of net exposure per coin
- **Trade confirmations**: Order status, pair, side, price, quantity
- **Trade errors**: Error messages from failed orders
- **Pending order warnings**: If any orders remain unfilled after trading
- **Data fetch failures**: Alerts when falling back to cached prices or when cache is too old

Telegram monitoring allows real-time oversight without SSH access to the cloud server.

### Performance Evaluation Hooks

The CSV logs are designed for easy post-processing:

1. **Join trade logs with Roostoo API history** to verify fills and compute realized PnL.
2. **Aggregate balance snapshots** to compute equity curve.
3. **Calculate metrics**: Sharpe, Sortino, Calmar ratios, max drawdown, turnover.
4. **Analyze signal contributions**: Decompose PnL by strategy or symbol to identify top contributors.

---
