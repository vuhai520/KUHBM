"""Chat GPT / local API tương thích OpenAI. Cấu hình trong .env, không đưa key vào HTML."""
import json
import logging
from urllib.parse import urlsplit
from flask import Blueprint, render_template, request, jsonify, session, abort, current_app
from flask_login import login_required, current_user
from models import Room

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


def bao_loi_chat(chi_tiet, status=503):
    # Chi tiết cấu hình chỉ ghi ở server, không gửi tới giao diện khách.
    logging.getLogger(__name__).warning('Trợ lý chưa khả dụng: %s', chi_tiet)
    return jsonify(response='Trợ lý hiện chưa thể trả lời. Bạn vui lòng thử lại sau hoặc nhắn lễ tân để được hỗ trợ.'), status


def cau_hinh_token(model, hostname):
    """Hỗ trợ cả .env cũ điền 1000 và tên trường của API."""
    truong = str(current_app.config.get('OPENAI_TOKEN_PARAMETER', '')).strip()
    gioi_han = str(current_app.config.get('OPENAI_MAX_OUTPUT_TOKENS', '')).strip()
    if truong.isdecimal():
        gioi_han = gioi_han or truong
        truong = ''
    try:
        so_token = int(gioi_han or '1024')
    except ValueError:
        raise ValueError('OPENAI_MAX_OUTPUT_TOKENS cần là số nguyên 1–16384.')
    if not 1 <= so_token <= 16384:
        raise ValueError('OPENAI_MAX_OUTPUT_TOKENS cần nằm trong khoảng 1–16384.')
    if not truong:
        ten = model.rsplit('/', 1)[-1].lower()
        gpt_moi = ten.startswith(('gpt-5', 'gpt-6', 'o1', 'o3', 'o4'))
        truong = 'max_completion_tokens' if hostname == 'api.openai.com' or gpt_moi else 'max_tokens'
    if truong not in ('max_tokens', 'max_completion_tokens'):
        raise ValueError('OPENAI_TOKEN_PARAMETER chỉ nhận tên trường hoặc số nguyên dương.')
    return truong, so_token


def khong_ho_tro_truong(loi, truong):
    """Chỉ thử trường khác khi API báo rõ trường token không được hỗ trợ."""
    noi_dung = getattr(loi, 'body', None)
    if not isinstance(noi_dung, dict):
        return False
    noi_dung = noi_dung.get('error', noi_dung)
    if not isinstance(noi_dung, dict):
        return False
    ma = str(noi_dung.get('code', '')).lower()
    thong_bao = str(noi_dung.get('message', '')).lower()
    khong_ho_tro = ma in ('unsupported_parameter', 'unknown_parameter', 'unrecognized_parameter') or any(
        tu in thong_bao for tu in ('unsupported', 'not supported', 'unrecognized', 'unknown parameter'))
    return khong_ho_tro and (noi_dung.get('param') == truong or truong in thong_bao)


@chat_bp.get('/')
@login_required
def index():
    if current_user.role != 'guest': abort(403)
    return render_template('guest/chat.html')


@chat_bp.post('/send')
@login_required
def send():
    if current_user.role != 'guest': abort(403)
    du_lieu = request.get_json(silent=True) or {}
    if not isinstance(du_lieu, dict):
        return jsonify(response='Dữ liệu câu hỏi không hợp lệ.'), 400
    noi_dung = du_lieu.get('message', '')
    if not isinstance(noi_dung, str) or not 1 <= len(noi_dung.strip()) <= 500:
        return jsonify(response='Câu hỏi cần 1–500 ký tự.'), 400

    dia_chi = current_app.config.get('OPENAI_BASE_URL', '').strip().rstrip('/')
    model = current_app.config.get('OPENAI_MODEL', '').strip()
    khoa = current_app.config.get('OPENAI_API_KEY', '').strip()
    try:
        url = urlsplit(dia_chi)
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError
        url.port  # Kiểm tra định dạng cổng nếu có.
    except ValueError:
        return bao_loi_chat('OPENAI_BASE_URL không hợp lệ.')
    if url.path.rstrip('/').endswith('/chat/completions'):
        return bao_loi_chat('Bỏ /chat/completions khỏi OPENAI_BASE_URL.')
    if not model:
        return bao_loi_chat('Chưa cấu hình OPENAI_MODEL.')
    if not khoa:
        if url.hostname in ('localhost', '127.0.0.1', '::1'):
            # SDK bắt buộc có chuỗi key; server local không xác thực có thể bỏ qua key mẫu này.
            khoa = 'local-no-key'
        else:
            return bao_loi_chat('Chưa cấu hình OPENAI_API_KEY.')

    try:
        truong_token, so_token = cau_hinh_token(model, url.hostname)
    except ValueError as loi:
        return bao_loi_chat(str(loi))

    # Chỉ đọc thông tin phòng công khai, không gửi email, điện thoại hoặc đơn riêng.
    phong = [{'number': p.number, 'type': p.type, 'price': p.base_price}
             for p in Room.query.filter(Room.status!='maintenance').all()]
    huong_dan = (
        'Giới thiệu là Trợ lý khách sạn KUHBM. Chỉ tư vấn thông tin lưu trú, '
        'không tự nêu tên nhà cung cấp, tên model hoặc chi tiết triển khai. '
        'Trả lời ngắn gọn theo ngôn ngữ của khách. Giá là AED. '
        'Ngày trả >= ngày nhận, cùng ngày tính một đêm. Có một ngày dọn sau ngày trả, không tính tiền. '
        'Đặt online cọc mô phỏng 30%, khách tự bấm xác nhận. Mọi thu tiền trong bài đều mô phỏng. '
        'Thông tin phòng dưới đây không chứa lịch trống; hướng dẫn dùng Book a Room để kiểm tra lịch. '
        'Khách mở Tin nhắn để trao đổi với lễ tân. Không tự đặt, thu tiền hoặc thay đổi dữ liệu. '
        'Thông tin phòng công khai: ' + json.dumps(phong, ensure_ascii=False)
    )
    lich_su = session.get('assistant_history', [])
    from openai import OpenAI, AuthenticationError, NotFoundError, RateLimitError, APIConnectionError, APITimeoutError, BadRequestError
    try:
        # Chat Completions dùng chung được cho OpenAI và local API cùng chuẩn.
        with OpenAI(api_key=khoa, base_url=dia_chi, timeout=60.0, max_retries=0) as client:
            tham_so = {'model': model, 'messages': [
                {'role': 'system', 'content': huong_dan}, *lich_su,
                {'role': 'user', 'content': noi_dung.strip()}]}
            try:
                ket_qua = client.chat.completions.create(**tham_so, **{truong_token: so_token})
            except BadRequestError as loi:
                if not khong_ho_tro_truong(loi, truong_token):
                    raise
                truong_khac = 'max_tokens' if truong_token == 'max_completion_tokens' else 'max_completion_tokens'
                ket_qua = client.chat.completions.create(**tham_so, **{truong_khac: so_token})
        tra_loi = ket_qua.choices[0].message.content if ket_qua.choices else None
        if not isinstance(tra_loi, str) or not tra_loi.strip():
            return bao_loi_chat('Không có nội dung văn bản trong phản hồi.', 502)
        lich_su += [{'role': 'user', 'content': noi_dung.strip()}, {'role': 'assistant', 'content': tra_loi[:500]}]
        while lich_su and len(json.dumps(lich_su).encode()) > 2000:
            lich_su = lich_su[2:]
        session['assistant_history'] = lich_su
        return jsonify(response=tra_loi)
    except AuthenticationError:
        thong_bao = 'API từ chối key. Kiểm tra OPENAI_API_KEY của đúng server đang dùng.'
    except NotFoundError:
        thong_bao = 'Không tìm thấy endpoint/model. Kiểm tra OPENAI_BASE_URL và OPENAI_MODEL.'
    except RateLimitError:
        thong_bao = 'API đang giới hạn lượt gọi hoặc quota. Hãy kiểm tra server/tài khoản API.'
    except APITimeoutError:
        return bao_loi_chat('Hết thời gian chờ sau 60 giây.', 504)
    except APIConnectionError:
        thong_bao = 'Không kết nối được API. Hãy bật local server và kiểm tra địa chỉ/cổng trong OPENAI_BASE_URL.'
    except BadRequestError:
        thong_bao = ('Server không nhận cấu hình gửi lên. Kiểm tra model và OPENAI_TOKEN_PARAMETER '
                     '(max_tokens hoặc max_completion_tokens).')
    except Exception as loi:
        # Chỉ ghi loại lỗi, không ghi key, câu hỏi hoặc phản hồi riêng vào log.
        logging.getLogger(__name__).warning('Chat API: %s', type(loi).__name__)
        thong_bao = 'API chat tạm thời không khả dụng. Bạn vẫn có thể nhắn trực tiếp lễ tân.'
    return bao_loi_chat(thong_bao)
