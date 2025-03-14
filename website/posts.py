from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import current_user, login_required
from .models import Post, db

posts = Blueprint('posts', __name__)

@posts.route('/post/<string:slug>')
def post_detail(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    return render_template('post_detail.html', post=post, user=current_user)

@posts.route('/manage-posts')
@login_required
def manage_posts():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    if current_user.is_admin:
        posts = Post.query.order_by(Post.updated_at.desc()) \
                        .paginate(page=page, per_page=per_page, error_out=False)
    else:
        posts = Post.query.filter_by(user_id=current_user.id) \
                        .order_by(Post.updated_at.desc()) \
                        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('manage_posts.html', user=current_user, posts=posts)

@posts.route('/delete-posts', methods=['POST'])
@login_required
def delete_posts():
    post_ids = request.form.getlist('post_ids')
    if post_ids:
        if current_user.is_admin:
            Post.query.filter(Post.id.in_(post_ids)).delete(synchronize_session=False)
        else:
            Post.query.filter(Post.id.in_(post_ids), Post.user_id == current_user.id).delete(synchronize_session=False)
        db.session.commit()
        flash(f'Đã xóa {len(post_ids)} bài viết thành công', 'success')
    else:
        flash('Vui lòng chọn ít nhất một bài viết để xóa', 'warning')

    return redirect(url_for('posts.manage_posts'))

@posts.route('/create-post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        image_url = request.form.get('image_url')
        flow = request.form.get('flow')

        if not title or not content:
            flash('Tiêu đề và nội dung không được để trống', 'error')
            return redirect(url_for('posts.create_post'))

        new_post = Post(
            title=title, 
            content=content, 
            image_url=image_url,
            flow=flow,
            user_id=current_user.id
        )
        db.session.add(new_post)
        db.session.commit()
        flash('Bài viết đã được tạo thành công!', 'success')
        return redirect(url_for('posts.manage_posts'))

    return render_template('create_post.html', user=current_user)

@posts.route('/edit-post/<string:slug>', methods=['GET', 'POST'])
@login_required
def edit_post(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        image_url = request.form.get('image_url')
        flow = request.form.get('flow')

        if not title or not content:
            flash('Tiêu đề và nội dung không được để trống', 'error')
            return redirect(url_for('posts.edit_post', slug=slug))

        post.title = title
        post.content = content
        post.image_url = image_url
        post.flow = flow
        db.session.commit()
        flash('Bài viết đã được cập nhật!', 'success')
        return redirect(url_for('posts.manage_posts'))

    return render_template('edit_post.html', post=post, user=current_user)

@posts.route('/api/posts')
def get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 10, type=int)
    get_all = request.args.get('all', 'false') == 'true'

    if get_all:
        pagination = Post.query.order_by(Post.updated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    else:
        pagination = Post.query.filter_by(user_id=current_user.id).order_by(Post.updated_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    posts_data = [
        {
            'id': post.id,
            'title': post.title,
            'updated_at': post.updated_at.strftime('%d/%m/%Y'),
            'content': post.content[:100],
            'slug': post.slug,
            'author': post.author.username,
            'image_url': post.image_url,
            'flow': post.flow
        }
        for post in pagination.items
    ]

    return jsonify({
        'posts': posts_data,
        'has_next': pagination.has_next
    })
