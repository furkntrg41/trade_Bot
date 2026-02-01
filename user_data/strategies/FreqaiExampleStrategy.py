"""
FreqAI + LightGBM Futures Strategy + CoinGecko Sentiment Filter
5m timeframe, Binance Futures için optimize edilmiş.

UYARI: Bu strateji PAPER TRADING içindir.
Gerçek parayla kullanmadan önce en az 3 ay backtest + 1 ay dry-run yap.
"""
import logging
import os
import time
from functools import reduce
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

try:
    import requests
except ImportError:
    requests = None

from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter, IStrategy, merge_informative_pair


logger = logging.getLogger(__name__)


class FreqaiExampleStrategy(IStrategy):
    """
    FreqAI LightGBM Regressor Strategy
    
    Bu strateji ML modeli ile fiyat hareketini tahmin eder.
    &-target değeri: Gelecekteki fiyat değişim yüzdesi
    """
    
    # ROI: Endüstri standardı - agresif profit taking
    minimal_roi = {"0": 0.15, "120": 0.075, "360": 0.025, "1440": 0}
    
    # Stoploss: %10 - Futures 2x leverage ile efektif %20
    # Endüstri standardı: Trade'e nefes alma alanı bırak
    stoploss = -0.10
    
    # Trailing stoploss - Endüstri standardı ayarları
    trailing_stop = True
    trailing_stop_positive = 0.02  # Kâr %2'ye ulaşınca trailing başlar
    trailing_stop_positive_offset = 0.03  # %3 offset - kâr koruma
    trailing_only_offset_is_reached = True
    
    # Timeframe
    timeframe = "5m"
    
    # Informative pairs - Multi-timeframe analiz için
    def informative_pairs(self):
        """15m ve 1h RSI için informative pairs tanımla"""
        # dp hazır değilse boş dön
        if not self.dp:
            return []
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        for pair in pairs:
            informative_pairs.append((pair, "15m"))
            informative_pairs.append((pair, "1h"))
        return informative_pairs
    
    # Futures ayarları
    can_short = True  # Short pozisyon açabilir
    
    def leverage(self, pair: str, current_time, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag,
                 side: str, **kwargs) -> float:
        """
        Dinamik leverage. Dry-run'da düşük tut, risk kontrolü için.
        Gerçek trade'de bile max 3x önerilir.
        """
        # Dry-run'da güvenli leverage
        return 2.0
    
    # FreqAI zorunlu ayarlar
    process_only_new_candles = True
    use_exit_signal = True
    
    # FreqAI prediction threshold - DENGELİ AYARLAR
    # Model çıktısı bu değerin üstündeyse LONG, altındaysa SHORT
    entry_threshold = DecimalParameter(0.01, 2.0, default=0.08, space="buy", optimize=True)
    exit_threshold = DecimalParameter(-2.0, -0.01, default=-0.08, space="sell", optimize=True)
    
    # Hyperopt için
    buy_rsi = IntParameter(20, 40, default=30, space="buy", optimize=True)
    sell_rsi = IntParameter(60, 80, default=70, space="sell", optimize=True)
    
    # Sentiment cache (API çağrılarını azaltmak için)
    # Max 100 key sakla, memory leak önleme
    sentiment_cache = {}
    events_cache = {}
    fear_greed_cache = {}
    funding_rate_cache = {}
    _cache_max_size = 50  # Her cache için max key sayısı

    def _clean_old_cache(self, cache_dict: dict, max_size: int = None) -> None:
        """Eski cache key'lerini temizle - Memory leak önleme"""
        if max_size is None:
            max_size = self._cache_max_size
        if len(cache_dict) > max_size:
            # En eski key'leri sil (ilk eklenenler)
            keys_to_remove = list(cache_dict.keys())[:-max_size//2]
            for key in keys_to_remove:
                del cache_dict[key]
            logger.debug(f"Cache cleaned: removed {len(keys_to_remove)} old entries")

    def _get_coingecko_data(self, coin_id: str) -> dict:
        """
        CoinGecko API'den tüm veriyi al (tek istek ile hem sentiment hem events).
        Rate limit tasarrufu için birleştirilmiş metod.
        """
        try:
            if requests is None:
                return {}
            
            cache_key = f"{coin_id}_coingecko_{int(time.time() / 3600)}"
            if cache_key in self.events_cache:
                return self.events_cache[cache_key]
            
            # Cache temizle
            self._clean_old_cache(self.events_cache)
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&community_data=true"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            
            self.events_cache[cache_key] = data
            return data
            
        except Exception as e:
            logger.warning(f"CoinGecko fetch error for {coin_id}: {e}")
            return {}

    def get_coingecko_events(self, coin_id: str) -> dict:
        """
        CoinGecko'dan yaklaşan etkinlikleri al (7 gün içinde).
        """
        try:
            data = self._get_coingecko_data(coin_id)
            if not data:
                return {"has_event": False, "impact": "neutral"}
            
            # Etkinlik kontrolü - upcoming events var mı
            events = data.get("events", [])
            has_event = len(events) > 0
            
            if has_event:
                event_name = events[0].get("title", "Unknown")
                logger.info(f"{coin_id} upcoming event: {event_name}")
                return {"has_event": True, "impact": "positive", "name": event_name}
            
            return {"has_event": False, "impact": "neutral"}
            
        except Exception as e:
            logger.warning(f"Events fetch error for {coin_id}: {e}")
            return {"has_event": False, "impact": "neutral"}
    
    def get_cryptopanic_sentiment(self, coin_id: str = "BTC") -> dict:
        """
        Cryptopanic'ten son 24 saat haber sentiment'i al.
        Developer Plan: 100 req/ay - 12 saatlik cache kullan
        """
        try:
            if requests is None:
                return {"positive": 0, "negative": 0, "neutral": 100}
            
            # 12 saatlik cache (100 req/ay limitini aşmamak için: 2 coin × 2/gün × 30 = 120 ama bazı günler daha az)
            # Güvenli hesap: 2 × 2 × 30 = 120, buffer ile ~90 istek/ay
            cache_key = f"{coin_id}_cryptopanic_{int(time.time() / 43200)}"
            if cache_key in self.sentiment_cache:
                return self.sentiment_cache[cache_key]
            
            # Cache temizle
            self._clean_old_cache(self.sentiment_cache)
            
            # CryptoPanic API - Environment variable'dan al
            api_key = os.environ.get("CRYPTOPANIC_API_KEY", "9993cd1826da97d855ee019eadf92a71de388063")
            url = f"https://cryptopanic.com/api/developer/v2/posts/?auth_token={api_key}&currencies={coin_id}&filter=hot&public=true"
            
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            # Sentiment analizi
            positive = 0
            negative = 0
            neutral = 0
            
            results = data.get("results", [])[:10]  # Son 10 haber
            for post in results:
                votes = post.get("votes", {})
                positive += votes.get("positive", 0)
                negative += votes.get("negative", 0)
                # Sentiment field varsa kullan
                sent = post.get("sentiment")
                if sent == "positive":
                    positive += 1
                elif sent == "negative":
                    negative += 1
                else:
                    neutral += 1
            
            total = positive + negative + neutral
            if total == 0:
                total = 1
            
            result = {
                "positive": round(positive / total * 100),
                "negative": round(negative / total * 100),
                "neutral": round(neutral / total * 100),
                "news_count": len(results)
            }
            
            logger.info(f"{coin_id} news sentiment: +{result['positive']}% / -{result['negative']}% ({result['news_count']} news)")
            
            self.sentiment_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.warning(f"Cryptopanic sentiment error: {e}")
            return {"positive": 0, "negative": 0, "neutral": 100}

    def get_fear_greed_index(self) -> dict:
        """
        Fear & Greed Index al (alternative.me - ücretsiz).
        0-25: Extreme Fear (alım fırsatı)
        25-45: Fear
        45-55: Neutral
        55-75: Greed
        75-100: Extreme Greed (satış fırsatı)
        """
        try:
            if requests is None:
                return {"value": 50, "classification": "Neutral"}
            
            # 2 saatlik cache (günde 12 istek - daha güncel veri)
            cache_key = f"fear_greed_{int(time.time() / 7200)}"
            if cache_key in self.fear_greed_cache:
                return self.fear_greed_cache[cache_key]
            
            # Cache temizle
            self._clean_old_cache(self.fear_greed_cache)
            
            url = "https://api.alternative.me/fng/?limit=1"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            fng_data = data.get("data", [{}])[0]
            value = int(fng_data.get("value", 50))
            classification = fng_data.get("value_classification", "Neutral")
            
            result = {"value": value, "classification": classification}
            
            logger.info(f"Fear & Greed Index: {value} ({classification})")
            
            self.fear_greed_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.warning(f"Fear & Greed fetch error: {e}")
            return {"value": 50, "classification": "Neutral"}

    def get_funding_rate(self, symbol: str = "BTCUSDT") -> float:
        """
        Binance Futures Funding Rate al.
        Pozitif = Longlar ödüyor (çok fazla long var, short fırsatı)
        Negatif = Shortlar ödüyor (çok fazla short var, long fırsatı)
        Normal aralık: -0.01% ile +0.01%
        Extreme: > 0.05% veya < -0.05%
        """
        try:
            if requests is None:
                return 0.0
            
            # 30 dakikalık cache (funding 8 saatte bir güncellenir ama daha sık kontrol)
            cache_key = f"funding_{symbol}_{int(time.time() / 1800)}"
            if cache_key in self.funding_rate_cache:
                return self.funding_rate_cache[cache_key]
            
            # Cache temizle
            self._clean_old_cache(self.funding_rate_cache)
            
            url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if data and len(data) > 0:
                funding_rate = float(data[0].get("fundingRate", 0)) * 100  # Yüzde olarak
            else:
                funding_rate = 0.0
            
            logger.info(f"{symbol} Funding Rate: {funding_rate:.4f}%")
            
            self.funding_rate_cache[cache_key] = funding_rate
            return funding_rate
            
        except Exception as e:
            logger.warning(f"Funding rate fetch error: {e}")
            return 0.0

    def get_coingecko_sentiment(self, coin_id: str) -> str:
        """
        CoinGecko API'den sentiment bilgisi al (7 günlük trend).
        coin_id: 'bitcoin' veya 'ethereum'
        """
        try:
            # Birleştirilmiş CoinGecko verisini kullan (rate limit tasarrufu)
            data = self._get_coingecko_data(coin_id)
            if not data:
                return "neutral"
            
            # Price change 7 gün içinde
            price_change_7d = data.get("market_data", {}).get("price_change_percentage_7d", 0)
            
            if price_change_7d > 5:
                sentiment = "positive"
            elif price_change_7d < -5:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            logger.info(f"{coin_id} sentiment: {sentiment} (7d: {price_change_7d:.2f}%)")
            return sentiment
            
        except Exception as e:
            logger.warning(f"Sentiment fetch error for {coin_id}: {e}")
            return "neutral"

    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        FreqAI için feature üretimi.
        Bu fonksiyon config'deki indicator_periods_candles değerleri için çağrılır.
        period: [10, 20, 50] -> her biri için ayrı ayrı çalışır
        """
        # RSI
        dataframe[f"%-rsi-period_{period}"] = ta.RSI(dataframe, timeperiod=period)
        
        # MFI - Money Flow Index
        dataframe[f"%-mfi-period_{period}"] = ta.MFI(dataframe, timeperiod=period)
        
        # ADX - Trend gücü
        dataframe[f"%-adx-period_{period}"] = ta.ADX(dataframe, timeperiod=period)
        
        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=period, stds=2.2
        )
        dataframe[f"%-bb_lowerband-period_{period}"] = bollinger["lower"]
        dataframe[f"%-bb_middleband-period_{period}"] = bollinger["mid"]
        dataframe[f"%-bb_upperband-period_{period}"] = bollinger["upper"]
        dataframe[f"%-bb_width-period_{period}"] = (
            (bollinger["upper"] - bollinger["lower"]) / bollinger["mid"]
        )
        
        # MACD
        macd = ta.MACD(dataframe, fastperiod=period, slowperiod=period*2, signalperiod=9)
        dataframe[f"%-macd-period_{period}"] = macd["macd"]
        dataframe[f"%-macdsignal-period_{period}"] = macd["macdsignal"]
        dataframe[f"%-macdhist-period_{period}"] = macd["macdhist"]
        
        # EMA
        dataframe[f"%-ema-period_{period}"] = ta.EMA(dataframe, timeperiod=period)
        
        # SMA
        dataframe[f"%-sma-period_{period}"] = ta.SMA(dataframe, timeperiod=period)
        
        # ATR - Volatilite
        dataframe[f"%-atr-period_{period}"] = ta.ATR(dataframe, timeperiod=period)
        
        # ROC - Rate of Change
        dataframe[f"%-roc-period_{period}"] = ta.ROC(dataframe, timeperiod=period)
        
        # Williams %R
        dataframe[f"%-willr-period_{period}"] = ta.WILLR(dataframe, timeperiod=period)
        
        # CCI
        dataframe[f"%-cci-period_{period}"] = ta.CCI(dataframe, timeperiod=period)

        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Sabit period gerektirmeyen feature'lar.
        Fiyat değişimleri, pattern'ler vs.
        """
        # Fiyat değişim oranları
        dataframe["%-pct_change"] = dataframe["close"].pct_change()
        dataframe["%-pct_change_2"] = dataframe["close"].pct_change(periods=2)
        dataframe["%-pct_change_5"] = dataframe["close"].pct_change(periods=5)
        
        # Volume değişimi
        dataframe["%-volume_pct_change"] = dataframe["volume"].pct_change()
        
        # High-Low range
        dataframe["%-hl_range"] = (dataframe["high"] - dataframe["low"]) / dataframe["close"]
        
        # Close pozisyonu (High-Low içinde nerede?)
        hl_range = dataframe["high"] - dataframe["low"]
        dataframe["%-close_position"] = np.where(
            hl_range > 0,
            (dataframe["close"] - dataframe["low"]) / hl_range,
            0.5  # Eşit high-low durumunda orta nokta
        )
        
        # VWAP - Rolling window (20 period) ile hesapla
        typical_price = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3
        vol_sum = dataframe["volume"].rolling(window=20).sum()
        dataframe["%-vwap"] = (
            (typical_price * dataframe["volume"]).rolling(window=20).sum() / 
            vol_sum.replace(0, np.nan)  # Division by zero koruması
        ).fillna(typical_price)  # NaN'ları typical_price ile doldur

        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        FreqAI'ın beklediği standart feature'lar.
        %- prefix'i FreqAI'ın bunları feature olarak algılaması için zorunlu.
        """
        # Day of week (0-6)
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        
        # Hour of day (0-23)
        dataframe["%-hour_of_day"] = dataframe["date"].dt.hour

        return dataframe

    def set_freqai_targets(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        ML modelinin tahmin edeceği hedef değişken.
        &- prefix'i zorunlu.
        
        Burada: Gelecek N mum sonraki fiyat değişimi (%)
        label_period_candles config'den gelir (24 mum = 2 saat @ 5m)
        """
        # Gelecekteki fiyat değişimi hesapla (pandas 2.1+ uyumlu)
        label_period = self.freqai_info["feature_parameters"]["label_period_candles"]
        future_close = dataframe["close"].shift(-label_period)
        dataframe["&-target"] = ((future_close - dataframe["close"]) / dataframe["close"]) * 100

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Standart indicator'lar + FreqAI prediction + Multi-timeframe RSI.
        """
        # FreqAI prediction'ı al
        dataframe = self.freqai.start(dataframe, metadata, self)
        
        # 5m RSI (ana timeframe)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        
        # Multi-timeframe RSI ekleme
        pair = metadata.get("pair", "")
        
        # 15m RSI
        if self.dp:
            inf_15m = self.dp.get_pair_dataframe(pair=pair, timeframe="15m")
            if not inf_15m.empty and len(inf_15m) > 14:
                inf_15m["rsi"] = ta.RSI(inf_15m, timeperiod=14)
                dataframe = merge_informative_pair(
                    dataframe, inf_15m[["date", "rsi"]], 
                    self.timeframe, "15m", ffill=True
                )
                # Rename column (merge_informative_pair adds _15m suffix)
                if "rsi_15m" in dataframe.columns:
                    pass  # Already correct name
                elif "rsi" in dataframe.columns:
                    dataframe["rsi_15m"] = dataframe["rsi"]
            else:
                dataframe["rsi_15m"] = 50  # Default
        
            # 1h RSI
            inf_1h = self.dp.get_pair_dataframe(pair=pair, timeframe="1h")
            if not inf_1h.empty and len(inf_1h) > 14:
                inf_1h["rsi"] = ta.RSI(inf_1h, timeperiod=14)
                dataframe = merge_informative_pair(
                    dataframe, inf_1h[["date", "rsi"]], 
                    self.timeframe, "1h", ffill=True
                )
                # Rename column
                if "rsi_1h" in dataframe.columns:
                    pass
                elif "rsi" in dataframe.columns:
                    dataframe["rsi_1h"] = dataframe["rsi"]
            else:
                dataframe["rsi_1h"] = 50  # Default
                
            # Ensure columns exist with defaults
            if "rsi_15m" not in dataframe.columns:
                dataframe["rsi_15m"] = 50
            if "rsi_1h" not in dataframe.columns:
                dataframe["rsi_1h"] = 50
        else:
            dataframe["rsi_15m"] = 50
            dataframe["rsi_1h"] = 50

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Giriş sinyalleri.
        FreqAI prediction + CoinGecko sentiment + News sentiment + 
        Fear & Greed Index + Funding Rate + klasik RSI filtreleme.
        """
        # Sentiments kontrol - SADECE ilk çağrıda (cache kullan)
        # Her candle'da API çağrısı yapma - rate limit!
        pair = metadata.get('pair', 'BTC/USDT:USDT')
        
        # Default değerler
        sentiment = "neutral"
        news_sentiment = {"positive": 0, "negative": 0, "neutral": 100}
        fear_greed = {"value": 50, "classification": "Neutral"}
        funding_rate = 0.0
        
        # API çağrıları - BTC ve ETH için ayrı cache
        current_hour = int(time.time() / 3600)
        
        # Pair'e göre coin_id ve symbol belirle
        if pair == "BTC/USDT:USDT":
            coin_id = "bitcoin"
            symbol = "BTC"
            funding_symbol = "BTCUSDT"
        elif pair == "ETH/USDT:USDT":
            coin_id = "ethereum"
            symbol = "ETH"
            funding_symbol = "ETHUSDT"
        else:
            coin_id = None
            symbol = None
            funding_symbol = None
        
        if coin_id:
            # Cache key kontrolü - 30 dakikada 1 kez çağır (daha güncel)
            cache_key = f"api_calls_{symbol}_{int(time.time() / 1800)}"
            if cache_key not in self.sentiment_cache:
                sentiment = self.get_coingecko_sentiment(coin_id)
                news_sentiment = self.get_cryptopanic_sentiment(symbol)
                # Events kaldırıldı - CoinGecko API'de boş dönüyor
                fear_greed = self.get_fear_greed_index()  # Bu global, her iki coin için aynı
                funding_rate = self.get_funding_rate(funding_symbol)
                self.sentiment_cache[cache_key] = {
                    "sentiment": sentiment, 
                    "news": news_sentiment, 
                    "fear_greed": fear_greed,
                    "funding_rate": funding_rate
                }
            else:
                cached = self.sentiment_cache[cache_key]
                sentiment = cached.get("sentiment", "neutral")
                news_sentiment = cached.get("news", {"positive": 0, "negative": 0, "neutral": 100})
                fear_greed = cached.get("fear_greed", {"value": 50, "classification": "Neutral"})
                funding_rate = cached.get("funding_rate", 0.0)
        
        # Uyarlanabilir entry threshold
        entry_threshold = self.entry_threshold.value
        exit_threshold_adj = self.exit_threshold.value
        
        # === FEAR & GREED INDEX ETKİSİ ===
        fg_value = fear_greed.get("value", 50)
        
        # Extreme Fear (< 25): LONG için threshold düşür (alım fırsatı!)
        if fg_value < 25:
            entry_threshold -= 0.05
            logger.info(f"🟢 Extreme Fear ({fg_value}): LONG boost, threshold {self.entry_threshold.value} -> {entry_threshold}")
        
        # Extreme Greed (> 75): SHORT için threshold düşür (satış fırsatı!)
        elif fg_value > 75:
            exit_threshold_adj += 0.05  # Daha az negatif = daha kolay short
            logger.info(f"🔴 Extreme Greed ({fg_value}): SHORT boost, threshold {self.exit_threshold.value} -> {exit_threshold_adj}")
        
        # === FUNDING RATE ETKİSİ ===
        # Yüksek pozitif funding (> 0.05%): Çok fazla long var, short fırsatı
        if funding_rate > 0.05:
            exit_threshold_adj += 0.03
            logger.info(f"📈 High Funding ({funding_rate:.4f}%): SHORT favored")
        
        # Yüksek negatif funding (< -0.05%): Çok fazla short var, long fırsatı
        elif funding_rate < -0.05:
            entry_threshold -= 0.03
            logger.info(f"📉 Negative Funding ({funding_rate:.4f}%): LONG favored")
        
        # === NEWS SENTIMENT ETKİSİ ===
        if news_sentiment.get("positive", 0) >= 70:
            entry_threshold -= 0.05
            logger.info(f"📰 Positive news: LONG boost")
        
        if news_sentiment.get("negative", 0) >= 70:
            exit_threshold_adj += 0.05
            logger.info(f"📰 Negative news: SHORT boost")
        
        # DEBUG: Son prediction değerlerini logla
        if len(dataframe) > 0:
            last_pred = dataframe["&-target"].iloc[-1] if "&-target" in dataframe.columns else 0
            last_di = dataframe["DI_values"].iloc[-1] if "DI_values" in dataframe.columns else 999
            last_do_predict = dataframe["do_predict"].iloc[-1] if "do_predict" in dataframe.columns else 0
            last_rsi = dataframe["rsi"].iloc[-1] if "rsi" in dataframe.columns else 50
            last_rsi_15m = dataframe["rsi_15m"].iloc[-1] if "rsi_15m" in dataframe.columns else 50
            last_rsi_1h = dataframe["rsi_1h"].iloc[-1] if "rsi_1h" in dataframe.columns else 50
            logger.info(f"📊 {pair} | Pred: {last_pred:.4f} | DI: {last_di:.2f} | do_predict: {last_do_predict} | RSI: {last_rsi:.1f}/{last_rsi_15m:.1f}/{last_rsi_1h:.1f} | Sentiment: {sentiment}")
            logger.info(f"📊 Thresholds | LONG > {entry_threshold:.2f} | SHORT < {exit_threshold_adj:.2f}")

        # LONG giriş - MTF RSI confluence
        dataframe.loc[
            (
                # FreqAI tahmin geçerli (do_predict == 1)
                (dataframe["do_predict"] == 1)
                &
                # FreqAI pozitif tahmin (fiyat artacak)
                (dataframe["&-target"] > entry_threshold)
                &
                # DI filtresi (model güvenilirliği) - config.json ile uyumlu
                (dataframe["DI_values"] < 4)
                &
                # RSI 5m oversold değil
                (dataframe["rsi"] < 70)
                &
                # MTF confluence: 15m veya 1h RSI de uygun olmalı
                ((dataframe["rsi_15m"] < 65) | (dataframe["rsi_1h"] < 60))
                &
                # Volume var
                (dataframe["volume"] > 0)
            ),
            "enter_long"
        ] = 1

        # SHORT giriş - MTF RSI confluence
        dataframe.loc[
            (
                # FreqAI tahmin geçerli (do_predict == 1)
                (dataframe["do_predict"] == 1)
                &
                # FreqAI negatif tahmin (fiyat düşecek)
                (dataframe["&-target"] < exit_threshold_adj)
                &
                # DI filtresi - config.json ile uyumlu
                (dataframe["DI_values"] < 4)
                &
                # RSI 5m overbought değil
                (dataframe["rsi"] > 30)
                &
                # MTF confluence: 15m veya 1h RSI de uygun olmalı
                ((dataframe["rsi_15m"] > 35) | (dataframe["rsi_1h"] > 40))
                &
                (dataframe["volume"] > 0)
            ),
            "enter_short"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Çıkış sinyalleri - Model tahminlerine göre.
        Partial TP için ROI kullan (minimal_roi tanımı).
        """
        # News sentiment kontrol - pair'e göre cache key
        pair = metadata.get('pair', 'BTC/USDT:USDT')
        news_sentiment = {"positive": 0, "negative": 0, "neutral": 100}
        
        current_hour = int(time.time() / 3600)
        
        # Pair'e göre symbol belirle
        if pair == "BTC/USDT:USDT":
            symbol = "BTC"
        elif pair == "ETH/USDT:USDT":
            symbol = "ETH"
        else:
            symbol = None
        
        if symbol:
            cache_key = f"api_calls_{symbol}_{current_hour}"
            if cache_key in self.sentiment_cache:
                news_sentiment = self.sentiment_cache[cache_key].get("news", news_sentiment)
        
        # LONG çıkış - OR koşulu ile daha güvenli
        dataframe.loc[
            (
                # Model güçlü negatif hale geldi VEYA RSI overbought
                (dataframe["&-target"] < -0.15)
                |
                # RSI çok overbought
                (dataframe["rsi"] > 80)
            ),
            "exit_long"
        ] = 1

        # SHORT çıkış - OR koşulu ile daha güvenli
        dataframe.loc[
            (
                # Model güçlü pozitif hale geldi VEYA RSI oversold
                (dataframe["&-target"] > 0.15)
                |
                # RSI çok oversold
                (dataframe["rsi"] < 20)
            ),
            "exit_short"
        ] = 1

        return dataframe
