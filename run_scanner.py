#!/usr/bin/env python3
"""
🚀 COINTEGRATION SCANNER - STANDALONE EXECUTABLE
=================================================
Analyzes Binance Futures market data to find statistically cointegrated pairs
for mean-reversion trading strategies.

USAGE:
    python run_scanner.py

REQUIREMENTS:
    - Binance API credentials in config.json or environment variables
    - Internet connection for data fetching
    - Required packages: ccxt, statsmodels, pandas, numpy, matplotlib

OUTPUT:
    1. pairs_config.json - Bot configuration file
    2. cointegration_results_TIMESTAMP.csv - Detailed analysis
    3. plots/*.png - Visual validation charts

Author: Quant Team
Date: 2026-02-01
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """Verify all required packages are installed"""
    required = {
        'ccxt': 'ccxt',
        'statsmodels': 'statsmodels',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'matplotlib': 'matplotlib'
    }
    
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ Missing required packages:")
        for pkg in missing:
            print(f"   • {pkg}")
        print("\n📦 Install with: pip install " + " ".join(missing))
        return False
    
    return True


def print_banner():
    """Print welcome banner"""
    print("\n" + "="*80)
    print("🚀 COINTEGRATION SCANNER - MARKET ANALYZER")
    print("="*80)
    print("Searching for mathematically linked pairs in crypto futures markets")
    print("Method: Engle-Granger Two-Step Cointegration Test")
    print("="*80 + "\n")


async def run_scanner():
    """Execute the scanner"""
    try:
        from quant_arbitrage.cointegration_scanner import main as scanner_main
        await scanner_main()
        return True
    except Exception as e:
        print(f"\n❌ Scanner execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    print_banner()
    
    # Check dependencies
    print("📋 Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print("✅ All dependencies installed\n")
    
    # Check config
    config_path = project_root / "quant_arbitrage" / "config.py"
    if not config_path.exists():
        print("⚠️ Warning: config.py not found")
        print("   Make sure Binance API credentials are configured\n")
    
    # Run scanner
    print("🔍 Starting scanner...\n")
    success = asyncio.run(run_scanner())
    
    if success:
        print("\n" + "="*80)
        print("✅ SCANNER COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nNext steps:")
        print("1. Review pairs_config.json for valid trading pairs")
        print("2. Validate spread plots in plots/ directory")
        print("3. Start the trading bot with: python -m quant_arbitrage.main_bot")
        print("="*80 + "\n")
    else:
        print("\n❌ Scanner failed. Check errors above.\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Scanner interrupted by user. Exiting...\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        sys.exit(1)
