#!/usr/bin/env python3
"""
블랙리스트 관리 도구
사용법:
- python3 manage_blacklist.py list          # 현재 블랙리스트 보기
- python3 manage_blacklist.py add <symbol>  # 블랙리스트에 추가
- python3 manage_blacklist.py remove <symbol> # 블랙리스트에서 제거
- python3 manage_blacklist.py clear         # 블랙리스트 초기화
"""

import json
import sys
from datetime import datetime

BLACKLIST_FILE = "blacklist.json"

def load_blacklist():
    """블랙리스트 파일 로드"""
    try:
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('blacklist', [])
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"블랙리스트 파일 읽기 오류: {e}")
        return []

def save_blacklist(blacklist):
    """블랙리스트 파일 저장"""
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": "LBank 펀딩 레이트 수집에서 제외할 티커들의 블랙리스트",
        "blacklist": blacklist
    }
    
    try:
        with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ 블랙리스트가 {BLACKLIST_FILE}에 저장되었습니다.")
    except Exception as e:
        print(f"❌ 블랙리스트 저장 오류: {e}")

def list_blacklist():
    """현재 블랙리스트 출력"""
    blacklist = load_blacklist()
    if not blacklist:
        print("📋 현재 블랙리스트가 비어있습니다.")
        return
    
    print(f"📋 현재 블랙리스트 ({len(blacklist)}개):")
    for i, symbol in enumerate(blacklist, 1):
        print(f"  {i}. {symbol}")

def add_to_blacklist(symbol):
    """블랙리스트에 심볼 추가"""
    if not symbol:
        print("❌ 심볼을 입력해주세요.")
        return
    
    symbol = symbol.lower()
    blacklist = load_blacklist()
    
    if symbol in blacklist:
        print(f"⚠️  {symbol}는 이미 블랙리스트에 있습니다.")
        return
    
    blacklist.append(symbol)
    save_blacklist(blacklist)
    print(f"✅ {symbol}가 블랙리스트에 추가되었습니다.")

def remove_from_blacklist(symbol):
    """블랙리스트에서 심볼 제거"""
    if not symbol:
        print("❌ 심볼을 입력해주세요.")
        return
    
    symbol = symbol.lower()
    blacklist = load_blacklist()
    
    if symbol not in blacklist:
        print(f"⚠️  {symbol}는 블랙리스트에 없습니다.")
        return
    
    blacklist.remove(symbol)
    save_blacklist(blacklist)
    print(f"✅ {symbol}가 블랙리스트에서 제거되었습니다.")

def clear_blacklist():
    """블랙리스트 초기화"""
    response = input("정말로 블랙리스트를 모두 지우시겠습니까? (y/N): ")
    if response.lower() == 'y':
        save_blacklist([])
        print("✅ 블랙리스트가 초기화되었습니다.")
    else:
        print("❌ 블랙리스트 초기화가 취소되었습니다.")

def show_usage():
    """사용법 출력"""
    print("""
🔧 블랙리스트 관리 도구

사용법:
  python3 manage_blacklist.py list                    # 현재 블랙리스트 보기
  python3 manage_blacklist.py add <symbol>            # 블랙리스트에 추가
  python3 manage_blacklist.py remove <symbol>         # 블랙리스트에서 제거
  python3 manage_blacklist.py clear                   # 블랙리스트 초기화

예시:
  python3 manage_blacklist.py add win_usdt
  python3 manage_blacklist.py remove btc_usdt
  python3 manage_blacklist.py list
""")

def main():
    if len(sys.argv) < 2:
        show_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == "list":
        list_blacklist()
    elif command == "add":
        if len(sys.argv) < 3:
            print("❌ 추가할 심볼을 입력해주세요.")
            return
        add_to_blacklist(sys.argv[2])
    elif command == "remove":
        if len(sys.argv) < 3:
            print("❌ 제거할 심볼을 입력해주세요.")
            return
        remove_from_blacklist(sys.argv[2])
    elif command == "clear":
        clear_blacklist()
    else:
        print(f"❌ 알 수 없는 명령어: {command}")
        show_usage()

if __name__ == "__main__":
    main() 