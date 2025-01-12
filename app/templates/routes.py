from flask import Blueprint, render_template, Response, jsonify, request
import cv2
from app.detection.utils import process_frame
from app.detection import fall_detector
from app.detection.video import get_video_capture
import psutil
from datetime import datetime, timedelta

main = Blueprint('main', __name__)


def gen_frames():
    cap = get_video_capture()
    if cap is None:
        return

    try:
        while True:
            success, frame = cap.read()
            if not success:
                break
            else:
                # Processar o frame com a detecção
                processed_frame = process_frame(frame)

                # Converter para formato JPEG para streaming
                ret, buffer = cv2.imencode('.jpg', processed_frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    finally:
        cap.release()


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@main.route('/status')
def get_status():
    # Verificar se alguma pessoa está caída
    any_fallen = any(person_data.get('is_fallen', False)
                     for person_data in fall_detector.people_tracking.values())

    # Verificar se algum alerta foi enviado
    any_alert = any(person_data.get('alert_sent', False)
                    for person_data in fall_detector.people_tracking.values())

    return {
        'fall_detected': any_fallen,
        'alert_sent': any_alert
    }


@main.route('/update_settings', methods=['POST'])
def update_settings():
    settings = request.json
    # Atualizar configurações do detector
    fall_detector.update_settings(settings)
    return jsonify({'status': 'success'})


@main.route('/get_logs')
def get_logs():
    # Implementar recuperação de logs se necessário
    return jsonify({'logs': fall_detector.get_logs()})


@main.route('/system_stats')
def system_stats():
    # Coletar estatísticas do sistema
    cpu_usage = psutil.cpu_percent()

    # Obter FPS atual
    current_fps = fall_detector.get_fps()

    # Coletar estatísticas de detecção
    stats = fall_detector.get_stats()

    return jsonify({
        'cpu_usage': cpu_usage,
        'fps': current_fps,
        'total_detections': stats['total_detections'],
        'detections_per_hour': stats['detections_per_hour']
    })
