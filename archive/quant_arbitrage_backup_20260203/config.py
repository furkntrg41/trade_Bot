"""
Config Module - Centralized Configuration Management
=====================================================
Tüm parametreleri kontrol eden merkezi config.
Magic number yok, her şey buradan gelir.

Author: Quant Team
Date: 2026-02-01
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class TradingMode(Enum):
    """Trading modu"""
    PAPER = "paper"
    LIVE = "live"


@dataclass
class CointegrationConfig:
    """Kointegrasyon analiz konfigürasyonu"""
    
    # Tarama parametreleri
    lookback_days: int = 252  # 1 yıl veri
    min_correlation: float = 0.5  # Ön-filtre
    adf_pvalue_threshold: float = 0.05  # ADF stationarity
    coint_pvalue_threshold: float = 0.05  # Kointegrasyon threshold
    
    # Universe
    exchange: str = "binance"
    trading_pair_suffix: str = "USDT"  # BTCUSDT, ETHUSDT, etc.
    top_n_pairs: int = 10  # Kaç best pair döndür
    min_volume_usdt: float = 1_000_000  # Min 1M USDT volume
    
    # Filtreleme
    exclude_symbols: List[str] = field(default_factory=lambda: ["USDT", "BUSD", "FDUSD"])
    
    def __post_init__(self):
        """Validasyon"""
        assert 0 < self.min_correlation <= 1.0, "Correlation must be 0-1"
        assert 0 < self.adf_pvalue_threshold < 1.0, "P-value must be 0-1"
        assert self.top_n_pairs > 0, "Top N must be positive"


@dataclass
class SpreadSignalConfig:
    """Spread sinyal üretim konfigürasyonu"""
    
    # Z-Score thresholds
    entry_threshold: float = 2.0  # Entry için |Z| > 2σ
    exit_threshold: float = 0.5  # Exit için |Z| < 0.5σ
    stop_loss_threshold: float = 4.0  # SL: Z > 4σ (model break)
    
    # Lookback period
    lookback_periods: int = 252  # Rolling mean/std için
    min_periods: int = 20  # Minimum örnek sayısı
    
    # Kalman filter (dinamik β)
    use_kalman_filter: bool = True
    kalman_process_noise: float = 1e-5
    kalman_measurement_noise: float = 1e-4
    
    def __post_init__(self):
        """Validasyon"""
        assert self.entry_threshold > self.exit_threshold, "Entry > exit threshold"
        assert self.stop_loss_threshold > self.entry_threshold, "SL > entry threshold"
        assert self.lookback_periods > self.min_periods, "Lookback > min_periods"


@dataclass
class FundingArbConfig:
    """Funding rate arbitraj konfigürasyonu"""
    
    # Threshold
    annualized_funding_threshold: float = 0.05  # %5 yıllık
    
    # Position
    min_position_size: float = 0.1  # Min 0.1 BTC/ETH
    max_position_size: float = 10.0  # Max 10 BTC/ETH
    
    # Spread tolerance
    max_spread_tolerance: float = 0.001  # %0.1 spread
    
    # Costs
    trading_fee_per_side: float = 0.0002  # %0.02
    spot_borrow_fee_daily: float = 0.0001  # %0.01 daily
    
    def __post_init__(self):
        """Validasyon"""
        assert 0 < self.min_position_size <= self.max_position_size
        assert 0 < self.annualized_funding_threshold < 1.0


@dataclass
class RiskConfig:
    """Risk management konfigürasyonu"""
    
    # Account
    account_equity_usdt: float = 10_000  # Başlangıç öz sermayesi
    max_drawdown_daily_pct: float = 0.02  # %2 günlük max drawdown
    max_drawdown_monthly_pct: float = 0.10  # %10 aylık
    
    # Position sizing
    max_loss_per_trade_pct: float = 0.01  # %1 per trade
    max_total_delta_exposure: float = 0.10  # %10 portfolio delta
    max_concentration_per_symbol: float = 0.05  # %5 per symbol
    max_leverage: float = 2.0  # Max 2x leverage
    
    # Kelly criterion
    kelly_fraction: float = 0.25  # 1/4 Kelly (safer)
    
    # Position limits
    max_open_positions: int = 5  # Max 5 eş zamanlı
    
    def __post_init__(self):
        """Validasyon"""
        assert 0 < self.account_equity_usdt, "Equity must be positive"
        assert 0 < self.max_loss_per_trade_pct < 1.0
        assert 0 < self.kelly_fraction <= 1.0
        assert self.max_open_positions > 0


@dataclass
class DataConfig:
    """Veri akışı konfigürasyonu"""
    
    # WebSocket
    use_testnet: bool = False
    ws_max_reconnect_attempts: int = 5
    ws_reconnect_delay_seconds: float = 5.0
    
    # Cache
    price_cache_max_size: int = 1000  # Circular buffer
    
    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    log_file: Optional[str] = "bot.log"
    
    # Storage
    db_type: str = "sqlite"  # sqlite, postgres
    db_path: str = "./data/bot.db"


@dataclass
class ExecutionConfig:
    """Order execution konfigürasyonu"""
    
    # Order type
    use_limit_orders: bool = True
    post_only: bool = True  # Maker fees (cheaper)
    
    # Slippage
    max_slippage_pct: float = 0.001  # %0.1
    
    # Timing
    order_timeout_seconds: int = 30  # Order cancel timeout
    min_time_between_orders_ms: int = 100  # Min 100ms delay
    
    # Retry
    max_order_retries: int = 3
    retry_delay_ms: int = 500


@dataclass
class Config:
    """Master configuration container"""
    
    # Mode
    trading_mode: TradingMode = TradingMode.PAPER
    dry_run: bool = True
    
    # Components
    cointegration: CointegrationConfig = field(default_factory=CointegrationConfig)
    signal: SpreadSignalConfig = field(default_factory=SpreadSignalConfig)
    funding: FundingArbConfig = field(default_factory=FundingArbConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    data: DataConfig = field(default_factory=DataConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    
    # API Keys (from environment variables)
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    
    @classmethod
    def load_from_env(cls) -> "Config":
        """Environment variables'dan config yükle"""
        import os
        
        config = cls()
        config.binance_api_key = os.getenv("BINANCE_API_KEY")
        config.binance_api_secret = os.getenv("BINANCE_API_SECRET")
        config.trading_mode = TradingMode(os.getenv("TRADING_MODE", "paper"))
        config.dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
        
        return config
    
    def validate(self, require_api_keys: bool = True) -> bool:
        """
        Validate configuration
        
        Args:
            require_api_keys: If False, skip API key validation (for scanner)
        """
        if require_api_keys:
            assert self.binance_api_key, "API key required"
            assert self.binance_api_secret, "API secret required"
        
        # Consistency checks
        assert (
            self.signal.entry_threshold > self.signal.exit_threshold
        ), "Entry > exit threshold"
        
        assert (
            self.risk.max_loss_per_trade_pct < 1.0
        ), "Loss per trade < 100%"
        
        return True
    
    def __str__(self) -> str:
        """Config özeti"""
        return (
            f"Config[\n"
            f"  Mode: {self.trading_mode.value}\n"
            f"  Equity: {self.risk.account_equity_usdt} USDT\n"
            f"  Max Loss/Trade: {self.risk.max_loss_per_trade_pct*100:.1f}%\n"
            f"  Entry Threshold: {self.signal.entry_threshold}σ\n"
            f"  Funding Threshold: {self.funding.annualized_funding_threshold*100:.1f}%\n"
            f"]"
        )


# Global config instance
_global_config: Optional[Config] = None


def get_config(require_api_keys: bool = True) -> Config:
    """
    Get global config instance
    
    Args:
        require_api_keys: If False, skip API key validation (for scanner)
    """
    global _global_config
    if _global_config is None:
        _global_config = Config.load_from_env()
        _global_config.validate(require_api_keys=require_api_keys)
    return _global_config


def set_config(config: Config) -> None:
    """Global config'i set et (testing için)"""
    global _global_config
    _global_config = config
