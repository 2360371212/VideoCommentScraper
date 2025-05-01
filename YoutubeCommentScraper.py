from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import pandas as pd
import argparse
import re


class YouTubeCommentScraper:
    def __init__(self, headless=True):
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--lang=zh-CN')
        # 创建WebDriver
        self.driver = webdriver.Chrome(options=self.options)

    def extract_video_id(self, url):
        if 'youtube.com/watch' in url:
            video_id = re.search(r'v=([^&]+)', url)
            if video_id:
                return video_id.group(1)

        # 处理短链接
        if 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1]
            if '?' in video_id:
                video_id = video_id.split('?')[0]
            return video_id
        return None

    def get_comments(self, url, max_comments):
        video_id = self.extract_video_id(url)
        if not video_id:
            print("There is no video id")
            return []

        full_url = f"https://www.youtube.com/watch?v={video_id}"
        self.driver.get(full_url)

        # wait for lording
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "ytd-comment-thread-renderer"))
            )
        except TimeoutException:
            print("Can't catch the comments, please check your internet connection")
            return []

        comments = []
        last_comment_count = 0

        print(f"Start to fetch the comments, the target quantity : {max_comments}")

        while len(comments) < max_comments:
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)

            comment_elements = self.driver.find_elements(By.TAG_NAME, "ytd-comment-thread-renderer")

            if len(comment_elements) == last_comment_count:
                wait_attempts = 0
                while len(comment_elements) == last_comment_count and wait_attempts < 3:
                    time.sleep(2)
                    self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                    comment_elements = self.driver.find_elements(By.TAG_NAME, "ytd-comment-thread-renderer")
                    wait_attempts += 1

                if len(comment_elements) == last_comment_count:
                    print(f"没有更多评论可加载，已获取 {len(comments)} 条评论")
                    break

            last_comment_count = len(comment_elements)

            for i in range(len(comments), min(len(comment_elements), max_comments)):
                comment_element = comment_elements[i]

                author = comment_element.find_element(By.XPATH, './/a[@id="author-text"]/span').text

                content = comment_element.find_element(By.XPATH,
                                                       './/yt-attributed-string[@id="content-text"]/span').text

                time_element = comment_element.find_element(By.XPATH,
                                                            './/div[@id="header-author"]/span[@id="published-time-text"]')
                comment_time = time_element.text

                try:
                    like_count_element = comment_element.find_element(By.XPATH, './/span[@id="vote-count-middle"]')
                    like_count = like_count_element.text
                    if like_count == '':
                        like_count = '0'
                except:
                    like_count = '0'

                comments.append({
                    'author': author,
                    'content': content,
                    'time': comment_time,
                    'likes': like_count
                })

                if len(comments) % 10 == 0:
                    print(f"{len(comments)} comments have been obtained")

                if len(comments) >= max_comments:
                    break

        print(f"Finally get {len(comments)} comments")
        return comments

    def save_to_csv(self, comments, filename="youtube_comments.csv"):

        if not comments:
            print("nothing to save")
            return

        df = pd.DataFrame(comments)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Save success")

    def close(self):
        if self.driver:
            self.driver.quit()


def main():
    parser = argparse.ArgumentParser(description='YouTube video comments scraper')
    parser.add_argument('--url', default='https://www.youtube.com/watch?v=80Y6R04eZRw', help='YouTube URL')
    parser.add_argument('--count', type=int, default=100, help='The number of comments to be fetched(default: 100)')
    parser.add_argument('--output', default='output/youtube_comments.csv',
                        help='Save as CSV file (default: youtube_comments.csv)')
    parser.add_argument('--show-browser', action='store_true', help='Show the browser(default true)')

    args = parser.parse_args()

    try:
        scraper = YouTubeCommentScraper(headless=args.show_browser)
        comments = scraper.get_comments(args.url, args.count)
        scraper.save_to_csv(comments, args.output)
    finally:
        if 'scraper' in locals():
            scraper.close()


if __name__ == "__main__":
    main()
