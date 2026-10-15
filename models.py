from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from sqlalchemy import text

db = SQLAlchemy()
bcrypt = Bcrypt()


def hom_nay():
    return datetime.now(timezone(timedelta(hours=7))).date()


def so_tien(gia_tri):
    """Tính tiền bằng Decimal, chỉ đổi sang float khi lưu cột cũ của dự án."""
    try:
        so = Decimal(str(gia_tri))
        if not so.is_finite() or so < 0 or so > 1000000000:
            raise ValueError
        return so.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('Số tiền phải hợp lệ, từ 0 đến 1 tỷ.')


def doc_ngay(ngay_nhan, ngay_tra):
    try:
        ci, co = date.fromisoformat(ngay_nhan), date.fromisoformat(ngay_tra)
    except (ValueError, TypeError):
        raise ValueError('Vui lòng chọn ngày nhận/trả hợp lệ.')
    if ci < hom_nay() or co < ci or (co-ci).days > 365:
        raise ValueError('Ngày nhận từ hôm nay; ngày trả >= ngày nhận, tối đa 365 ngày.')
    return ci, co


def khoa_ghi():
    """SQLite khóa ghi trước khi kiểm tra trùng. Route commit/rollback cả nhóm."""
    if db.engine.dialect.name == 'sqlite':
        db.session.execute(text('BEGIN IMMEDIATE'))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='guest')  # guest, reception, service_staff, admin
    is_blocked = db.Column(db.Boolean, default=False)
    phone = db.Column(db.String(30), default='')

    bookings = db.relationship('Booking', backref='guest', lazy=True)
    service_requests = db.relationship('ServiceRequest', backref='requester', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def co_the_chat(self, nguoi_nhan):
        quyen = {'guest': {'reception'}, 'reception': {'guest', 'admin', 'service_staff'},
                 'admin': {'reception', 'service_staff'}, 'service_staff': {'admin', 'reception'}}
        return (self.id != nguoi_nhan.id and not self.is_blocked and not nguoi_nhan.is_blocked
                and nguoi_nhan.role in quyen.get(self.role, set()))


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(10), unique=True, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # single, double, suite
    base_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='available')  # available, occupied, maintenance
    description = db.Column(db.String(300))

    bookings = db.relationship('Booking', backref='room', lazy=True)

    def co_trung_lich(self, ci, co):
        return Booking.query.filter(
            Booking.room_id == self.id, Booking.status.in_(['confirmed', 'checked_in', 'checked_out']),
            Booking.check_in < co + timedelta(days=1), Booking.hold_until > ci
        ).first() is not None

    def co_the_dat(self, ci, co):
        return (self.status != 'maintenance' and not self.co_trung_lich(ci, co)
                and (ci != hom_nay() or self.status == 'available'))

    def sua(self, loai, gia, mo_ta):
        if loai not in ('single', 'double', 'suite') or so_tien(gia) <= 0:
            raise ValueError('Chọn loại phòng và giá lớn hơn 0.')
        if len(mo_ta) > 300:
            raise ValueError('Mô tả tối đa 300 ký tự.')
        self.type, self.base_price, self.description = loai, float(so_tien(gia)), mo_ta


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='confirmed')  # confirmed, checked_in, checked_out, cancelled
    total_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    nightly_rate = db.Column(db.Float)
    source = db.Column(db.String(20), default='online')
    deposit_amount = db.Column(db.Float, default=0)
    paid_amount = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(20))
    paid_at = db.Column(db.DateTime)
    room_checked = db.Column(db.Boolean, default=False)
    inspection_note = db.Column(db.String(500), default='')
    hold_until = db.Column(db.Date)
    cancel_reason = db.Column(db.String(200), default='')

    service_requests = db.relationship('ServiceRequest', backref='booking', lazy=True)

    @property
    def so_dem(self):
        return max(1, (self.check_out-self.check_in).days)

    @property
    def phi_dich_vu(self):
        return sum((so_tien(r.cost or 0) for r in self.service_requests if r.status == 'completed'), Decimal('0.00'))

    @property
    def tong_tien(self):
        return so_tien(self.total_price) + self.phi_dich_vu

    @property
    def con_phai_thu(self):
        return max(Decimal('0.00'), self.tong_tien-so_tien(self.paid_amount or 0))

    @classmethod
    def tao(cls, khach, phong, ci, co, nguon='online'):
        if ci < hom_nay() or co < ci or (co-ci).days > 365:
            raise ValueError('Ngày đặt không hợp lệ.')
        if not phong.co_the_dat(ci, co):
            raise ValueError('Phòng không sẵn sàng hoặc trùng lịch/ngày dọn.')
        gia = so_tien(phong.base_price)
        tong = so_tien(gia * max(1, (co-ci).days))
        don = cls(user_id=khach.id, room_id=phong.id, check_in=ci, check_out=co,
                  total_price=float(tong), nightly_rate=float(gia), source=nguon,
                  deposit_amount=float((tong*Decimal('0.30')).quantize(Decimal('0.01')) if nguon == 'online' else 0),
                  paid_amount=0, hold_until=co+timedelta(days=1), status='confirmed')
        db.session.add(don)
        return don

    def xac_nhan_coc(self):
        if self.status != 'confirmed' or self.source != 'online' or (self.paid_amount or 0) > 0:
            raise ValueError('Đơn không cần xác nhận cọc hoặc đã được xác nhận.')
        self.paid_amount = self.deposit_amount

    def nhan_phong(self):
        if self.status != 'confirmed' or not self.check_in <= hom_nay() <= self.check_out:
            raise ValueError('Đơn chưa đúng thời gian nhận phòng.')
        if self.room.status != 'available':
            raise ValueError('Phòng chưa sẵn sàng; cần dọn hoặc xử lý khách đang ở trước.')
        if Booking.query.filter(Booking.room_id==self.room_id, Booking.id!=self.id,
                Booking.status=='checked_out', Booking.hold_until>hom_nay()).first():
            raise ValueError('Phòng vẫn trong khoảng giữ để dọn của đơn trước.')
        if so_tien(self.paid_amount or 0) < so_tien(self.deposit_amount or 0):
            raise ValueError('Khách chưa xác nhận cọc mô phỏng.')
        self.status, self.room.status = 'checked_in', 'occupied'

    def thanh_toan(self, cach_tra, tien_nhan):
        if self.status != 'checked_in' or self.paid_at:
            raise ValueError('Đơn chưa nhận phòng hoặc đã thanh toán.')
        if not self.room_checked:
            raise ValueError('Cần kiểm tra phòng trước khi thanh toán.')
        if any(r.status in ('pending', 'in_progress') for r in self.service_requests):
            raise ValueError('Cần hoàn tất hoặc hủy các yêu cầu dịch vụ trước khi chốt tiền.')
        if cach_tra not in ('cash', 'card', 'transfer'):
            raise ValueError('Phương thức thanh toán không hợp lệ.')
        can_thu = self.con_phai_thu
        tien_nhan = so_tien(tien_nhan)
        if tien_nhan < can_thu or (cach_tra != 'cash' and tien_nhan != can_thu):
            raise ValueError('Số tiền chưa đủ hoặc khác số phải thu đối với thẻ/chuyển khoản.')
        self.paid_amount = float(self.tong_tien)
        self.paid_at, self.payment_method, self.status = datetime.utcnow(), cach_tra, 'checked_out'
        self.hold_until = max(self.hold_until, hom_nay()+timedelta(days=1))
        self.room.status = 'cleaning'
        return tien_nhan-can_thu  # Tiền thừa trả lại; không cộng thừa vào doanh thu.


class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    type = db.Column(db.String(30), nullable=False)  # housekeeping, room_service, maintenance
    description = db.Column(db.String(500))
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, in_progress, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cost = db.Column(db.Float, default=0)

    def cap_nhat(self, trang_thai, chi_phi=None):
        if self.booking and self.booking.status != 'checked_in':
            raise ValueError('Đơn không đang lưu trú; không sửa phí sau khi đã thanh toán.')
        if trang_thai not in ('pending', 'in_progress', 'completed', 'cancelled'):
            raise ValueError('Trạng thái yêu cầu không hợp lệ.')
        if chi_phi is not None:
            self.cost = float(so_tien(chi_phi))
        if self.booking and trang_thai == 'completed':
            phi_khac = sum((so_tien(r.cost or 0) for r in self.booking.service_requests
                            if r.id != self.id and r.status == 'completed'), Decimal('0.00'))
            so_tien(so_tien(self.booking.total_price) + phi_khac + so_tien(self.cost or 0))
        self.status, self.updated_at = trang_thai, datetime.utcnow()
        if self.booking:
            self.booking.room_checked = False


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    body = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship('User', foreign_keys=[sender_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])
