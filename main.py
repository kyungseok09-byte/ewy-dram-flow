#!/usr/bin/env python3
"""
DRAM/EWY 수급 리포트 (GitHub Actions 자동화)
- 잠정치(08:00 KST): 전날 마감 데이터
- 확정치(10:00 KST): 당일 장 개시 직전 최종 데이터
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
import pytz
import requests
from bs4 import BeautifulSoup

# 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATE_FILE = "state.json"

# 타겟 종목 코드
TARGETS = {
    "삼성전자": "005930",
    "SK하이닉스": "000660"
}

def load_state():
    """상태 파일 로드"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_run": None, "last_mode": None, "last_data": {}}

def save_state(state):
    """상태 파일 저장"""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_stock_trading_data(code):
    """네이버 금융에서 종목 수급 데이터 수집"""
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), 'html.parser')
        
        # 두 번째 테이블에 외국인/기관 수급 데이터가 있음
        tables = soup.select('table.type2')
        if len(tables) < 2:
            return None
            
        table = tables[1]  # 두 번째 테이블
        rows = table.select('tr')
        
        for row in rows:
            cells = row.select('td')
            if len(cells) >= 7:
                date = cells[0].text.strip()
                if not date or '날짜' in date or not date[0].isdigit():
                    continue
                    
                close_price = cells[1].text.strip().replace(',', '')
                foreign = cells[4].text.strip().replace(',', '')
                institution = cells[6].text.strip().replace(',', '')
                
                return {
                    "date": date,
                    "close": close_price,
                    "foreign": foreign,
                    "institution": institution
                }
        return None
    except Exception as e:
        print(f"Error fetching {code}: {e}")
        return None

def get_ewy_flow_data(state):
    """EWY ETF 자금 유출입 분석 (yfinance 사용)"""
    try:
        import yfinance as yf
        
        # EWY 데이터 수집
        ewy = yf.Ticker("EWY")
        info = ewy.info
        hist = ewy.history(period="5d")
        
        if hist.empty or len(hist) < 2:
            return None
        
        # 최신 데이터
        latest_date = hist.index[-1].strftime('%Y-%m-%d')
        latest_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        change_pct = ((latest_price - prev_price) / prev_price) * 100
        
        # NAV 및 발행좌수
        nav = info.get('navPrice', latest_price)
        shares_outstanding = info.get('sharesOutstanding', 0)
        
        # 전일 발행좌수 (state에서 가져오기)
        prev_shares = state.get('last_data', {}).get('EWY', {}).get('shares_outstanding', shares_outstanding)
        
        # 발행좌수 변화 계산
        shares_change = shares_outstanding - prev_shares
        
        # 순유입/유출 계산 (달러)
        flow_usd = shares_change * nav
        
        # EWY holdings 비중 로드
        holdings = load_holdings()
        samsung_weight = holdings['samsung_electronics'] / 100
        hynix_weight = holdings['sk_hynix'] / 100
        total_semi_weight = samsung_weight + hynix_weight
        
        # 반도체 섹터 유입 (달러)
        semi_flow_usd = flow_usd * total_semi_weight
        
        # 환율 가져오기
        usd_krw = get_exchange_rate()
        
        # 원화 환산
        semi_flow_krw = semi_flow_usd * usd_krw
        
        # 삼성전자 / SK하이닉스 배분
        samsung_flow_krw = semi_flow_krw * (samsung_weight / total_semi_weight)
        hynix_flow_krw = semi_flow_krw * (hynix_weight / total_semi_weight)
        
        return {
            "date": latest_date,
            "price": round(latest_price, 2),
            "change_pct": round(change_pct, 2),
            "nav": round(nav, 2),
            "shares_outstanding": shares_outstanding,
            "shares_change": shares_change,
            "flow_usd": flow_usd,
            "flow_krw": flow_usd * usd_krw,
            "semi_flow_krw": semi_flow_krw,
            "samsung_flow_krw": samsung_flow_krw,
            "hynix_flow_krw": hynix_flow_krw,
            "usd_krw": usd_krw,
            "samsung_weight": samsung_weight * 100,
            "hynix_weight": hynix_weight * 100
        }
    except Exception as e:
        print(f"Error fetching EWY flow: {e}")
        import traceback
        traceback.print_exc()
        return None

def load_holdings():
    """EWY holdings 비중 로드"""
    try:
        with open('ewy_holdings.json', 'r') as f:
            data = json.load(f)
            return data['holdings']
    except:
        # 기본값
        return {
            "samsung_electronics": 27.5,
            "sk_hynix": 3.8,
            "total_semiconductor": 31.3
        }

def get_exchange_rate():
    """원/달러 환율 가져오기 (네이버 금융)"""
    try:
        url = "https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_USDKRW"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), 'html.parser')
        
        rate_elem = soup.select_one('.no_today .no_up')
        if not rate_elem:
            rate_elem = soup.select_one('.no_today .no_down')
        if not rate_elem:
            rate_elem = soup.select_one('.no_today em')
        
        if rate_elem:
            rate_str = rate_elem.text.strip().replace(',', '')
            return float(rate_str)
        return 1350.0  # 기본값
    except:
        return 1350.0  # 기본값

def format_number(val):
    """수급 숫자 포맷팅 (억 단위)"""
    try:
        num = int(val)
        if num == 0:
            return "0"
        sign = "+" if num > 0 else ""
        return f"{sign}{num:,}주"
    except:
        return val

def send_telegram(message):
    """텔레그램 메시지 발송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("텔레그램 토큰/Chat ID 미설정")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        print("텔레그램 발송 성공")
        return True
    except Exception as e:
        print(f"텔레그램 발송 실패: {e}")
        return False

def build_report(mode, data):
    """리포트 메시지 생성"""
    kst = datetime.now(pytz.timezone('Asia/Seoul'))
    mode_label = "잠정치" if mode == "preliminary" else "확정치"
    
    lines = [
        f"📊 *[DRAM/EWY 수급 리포트 - {mode_label}]*",
        f"🕐 생성 시각: {kst.strftime('%Y-%m-%d %H:%M KST')}\n"
    ]
    
    # EWY 자금 흐름 분석
    ewy = data.get("EWY")
    if ewy and 'flow_usd' in ewy:
        flow_usd_m = ewy['flow_usd'] / 1_000_000
        flow_krw_b = ewy['flow_krw'] / 100_000_000
        semi_flow_krw_b = ewy['semi_flow_krw'] / 100_000_000
        samsung_flow_b = ewy['samsung_flow_krw'] / 100_000_000
        hynix_flow_b = ewy['hynix_flow_krw'] / 100_000_000
        
        flow_sign = "+" if flow_usd_m >= 0 else ""
        semi_sign = "+" if semi_flow_krw_b >= 0 else ""
        samsung_sign = "+" if samsung_flow_b >= 0 else ""
        hynix_sign = "+" if hynix_flow_b >= 0 else ""
        
        lines.append(f"🇺🇸 *[EWY 자금 흐름 분석]* ({ewy['date']})")
        lines.append(f"  현재가: ${ewy['price']} ({ewy['change_pct']:+.2f}%)")
        lines.append(f"  NAV: ${ewy['nav']} | 환율: {ewy['usd_krw']:.2f}원")
        lines.append(f"  발행좌수 변화: {ewy['shares_change']:+,}주")
        lines.append(f"💵 EWY 순유입: {flow_sign}${flow_usd_m:.1f}M ({flow_sign}{flow_krw_b:.0f}억원)")
        lines.append(f"🇰🇷 반도체 유입(추정): {semi_sign}{semi_flow_krw_b:.0f}억원")
        lines.append(f"  🔵 삼성전자({ewy['samsung_weight']:.1f}%): {samsung_sign}{samsung_flow_b:.0f}억원")
        lines.append(f"  🟢 하이닉스({ewy['hynix_weight']:.1f}%): {hynix_sign}{hynix_flow_b:.0f}억원\n")
    elif ewy:
        lines.append(f"🇺🇸 *EWY* ({ewy.get('date', 'N/A')})")
        lines.append(f"  가격: ${ewy.get('price', 'N/A')}")
        lines.append(f"  변동: {ewy.get('change_pct', 'N/A')}%\n")
    else:
        lines.append("🇺🇸 *EWY*: 데이터 수집 실패\n")
    
    # 삼성전자
    samsung = data.get("삼성전자")
    if samsung:
        lines.append(f"🔵 *삼성전자* ({samsung['date']})")
        lines.append(f"  종가: {samsung['close']}원")
        lines.append(f"  외국인: {format_number(samsung['foreign'])}")
        lines.append(f"  기관: {format_number(samsung['institution'])}\n")
    else:
        lines.append("🔵 *삼성전자*: 데이터 수집 실패\n")
    
    # SK하이닉스
    hynix = data.get("SK하이닉스")
    if hynix:
        lines.append(f"🟢 *SK하이닉스* ({hynix['date']})")
        lines.append(f"  종가: {hynix['close']}원")
        lines.append(f"  외국인: {format_number(hynix['foreign'])}")
        lines.append(f"  기관: {format_number(hynix['institution'])}")
    else:
        lines.append("🟢 *SK하이닉스*: 데이터 수집 실패")
    
    lines.append("\n---------------")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preliminary", "confirmed"], required=True)
    args = parser.parse_args()
    
    print(f"🚀 DRAM/EWY 리포트 시작: mode={args.mode}")
    
    # 상태 로드
    state = load_state()
    
    # 데이터 수집
    collected = {}
    for name, code in TARGETS.items():
        print(f"수집 중: {name} ({code})")
        data = get_stock_trading_data(code)
        if data:
            collected[name] = data
    
    # EWY 수집 (자금 흐름 분석)
    print("수집 중: EWY (자금 흐름)")
    ewy = get_ewy_flow_data(state)
    if ewy:
        collected["EWY"] = ewy
    
    # 리포트 생성
    report = build_report(args.mode, collected)
    print("\n" + report)
    
    # 텔레그램 발송
    send_telegram(report)
    
    # 상태 저장
    state["last_run"] = datetime.now(pytz.timezone('Asia/Seoul')).isoformat()
    state["last_mode"] = args.mode
    state["last_data"] = collected
    save_state(state)
    
    print("✅ 리포트 완료")

if __name__ == "__main__":
    main()
