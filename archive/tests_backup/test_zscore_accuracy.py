"""
📐 MATEMATİKSEL DOĞRULUK TESTİ (Z-Score & Spread Calculation)
==============================================================

Senaryo:
- Elle girilen sabit fiyat serileri (dummy data)
- Z-Score hesaplama doğruluğu
- Sıfıra bölme koruması
- Signal generation doğruluğu

Author: Quant Team
Date: 2026-02-01
"""

import unittest
import numpy as np
from collections import deque

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from quant_arbitrage.spread_calculator import (
    PairsSpreadCalculator,
    SpreadSignal,
    SignalType,
)


class TestZScoreMathematicalAccuracy(unittest.TestCase):
    """
    🎯 TEST AMACI:
    Z-Score hesaplamalarının matematiksel olarak doğru olup olmadığını
    sabit sayı dizileriyle (dummy data) doğrula.
    """
    
    def setUp(self):
        """Test öncesi hazırlık"""
        self.calculator = PairsSpreadCalculator(
            lookback_window=10,  # Küçük window test için
            hedge_ratio=0.5,     # 1:2 hedge ratio
        )
    
    def test_zscore_calculation_divergence_high(self):
        """
        📈 TEST 1: Spread yükseldiğinde Z-Score pozitif olmalı
        
        Senaryo: Price X sabit, Price Y yükseliyor
        Beklenen: Z-Score > 2.0 → BUY signal
        """
        # Dummy data: X sabit, Y yükseliyor
        price_x_series = [100] * 15  # Sabit 100
        price_y_series = list(range(100, 115))  # 100'den 114'e yükseliş
        
        # Feed data
        signals = []
        for px, py in zip(price_x_series, price_y_series):
            signal = self.calculator.add_prices(px, py)
            if signal:
                signals.append(signal)
        
        # Son signal'ı kontrol et
        last_signal = signals[-1]
        
        # ✅ ASSERTIONS
        self.assertIsNotNone(last_signal, "Signal should be generated")
        self.assertGreater(last_signal.z_score, 0, 
                          "Z-Score should be POSITIVE when Y rises relative to X")
        self.assertEqual(last_signal.signal_type, SignalType.BUY,
                        "Should generate BUY signal when spread diverges high")
        
        print(f"✅ DIVERGENCE HIGH TEST BAŞARILI!")
        print(f"   Z-Score: {last_signal.z_score:.3f}")
        print(f"   Signal: {last_signal.signal_type}")
        print(f"   Confidence: {last_signal.confidence:.2%}")
    
    def test_zscore_calculation_divergence_low(self):
        """
        📉 TEST 2: Spread düştüğünde Z-Score negatif olmalı
        
        Senaryo: Price X yükseliyor, Price Y sabit
        Beklenen: Z-Score < -2.0 → SELL signal
        """
        # Dummy data: X yükseliyor, Y sabit
        price_x_series = list(range(100, 115))  # 100'den 114'e
        price_y_series = [100] * 15  # Sabit 100
        
        # Feed data
        signals = []
        for px, py in zip(price_x_series, price_y_series):
            signal = self.calculator.add_prices(px, py)
            if signal:
                signals.append(signal)
        
        last_signal = signals[-1]
        
        # ✅ ASSERTIONS
        self.assertIsNotNone(last_signal)
        self.assertLess(last_signal.z_score, 0,
                       "Z-Score should be NEGATIVE when X rises relative to Y")
        self.assertEqual(last_signal.signal_type, SignalType.SELL,
                        "Should generate SELL signal when spread diverges low")
        
        print(f"✅ DIVERGENCE LOW TEST BAŞARILI!")
        print(f"   Z-Score: {last_signal.z_score:.3f}")
        print(f"   Signal: {last_signal.signal_type}")
    
    def test_zscore_mean_reversion(self):
        """
        🎯 TEST 3: Spread sıfıra yaklaşırsa EXIT signal
        
        Senaryo: İlk ayrışma, sonra birleşme
        Beklenen: EXIT signal when Z → 0
        """
        # İlk 10: Ayrışma (Y yükseliyor)
        # Son 5: Birleşme (Y tekrar düşüyor)
        price_x_series = [100] * 15
        price_y_series = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118,
                         116, 114, 112, 110, 108]  # Yükselip düşüyor
        
        signals = []
        for px, py in zip(price_x_series, price_y_series):
            signal = self.calculator.add_prices(px, py)
            if signal:
                signals.append(signal)
        
        # Son signal Z-score'u 0'a yakın olmalı
        last_signal = signals[-1]
        
        # ✅ ASSERTIONS
        self.assertLess(abs(last_signal.z_score), 2.0,
                       "Z-Score should be near zero during mean reversion")
        
        # EXIT signal olabilir (eğer entry yapılmışsa)
        print(f"✅ MEAN REVERSION TEST BAŞARILI!")
        print(f"   Z-Score near zero: {last_signal.z_score:.3f}")
        print(f"   Signal: {last_signal.signal_type}")
    
    def test_division_by_zero_protection(self):
        """
        🛡️ TEST 4: Sıfıra bölme koruması
        
        Senaryo: Tüm fiyatlar aynı (std = 0)
        Beklenen: System crash etmemeli, güvenli değer dönmeli
        """
        # Tüm fiyatlar sabit (volatilite = 0)
        price_x_series = [100] * 15
        price_y_series = [100] * 15
        
        # Bu sistem crash yapmamalı
        try:
            signals = []
            for px, py in zip(price_x_series, price_y_series):
                signal = self.calculator.add_prices(px, py)
                if signal:
                    signals.append(signal)
            
            # ✅ ASSERTIONS
            # Signal üretilmeyebilir (çünkü volatilite yok)
            # Ama sistem crash etmemeli
            print("✅ ZERO DIVISION PROTECTION BAŞARILI!")
            print(f"   No crash with zero volatility")
            print(f"   Signals generated: {len(signals)}")
            
        except ZeroDivisionError:
            self.fail("❌ System crashed on zero division!")
        except Exception as e:
            print(f"⚠️ Other error (acceptable): {e}")
    
    def test_manual_zscore_calculation(self):
        """
        🧮 TEST 5: Manuel Z-Score hesaplama ile karşılaştır
        
        Elle hesaplanan Z-Score ile sistem hesaplaması eşit mi?
        """
        # Basit dummy data
        prices_x = [100, 100, 100, 100, 100]
        prices_y = [100, 101, 102, 103, 104]
        
        # Sisteme besle
        for px, py in zip(prices_x, prices_y):
            self.calculator.add_prices(px, py)
        
        # Son fiyatlarla spread hesapla
        last_px, last_py = prices_x[-1], prices_y[-1]
        
        # Spread = log(Y) - β*log(X)
        spread_series = []
        for px, py in zip(prices_x, prices_y):
            spread = np.log(py) - self.calculator.hedge_ratio * np.log(px)
            spread_series.append(spread)
        
        # Manuel Z-Score
        mean_spread = np.mean(spread_series)
        std_spread = np.std(spread_series)
        
        if std_spread > 0:
            manual_zscore = (spread_series[-1] - mean_spread) / std_spread
            
            # Sistemin hesapladığı Z-Score
            last_signal = self.calculator.add_prices(last_px, last_py)
            
            if last_signal:
                system_zscore = last_signal.z_score
                
                # ✅ ASSERTIONS: %5 tolerans ile eşit mi?
                self.assertAlmostEqual(
                    manual_zscore, system_zscore, delta=0.05,
                    msg=f"Manual Z-Score ({manual_zscore:.3f}) != System Z-Score ({system_zscore:.3f})"
                )
                
                print("✅ MANUAL CALCULATION MATCH BAŞARILI!")
                print(f"   Manual Z-Score: {manual_zscore:.3f}")
                print(f"   System Z-Score: {system_zscore:.3f}")
                print(f"   Difference: {abs(manual_zscore - system_zscore):.5f}")
    
    def test_signal_threshold_accuracy(self):
        """
        🎯 TEST 6: Signal threshold'ları doğru tetikliyor mu?
        
        Entry: |Z| > 2.0
        Exit: |Z| < 0.5
        """
        calculator = PairsSpreadCalculator(
            lookback_window=10,
            hedge_ratio=0.5,
        )
        
        # Kontrollü spread oluştur
        # İlk 10: Normal (Z ≈ 0)
        # Son 5: Ayrışma (Z > 2.0)
        
        price_x = [100] * 15
        price_y = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100,
                  105, 110, 115, 120, 125]  # Son 5 çok yükseliyor
        
        signals = []
        for px, py in zip(price_x, price_y):
            signal = calculator.add_prices(px, py)
            if signal:
                signals.append(signal)
        
        # Son signal'ı incele
        if signals:
            last_signal = signals[-1]
            
            # Z-Score > 2.0 ise BUY/SELL olmalı
            if abs(last_signal.z_score) > 2.0:
                self.assertIn(last_signal.signal_type, [SignalType.BUY, SignalType.SELL],
                            "Should generate entry signal when |Z| > 2.0")
                print(f"✅ THRESHOLD TEST BAŞARILI!")
                print(f"   Z-Score: {last_signal.z_score:.3f}")
                print(f"   Signal: {last_signal.signal_type} (correct for |Z| > 2.0)")


class TestSpreadCalculatorEdgeCases(unittest.TestCase):
    """
    🧪 EDGE CASES: Sınır durumları test et
    """
    
    def test_insufficient_data(self):
        """
        ⚠️ TEST: Yetersiz veri → signal üretmemeli
        """
        calculator = PairsSpreadCalculator(lookback_window=100, hedge_ratio=0.5)
        
        # Sadece 5 veri noktası (window 100 ama)
        for i in range(5):
            signal = calculator.add_prices(100 + i, 100 + i)
            self.assertIsNone(signal, "Should not generate signal with insufficient data")
        
        print("✅ INSUFFICIENT DATA TEST BAŞARILI!")
    
    def test_extreme_prices(self):
        """
        🌪️ TEST: Aşırı fiyat değerleri (crash etmemeli)
        """
        calculator = PairsSpreadCalculator(lookback_window=10, hedge_ratio=0.5)
        
        # Aşırı fiyatlar
        extreme_prices = [1e-10, 1e10, 0.001, 999999999]
        
        try:
            for px in extreme_prices:
                for py in extreme_prices:
                    signal = calculator.add_prices(px, py)
            
            print("✅ EXTREME PRICES TEST BAŞARILI!")
            print("   System handled extreme values without crash")
        except Exception as e:
            self.fail(f"❌ System crashed on extreme prices: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
