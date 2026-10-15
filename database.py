"""Nâng cấp các cột mới, giữ nguyên dữ liệu trong hotel.db của ZIP gốc."""
from sqlalchemy import inspect, text
from models import db, Booking
from datetime import timedelta


def nang_cap_du_lieu():
    cot_moi = {
        'user': {'phone': "VARCHAR(30) DEFAULT ''"},
        'booking': {
            'nightly_rate': 'FLOAT', 'source': "VARCHAR(20) DEFAULT 'online'",
            'deposit_amount': 'FLOAT DEFAULT 0', 'paid_amount': 'FLOAT DEFAULT 0',
            'payment_method': 'VARCHAR(20)', 'paid_at': 'TIMESTAMP',
            'room_checked': 'BOOLEAN DEFAULT FALSE', 'inspection_note': "VARCHAR(500) DEFAULT ''",
            'hold_until': 'DATE', 'cancel_reason': "VARCHAR(200) DEFAULT ''",
        }, 'service_request': {'cost': 'FLOAT DEFAULT 0'},
    }
    with db.engine.begin() as ket_noi:
        for bang, cac_cot in cot_moi.items():
            cot_cu = {cot['name'] for cot in inspect(ket_noi).get_columns(bang)}
            for ten, kieu in cac_cot.items():
                if ten not in cot_cu:
                    ket_noi.execute(text(f'ALTER TABLE "{bang}" ADD COLUMN "{ten}" {kieu}'))
    # Giá đã chốt lấy từ tổng tiền cũ, không lấy giá phòng vừa chỉnh sửa.
    for don in Booking.query.filter(Booking.hold_until.is_(None)).all():
        don.hold_until = don.check_out + timedelta(days=1)
        don.nightly_rate = don.total_price / max(1, (don.check_out-don.check_in).days)
    db.session.commit()
