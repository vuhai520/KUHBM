"""Chat giữa người dùng, tách khỏi chat AI Gemini."""
from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from models import db, User, Message

messages_bp = Blueprint('messages', __name__, url_prefix='/messages')


def nguoi_nhan_hop_le(user_id):
    nguoi = User.query.get_or_404(user_id)
    if not current_user.co_the_chat(nguoi):
        abort(403)
    return nguoi


def hoi_thoai(nguoi):
    return Message.query.filter(or_(
        and_(Message.sender_id==current_user.id, Message.recipient_id==nguoi.id),
        and_(Message.sender_id==nguoi.id, Message.recipient_id==current_user.id)))


@messages_bp.get('/')
@login_required
def index():
    lien_he = [n for n in User.query.filter_by(is_blocked=False).order_by(User.name).all() if current_user.co_the_chat(n)]
    return render_template('messages.html', contacts=lien_he, recipient=None, messages=[])


@messages_bp.get('/<int:user_id>')
@login_required
def thread(user_id):
    nguoi = nguoi_nhan_hop_le(user_id)
    lien_he = [n for n in User.query.filter_by(is_blocked=False).order_by(User.name).all() if current_user.co_the_chat(n)]
    tin_nhan = hoi_thoai(nguoi).order_by(Message.id.desc()).limit(100).all()[::-1]
    return render_template('messages.html', contacts=lien_he, recipient=nguoi, messages=tin_nhan)


@messages_bp.get('/<int:user_id>/updates')
@login_required
def updates(user_id):
    nguoi = nguoi_nhan_hop_le(user_id)
    sau = max(0, request.args.get('after', 0, type=int))
    cac_tin = hoi_thoai(nguoi).filter(Message.id>sau).order_by(Message.id).limit(100).all()
    return jsonify(messages=[{'id': t.id, 'mine': t.sender_id==current_user.id, 'body': t.body,
                              'time': t.created_at.isoformat()+'Z'} for t in cac_tin])


@messages_bp.post('/<int:user_id>/send')
@login_required
def send(user_id):
    nguoi = nguoi_nhan_hop_le(user_id)
    du_lieu = request.get_json(silent=True) or {}
    if not isinstance(du_lieu, dict):
        return jsonify(error='Dữ liệu tin nhắn không hợp lệ.'), 400
    noi_dung = du_lieu.get('message', '')
    if not isinstance(noi_dung, str) or not 1 <= len(noi_dung.strip()) <= 2000:
        return jsonify(error='Tin nhắn cần 1–2.000 ký tự.'), 400
    tin = Message(sender_id=current_user.id, recipient_id=nguoi.id, body=noi_dung.strip())
    db.session.add(tin)
    db.session.commit()
    return jsonify(ok=True), 201
