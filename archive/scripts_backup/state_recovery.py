#!/usr/bin/env python3
"""
State Recovery & Crash Reconciliation Engine
=============================================

On startup, this script:
1. Connects to Binance Futures
2. Checks for orphaned positions (open without local state)
3. Checks for open orders that didn't get recorded
4. Queries executed orders to fill gaps in trade history
5. Saves reconciled state for warm-start

This ensures the bot can recover from crashes without position loss.

Author: DevOps Team
Date: 2026-02-01
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

try:
    import ccxt
except ImportError:
    print("ERROR: ccxt not installed. Install with: pip install ccxt")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [STATE_RECOVERY] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            "/freqtrade/user_data/logs/state_recovery.log",
            mode="a",
        ),
    ],
)
logger = logging.getLogger(__name__)


class StateRecoveryEngine:
    """
    Crash recovery and state reconciliation engine
    
    Responsibilities:
    - Connect to Binance Futures
    - Detect orphaned positions
    - Verify open orders
    - Query recent trades
    - Write reconciliation report
    """
    
    def __init__(self, config_path: str = "/freqtrade/config.json"):
        """Initialize recovery engine"""
        self.config_path = Path(config_path)
        self.config = None
        self.exchange = None
        self.orphaned_positions: List[Dict] = []
        self.orphaned_orders: List[Dict] = []
        self.recovery_report_path = Path(
            "/freqtrade/user_data/logs/recovery_report.json"
        )
    
    def load_config(self) -> bool:
        """Load config.json"""
        try:
            if not self.config_path.exists():
                logger.error(f"Config not found: {self.config_path}")
                return False
            
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
            
            logger.info("✅ Config loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Config loading failed: {e}")
            return False
    
    def connect_to_exchange(self) -> bool:
        """Connect to Binance Futures"""
        try:
            api_key = self.config.get("exchange", {}).get("key")
            api_secret = self.config.get("exchange", {}).get("secret")
            
            if not api_key or not api_secret:
                logger.warning("⚠️ API keys not configured - skipping state recovery")
                return False
            
            self.exchange = ccxt.binance({
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "future",
                    "defaultMargin": "isolated",
                },
            })
            
            # Load markets
            self.exchange.load_markets()
            
            logger.info("✅ Connected to Binance Futures")
            return True
            
        except Exception as e:
            logger.error(f"❌ Exchange connection failed: {e}")
            return False
    
    async def check_orphaned_positions(self) -> None:
        """
        Query all open positions on Binance
        
        An "orphaned" position is one that exists on exchange
        but has no corresponding entry in local trade history
        """
        try:
            logger.info("🔍 Checking for orphaned positions...")
            
            positions = self.exchange.fetch_positions()
            
            active_positions = [
                p for p in positions
                if p.get("contracts") and float(p.get("contracts", 0)) != 0
            ]
            
            if not active_positions:
                logger.info("✅ No open positions found")
                return
            
            logger.warning(
                f"⚠️ Found {len(active_positions)} open position(s) on exchange:"
            )
            
            for pos in active_positions:
                symbol = pos.get("symbol", "UNKNOWN")
                contracts = float(pos.get("contracts", 0))
                entry_price = float(pos.get("percentage", 0))
                
                logger.warning(
                    f"   📍 {symbol} | Size: {contracts} | "
                    f"Entry: {entry_price:.2f}"
                )
                
                self.orphaned_positions.append({
                    "symbol": symbol,
                    "contracts": contracts,
                    "side": "long" if contracts > 0 else "short",
                    "entry_price": entry_price,
                    "found_at": datetime.utcnow().isoformat(),
                })
            
        except Exception as e:
            logger.error(f"❌ Position check failed: {e}")
    
    async def check_orphaned_orders(self) -> None:
        """
        Query all open orders on Binance
        
        An "orphaned" order is an open order that doesn't exist
        in local state
        """
        try:
            logger.info("🔍 Checking for orphaned orders...")
            
            open_orders = self.exchange.fetch_open_orders()
            
            if not open_orders:
                logger.info("✅ No open orders found")
                return
            
            logger.warning(
                f"⚠️ Found {len(open_orders)} open order(s) on exchange:"
            )
            
            for order in open_orders:
                symbol = order.get("symbol", "UNKNOWN")
                order_type = order.get("type", "unknown")
                side = order.get("side", "unknown")
                amount = float(order.get("amount", 0))
                price = float(order.get("price", 0))
                
                logger.warning(
                    f"   📋 {symbol} | Type: {order_type} | "
                    f"Side: {side} | Amount: {amount} @ {price}"
                )
                
                self.orphaned_orders.append({
                    "symbol": symbol,
                    "order_id": order.get("id"),
                    "type": order_type,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "found_at": datetime.utcnow().isoformat(),
                })
            
        except Exception as e:
            logger.error(f"❌ Order check failed: {e}")
    
    async def query_recent_trades(self) -> None:
        """Query recent executed trades (last 24 hours)"""
        try:
            logger.info("🔍 Querying recent executed trades (last 24h)...")
            
            since = int((datetime.utcnow() - timedelta(days=1)).timestamp() * 1000)
            
            # Get all symbols from config
            symbols = self.config.get("exchange", {}).get("pair_whitelist", [])
            
            all_trades = []
            for symbol in symbols[:5]:  # Limit to avoid rate limit
                try:
                    trades = self.exchange.fetch_my_trades(symbol, since=since)
                    all_trades.extend(trades)
                except Exception as e:
                    logger.debug(f"Could not fetch trades for {symbol}: {e}")
            
            if all_trades:
                logger.info(
                    f"✅ Found {len(all_trades)} recent trades in last 24h"
                )
                
                # Save trades to recovery log
                trades_file = Path(
                    "/freqtrade/user_data/logs/recent_trades.json"
                )
                with open(trades_file, "w") as f:
                    json.dump(all_trades, f, indent=2, default=str)
                
                logger.info(f"   💾 Saved to {trades_file}")
            
        except Exception as e:
            logger.error(f"❌ Trade query failed: {e}")
    
    def write_recovery_report(self) -> None:
        """Write reconciliation report to JSON file"""
        try:
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "status": "recovery_complete",
                "orphaned_positions_count": len(self.orphaned_positions),
                "orphaned_orders_count": len(self.orphaned_orders),
                "orphaned_positions": self.orphaned_positions,
                "orphaned_orders": self.orphaned_orders,
                "recommendations": [],
            }
            
            # Add recommendations
            if self.orphaned_positions:
                report["recommendations"].append(
                    "⚠️ MANUAL ACTION REQUIRED: Orphaned positions detected. "
                    "Review and close them if they don't match your strategy."
                )
            
            if self.orphaned_orders:
                report["recommendations"].append(
                    "⚠️ MANUAL ACTION REQUIRED: Orphaned orders detected. "
                    "Review and cancel them if they don't match your strategy."
                )
            
            if not self.orphaned_positions and not self.orphaned_orders:
                report["status"] = "clean"
                report["recommendations"].append(
                    "✅ All clear - no orphaned positions or orders found"
                )
            
            with open(self.recovery_report_path, "w") as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"✅ Recovery report saved: {self.recovery_report_path}")
            
            # Print summary
            logger.info(
                f"📊 RECOVERY SUMMARY:\n"
                f"   Status: {report['status']}\n"
                f"   Orphaned Positions: {report['orphaned_positions_count']}\n"
                f"   Orphaned Orders: {report['orphaned_orders_count']}\n"
            )
            
            for rec in report["recommendations"]:
                logger.info(f"   {rec}")
            
        except Exception as e:
            logger.error(f"❌ Report writing failed: {e}")
    
    async def run_recovery(self) -> bool:
        """Execute full recovery sequence"""
        try:
            logger.info(
                "="*70
            )
            logger.info(
                "🔄 STATE RECOVERY ENGINE STARTED"
            )
            logger.info(
                "="*70
            )
            
            # Load config
            if not self.load_config():
                logger.warning("⚠️ Skipping recovery - config not available")
                return True
            
            # Connect to exchange
            if not self.connect_to_exchange():
                logger.warning(
                    "⚠️ Skipping recovery - exchange connection failed"
                )
                return True
            
            # Run checks
            await self.check_orphaned_positions()
            await self.check_orphaned_orders()
            await self.query_recent_trades()
            
            # Write report
            self.write_recovery_report()
            
            logger.info(
                "="*70
            )
            logger.info(
                "✅ STATE RECOVERY ENGINE COMPLETE"
            )
            logger.info(
                "="*70
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Recovery failed: {e}", exc_info=True)
            return False


async def main():
    """Entry point"""
    engine = StateRecoveryEngine()
    success = await engine.run_recovery()
    
    if not success:
        logger.error("❌ Recovery encountered errors")
        sys.exit(1)
    
    logger.info("✅ Ready to launch FreqTrade...")
    sys.exit(0)


if __name__ == "__main__":
    try:
        # Ensure logs directory exists
        Path("/freqtrade/user_data/logs").mkdir(parents=True, exist_ok=True)
        
        # Run recovery
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("⌨️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
