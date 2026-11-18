"""
数据库管理模块（SQL Server 版本）
包含音乐数据表和用户表（含角色）
"""

from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float, inspect
import pandas as pd


class MusicDB:
    def __init__(self, server='localhost', database='MusicAnalysis',
                 username=None, password=None, trusted_connection=True):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.trusted_connection = trusted_connection

        # 构建 SQLAlchemy 连接字符串
        if trusted_connection:
            conn_str = f'mssql+pyodbc://@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
        else:
            conn_str = f'mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server'
        self.engine = create_engine(conn_str)

        self._ensure_database_exists()
        self._init_table()
        self.init_user_table()  # 确保用户表存在并包含 role 列

    def _ensure_database_exists(self):
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            # 若数据库不存在，连接到 master 创建
            if self.trusted_connection:
                master_url = f'mssql+pyodbc://@{self.server}/master?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
            else:
                master_url = f'mssql+pyodbc://{self.username}:{self.password}@{self.server}/master?driver=ODBC+Driver+17+for+SQL+Server'
            master_engine = create_engine(master_url)
            with master_engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE [{self.database}]"))
                conn.commit()
            # 重建引擎指向新数据库
            if self.trusted_connection:
                conn_str = f'mssql+pyodbc://@{self.server}/{self.database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
            else:
                conn_str = f'mssql+pyodbc://{self.username}:{self.password}@{self.server}/{self.database}?driver=ODBC+Driver+17+for+SQL+Server'
            self.engine = create_engine(conn_str)

    def _init_table(self):
        metadata = MetaData()
        Table(
            'music', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('title', String(200), nullable=False),
            Column('singer', String(100)),
            Column('rating', Float),
            Column('rating_people', Integer),
            Column('release_date', String(50)),
            Column('release_year', Integer),
            Column('album_type', String(50)),
            Column('medium', String(50)),
            Column('genre', String(100)),
            Column('popularity_score', Float),
            Column('link', String(300))
        )
        metadata.create_all(self.engine, checkfirst=True)

    def init_user_table(self):
        """创建用户表（如果不存在），并确保 role 列存在"""
        metadata = MetaData()
        Table(
            'users', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('username', String(50), unique=True, nullable=False),
            Column('password_hash', String(200), nullable=False),
            Column('role', String(20), nullable=False, default='user'),  # 'admin' 或 'user'
            Column('created_at', String(30))
        )
        metadata.create_all(self.engine, checkfirst=True)

        # 检查并添加 role 列（如果表已存在但该列缺失）
        inspector = inspect(self.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'role' not in columns:
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD role VARCHAR(20) DEFAULT 'user' NOT NULL"))
                conn.commit()
                print("已添加 role 列到 users 表")

        # 若没有任何用户，自动创建一个管理员（默认 admin/admin123）
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            if result == 0:
                from werkzeug.security import generate_password_hash
                admin_pwd = generate_password_hash('admin123')
                conn.execute(
                    text("INSERT INTO users (username, password_hash, role, created_at) VALUES (:uname, :pwd, 'admin', :created)"),
                    {"uname": "admin", "pwd": admin_pwd, "created": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
                )
                conn.commit()
                print("已创建默认管理员账号: admin / admin123")

    def insert_music(self, df):
        if df.empty:
            return 0
        df_to_insert = df[['title','singer','rating','rating_people',
                           'release_date','release_year','album_type',
                           'medium','genre','popularity_score','link']].copy()
        df_to_insert = df_to_insert.where(pd.notnull(df_to_insert), None)
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM music"))
            conn.commit()
            df_to_insert.to_sql('music', self.engine, if_exists='append', 
                                index=False, chunksize=500)
            conn.commit()
        return len(df_to_insert)

    def query_all(self):
        return pd.read_sql('SELECT * FROM music', self.engine)

    def query_by_genre(self, genre):
        return pd.read_sql('SELECT * FROM music WHERE genre = ?', self.engine, params=(genre,))

    def query_top_by_popularity(self, limit=10):
        return pd.read_sql('SELECT TOP (?) * FROM music ORDER BY popularity_score DESC', self.engine, params=(limit,))

    def get_genre_stats(self):
        return pd.read_sql('''
            SELECT genre, COUNT(*) AS album_count, AVG(rating) AS avg_rating,
                   SUM(rating_people) AS total_rating_people, AVG(popularity_score) AS avg_popularity
            FROM music WHERE genre != '未知' GROUP BY genre ORDER BY avg_popularity DESC
        ''', self.engine)

    def get_yearly_trend(self):
        df = pd.read_sql('''
            SELECT release_year, genre, COUNT(*) AS album_count
            FROM music
            WHERE release_year IS NOT NULL AND genre != '未知'
            GROUP BY release_year, genre
            ORDER BY release_year, genre
        ''', self.engine)
        return df

    def clear_all(self):
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM music"))
            conn.commit()

    # ---------- 用户管理 ----------
    def add_user(self, username, password_hash, role='user'):
        """添加新用户，返回 True/False"""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT 1 FROM users WHERE username = :username"), {"username": username})
            if result.fetchone():
                return False
            conn.execute(
                text("INSERT INTO users (username, password_hash, role, created_at) VALUES (:username, :pwd, :role, :created)"),
                {"username": username, "pwd": password_hash, "role": role,
                 "created": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
            )
            conn.commit()
            return True

    def get_user(self, username):
        """根据用户名获取用户信息（返回字典或None）"""
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, username, password_hash, role FROM users WHERE username = :username"),
                {"username": username}
            ).fetchone()
            if result:
                return {"id": result[0], "username": result[1], "password_hash": result[2], "role": result[3]}
            return None

    def get_user_by_id(self, user_id):
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, username, role FROM users WHERE id = :id"),
                {"id": user_id}
            ).fetchone()
            if result:
                return {"id": result[0], "username": result[1], "role": result[2]}
            return None

    def get_all_users(self):
        """获取所有用户（除密码外）"""
        return pd.read_sql("SELECT id, username, role, created_at FROM users ORDER BY id", self.engine)

    def delete_user(self, user_id):
        """删除用户（禁止删除管理员自身）"""
        with self.engine.connect() as conn:
            # 检查是否管理员
            user = self.get_user_by_id(user_id)
            if user and user['role'] == 'admin':
                return False  # 不允许删除管理员
            conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
            conn.commit()
            return True

    def update_user_role(self, user_id, new_role):
        """更新用户角色"""
        with self.engine.connect() as conn:
            # 不能修改最后一个管理员
            if new_role != 'admin':
                # 检查是否只剩一个管理员
                admin_count = conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin'")).scalar()
                user = self.get_user_by_id(user_id)
                if user and user['role'] == 'admin' and admin_count <= 1:
                    return False
            conn.execute(
                text("UPDATE users SET role = :role WHERE id = :id"),
                {"role": new_role, "id": user_id}
            )
            conn.commit()
            return True


if __name__ == '__main__':
    db = MusicDB(server='localhost', database='MusicAnalysis', trusted_connection=True)
    print("数据库初始化成功")