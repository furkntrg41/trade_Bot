"""
Main Entry Point - Production Trading Bot Orchestrator
=======================================================
Assembles ExecutionEngine, StrategyCore, and WebSocket streams
to execute statistical arbitrage on cointegrated pairs.

ARCHITECTURE:
1. Load config.json (API keys) and pairs_config.json (pairs)
2. Initialize ExecutionEngine (connect to Binance Futures)
3. Initialize SignalGenerator for each pair
4. Subscribe to WebSocket streams (asyncio.gather)
5. Process ticks -> Update strategy -> Get signal -> Execute

Features:
- Graceful shutdown (Ctrl+C)
- Concurrent pair monitoring
- Error recovery
- Real-time logging
- Safety protocol integration

Author: Quant Team
Date: 2026-02-01
"""

import asyncio
import json
import logging
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

from quant_arbitrage.config import get_config, Config
from quant_arbitrage.execution_engine import ExecutionEngine
from quant_arbitrage.signal_generator import SignalGenerator, TradingSignal


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            "logs/trading_bot.log",
            mode="a",
        ),
    ],
)

logger = logging.getLogger(__name__)


@dataclass
class PairConfig:
    """Trading pair configuration from pairs_config.json"""
    pair_id: str
    leg_a: str
    leg_b: str
    hedge_ratio: float
    z_score_threshold: float = 2.0
    stop_loss_z: float = 4.0
    half_life_candles: int = 12


class TradingBot:
    """
    Main trading bot orchestrator
    
    Responsibilities:
    - Component initialization and lifecycle
    - WebSocket subscription management
    - Tick processing and signal generation
    - Trade execution coordination
    - Graceful error handling and shutdown
    """
    
    def __init__(
        self,
        config_path: str = "config.json",
        pairs_config_path: str = "pairs_config.json",
    ):
        """
        Initialize bot with configuration files
        
        Args:
            config_path: Path to config.json (API keys)
            pairs_config_path: Path to pairs_config.json (trading pairs)
        """
        self.config_path = Path(config_path)
        self.pairs_config_path = Path(pairs_config_path)
        
        # Configuration
        self.config: Optional[Config] = None
        self.pair_configs: List[PairConfig] = []
        
        # Components
        self.execution_engine: Optional[ExecutionEngine] = None
        self.signal_generators: Dict[str, SignalGenerator] = {}
        
        # State management
        self.running = False
        self.active_tasks: Set[asyncio.Task] = set()
        self.shutdown_event = asyncio.Event()
        
        # Statistics
        self.signals_processed = 0
        self.trades_executed = 0
        self.start_time = datetime.utcnow()
        
        logger.info(
            "🤖 TradingBot initialized | "
            f"Config: {self.config_path} | "
            f"Pairs: {self.pairs_config_path}"
        )
    
    def load_configuration(self) -> bool:
        """
        Load config.json and pairs_config.json
        
        Returns:
            True if loaded successfully
        """
        try:
            # Load main config (API keys)
            self.config = get_config(require_api_keys=True)
            logger.info(
                f"✅ Config loaded | "
                f"Mode: {self.config.trading_mode.value} | "
                f"Dry-run: {self.config.dry_run}"
            )
            
            # Load pairs configuration
            if not self.pairs_config_path.exists():
                logger.error(
                    f"❌ Pairs config not found: {self.pairs_config_path}"
                )
                return False
            
            with open(self.pairs_config_path, "r") as f:
                pairs_data = json.load(f)
            
            self.pair_configs = [
                PairConfig(
                    pair_id=pair["pair_id"],
                    leg_a=pair["leg_a"],
                    leg_b=pair["leg_b"],
                    hedge_ratio=pair["hedge_ratio"],
                    z_score_threshold=pair.get("z_score_threshold", 2.0),
                    stop_loss_z=pair.get("stop_loss_z", 4.0),
                    half_life_candles=pair.get("half_life_candles", 12),
                )
                for pair in pairs_data.get("pairs", [])
            ]
            
            logger.info(
                f"✅ Pairs config loaded | "
                f"Pairs: {len(self.pair_configs)}"
            )
            
            for pair in self.pair_configs:
                logger.info(
                    f"   📊 {pair.pair_id} | "
                    f"{pair.leg_a} ↔ {pair.leg_b} | "
                    f"β={pair.hedge_ratio:.4f}"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Configuration loading failed: {e}", exc_info=True)
            return False
    
    async def initialize_components(self) -> bool:
        """
        Initialize ExecutionEngine and SignalGenerators
        
        Returns:
            True if all components initialized successfully
        """
        try:
            # Initialize ExecutionEngine
            self.execution_engine = ExecutionEngine(config=self.config)
            connected = await self.execution_engine.connect()
            
            if not connected:
                logger.error("❌ ExecutionEngine connection failed")
                return False
            
            logger.info("✅ ExecutionEngine initialized")
            
            # Initialize SignalGenerator for each pair
            for pair_config in self.pair_configs:
                try:
                    # Extract symbols (remove /USDT suffix)
                    symbol_a = pair_config.leg_a.replace("/USDT", "")
                    symbol_b = pair_config.leg_b.replace("/USDT", "")
                    
                    # Create SignalGenerator
                    signal_gen = SignalGenerator(
                        pair_x=symbol_a,
                        pair_y=symbol_b,
                        hedge_ratio=pair_config.hedge_ratio,
                        config=self.config,
                    )
                    
                    # Register execution callback
                    signal_gen.register_signal_callback(
                        self._create_execution_callback(pair_config)
                    )
                    
                    self.signal_generators[pair_config.pair_id] = signal_gen
                    
                    logger.info(
                        f"✅ SignalGenerator initialized | "
                        f"Pair: {pair_config.pair_id}"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"❌ SignalGenerator init failed for {pair_config.pair_id}: {e}",
                        exc_info=True,
                    )
                    return False
            
            logger.info(
                f"✅ All {len(self.signal_generators)} "
                f"SignalGenerators initialized"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Component initialization failed: {e}", exc_info=True)
            return False
    
    def _create_execution_callback(self, pair_config: PairConfig):
        """
        Create execution callback for a pair
        
        Args:
            pair_config: Trading pair configuration
            
        Returns:
            Async callback function
        """
        async def execute_signal_callback(signal: TradingSignal) -> None:
            """
            Execute trade when signal arrives
            
            Args:
                signal: TradingSignal from SignalGenerator
            """
            try:
                self.signals_processed += 1
                
                logger.info(
                    f"📡 SIGNAL RECEIVED #{self.signals_processed} | "
                    f"{signal}"
                )
                
                # Only execute if ExecutionEngine is ready
                if not self.execution_engine or not self.execution_engine.exchange:
                    logger.warning(
                        f"⚠️ Skipping execution: ExecutionEngine not ready"
                    )
                    return
                
                # Execute signal
                executed = await self.execution_engine.execute_signal(signal)
                
                if executed:
                    self.trades_executed += 1
                    logger.info(
                        f"✅ TRADE EXECUTED #{self.trades_executed} | "
                        f"Pair: {pair_config.pair_id} | "
                        f"Signal: {signal.signal_type.name}"
                    )
                else:
                    logger.warning(
                        f"⚠️ EXECUTION FAILED | "
                        f"Pair: {pair_config.pair_id}"
                    )
                    
            except Exception as e:
                logger.error(
                    f"❌ Signal execution failed: {e}",
                    exc_info=True,
                )
        
        return execute_signal_callback
    
    async def start_monitoring(self) -> None:
        """
        Start WebSocket monitoring for all pairs
        
        Subscribes to real-time ticker updates and processes signals
        """
        logger.info("🔌 Starting WebSocket monitoring...")
        
        # Create tasks for each SignalGenerator
        monitoring_tasks = []
        
        for pair_id, signal_gen in self.signal_generators.items():
            try:
                # Each generator runs independently
                task = asyncio.create_task(
                    self._monitor_pair(pair_id, signal_gen)
                )
                monitoring_tasks.append(task)
                
            except Exception as e:
                logger.error(
                    f"❌ Failed to start monitoring for {pair_id}: {e}",
                    exc_info=True,
                )
        
        if not monitoring_tasks:
            logger.error("❌ No monitoring tasks created")
            return
        
        # Store tasks for cleanup
        self.active_tasks.update(monitoring_tasks)
        
        logger.info(
            f"✅ Monitoring started for {len(monitoring_tasks)} pairs"
        )
        
        # Wait for all monitoring tasks (until shutdown)
        try:
            await asyncio.gather(*monitoring_tasks, return_exceptions=True)
        except asyncio.CancelledError:
            logger.info("📢 Monitoring tasks cancelled")
        except Exception as e:
            logger.error(f"❌ Monitoring error: {e}", exc_info=True)
    
    async def _monitor_pair(
        self,
        pair_id: str,
        signal_gen: SignalGenerator,
    ) -> None:
        """
        Monitor single pair for cointegration signals
        
        Args:
            pair_id: Pair identifier
            signal_gen: SignalGenerator instance
        """
        try:
            logger.info(f"📊 Starting monitoring for {pair_id}")
            
            # Start WebSocket streaming for this pair
            # Subscribe to ticker updates from exchange
            await signal_gen.ws_provider.watch_ticker(
                signal_gen.pair_x,
                signal_gen.pair_y,
            )
            
        except asyncio.CancelledError:
            logger.info(f"🛑 Monitoring stopped for {pair_id}")
        except Exception as e:
            logger.error(
                f"❌ Monitoring error for {pair_id}: {e}",
                exc_info=True,
            )
    
    async def shutdown_gracefully(self) -> None:
        """
        Graceful shutdown handler
        
        - Cancel all pending tasks
        - Close exchange connections
        - Save final state
        """
        logger.info("🛑 Initiating graceful shutdown...")
        self.running = False
        
        # Set shutdown event
        self.shutdown_event.set()
        
        # Cancel all active tasks
        for task in self.active_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to finish
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        
        # Close ExecutionEngine
        if self.execution_engine:
            try:
                await self.execution_engine.disconnect()
                logger.info("✅ ExecutionEngine disconnected")
            except Exception as e:
                logger.error(f"⚠️ Disconnect error: {e}")
        
        # Close SignalGenerators
        for pair_id, signal_gen in self.signal_generators.items():
            try:
                # Close WebSocket connections if any
                if hasattr(signal_gen, 'ws_provider'):
                    await signal_gen.ws_provider.close()
            except Exception as e:
                logger.error(
                    f"⚠️ SignalGenerator cleanup error for {pair_id}: {e}"
                )
        
        # Log final statistics
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        logger.info(
            f"📊 FINAL STATISTICS:\n"
            f"   Uptime: {uptime:.1f}s\n"
            f"   Signals processed: {self.signals_processed}\n"
            f"   Trades executed: {self.trades_executed}\n"
            f"   Success rate: {self.trades_executed/max(self.signals_processed, 1)*100:.1f}%"
        )
        
        logger.info("✅ Graceful shutdown complete")
    
    async def run(self) -> None:
        """
        Main bot execution loop
        
        Steps:
        1. Load configuration
        2. Initialize components
        3. Start monitoring
        4. Wait for shutdown
        """
        try:
            # Step 1: Load configuration
            if not self.load_configuration():
                logger.error("❌ Failed to load configuration")
                return
            
            # Step 2: Initialize components
            if not await self.initialize_components():
                logger.error("❌ Failed to initialize components")
                return
            
            # Step 3: Start monitoring
            self.running = True
            logger.info(
                "================================================================================\n"
                "🚀 TRADING BOT STARTED\n"
                "================================================================================\n"
                f"Config: {self.config.trading_mode.value} mode (dry_run={self.config.dry_run})\n"
                f"Pairs: {len(self.pair_configs)}\n"
                f"Time: {datetime.utcnow().isoformat()}\n"
                "================================================================================\n"
                "Press Ctrl+C to stop\n"
                "================================================================================"
            )
            
            # Start WebSocket monitoring (blocks until shutdown)
            await self.start_monitoring()
            
        except Exception as e:
            logger.error(f"❌ Bot execution failed: {e}", exc_info=True)
        finally:
            await self.shutdown_gracefully()


async def main():
    """
    Entry point for trading bot
    
    Sets up signal handlers and runs async event loop
    """
    bot = TradingBot(
        config_path="config.json",
        pairs_config_path="pairs_config.json",
    )
    
    # Signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"📢 Signal {sig} received")
        # Schedule shutdown
        asyncio.create_task(bot.shutdown_gracefully())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run the bot
        await bot.run()
    except KeyboardInterrupt:
        logger.info("⌨️ Keyboard interrupt received")
        await bot.shutdown_gracefully()
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        await bot.shutdown_gracefully()


if __name__ == "__main__":
    try:
        # Create logs directory
        Path("logs").mkdir(exist_ok=True)
        
        # Run async event loop
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
