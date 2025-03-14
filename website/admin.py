from flask import Blueprint, render_template, request, jsonify, url_for, flash, redirect
from flask_login import login_required, current_user
from .models import User
from . import db

admin = Blueprint('admin', __name__)

@admin.route('/manage-users')
@login_required
def manage_users():
    if not current_user.is_admin:
        flash("Bạn không có quyền truy cập trang này.", "warning")
        return redirect(url_for('views.home'))
    
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=10)
    return render_template('manage_users.html', users=users)

@admin.route('/toggle_user_status/<int:user_id>', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    user.blocked = not user.blocked
    db.session.commit()
    return jsonify(success=True, new_status="active" if not user.blocked else "blocked")
