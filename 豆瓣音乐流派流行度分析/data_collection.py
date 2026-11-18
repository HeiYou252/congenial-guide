"""
数据采集模块：从豆瓣音乐TOP250采集音乐数据
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re


def collect_music_data(max_pages=10):
    """
    采集豆瓣音乐TOP250的数据
    
    参数:
        max_pages: 最大采集页数（每页25条）
    
    返回:
        DataFrame: 采集到的音乐数据
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    music_list = []
    
    for page in range(max_pages):
        start = page * 25
        url = f'https://music.douban.com/top250?start={start}'
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            items = soup.select('tr.item')
            
            if not items:
                break
                
            for item in items:
                try:
                    title_elem = item.select_one('.pl2 a')
                    title = title_elem.text.replace('\n', '').strip() if title_elem else '未知'
                    link = title_elem['href'] if title_elem else ''
                    
                    rating_elem = item.select_one('.rating_nums')
                    rating = float(rating_elem.text) if rating_elem else 0.0
                    
                    people_elem = item.select('.pl')[1] if len(item.select('.pl')) > 1 else None
                    if people_elem:
                        people_text = people_elem.text.strip()
                        people_match = re.search(r'(\d+)', people_text)
                        rating_people = int(people_match.group(1)) if people_match else 0
                    else:
                        rating_people = 0
                    
                    info_elem = item.select_one('.pl')
                    if info_elem:
                        info_text = info_elem.text.strip()
                        parts = info_text.split(' / ')
                        singer = parts[0] if len(parts) > 0 else '未知'
                        release_date = parts[1] if len(parts) > 1 else '未知'
                        album_type = parts[2] if len(parts) > 2 else '未知'
                        medium = parts[3] if len(parts) > 3 else '未知'
                        genre = parts[4] if len(parts) > 4 else '未知'
                    else:
                        singer = release_date = album_type = medium = genre = '未知'
                    
                    music_list.append({
                        'title': title,
                        'link': link,
                        'rating': rating,
                        'rating_people': rating_people,
                        'singer': singer,
                        'release_date': release_date,
                        'album_type': album_type,
                        'medium': medium,
                        'genre': genre
                    })
                    
                except Exception as e:
                    print(f'解析单条数据出错: {e}')
                    continue
            
            print(f'已采集第 {page+1} 页，共 {len(items)} 条数据')
            time.sleep(1)
            
        except Exception as e:
            print(f'采集第 {page+1} 页出错: {e}')
            break
    
    return pd.DataFrame(music_list)


if __name__ == '__main__':
    df = collect_music_data(max_pages=5)
    print(f'共采集 {len(df)} 条数据')
    print(df.head())