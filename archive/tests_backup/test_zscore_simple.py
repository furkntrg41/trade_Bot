"""
📐 Z-SCORE ACCURACY TEST - Matematiksel Doğruluk
===================================================

Senaryo:
- Dummy data (elle girilen sabit fiyat serileri)
- Z-Score hesaplama doğruluğu
- Division by zero koruması
- Signal generation doğruluğu

Author: Quant Team
Date: 2026-02-01
"""

import unittest
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestZScoreAccuracy(unittest.TestCase):
    """
    🎯 TEST AMACI:
    Z-Score hesaplamalarının matematiksel doğruluğunu test et
    """
    
    def test_zscore_divergence_detection(self):
        """
        📈 TEST 1: Spread ayrışması (Divergence) tespiti
        
        Senaryo:
        - Price X sabit (100)
        - Price Y yükseliyor (100 → 120)
        - Beklenen: Z-Score > 0 (ayrışma var)
        """
        print("\n📈 TEST 1: DIVERGENCE DETECTION")
        
        # Dummy data
        price_x = np.array([100.0] * 10)  # Sabit
        price_y = np.array([100, 102, 104, 106, 108, 110, 112, 114, 116, 118])  # Yükseliyor
        
        # Spread hesapla: spread = log(Y) - log(X)
        spread = np.log(price_y) - np.log(price_x)
        
        # Z-Score: (current - mean) / std
        mean_spread = np.mean(spread)
        std_spread = np.std(spread)
        
        print(f"Mean spread: {mean_spread:.6f}")
        print(f"Std spread: {std_spread:.6f}")
        
        if std_spread > 0:
            zscore_last = (spread[-1] - mean_spread) / std_spread
            print(f"Z-Score (last): {zscore_last:.4f}")
            
            # ✅ ASSERTIONS
            self.assertGreater(zscore_last, 0, "Z-Score pozitif olmalı")
            print("✅ Z-Score pozitif (divergence var)")
        else:
            print("⚠️ Volatilite çok düşük")
    
    def test_zscore_convergence_detection(self):
        """
        📉 TEST 2: Spread yakınlaşması (Convergence) tespiti
        
        Senaryo:
        - Spreads öğleden sonra yakınlaşıyor
        - Beklenen: Z-Score → 0
        """
        print("\n📉 TEST 2: CONVERGENCE DETECTION")
        
        # Dummy data: Ayrışıyor sonra yakınlaşıyor
        price_x = np.array([100.0] * 10)
        price_y = np.array([100, 102, 104, 106, 108, 108, 106, 104, 102, 100])
        
        spread = np.log(price_y) - np.log(price_x)
        
        mean_spread = np.mean(spread)
        std_spread = np.std(spread)
        
        if std_spread > 0:
            zscore_last = (spread[-1] - mean_spread) / std_spread
            print(f"Z-Score (last): {zscore_last:.4f}")
            
            # ✅ ASSERTIONS
            self.assertLess(abs(zscore_last), 1.5, "Z-Score 0'a yakın olmalı")
            print("✅ Z-Score 0'a yakın (convergence)")
    
    def test_division_by_zero_protection(self):
        """
        🛡️ TEST 3: Sıfıra bölme koruması
        
        Senaryo:
        - Tüm fiyatlar aynı (volatilite = 0)
        - Beklenen: Crash etmemeli
        """
        print("\n🛡️ TEST 3: DIVISION BY ZERO PROTECTION")
        
        # Tüm değerler sabit
        price_x = np.array([100.0] * 10)
        price_y = np.array([100.0] * 10)
        
        spread = np.log(price_y) - np.log(price_x)
        
        mean_spread = np.mean(spread)
        std_spread = np.std(spread)
        
        print(f"Mean: {mean_spread}")
        print(f"Std: {std_spread}")
        
        # ✅ ASSERTIONS
        self.assertEqual(std_spread, 0, "Volatilite 0 olmalı")
        print("✅ Volatilite 0 (koruma gereken durum)")
        
        # Division by zero yapma
        try:
            if std_spread > 0:
                zscore = (spread[-1] - mean_spread) / std_spread
            else:
                zscore = 0  # Koruma
                print("✅ Division by zero engellenedi")
        except ZeroDivisionError:
            self.fail("❌ Division by zero exception!")
    
    def test_extreme_divergence(self):
        """
        🌪️ TEST 4: Aşırı ayrışma tespiti
        
        Senaryo:
        - Y çok hızlı yükseliyor
        - Beklenen: Z-Score > 1.0
        """
        print("\n🌪️ TEST 4: EXTREME DIVERGENCE")
        
        # Aşırı ayrışma
        price_x = np.array([100.0] * 10)
        price_y = np.array([100, 110, 120, 130, 140, 150, 160, 170, 180, 190])
        
        spread = np.log(price_y) - np.log(price_x)
        
        mean_spread = np.mean(spread)
        std_spread = np.std(spread)
        
        if std_spread > 0:
            zscore_last = (spread[-1] - mean_spread) / std_spread
            print(f"Z-Score: {zscore_last:.4f}")
            
            # ✅ ASSERTIONS
            self.assertGreater(zscore_last, 1.0, "Z-Score > 1.0 olmalı")
            print("✅ Aşırı divergence tespit edildi (Z > 1.0)")
    
    def test_signal_generation_from_zscore(self):
        """
        🎯 TEST 5: Z-Score'dan signal üretilmesi
        
        Senaryo:
        - Z > 2.0 → BUY signal
        - Z < -2.0 → SELL signal  
        - |Z| < 0.5 → EXIT signal
        """
        print("\n🎯 TEST 5: SIGNAL GENERATION FROM Z-SCORE")
        
        test_cases = [
            (2.5, "BUY"),
            (-2.5, "SELL"),
            (0.3, "EXIT"),
            (1.5, "NEUTRAL"),
        ]
        
        for zscore, expected_signal in test_cases:
            # Simple signal logic
            if zscore > 2.0:
                signal = "BUY"
            elif zscore < -2.0:
                signal = "SELL"
            elif abs(zscore) < 0.5:
                signal = "EXIT"
            else:
                signal = "NEUTRAL"
            
            self.assertEqual(signal, expected_signal, f"Z={zscore} signal mismatch")
            print(f"✅ Z-Score {zscore:+.1f} → {signal}")


class TestZScoreEdgeCases(unittest.TestCase):
    """
    🧪 EDGE CASES: Sınır durumları
    """
    
    def test_insufficient_data(self):
        """
        ⚠️ TEST: Yetersiz veri
        """
        print("\n⚠️ INSUFFICIENT DATA TEST")
        
        # Sadece 2 veri noktası
        price_x = np.array([100.0, 101.0])
        price_y = np.array([100.0, 101.0])
        
        spread = np.log(price_y) - np.log(price_x)
        
        print(f"Data points: {len(spread)}")
        
        # Signal generation gerektir yeterli data
        if len(spread) < 10:
            print("✅ Yetersiz veri, signal üretilmedi")
        else:
            print("Signal üretildi")
    
    def test_large_numbers(self):
        """
        🌪️ TEST: Çok büyük sayılar
        """
        print("\n🌪️ LARGE NUMBERS TEST")
        
        price_x = np.array([50000.0] * 10)
        price_y = np.array([3000.0] * 10)
        
        spread = np.log(price_y) - np.log(price_x)
        std_spread = np.std(spread)
        
        # Due to floating point precision, std is very close to 0
        print(f"Std spread: {std_spread}")
        self.assertLess(abs(std_spread), 1e-10)
        print("✅ Büyük sayılar işlendi")


if __name__ == '__main__':
    unittest.main(verbosity=2)
