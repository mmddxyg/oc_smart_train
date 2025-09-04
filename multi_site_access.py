import threading
import requests
import time
import sys
import os
import logging
import tkinter as tk
from tkinter import simpledialog, messagebox
from concurrent.futures import ThreadPoolExecutor
import random
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('access_log.txt'),
        logging.StreamHandler(sys.stdout)
    ]
)

# User-Agent 列表，随机选择模拟浏览器
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/89.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36'
]

# 目标网站及其域名列表（移除无效域名）
WEBSITES = {
    "TikTok": [
        "https://www.tiktok.com",
        "https://m.tiktok.com",
        "https://v.tiktok.com"
    ],
    "YouTube": [
        "https://www.youtube.com",
        "https://m.youtube.com",
        "https://youtube.googleapis.com"
    ],
    "Netflix": [
        "https://www.netflix.com",
        "https://account.netflix.com",
        "https://media.netflix.com"
    ],
    "Reddit": [
        "https://www.reddit.com",
        "https://m.reddit.com",
        "https://oauth.reddit.com"
    ],
    "X": [
        "https://www.x.com",
        "https://api.x.com",
        "https://mobile.x.com"
    ],
    "Instagram": [
        "https://www.instagram.com",
        "https://i.instagram.com",
        "https://api.instagram.com"
    ],
    "Facebook": [
        "https://www.facebook.com",
        "https://m.facebook.com",
        "https://graph.facebook.com"
    ],
    "Twitch": [
        "https://www.twitch.tv",
        "https://m.twitch.tv",
        "https://api.twitch.tv"
    ],
    "Hulu": [
        "https://www.hulu.com",
        "https://secure.hulu.com",
        "https://play.hulu.com"
    ],
    "BBC": [
        "https://www.bbc.com",
        "https://www.bbc.co.uk",
        "https://news.bbc.co.uk"
    ],
    "CNN": [
        "https://www.cnn.com",
        "https://edition.cnn.com",
        "https://m.cnn.com"
    ],
    "Amazon": [
        "https://www.amazon.com",
        "https://aws.amazon.com",
        "https://smile.amazon.com"
    ],
    "eBay": [
        "https://www.ebay.com",
        "https://m.ebay.com",
        "https://signin.ebay.com"
    ],
    "Google": [
        "https://www.google.com",
        "https://mail.google.com",
        "https://drive.google.com"
    ],
    "Dropbox": [
        "https://www.dropbox.com",
        "https://www.dropboxstatic.com"
    ]
}

# 全局计数器
request_counter = 0
counter_lock = threading.Lock()

def visit_url(site_name, urls, session):
    """访问单个网站的随机 URL"""
    global request_counter
    while True:
        try:
            url = random.choice(urls)  # 随机选择一个域名
            request_url = f"{url}{'?num=' if '?' not in url else '&num='}{request_counter}"
            headers = {'User-Agent': random.choice(USER_AGENTS)}  # 随机 User-Agent
            response = session.get(request_url, timeout=30, verify=False, headers=headers)  # 增加 timeout, 忽略 SSL 验证
            with counter_lock:
                request_counter += 1
                logging.info(f"访问 {site_name} ({request_url}), 状态码: {response.status_code}")
            if response.status_code == 429:
                logging.warning(f"触发 429 率限，额外等待 5 秒")
                time.sleep(5)
            time.sleep(random.uniform(0.5, 2.0))  # 随机间隔，防止反爬
        except requests.exceptions.SSLError as e:
            logging.error(f"SSL 错误 {site_name} ({request_url}): {e} - 跳过")
            time.sleep(1)
        except requests.exceptions.ConnectTimeout as e:
            logging.error(f"连接超时 {site_name} ({request_url}): {e} - 重试")
            time.sleep(2)  # 重试前等待
        except requests.exceptions.ReadTimeout as e:
            logging.error(f"读取超时 {site_name} ({request_url}): {e} - 跳过")
            time.sleep(1)
        except requests.exceptions.NameResolutionError as e:
            logging.error(f"域名解析失败 {site_name} ({request_url}): {e} - 跳过域名")
            urls.remove(url) if url in urls else None  # 移除无效域名
        except requests.RequestException as e:
            logging.error(f"其他请求错误 {site_name} ({request_url}): {e} - 跳过")
            time.sleep(1)
        except KeyboardInterrupt:
            logging.info("线程被用户终止")
            break

def main():
    """主函数，分配线程并启动访问"""
    # 创建 Tkinter 窗口（隐藏主窗口）
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    try:
        # 弹出输入框获取线程数
        threads_per_site = simpledialog.askinteger(
            "输入线程数",
            "请输入每个网站的线程数（建议 5-10）：",
            parent=root,
            minvalue=1,
            maxvalue=10
        )
        if threads_per_site is None:
            raise ValueError("用户取消输入")
    except ValueError as e:
        logging.error(f"无效输入: {e}")
        messagebox.showerror("错误", "无效线程数，使用默认值 5")
        threads_per_site = 5  # 默认每个网站 5 个线程

    # 销毁 Tkinter 窗口
    root.destroy()

    # 创建请求会话，配置代理和重试机制
    session = requests.Session()
    retry = Retry(
        total=3,  # 总重试次数
        backoff_factor=1,  # 指数退避
        status_forcelist=[429, 500, 502, 503, 504]  # 重试这些状态码
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    # 若使用 OpenClash 代理，取消注释并填入代理地址
    # session.proxies = {'http': 'http://192.168.1.1:7890', 'https': 'http://192.168.1.1:7890'}

    # 使用 ThreadPoolExecutor 管理线程
    logging.info(f"每个网站分配线程数: {threads_per_site}")
    logging.info(f"目标网站: {list(WEBSITES.keys())}")
    with ThreadPoolExecutor(max_workers=threads_per_site * len(WEBSITES)) as executor:
        for site_name, urls in WEBSITES.items():
            for i in range(threads_per_site):
                executor.submit(visit_url, site_name, urls, session)

    logging.info("所有线程已启动，按 Ctrl+C 退出")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("程序已停止")
        sys.exit(0)