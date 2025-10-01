#!/usr/bin/env python3
"""
Тестирование получения логотипов акций через различные API
"""

import requests
import time

def test_clearbit_logos():
    """Тестирует получение логотипов через Clearbit"""
    print("🔍 Тестирование Clearbit Logo API...")
    
    company_domains = {
        'SBER': 'sberbank.com',
        'GAZP': 'gazprom.com', 
        'LKOH': 'lukoil.com',
        'YNDX': 'yandex.com',
        'ROSN': 'rosneft.com',
        'NVTK': 'novatek.ru',
        'TCSG': 'tinkoff.ru',
        'VTBR': 'vtb.ru',
        'GMKN': 'nornickel.com',
        'MTSS': 'mts.ru'
    }
    
    working_logos = []
    
    for ticker, domain in company_domains.items():
        try:
            logo_url = f"https://logo.clearbit.com/{domain}?size=96"
            response = requests.head(logo_url, timeout=3)
            
            if response.status_code == 200:
                print(f"✅ {ticker}: {logo_url}")
                working_logos.append((ticker, logo_url))
            else:
                print(f"❌ {ticker}: {response.status_code}")
                
            time.sleep(0.1)  # Небольшая задержка
            
        except Exception as e:
            print(f"❌ {ticker}: Ошибка - {e}")
    
    print(f"\n📊 Работающих логотипов: {len(working_logos)}/{len(company_domains)}")
    return working_logos

def test_fmp_logos():
    """Тестирует получение логотипов через Financial Modeling Prep"""
    print("\n🔍 Тестирование Financial Modeling Prep API...")
    
    international_tickers = {
        'SBER': 'SBER.ME',
        'GAZP': 'GAZP.ME',
        'LKOH': 'LKOH.ME', 
        'ROSN': 'ROSN.ME',
        'NVTK': 'NVTK.ME',
        'GMKN': 'GMKN.ME',
        'MTSS': 'MTSS.ME'
    }
    
    working_logos = []
    
    for ticker, international_ticker in international_tickers.items():
        try:
            fmp_url = f"https://financialmodelingprep.com/image-stock/{international_ticker}.png"
            response = requests.head(fmp_url, timeout=3)
            
            if response.status_code == 200:
                print(f"✅ {ticker}: {fmp_url}")
                working_logos.append((ticker, fmp_url))
            else:
                print(f"❌ {ticker}: {response.status_code}")
                
            time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ {ticker}: Ошибка - {e}")
    
    print(f"\n📊 Работающих логотипов: {len(working_logos)}/{len(international_tickers)}")
    return working_logos

def test_yahoo_finance_logos():
    """Тестирует получение логотипов через Yahoo Finance"""
    print("\n🔍 Тестирование Yahoo Finance логотипов...")
    
    # Yahoo Finance использует другой формат
    tickers = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'ROSN']
    working_logos = []
    
    for ticker in tickers:
        try:
            # Пробуем разные форматы Yahoo Finance
            yahoo_urls = [
                f"https://s.yimg.com/cv/apiv2/default/20191101/{ticker}.png",
                f"https://logo.yahoo.com/api/resource/finance/logo/{ticker}",
                f"https://s.yimg.com/rz/d/yahoo_finance_en-US_s_f_pw_141x37_finance_2x.png"
            ]
            
            for url in yahoo_urls:
                response = requests.head(url, timeout=3)
                if response.status_code == 200:
                    print(f"✅ {ticker}: {url}")
                    working_logos.append((ticker, url))
                    break
            else:
                print(f"❌ {ticker}: Логотип не найден")
                
            time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ {ticker}: Ошибка - {e}")
    
    print(f"\n📊 Работающих логотипов: {len(working_logos)}/{len(tickers)}")
    return working_logos

def test_alternative_apis():
    """Тестирует альтернативные API для логотипов"""
    print("\n🔍 Тестирование альтернативных API...")
    
    tickers = ['SBER', 'GAZP', 'LKOH']
    working_logos = []
    
    for ticker in tickers:
        try:
            # Пробуем разные API
            apis = [
                f"https://api.logo.dev/{ticker}?token=free",
                f"https://img.logo.dev/{ticker}?token=free",
                f"https://logo.dev/{ticker}.png",
                f"https://companieslogo.com/img/orig/{ticker}.png"
            ]
            
            for api_url in apis:
                try:
                    response = requests.head(api_url, timeout=3)
                    if response.status_code == 200:
                        print(f"✅ {ticker}: {api_url}")
                        working_logos.append((ticker, api_url))
                        break
                except:
                    continue
            else:
                print(f"❌ {ticker}: Логотип не найден в альтернативных API")
                
            time.sleep(0.1)
            
        except Exception as e:
            print(f"❌ {ticker}: Ошибка - {e}")
    
    print(f"\n📊 Работающих логотипов: {len(working_logos)}/{len(tickers)}")
    return working_logos

def main():
    """Запускает все тесты"""
    print("🚀 Тестирование получения логотипов акций через API")
    print("=" * 60)
    
    all_working_logos = []
    
    # Тестируем разные API
    clearbit_logos = test_clearbit_logos()
    all_working_logos.extend(clearbit_logos)
    
    fmp_logos = test_fmp_logos()
    all_working_logos.extend(fmp_logos)
    
    yahoo_logos = test_yahoo_finance_logos()
    all_working_logos.extend(yahoo_logos)
    
    alt_logos = test_alternative_apis()
    all_working_logos.extend(alt_logos)
    
    # Итоговая статистика
    print("\n" + "=" * 60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"Всего найдено работающих логотипов: {len(all_working_logos)}")
    
    if all_working_logos:
        print("\n✅ Работающие логотипы:")
        for ticker, url in all_working_logos:
            print(f"   {ticker}: {url}")
        
        print(f"\n💡 Рекомендация: Используйте Clearbit API - наиболее надежный")
        print(f"   Формат: https://logo.clearbit.com/{{domain}}?size=96")
    else:
        print("\n❌ Работающих логотипов не найдено")
        print("💡 Рекомендация: Используйте UI Avatars для генерации")

if __name__ == "__main__":
    main()
