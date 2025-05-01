from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import pandas as pd
import argparse
import re


class YouTubeSubtitlesScraper:
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

    def get_subtitles(self, url):
        video_id = self.extract_video_id(url)
        if not video_id:
            print("There is no video id")
            return []

        full_url = f"https://www.youtube.com/watch?v={video_id}"
        self.driver.get(full_url)

        # wait for lording
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, './/div[@id="description"]'))
            )
        except TimeoutException:
            print("Can't catch the subtitles, please check your internet connection")
            return []
        try:
            more_button = self.driver.find_element(By.XPATH, './/tp-yt-paper-button[@id="expand"]')
            more_button.click()

            time.sleep(1)

            get_text_button = self.driver.find_element(By.XPATH, '//button[.//span[text()="内容转文字"]]')
            get_text_button.click()

            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "ytd-transcript-segment-renderer"))
                )
            except TimeoutException:
                print("Can't catch the transcript, please check your internet connection")
                return []

            transcript_elements = self.driver.find_elements(By.TAG_NAME, "ytd-transcript-segment-renderer")

            transcripts = []

            for i in range(0, len(transcript_elements)):
                transcript_element = transcript_elements[i]
                timestamp = transcript_element.find_element(By.XPATH,
                                                            './/div[@class="segment-timestamp style-scope ytd-transcript-segment-renderer"]').text
                text = transcript_element.find_element(By.XPATH, './/yt-formatted-string').text
                transcripts.append({
                    'timestamp': timestamp,
                    'text': text
                })
            print(f"Finally get {len(transcripts)} transcripts")
            return transcripts
        except NoSuchElementException:
            print("Can't get the transcript, maybe it is not available")
            return []

    def save_to_csv(self, transcripts, filename="youtube_subtitles.csv"):

        if not transcripts:
            print("nothing to save")
            return

        df = pd.DataFrame(transcripts)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Save success")

    def close(self):
        if self.driver:
            self.driver.quit()


def main():
    parser = argparse.ArgumentParser(description='YouTube Subtitles Scraper')
    parser.add_argument('--url', default='https://www.youtube.com/watch?v=80Y6R04eZRw', help='YouTube URL')
    parser.add_argument('--output', default='output/youtube_subtitles.csv',
                        help='Save as CSV file (default: youtube_subtitles.csv)')
    parser.add_argument('--show-browser', action='store_true', help='Show the browser(default true)')

    args = parser.parse_args()

    try:
        scraper = YouTubeSubtitlesScraper(headless=args.show_browser)
        transcripts = scraper.get_subtitles(args.url)
        scraper.save_to_csv(transcripts, args.output)
    finally:
        if 'scraper' in locals():
            scraper.close()


if __name__ == '__main__':
    main()
