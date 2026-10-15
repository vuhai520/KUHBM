from flask import Flask, request, session, abort, jsonify, flash, redirect, url_for
from flask_login import LoginManager, current_user, logout_user
from sqlalchemy.exc import IntegrityError
import secrets
import hmac
from config import Config
from models import db, bcrypt, User, hom_nay
from routes.auth import auth_bp
from routes.guest import guest_bp
from routes.reception import reception_bp
from routes.staff import staff_bp
from routes.admin import admin_bp
from routes.chat import chat_bp
from routes.messages import messages_bp

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=128*1024)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    bcrypt.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id)) if user_id.isdigit() else None

    @app.before_request
    def bao_ve_form():
        session.setdefault('csrf_token', secrets.token_hex(24))
        if current_user.is_authenticated and current_user.is_blocked:
            logout_user()
            abort(403)
        if request.method == 'POST':
            ma = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
            if not hmac.compare_digest(ma.encode(), session['csrf_token'].encode()):
                abort(400, description='Form hết hạn. Hãy tải lại trang.')

    @app.context_processor
    def bien_chung():
        return {'today_iso': hom_nay().isoformat(),
                'role_labels': {'guest':'Khách hàng','reception':'Lễ tân','service_staff':'Nhân viên dịch vụ','admin':'Quản lý'},
                'room_labels': {'single':'Phòng đơn','double':'Phòng đôi','suite':'Phòng suite'}}

    @app.errorhandler(ValueError)
    def loi_nhap_lieu(loi):
        db.session.rollback()
        if request.is_json:
            return jsonify(error=str(loi)), 400
        flash(str(loi), 'danger')
        return redirect(url_for('auth.dashboard') if current_user.is_authenticated else url_for('auth.index'))

    @app.errorhandler(IntegrityError)
    def loi_trung_du_lieu(loi):
        db.session.rollback()
        flash('Thông tin đã tồn tại hoặc dữ liệu liên kết chưa hợp lệ.', 'danger')
        return redirect(url_for('auth.dashboard') if current_user.is_authenticated else url_for('auth.index'))

    app.register_blueprint(auth_bp)
    app.register_blueprint(guest_bp)
    app.register_blueprint(reception_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(messages_bp)

    with app.app_context():
        db.create_all()
        from database import nang_cap_du_lieu
        nang_cap_du_lieu()
        # Auto-seed if database is empty (e.g. fresh Render deployment)
        if User.query.count() == 0:
            from seed import seed_db
            seed_db()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=False)
