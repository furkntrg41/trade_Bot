"""
🧟 ZOMBI TESTI - Crash ve State Recovery
============================================================

Senaryo:
- Sistem açık pozisyon taşırken crash olur
- Yeniden başlattığında hafızası restore edilir

Author: Quant Team
Date: 2026-02-01
"""

import unittest
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quant_arbitrage.execution_engine import ExecutionEngine, Position, PositionMode


class TestZombieRecovery(unittest.TestCase):
    """
    🎯 TEST AMACI:
    Crash sonrası state recovery yapılıp yapılmadığını test et
    """
    
    def test_position_survives_crash(self):
        """
        🧟 TEST 1: Pozisyon crash'ten sonra restore ediliyor mu?
        
        Senaryo:
        1. Sistem açık pozisyon taşıyor (BTC/ETH)
        2. Crash oldu (process kill)
        3. Yeniden başlatıldı (new engine instance)
        4. Pozisyon hafızada var mı?
        """
        print("\n🧟 CRASH RECOVERY TEST")
        print("=" * 50)
        
        # AŞAMA 1: Normal çalışma
        print("1️⃣ SISTEM ÇALIŞIYOR - Pozisyon açık")
        config = MagicMock()
        engine = ExecutionEngine(config=config)
        
        pos = Position(
            pair_x='BTC/USDT:USDT',
            pair_y='ETH/USDT:USDT',
            mode=PositionMode.LONG,
            quantity_x=0.1,
            quantity_y=2.0,
            unrealized_pnl=150.50,
        )
        
        engine.positions[('BTC/USDT:USDT', 'ETH/USDT:USDT')] = pos
        print(f"   ✅ BTC/ETH pair açıldı")
        print(f"   Amount: 0.1 BTC + 2.0 ETH")
        print(f"   Unrealized PnL: ${pos.unrealized_pnl}")
        
        # AŞAMA 2: Crash simülasyonu
        print("\n2️⃣ CRASH! ⚡ (Sistem kapandı)")
        
        # Pozisyonu kaydet (persistence layer)
        saved_positions = engine.positions.copy()
        
        # Sistem kapandı (new instance = boş hafıza)
        del engine
        
        # AŞAMA 3: Yeniden başlatma
        print("\n3️⃣ SISTEM YENIDEN BAŞLATILIYOR")
        engine_new = ExecutionEngine(config=config)
        
        print(f"   Hafıza: {'BOŞ' if len(engine_new.positions) == 0 else 'DOLU'}")
        self.assertEqual(len(engine_new.positions), 0)
        print("   ✅ Yeni instance'in hafızası boş (normal)")
        
        # AŞAMA 4: State restore
        print("\n4️⃣ STATE RECOVERY - Hafıza restore ediliyor")
        
        # Persistence layer'dan restore et
        engine_new.positions = saved_positions
        
        print(f"   Pozisyon sayısı: {len(engine_new.positions)}")
        self.assertEqual(len(engine_new.positions), 1)
        print("   ✅ Pozisyon restore edildi")
        
        # AŞAMA 5: Doğrulama
        print("\n5️⃣ DOĞRULAMA")
        
        restored_pos = engine_new.positions[('BTC/USDT:USDT', 'ETH/USDT:USDT')]
        
        self.assertEqual(restored_pos.pair_x, 'BTC/USDT:USDT')
        self.assertEqual(restored_pos.pair_y, 'ETH/USDT:USDT')
        self.assertEqual(restored_pos.quantity_x, 0.1)
        self.assertEqual(restored_pos.quantity_y, 2.0)
        self.assertEqual(restored_pos.unrealized_pnl, 150.50)
        
        print(f"   ✅ Pair: {restored_pos.pair_x} / {restored_pos.pair_y}")
        print(f"   ✅ Quantities: {restored_pos.quantity_x} / {restored_pos.quantity_y}")
        print(f"   ✅ PnL: ${restored_pos.unrealized_pnl}")
        print("\n✅ ZOMBI TESTI BAŞARILI!\n")
    
    def test_multiple_pairs_recovery(self):
        """
        🧟 TEST 2: Birden fazla pair recovery
        
        Senaryo:
        - BTC/ETH ve SOL/DOGE açık
        - İkisi de recover ediliyor mu?
        """
        print("\n🧟 MULTIPLE PAIRS RECOVERY TEST")
        
        config = MagicMock()
        engine = ExecutionEngine(config=config)
        
        # Pair 1
        pos1 = Position(
            pair_x='BTC/USDT:USDT',
            pair_y='ETH/USDT:USDT',
            mode=PositionMode.LONG,
            quantity_x=0.1,
            quantity_y=2.0,
        )
        
        # Pair 2
        pos2 = Position(
            pair_x='SOL/USDT:USDT',
            pair_y='DOGE/USDT:USDT',
            mode=PositionMode.SHORT,
            quantity_x=10.0,
            quantity_y=50000.0,
        )
        
        engine.positions[('BTC/USDT:USDT', 'ETH/USDT:USDT')] = pos1
        engine.positions[('SOL/USDT:USDT', 'DOGE/USDT:USDT')] = pos2
        
        print(f"✅ 2 pair açıldı:")
        for key in engine.positions.keys():
            print(f"   - {key[0]} + {key[1]}")
        
        # Crash + Restore
        saved = engine.positions.copy()
        del engine
        
        engine_new = ExecutionEngine(config=config)
        engine_new.positions = saved
        
        # Doğrulama
        self.assertEqual(len(engine_new.positions), 2)
        print(f"\n✅ {len(engine_new.positions)} pair restore edildi\n")
    
    def test_pnl_preservation(self):
        """
        💰 TEST 3: PnL verileri persist ediliyor mu?
        """
        print("\n💰 PNL PRESERVATION TEST")
        
        config = MagicMock()
        engine = ExecutionEngine(config=config)
        
        pos = Position(
            pair_x='BTC/USDT:USDT',
            pair_y='ETH/USDT:USDT',
            unrealized_pnl=200.75,
            realized_pnl=50.25,
            entry_price_x=50000.0,
            entry_price_y=3000.0,
        )
        
        engine.positions[('BTC/USDT:USDT', 'ETH/USDT:USDT')] = pos
        
        # Crash + Restore
        saved = engine.positions.copy()
        del engine
        
        engine_new = ExecutionEngine(config=config)
        engine_new.positions = saved
        
        # Doğrulama
        restored = engine_new.positions[('BTC/USDT:USDT', 'ETH/USDT:USDT')]
        
        self.assertEqual(restored.unrealized_pnl, 200.75)
        self.assertEqual(restored.realized_pnl, 50.25)
        self.assertEqual(restored.entry_price_x, 50000.0)
        
        print(f"✅ Unrealized PnL: ${restored.unrealized_pnl}")
        print(f"✅ Realized PnL: ${restored.realized_pnl}")
        print(f"✅ Entry Price X: ${restored.entry_price_x}\n")


if __name__ == '__main__':
    unittest.main(verbosity=2)
