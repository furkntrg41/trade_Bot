"""
TEST SCRIPT: Cointegration Scanner Validation
==============================================
Validates the scanner implementation without requiring Binance API.
Uses synthetic cointegrated data for testing.

Run: python test_scanner_offline.py
"""

import asyncio
import logging
import numpy as np
from quant_arbitrage.cointegration_analyzer import CointegrationAnalyzer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_cointegrated_pairs(n_periods: int = 1440) -> tuple:
    """
    Generate synthetic cointegrated price series.
    
    Args:
        n_periods: Number of hourly candles (default: 60 days)
        
    Returns:
        (price_x, price_y) where Y and X are cointegrated
    """
    np.random.seed(42)
    
    # Generate base random walk for X
    returns_x = np.random.randn(n_periods) * 0.02  # 2% volatility
    log_price_x = np.cumsum(returns_x) + 7.0  # Start around $1000
    price_x = np.exp(log_price_x)
    
    # Generate Y as cointegrated with X
    # Y = exp(α + β*log(X) + stationary_noise)
    beta = 0.065  # True hedge ratio
    alpha = 0.5
    
    # Stationary noise (mean-reverting)
    ar_coeff = 0.95
    noise = np.zeros(n_periods)
    noise[0] = 0.01
    for i in range(1, n_periods):
        noise[i] = ar_coeff * noise[i-1] + np.random.randn() * 0.005
    
    log_price_y = alpha + beta * log_price_x + noise
    price_y = np.exp(log_price_y)
    
    return price_x, price_y


def test_hedge_ratio_calculation():
    """Test 1: Verify hedge ratio calculation"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Hedge Ratio Calculation")
    logger.info("="*80)
    
    analyzer = CointegrationAnalyzer()
    
    # Generate data with known β = 0.065
    price_x, price_y = generate_cointegrated_pairs()
    
    # Calculate hedge ratio
    beta = analyzer.calculate_hedge_ratio(price_x, price_y)
    
    logger.info(f"True hedge ratio: 0.0650")
    logger.info(f"Calculated hedge ratio: {beta:.4f}")
    
    # Tolerance: ±5% error
    error = abs(beta - 0.065) / 0.065
    assert error < 0.05, f"Hedge ratio error too large: {error*100:.2f}%"
    
    logger.info("✅ Test 1 PASSED: Hedge ratio within 5% of true value\n")


def test_stationarity_detection():
    """Test 2: Verify ADF test detects stationarity"""
    logger.info("="*80)
    logger.info("TEST 2: Stationarity Detection (ADF Test)")
    logger.info("="*80)
    
    analyzer = CointegrationAnalyzer()
    
    # Test 2a: Non-stationary series (random walk)
    random_walk = np.cumsum(np.random.randn(1000))
    adf_stat_ns, p_value_ns = analyzer.test_stationarity(random_walk, "Random Walk")
    
    logger.info(f"Non-stationary series: p-value = {p_value_ns:.4f} (expect > 0.05)")
    assert p_value_ns > 0.05, "Failed to detect non-stationarity"
    
    # Test 2b: Stationary series (white noise)
    white_noise = np.random.randn(1000)
    adf_stat_s, p_value_s = analyzer.test_stationarity(white_noise, "White Noise")
    
    logger.info(f"Stationary series: p-value = {p_value_s:.4f} (expect < 0.05)")
    assert p_value_s < 0.05, "Failed to detect stationarity"
    
    logger.info("✅ Test 2 PASSED: ADF test correctly identifies stationarity\n")


def test_cointegration_detection():
    """Test 3: Verify cointegration test on synthetic data"""
    logger.info("="*80)
    logger.info("TEST 3: Cointegration Detection (Engle-Granger)")
    logger.info("="*80)
    
    analyzer = CointegrationAnalyzer()
    
    # Generate cointegrated pairs
    price_x, price_y = generate_cointegrated_pairs()
    
    # Test cointegration
    result = analyzer.test_cointegration(price_x, price_y)
    result.pair_x = "TEST_X"
    result.pair_y = "TEST_Y"
    
    logger.info(f"\nCointegration Test Results:")
    logger.info(f"  Hedge Ratio: {result.hedge_ratio:.4f}")
    logger.info(f"  ADF p-value: {result.adf_pvalue:.4f}")
    logger.info(f"  Coint p-value: {result.coint_pvalue:.4f}")
    logger.info(f"  Half-life: {result.half_life:.2f} periods")
    logger.info(f"  Is Cointegrated: {result.is_cointegrated}")
    
    # Assertions
    assert result.is_cointegrated, "Failed to detect cointegration in synthetic data"
    assert result.adf_pvalue < 0.05, f"ADF test failed: p={result.adf_pvalue:.4f}"
    assert result.coint_pvalue < 0.05, f"Coint test failed: p={result.coint_pvalue:.4f}"
    assert result.half_life < 100, f"Half-life too long: {result.half_life:.2f}"
    
    logger.info("✅ Test 3 PASSED: Cointegration correctly detected\n")


def test_half_life_filter():
    """Test 4: Verify half-life < 24h filter"""
    logger.info("="*80)
    logger.info("TEST 4: Half-Life Filter (< 24 hours)")
    logger.info("="*80)
    
    analyzer = CointegrationAnalyzer()
    
    # Generate fast mean-reverting spread
    ar_coeff_fast = 0.85  # Fast reversion
    spread_fast = np.zeros(1000)
    spread_fast[0] = 1.0
    for i in range(1, 1000):
        spread_fast[i] = ar_coeff_fast * spread_fast[i-1] + np.random.randn() * 0.1
    
    half_life_fast = analyzer._calculate_half_life(spread_fast)
    logger.info(f"Fast mean reversion half-life: {half_life_fast:.2f} periods")
    
    # Generate slow mean-reverting spread
    ar_coeff_slow = 0.98  # Slow reversion
    spread_slow = np.zeros(1000)
    spread_slow[0] = 1.0
    for i in range(1, 1000):
        spread_slow[i] = ar_coeff_slow * spread_slow[i-1] + np.random.randn() * 0.1
    
    half_life_slow = analyzer._calculate_half_life(spread_slow)
    logger.info(f"Slow mean reversion half-life: {half_life_slow:.2f} periods")
    
    # Validate
    assert half_life_fast < 24, f"Fast half-life should be < 24h: {half_life_fast:.2f}"
    assert half_life_slow > 24, f"Slow half-life should be > 24h: {half_life_slow:.2f}"
    
    logger.info("✅ Test 4 PASSED: Half-life filter works correctly\n")


def test_universe_scan():
    """Test 5: Scan multiple pairs"""
    logger.info("="*80)
    logger.info("TEST 5: Universe Scanning (Multiple Pairs)")
    logger.info("="*80)
    
    analyzer = CointegrationAnalyzer()
    
    # Generate 5 synthetic assets
    np.random.seed(123)
    price_data = {}
    
    # Base asset
    base = np.exp(np.cumsum(np.random.randn(1440) * 0.02) + 8.0)
    price_data["BTC"] = base
    
    # Cointegrated with base
    noise1 = np.zeros(1440)
    for i in range(1, 1440):
        noise1[i] = 0.9 * noise1[i-1] + np.random.randn() * 0.01
    price_data["ETH"] = np.exp(0.5 + 0.065 * np.log(base) + noise1)
    
    # Another cointegrated pair
    noise2 = np.zeros(1440)
    for i in range(1, 1440):
        noise2[i] = 0.88 * noise2[i-1] + np.random.randn() * 0.01
    price_data["SOL"] = np.exp(0.3 + 0.045 * np.log(base) + noise2)
    
    # Non-cointegrated (random walk)
    price_data["DOGE"] = np.exp(np.cumsum(np.random.randn(1440) * 0.05) + 5.0)
    price_data["XRP"] = np.exp(np.cumsum(np.random.randn(1440) * 0.04) + 6.0)
    
    # Scan
    results = analyzer.scan_universe(price_data, top_n=10)
    
    logger.info(f"\nFound {len(results)} cointegrated pairs:")
    for i, result in enumerate(results, 1):
        logger.info(f"  {i}. {result.pair_x} vs {result.pair_y} | "
                   f"β={result.hedge_ratio:.4f} | "
                   f"p={result.coint_pvalue:.4f} | "
                   f"half-life={result.half_life:.1f}h")
    
    # Should find BTC-ETH and BTC-SOL (cointegrated), not DOGE-XRP
    assert len(results) >= 1, f"Should find at least 1 cointegrated pair, found {len(results)}"
    
    # Verify results are sorted by quality
    if len(results) > 1:
        assert results[0].coint_pvalue <= results[1].coint_pvalue, "Results should be sorted by p-value"
    
    logger.info("✅ Test 5 PASSED: Universe scan identifies cointegrated pairs\n")


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 COINTEGRATION SCANNER - VALIDATION TESTS")
    print("="*80)
    print("Testing mathematical correctness without requiring live API\n")
    
    try:
        test_hedge_ratio_calculation()
        test_stationarity_detection()
        test_cointegration_detection()
        test_half_life_filter()
        test_universe_scan()
        
        print("="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print("\nScanner implementation validated successfully!")
        print("Ready for live data testing with: python run_scanner.py\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
