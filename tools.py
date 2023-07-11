# encoding = utf-8
import csv
import imghdr
import logging
import msvcrt
from multiprocessing.pool import ThreadPool
import os
import threading
import time
import requests

logging.basicConfig(filename="test.log", filemode="a", format="%(asctime)s %(name)s:%(levelname)s:%(message)s", datefmt="%D %H:%M:%S", level=logging.ERROR)


ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.10240"

# 开4个 worker，没有参数时默认是 cpu 的核心数
pool = ThreadPool(processes=4)

# 请求网页内容
def request_page(url, times = 10, type = 'text'):
    try:
        number = 0
        flag = False
        while (number < times and flag == False):
            number = number + 1
            # print(f"`````{number}")
            response = requests.request('GET', url, headers={'User-agent': ua})
            if response.status_code == 200:
                flag = True
                # 文本
                if type == 'text':
                    return response.text
                # 字节
                return response.content
                
            time.sleep(2)
            if (number == times - 1):
                print(f'请求- {url} ,错误{times}次')
        return False
    except AssertionError as error:
        return None
    
    
# 创建文件夹 方法
def path_create(relative_path):
    if not os.path.isdir(relative_path): 
        os.makedirs(relative_path)


# 写入 csv
def write_csv(dir, csvname, headers, row):
    path_create(dir)
    csv_path = f'{dir}/{csvname}.csv'
    if not os.path.exists(csv_path):
        with open(csv_path,'a+',encoding='utf-8-sig',newline='') as f :
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 100)
            writer = csv.writer(f)
            writer.writerow(headers)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 100)
            

    with open(csv_path,'a+',encoding='utf-8-sig',newline='') as f2 :
        # lock the file
        msvcrt.locking(f2.fileno(), msvcrt.LK_LOCK, 100)
        writer = csv.writer(f2)
        writer.writerow(row)
        msvcrt.locking(f2.fileno(), msvcrt.LK_UNLCK, 100)
                
        
#多线程下载图片数据
def thread_down(imgInfoArr, times = 0):
    print(f' -- thread_down.-|-{threading.current_thread().ident} ')
    # print(f'图片 数量 {len(imgInfoArr)}')
    try:
        times = times + 1
        global pool
        if (times == 2):
            logging.error(f'imgInfoArr--\n {imgInfoArr}')
        results = pool.map(dowm, imgInfoArr)
        # pool.close()
        # pool.join()
        # print("thread_down 完成".center(50, "-"))
        # print("")
    except:
        print("Error: unable to start thread")
        logging.error(f'unable to start thread------- {times}')
        time.sleep(3)
        if (times < 5):
            thread_down(imgInfoArr, times)
        else:
            logging.error(f'unable to start thread------- {times}\n')
            logging.error(f'imgInfoArr-final-- {imgInfoArr}')
            
        
     
        
#下载图片数据
def dowm(data):
    print(f' -- down.-|-{threading.current_thread().ident} ')
    url = data['detail_origin_path']   # origin
    down_index = data['down_index']
    down_dir = data['down_dir']
    format = data['format']
    
    img = request_page(url, 5, 'content')
    if (img == None or img == False):
        print(f'image error - img_data----\n{data}\n')
        logging.error(f'image error - img_data----\n{data}\n')
        return
    if (format== ''):
        format = imghdr.what(None,img)
    filename = f'{down_dir}/{str(down_index).zfill(2)}.{format}'
    
    # print(f'-|-{threading.current_thread().ident}  -- down.: {filename}')
    with open(filename, 'wb') as f:
        f.write(img)
        

# 获取 dict 的值， 为空返回 默认 '0'
def dict_key(data, key, null_value = '0'):
    try:
        # 原 python dict 方法
        if data.get(key) == None:
            return null_value
        else:
            return data.get(key)
    except Exception:
        # 使用 js2py.eval_js 转化的数据
        if data[key] == None:
            return null_value
        else:
            return data[key]
        # raise e
