import time
import yagmail
from datetime import datetime
from tempfile import TemporaryDirectory
from django.core.cache import cache
import pandas as pd
import requests
from bs4 import BeautifulSoup

def task1(name):
    print("Hello!")
    time.sleep(3)
    print(name)

def send_email(data):
    with TemporaryDirectory() as tmp_folder:
        cache_data = cache.get(data['sid'])
        orders_df = pd.read_json(cache_data, orient='table')
        print(orders_df)
        dt = datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
        file_path = f'{tmp_folder}/{dt}.csv'
        orders_df.to_csv(file_path, encoding='gbk')
        yag = yagmail.SMTP(user='724996686@qq.com', host='smtp.qq.com')
        content = ['订单数据表格请见附件', file_path]
        yag.send(data['email'], data['subject'], content)
    return True

def ifeng_spider():
    url = 'http://www.ifeng.com/'
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    }
    html = requests.get(url, headers=headers)
    soup = BeautifulSoup(html.text, 'lxml')
    urls = soup.select('div.hot_box-1yXFLW7e  p a')
    result = []
    for url in urls:
        print(f"正在处理{url['title']}")
        html = requests.get(url['href'], headers=headers)
        soup = BeautifulSoup(html.text, 'lxml')
        text = ''
        paragraphs = soup.select('div.main_content-r5RGqegj p')
        for p in paragraphs:
            text += p.text
        result.append({
            "href": url['href'],
            "title": url['title'],
            "content": text
        })
    cache.set('ifeng-spider',result)
    return True
