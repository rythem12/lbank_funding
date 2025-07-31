import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging

class LBankFundingTest:
    def __init__(self):
        self.funding_file = "lbank_funding.json"
        self.tickers_file = "lbank_tickers.json"
        self.log_file = "lbank_funding.log"
        self.driver = None
        self.driver_lock = threading.Lock()
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()  # 콘솔 출력만 사용
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_selenium(self):
        """Setup Selenium WebDriver"""
        try:
            options = Options()
            options.add_argument('--headless')  # 헤드리스 모드
            
            # Firefox 설정
            service = Service(executable_path='/usr/local/bin/geckodriver')
            driver = webdriver.Firefox(service=service, options=options)
            self.logger.info(f"Firefox WebDriver successfully initialized for thread {threading.get_ident()}")
            return driver
        except Exception as e:
            self.logger.error(f"Error setting up Firefox WebDriver: {e}")
            raise

    def read_tickers(self) -> list:
        """Read tickers from JSON file"""
        try:
            with open(self.tickers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 티커 데이터에서 symbol만 추출
                tickers = [item['symbol'] for item in data.get('tickers', [])]
                self.logger.info(f"Read {len(tickers)} tickers from {self.tickers_file}")
                return tickers
        except Exception as e:
            self.logger.error(f"Error reading tickers: {e}")
            return []

    def get_funding_rate_from_web(self, symbol: str) -> dict:
        """Get funding rate from LBank website using Selenium and BeautifulSoup"""
        driver = None
        try:
            # 각 스레드마다 독립적인 드라이버 생성
            driver = self.setup_selenium()

            # symbol 형식 변환 (예: btc_usdt -> btcusdt)
            symbol_converted = symbol.replace('_', '').lower()
            url = f"https://www.lbank.com/futures/{symbol_converted}"
            self.logger.info(f"Fetching funding rate for {symbol} from {url}")
            
            self.logger.info("Loading page...")
            driver.get(url)
            
            # JavaScript 실행 완료까지 대기
            self.logger.info("Waiting for JavaScript to complete...")
            time.sleep(20)  # JavaScript 실행을 위한 충분한 대기 시간
            
            # 페이지가 완전히 로드되었는지 확인
            self.logger.info("Checking if page is fully loaded...")
            time.sleep(5)  # 추가 대기 시간
            
            # HTML 가져오기
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # funding rate와 countdown 찾기
            self.logger.info("Searching for funding rate and countdown in HTML...")
            
            # funding-rate 클래스를 가진 div 찾기
            funding_divs = soup.find_all('div', class_='funding-rate')
            self.logger.info(f"Found {len(funding_divs)} divs with funding-rate class")
            
            for div in funding_divs:
                # funding rate 찾기
                funding_rate_span = div.find('span', class_='warning_color')
                if funding_rate_span and '%' in funding_rate_span.text:
                    funding_rate = funding_rate_span.text.strip()
                    self.logger.info(f"Found funding rate: {funding_rate}")
                    
                    # countdown 찾기
                    countdown_span = div.find('span', class_='countdown')
                    if countdown_span:
                        countdown = countdown_span.text.strip()
                        self.logger.info(f"Found countdown: {countdown}")
                    else:
                        # countdown 클래스가 없는 경우, funding rate 다음 span 찾기
                        next_span = funding_rate_span.find_next('span')
                        if next_span:
                            countdown = next_span.text.strip()
                            self.logger.info(f"Found countdown (next span): {countdown}")
                        else:
                            countdown = "Not found"
                            self.logger.info("Countdown not found")
                    
                    return {
                        "symbol": symbol,
                        "funding_rate": funding_rate,
                        "countdown": countdown,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
            
            # funding-rate div에서 찾지 못한 경우, warning_color span에서 다시 시도
            funding_spans = soup.find_all('span', class_='warning_color')
            self.logger.info(f"Found {len(funding_spans)} spans with warning_color class")
            
            for span in funding_spans:
                if '%' in span.text:
                    funding_rate = span.text.strip()
                    self.logger.info(f"Found funding rate: {funding_rate}")
                    
                    # 다음 span 찾기 (countdown)
                    next_span = span.find_next('span')
                    if next_span:
                        countdown = next_span.text.strip()
                        self.logger.info(f"Found countdown: {countdown}")
                    else:
                        countdown = "Not found"
                        self.logger.info("Countdown not found")
                    
                    return {
                        "symbol": symbol,
                        "funding_rate": funding_rate,
                        "countdown": countdown,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
            
            self.logger.info("Could not find funding rate in HTML")
            return None
                
        except Exception as e:
            self.logger.error(f"[LBank] Error getting funding rate from web for {symbol}: {e}")
            return None
            
        finally:
            if driver:
                driver.quit()

    def save_funding_rates(self, funding_data: list):
        """Save funding rate information to JSON file"""
        try:
            data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "funding_rates": funding_data
            }
            
            with open(self.funding_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved funding rates to {self.funding_file}")
            self.logger.info(f"Total funding rates saved: {len(funding_data)}")
            
        except Exception as e:
            self.logger.error(f"Error saving funding rates: {e}")

    def process_ticker_batch(self, tickers: list, batch_num: int) -> list:
        """Process a batch of tickers in parallel"""
        start_time = datetime.now()
        self.logger.info(f"Starting batch {batch_num} with {len(tickers)} tickers at {start_time}")
        
        funding_rates = []
        
        with ThreadPoolExecutor(max_workers=20) as executor:  # 스레드 수를 20으로 증가
            # 각 티커에 대해 병렬로 펀딩비 가져오기
            future_to_ticker = {executor.submit(self.get_funding_rate_from_web, ticker): ticker for ticker in tickers}
            
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    funding_data = future.result()
                    if funding_data:
                        funding_rates.append(funding_data)
                except Exception as e:
                    self.logger.error(f"Error processing ticker {ticker}: {e}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        self.logger.info(f"Completed batch {batch_num} in {duration:.2f} seconds at {end_time}")
        self.logger.info(f"Successfully processed {len(funding_rates)}/{len(tickers)} tickers in batch {batch_num}")
        
        return funding_rates

    def fetch_all_funding_rates(self):
        """Fetch funding rates for all tickers"""
        self.logger.info("Starting to fetch funding rates for all tickers...")
        
        try:
            # 티커 읽기
            tickers = self.read_tickers()
            if not tickers:
                self.logger.error("No tickers found")
                return
            
            all_funding_rates = []
            batch_size = 100
            
            # 티커를 배치로 나누어 처리
            for i in range(0, len(tickers), batch_size):
                batch = tickers[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                # 배치 처리
                funding_rates = self.process_ticker_batch(batch, batch_num)
                all_funding_rates.extend(funding_rates)
                
                # 배치 간 대기
                if i + batch_size < len(tickers):
                    self.logger.info("Waiting before next batch...")
                    time.sleep(5)  # 5초 대기
            
            # 결과 저장
            if all_funding_rates:
                self.save_funding_rates(all_funding_rates)
            else:
                self.logger.error("No funding rates were fetched")
                
        except Exception as e:
            self.logger.error(f"Error in fetching funding rates: {e}")
            
        finally:
            self.logger.info("Process completed")

def main():
    test = LBankFundingTest()
    test.fetch_all_funding_rates()

if __name__ == "__main__":
    main() 