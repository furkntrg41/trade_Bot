#!/usr/bin/env python3
"""
Pre-flight Check Script
=======================
Validates that all components are ready for trading bot execution.

Run this before starting main.py to ensure all dependencies and configs are correct.
"""

import sys
import json
from pathlib import Path
from typing import Tuple

def check_files() -> Tuple[bool, str]:
    """Check that all required files exist"""
    required_files = [
        "config.json",
        "pairs_config.json",
        "quant_arbitrage/execution_engine.py",
        "quant_arbitrage/signal_generator.py",
        "quant_arbitrage/config.py",
        "main.py",
    ]
    
    print("\n📋 Checking required files...")
    all_exist = True
    
    for file in required_files:
        path = Path(file)
        if path.exists():
            size = path.stat().st_size
            print(f"  ✅ {file} ({size:,} bytes)")
        else:
            print(f"  ❌ {file} - NOT FOUND")
            all_exist = False
    
    return all_exist, "Files" if all_exist else "Missing files"

def check_config() -> Tuple[bool, str]:
    """Check config.json is valid"""
    print("\n⚙️  Checking config.json...")
    
    try:
        with open("config.json") as f:
            config = json.load(f)
        
        # Check exchange key and secret
        exchange_config = config.get("exchange", {})
        api_key = exchange_config.get("key", "")
        api_secret = exchange_config.get("secret", "")
        
        if not api_key or not api_secret:
            print(f"  ⚠️  API keys not configured in config.json")
            print("  → Update config.json with your Binance API credentials:")
            print(f'     "key": "your_api_key",')
            print(f'     "secret": "your_api_secret",')
            return False, "Config incomplete"
        
        # Check for sensitive info
        if api_key and len(api_key) > 4:
            masked = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
            print(f"  ✅ API Key: {masked}")
        else:
            print(f"  ✅ API Key configured")
        
        print(f"  ✅ Config valid")
        return True, "Config"
        
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid JSON: {e}")
        return False, "Config JSON error"
    except Exception as e:
        print(f"  ❌ Error reading config: {e}")
        return False, "Config read error"

def check_pairs_config() -> Tuple[bool, str]:
    """Check pairs_config.json has valid pairs"""
    print("\n📊 Checking pairs_config.json...")
    
    try:
        with open("pairs_config.json") as f:
            pairs_data = json.load(f)
        
        pairs = pairs_data.get("pairs", [])
        print(f"  ✅ Found {len(pairs)} trading pairs")
        
        if len(pairs) < 3:
            print(f"  ⚠️  Warning: Only {len(pairs)} pairs (recommend >= 3)")
        
        # Validate pair structure
        for i, pair in enumerate(pairs[:3]):  # Show first 3
            required = ["pair_id", "leg_a", "leg_b", "hedge_ratio"]
            missing = [k for k in required if k not in pair]
            
            if missing:
                print(f"  ❌ Pair {i} missing: {missing}")
                return False, "Pair structure invalid"
            
            print(
                f"  ✅ Pair {i+1}: {pair['pair_id']} "
                f"(β={pair['hedge_ratio']:.4f})"
            )
        
        if len(pairs) > 3:
            print(f"  ... and {len(pairs)-3} more pairs")
        
        return True, "Pairs config"
        
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid JSON: {e}")
        return False, "Pairs JSON error"
    except Exception as e:
        print(f"  ❌ Error reading pairs: {e}")
        return False, "Pairs read error"

def check_dependencies() -> Tuple[bool, str]:
    """Check Python dependencies"""
    print("\n📦 Checking Python dependencies...")
    
    required = {
        "asyncio": "async support",
        "ccxt": "exchange API",
        "numpy": "numerical computing",
        "pandas": "data processing",
        "statsmodels": "statistical tests",
    }
    
    missing = []
    for module, description in required.items():
        try:
            __import__(module)
            print(f"  ✅ {module}: {description}")
        except ImportError:
            print(f"  ❌ {module}: {description} - NOT INSTALLED")
            missing.append(module)
    
    if missing:
        print(f"\n  Install with: pip install {' '.join(missing)}")
        return False, "Missing dependencies"
    
    return True, "Dependencies"

def check_logs_dir() -> Tuple[bool, str]:
    """Check/create logs directory"""
    print("\n📁 Checking logs directory...")
    
    logs_dir = Path("logs")
    try:
        logs_dir.mkdir(exist_ok=True)
        print(f"  ✅ Logs directory ready: {logs_dir.absolute()}")
        return True, "Logs dir"
    except Exception as e:
        print(f"  ❌ Cannot create logs dir: {e}")
        return False, "Logs dir error"

def main():
    """Run all checks"""
    print("=" * 70)
    print("🚀 TRADING BOT PRE-FLIGHT CHECK")
    print("=" * 70)
    
    checks = [
        check_files,
        check_config,
        check_pairs_config,
        check_dependencies,
        check_logs_dir,
    ]
    
    results = []
    for check_func in checks:
        try:
            passed, name = check_func()
            results.append((passed, name))
        except Exception as e:
            print(f"❌ Unexpected error in {check_func.__name__}: {e}")
            results.append((False, check_func.__name__))
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 CHECK SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for p, _ in results if p)
    total = len(results)
    
    for passed_flag, name in results:
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("=" * 70)
    
    if passed == total:
        print(f"\n✅ ALL CHECKS PASSED ({passed}/{total})")
        print("\n🚀 Ready to start trading bot!")
        print("\n   Run: python main.py")
        return 0
    else:
        print(f"\n❌ SOME CHECKS FAILED ({passed}/{total})")
        print("\nFix the issues above and try again.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
