"""
数据清洗与处理模块：验证数据完整性，处理缺失或异常值
"""

import pandas as pd
import numpy as np


def clean_music_data(df):
    """
    清洗音乐数据
    
    参数:
        df: 原始DataFrame
    
    返回:
        DataFrame: 清洗后的数据
    """
    if df.empty:
        return df
    
    # 1. 去除完全重复的行
    df = df.drop_duplicates(subset=['title', 'singer'], keep='first')
    
    # 2. 处理缺失值
    # 评分缺失 -> 填充为该列均值
    df['rating'] = df['rating'].fillna(df['rating'].mean())
    # 评分人数缺失 -> 填充为0
    df['rating_people'] = df['rating_people'].fillna(0)
    # 流派缺失 -> 填充为'未知'
    df['genre'] = df['genre'].fillna('未知')
    df['singer'] = df['singer'].fillna('未知')
    df['release_date'] = df['release_date'].fillna('未知')
    
    # 3. 处理异常值
    # 评分范围应为0-10，超出范围的修正
    df['rating'] = df['rating'].clip(0, 10)
    # 评分人数不能为负数
    df['rating_people'] = df['rating_people'].apply(lambda x: max(0, x))
    
    # 4. 标准化流派名称（去除多余空格，统一格式）
    df['genre'] = df['genre'].str.strip()
    
    # 5. 提取发行年份
    def extract_year(date_str):
        if pd.isna(date_str) or date_str == '未知':
            return None
        # 尝试提取4位数字年份
        import re
        match = re.search(r'(\d{4})', str(date_str))
        return int(match.group(1)) if match else None
    
    df['release_year'] = df['release_date'].apply(extract_year)
    
    # 6. 添加流行度指标（评分人数越高越流行）
    max_people = df['rating_people'].max()
    if max_people > 0:
        df['popularity_score'] = df['rating_people'] / max_people * 100
    else:
        df['popularity_score'] = 0
    
    return df


def validate_data(df):
    """
    验证数据完整性
    
    参数:
        df: 待验证的DataFrame
    
    返回:
        dict: 验证结果
    """
    result = {
        'total_rows': len(df),
        'missing_values': df.isnull().sum().to_dict(),
        'unique_genres': df['genre'].nunique(),
        'unique_singers': df['singer'].nunique(),
        'rating_range': (df['rating'].min(), df['rating'].max()),
        'valid': True
    }
    
    # 检查关键字段是否为空
    if df['title'].isnull().any():
        result['valid'] = False
        result['error'] = '存在空标题'
    
    return result


if __name__ == '__main__':
    # 测试清洗功能
    from data_collection import collect_music_data
    raw_df = collect_music_data(max_pages=3)
    clean_df = clean_music_data(raw_df)
    print(validate_data(clean_df))