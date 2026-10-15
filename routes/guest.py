from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import db, Room, Booking, ServiceRequest, doc_ngay, khoa_ghi

guest_bp = Blueprint('guest', __name__, url_prefix='/guest')


def guest_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'guest': abort(403)
        return f(*args, **kwargs)
    return decorated


@guest_bp.get('/dashboard')
@login_required
@guest_required
def dashboard():
    return render_template('guest/dashboard.html',
        bookings=Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).limit(3).all(),
        requests=ServiceRequest.query.filter_by(user_id=current_user.id).order_by(ServiceRequest.created_at.desc()).limit(3).all())


@guest_bp.get('/book')
@login_required
@guest_required
def book():
    ci_chuoi, co_chuoi = request.args.get('check_in'), request.args.get('check_out')
    loai = request.args.get('room_type', '')
    cac_phong = None
    if ci_chuoi or co_chuoi:
        ci, co = doc_ngay(ci_chuoi, co_chuoi)
        cac_phong = [p for p in Room.query.order_by(Room.number).all()
                     if (not loai or p.type == loai) and p.co_the_dat(ci, co)]
    return render_template('guest/book.html', rooms=cac_phong, check_in=ci_chuoi, check_out=co_chuoi, room_type=loai)


@guest_bp.post('/book/confirm/<int:room_id>')
@login_required
@guest_required
def confirm_booking(room_id):
    ci, co = doc_ngay(request.form.get('check_in'), request.form.get('check_out'))
    khoa_ghi()
    phong = Room.query.filter_by(id=room_id).with_for_update().first_or_404()
    Booking.tao(current_user, phong, ci, co)
    db.session.commit()
    flash('Đã đặt phòng. Hãy bấm xác nhận cọc mô phỏng 30% trong My Bookings.', 'success')
    return redirect(url_for('guest.bookings'))


@guest_bp.get('/bookings')
@login_required
@guest_required
def bookings():
    return render_template('guest/bookings.html', bookings=Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all())


@guest_bp.post('/bookings/<int:booking_id>/deposit')
@login_required
@guest_required
def deposit(booking_id):
    from routes.reception import lay_don_khoa
    don = lay_don_khoa(booking_id)
    if don.user_id != current_user.id: abort(403)
    don.xac_nhan_coc()
    db.session.commit()
    flash('Đã xác nhận cọc mô phỏng; không có chuyển tiền thật.', 'success')
    return redirect(url_for('guest.bookings'))


@guest_bp.post('/bookings/<int:booking_id>/cancel')
@login_required
@guest_required
def cancel_booking(booking_id):
    from routes.reception import lay_don_khoa
    don = lay_don_khoa(booking_id)
    if don.user_id != current_user.id: abort(403)
    if don.status != 'confirmed': raise ValueError('Chỉ hủy được đơn chưa nhận phòng.')
    don.status, don.cancel_reason = 'cancelled', 'Khách yêu cầu hủy'
    db.session.commit()
    flash('Đã hủy đơn. Cọc chỉ mô phỏng, không cần hoàn tiền thật.', 'success')
    return redirect(url_for('guest.bookings'))


@guest_bp.route('/services', methods=['GET', 'POST'])
@login_required
@guest_required
def services():
    if request.method == 'POST':
        khoa_ghi()
        don = Booking.query.filter_by(user_id=current_user.id, status='checked_in').first()
        if not don: raise ValueError('Bạn cần nhận phòng trước khi yêu cầu dịch vụ.')
        # Cùng khóa với thanh toán để không thêm phí sau khi đã chốt đơn.
        Room.query.filter_by(id=don.room_id).with_for_update().one()
        db.session.refresh(don)
        if don.status != 'checked_in': raise ValueError('Đơn đã trả phòng.')
        loai, mo_ta = request.form.get('type'), request.form.get('description','').strip()
        if loai not in ('housekeeping','room_service','maintenance') or not 1 <= len(mo_ta) <= 500:
            raise ValueError('Chọn loại yêu cầu và nhập mô tả 1–500 ký tự.')
        db.session.add(ServiceRequest(user_id=current_user.id, booking_id=don.id, type=loai, description=mo_ta, cost=0))
        don.room_checked = False
        db.session.commit()
        flash('Đã gửi yêu cầu tới nhân viên/lễ tân.', 'success')
        return redirect(url_for('guest.services'))
    return render_template('guest/services.html', requests=ServiceRequest.query.filter_by(user_id=current_user.id).order_by(ServiceRequest.created_at.desc()).all())
