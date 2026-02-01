# FreqAI + LightGBM için Custom Image
# Neden develop? -> stable branch'te datasieve, yeni feature'lar yok.
# Neden freqaiimage? -> freqtrade base image'ı ML dependencies içermiyor.

FROM freqtradeorg/freqtrade:develop_freqai

# DNS: docker-compose.yml'de dns: 8.8.8.8 olarak tanımlandı.
# Build-time'da /etc/resolv.conf read-only, runtime'da docker-compose halleder.

# LightGBM için ek optimizasyon - OpenMP thread limiti
# VPS: 2 vCPU (Hetzner CPX22)
ENV OMP_NUM_THREADS=2
ENV NUMEXPR_MAX_THREADS=2

WORKDIR /freqtrade
