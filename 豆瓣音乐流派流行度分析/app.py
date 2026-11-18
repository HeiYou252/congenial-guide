"""
用户登录与数据查询模块 + 用户管理（管理员）
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from db_manager import MusicDB
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'  # 务必修改

db = MusicDB(
    server='localhost',
    database='MusicAnalysis',
    trusted_connection=True
    # 若使用 SQL Server 身份验证，改为 username='sa', password='xxx', trusted_connection=False
)


# ---------- 辅助函数 ----------
def is_logged_in():
    return 'user_id' in session

def is_admin():
    return is_logged_in() and session.get('role') == 'admin'


# ---------- 路由 ----------

@app.route('/')
def index():
    if is_logged_in():
        return redirect(url_for('query'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('用户名和密码不能为空')
            return render_template_string(LOGIN_HTML)

        user = db.get_user(username)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']  # 记录角色
            flash('登录成功！')
            return redirect(url_for('query'))
        else:
            flash('用户名或密码错误')
    return render_template_string(LOGIN_HTML)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm', '').strip()
        if not username or not password:
            flash('用户名和密码不能为空')
            return render_template_string(REGISTER_HTML)
        if password != confirm:
            flash('两次密码输入不一致')
            return render_template_string(REGISTER_HTML)
        if len(password) < 6:
            flash('密码长度至少6位')
            return render_template_string(REGISTER_HTML)
        pwd_hash = generate_password_hash(password)
        # 默认角色为 'user'
        success = db.add_user(username, pwd_hash, role='user')
        if success:
            flash('注册成功，请登录')
            return redirect(url_for('login'))
        else:
            flash('用户名已存在，请更换')
    return render_template_string(REGISTER_HTML)


@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录')
    return redirect(url_for('login'))


@app.route('/query', methods=['GET', 'POST'])
def query():
    if not is_logged_in():
        flash('请先登录')
        return redirect(url_for('login'))

    genre = request.args.get('genre', '').strip()
    min_rating = request.args.get('min_rating', '').strip()
    max_rating = request.args.get('max_rating', '').strip()
    title = request.args.get('title', '').strip()
    limit = request.args.get('limit', '50').strip()

    conditions = []
    params = {}

    if genre:
        conditions.append("genre LIKE :genre")
        params['genre'] = f'%{genre}%'
    if min_rating:
        try:
            mr = float(min_rating)
            conditions.append("rating >= :min_rating")
            params['min_rating'] = mr
        except ValueError:
            pass
    if max_rating:
        try:
            mr = float(max_rating)
            conditions.append("rating <= :max_rating")
            params['max_rating'] = mr
        except ValueError:
            pass
    if title:
        conditions.append("title LIKE :title")
        params['title'] = f'%{title}%'

    try:
        lim = int(limit)
        if lim < 1:
            lim = 50
        elif lim > 200:
            lim = 200
    except:
        lim = 50

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    sql = f"""
        SELECT TOP {lim} id, title, singer, rating, rating_people, release_date, genre
        FROM music
        WHERE {where_clause}
        ORDER BY rating DESC, rating_people DESC
    """
    with db.engine.connect() as conn:
        if params:
            df = pd.read_sql(sql, conn, params=params)
        else:
            df = pd.read_sql(sql, conn)

    genre_list = []
    try:
        genre_df = pd.read_sql("SELECT DISTINCT genre FROM music WHERE genre != '未知' ORDER BY genre", db.engine)
        genre_list = genre_df['genre'].tolist()
    except:
        pass

    return render_template_string(
        QUERY_HTML,
        results=df.to_dict('records'),
        genres=genre_list,
        genre=genre,
        min_rating=min_rating,
        max_rating=max_rating,
        title=title,
        limit=lim,
        username=session.get('username', ''),
        is_admin=is_admin()
    )


# ---------- 管理员后台 ----------
@app.route('/admin')
def admin_panel():
    if not is_admin():
        flash('需要管理员权限')
        return redirect(url_for('query'))
    
    users_df = db.get_all_users()
    users = users_df.to_dict('records')
    return render_template_string(ADMIN_HTML, users=users)


@app.route('/admin/delete/<int:user_id>')
def admin_delete_user(user_id):
    if not is_admin():
        flash('权限不足')
        return redirect(url_for('query'))
    # 禁止删除自己
    if user_id == session['user_id']:
        flash('不能删除自己')
        return redirect(url_for('admin_panel'))
    success = db.delete_user(user_id)
    if success:
        flash('用户已删除')
    else:
        flash('无法删除管理员用户（至少保留一个）')
    return redirect(url_for('admin_panel'))


@app.route('/admin/role/<int:user_id>/<role>')
def admin_change_role(user_id, role):
    if not is_admin():
        flash('权限不足')
        return redirect(url_for('query'))
    if role not in ('admin', 'user'):
        flash('无效角色')
        return redirect(url_for('admin_panel'))
    # 不能修改自己的角色（防止意外）
    if user_id == session['user_id']:
        flash('不能修改自己的角色')
        return redirect(url_for('admin_panel'))
    success = db.update_user_role(user_id, role)
    if success:
        flash('角色已更新')
    else:
        flash('操作失败：至少保留一个管理员')
    return redirect(url_for('admin_panel'))


# ---------- HTML 模板 ----------
LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>登录</title>
<style>
body { font-family: Arial; background: #f4f4f4; display: flex; justify-content: center; padding-top: 80px; }
.card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 360px; }
h2 { text-align: center; }
input { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; }
button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
button:hover { background: #0056b3; }
.flash { color: red; text-align: center; }
a { display: block; text-align: center; margin-top: 12px; }
</style>
</head>
<body>
<div class="card">
<h2>用户登录</h2>
{% with messages = get_flashed_messages() %}
  {% if messages %}<div class="flash">{{ messages[0] }}</div>{% endif %}
{% endwith %}
<form method="POST">
  <input type="text" name="username" placeholder="用户名" required>
  <input type="password" name="password" placeholder="密码" required>
  <button type="submit">登录</button>
</form>
<a href="{{ url_for('register') }}">没有账号？立即注册</a>
</div>
</body>
</html>
'''

REGISTER_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>注册</title>
<style>
body { font-family: Arial; background: #f4f4f4; display: flex; justify-content: center; padding-top: 80px; }
.card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 360px; }
h2 { text-align: center; }
input { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; }
button { width: 100%; padding: 10px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; }
button:hover { background: #218838; }
.flash { color: red; text-align: center; }
a { display: block; text-align: center; margin-top: 12px; }
</style>
</head>
<body>
<div class="card">
<h2>用户注册</h2>
{% with messages = get_flashed_messages() %}
  {% if messages %}<div class="flash">{{ messages[0] }}</div>{% endif %}
{% endwith %}
<form method="POST">
  <input type="text" name="username" placeholder="用户名" required>
  <input type="password" name="password" placeholder="密码（至少6位）" required>
  <input type="password" name="confirm" placeholder="确认密码" required>
  <button type="submit">注册</button>
</form>
<a href="{{ url_for('login') }}">已有账号？去登录</a>
</div>
</body>
</html>
'''

QUERY_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>数据查询</title>
<style>
body { font-family: Arial; background: #f4f4f4; margin: 20px; }
.container { max-width: 1300px; margin: auto; background: white; padding: 20px; border-radius: 8px; }
.top-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 10px; }
h2 { margin: 0; }
.user-info { font-weight: bold; }
.logout-btn { background: #dc3545; color: white; padding: 6px 15px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; }
.logout-btn:hover { background: #c82333; }
.admin-link { margin-right: 15px; }
.filter-form { display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; align-items: center; }
.filter-form input, .filter-form select { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
.filter-form button { padding: 8px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
.filter-form button:hover { background: #0056b3; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
th { background: #f2f2f2; }
tr:hover { background: #f9f9f9; }
.empty { text-align: center; padding: 20px; color: #888; }
</style>
</head>
<body>
<div class="container">
  <div class="top-bar">
    <h2>🎵 音乐数据查询</h2>
    <div>
      {% if is_admin %}
        <a href="{{ url_for('admin_panel') }}" class="admin-link" style="color:#007bff;">👑 管理后台</a>
      {% endif %}
      <span class="user-info">欢迎，{{ username }}</span>
      <a href="{{ url_for('logout') }}" class="logout-btn">登出</a>
    </div>
  </div>

  <form method="GET" class="filter-form">
    <input type="text" name="title" placeholder="专辑名称" value="{{ title }}">
    <input type="text" name="genre" placeholder="流派 (如 摇滚)" value="{{ genre }}">
    <input type="number" step="0.1" min="0" max="10" name="min_rating" placeholder="最低评分" value="{{ min_rating }}">
    <input type="number" step="0.1" min="0" max="10" name="max_rating" placeholder="最高评分" value="{{ max_rating }}">
    <input type="number" name="limit" placeholder="显示条数" value="{{ limit }}" style="width:80px;">
    <button type="submit">查询</button>
    <a href="{{ url_for('query') }}" style="text-decoration:none;color:#007bff;">重置</a>
  </form>

  <div style="margin-top:10px;font-size:14px;color:#666;">
    共 {{ results|length }} 条记录
  </div>

  {% if results %}
  <table>
    <thead>
      <tr>
        <th>ID</th><th>专辑</th><th>歌手</th><th>评分</th><th>评分人数</th><th>发行日期</th><th>流派</th>
      </tr>
    </thead>
    <tbody>
      {% for row in results %}
      <tr>
        <td>{{ row.id }}</td>
        <td>{{ row.title }}</td>
        <td>{{ row.singer }}</td>
        <td>{{ row.rating }}</td>
        <td>{{ row.rating_people }}</td>
        <td>{{ row.release_date }}</td>
        <td>{{ row.genre }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="empty">没有找到匹配的记录</div>
  {% endif %}
</div>
</body>
</html>
'''

ADMIN_HTML = '''
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>用户管理</title>
<style>
body { font-family: Arial; background: #f4f4f4; margin: 20px; }
.container { max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 8px; }
.top-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; padding-bottom: 10px; }
h2 { margin: 0; }
.btn { display: inline-block; padding: 4px 10px; border-radius: 4px; text-decoration: none; color: white; font-size: 13px; margin: 0 2px; }
.btn-danger { background: #dc3545; }
.btn-danger:hover { background: #c82333; }
.btn-warning { background: #ffc107; color: #212529; }
.btn-warning:hover { background: #e0a800; }
.btn-success { background: #28a745; }
.btn-success:hover { background: #218838; }
.btn-primary { background: #007bff; }
.btn-primary:hover { background: #0056b3; }
.back-link { margin-bottom: 15px; display: inline-block; }
table { width: 100%; border-collapse: collapse; margin-top: 15px; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
th { background: #f2f2f2; }
.flash { color: red; text-align: center; margin: 10px 0; }
</style>
</head>
<body>
<div class="container">
  <div class="top-bar">
    <h2>👑 用户管理</h2>
    <a href="{{ url_for('query') }}" class="btn btn-primary">返回查询</a>
  </div>

  {% with messages = get_flashed_messages() %}
    {% if messages %}<div class="flash">{{ messages[0] }}</div>{% endif %}
  {% endwith %}

  <table>
    <thead>
      <tr>
        <th>ID</th><th>用户名</th><th>角色</th><th>注册时间</th><th>操作</th>
      </tr>
    </thead>
    <tbody>
      {% for user in users %}
      <tr>
        <td>{{ user.id }}</td>
        <td>{{ user.username }}</td>
        <td>{{ user.role }}</td>
        <td>{{ user.created_at }}</td>
        <td>
          {% if user.role == 'admin' %}
            <a href="{{ url_for('admin_change_role', user_id=user.id, role='user') }}" class="btn btn-warning">降为普通用户</a>
          {% else %}
            <a href="{{ url_for('admin_change_role', user_id=user.id, role='admin') }}" class="btn btn-success">设为管理员</a>
          {% endif %}
          {% if user.id != session.user_id %}
            <a href="{{ url_for('admin_delete_user', user_id=user.id) }}" class="btn btn-danger" onclick="return confirm('确定删除该用户吗？')">删除</a>
          {% else %}
            <span style="color:#999;">（自己）</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
</body>
</html>
'''


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)