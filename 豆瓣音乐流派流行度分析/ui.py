"""
用户界面模块：生成包含图表的HTML可视化报告
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # 无GUI后端
import matplotlib.pyplot as plt
import os
import base64
from io import BytesIO


def create_visualization(df, analysis_results):
    """
    创建可视化图表并生成HTML报告
    
    参数:
        df: 清洗后的数据
        analysis_results: 分析结果字典
    """
    if df.empty:
        print('没有数据可可视化')
        return
    
    # 确保输出目录存在
    os.makedirs('output', exist_ok=True)
    
    # 1. 流派分布柱状图（TOP10）
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    genre_counts = df['genre'].value_counts().head(10)
    colors = plt.cm.Set3(range(len(genre_counts)))
    bars = ax1.bar(genre_counts.index, genre_counts.values, color=colors)
    ax1.set_title('TOP10 音乐流派专辑数量分布', fontsize=16, fontweight='bold')
    ax1.set_xlabel('流派', fontsize=12)
    ax1.set_ylabel('专辑数量', fontsize=12)
    ax1.tick_params(axis='x', rotation=45)
    # 添加数值标签
    for bar, val in zip(bars, genre_counts.values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                str(val), ha='center', va='bottom', fontsize=10)
    plt.tight_layout()
    img1 = fig_to_base64(fig1)
    plt.close(fig1)
    
    # 2. 流派平均评分对比图
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    genre_rating = df.groupby('genre')['rating'].mean().sort_values(ascending=False).head(10)
    bars2 = ax2.barh(genre_rating.index, genre_rating.values, color='skyblue')
    ax2.set_title('TOP10 流派平均评分', fontsize=16, fontweight='bold')
    ax2.set_xlabel('平均评分', fontsize=12)
    ax2.set_ylabel('流派', fontsize=12)
    # 添加数值标签
    for bar, val in zip(bars2, genre_rating.values):
        ax2.text(val + 0.05, bar.get_y() + bar.get_height()/2, 
                f'{val:.2f}', ha='left', va='center', fontsize=10)
    plt.tight_layout()
    img2 = fig_to_base64(fig2)
    plt.close(fig2)
    
    # 3. 流派流行度指数（综合）
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    if 'popularity_index' in analysis_results['genre_stats'].columns:
        pop_data = analysis_results['genre_stats'].head(10)
        bars3 = ax3.barh(pop_data['genre'], pop_data['popularity_index'], 
                         color='lightcoral')
        ax3.set_title('TOP10 流派综合流行度指数', fontsize=16, fontweight='bold')
        ax3.set_xlabel('流行度指数', fontsize=12)
        ax3.set_ylabel('流派', fontsize=12)
        for bar, val in zip(bars3, pop_data['popularity_index']):
            ax3.text(val + 0.5, bar.get_y() + bar.get_height()/2, 
                    f'{val:.1f}', ha='left', va='center', fontsize=10)
        plt.tight_layout()
        img3 = fig_to_base64(fig3)
        plt.close(fig3)
    else:
        img3 = ''
    
    # 4. 评分分布直方图
    fig4, ax4 = plt.subplots(figsize=(10, 5))
    ax4.hist(df['rating'], bins=20, color='purple', alpha=0.7, edgecolor='black')
    ax4.set_title('音乐评分分布', fontsize=16, fontweight='bold')
    ax4.set_xlabel('评分', fontsize=12)
    ax4.set_ylabel('专辑数量', fontsize=12)
    plt.tight_layout()
    img4 = fig_to_base64(fig4)
    plt.close(fig4)
    
    # 生成HTML报告
    html_content = generate_html_report(df, analysis_results, img1, img2, img3, img4)
    
    # 保存HTML
    with open('output/analysis_report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print('可视化报告已生成: output/analysis_report.html')


def fig_to_base64(fig):
    """将matplotlib图形转换为base64编码"""
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    buffer.close()
    return img_base64


def generate_html_report(df, results, img1, img2, img3, img4):
    """生成HTML报告"""
    
    # 准备数据表格
    top_genres_html = ''
    if not results['genre_stats'].empty:
        top10 = results['genre_stats'].head(10)
        for _, row in top10.iterrows():
            top_genres_html += f'''
            <tr>
                <td>{row['genre']}</td>
                <td>{row['album_count']}</td>
                <td>{row['avg_rating']:.2f}</td>
                <td>{row['total_rating_people']:,}</td>
                <td>{row['popularity_index']:.1f}</td>
            </tr>
            '''
    
    # 预测结果
    pred_html = ''
    if 'predictions' in results:
        for p in results.get('predictions', []):
            pred_html += f'''
            <div class="pred-item">
                <span class="genre-name">{p['genre']}</span>
                <span class="pop-value">当前: {p['current_popularity']}</span>
                <span class="pop-value">预测: {p['predicted_next']}</span>
                <span class="trend {p['trend']}">{p['trend']}</span>
            </div>
            '''
    
    html = f'''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>豆瓣音乐流派流行度分析报告</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', 'PingFang SC', Roboto, 'Helvetica Neue', sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
                padding: 30px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            }}
            h1 {{
                text-align: center;
                color: #2c3e50;
                font-size: 32px;
                margin-bottom: 10px;
                border-bottom: 4px solid #3498db;
                padding-bottom: 20px;
            }}
            .subtitle {{
                text-align: center;
                color: #7f8c8d;
                font-size: 14px;
                margin-bottom: 30px;
            }}
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }}
            .stat-card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }}
            .stat-card .number {{
                font-size: 32px;
                font-weight: bold;
            }}
            .stat-card .label {{
                font-size: 14px;
                opacity: 0.9;
                margin-top: 5px;
            }}
            .stat-card:nth-child(2) {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4);
            }}
            .stat-card:nth-child(3) {{
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                box-shadow: 0 4px 15px rgba(79, 172, 254, 0.4);
            }}
            .stat-card:nth-child(4) {{
                background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
                box-shadow: 0 4px 15px rgba(67, 233, 123, 0.4);
            }}
            .chart-container {{
                margin: 30px 0;
                text-align: center;
            }}
            .chart-container img {{
                max-width: 100%;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            }}
            .section-title {{
                font-size: 24px;
                color: #2c3e50;
                margin: 30px 0 15px 0;
                padding-left: 15px;
                border-left: 5px solid #3498db;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0 30px 0;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05);
            }}
            th {{
                background: #2c3e50;
                color: white;
                padding: 12px 15px;
                text-align: left;
                font-weight: 600;
            }}
            td {{
                padding: 10px 15px;
                border-bottom: 1px solid #ecf0f1;
            }}
            tr:hover {{
                background: #f8f9fa;
            }}
            .prediction-box {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .pred-item {{
                background: #f8f9fa;
                padding: 15px 20px;
                border-radius: 10px;
                border-left: 4px solid #3498db;
                display: flex;
                align-items: center;
                gap: 15px;
                flex-wrap: wrap;
            }}
            .pred-item .genre-name {{
                font-weight: bold;
                font-size: 16px;
                color: #2c3e50;
                min-width: 60px;
            }}
            .pred-item .pop-value {{
                background: white;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 13px;
                color: #555;
            }}
            .pred-item .trend {{
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: bold;
            }}
            .trend.上升 {{
                background: #d4edda;
                color: #155724;
            }}
            .trend.稳定 {{
                background: #fff3cd;
                color: #856404;
            }}
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ecf0f1;
                color: #95a5a6;
                font-size: 13px;
            }}
            @media (max-width: 768px) {{
                .container {{ padding: 20px; }}
                .stats-grid {{ grid-template-columns: 1fr 1fr; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>豆瓣音乐流派流行度分析报告</h1>
            <p class="subtitle">数据来源：豆瓣音乐TOP250 | 生成时间：{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">{len(df)}</div>
                    <div class="label">专辑总数</div>
                </div>
                <div class="stat-card">
                    <div class="number">{results.get('total_genres', 0)}</div>
                    <div class="label">流派种类</div>
                </div>
                <div class="stat-card">
                    <div class="number">{df['rating'].mean():.2f}</div>
                    <div class="label">平均评分</div>
                </div>
                <div class="stat-card">
                    <div class="number">{df['rating_people'].sum():,}</div>
                    <div class="label">总评分人数</div>
                </div>
            </div>
            
            <h2 class="section-title">流派分布（TOP10）</h2>
            <div class="chart-container">
                <img src="data:image/png;base64,{img1}" alt="流派分布图">
            </div>
            
            <h2 class="section-title">流派平均评分（TOP10）</h2>
            <div class="chart-container">
                <img src="data:image/png;base64,{img2}" alt="流派评分图">
            </div>
            
            <h2 class="section-title">流派综合流行度指数（TOP10）</h2>
            <div class="chart-container">
                <img src="data:image/png;base64,{img3}" alt="流派流行度图">
            </div>
            
            <h2 class="section-title">评分分布</h2>
            <div class="chart-container">
                <img src="data:image/png;base64,{img4}" alt="评分分布图">
            </div>
            
            <h2 class="section-title">流派流行度排行榜</h2>
            <table>
                <thead>
                    <tr>
                        <th>流派</th>
                        <th>专辑数量</th>
                        <th>平均评分</th>
                        <th>总评分人数</th>
                        <th>流行度指数</th>
                    </tr>
                </thead>
                <tbody>
                    {top_genres_html}
                </tbody>
            </table>
            
            <h2 class="section-title">流行度趋势预测</h2>
            <div class="prediction-box">
                {pred_html if pred_html else '<p>暂无预测数据</p>'}
            </div>
            <p style="color:#7f8c8d;font-size:13px;margin-top:5px;">
                预测方法：基于历史流行度指数的趋势外推
            </p>
            
            <div class="footer">
                <p>豆瓣音乐流派流行度分析系统 | 综合课程设计Ⅲ</p>
                <p>Powered by Python + Matplotlib</p>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html


if __name__ == '__main__':
    # 测试UI功能
    from data_collection import collect_music_data
    from data_processing import clean_music_data
    from data_analysis import analyze_genre_popularity, predict_popularity_trend
    
    raw_df = collect_music_data(max_pages=5)
    clean_df = clean_music_data(raw_df)
    results = analyze_genre_popularity(clean_df)
    results['predictions'] = predict_popularity_trend(results['genre_stats'])['predictions']
    create_visualization(clean_df, results)