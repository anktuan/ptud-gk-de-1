from flask import Flask, render_template, request, redirect, url_for, make_response
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = Flask(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            content TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS follows (
            user_id INTEGER,
            post_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            post_id INTEGER,
            message TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_token TEXT UNIQUE,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts LIMIT ? OFFSET ?', (per_page, offset))
    posts = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) FROM posts')
    total_posts = cursor.fetchone()[0]
    conn.close()
    return render_template('index.html', posts=posts, total_posts=total_posts, per_page=per_page, page=page)

@app.route('/add_post', methods=['POST'])
def add_post():
    user_id = get_user_id_from_session()
    if not user_id:
        return redirect(url_for('login'))
    
    title = request.form['title']
    content = request.form['content']
    image_url = request.form['image_url']
    
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO posts (title, content, image_url) VALUES (?, ?, ?)', 
                      (title, content, image_url))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return "Error adding post", 500
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    content = request.form['content']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO comments (post_id, content) VALUES (?, ?)', (post_id, content))
    conn.commit()

    # Notify users who follow the post
    cursor.execute('SELECT user_id FROM follows WHERE post_id = ?', (post_id,))
    followers = cursor.fetchall()
    for follower in followers:
        cursor.execute('INSERT INTO notifications (user_id, post_id, message) VALUES (?, ?, ?)', (follower[0], post_id, 'New comment on a post you follow.'))
    
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/follow/<int:post_id>', methods=['POST'])
def follow_post(post_id):
    user_id = get_user_id_from_session()
    if not user_id:
        return redirect(url_for('login'))
    
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        # Kiểm tra xem đã follow chưa
        cursor.execute('SELECT * FROM follows WHERE user_id = ? AND post_id = ?', 
                      (user_id, post_id))
        if cursor.fetchone():
            return "Already following", 400
            
        cursor.execute('INSERT INTO follows (user_id, post_id) VALUES (?, ?)', 
                      (user_id, post_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return "Error following post", 500
    finally:
        conn.close()
    return redirect(url_for('index'))

def get_user_id_from_session():
    session_token = request.cookies.get('session_token')
    if session_token:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM sessions WHERE session_token = ?', (session_token,))
        user = cursor.fetchone()
        conn.close()
        return user[0] if user else None
    return None

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    if user and check_password_hash(user[2], password):
        session_token = secrets.token_hex(16)
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sessions (user_id, session_token) VALUES (?, ?)', (user[0], session_token))
        conn.commit()
        conn.close()
        response = redirect(url_for('index'))
        response.set_cookie('session_token', session_token)
        return response
    return "Login Failed", 401

@app.route('/logout')
def logout():
    session_token = request.cookies.get('session_token')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE session_token = ?', (session_token,))
    conn.commit()
    conn.close()
    response = redirect(url_for('index'))
    response.delete_cookie('session_token')
    return response

@app.route('/notifications')
def notifications():
    user_id = get_user_id_from_session()
    if user_id:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM notifications WHERE user_id = ?', (user_id,))
        user_notifications = cursor.fetchall()
        conn.close()
        return render_template('notifications.html', notifications=user_notifications)
    return redirect(url_for('index'))

@app.route('/search')
def search():
    query = request.args.get('query')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts WHERE title LIKE ? OR content LIKE ?', ('%' + query + '%', '%' + query + '%'))
    results = cursor.fetchall()
    conn.close()
    return render_template('search_results.html', results=results)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)