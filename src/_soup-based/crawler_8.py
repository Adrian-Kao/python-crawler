import re
import requests
import urllib
from bs4 import BeautifulSoup
from multiprocessing import Pool


class PTTCrawler():
    # 預設要爬的看板首頁網址
    url = 'https://www.ptt.cc/bbs/movie/index.html'
    # 當文章被刪除時，PTT 會顯示「本文已被刪除」
    NOT_EXIST = BeautifulSoup('<a>本文已被刪除</a>', 'lxml').a

    def __init__(self):
        # 初始化變數
        self.posts = list()           # 用來儲存每篇文章的資訊（標題、作者、日期、連結）
        self.ctrl = None              # 控制頁面翻頁的按鈕
        self.next_url = PTTCrawler.url  # 下一頁的網址
        self.total_pages = 0          # 記錄總頁數

    def get_recent_page(self, pages):
        """
        取得最近幾頁的文章列表。
        pages：想要爬取的頁數
        """
        for i in range(pages):
            if i == 1:  # 第二次迴圈時（即抓第二頁）才統計總頁數
                self.count_pages()
            # 取得當前頁的所有文章列表
            self.get_posts_list(self.next_url)
            # 更新下一頁的網址
            self.next_url = self.get_next_url()

        return self.posts  # 回傳所有已取得的文章資訊

    def get_next_url(self):
        """
        從頁面控制按鈕中找到「上一頁」的連結。
        """
        prev_link = self.ctrl[1]['href']  # 第二個按鈕通常是「‹ 上一頁」
        return urllib.parse.urljoin(PTTCrawler.url, prev_link)  # 拼出完整網址

    def count_pages(self):
        """
        根據當前頁面的 URL 推算目前的頁碼，並計算總頁數。
        """
        prev_page_counter = re.findall('index(\d+?).html', self.next_url)
        self.total_pages = int(prev_page_counter[0]) + 1

    def get_posts_list(self, url):
        """
        取得某一頁的所有文章列表。
        """
        response = requests.get(url)               # 送出 HTTP GET 請求
        soup = BeautifulSoup(response.text, 'lxml')  # 解析 HTML
        articles = soup.find_all('div', 'r-ent')   # 找到所有文章區塊

        # 找到頁面控制按鈕，例如「上一頁」、「下一頁」
        self.ctrl = soup.find('div', 'btn-group-paging').find_all('a', 'btn')

        # 對每篇文章進行解析
        for article in articles:
            # 有些文章可能被刪除，找不到 <a> 標籤
            title_meta = article.find('div', 'title').find('a') \
                or PTTCrawler.NOT_EXIST
            meta = article.find('div', 'meta')  # 作者、日期區塊

            post = dict()
            post['link'] = title_meta.get('href', '')        # 文章連結
            post['title'] = title_meta.string.strip()        # 標題文字
            post['date'] = meta.find('div', 'date').string   # 日期
            post['author'] = meta.find('div', 'author').string  # 作者
            self.posts.append(post)  # 加入清單


def get_articles(ptt):
    """
    使用 multiprocessing Pool 平行處理下載每篇文章內容。
    """
    post_links = [post['link'] for post in ptt.posts]  # 抽出所有連結
    contents = pool.map(get_article, post_links)       # 平行下載
    return zip(ptt.posts, contents)                    # 將文章資料與內容配對


def get_article(link):
    """
    根據文章連結取得完整內文。
    """
    url = urllib.parse.urljoin(PTTCrawler.url, link)
    response = requests.get(url)
    return response.text  # 回傳 HTML 文字內容


if __name__ == '__main__':
    pool = Pool(8)  # 建立 8 個平行處理程序
    ptt = PTTCrawler()

    import time
    start = time.time()

    # 爬取最近 5 頁的文章列表
    posts = ptt.get_recent_page(5)
    # 取得所有文章內容
    articles = get_articles(ptt)

    print('花費: %f 秒' % (time.time() - start))  # 顯示耗時

    # 印出結果摘要
    print('共%d項結果：' % len(posts))
    for post, content in articles:
        print('{0} {1: <15} {2}'.format(
            post['date'], post['author'], post['title']))
