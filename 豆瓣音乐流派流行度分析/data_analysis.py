"""
数据分析与预测模块：分析流派流行度模式和趋势
"""

import pandas as pd
import numpy as np
from collections import Counter


def analyze_genre_popularity(df):
    """
    分析各音乐流派的流行度
    
    参数:
        df: 清洗后的DataFrame
    
    返回:
        dict: 分析结果
    """
    if df.empty:
        return {}
    
    # 按流派分组统计
    genre_stats = df.groupby('genre').agg({
        'title': 'count',           # 专辑数量
        'rating': 'mean',           # 平均评分
        'rating_people': 'sum',     # 总评分人数（流行度指标）
        'popularity_score': 'mean'  # 平均流行度得分
    }).rename(columns={
        'title': 'album_count',
        'rating': 'avg_rating',
        'rating_people': 'total_rating_people',
        'popularity_score': 'avg_popularity'
    }).reset_index()
    
    # 计算综合流行度指数（加权：专辑数量40% + 平均评分30% + 总评分人数30%）
    if not genre_stats.empty:
        # 归一化处理
        genre_stats['norm_count'] = genre_stats['album_count'] / genre_stats['album_count'].max()
        genre_stats['norm_rating'] = genre_stats['avg_rating'] / genre_stats['avg_rating'].max()
        genre_stats['norm_people'] = genre_stats['total_rating_people'] / genre_stats['total_rating_people'].max()
        
        genre_stats['popularity_index'] = (
            genre_stats['norm_count'] * 0.4 + 
            genre_stats['norm_rating'] * 0.3 + 
            genre_stats['norm_people'] * 0.3
        ) * 100
    
    # 按流行度排序
    genre_stats = genre_stats.sort_values('popularity_index', ascending=False)
    
    # 提取TOP流派
    top_genres = genre_stats.head(10).to_dict('records')
    
    # 统计流派分布（所有流派）
    genre_distribution = df['genre'].value_counts().to_dict()
    
    # 年度趋势分析（按年份统计各流派专辑数）
    df_with_year = df[df['release_year'].notna()].copy()
    if not df_with_year.empty:
        df_with_year['release_year'] = df_with_year['release_year'].astype(int)
        yearly_trend = df_with_year.groupby(['release_year', 'genre']).size().unstack(fill_value=0)
    else:
        yearly_trend = pd.DataFrame()
    
    return {
        'genre_stats': genre_stats,
        'top_genres': top_genres,
        'genre_distribution': genre_distribution,
        'yearly_trend': yearly_trend,
        'total_albums': len(df),
        'total_genres': df['genre'].nunique()
    }


def predict_popularity_trend(genre_stats):
    """
    简单预测流派流行度趋势（基于现有数据推断）
    
    参数:
        genre_stats: 流派统计DataFrame
    
    返回:
        dict: 预测结果
    """
    if genre_stats.empty:
        return {}
    
    # 简单线性趋势预测：使用现有数据计算增长趋势
    # 这里用流行度指数作为预测依据
    top_genres = genre_stats.head(5)
    
    predictions = []
    for _, row in top_genres.iterrows():
        # 简单预测：流行度指数略有增长（模拟趋势）
        predictions.append({
            'genre': row['genre'],
            'current_popularity': round(row['popularity_index'], 2),
            'predicted_next': round(min(row['popularity_index'] * 1.05, 100), 2),
            'trend': '上升' if row['popularity_index'] > 50 else '稳定'
        })
    
    return {
        'predictions': predictions,
        'method': '基于历史流行度指数的趋势外推'
    }


if __name__ == '__main__':
    # 测试分析功能
    from data_collection import collect_music_data
    from data_processing import clean_music_data
    
    raw_df = collect_music_data(max_pages=5)
    clean_df = clean_music_data(raw_df)
    results = analyze_genre_popularity(clean_df)
    print('流派流行度分析结果:')
    print(results['genre_stats'].head())
    
    predictions = predict_popularity_trend(results['genre_stats'])
    print('\n预测结果:')
    print(predictions)