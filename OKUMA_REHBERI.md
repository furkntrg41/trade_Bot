# 📖 OKUMA REHBERİ - Sistemin Derinlemesine Anlaşılması

## Merhaba! 👋

Sistem çok karmaşık görünüyor ama aslında basit bir mantığa dayalı. Bu dosya sana hangi kaynağı ne zaman okumanız gerektiğini gösterir.

---

## 🎯 HIZLI BAŞLANGIÇ (5 dakika)

Eğer sadece sistemin çalışıp çalışmadığını görmek istersen:

```bash
# 1. SSH'ye bağlan
ssh -i ~/.ssh/id_rsa_hetzner root@91.98.133.146

# 2. Bot çalışıyor mu kontrol et
docker ps | grep freqtrade_bot

# 3. Sağlıklı mı kontrol et
curl http://localhost:8080/api/v1/ping
```

**Başarılı?** → Sistem çalışıyor! ✅

---

## 📚 SEVIYELI OKUMA REHBERI

### LEVEL 1: BAŞLANGICI (Bu konuları ÖNCE oku)

**Sürü:** 15 dakika

1. **[SISTEM_MIMARISI_DETAYLICA.md](SISTEM_MIMARISI_DETAYLICA.md)** - Bölüm 1-2
   - Ne olduğu: Docker container ve veri akışı katmanları
   - Neden önemli: Sistem nasıl organize edilmiş?
   - Çıkardığın sonuç: System architecture temeli

2. **[SISTEM_MIMARISI_DETAYLICA.md](SISTEM_MIMARISI_DETAYLICA.md)** - Bölüm 7
   - Ne olduğu: Trade akışı (Başlama → Izleme → Kapatma)
   - Neden önemli: Tüm işlem ne şekilde gerçekleşiyor?
   - Çıkardığın sonuç: Bir trade nasıl açılıyor?

---

### LEVEL 2: ARA SEVİYE (Sistem nasıl çalışıyor?)

**Sürü:** 30 dakika

3. **[SISTEM_MIMARISI_DETAYLICA.md](SISTEM_MIMARISI_DETAYLICA.md)** - Bölüm 3-4
   - Bölüm 3: Veri akışı ve depolama
     - Nereye veriler gidiyor?
     - Nasıl kalıcı hale getiriliyor?
   - Bölüm 4: Crash recovery
     - Bot kapanırsa ne oluyor?
     - Nasıl otomatik kurtarılıyor?

4. **[PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)**
   - Docker yapısı derinlemesine
   - Health checks nasıl çalışıyor?
   - Log rotation neden önemli?

---

### LEVEL 3: İLERİ SEVİYE (Derinlemesine teknik anlama)

**Sürü:** 45 dakika

5. **[SISTEM_MIMARISI_DETAYLICA.md](SISTEM_MIMARISI_DETAYLICA.md)** - Bölüm 5-6
   - Bölüm 5: Yapılandırma dosyaları detayı
     - config.json ne yapıyor?
     - pairs_config.json hassasiyeti?
     - docker-compose.production.yml kritik ayarları?
   - Bölüm 6: Monitoring yapıları
     - REST API endpoints
     - Docker logs analiz
     - Recovery report yorumlama

6. **[COMMANDS_REFERENCE.md](COMMANDS_REFERENCE.md)**
   - Tüm terminal komutları
   - Çıktı örnekleri
   - Hata çözme adımları

---

### LEVEL 4: MASTER SEVİYE (Operasyonel uzmanlaşma)

**Sürü:** Sürekli referans**

7. **[SISTEM_MIMARISI_DETAYLICA.md](SISTEM_MIMARISI_DETAYLICA.md)** - Bölüm 8-9
   - Günlük kontrol listesi
   - Önemli kavramlar açıklama
   - Teknik terimlerin Türkçe tanımı

8. **[DEPLOYMENT_READY.md](DEPLOYMENT_READY.md)**
   - İşletim checklist
   - Sorun giderme rehberi
   - Best practices

---

## 🔍 AMAÇ BAZLI REHBERLİ OKUMA

### Amaç: "Bot çalışıyor mu görmek istiyorum"
```
→ git LEVEL 1 adımı 1 (SISTEM_MIMARISI_DETAYLICA.md, Bölüm 1-2)
→ Çalış 5 dakika
→ docker ps komutu çalıştır
✅ Tamam!
```

### Amaç: "Bot nasıl trade açıyor anlamak istiyorum"
```
→ git LEVEL 1 adımı 2 (SISTEM_MIMARISI_DETAYLICA.md, Bölüm 7)
→ Çalış 10 dakika, akış diyagramına bak
→ docker logs -f komutu çalıştır, gerçek logs izle
✅ Tamam!
```

### Amaç: "Bot kapanırsa ne olur anlamak istiyorum"
```
→ git LEVEL 2 adımı 3 (SISTEM_MIMARISI_DETAYLICA.md, Bölüm 4)
→ Çalış 15 dakika, recovery flow diyagramına bak
→ recovery_report.json dosyasına bak
✅ Tamam!
```

### Amaç: "Hata var, çözmek istiyorum"
```
→ git LEVEL 2 adımı 4 (PRODUCTION_DEPLOYMENT.md, troubleshooting)
→ git LEVEL 3 adımı 6 (COMMANDS_REFERENCE.md, debugging)
→ Komutu çalıştır, çıktıyı kontrol et
✅ Tamam!
```

### Amaç: "Günlük sistemi izlemek istiyorum"
```
→ git LEVEL 4 adımı 7 (SISTEM_MIMARISI_DETAYLICA.md, Bölüm 8)
→ Kontrol listesi adımlarını izle
→ docker stats, logs, API çalıştır
✅ Tamam!
```

---

## 📋 DOKÜMANTASYON HARİTASI

```
freqtrade_bot/
├── SISTEM_MIMARISI_DETAYLICA.md          ← 👈 BAŞLANGICI NOKTASI
│   ├─ Bölüm 1-2: Mimari & Katmanlar
│   ├─ Bölüm 3: Veri akışı
│   ├─ Bölüm 4: Crash recovery
│   ├─ Bölüm 5: Yapılandırma
│   ├─ Bölüm 6: Monitoring
│   ├─ Bölüm 7: Trade akışı
│   ├─ Bölüm 8: Kontrol listesi
│   └─ Bölüm 9: Kullanışlı komutlar
│
├── PRODUCTION_DEPLOYMENT.md               ← Docker derinlemesine
│   ├─ Dockerfile açıklama
│   ├─ docker-compose ayarları
│   ├─ Health checks
│   ├─ Log management
│   └─ Troubleshooting
│
├── COMMANDS_REFERENCE.md                  ← Terminal komutları
│   ├─ SSH bağlantı
│   ├─ Docker komutları
│   ├─ Monitoring komutları
│   ├─ Debugging komutları
│   └─ Emergency işlemleri
│
├── DEPLOYMENT_READY.md                    ← Hızlı referans
│   ├─ Checklist
│   ├─ Sistem durumu
│   └─ Harita
│
└── OKUMA_REHBERI.md                       ← Bu dosya (seni buraya çeken)
```

---

## ⏱️ ZAMANLI ÖĞRENİM PLANI

### GÜN 1 (Pazartesi) - TEMEL

**Toplam:** 1 saat

- [ ] 08:00 - SISTEM_MIMARISI_DETAYLICA.md, Bölüm 1-2 (15 min)
- [ ] 08:15 - docker ps komutu çalıştır (5 min)
- [ ] 08:20 - SISTEM_MIMARISI_DETAYLICA.md, Bölüm 7 oku (20 min)
- [ ] 08:40 - docker logs -f komutu çalıştır, logs izle (10 min)
- [ ] 08:50 - DEPLOYMENT_READY.md oku (10 min)

**Hedef:** Sistem nedir, nasıl çalışır?

---

### GÜN 2 (Salı) - ÖRN OPERASYON

**Toplam:** 1.5 saat

- [ ] 09:00 - SISTEM_MIMARISI_DETAYLICA.md, Bölüm 3 oku (15 min)
- [ ] 09:15 - SISTEM_MIMARISI_DETAYLICA.md, Bölüm 4 oku (20 min)
- [ ] 09:35 - recovery_report.json dosyasına bak (10 min)
- [ ] 09:45 - PRODUCTION_DEPLOYMENT.md oku (30 min)
- [ ] 10:15 - Sistem kontrol listesi (SISTEM_MIMARISI_DETAYLICA.md, Bölüm 8) (15 min)

**Hedef:** Veri nasıl tutulur, crash recovery nasıl çalışır?

---

### GÜN 3 (Çarşamba) - MONITORING

**Toplam:** 1 saat

- [ ] 10:00 - SISTEM_MIMARISI_DETAYLICA.md, Bölüm 5-6 oku (25 min)
- [ ] 10:25 - COMMANDS_REFERENCE.md oku (20 min)
- [ ] 10:45 - Tüm komutları örnekle (15 min)

**Hedef:** Sistemi nasıl izlerim, hata nasıl çözerim?

---

## 🎓 KEYFİ DERINLEMESINE ARAŞTIRMALAR

Eğer çok ilginizi çekerse:

### Cointegration Matematiği
**Dosya:** SISTEM_MIMARISI_DETAYLICA.md, Bölüm 9 - "Önemli Kavramlar"
- ADF testi neden gerekli?
- Z-Score nasıl hesaplanıyor?
- Stationary (durağan) nedir?

### Execution Engine Güvenliği
**Dosya:** SISTEM_MIMARISI_DETAYLICA.md, Bölüm 9
- Idempotency neden önemli?
- Ghost order nedir?
- Dynamic hedging nasıl çalışıyor?

### Machine Learning Modeli
Quant arbitrage modüllerin içerisinde:
- `quant_arbitrage/signal_generator.py` - Z-Score hesaplaması
- `quant_arbitrage/execution_engine.py` - Order execution
- `quant_arbitrage/cointegration_analyzer.py` - Cointegration test

---

## 🚨 SORUN GİDERME REHBERI

**Sorundur:** Bot kapandı, ne yapmalıyım?

```
1. docker ps komutu çalıştır (status görmek için)
2. docker logs freqtrade_bot --tail 50 (son 50 satırı görüşt)
3. recovery_report.json'a bak (reconciliation sonucu)
4. Bot kendiliğinden başlayacak (unless-stopped policy)
5. Eğer başlamazsa → PRODUCTION_DEPLOYMENT.md, troubleshooting
```

**Sorundur:** Logs'ta [SAFETY] uyarısı var

```
1. docker logs -f freqtrade_bot | grep "\[SAFETY\]" (alerts filtrele)
2. Hangi pair'de oldu? (PAIR_001 mi, PAIR_002 mi?)
3. Neden triggered? (stop-loss mu, rollback mi?)
4. SYSTEM_MIMARISI_DETAYLICA.md, Bölüm 2 (AŞAMA 5: Mean Reversion Kontrolü) oku
5. curl http://localhost:8080/api/v1/trades (işlemler kontrol et)
```

**Sorundur:** API yanıt vermiyor

```
1. docker ps komutu çalıştır (container alive mi?)
2. docker stats freqtrade_bot (CPU/memory high mi?)
3. docker logs freqtrade_bot (error var mı?)
4. docker restart freqtrade_bot (container yeniden başlat)
5. Hala yoksa → PRODUCTION_DEPLOYMENT.md, advanced troubleshooting
```

---

## 📞 YAPACAK SORULAR

Okurken çıkan soruları burada yanıtla:

- [ ] **Soru:** Cointegration nedir?
  **Cevap:** SISTEM_MIMARISI_DETAYLICA.md, Bölüm 9 - "COINTEGRATION"

- [ ] **Soru:** Z-Score nasıl trigger'ı tetikler?
  **Cevap:** SISTEM_MIMARISI_DETAYLICA.md, Bölüm 2 - "AŞAMA 2"

- [ ] **Soru:** Docker container neden `unless-stopped`?
  **Cevap:** SISTEM_MIMARISI_DETAYLICA.md, Bölüm 5C - docker-compose açıklaması

- [ ] **Soru:** Bot kapanırsa veriler kaybolur mu?
  **Cevap:** SISTEM_MIMARISI_DETAYLICA.md, Bölüm 4 - "Crash Recovery"

- [ ] **Soru:** Ne kadar profit beklesen?
  **Cevap:** SISTEM_MIMARISI_DETAYLICA.md, Bölüm 7 - "TİCARET DÜZENI ÖZET"

---

## 🎯 SONUÇ

Sistemi anlamak için sıra önemli:

1. **İlk olarak:** Architecture bak (Bölüm 1-2)
2. **Sonra:** Trade flow bak (Bölüm 7)
3. **Sonra:** Crash recovery bak (Bölüm 4)
4. **Sonra:** Monitoring yapıları bak (Bölüm 6)
5. **Son olarak:** Teknik detaylar bak (Bölüm 5, 8, 9)

Her bölümü bitirdikten sonra:
```bash
# Gerçek sistemde test et
docker ps
docker logs -f freqtrade_bot
curl http://localhost:8080/api/v1/ping
```

Böyle yapsan 3 gün içinde expert olursun! 🎉

---

**Son güncelleme:** 2026-02-02
**Versiyon:** 1.0
**Dil:** Türkçe

Başarılar! 🚀
