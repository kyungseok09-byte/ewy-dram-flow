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
        
        # 최근 데이터 (첫 번째 tr)
        table = soup.select_one('table.type2')
        if not table:
            return None
            
        rows = table.select('tr')
        for row in rows:
            cells = row.select('td')
            if len(cells) >= 7:
                date = cells[0].text.strip()
                if not date or '날짜' in date:
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

def get_ewy_data():
    """EWY ETF 데이터 수집 (Yahoo Finance 우회)"""
    try:
        # 네이버 해외 주식에서 EWY 검색
        url = "https://finance.naver.com/world/sise.naver?symbol=EWY"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.content.decode('euc-kr', 'replace'), 'html.parser')
        
        # 현재가
        price_elem = soup.select_one('.no_today .no_up')
        if not price_elem:
            price_elem = soup.select_one('.no_today .no_down')
        if not price_elem:
            price_elem = soup.select_one('.no_today em')
            
        price = price_elem.text.strip() if price_elem else "N/A"
        
        # 변동률
        rate_elem = soup.select_one('.no_exday .no_up')
        if not rate_elem:
            rate_elem = soup.select_one('.no_exday .no_down')
            
        rate = rate_elem.text.strip() if rate_elem else "N/A"
        
        return {
            "price": price,
            "change_rate": rate,
            "timestamp": datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M')
        }
    except Exception as e:
        print(f"Error fetching EWY: {e}")
        return None

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
        lines.append(f"  기관: {format_number(hynix['institution'])}\n")
    else:
        lines.append("🟢 *SK하이닉스*: 데이터 수집 실패\n")
    
    # EWY ETF
    ewy = data.get("EWY")
    if ewy:
        lines.append(f"🇺🇸 *EWY (iShares MSCI Korea)* ({ewy['timestamp']})")
        lines.append(f"  가격: ${ewy['price']}")
        lines.append(f"  변동: {ewy['change_rate']}")
    else:
        lines.append("🇺🇸 *EWY*: 데이터 수집 실패")
    
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
    
    # EWY 수집
    print("수집 중: EWY")
    ewy = get_ewy_data()
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
