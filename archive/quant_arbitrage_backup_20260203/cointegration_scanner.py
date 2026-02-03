"""
Cointegration Scanner - Binance Verisini Çekip Tarama
=======================================================
Binance spot/futures'dan OHLCV verisi çekerek,
kointegrasyon testi yapıp best pairs'ı bulup raporlayan scanner.

CCXT Async ile ve statsmodels'i kullanan production-grade kod.

Author: Quant Team
Date: 2026-02-01
"""

import asyncio
import logging
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

try:
    import ccxt.async_support as ccxt
except ImportError:
    raise ImportError("CCXT kütüphanesi gerekli: pip install ccxt")

from .cointegration_analyzer import CointegrationAnalyzer, CointegrationResult
from .config import get_config, Config

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
except ImportError:
    logger.warning("matplotlib not installed - plotting disabled")
    plt = None


logger = logging.getLogger(__name__)


class CointegrationScanner:
    """
    Binance'den veri çekerek kointegrasyon testi yapan scanner.
    
    Workflow:
    1. Binance'den trading pair listesini al (filter: volume, liquid)
    2. Her pair için geçmiş OHLCV verisini indir
    3. Close fiyatlarında kointegrasyon testi çalıştır
    4. Best pairs'ı raporla (CSV/JSON)
    
    Type-safe, async, error-handled.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Args:
            config: Configuration object (default: get_config())
        """
        self.config = config or get_config()
        self.exchange: Optional[ccxt.Exchange] = None
        self.analyzer = CointegrationAnalyzer(
            lookback_window=self.config.cointegration.lookback_days,
            adf_pvalue_threshold=self.config.cointegration.adf_pvalue_threshold,
            coint_pvalue_threshold=self.config.cointegration.coint_pvalue_threshold,
            min_correlation=self.config.cointegration.min_correlation,
        )
        
        self.price_data: Dict[str, np.ndarray] = {}
        self.results: List[CointegrationResult] = []
        
    async def connect(self) -> bool:
        """
        Connect to Binance (CCXT async)
        
        For scanner, we only need public data (no API keys required)
        
        Returns:
            True if connected
        """
        try:
            # Scanner only needs public data - no API keys required
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Futures market
                },
            })
            
            # Test connection
            markets = await self.exchange.load_markets()
            logger.info(f"✅ Binance connection successful ({len(markets)} markets)")
            logger.info("📊 Using public API (no authentication required for scanner)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Binance bağlantı hatası: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Binance bağlantısını kapat"""
        if self.exchange:
            await self.exchange.close()
    
    async def get_universe(self) -> List[str]:
        """
        Trading universe'ü al: Likid USDT pair'leri
        
        Returns:
            [BTC/USDT, ETH/USDT, ...] şeklinde pair listesi
        """
        if not self.exchange:
            logger.error("Exchange bağlı değil")
            return []
        
        try:
            # Tüm USDT pair'lerini al
            pairs = [
                symbol for symbol in self.exchange.symbols
                if symbol.endswith(f"/{self.config.cointegration.trading_pair_suffix}")
                and symbol.split('/')[0] not in self.config.cointegration.exclude_symbols
            ]
            
            logger.info(f"📊 {len(pairs)} USDT pair bulundu")
            
            # Volume filtrelemesi (çok likit olanları koru)
            logger.info("📈 Volume filtrelemesi yapılıyor...")
            
            filtered_pairs = []
            for pair in pairs[:50]:  # İlk 50 taranır
                try:
                    ticker = await self.exchange.fetch_ticker(pair)
                    volume_usdt = ticker.get('quoteVolume', 0)
                    
                    if volume_usdt >= self.config.cointegration.min_volume_usdt:
                        filtered_pairs.append(pair)
                        logger.debug(f"  ✅ {pair}: {volume_usdt:,.0f} USDT")
                    else:
                        logger.debug(f"  ❌ {pair}: {volume_usdt:,.0f} USDT (çok az)")
                    
                except Exception as e:
                    logger.warning(f"  ⚠️ {pair} ticker hatası: {e}")
                    continue
            
            logger.info(f"✅ {len(filtered_pairs)} likid pair seçildi")
            return filtered_pairs[:30]  # Top 30 döndür
            
        except Exception as e:
            logger.error(f"Universe alma hatası: {e}")
            return []
    
    async def fetch_ohlcv(
        self,
        pair: str,
        days: int = 60,
    ) -> Optional[np.ndarray]:
        """
        Pair için geçmiş OHLCV verisi indir.
        
        Args:
            pair: BTC/USDT
            days: Kaç günlük veri (default: 60 gün = 1440 saat)
            
        Returns:
            Close fiyatları np.ndarray veya None
        """
        if not self.exchange:
            logger.error("Exchange bağlı değil")
            return None
        
        try:
            timeframe = '1h'  # 1-hour candles
            
            # Veri indir
            since = self.exchange.parse8601(
                (datetime.utcnow() - timedelta(days=days)).isoformat()
            )
            
            logger.debug(f"🔄 {pair} için {days} günlük (1h) veri indiriliyor...")
            
            ohlcv = await self.exchange.fetch_ohlcv(
                pair,
                timeframe=timeframe,
                since=since,
                limit=days * 24 + 100,  # 60 days * 24 hours + buffer
            )
            
            if not ohlcv:
                logger.warning(f"⚠️ {pair} veri boş")
                return None
            
            # Close fiyatlarını çıkar
            close_prices = np.array([candle[4] for candle in ohlcv])
            
            logger.debug(f"✅ {pair}: {len(close_prices)} mum indirildi")
            return close_prices
            
        except Exception as e:
            logger.error(f"❌ {pair} indirme hatası: {e}")
            return None
    
    async def scan_pairs(self, pairs: Optional[List[str]] = None) -> List[CointegrationResult]:
        """
        Pair'lerin kointegrasyon testini yap.
        
        Args:
            pairs: Test edilecek pair listesi (None = universe al)
            
        Returns:
            CointegrationResult listesi (sıralı)
        """
        # Universe al
        if pairs is None:
            pairs = await self.get_universe()
        
        if len(pairs) < 2:
            logger.error("En azından 2 pair gereklidir")
            return []
        
        # OHLCV verisini indir
        logger.info(f"📥 {len(pairs)} pair için veri indiriliyor...")
        
        self.price_data = {}
        for pair in pairs:
            close_prices = await self.fetch_ohlcv(pair, self.config.cointegration.lookback_days)
            if close_prices is not None and len(close_prices) >= 100:
                # Pair adını sadeleştir (BTC/USDT → BTC)
                symbol = pair.split('/')[0]
                self.price_data[symbol] = close_prices
                logger.info(f"✅ {symbol}: {len(close_prices)} mum")
            
            # Rate limiting
            await asyncio.sleep(0.2)
        
        logger.info(f"📊 {len(self.price_data)} pair veri yüklü, tarama başlıyor...")
        
        # Kointegrasyon testi
        self.results = self.analyzer.scan_universe(
            self.price_data,
            top_n=self.config.cointegration.top_n_pairs,
        )
        
        return self.results
    
    def export_pairs_config(self, filename: str = "pairs_config.json") -> str:
        """
        Generate production-ready pairs_config.json for the bot.
        
        Args:
            filename: Output filename
            
        Returns:
            File path
        """
        import json
        
        if not self.results:
            logger.warning("No results to export")
            return ""
        
        # Filter: Only cointegrated pairs with half-life < 24 hours
        valid_pairs = [
            r for r in self.results
            if r.is_cointegrated and r.half_life < 24.0
        ]
        
        if not valid_pairs:
            logger.warning("No valid pairs found (half-life < 24h)")
            return ""
        
        config_data = {
            "pairs": [
                {
                    "pair_id": f"{result.pair_x}_{result.pair_y}",
                    "leg_a": f"{result.pair_x}/USDT",
                    "leg_b": f"{result.pair_y}/USDT",
                    "hedge_ratio": round(result.hedge_ratio, 4),
                    "z_score_threshold": 2.0,
                    "stop_loss_z": 4.0,
                    "half_life_candles": int(result.half_life)
                }
                for result in valid_pairs
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"✅ pairs_config.json generated: {len(valid_pairs)} valid pairs")
        logger.info(f"💾 Saved to: {filename}")
        
        return filename
    
    def export_results(self, format: str = "csv") -> str:
        """
        Sonuçları dosyaya kaydet.
        
        Args:
            format: csv veya json
            
        Returns:
            Dosya yolu
        """
        if not self.results:
            logger.warning("Sonuç yok")
            return ""
        
        # DataFrame oluştur
        data = []
        for result in self.results:
            data.append({
                'Pair X': result.pair_x,
                'Pair Y': result.pair_y,
                'Correlation': f"{result.correlation:.4f}",
                'Hedge Ratio (β)': f"{result.hedge_ratio:.4f}",
                'ADF Statistic': f"{result.adf_statistic:.4f}",
                'ADF P-Value': f"{result.adf_pvalue:.4f}",
                'Coint P-Value': f"{result.coint_pvalue:.4f}",
                'Cointegrated': '✅ Yes' if result.is_cointegrated else '❌ No',
                'Half-Life (hours)': f"{result.half_life:.1f}",
            })
        
        df = pd.DataFrame(data)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        if format == "csv":
            filepath = f"cointegration_results_{timestamp}.csv"
            df.to_csv(filepath, index=False)
            logger.info(f"💾 Sonuçlar kaydedildi: {filepath}")
        elif format == "json":
            filepath = f"cointegration_results_{timestamp}.json"
            df.to_json(filepath, orient='records', indent=2)
            logger.info(f"💾 Sonuçlar kaydedildi: {filepath}")
        
        return filepath
    
    def get_best_pairs(self, n: int = 5) -> List[Tuple[str, str, float]]:
        """
        En iyi N pair'i döndür (pair_x, pair_y, hedge_ratio)
        
        Args:
            n: Kaç pair
            
        Returns:
            [(X, Y, β), ...] listesi
        """
        best = [
            (r.pair_x, r.pair_y, r.hedge_ratio)
            for r in self.results[:n]
            if r.is_cointegrated
        ]
        return best
    
    def plot_spread(self, result: CointegrationResult, output_dir: str = "plots") -> str:
        """
        Generate visual plot of the spread for validation.
        
        Args:
            result: CointegrationResult to plot
            output_dir: Directory to save plots
            
        Returns:
            Plot file path
        """
        if plt is None:
            logger.warning("matplotlib not installed - cannot plot")
            return ""
        
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Get price data
        price_x = self.price_data.get(result.pair_x)
        price_y = self.price_data.get(result.pair_y)
        
        if price_x is None or price_y is None:
            logger.warning(f"No price data for {result.pair_x} or {result.pair_y}")
            return ""
        
        # Calculate spread
        log_x = np.log(price_x)
        log_y = np.log(price_y)
        spread = log_y - result.hedge_ratio * log_x
        
        # Calculate z-score
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)
        z_score = (spread - spread_mean) / spread_std
        
        # Create plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Plot 1: Normalized prices
        ax1.plot(price_x / price_x[0], label=f'{result.pair_x} (normalized)', alpha=0.7)
        ax1.plot(price_y / price_y[0], label=f'{result.pair_y} (normalized)', alpha=0.7)
        ax1.set_title(f'Normalized Prices: {result.pair_x} vs {result.pair_y}', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Normalized Price')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Z-Score of Spread
        ax2.plot(z_score, label='Z-Score', color='purple', linewidth=1.5)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)
        ax2.axhline(y=2, color='red', linestyle='--', linewidth=1, alpha=0.7, label='Entry Threshold (+2σ)')
        ax2.axhline(y=-2, color='green', linestyle='--', linewidth=1, alpha=0.7, label='Entry Threshold (-2σ)')
        ax2.axhline(y=4, color='darkred', linestyle=':', linewidth=1, alpha=0.7, label='Stop Loss (±4σ)')
        ax2.axhline(y=-4, color='darkred', linestyle=':', linewidth=1, alpha=0.7)
        ax2.fill_between(range(len(z_score)), -2, 2, alpha=0.1, color='gray')
        ax2.set_title(f'Spread Z-Score (Hedge Ratio β={result.hedge_ratio:.4f})', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Time (hours)')
        ax2.set_ylabel('Z-Score')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)
        
        # Add statistics text
        stats_text = (
            f"Cointegration Stats:\\n"
            f"• ADF p-value: {result.adf_pvalue:.4f}\\n"
            f"• Coint p-value: {result.coint_pvalue:.4f}\\n"
            f"• Half-life: {result.half_life:.1f} hours\\n"
            f"• Correlation: {result.correlation:.4f}"
        )
        ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes, 
                fontsize=9, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # Save
        filename = f"{result.pair_x}_{result.pair_y}_spread.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"📊 Plot saved: {filepath}")
        return filepath
    
    def plot_all_valid_pairs(self, output_dir: str = "plots") -> List[str]:
        """
        Generate plots for all valid cointegrated pairs.
        
        Args:
            output_dir: Directory to save plots
            
        Returns:
            List of plot file paths
        """
        valid_pairs = [
            r for r in self.results
            if r.is_cointegrated and r.half_life < 24.0
        ]
        
        if not valid_pairs:
            logger.warning("No valid pairs to plot")
            return []
        
        plot_paths = []
        for result in valid_pairs:
            try:
                path = self.plot_spread(result, output_dir)
                if path:
                    plot_paths.append(path)
            except Exception as e:
                logger.error(f"Error plotting {result.pair_x}_{result.pair_y}: {e}")
        
        logger.info(f"✅ Generated {len(plot_paths)} plots in {output_dir}/")
        return plot_paths


async def main():
    """Production-ready scanner with complete workflow"""
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger.info("="*80)
    logger.info("🚀 COINTEGRATION SCANNER - PRODUCTION MODE")
    logger.info("="*80)
    logger.info("Objective: Find mean-reverting pairs for statistical arbitrage")
    logger.info("Method: Engle-Granger Two-Step Cointegration Test")
    logger.info("Data: Binance Futures, 1h candles, 60 days lookback")
    logger.info("="*80 + "\n")
    
    # Config create (scanner doesn't need API keys - uses public data)
    config = get_config(require_api_keys=False)  # Scanner uses public data only
    
    # Scanner create
    scanner = CointegrationScanner(config)
    
    try:
        # 1. Connect
        logger.info("📡 Step 1: Connecting to Binance Futures API (public data)...")
        if not await scanner.connect():
            logger.error("❌ Connection failed. Aborting.")
            return
        logger.info("✅ Connected successfully\n")
        
        # 2. Scan
        logger.info("🔍 Step 2: Scanning for cointegrated pairs...")
        results = await scanner.scan_pairs()
        
        if not results:
            logger.warning("⚠️ No cointegrated pairs found. Try adjusting thresholds.")
            return
        
        logger.info(f"✅ Scan complete: {len(results)} pairs found\n")
        
        # 3. Sonuçları göster
        logger.info("="*80)
        logger.info("🎯 TOP COINTEGRATED PAIRS")
        logger.info("="*80)
        
        for i, result in enumerate(results[:10], 1):
            status = "✅ VALID" if result.half_life < 24.0 else "⚠️ SLOW"
            logger.info(f"{i}. {result.pair_x} vs {result.pair_y}")
            logger.info(f"   Hedge Ratio: {result.hedge_ratio:.4f} | ADF p: {result.adf_pvalue:.4f} | Half-life: {result.half_life:.1f}h {status}")
        
        logger.info("\n" + "="*80)
        
        # 4. pairs_config.json oluştur
        logger.info("\n📝 Step 3: Generating pairs_config.json...")
        config_file = scanner.export_pairs_config("pairs_config.json")
        
        if config_file:
            logger.info(f"✅ Configuration file generated: {config_file}")
        else:
            logger.warning("⚠️ No valid pairs for config (half-life >= 24h)")
        
        # 5. CSV export
        logger.info("\n📊 Step 4: Exporting detailed results...")
        csv_file = scanner.export_results("csv")
        logger.info(f"✅ Results exported: {csv_file}")
        
        # 6. Grafikleri oluştur
        logger.info("\n📈 Step 5: Generating spread visualization plots...")
        plot_files = scanner.plot_all_valid_pairs("plots")
        
        if plot_files:
            logger.info(f"✅ Generated {len(plot_files)} plots:")
            for pf in plot_files[:5]:  # Show first 5
                logger.info(f"   • {pf}")
            if len(plot_files) > 5:
                logger.info(f"   ... and {len(plot_files)-5} more")
        else:
            logger.warning("⚠️ No plots generated (matplotlib not installed or no valid pairs)")
        
        # Final summary
        logger.info("\n" + "="*80)
        logger.info("✅ SCAN COMPLETE")
        logger.info("="*80)
        logger.info(f"Total pairs scanned: {len(scanner.price_data) * (len(scanner.price_data)-1) // 2}")
        logger.info(f"Cointegrated pairs: {len(results)}")
        valid_count = len([r for r in results if r.half_life < 24.0])
        logger.info(f"Valid pairs (half-life < 24h): {valid_count}")
        logger.info(f"\nOutput files:")
        logger.info(f"  • pairs_config.json (bot configuration)")
        logger.info(f"  • {csv_file} (detailed results)")
        logger.info(f"  • plots/ directory ({len(plot_files)} visualizations)")
        logger.info("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"❌ Scanner error: {e}", exc_info=True)
        
    finally:
        await scanner.disconnect()
        logger.info("👋 Disconnected from exchange\n")


if __name__ == "__main__":
    asyncio.run(main())
