import threading
import requests
import time
import sys
import os
import logging
import tkinter as tk
from tkinter import simpledialog, messagebox
from concurrent.futures import ThreadPoolExecutor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('access_log.txt'),
        logging.StreamHandler(sys.stdout)
    ]
)

# 目标网站列表
BASE_URLS = [
    "https://www.tiktok.com",
    "https://www.youtube.com",
    "https://www.netflix.com",
    "https://www.reddit.com",
    "https://www.x.com",
    "https://www.instagram.com",
    "https://www.facebook.com",
    "https://www.twitch.tv",
    "https://www.hulu.com",
    "https://www.bbc.com",
    "https://www.cnn.com",
    "https://www.amazon.com",
    "https://www.ebay.com",
    "https://www.google.com",
    "https://www.dropbox.com"
]

# 全局计数器
request_counter = 0
counter_lock = threading.Lock()

def visit_url(url, session):
    """访问单个 URL 的函数"""
    global request_counter
    while True:
        try:
            request_url = f"{url}{'?num=' if '?' not in url else '&num='}{request_counter}"
            response = session.get(request_url, timeout=5)
            with counter_lock:
                request_counter += 1
                logging.info(f"访问 {request_url}, 状态码: {response.status_code}")
            time.sleep(0.5)  # 调整为 0.5 秒，防止触发反爬机制
        except requests.RequestException as e:
            logging.error(f"访问 {request_url} 出错: {e}")
            time.sleep(1)  # 错误后等待重试
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
            "请输入每个网站的线程数（建议 5-20）：",
            parent=root,
            minvalue=1,
            maxvalue=20
        )
        if threads_per_site is None:
            raise ValueError("用户取消输入")
    except ValueError as e:
        logging.error(f"无效输入: {e}")
        messagebox.showerror("错误", "无效线程数，使用默认值 5")
        threads_per_site = 5  # 默认每个网站 5 个线程

    # 销毁 Tkinter 窗口
    root.destroy()

    # 创建请求会话，配置代理（若使用 OpenClash）
    session = requests.Session()
    # 若使用 OpenClash 代理，取消注释并填入代理地址
    # session.proxies = {'http': 'http://192.168.1.1:7890', 'https': 'http://192.168.1.1:7890'}

    # 使用 ThreadPoolExecutor 管理线程
    logging.info(f"每个网站分配线程数: {threads_per_site}")
    logging.info(f"目标网站: {BASE_URLS}")
    with ThreadPoolExecutor(max_workers=threads_per_site * len(BASE_URLS)) as executor:
        for url in BASE_URLS:
            for i in range(threads_per_site):
                executor.submit(visit_url, url, session)

    logging.info("所有线程已启动，按 Ctrl+C 退出")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("程序已停止")
        sys.exit(0)