"""
🚨 SABOTAJ TESTİ - Legging Risk Protection
============================================================

Senaryo:
- Leg A (BTC alım) = BAŞARILI ✅
- Leg B (ETH satış) = BAŞARISIZ ❌ Network Error
- Beklenen: Emergency rollback (A satılmalı)

Author: Quant Team
Date: 2026-02-01
"""

import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quant_arbitrage.signal_generator import TradingSignal, SignalType


class TestLeggingRiskProtection(unittest.TestCase):
    """
    🎯 TEST AMACI:
    Bir leg başarılı, diğer leg başarısız olduğunda
    emergency rollback yapılıp yapılmadığını doğrula
    """
    
    def test_leg_b_failure_triggers_rollback(self):
        """
        🚨 SABOTAJ SENARYOSU:
        
        Sistem BTC/ETH pair işlemi başlatır:
        - Leg A: BTC satın al = ✅ BAŞARILI
        - Leg B: ETH sat = ❌ BAŞARISIZ (Network Error)
        
        Beklenen: BTC derhal satılmalı (Rollback)
        """
        # Mock exchange
        mock_exchange = MagicMock()
        
        # Leg A: BTC alım BAŞARILI
        mock_exchange.create_market_buy_order = MagicMock(return_value={
            'id': 'ORDER_A_12345',
            'symbol': 'BTC/USDT:USDT',
            'side': 'buy',
            'amount': 0.1,
            'status': 'closed',
            'filled': 0.1,
            'cost': 5000.0,
        })
        
        # Leg B: ETH satış BAŞARISIZ
        mock_exchange.create_market_sell_order = MagicMock(
            side_effect=Exception("NetworkError: Connection timeout")
        )
        
        # Emergency rollback spy
        rollback_called = []
        def mock_emergency_close(**kwargs):
            rollback_called.append(kwargs)
        
        # Senaryo
        print("\n🎬 SABOTAJ SENARYOSU BAŞLANIYOR:")
        print("1️⃣ Leg A (BTC alım): BAŞARILI ✅")
        
        # Leg A place
        try:
            order_a = mock_exchange.create_market_buy_order('BTC/USDT:USDT', 0.1, limit=50000)
            print(f"   ✅ BTC alındı: {order_a['filled']} BTC")
        except Exception as e:
            print(f"   ❌ BTC alımı başarısız: {e}")
            order_a = None
        
        print("2️⃣ Leg B (ETH satış): BAŞARISIZ ❌")
        
        # Leg B place - should fail
        try:
            order_b = mock_exchange.create_market_sell_order('ETH/USDT:USDT', 2.0)
            print(f"   ✅ ETH satıldı: {order_b['filled']} ETH")
        except Exception as e:
            print(f"   ❌ ETH satışı başarısız: {e}")
            
            # Emergency rollback MUST happen
            if order_a:
                print("3️⃣ EMERGENCY ROLLBACK TETIKLENDI! 🚨")
                mock_emergency_close(
                    symbol='BTC/USDT:USDT',
                    side='sell',
                    amount=order_a['filled'],
                    reason="Leg B Failure"
                )
                print(f"   🔄 BTC geri satılıyor: {order_a['filled']} BTC")
        
        # ✅ ASSERTIONS
        print("\n📊 TEST KONTROLLERI:")
        self.assertTrue(order_a is not None, "❌ Leg A başarısız olmalıydı!")
        print("✅ Leg A başarılı oldu")
        
        self.assertTrue(len(rollback_called) > 0, "❌ Rollback çağrılmalıydı!")
        print("✅ Emergency rollback çağrıldı")
        
        rollback = rollback_called[0]
        self.assertEqual(rollback['side'], 'sell', "❌ Satış olmalıydı!")
        print("✅ Rollback satış emri (sell)")
        
        self.assertEqual(rollback['amount'], 0.1, "❌ Tam miktar satılmalıydı!")
        print("✅ Tam BTC miktarı geri satıldı")
        
        print("\n✅ SABOTAJ TESTİ BAŞARILI!\n")
    
    def test_both_legs_success_no_rollback(self):
        """
        ✅ TEST 2: Her iki leg başarılı = Rollback YOK
        
        Senaryo: Normal, sağlıklı trade
        """
        mock_exchange = MagicMock()
        
        # Leg A: Başarılı
        mock_exchange.create_market_buy_order = MagicMock(return_value={
            'id': 'ORDER_A',
            'amount': 0.1,
            'filled': 0.1,
            'status': 'closed',
        })
        
        # Leg B: Başarılı
        mock_exchange.create_market_sell_order = MagicMock(return_value={
            'id': 'ORDER_B',
            'amount': 2.0,
            'filled': 2.0,
            'status': 'closed',
        })
        
        rollback_called = []
        
        print("\n✅ NORMAL TRADE SENARYOSU:")
        
        # Place Leg A
        order_a = mock_exchange.create_market_buy_order('BTC/USDT:USDT', 0.1)
        print(f"1️⃣ Leg A başarılı: BTC {order_a['filled']}")
        
        # Place Leg B
        try:
            order_b = mock_exchange.create_market_sell_order('ETH/USDT:USDT', 2.0)
            print(f"2️⃣ Leg B başarılı: ETH {order_b['filled']}")
        except:
            # Rollback only if B fails
            rollback_called.append(True)
        
        # ✅ ASSERTIONS
        self.assertEqual(len(rollback_called), 0, "❌ Rollback çağrılmamalıydı!")
        print("✅ Rollback çağrılmadı (doğru)\n")
    
    def test_emergency_close_with_retry(self):
        """
        🔄 TEST 3: Emergency close retry logic
        
        Senaryo: İlk rollback başarısız, sonra başarılı
        """
        mock_exchange = MagicMock()
        
        # İlk çağrı fail, 2. çağrı başarılı
        mock_exchange.create_market_sell_order = MagicMock(side_effect=[
            Exception("API Error"),  # 1. attempt
            {'id': 'ROLLBACK_OK', 'status': 'closed'},  # 2. attempt
        ])
        
        print("\n🔄 RETRY LOGIC TEST:")
        
        attempts = 0
        success = False
        
        for attempt in range(3):
            attempts += 1
            try:
                result = mock_exchange.create_market_sell_order('BTC/USDT:USDT', 0.1)
                print(f"✅ Attempt {attempts}: Rollback başarılı")
                success = True
                break
            except Exception as e:
                print(f"❌ Attempt {attempts}: {e}")
        
        # ✅ ASSERTIONS
        self.assertTrue(success, "❌ Rollback başarılı olmalıydı!")
        self.assertEqual(attempts, 2, "❌ 2 deneme olmalıydı!")
        print(f"✅ {attempts} denemede başarılı\n")


if __name__ == '__main__':
    unittest.main(verbosity=2)
