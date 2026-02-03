"""
Quant Arbitrage Module
======================

Production-grade quantitative arbitrage system for Binance Futures.

Core Components:
1. CointegrationScanner - Pairs discovery from Binance data
2. SignalGenerator - Real-time Z-score signals via WebSocket
3. ExecutionEngine - Order placement via CCXT

Supporting Modules:
- cointegration_analyzer: Engle-Granger cointegration testing
- spread_calculator: Z-score signals + Kalman filter
- websocket_provider: Real-time tick data
- funding_arbitrage: Spot+Futures delta-neutral arb
- risk_manager: Kelly criterion, position sizing
- config: Centralized configuration

Architecture:
    CointegrationScanner 
        ↓ (find pairs)
    SignalGenerator (via WebSocket)
        ↓ (generate signals)
    ExecutionEngine (place orders)

Usage:
    from quant_arbitrage import (
        CointegrationScanner,
        SignalGenerator,
        ExecutionEngine,
    )
    
    # 1. Discover pairs (offline, one-time)
    scanner = CointegrationScanner()
    await scanner.connect()
    pairs = await scanner.scan_pairs()
    
    # 2. Monitor signals (real-time)
    gen = SignalGenerator(pair_x, pair_y, hedge_ratio)
    gen.register_signal_callback(on_signal)
    
    # 3. Execute trades
    engine = ExecutionEngine()
    await engine.connect()
    await engine.execute_signal(signal)

Author: Quant Team
Version: 1.0
License: MIT
"""

# Core components (main entry points)
from .cointegration_scanner import CointegrationScanner
from .signal_generator import SignalGenerator, MultiPairSignalGenerator, TradingSignal, SignalStrength
from .execution_engine import ExecutionEngine, Order, OrderStatus, Position, PositionMode

# Analyzers
from .cointegration_analyzer import CointegrationAnalyzer, CointegrationResult

# Signals
from .spread_calculator import PairsSpreadCalculator, SpreadSignal, SignalType, KalmanFilterHedgeRatio

# Data
from .websocket_provider import BinanceWebSocketProvider, TickData

# Alias for convenience
WebSocketProvider = BinanceWebSocketProvider

# Arbitrage
from .funding_arbitrage import FundingArbitrage, FundingStatus, FundingRateMonitor

# Risk
from .risk_manager import RiskManager, RiskMetrics, PositionSide

# Config
from .config import Config, get_config, set_config, CointegrationConfig, SpreadSignalConfig, FundingArbConfig, RiskConfig, DataConfig, ExecutionConfig


__all__ = [
    # Core (main entry points)
    'CointegrationScanner',
    'SignalGenerator',
    'MultiPairSignalGenerator',
    'ExecutionEngine',
    
    # Signals & Orders
    'TradingSignal',
    'SignalStrength',
    'Order',
    'OrderStatus',
    'Position',
    'PositionMode',
    
    # Analyzers
    'CointegrationAnalyzer',
    'CointegrationResult',
    
    # Spread Signals
    'PairsSpreadCalculator',
    'SpreadSignal',
    'SignalType',
    'KalmanFilterHedgeRatio',
    
    # Data
    'BinanceWebSocketProvider',
    'WebSocketProvider',
    'TickData',
    
    # Arbitrage
    'FundingArbitrage',
    'FundingStatus',
    'FundingRateMonitor',
    
    # Risk
    'RiskManager',
    'RiskMetrics',
    'PositionSide',
    
    # Config
    'Config',
    'get_config',
    'set_config',
    'CointegrationConfig',
    'SpreadSignalConfig',
    'FundingArbConfig',
    'RiskConfig',
    'DataConfig',
    'ExecutionConfig',
]

__version__ = "1.0.0"
__author__ = "Quant Team"
