"""
Authentication blueprint for user management
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models.auth import User, LoginLog, db
from forms import LoginForm, SignupForm, ChangePasswordForm, UserManagementForm, CreateUserForm
from datetime import datetime
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def log_user_login(user, request):
    """Log user login"""
    login_log = LoginLog()
    login_log.user_id = user.id
    login_log.login_time = datetime.utcnow()
    login_log.ip_address = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    login_log.user_agent = request.headers.get('User-Agent')
    db.session.add(login_log)
    
    # Update user's last login time
    user.last_login = datetime.utcnow()
    db.session.commit()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        if current_user.first_login:
            return redirect(url_for('auth.change_password'))
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account is inactive. Please contact administrator.', 'error')
                return render_template('auth/login.html', form=form)
            
            login_user(user, remember=form.remember_me.data)
            log_user_login(user, request)
            
            # Check if first time login
            if user.first_login:
                flash('Please change your password on first login.', 'info')
                return redirect(url_for('auth.change_password'))
            
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = SignupForm()
    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.set_password(form.password.data)
        user.active = False  # Inactive by default
        user.first_login = True
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Your account is pending admin approval.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/signup.html', form=form)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            current_user.first_login = False
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Current password is incorrect', 'error')
    
    return render_template('auth/change_password.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    flash(f'Goodbye, {current_user.username}!', 'info')
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/admin/users')
@login_required
@admin_required
def user_management():
    """User management page for admin"""
    users = User.query.all()
    return render_template('auth/user_management.html', users=users)

@auth_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user page"""
    user = User.query.get_or_404(user_id)
    form = UserManagementForm()
    
    if form.validate_on_submit():
        # Prevent admin from deactivating themselves
        if user.id == current_user.id and form.active.data == '0':
            flash('You cannot deactivate your own account!', 'error')
            return render_template('auth/edit_user.html', form=form, user=user)
        
        user.username = form.username.data
        user.email = form.email.data
        user.active = form.active.data == '1'
        user.is_admin = form.is_admin.data
        db.session.commit()
        flash(f'User {user.username} updated successfully!', 'success')
        return redirect(url_for('auth.user_management'))
    
    # Pre-populate form
    form.username.data = user.username
    form.email.data = user.email
    form.active.data = '1' if user.active else '0'
    form.is_admin.data = user.is_admin
    
    return render_template('auth/edit_user.html', form=form, user=user)

@auth_bp.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create new user page"""
    form = CreateUserForm()
    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.set_password(form.password.data)
        user.active = form.active.data
        user.is_admin = form.is_admin.data
        user.first_login = True
        
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.username} created successfully!', 'success')
        return redirect(url_for('auth.user_management'))
    
    return render_template('auth/create_user.html', form=form)

@auth_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'error')
        return redirect(url_for('auth.user_management'))
    
    # Prevent deleting the last admin
    admin_count = User.query.filter_by(is_admin=True).count()
    if user.is_admin and admin_count <= 1:
        flash('Cannot delete the last admin user!', 'error')
        return redirect(url_for('auth.user_management'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} deleted successfully!', 'success')
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/admin/login-logs')
@login_required
@admin_required
def login_logs():
    """View login logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs = LoginLog.query.join(User).order_by(LoginLog.login_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('auth/login_logs.html', logs=logs)
