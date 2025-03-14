from flask import Blueprint, render_template, request, flash, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from .models import User, db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user:
            if user.blocked:
                flash('Tài khoản của bạn đã bị khóa', category='warning')
                return redirect(url_for('auth.login'))
            elif check_password_hash(user.password, password):
                flash('Đăng nhập thành công!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Mật khẩu không đúng, thử lại lần nữa', category='error')
        else:
            flash('Tài khoản hiện chưa được đăng ký', category='error')

    data = request.form
    print(data)

    return render_template('login.html', user=current_user)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter((User.username == username) | (User.email == email)).first()

        if user:
            flash('Tài khoản hoặc email đã được sử dụng!', category='error')
        elif len(username) < 3:
            flash('Tên tài khoản phải có ít nhất 3 ký tự', category='error')
        elif len(password1) < 5:
            flash('Mật khẩu phải có tối thiểu 5 ký tự', category='error')
        elif password1 != password2:
            flash('Mật khẩu không đồng nhất', category='error')
        else:
            try:
                new_user = User(
                    username=username,
                    email=email,
                    password=generate_password_hash(password1, method='pbkdf2:sha256')
                )
                db.session.add(new_user)
                db.session.commit()
                flash('Tạo tài khoản thành công!', category='success')

                login_user(new_user)
                return redirect(url_for('views.home'))
            except Exception as e:
                db.session.rollback()
                flash('Đã xảy ra lỗi khi tạo tài khoản!', category='error')

    return render_template('register.html', user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.home'))