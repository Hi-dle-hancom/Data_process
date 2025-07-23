import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
# TutorialsTeacher.com 페이지 구조에 맞지 않아 BeautifulSoup은 더 이상 사용하지 않습니다.

def crawl() -> list:
    """
    TutorialsTeacher.com Python Error Types 페이지에서 데이터를 크롤링하는 함수입니다.
    이 함수는 Selenium을 사용하여 웹 브라우저를 로드하고,
    제공된 CSS 선택자를 사용하여 테이블의 tbody를 찾고,
    그 안의 tr 행들에서 td:nth-child(1)와 td:nth-child(2) 데이터를 추출하려고 시도합니다.

    주의: 이 페이지의 메인 오류 설명 콘텐츠는 일반적인 h3/p 태그 구조를 사용합니다.
    제공된 긴 테이블 선택자로는 원하는 오류 설명 데이터를 얻지 못할 가능성이 높습니다.
    이 코드는 요청하신 CSS 선택자 로직을 그대로 구현한 것입니다.

    Returns:
        list: 추출된 데이터가 담긴 리스트입니다.
              각 딕셔너리는 'title', 'description', 'source' 키를 가집니다.
    """
    # 🔹 크롤링할 웹사이트 URL 설정
    url = "https://www.tutorialsteacher.com/python/error-types-in-python"

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

        print("TutorialsTeacher crawl 함수 호출됨 (요청된 선택자 사용)")

        # 🔹 tbody 요소 찾기
        # 사용자님이 제공한 긴 CSS 선택자를 사용하여 tbody를 찾습니다.
        tbody_selector = "#__next > div > div.container-fluid.px-0 > div > div > div > div.col-12.col-md-10.col-xl-10.ps-md-0.bg-color-light.article-body-light > div > div > div > div > div.col-md-12.pr-md-0.col-lg-12.col-xl-8 > div:nth-child(2) > article > div.table-responsive > table > tbody"
        
        try:
            tbody_element = driver.find_element(By.CSS_SELECTOR, tbody_selector)
            print(f"tbody 요소를 성공적으로 찾았습니다: {tbody_selector}")
            
            # tbody 안의 모든 행(tr)을 찾습니다.
            data_rows = tbody_element.find_elements(By.TAG_NAME, "tr")
            print(f"tbody에 있는 tr의 개수: {len(data_rows)}개")

            # 각 데이터 행을 반복하며 1열과 2열의 데이터를 추출합니다.
            for row_index, row in enumerate(data_rows):
                title_data = "N/A"
                description_data = "N/A"

                try:
                    # 1열 데이터 추출: `td:nth-child(1)`
                    col1_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)")
                    title_data = col1_element.text.strip()
                except Exception as e:
                    # print(f"경고: 행 {row_index}의 1열 데이터를 찾을 수 없습니다: {e}")
                    pass 

                try:
                    # 2열 데이터 추출: `td:nth-child(2)`
                    col2_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)")
                    description_data = col2_element.text.strip()
                except Exception as e:
                    # print(f"경고: 행 {row_index}의 2열 데이터를 찾을 수 없습니다: {e}")
                    pass
                
                # 유효한 데이터를 찾았을 경우에만 추가
                if title_data != "N/A" or description_data != "N/A":
                    extracted_data.append({
                        "title": title_data,
                        "description": description_data,
                        "source": "tutorialsteacher.com" # 소스 추가
                    })
                else:
                    print(f"경고: 행 {row_index}에서 유효한 데이터를 추출하지 못했습니다.")

        except Exception as e:
            print(f"오류: 지정된 CSS 선택자 '{tbody_selector}'로 테이블 또는 tbody를 찾을 수 없습니다. {e}")
            print("이 선택자는 TutorialsTeacher.com 페이지의 현재 HTML 구조와 맞지 않을 가능성이 높습니다.")

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
            print(f"제목: {item.get('title', 'N/A')}")
            desc = item.get('description', 'N/A')
            print(f"설명: {desc[:150]}{'...' if len(desc) > 150 else ''}")
            print(f"소스: {item.get('source', 'N/A')}")
            print("-" * 30)
    else:
        print("크롤링된 데이터가 없거나 오류가 발생했습니다. URL 또는 웹사이트 구조를 다시 확인하세요.")
