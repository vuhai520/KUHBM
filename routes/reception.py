"""Lễ tân: đặt tại quầy, nhận phòng, kiểm phòng, tính tiền và xử lý yêu cầu."""
from functools import wraps
import secrets
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from models import db, Booking, Room, User, ServiceRequest, doc_ngay, khoa_ghi

reception_bp = Blueprint('reception', __name__, url_prefix='/reception')


def reception_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ('reception', 'admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def lay_don_khoa(booking_id):
    khoa_ghi()
    don = Booking.query.get_or_404(booking_id)
    Room.query.filter_by(id=don.room_id).populate_existing().with_for_update().one()
    return Booking.query.filter_by(id=booking_id).populate_existing().with_for_update().one()


@reception_bp.get('/dashboard')
@login_required
@reception_required
def dashboard():
    return render_template('reception/dashboard.html', bookings=Booking.query.order_by(Booking.created_at.desc()).all(),
                           rooms=Room.query.order_by(Room.number).all())


@reception_bp.route('/book', methods=['GET', 'POST'])
@login_required
@reception_required
def book():
    if request.method == 'POST':
        ci, co = doc_ngay(request.form.get('check_in'), request.form.get('check_out'))
        khoa_ghi()
        phong = Room.query.filter_by(id=request.form.get('room_id', type=int)).with_for_update().first_or_404()
        ma_khach = request.form.get('guest_id', type=int)
        if ma_khach:
            khach = User.query.filter_by(id=ma_khach, role='guest', is_blocked=False).first_or_404()
        else:
            ten, phone = request.form.get('guest_name', '').strip(), request.form.get('phone', '').strip()
            if not 2 <= len(ten) <= 100 or len(phone) > 30:
                raise ValueError('Nhập tên khách 2–100 ký tự, điện thoại tối đa 30 ký tự.')
            # Khách lẻ tại quầy không cần email thật hay tài khoản đăng nhập.
            khach = User(name=ten, phone=phone, email=f'walkin-{secrets.token_hex(12)}@hotel.invalid', role='guest')
            khach.set_password(secrets.token_urlsafe(32))
            db.session.add(khach)
            db.session.flush()
        don = Booking.tao(khach, phong, ci, co, 'counter')
        db.session.commit()
        flash('Đã đặt tại quầy, giá đã chốt theo số đêm.', 'success')
        return redirect(url_for('reception.bill', booking_id=don.id))
    return render_template('reception/book.html', rooms=Room.query.filter(Room.status!='maintenance').all(),
                           guests=User.query.filter_by(role='guest', is_blocked=False).all())


@reception_bp.get('/availability')
@login_required
@reception_required
def availability():
    ci, co = doc_ngay(request.args.get('check_in'), request.args.get('check_out'))
    return jsonify(rooms=[{'id': p.id, 'number': p.number, 'type': p.type, 'price': p.base_price}
                          for p in Room.query.order_by(Room.number).all() if p.co_the_dat(ci, co)])


@reception_bp.post('/checkin/<int:booking_id>')
@login_required
@reception_required
def checkin(booking_id):
    don = lay_don_khoa(booking_id)
    don.nhan_phong()
    db.session.commit()
    flash('Đã nhận phòng.', 'success')
    return redirect(url_for('reception.bill', booking_id=booking_id))


@reception_bp.post('/checkout/<int:booking_id>')
@login_required
@reception_required
def checkout(booking_id):
    # Không bỏ qua kiểm phòng/thanh toán như nút check-out cũ.
    Booking.query.get_or_404(booking_id)
    return redirect(url_for('reception.bill', booking_id=booking_id))


@reception_bp.get('/bill/<int:booking_id>')
@login_required
@reception_required
def bill(booking_id):
    return render_template('reception/bill.html', booking=Booking.query.get_or_404(booking_id))


@reception_bp.post('/inspect/<int:booking_id>')
@login_required
@reception_required
def inspect_room(booking_id):
    don = lay_don_khoa(booking_id)
    if don.status != 'checked_in':
        raise ValueError('Chỉ kiểm tra phòng của khách đang lưu trú.')
    ghi_chu = request.form.get('note', '').strip()
    if len(ghi_chu) > 500:
        raise ValueError('Ghi chú tối đa 500 ký tự.')
    don.room_checked, don.inspection_note = True, ghi_chu
    db.session.commit()
    flash('Đã ghi nhận kiểm tra phòng.', 'success')
    return redirect(url_for('reception.bill', booking_id=booking_id))


@reception_bp.post('/pay/<int:booking_id>')
@login_required
@reception_required
def pay(booking_id):
    don = lay_don_khoa(booking_id)
    tien_thua = don.thanh_toan(request.form.get('method'), request.form.get('received'))
    db.session.commit()
    flash(f'Đã thanh toán mô phỏng và trả phòng. Tiền thừa: AED {tien_thua:.2f}. Phòng chờ dọn.', 'success')
    return redirect(url_for('reception.bill', booking_id=booking_id))


@reception_bp.post('/cancel/<int:booking_id>')
@login_required
@reception_required
def cancel(booking_id):
    don = lay_don_khoa(booking_id)
    if don.status != 'confirmed':
        raise ValueError('Chỉ hủy đơn chưa nhận phòng.')
    don.status, don.cancel_reason = 'cancelled', request.form.get('reason', '').strip()[:200] or 'Hủy tại quầy'
    db.session.commit()
    flash('Đã hủy đơn; cọc trong bài chỉ là mô phỏng.', 'success')
    return redirect(url_for('reception.dashboard'))


@reception_bp.route('/requests', methods=['GET', 'POST'])
@login_required
@reception_required
def requests_view():
    if request.method == 'POST':
        don = lay_don_khoa(request.form.get('booking_id', type=int))
        loai, mo_ta = request.form.get('type'), request.form.get('description', '').strip()
        if don.status != 'checked_in' or loai not in ('housekeeping','room_service','maintenance') or not 1 <= len(mo_ta) <= 500:
            raise ValueError('Chọn đơn đang ở, loại yêu cầu và mô tả 1–500 ký tự.')
        db.session.add(ServiceRequest(user_id=don.user_id, booking_id=don.id, type=loai, description=mo_ta, cost=0))
        don.room_checked = False
        db.session.commit()
        flash('Đã tiếp nhận yêu cầu của khách.', 'success')
        return redirect(url_for('reception.requests_view'))
    return render_template('reception/requests.html', requests=ServiceRequest.query.order_by(ServiceRequest.created_at.desc()).all(),
                           active=Booking.query.filter_by(status='checked_in').all())


@reception_bp.post('/requests/<int:req_id>/update')
@login_required
@reception_required
def update_request(req_id):
    sr = ServiceRequest.query.get_or_404(req_id)
    if sr.booking_id:
        lay_don_khoa(sr.booking_id)
        db.session.refresh(sr)
    sr.cap_nhat(request.form.get('status'), request.form.get('cost', '0'))
    db.session.commit()
    flash('Đã cập nhật yêu cầu và phí dịch vụ.', 'success')
    return redirect(url_for('reception.requests_view'))


@reception_bp.post('/rooms/<int:room_id>/clean')
@login_required
@reception_required
def clean_room(room_id):
    khoa_ghi()
    phong = Room.query.filter_by(id=room_id).with_for_update().first_or_404()
    if phong.status != 'cleaning':
        raise ValueError('Phòng không đang chờ dọn.')
    phong.status = 'available'
    db.session.commit()
    flash('Đã dọn xong. Khoảng giữ thêm một ngày vẫn được bảo toàn.', 'success')
    return redirect(url_for('reception.dashboard'))
