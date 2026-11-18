"""
主程序：整合所有模块，完成完整的分析流程
"""

import os
import sys
from data_collection import collect_music_data
from data_processing import clean_music_data, validate_data
from data_analysis import analyze_genre_popularity, predict_popularity_trend
from db_manager import MusicDB
from ui import create_visualization


def main(max_pages=10):
    """
    主函数：执行完整的分析流程
    
    参数:
        max_pages: 采集页数（每页25条）
    """
    print('=' * 60)
    print('豆瓣音乐流派流行度分析系统')
    print('=' * 60)
    
    # 确保输出目录存在
    os.makedirs('output', exist_ok=True)
    
    # 1. 数据采集
    print('\n[1/6] 数据采集模块：正在采集豆瓣音乐数据...')
    raw_df = collect_music_data(max_pages=max_pages)
    print(f'采集完成，共 {len(raw_df)} 条原始数据')
    
    if raw_df.empty:
        print('未采集到数据，请检查网络连接')
        return
    
    # 2. 数据清洗
    print('\n[2/6] 数据清洗与处理模块：正在清洗数据...')
    clean_df = clean_music_data(raw_df)
    print(f'清洗完成，有效数据 {len(clean_df)} 条')
    
    # 3. 数据验证
    print('\n[3/6] 验证数据完整性...')
    validation = validate_data(clean_df)
    print(f'验证通过: {validation}')
    
    # 4. 数据分析
    print('\n[4/6] 数据分析与预测模块：正在分析流派流行度...')
    analysis_results = analyze_genre_popularity(clean_df)
    print(f'分析完成，共发现 {analysis_results["total_genres"]} 种流派')
    
    # 5. 趋势预测
    print('\n[5/6] 正在预测流行度趋势...')
    pred_results = predict_popularity_trend(analysis_results['genre_stats'])
    analysis_results['predictions'] = pred_results.get('predictions', [])
    print(f'预测完成')
    
    # 6. 数据库存储
    print('\n[6/6] 数据库管理模块：正在存储数据...')
    db = MusicDB(
    server='localhost',          
    database='MusicAnalysis',
    trusted_connection=True
)
    count = db.insert_music(clean_df)
    print(f'已存储 {count} 条数据到数据库')
    
    # 7. 生成可视化报告
    print('\n正在生成可视化报告...')
    create_visualization(clean_df, analysis_results)
    
    # 输出汇总
    print('\n' + '=' * 60)
    print('分析结果汇总')
    print('=' * 60)
    print(f'专辑总数: {len(clean_df)}')
    print(f'流派种类: {analysis_results["total_genres"]}')
    print(f'平均评分: {clean_df["rating"].mean():.2f}')
    print(f'最流行流派: {analysis_results["genre_stats"].iloc[0]["genre"] if not analysis_results["genre_stats"].empty else "无"}')
    print(f'流行度最高: {analysis_results["genre_stats"].iloc[0]["popularity_index"]:.1f} 分' if not analysis_results["genre_stats"].empty else '')
    
    print('\n所有任务完成！')
    print('报告位置: output/analysis_report.html')
    print('数据库位置: output/music.db')
    print('=' * 60)


if __name__ == '__main__':
    # 可调整采集页数（每页25条，10页=250条）
    main(max_pages=10)