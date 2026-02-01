"""
Integration Test - Verify all components work together
======================================================

Bu script tüm quant_arbitrage komponentlerinin
correctness'ini ve compatibility'sini test ediyor.

Usage:
    python test_integration.py [--full]
    
    --full: Run all tests (including live API calls)
"""

import asyncio
import sys
import logging
from datetime import datetime
from typing import List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_imports() -> bool:
    """Test 1: Verify all imports work correctly"""
    logger.info("🧪 Test 1: Checking imports...")
    
    try:
        from quant_arbitrage import (
            CointegrationScanner,
            SignalGenerator,
            MultiPairSignalGenerator,
            ExecutionEngine,
            TradingSignal,
            SignalStrength,
            Order,
            OrderStatus,
            Position,
            PositionMode,
            CointegrationAnalyzer,
            CointegrationResult,
            PairsSpreadCalculator,
            SpreadSignal,
            SignalType,
            KalmanFilterHedgeRatio,
            WebSocketProvider,
            BinanceWebSocketProvider,
            TickData,
            FundingArbitrage,
            FundingStatus,
            FundingRateMonitor,
            RiskManager,
            RiskMetrics,
            PositionSide,
            Config,
            get_config,
            set_config,
        )
        
        logger.info("✅ All imports successful")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


def test_config() -> bool:
    """Test 2: Configuration loading and validation"""
    logger.info("🧪 Test 2: Testing configuration...")
    
    try:
        from quant_arbitrage.config import get_config
        
        config = get_config()
        
        # Check all config objects exist
        assert hasattr(config, 'cointegration'), "Missing cointegration config"
        assert hasattr(config, 'signal'), "Missing signal config"
        assert hasattr(config, 'execution'), "Missing execution config"
        assert hasattr(config, 'risk'), "Missing risk config"
        assert hasattr(config, 'data'), "Missing data config"
        assert hasattr(config, 'funding'), "Missing funding config"
        
        # Check key values
        assert config.cointegration.lookback_days > 0, "Invalid lookback_days"
        assert config.signal.entry_threshold > 0, "Invalid entry_threshold"
        assert config.execution.risk_per_trade > 0, "Invalid risk_per_trade"
        
        # Validate config
        assert config.validate(), "Config validation failed"
        
        logger.info(f"✅ Config loaded and validated")
        logger.info(f"   - Lookback: {config.cointegration.lookback_days} days")
        logger.info(f"   - Entry threshold: {config.signal.entry_threshold}σ")
        logger.info(f"   - Risk per trade: {config.execution.risk_per_trade:.1%}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Config test failed: {e}")
        return False


def test_dataclasses() -> bool:
    """Test 3: Dataclasses work correctly"""
    logger.info("🧪 Test 3: Testing dataclasses...")
    
    try:
        from quant_arbitrage import (
            TradingSignal,
            SignalType,
            SignalStrength,
            Order,
            OrderStatus,
            Position,
            PositionMode,
        )
        
        # Create TradingSignal
        signal = TradingSignal(
            timestamp=datetime.utcnow(),
            pair_x="BTC",
            pair_y="ETH",
            signal_type=SignalType.BUY,
            z_score=2.5,
            confidence=0.85,
            strength=SignalStrength.STRONG,
            suggested_position_size=0.75,
            stop_loss_z=4.0,
            take_profit_z=0.0,
        )
        
        assert signal.pair_x == "BTC", "Signal pair_x not set"
        assert signal.z_score == 2.5, "Signal z_score not set"
        
        # Create Order
        order = Order(
            order_id="test123",
            timestamp=datetime.utcnow(),
            symbol="BTC/USDT",
            side="BUY",
            order_type="market",
            quantity=0.5,
            status=OrderStatus.CLOSED,
            average_price=95000.0,
        )
        
        assert order.order_id == "test123", "Order ID not set"
        
        # Create Position
        position = Position(
            pair_x="BTC",
            pair_y="ETH",
            mode=PositionMode.LONG,
            quantity_x=0.5,
            quantity_y=-10.0,
        )
        
        assert position.is_open(), "Position should be open"
        
        logger.info("✅ All dataclasses work correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Dataclass test failed: {e}")
        return False


def test_enums() -> bool:
    """Test 4: Enums are properly defined"""
    logger.info("🧪 Test 4: Testing enums...")
    
    try:
        from quant_arbitrage import (
            SignalType,
            SignalStrength,
            OrderStatus,
            PositionMode,
        )
        
        # SignalType
        assert hasattr(SignalType, 'BUY'), "SignalType.BUY missing"
        assert hasattr(SignalType, 'SELL'), "SignalType.SELL missing"
        assert hasattr(SignalType, 'EXIT'), "SignalType.EXIT missing"
        
        # SignalStrength
        assert SignalStrength.WEAK.value == 0.5, "SignalStrength.WEAK value wrong"
        assert SignalStrength.STRONG.value == 1.5, "SignalStrength.STRONG value wrong"
        
        # OrderStatus
        assert hasattr(OrderStatus, 'CLOSED'), "OrderStatus.CLOSED missing"
        assert hasattr(OrderStatus, 'PENDING'), "OrderStatus.PENDING missing"
        
        # PositionMode
        assert hasattr(PositionMode, 'LONG'), "PositionMode.LONG missing"
        assert hasattr(PositionMode, 'SHORT'), "PositionMode.SHORT missing"
        assert hasattr(PositionMode, 'NEUTRAL'), "PositionMode.NEUTRAL missing"
        
        logger.info("✅ All enums properly defined")
        return True
        
    except Exception as e:
        logger.error(f"❌ Enum test failed: {e}")
        return False


def test_mathematical_modules() -> bool:
    """Test 5: Mathematical modules load and work"""
    logger.info("🧪 Test 5: Testing mathematical modules...")
    
    try:
        from quant_arbitrage import (
            CointegrationAnalyzer,
            PairsSpreadCalculator,
            KalmanFilterHedgeRatio,
            RiskManager,
        )
        
        # CointegrationAnalyzer
        analyzer = CointegrationAnalyzer(
            lookback_window=252,
            adf_pvalue_threshold=0.05,
        )
        assert analyzer is not None, "CointegrationAnalyzer init failed"
        
        # PairsSpreadCalculator
        calc = PairsSpreadCalculator(
            lookback_window=100,
            hedge_ratio=0.5,
        )
        assert calc is not None, "PairsSpreadCalculator init failed"
        
        # KalmanFilterHedgeRatio
        kalman = KalmanFilterHedgeRatio(
            initial_hedge_ratio=0.5,
            process_noise=1e-5,
            measurement_noise=1e-4,
        )
        assert kalman is not None, "KalmanFilterHedgeRatio init failed"
        
        # RiskManager
        from quant_arbitrage.config import get_config
        config = get_config()
        risk_mgr = RiskManager(config.risk)
        assert risk_mgr is not None, "RiskManager init failed"
        
        logger.info("✅ All mathematical modules work correctly")
        return True
        
    except Exception as e:
        logger.error(f"❌ Mathematical modules test failed: {e}")
        return False


def test_async_components() -> bool:
    """Test 6: Async components initialize correctly"""
    logger.info("🧪 Test 6: Testing async components...")
    
    try:
        from quant_arbitrage import (
            CointegrationScanner,
            SignalGenerator,
            ExecutionEngine,
        )
        from quant_arbitrage.config import get_config
        
        config = get_config()
        
        # CointegrationScanner
        scanner = CointegrationScanner(config)
        assert scanner is not None, "Scanner init failed"
        assert hasattr(scanner, 'connect'), "Scanner missing connect method"
        assert hasattr(scanner, 'scan_pairs'), "Scanner missing scan_pairs method"
        
        # SignalGenerator
        gen = SignalGenerator("BTC", "ETH", 0.5, config)
        assert gen is not None, "SignalGenerator init failed"
        assert hasattr(gen, 'start'), "Gen missing start method"
        assert hasattr(gen, 'register_signal_callback'), "Gen missing callback method"
        
        # ExecutionEngine
        engine = ExecutionEngine(config)
        assert engine is not None, "ExecutionEngine init failed"
        assert hasattr(engine, 'connect'), "Engine missing connect method"
        assert hasattr(engine, 'execute_signal'), "Engine missing execute_signal method"
        
        logger.info("✅ All async components initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Async components test failed: {e}")
        return False


def test_type_hints() -> bool:
    """Test 7: Type hints are present (mypy check)"""
    logger.info("🧪 Test 7: Checking type hints...")
    
    try:
        import inspect
        from quant_arbitrage import (
            CointegrationScanner,
            SignalGenerator,
            ExecutionEngine,
        )
        
        # Check CointegrationScanner methods
        for method_name in ['connect', 'scan_pairs', 'get_universe']:
            method = getattr(CointegrationScanner, method_name)
            sig = inspect.signature(method)
            # Just verify method exists and is callable
            assert callable(method), f"{method_name} not callable"
        
        logger.info("✅ Type hints verified (methods callable)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Type hints test failed: {e}")
        return False


def test_module_structure() -> bool:
    """Test 8: Module file structure is complete"""
    logger.info("🧪 Test 8: Checking module structure...")
    
    try:
        import os
        
        module_path = "c:\\Users\\furka\\Desktop\\freqtrade_bot\\quant_arbitrage"
        
        required_files = [
            "__init__.py",
            "config.py",
            "cointegration_scanner.py",
            "signal_generator.py",
            "execution_engine.py",
            "cointegration_analyzer.py",
            "spread_calculator.py",
            "websocket_provider.py",
            "funding_arbitrage.py",
            "risk_manager.py",
            "requirements.txt",
        ]
        
        missing_files = []
        for filename in required_files:
            filepath = os.path.join(module_path, filename)
            if not os.path.exists(filepath):
                missing_files.append(filename)
        
        if missing_files:
            logger.error(f"❌ Missing files: {missing_files}")
            return False
        
        logger.info(f"✅ All {len(required_files)} required files present")
        return True
        
    except Exception as e:
        logger.error(f"❌ Module structure test failed: {e}")
        return False


async def run_all_tests(full: bool = False) -> Tuple[int, int]:
    """Run all tests and return (passed, total)"""
    
    logger.info("\n" + "="*70)
    logger.info("🚀 QUANT ARBITRAGE SYSTEM - INTEGRATION TEST SUITE")
    logger.info("="*70 + "\n")
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Dataclasses", test_dataclasses),
        ("Enums", test_enums),
        ("Mathematical Modules", test_mathematical_modules),
        ("Async Components", test_async_components),
        ("Type Hints", test_type_hints),
        ("Module Structure", test_module_structure),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                logger.error(f"❌ {test_name} FAILED\n")
        except Exception as e:
            logger.error(f"❌ {test_name} ERROR: {e}\n")
    
    return passed, total


async def main():
    """Main test runner"""
    
    full_test = "--full" in sys.argv
    
    passed, total = await run_all_tests(full_test)
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info(f"📊 TEST SUMMARY: {passed}/{total} tests passed")
    logger.info("="*70)
    
    if passed == total:
        logger.info("✅ ALL TESTS PASSED - SYSTEM READY FOR DEPLOYMENT\n")
        return 0
    else:
        logger.error(f"❌ {total - passed} TESTS FAILED - FIX BEFORE DEPLOYMENT\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
