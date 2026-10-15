from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, ServiceRequest, Room, khoa_ghi
from datetime import datetime

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')


def staff_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ['service_staff', 'admin']:
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated


@staff_bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    pending = ServiceRequest.query.filter_by(status='pending').order_by(ServiceRequest.created_at).all()
    in_progress = ServiceRequest.query.filter_by(status='in_progress').order_by(ServiceRequest.created_at).all()
    completed = ServiceRequest.query.filter_by(status='completed').order_by(ServiceRequest.updated_at.desc()).limit(10).all()
    return render_template('staff/dashboard.html',
                           pending=pending,
                           in_progress=in_progress,
                           completed=completed, rooms=Room.query.filter_by(status='cleaning').all())


@staff_bp.route('/requests/<int:req_id>/update', methods=['POST'])
@login_required
@staff_required
def update_request(req_id):
    from routes.reception import lay_don_khoa
    sr = ServiceRequest.query.get_or_404(req_id)
    if sr.booking_id:
        lay_don_khoa(sr.booking_id)
        db.session.refresh(sr)
    sr.cap_nhat(request.form.get('status'))
    db.session.commit()
    flash('Đã cập nhật yêu cầu.', 'success')
    return redirect(url_for('staff.dashboard'))


@staff_bp.post('/rooms/<int:room_id>/clean')
@login_required
@staff_required
def clean_room(room_id):
    khoa_ghi()
    phong = Room.query.filter_by(id=room_id).with_for_update().first_or_404()
    if phong.status != 'cleaning': raise ValueError('Phòng không đang chờ dọn.')
    phong.status = 'available'
    db.session.commit()
    flash('Đã dọn xong, vẫn giữ đủ một ngày dọn trong lịch.', 'success')
    return redirect(url_for('staff.dashboard'))
