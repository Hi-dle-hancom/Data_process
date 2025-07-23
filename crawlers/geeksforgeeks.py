import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

def crawl() -> list:
    
    # 🔹 크롤링할 웹사이트 URL 설정
    url = "https://www.geeksforgeeks.org/python-exception-handling/"

    # 🔹 Chrome 드라이버 설정
    chrome_options = Options()
    # 백그라운드에서 브라우저를 실행하려면 아래 주석을 해제하세요.
    chrome_options.add_argument("--headless")
    # 자동화 제어 플래그를 숨겨 봇 감지를 어렵게 합니다.
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # 드라이버 인스턴스 생성
    driver = webdriver.Chrome(options=chrome_options)

    extracted_data = [] # 추출된 데이터를 저장할 리스트

    try:
        # 🔹 웹 페이지 열기
        print(f"URL 접속 중: {url}")
        driver.get(url)

        # 페이지 로딩을 기다립니다 (최대 10초)
        driver.implicitly_wait(10)
        
        table_element = driver.find_element(By.CSS_SELECTOR, "#post-142824 > div.text > table")

        if table_element:
            print("테이블을 성공적으로 찾았습니다.")
            # 테이블 내의 모든 행(tr)을 찾습니다.
            rows = table_element.find_elements(By.TAG_NAME, "tr")
            
            # 테이블의 길이를 세는 것은 len(rows)로 가능합니다.
            print(f"테이블의 총 행 수: {len(rows)}")

            # 첫 번째 행은 보통 헤더이므로 건너뛰고 (인덱스 1부터 시작) 실제 데이터 행을 반복합니다.
            # 사용자님이 제공한 선택자 (#post-142824 > div.text > table > tbody > tr:nth-child(1) > th)는
            # tbody 바로 아래의 tr을 가리키므로, tbody를 찾은 후 tr을 반복하는 것이 더 안정적입니다.
            tbody_element = table_element.find_element(By.TAG_NAME, "tbody")
            if tbody_element:
                data_rows = tbody_element.find_elements(By.TAG_NAME, "tr")
                for row_index, row in enumerate(data_rows):
                    # print(f"처리 중인 행 인덱스 (tbody 기준): {row_index}") # 디버깅용

                    # 1열 (예외 이름) 추출: <th> 태그 아래의 <code><span> 텍스트
                    # copy selector: #post-142824 > div.text > table > tbody > tr:nth-child(X) > th > [a] > code > span
                    # `row.find_element`는 해당 행 내에서 요소를 찾습니다.
                    name_element = None
                    try:
                        # <a> 태그가 있는 경우
                        name_element = row.find_element(By.CSS_SELECTOR, "th a code span")
                    except:
                        # <a> 태그 없이 바로 <th> 아래에 <code>가 있는 경우
                        try:
                            name_element = row.find_element(By.CSS_SELECTOR, "th code span")
                        except Exception as e:
                            print(f"경고: 예외 이름 요소를 찾을 수 없습니다. (행 인덱스 {row_index}, 에러: {e})")

                    exception_name = name_element.text.strip() if name_element else "N/A"

                    # 2열 (예외 설명) 추출: <td> 태그 아래의 <span> 텍스트
                    # copy selector: #post-142824 > div.text > table > tbody > tr:nth-child(X) > td > span
                    description_element = None
                    try:
                        description_element = row.find_element(By.CSS_SELECTOR, "td span")
                    except Exception as e:
                        print(f"경고: 예외 설명 요소를 찾을 수 없습니다. (행 인덱스 {row_index}, 에러: {e})")
                    
                    exception_description = description_element.text.strip() if description_element else "N/A"
                    
                    if exception_name != "N/A" and exception_description != "N/A":
                        extracted_data.append({
                            "title": exception_name,
                            "description": exception_description,
                            "source": "geeksforgeeks",
                        })
                    else:
                        print(f"경고: 행 {row_index}에서 유효한 데이터 추출 실패.")

            else:
                print("경고: 테이블 바디(<tbody>)를 찾을 수 없습니다. 데이터 추출에 실패할 수 있습니다.")
        else:
            print("오류: 지정된 CSS 선택자로 테이블을 찾을 수 없습니다. 웹사이트 구조를 확인해주세요.")

    except Exception as e:
        print(f"크롤링 중 치명적인 오류 발생: {e}")
        return []
    finally:
        # 🔹 드라이버 종료
        driver.quit()

    return extracted_data

# 이 __name__ == "__main__" 블록은 이 스크립트가 직접 실행될 때만 작동합니다.
# 다른 스크립트에서 이 모듈을 임포트할 때는 실행되지 않습니다.
if __name__ == "__main__":
    print("이 스크립트를 직접 실행합니다 (테스트 목적).")
    crawled_results = crawl() 

    if crawled_results:
        print("\n--- 크롤링된 데이터 ---")
        for item in crawled_results:
            print(f"이름: {item.get('Exception Name', 'N/A')}")
            desc = item.get('Description', 'N/A')
            print(f"설명: {desc[:150]}{'...' if len(desc) > 150 else ''}")
            print("-" * 30)
    else:
        print("크롤링된 데이터가 없거나 오류가 발생했습니다. URL 또는 웹사이트 구조를 다시 확인하세요.")

