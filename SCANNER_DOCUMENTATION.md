# 🔍 COINTEGRATION SCANNER - DOCUMENTATION

## Overview
The Cointegration Scanner is the **"Brain"** of the statistical arbitrage bot. It analyzes historical market data to identify mathematically linked pairs suitable for mean-reversion trading.

## Mathematical Foundation

### Engle-Granger Two-Step Method

#### Step 1: OLS Regression
Calculate the Hedge Ratio (β) using Ordinary Least Squares:

```
log(Price_Y) = α + β·log(Price_X) + ε
```

Where:
- **β** = Hedge Ratio (how many units of Y per unit of X)
- **ε** = Residuals (the "spread")

#### Step 2: Stationarity Test
Run **Augmented Dickey-Fuller (ADF)** test on residuals:

**Hypotheses:**
- H₀: Residuals have unit root (non-stationary) → No cointegration
- H₁: Residuals are stationary → Cointegrated!

**Pass Condition:** p-value < 0.05 (95% confidence)

### Half-Life Calculation
Mean reversion speed using AR(1) model:

```
Δy_t = λ·(mean - y_{t-1}) + ε_t
Half-life = -ln(2) / ln(1 + λ)
```

**Filter:** Only pairs with **half-life < 24 hours** qualify (fast mean reversion).

## Usage

### Quick Start
```bash
# Run the scanner
python run_scanner.py

# Or directly
python -m quant_arbitrage.cointegration_scanner
```

### Configuration
Edit `quant_arbitrage/config.py`:

```python
@dataclass
class CointegrationConfig:
    lookback_days: int = 60              # Historical data period
    adf_pvalue_threshold: float = 0.05   # Stationarity confidence
    coint_pvalue_threshold: float = 0.05 # Cointegration confidence
    min_correlation: float = 0.5         # Pre-filter correlation
    top_n_pairs: int = 10                # How many pairs to return
    min_volume_usdt: float = 1_000_000   # Liquidity filter (1M USDT/day)
```

## Output Files

### 1. `pairs_config.json` (Bot Configuration)
Production-ready configuration for the trading bot:

```json
{
  "pairs": [
    {
      "pair_id": "ETH_BTC",
      "leg_a": "ETH/USDT",
      "leg_b": "BTC/USDT",
      "hedge_ratio": 0.0652,
      "z_score_threshold": 2.0,
      "stop_loss_z": 4.0,
      "half_life_candles": 12
    }
  ]
}
```

**Field Descriptions:**
- `pair_id`: Unique identifier for the pair
- `leg_a`: First asset to trade
- `leg_b`: Second asset (hedge)
- `hedge_ratio`: Calculated β from OLS regression
- `z_score_threshold`: Entry signal at ±2σ
- `stop_loss_z`: Emergency exit at ±4σ
- `half_life_candles`: Mean reversion speed (hours)

### 2. `cointegration_results_TIMESTAMP.csv`
Detailed statistical analysis:

| Pair X | Pair Y | Correlation | Hedge Ratio (β) | ADF Statistic | ADF P-Value | Coint P-Value | Cointegrated | Half-Life (hours) |
|--------|--------|-------------|-----------------|---------------|-------------|---------------|--------------|-------------------|
| ETH    | BTC    | 0.9823      | 0.0652          | -4.523        | 0.0001      | 0.0089        | ✅ Yes       | 12.3              |
| SOL    | ETH    | 0.9456      | 0.1234          | -3.891        | 0.0034      | 0.0156        | ✅ Yes       | 18.7              |

### 3. Visualization Plots (`plots/*.png`)
Each valid pair gets a chart with:

**Top Panel: Normalized Prices**
- Shows price movement correlation
- Both assets normalized to starting price

**Bottom Panel: Z-Score of Spread**
- Purple line: Real-time Z-score
- Green dashed lines: Entry thresholds (±2σ)
- Red dotted lines: Stop-loss levels (±4σ)
- Gray zone: Safe zone (no position)

**Statistics Box:**
- ADF p-value
- Cointegration p-value
- Half-life (hours)
- Correlation coefficient

## Algorithm Workflow

```
1. CONNECT TO EXCHANGE
   ↓
2. FETCH TOP 30 USDT PAIRS BY VOLUME
   ↓
3. DOWNLOAD 60 DAYS OF 1H CANDLES
   ↓
4. FOR EACH PAIR COMBINATION (X, Y):
   ├─ Calculate correlation → If < 0.5, skip
   ├─ OLS regression → Get hedge ratio β
   ├─ Calculate spread: log(Y) - β·log(X)
   ├─ ADF test → Check stationarity
   ├─ Cointegration test → Confirm linkage
   ├─ Calculate half-life → Filter if > 24h
   └─ If all pass → Add to valid pairs
   ↓
5. SORT BY: (1) Low p-value, (2) Fast half-life
   ↓
6. EXPORT:
   ├─ pairs_config.json (for bot)
   ├─ CSV results (for analysis)
   └─ PNG plots (for validation)
```

## Validation Checklist

Before using scanner output in production:

- [ ] **ADF p-value < 0.05** - Spread is stationary
- [ ] **Coint p-value < 0.05** - Pairs are cointegrated
- [ ] **Half-life < 24 hours** - Fast mean reversion
- [ ] **Correlation > 0.5** - Strong relationship
- [ ] **Visual validation** - Check plots for stable spread
- [ ] **Volume check** - Both assets liquid (>1M USDT/day)

## Troubleshooting

### No pairs found
**Causes:**
1. Thresholds too strict (relax p-value to 0.1)
2. Market regime shift (low correlation period)
3. Insufficient data (<60 days available)

**Solutions:**
```python
# In config.py
adf_pvalue_threshold: float = 0.10  # More lenient
min_correlation: float = 0.3        # Lower bar
```

### Half-life too long
**Cause:** Market conditions favor trending over mean reversion

**Solution:**
- Use shorter lookback window (30 days)
- Focus on highly correlated assets (>0.8)
- Check for structural breaks in relationships

### API rate limits
**Cause:** Fetching data too fast

**Solution:**
```python
# In scanner.py, scan_pairs() method
await asyncio.sleep(0.5)  # Increase delay between requests
```

## Dependencies

```bash
pip install ccxt statsmodels pandas numpy matplotlib scipy
```

## Advanced Usage

### Custom Symbol List
```python
# In scanner instance
custom_pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "MATIC/USDT"]
results = await scanner.scan_pairs(pairs=custom_pairs)
```

### Programmatic Access
```python
from quant_arbitrage.cointegration_scanner import CointegrationScanner

scanner = CointegrationScanner()
await scanner.connect()
results = await scanner.scan_pairs()

# Get best pairs
for result in results[:5]:
    if result.is_cointegrated and result.half_life < 24:
        print(f"{result.pair_x}/{result.pair_y}: β={result.hedge_ratio:.4f}")
```

## Performance Metrics

**Typical Execution:**
- 30 pairs × 435 combinations = ~13,050 pair tests
- ~5-10 minutes total runtime
- ~2-5 valid pairs found (varies by market)

**Resource Usage:**
- Memory: ~500MB (for price data)
- Network: ~100MB (OHLCV downloads)
- CPU: Single-threaded (asyncio)

## Next Steps

After running scanner:

1. **Review** `pairs_config.json` - Verify hedge ratios make sense
2. **Validate** plots in `plots/` - Check spread stability
3. **Backtest** pairs using historical data simulator
4. **Paper trade** with testnet before live deployment
5. **Monitor** live spreads for regime changes

## References

- Engle, R.F. and Granger, C.W.J. (1987). "Co-integration and Error Correction"
- Dickey, D.A. and Fuller, W.A. (1979). "Distribution of the Estimators for Autoregressive Time Series"
- Pole, A. (2007). "Statistical Arbitrage: Algorithmic Trading Insights and Techniques"

---

**Version:** 1.0.0  
**Last Updated:** 2026-02-01  
**Author:** Quant Team
