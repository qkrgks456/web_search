import tkinter as tk
from tkinter import messagebox
import threading
import queue

from selenium import webdriver
from selenium.webdriver.common.by import By
import time


# Selenium 드라이버 설정을 담당하는 함수
def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")  # 브라우저 창 최대화
    options.add_argument("--headless")  # 브라우저 숨기기
    options.add_argument("--disable-gpu")  # GPU 비활성화
    options.add_argument("--no-sandbox")  # 리소스 제한 문제 방지
    driver = webdriver.Chrome(options=options)
    return driver


def update_label():
    """queue에서 데이터를 꺼내와서 UI 업데이트"""
    while not data_queue.empty():
        new_text = data_queue.get()  # queue에서 데이터 가져오기
        current_text = result_text.get()  # 기존 값 가져오기
        if current_text != "":
            result_text.set(current_text + "\n" + new_text)  # 기존 값에 새 텍스트 추가
        else:
            result_text.set(new_text)
    # 100ms 후 다시 호출 (주기적으로 queue 확인)
    root.after(100, update_label)


# 첫 번째 메인 작업: 페이지를 뒤져서 블로그 제목 찾기
def find_blog_position_main(search_query, blog_title, event):
    driver = create_driver()  # 드라이버 생성
    data_queue.put("전체탭 검색중...")
    try:
        # 네이버 사이트 접속
        driver.get("https://www.naver.com")

        # 검색어 입력
        search_box = driver.find_element(By.NAME, "query")
        search_box.send_keys(search_query)
        search_box.send_keys("\n")  # 엔터 입력

        page = 1
        while True:
            # 현재 로드된 블로그 제목 리스트 가져오기
            titles = driver.find_elements(By.CSS_SELECTOR, "a")
            for index, element in enumerate(titles):
                if element.text in blog_title:
                    data_queue.put(f"'{blog_title}'은(는) 전체탭의 {page}번째 페이지에 위치합니다.")
                    return

            # 다음 페이지로 이동
            page += 1
            if page > 10:
                break
            try:
                next_page = driver.find_elements(By.CSS_SELECTOR, ".sc_page_inner a[aria-pressed='false']")
                for index, element in enumerate(next_page):
                    if str(page) == element.text:
                        element.click()
                        break
                time.sleep(1)
            except Exception:
                data_queue.put("에러가 발생했습니다. 개발자에게 문의바랍니다.")
                break
        data_queue.put(f"전체탭에서 '{blog_title}'을(를) 찾을 수 없습니다.")

    finally:
        driver.quit()
        event.set()

# 두 번째 작업: 블로그탭에서 제목 스크롤해서 찾기
def find_blog_position_scroll(search_query, blog_title, event):
    driver = create_driver()  # 드라이버 생성
    data_queue.put("블로그탭 검색중...")
    try:
        # 네이버 사이트 접속
        driver.get("https://www.naver.com")

        # 검색어 입력
        search_box = driver.find_element(By.NAME, "query")
        search_box.send_keys(search_query)
        search_box.send_keys("\n")  # 엔터 입력

        # 블로그 탭 클릭
        driver.find_element(By.LINK_TEXT, "블로그").click()
        time.sleep(2)  # 페이지 로딩 대기

        # 최대 높이
        last_height = driver.execute_script("return document.body.scrollHeight")

        SCROLL_PAUSE_TIME = 2

        while True:
            # 현재 로드된 블로그 제목 리스트 가져오기
            blog_titles = driver.find_elements(By.CSS_SELECTOR, "a.title_link")
            for index, element in enumerate(blog_titles):
                if element.text in blog_title:
                    data_queue.put(f"'{blog_title}'은(는) 블로그탭의 {index}번째에 위치합니다.")
                    return

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE_TIME)

            # 스크롤 후 새로운 높이 확인
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:  # 더 이상 데이터가 로드되지 않으면 종료
                break
            last_height = new_height
        data_queue.put(f"블로그탭에서 '{blog_title}'을(를) 찾을 수 없습니다.")

    finally:
        driver.quit()
        event.set()


def start_search(button):

    # 결과값 메시지 초기화
    result_text.set("")

    # 버튼 비활성화
    button.config(state="disabled")

    search_query = entry_query.get()
    blog_title = entry_blog_title.get()

    if not search_query or not blog_title:
        messagebox.showwarning("입력 오류", "검색어와 블로그 제목을 모두 입력해 주세요.")
        return
    # 검색을 별도의 스레드에서 실행
    event1 = threading.Event()
    event2 = threading.Event()

    stop_flag = threading.Event()

    search_thread = threading.Thread(target=find_blog_position_main, args=(search_query, blog_title, event1))
    search_thread.start()

    search_thread2 = threading.Thread(target=find_blog_position_scroll, args=(search_query, blog_title, event2))
    search_thread2.start()

    def check():
        if stop_flag.is_set():
            # 버튼 활성화
            button.config(state="normal")
            return  # stop_flag가 True면 루프 종료
        if event1.is_set() and event2.is_set():
            stop_flag.set()
        root.after(100, check)  # 100ms마다 check 함수 반복 실행

    root.after(100, check)  # 처음에 한 번 실행


# GUI 설정
root = tk.Tk()
root.title("블로그 검색 위치 찾기")

# 검색어 입력
label_query = tk.Label(root, text="검색어")
label_query.pack(pady=5)
entry_query = tk.Entry(root, width=40)
entry_query.pack(pady=5, padx=10)

# 블로그 제목 입력
label_blog_title = tk.Label(root, text="블로그 제목")
label_blog_title.pack(pady=5)
entry_blog_title = tk.Entry(root, width=40)
entry_blog_title.pack(pady=5, padx=10)

# 결과 표시
result_text = tk.StringVar()
label_result = tk.Label(root, textvariable=result_text, width=70, height=10, relief="solid")
label_result.pack(pady=10, padx=10)

# 검색 버튼
button_search = tk.Button(root, text="검색", command=lambda: start_search(button_search))
button_search.pack(pady=5, padx=10)

# 스레드와 UI 간 통신을 위한 Queue 생성
data_queue = queue.Queue()

# 주기적으로 UI 갱신
root.after(100, update_label)

# GUI 실행
root.mainloop()
