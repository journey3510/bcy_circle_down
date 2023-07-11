# encoding = utf-8
import concurrent
import json
import os
from concurrent.futures import ThreadPoolExecutor
import re
import sys
import threading
import time
import requests
import js2py
from configparser import ConfigParser
sys.path.append(".")
from tools import dict_key, thread_down, write_csv, path_create, request_page
import logging

logging.basicConfig(filename="test.log", filemode="a", format="%(asctime)s %(name)s:%(levelname)s:%(message)s", datefmt="%D %H:%M:%S", level=logging.ERROR)


file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
cf = ConfigParser(comment_prefixes='/', allow_no_value=True)
cf.read('config.ini', encoding='utf-8')


ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10240"
tagId = cf.get('down', 'tagId')
root_dir = cf.get('down', 'root_dir')
bcy_dir = f'{root_dir}/bcy'
root_item_url = f"https://bcy.net/item/detail/"


csv_headers = ['item_id', 'uname', 'uid', 'type', 'title', 'plain', 'collection_id', 
               'collection_title', 'like_count', 'view_count', 'tag_str', 'since', 'save_path']
csv_name = 'records_2'

# 排除 tag
exclude_tag = json.loads(cf.get('down', 'exclude_tag'))
# 包含 tag
include_tag = json.loads(cf.get('down', 'include_tag'))


# 生成文件夹路径
def create_dir_path(detail):
    # 根目录 + 作者
    dir = f'{bcy_dir}/{detail["uname"]} - {detail["uid"]}'
    if 'collection' in detail:
        # 文件夹 ＋ 合集 ＋ 单项
        dir = f'{dir}/合集-{detail["collection"]["collection_id"]}/{detail["item_id"]}'
    else:
        # 文件夹 ＋ 单项
        dir = f'{dir}/{detail["item_id"]}'
    return dir
        
        
# 获取单项网页数据
def get_one_page(url):
    try:
        html_text = request_page(url)
        if (html_text == False  or  html_text == None ):
            logging.error(f'请求页- {url} ----错误')           
        matchObj  = re.match( r'([\s\S]*)window.__ssr_data = (.*);([\s\S]*?)window._UID_', html_text, re.S)
        if matchObj:
            json_data = js2py.eval_js(matchObj.group(2))
            # 详情
            detail = json_data['detail']
            return detail
        else:
            logging.error(f'请求页- {url} ------ No match!!')
            print( "No match!!")
            return ''
    except Exception as e:
        raise e


# article 下载
def download_article(data):
    detail = data['item_detail']
    dir = create_dir_path(detail)
    path_create(dir)
    item_id = detail["item_id"]
    uname = detail["uname"]
    view_count = detail['view_count']
    
    url = f'{root_item_url}{detail["item_id"]}'
    try:
        detail = get_one_page(url)
        if detail != '':
            detail = detail['post_data']
            content = detail['content'].encode('utf-8', 'ignore').decode('utf-8')
            
            str1 = f'<p style=\"text-indent: 2em; margin-bottom: 1.5em; text-align: left;\">\t</p>'
            str2 = f'</p>'
 
            # 内容
            content = detail["content"].replace(str1, "\n").replace(str2, "\t\n\t\n").replace('</p>', "\t\n").replace('<br>	\n', "").replace('	\n	\n', "	\n")
            
            regex = re.compile(r"<.{1,80}?>")
            content = regex.sub('', content)
                    
            title = detail['title'] + '\n'
            summary = detail['summary'] if detail['summary'] == '' else f"\n 概要 :{detail['summary']}\n"
            context = title + summary + content
            context = context.encode('utf-8', 'ignore').decode('utf-8')
            
            with open(f'{dir}/{detail["item_id"]}.txt', "w", encoding="utf-8") as f:
                f.write(f'{context}\n')

            # csv 内容获取
            collection =  detail['collection']
            collection_id = '0'; collection_title = '0'
            if (collection):
                collection_id = collection['collection_id']
                collection_title = collection['title']
                
            # 1
            tag_Str = ''
            post_tags = detail['post_tags']
            if (post_tags):
                for index in range(len(post_tags)): 
                    if (tag_Str == '') : 
                        tag_Str = tag_Str + post_tags[index]['tag_name']
                    else: 
                        tag_Str = tag_Str + ('—' + post_tags[index]['tag_name']) 
                    
            data_row = ['* ' + str(detail['item_id']), uname, '* ' + str(detail['uid']),
                        detail['type'],
                        dict_key(detail, 'title'),
                        dict_key(detail, 'plain'), 
                        collection_id, collection_title, 
                        detail['like_count'], view_count,
                        tag_Str, dict_key(detail, 'ctime'), dir ]
            write_csv(dir=root_dir, csvname=csv_name, headers=csv_headers, row=data_row)
        
    except Exception as e:
        logging.error(f'article- {item_id} ------ {e}\n')
        print(f"==>> e: {e}")
        raise e


# note 图片 下载
def download_note(data):
    detail = data['item_detail']
    dir = create_dir_path(detail)
    path_create(dir)
    
    item_id = detail['item_id']
    imgList = detail['image_list']
    for index in range(len(imgList)):
        item = imgList[index]
        item['down_dir'] = dir
        item['page_item_id'] = item_id
        item['down_index'] = index + 1
        
    thread_down(imgList)

    # csv 内容获取
    try:
        collection = dict_key(detail, 'collection')
        collection_id= '0'; collection_title = '0'
        if (collection != '0'):
            collection_id = collection['collection_id']
            collection_title = collection['title']
        
        # 1
        tag_Str = ''
        post_tags = detail['post_tags']
        if (post_tags):
            for index in range(len(post_tags)): 
                if (tag_Str == '') : 
                    tag_Str = tag_Str + post_tags[index]['tag_name']
                else: 
                    tag_Str = tag_Str + ('—' + post_tags[index]['tag_name'])   
                 
        data_row = ['* ' + str(detail['item_id']), 
                    detail['uname'], '* ' + str(detail['uid']), detail['type'],
                    dict_key(detail, 'title'),
                    dict_key(detail, 'plain'), 
                    collection_id, collection_title, 
                    detail['like_count'], detail['view_count'],
                    tag_Str, dict_key(detail, 'ctime'), dir ]
        write_csv(dir=root_dir, csvname=csv_name, headers=csv_headers, row=data_row)
    except Exception as e:
        logging.error(f'note- {item_id} ------ {e}\n')
        print(f"==>> e: {e}")
        raise e


# 下载 分类
def download_sort(item):
    print(f"____ {item['item_detail']['item_id']} --|--{threading.current_thread().ident}  ----开始")
    
    tag = item['item_detail']['post_tags']
    global exclude_tag
    x = [k for k in tag if k['tag_name'] in exclude_tag]
    if len(x) > 0:
        return
    
    global include_tag
    x = [t for t in tag if t['tag_name'] in include_tag]
    if len(x) == 0:
        return
    
    type = item['item_detail']['type']  # type-: note || article || video || ganswer
    if type == 'note':
        download_note(item)
    elif type == 'article':
        download_article(item)
    elif type == 'video':
        print('video')
    elif type == 'ganswer':
        print('ganswer')
    else:
        print('none')
    print(str(item['item_detail']['item_id'] + '完成').center(50, "-"))
    print('||')


    
# 分配
def distribute(list_data):
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as exector:
        for item in list_data:
            exector.submit(download_sort, item)


def get_page_urls():
    tag_since = cf.get('down', 'tag_since')
    tag_url = f"https://bcy.net/apiv3/common/circleFeed?circle_id={str(tagId)}&since={tag_since}&sort_type=2&grid_type=10"

    with requests.request('GET', tag_url, headers={'User-agent': ua}) as res:
        content = res.text
        result = json.loads(content)
        list = result['data']['items']
        if (len(list) == 0):
            return None
        next_since = list[len(list) - 1]['since']
        print("".center(50, "-"))
    return {'list': list, 'next_since': next_since}
    

if __name__ == '__main__':
    flag = True
    while flag:
        print("如要退出，请在 倒计时 结束前退出".center(50, "-"))
        for i in range(1):
            print(f'倒计时 - {2 - i * 2} ')
            time.sleep(2)
        print("开始 - 请不要退出".center(50, "-"))
    
        # 网络 判断
        res = os.system("ping baidu.com -n 1")
        ping_Flag = True if res == 0 else False
        if (ping_Flag == False):
            print('error，网络连接失败，睡眠 60s')
            logging.error('error，网络连接失败，睡眠 60s')
            time.sleep(1*60)
        else:
            new_data = get_page_urls()
            
            if (new_data['list'] == None):
                flag = False
            else:
                distribute(new_data['list'])
                time.sleep(1)

                cf['down']['tag_since'] = new_data['next_since']
                with open('config.ini', 'w',encoding='utf-8') as configfile:
                    cf.write(configfile)
        
