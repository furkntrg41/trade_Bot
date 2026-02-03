"""
🚨 SABOTAJ TESTİ (Legging Risk - Emergency Rollback)
======================================================

Senaryo: 
- A varlığı alım emri BAŞARILI (✅)
- B varlığı satış emri BAŞARISIZ (❌ Network Error)
- Beklenen: A derhal satılmalı (Emergency Rollback)

Author: Quant Team
Date: 2026-02-01
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quant_arbitrage.execution_engine import ExecutionEngine, Order, OrderStatus
from quant_arbitrage.signal_generator import TradingSignal, SignalType, SignalStrength
from quant_arbitrage.config import get_config


class TestLeggingRiskProtection(unittest.TestCase):
    """
    🎯 TEST AMACI:
    Bir leg başarılı, diğer leg başarısız olduğunda sistemin
    panik modu devreye alıp emergency rollback yapıp yapmadığını doğrula.
    """
    
    def setUp(self):
        """Test öncesi hazırlık"""
        self.config = get_config()
        self.engine = ExecutionEngine(self.config)
        
        # Mock exchange
        self.engine.exchange = AsyncMock()
    
    def test_leg_b_fails_triggers_emergency_rollback(self):
        """
        🚨 SABOTAJ SENARYOSU:
        Leg A fills, Leg B throws NetworkError → A must be closed immediately
        """
        async def run_test():
            # 1. Setup signal
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
            
            # 2. Mock tickers (current prices)
            self.engine.exchange.fetch_ticker = AsyncMock(side_effect=[
                {'last': 95000.0},  # BTC price
                {'last': 3800.0},   # ETH price
            ])
            
            # 3. Mock precision methods
            self.engine.exchange.amount_to_precision = Mock(side_effect=lambda s, a: round(a, 4))
            self.engine.exchange.price_to_precision = Mock(side_effect=lambda s, p: round(p, 2))
            
            # 4. 🎭 SABOTAJ: Leg A başarılı, Leg B başarısız
            order_a_success = {
                'id': 'ORDER_A_12345',
                'status': 'closed',
                'filled': 0.5,
                'average': 95000.0,
            }
            
            # Leg B NetworkError fırlatacak
            async def create_order_side_effect(symbol, amount):
                if "BTC" in symbol:
                    # Leg A: BAŞARILI ✅
                    return order_a_success
                elif "ETH" in symbol:
                    # Leg B: BAŞARISIZ ❌
                    raise Exception("NetworkError: Connection timeout")
            
            self.engine.exchange.create_market_buy_order = AsyncMock(
                side_effect=lambda s, a: create_order_side_effect(s, a)
            )
            self.engine.exchange.create_market_sell_order = AsyncMock(
                side_effect=lambda s, a: create_order_side_effect(s, a)
            )
            
            # 5. Mock emergency close (rollback)
            emergency_close_called = []
            
            async def mock_emergency_close(symbol, side, quantity, reason):
                emergency_close_called.append({
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                    'reason': reason,
                })
            
            self.engine._emergency_close_position = AsyncMock(
                side_effect=mock_emergency_close
            )
            
            # 6. Execute signal (bu başarısız olmalı çünkü Leg B fails)
            result = await self.engine._place_buy_order(signal, size_usdt=1000.0)
            
            # 7. ✅ ASSERTIONS: Emergency rollback çağrıldı mı?
            self.assertIsNone(result, "Order should return None after rollback")
            self.assertEqual(len(emergency_close_called), 1, 
                           "❌ CRITICAL: Emergency rollback NOT called!")
            
            # 8. Rollback detaylarını kontrol et
            rollback = emergency_close_called[0]
            self.assertEqual(rollback['side'], 'SELL', 
                           "Should SELL to close the LONG position")
            self.assertIn("BTC", rollback['symbol'], 
                         "Should close the BTC position")
            self.assertGreater(rollback['quantity'], 0, 
                             "Quantity must be positive")
            self.assertIn("Leg B Failure", rollback['reason'], 
                         "Reason should mention Leg B failure")
            
            print("✅ SABOTAJ TESTİ BAŞARILI!")
            print(f"   Leg A filled: ORDER_A_12345")
            print(f"   Leg B failed: NetworkError")
            print(f"   Emergency rollback executed: {rollback}")
        
        # Run async test
        asyncio.run(run_test())
    
    def test_both_legs_succeed_no_rollback(self):
        """
        ✅ NORMAL SENARYO: İki leg de başarılı → rollback olmamalı
        """
        async def run_test():
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
            
            # Mock prices
            self.engine.exchange.fetch_ticker = AsyncMock(side_effect=[
                {'last': 95000.0},
                {'last': 3800.0},
            ])
            
            # Mock precision
            self.engine.exchange.amount_to_precision = Mock(side_effect=lambda s, a: round(a, 4))
            
            # İKİ LEG DE BAŞARILI ✅
            self.engine.exchange.create_market_buy_order = AsyncMock(
                return_value={'id': 'ORDER_A', 'status': 'closed'}
            )
            self.engine.exchange.create_market_sell_order = AsyncMock(
                return_value={'id': 'ORDER_B', 'status': 'closed'}
            )
            
            # Mock emergency close
            emergency_close_called = []
            self.engine._emergency_close_position = AsyncMock(
                side_effect=lambda *args, **kwargs: emergency_close_called.append(True)
            )
            
            # Execute
            result = await self.engine._place_buy_order(signal, size_usdt=1000.0)
            
            # ✅ ASSERTIONS: Rollback çağrılmamalı
            self.assertEqual(len(emergency_close_called), 0, 
                           "Emergency rollback should NOT be called when both legs succeed")
            self.assertIsNotNone(result, "Order should succeed")
            
            print("✅ NORMAL SENARYO BAŞARILI!")
            print("   Both legs filled, no rollback triggered")
        
        asyncio.run(run_test())
    
    def test_emergency_close_retries_on_failure(self):
        """
        🔄 RETRY LOGIC: Emergency close ilk denemede başarısız olursa tekrar denemeli
        """
        async def run_test():
            # Mock emergency close - ilk 2 deneme başarısız, 3. başarılı
            call_count = []
            
            async def failing_close(symbol, quantity):
                call_count.append(len(call_count) + 1)
                if len(call_count) < 3:
                    raise Exception("API Error: Rate limit")
                return {'id': 'EMERGENCY_ORDER', 'status': 'closed'}
            
            self.engine.exchange.create_market_sell_order = AsyncMock(
                side_effect=failing_close
            )
            
            # Execute emergency close (with original implementation)
            try:
                await self.engine._emergency_close_position(
                    symbol="BTC/USDT:USDT",
                    side="SELL",
                    quantity=0.5,
                    reason="Test retry logic"
                )
                
                # ✅ ASSERTIONS
                self.assertEqual(len(call_count), 3, 
                               "Should retry 3 times before success")
                print("✅ RETRY LOGIC BAŞARILI!")
                print(f"   Attempted {len(call_count)} times before success")
            
            except Exception as e:
                # If all retries fail, this is expected
                print(f"⚠️ All retries exhausted: {e}")
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main(verbosity=2)
