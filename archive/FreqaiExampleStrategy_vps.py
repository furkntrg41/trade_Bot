"""
FreqAI + LightGBM Futures Strategy + CoinGecko Sentiment Filter
5m timeframe, Binance Futures için optimize edilmiş.

UYARI: Bu strateji PAPER TRADING içindir.
Gerçek parayla kullanmadan önce en az 3 ay backtest + 1 ay dry-run yap.
"""
import logging
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

from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter, IStrategy


logger = logging.getLogger(__name__)


class FreqaiExampleStrategy(IStrategy):
    """
    FreqAI LightGBM Regressor Strategy
    
    Bu strateji ML modeli ile fiyat hareketini tahmin eder.
    &-target değeri: Gelecekteki fiyat değişim yüzdesi
    """
    
    # ROI: Sabit ROI yerine dinamik çıkış kullanacağız
    minimal_roi = {"0": 0.1, "240": 0.05, "1440": 0}
    
    # Stoploss: %4 - Futures'ta yüksek tutma, likidasyon riski var
    stoploss = -0.04
    
    # Trailing stoploss
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True
    
    # Timeframe
    timeframe = "5m"
    
    # Futures ayarları
    can_short = True  # Short pozisyon açabilir
    
    # FreqAI zorunlu ayarlar
    process_only_new_candles = True
    use_exit_signal = True
    
    # FreqAI prediction threshold
    # Model çıktısı bu değerin üstündeyse LONG, altındaysa SHORT
    entry_threshold = DecimalParameter(0.1, 2.0, default=0.5, space="buy", optimize=True)
    exit_threshold = DecimalParameter(-2.0, -0.1, default=-0.5, space="sell", optimize=True)
    
    # Hyperopt için
    buy_rsi = IntParameter(20, 40, default=30, space="buy", optimize=True)
    sell_rsi = IntParameter(60, 80, default=70, space="sell", optimize=True)
    
    # Sentiment cache (API çağrılarını azaltmak için)
    sentiment_cache = {}
    events_cache = {}

    def get_coingecko_events(self, coin_id: str) -> dict:
        """
        CoinGecko'dan yaklaşan etkinlikleri al (7 gün içinde).
        """
        try:
            if requests is None:
                return {"has_event": False, "impact": "neutral"}
            
            import time
            cache_key = f"{coin_id}_events_{int(time.time() / 3600)}"
            if cache_key in self.events_cache:
                return self.events_cache[cache_key]
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&community_data=true"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            
            # Etkinlik kontrolü - upcoming events var mı
            events = data.get("events", [])
            has_event = len(events) > 0
            
            if has_event:
                event_name = events[0].get("title", "Unknown")
                logger.info(f"{coin_id} upcoming event: {event_name}")
                result = {"has_event": True, "impact": "positive", "name": event_name}
            else:
                result = {"has_event": False, "impact": "neutral"}
            
            self.events_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.warning(f"Events fetch error for {coin_id}: {e}")
            return {"has_event": False, "impact": "neutral"}
    
    def get_cryptopanic_sentiment(self, coin_id: str = "BTC") -> dict:
        """
        Cryptopanic'ten son 24 saat haber sentiment'i al (Free API).
        """
        try:
            if requests is None:
                return {"positive": 0, "negative": 0, "neutral": 100}
            
            import time
            cache_key = f"{coin_id}_cryptopanic_{int(time.time() / 3600)}"
            if cache_key in self.sentiment_cache:
                return self.sentiment_cache[cache_key]
            
            # Cryptopanic free API (gözlemci modu)
            url = f"https://cryptopanic.com/api/v1/posts/?auth_token=DEMO&ticker={coin_id}"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            
            posts = data.get("results", [])
            if not posts:
                return {"positive": 0, "negative": 0, "neutral": 100}
            
            positive = sum(1 for p in posts if p.get("kind") in ["news", "positive"])
            negative = sum(1 for p in posts if p.get("kind") in ["negative"])
            neutral = len(posts) - positive - negative
            
            total = len(posts) if len(posts) > 0 else 1
            result = {
                "positive": int((positive / total) * 100),
                "negative": int((negative / total) * 100),
                "neutral": int((neutral / total) * 100)
            }
            
            logger.info(f"{coin_id} news sentiment: +{result['positive']}% -{result['negative']}%")
            self.sentiment_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.warning(f"Cryptopanic sentiment error: {e}")
            return {"positive": 0, "negative": 0, "neutral": 100}

    def get_coingecko_sentiment(self, coin_id: str) -> str:
        """
        CoinGecko API'den sentiment bilgisi al (7 günlük trend).
        coin_id: 'bitcoin' veya 'ethereum'
        """
        try:
            if requests is None:
                logger.warning("requests library not found, skipping sentiment check")
                return "neutral"
            
            # Cache check (her 60 dakikada 1 kere çağır)
            import time
            cache_key = f"{coin_id}_{int(time.time() / 3600)}"
            if cache_key in self.sentiment_cache:
                return self.sentiment_cache[cache_key]
            
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            
            # Price change 7 gün içinde
            price_change_7d = data.get("market_data", {}).get("price_change_percentage_7d", 0)
            
            if price_change_7d > 5:
                sentiment = "positive"
            elif price_change_7d < -5:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            self.sentiment_cache[cache_key] = sentiment
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
        dataframe["%-close_position"] = (
            (dataframe["close"] - dataframe["low"]) / 
            (dataframe["high"] - dataframe["low"] + 1e-10)
        )
        
        # VWAP benzeri
        dataframe["%-vwap"] = (
            (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3 * dataframe["volume"]
        ).cumsum() / dataframe["volume"].cumsum()

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
        dataframe["&-target"] = (
            dataframe["close"]
            .shift(-self.freqai_info["feature_parameters"]["label_period_candles"])
            .pct_change(self.freqai_info["feature_parameters"]["label_period_candles"], fill_method=None)
            * 100  # Yüzde olarak
        )

        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Standart indicator'lar + FreqAI prediction.
        """
        # FreqAI prediction'ı al
        dataframe = self.freqai.start(dataframe, metadata, self)
        
        # Ek indicator'lar (ML dışı karar desteği için)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Giriş sinyalleri.
        FreqAI prediction + CoinGecko sentiment + Events + News sentiment + klasik RSI filtreleme.
        """
        # Sentiments & Events kontrol
        sentiment = self.get_coingecko_sentiment("bitcoin")
        news_sentiment = self.get_cryptopanic_sentiment("BTC")
        events = self.get_coingecko_events("bitcoin")
        
        # Uyarlanabilir entry threshold (Event/News'e göre)
        entry_threshold = self.entry_threshold.value
        
        # Eğer positive events varsa, threshold'u düşür (daha kolay giriş)
        if events.get("has_event"):
            entry_threshold -= 0.2
            logger.info(f"Event boost: threshold {self.entry_threshold.value} -> {entry_threshold}")
        
        # Eğer haber sentiment çok positive ise (%70+), threshold düşür
        if news_sentiment.get("positive", 0) >= 70:
            entry_threshold -= 0.1
            logger.info(f"News boost: positive {news_sentiment['positive']}%")
        
        # Eğer haber sentiment çok negative ise (%70+), threshold yükselt
        if news_sentiment.get("negative", 0) >= 70:
            entry_threshold += 0.15
            logger.info(f"News risk: negative {news_sentiment['negative']}%")
        
        # LONG giriş
        dataframe.loc[
            (
                # FreqAI pozitif tahmin (fiyat artacak)
                (dataframe["&-target_mean"] > entry_threshold)
                &
                # DI filtresi (model güvenilirliği)
                (dataframe["DI_values"] < 1)
                &
                # RSI oversold değil (dipten alım)
                (dataframe["rsi"] < 70)
                &
                # Volume var
                (dataframe["volume"] > 0)
                &
                # YENI: Sentiment filtresi (model + market uyumu)
                (sentiment != "negative")  # Negatif sentiment'te PASS
            ),
            "enter_long"
        ] = 1

        # SHORT giriş
        dataframe.loc[
            (
                # FreqAI negatif tahmin (fiyat düşecek)
                (dataframe["&-target_mean"] < (self.exit_threshold.value - 0.1 if events.get("has_event") else self.exit_threshold.value))
                &
                # DI filtresi
                (dataframe["DI_values"] < 1)
                &
                # RSI overbought değil
                (dataframe["rsi"] > 30)
                &
                (dataframe["volume"] > 0)
            ),
            "enter_short"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Çıkış sinyalleri + Partial Take Profit + Smart Stoploss + News-driven exits.
        """
        # News sentiment kontrol - çok negatif haberse erken çıkış
        news_sentiment = self.get_cryptopanic_sentiment("BTC")
        
        # LONG çıkış - Partial Profit Taking + Model signal + News Risk
        dataframe.loc[
            (
                # Model negatif hale geldi veya RSI overbought
                ((dataframe["&-target_mean"] < 0) | (dataframe["rsi"] > self.sell_rsi.value))
                |
                # Haber sentiment çok negative ise panic çıkış
                (news_sentiment.get("negative", 0) > 75)
            ),
            "exit_long"
        ] = 1
        
        # Partial TP: +%15 kar → Tamamını sat
        dataframe.loc[(dataframe["profit"] > 0.15), "exit_long"] = 1
        
        # Partial TP: +%10 kar → %80'ini sat (exit_signal = 0.8)
        dataframe.loc[(dataframe["profit"] > 0.10) & (dataframe["profit"] <= 0.15), "exit_long"] = 0.8
        
        # Partial TP: +%5 kar → %50'sini sat (exit_signal = 0.5)
        dataframe.loc[(dataframe["profit"] > 0.05) & (dataframe["profit"] <= 0.10), "exit_long"] = 0.5
        
        # Smart Stoploss: Zamanla dynamic stoploss (Fiyat düşmeye başlamışsa daha agresif çık)
        # 1 saat içinde -1.5% kayıp → Exit (tight stop)
        dataframe.loc[(dataframe["profit"] < -0.015), "exit_long"] = 1
        
        # 2 saat+ içinde -2.5% kayıp → Exit (wider stop)
        dataframe.loc[(dataframe["profit"] < -0.025), "exit_long"] = 1

        # SHORT çıkış
        dataframe.loc[
            (
                # Model pozitif hale geldi veya RSI oversold
                ((dataframe["&-target_mean"] > 0) | (dataframe["rsi"] < self.buy_rsi.value))
                |
                # Positive news → Cover shorts
                (news_sentiment.get("positive", 0) > 70)
            ),
            "exit_short"
        ] = 1
        
        # Partial TP for SHORT: -%15 kar → Tamamını kapat
        dataframe.loc[(dataframe["profit"] > 0.15), "exit_short"] = 1
        
        # Partial TP for SHORT: -%10 kar → %80'ini kapat
        dataframe.loc[(dataframe["profit"] > 0.10) & (dataframe["profit"] <= 0.15), "exit_short"] = 0.8
        
        # Partial TP for SHORT: -%5 kar → %50'sini kapat
        dataframe.loc[(dataframe["profit"] > 0.05) & (dataframe["profit"] <= 0.10), "exit_short"] = 0.5

        return dataframe
