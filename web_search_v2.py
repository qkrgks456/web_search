import tkinter as tk
from tkinter import messagebox
import threading
import queue
from selenium import webdriver
from selenium.webdriver.common.by import By
import time


class BlogSearcher:
    def __init__(self):
        self.driver = None
        self.data_queue = queue.Queue()

    def create_driver(self):
        """WebDriver 생성 및 반환."""
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        return webdriver.Chrome(options=options)

    def close_driver(self, driver):
        """WebDriver 종료."""
        if driver:
            driver.quit()

    def search_blog_position(self, search_query, blog_title, event, search_type="main"):
        """블로그 제목의 위치를 검색하는 함수 (main 또는 scroll 방식)."""
        driver = self.create_driver()
        self.data_queue.put(f"{'전체탭' if search_type == 'main' else '블로그탭'} 검색중...")
        try:
            driver.get("https://www.naver.com")
            search_box = driver.find_element(By.NAME, "query")
            search_box.send_keys(search_query)
            search_box.send_keys("\n")

            if search_type == "main":
                self._search_main_tab(driver, blog_title)
            elif search_type == "scroll":
                self._search_blog_tab(driver, blog_title)
        finally:
            self.close_driver(driver)
            event.set()

    def _search_main_tab(self, driver, blog_title):
        """전체탭에서 블로그 제목 찾기."""
        page = 1
        while page <= 10:
            titles = driver.find_elements(By.CSS_SELECTOR, "a")
            for element in titles:
                if blog_title in element.text:
                    self.data_queue.put(f"'{blog_title}'은(는) 전체탭의 {page}번째 페이지에 위치합니다.")
                    return
            page += 1
            try:
                next_page = driver.find_elements(By.CSS_SELECTOR, ".sc_page_inner a[aria-pressed='false']")
                for element in next_page:
                    if str(page) == element.text:
                        element.click()
                        time.sleep(1)
                        break
            except Exception:
                self.data_queue.put("에러가 발생했습니다. 개발자에게 문의바랍니다.")
                break
        self.data_queue.put(f"전체탭에서 '{blog_title}'을(를) 찾을 수 없습니다.")

    def _search_blog_tab(self, driver, blog_title):
        """블로그탭에서 블로그 제목 찾기 (스크롤 방식)."""
        driver.find_element(By.LINK_TEXT, "블로그").click()
        time.sleep(2)
        last_height = driver.execute_script("return document.body.scrollHeight")
        SCROLL_PAUSE_TIME = 2

        while True:
            blog_titles = driver.find_elements(By.CSS_SELECTOR, "a.title_link")
            for index, element in enumerate(blog_titles):
                if blog_title in element.text:
                    self.data_queue.put(f"'{blog_title}'은(는) 블로그탭의 {index + 1}번째에 위치합니다.")
                    return
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SCROLL_PAUSE_TIME)

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        self.data_queue.put(f"블로그탭에서 '{blog_title}'을(를) 찾을 수 없습니다.")


class BlogSearchApp:
    def __init__(self, root):
        self.button_search = None
        self.entry_blog_title = None
        self.entry_query = None
        self.root = root
        self.root.title("블로그 검색 위치 찾기")
        self.searcher = BlogSearcher()
        self.result_text = tk.StringVar()
        self.create_widgets()

    def create_widgets(self):
        """GUI 위젯 생성."""
        label_query = tk.Label(self.root, text="검색어")
        label_query.pack(pady=5)
        self.entry_query = tk.Entry(self.root, width=40)
        self.entry_query.pack(pady=5, padx=10)

        label_blog_title = tk.Label(self.root, text="블로그 제목")
        label_blog_title.pack(pady=5)
        self.entry_blog_title = tk.Entry(self.root, width=40)
        self.entry_blog_title.pack(pady=5, padx=10)

        label_result = tk.Label(self.root, textvariable=self.result_text, width=70, height=10, relief="solid")
        label_result.pack(pady=10, padx=10)

        self.button_search = tk.Button(self.root, text="검색", command=self.start_search)
        self.button_search.pack(pady=5, padx=10)

    def update_label(self):
        """큐에서 가져온 데이터를 UI에 반영."""
        while not self.searcher.data_queue.empty():
            new_text = self.searcher.data_queue.get()
            current_text = self.result_text.get()
            self.result_text.set(f"{current_text}\n{new_text}" if current_text else new_text)
        self.root.after(100, self.update_label)

    def start_search(self):
        """검색을 시작하는 함수."""
        self.result_text.set("")
        search_query = self.entry_query.get()
        blog_title = self.entry_blog_title.get()

        if not search_query or not blog_title:
            messagebox.showwarning("입력 오류", "검색어와 블로그 제목을 모두 입력해 주세요.")
            return

        # 검색 버튼 비활성화
        self.button_search.config(state=tk.DISABLED)

        event1 = threading.Event()
        event2 = threading.Event()

        search_thread1 = threading.Thread(target=self.searcher.search_blog_position, args=(search_query, blog_title, event1, "main"))
        search_thread2 = threading.Thread(target=self.searcher.search_blog_position, args=(search_query, blog_title, event2, "scroll"))

        search_thread1.start()
        search_thread2.start()

        # 스레드 상태를 확인하고 버튼을 활성화하는 함수
        def check_threads():
            if event1.is_set() and event2.is_set():
                # 검색 완료 후 버튼 활성화
                self.button_search.config(state=tk.NORMAL)
            else:
                self.root.after(100, check_threads)  # 100ms 후 다시 실행

        check_threads()  # 한 번만 실행
        self.root.after(100, self.update_label)  # UI 갱신 시작

if __name__ == "__main__":
    root = tk.Tk()
    app = BlogSearchApp(root)
    root.mainloop()
