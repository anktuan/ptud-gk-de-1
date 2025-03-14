import os
import requests
from flask import Blueprint, render_template, url_for, flash, redirect, request
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from blog import db
from blog.models import User, Post, Comment, Follow

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)

# Auth routes
@auth.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('auth.register'))
        
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main.home'))
        else:
            flash('Invalid username or password')
            
    return render_template('login.html')

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))

# Main routes
@main.route("/")
@main.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=6)
    return render_template('home.html', posts=posts)

@main.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        # Get random image from picsum
        image_url = f"https://picsum.photos/800/400?random={Post.query.count() + 1}"
        
        post = Post(
            title=title,
            content=content,
            image_url=image_url,
            author=current_user
        )
        db.session.add(post)
        db.session.commit()
        
        return redirect(url_for('main.home'))
    
    return render_template('create_post.html')

@main.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)

@main.route("/post/<int:post_id>/comment", methods=['POST'])
@login_required
def comment_post(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content')
    
    comment = Comment(
        content=content,
        post=post,
        author=current_user
    )
    db.session.add(comment)
    db.session.commit()
    
    return redirect(url_for('main.post', post_id=post.id))

@main.route("/post/<int:post_id>/follow", methods=['POST'])
@login_required
def follow_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if not Follow.query.filter_by(user_id=current_user.id, post_id=post.id).first():
        follow = Follow(follower=current_user, post=post)
        db.session.add(follow)
        db.session.commit()
        flash('You are now following this post!')
    
    return redirect(url_for('main.post', post_id=post.id))

@main.route("/post/<int:post_id>/unfollow", methods=['POST'])
@login_required
def unfollow_post(post_id):
    follow = Follow.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first_or_404()
    
    db.session.delete(follow)
    db.session.commit()
    flash('You have unfollowed this post.')
    
    return redirect(url_for('main.post', post_id=post_id))
