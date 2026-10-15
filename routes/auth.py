from urllib.parse import urlsplit
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Room, doc_ngay

auth_bp = Blueprint('auth', __name__)


def trang_sau_dang_nhap(user):
    """Giữ lịch khách vừa chọn, chỉ cho chuyển tới trang đặt phòng nội bộ."""
    dich = request.values.get('next', '')
    try:
        tach = urlsplit(dich)
        if (user.role == 'guest' and dich.startswith('/') and not dich.startswith('//')
                and not tach.scheme and not tach.netloc and tach.path == '/guest/book'
                and '\\' not in dich and not any(ord(k) < 32 for k in dich)):
            return dich
    except ValueError:
        pass
    vai_tro = {'guest':'guest.dashboard', 'reception':'reception.dashboard',
               'service_staff':'staff.dashboard', 'admin':'admin.dashboard'}
    return url_for(vai_tro.get(user.role, 'guest.dashboard'))


@auth_bp.get('/')
def index():
    bo_loc = {k: request.args.get(k, '').strip() for k in ('check_in','check_out','room_type')}
    rooms = Room.query.filter(Room.status!='maintenance').order_by(Room.base_price, Room.number).all()
    da_tim = bool(bo_loc['check_in'] or bo_loc['check_out'])
    try:
        if bo_loc['room_type'] and bo_loc['room_type'] not in ('single','double','suite'):
            raise ValueError('Vui lòng chọn loại phòng hợp lệ.')
        if bo_loc['room_type']:
            rooms = [p for p in rooms if p.type == bo_loc['room_type']]
        if da_tim:
            ci, co = doc_ngay(bo_loc['check_in'], bo_loc['check_out'])
            rooms = [p for p in rooms if p.co_the_dat(ci, co)]
    except ValueError as loi:
        flash(str(loi), 'warning')
        rooms = []
    return render_template('home.html', public_page=True, rooms=rooms, filters=bo_loc, searched=da_tim)


@auth_bp.get('/workspace')
@login_required
def dashboard():
    # Khu vực làm việc riêng, trang / luôn dành cho giới thiệu phòng.
    vai_tro = {'guest':'guest.dashboard', 'reception':'reception.dashboard',
               'service_staff':'staff.dashboard', 'admin':'admin.dashboard'}
    return redirect(url_for(vai_tro.get(current_user.role, 'guest.dashboard')))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(trang_sau_dang_nhap(current_user))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if user.is_blocked:
                flash('Tài khoản đã bị khóa. Vui lòng liên hệ lễ tân.', 'danger')
                return render_template('auth/login.html')
            login_user(user)
            return redirect(trang_sau_dang_nhap(user))
        flash('Email hoặc mật khẩu chưa đúng.', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(trang_sau_dang_nhap(current_user))
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        if not 2 <= len(name) <= 100 or not 3 <= len(email) <= 120 or '@' not in email or not 6 <= len(password.encode()) <= 72:
            flash('Vui lòng nhập họ tên, email và mật khẩu hợp lệ (6–72 byte).', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(email=email).first():
            flash('Email đã được đăng ký.', 'danger')
            return render_template('auth/register.html')
        user = User(name=name, email=email, role='guest')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Đã tạo tài khoản. Chào mừng bạn!', 'success')
        return redirect(trang_sau_dang_nhap(user))
    return render_template('auth/register.html')


@auth_bp.get('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('auth.index'))
