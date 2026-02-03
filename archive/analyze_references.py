#!/usr/bin/env python3
"""
Referans Kitaplarından Strateji Bilgisi Çıkarma
Reference Books Knowledge Base Extraction
"""

import PyPDF2
import os
from pathlib import Path

os.chdir('referanslar')

# 1. ML for Algorithmic Trading - Risk Management
print("\n" + "="*70)
print("1. MACHINE LEARNING FOR ALGORITHMIC TRADING - Risk Management")
print("="*70)

with open('Machine Learning for Algorithmic Trading (2nd Edition).pdf', 'rb') as f:
    pdf = PyPDF2.PdfReader(f)
    
    # Risk Management chapters (genelde 80-160)
    for i in range(80, min(160, len(pdf.pages)), 10):
        text = pdf.pages[i].extract_text()
        if text and any(word in text.lower() for word in ['risk', 'stop', 'position', 'kelly', 'drawdown', 'leverage']):
            print(f"\n[Sayfa {i+1}]")
            print(text[:600])
            print("\n" + "-"*70)

# 2. Trading Exchanges - Market Microstructure
print("\n" + "="*70)
print("2. TRADING EXCHANGES - Market Microstructure")
print("="*70)

with open('Trading-Exchanges-Market-Microstructure-Practitioners Draft Copy.pdf', 'rb') as f:
    pdf = PyPDF2.PdfReader(f)
    
    # Liquidity, order flow sections
    for i in range(10, min(60, len(pdf.pages)), 5):
        text = pdf.pages[i].extract_text()
        if text and any(word in text.lower() for word in ['liquidity', 'order flow', 'slippage', 'spread', 'execution']):
            print(f"\n[Sayfa {i+1}]")
            print(text[:600])
            print("\n" + "-"*70)

# 3. Tsay - Time Series Analysis
print("\n" + "="*70)
print("3. TSAY - Zaman Serisi Analizi")
print("="*70)

with open('Tsay.pdf', 'rb') as f:
    pdf = PyPDF2.PdfReader(f)
    
    # Statistical models, volatility sections
    for i in range(50, min(150, len(pdf.pages)), 15):
        text = pdf.pages[i].extract_text()
        if text and any(word in text.lower() for word in ['volatility', 'var', 'garch', 'risk', 'threshold', 'trading']):
            print(f"\n[Sayfa {i+1}]")
            print(text[:600])
            print("\n" + "-"*70)

print("\n✅ Referans kitapları analiz edildi!")
