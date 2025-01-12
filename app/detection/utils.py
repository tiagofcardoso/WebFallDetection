import cv2
import mediapipe as mp
import numpy as np
from .alert import send_alert
from config import FALL_DETECTION_SETTINGS
from datetime import datetime, timedelta
import time
from ultralytics import YOLO


class FallDetector:
    def __init__(self):
        self.people_tracking = {}  # Dicionário para rastrear cada pessoa
        self.track_timeout = 30
        self.immobility_duration = 5.0  # 5 segundos para confirmar queda
        self.fps_history = []
        self.last_frame_time = time.time()
        self.detections_history = []

        # Inicializar modelos
        print("Initializing models...")
        self.model = YOLO("yolo11x.pt")
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Classes de objetos relevantes
        self.furniture_classes = {
            56: 'chair',
            57: 'couch',
            59: 'bed',
            60: 'dining table'
        }

    def get_person_id(self, box_coords, frame_width, frame_height):
        """Gera um ID único baseado na posição relativa da pessoa"""
        x1, y1, x2, y2 = box_coords
        center_x = (x1 + x2) / (2 * frame_width)
        center_y = (y1 + y2) / (2 * frame_height)

        # Procurar pessoa mais próxima no rastreamento
        min_dist = float('inf')
        closest_id = None
        current_time = time.time()

        # Limpar rastreamentos antigos
        self.people_tracking = {
            pid: data for pid, data in self.people_tracking.items()
            if current_time - data['last_seen'] < self.track_timeout
        }

        for pid, data in self.people_tracking.items():
            dist = np.sqrt((center_x - data['position'][0])**2 +
                           (center_y - data['position'][1])**2)
            if dist < min_dist and dist < 0.3:  # Threshold de distância
                min_dist = dist
                closest_id = pid

        if closest_id is None:
            closest_id = len(self.people_tracking)

        return closest_id

    def is_falling(self, pose_landmarks, prev_landmarks=None, nearby_furniture=None):
        if not pose_landmarks:
            return False, 0

        # Extrair landmarks principais
        landmarks = {
            'nose': pose_landmarks.landmark[self.mp_pose.PoseLandmark.NOSE],
            'left_shoulder': pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_SHOULDER],
            'right_shoulder': pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_SHOULDER],
            'left_hip': pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_HIP],
            'right_hip': pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_HIP],
            'left_ankle': pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_ANKLE],
            'right_ankle': pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_ANKLE]
        }

        # Calcular posições médias
        mid_shoulder = [(landmarks['left_shoulder'].x + landmarks['right_shoulder'].x)/2,
                        (landmarks['left_shoulder'].y + landmarks['right_shoulder'].y)/2]
        mid_hip = [(landmarks['left_hip'].x + landmarks['right_hip'].x)/2,
                   (landmarks['left_hip'].y + landmarks['right_hip'].y)/2]
        mid_ankle = [(landmarks['left_ankle'].x + landmarks['right_ankle'].x)/2,
                     (landmarks['left_ankle'].y + landmarks['right_ankle'].y)/2]

        ground_score = 0

        # Verificar distância do chão
        body_parts_near_ground = 0
        for part in ['nose', 'left_shoulder', 'right_shoulder']:
            if abs(landmarks[part].y - mid_ankle[1]) < 0.3:
                body_parts_near_ground += 1
                ground_score += 20

        # Verificar se está em um móvel adequado para deitar/sentar
        if nearby_furniture:
            for furniture in nearby_furniture:
                if furniture['type'] in ['couch', 'bed']:
                    # Verificar se a pessoa está em posição compatível com o móvel
                    nose_height = landmarks['nose'].y
                    hip_height = (
                        landmarks['left_hip'].y + landmarks['right_hip'].y) / 2
                    furniture_top = furniture['box'][1] / \
                        frame_height  # Normalizar altura

                    # Se a pessoa está na altura do móvel
                    if abs(hip_height - furniture_top) < 0.2:
                        # Movimento controlado indica ação intencional
                        if prev_landmarks is not None:
                            movement = np.linalg.norm(
                                np.array([landmarks['nose'].y]) - prev_landmarks)
                            if movement < 0.04:  # Movimento suave
                                return False, 0  # Não é queda, é deitar/sentar
                        else:
                            # Se já está na posição, provavelmente está deitado/sentado
                            return False, 0

        # Verificar velocidade de queda (apenas se não estiver em móvel)
        if prev_landmarks is not None:
            movement = np.linalg.norm(
                np.array([landmarks['nose'].y]) - prev_landmarks)

            if movement > 0.05:  # Movimento rápido para baixo
                if not any(f['type'] in ['couch', 'bed'] for f in (nearby_furniture or [])):
                    ground_score += 35

                    # Verificar se está próximo ao chão após movimento rápido
                    nose_height = landmarks['nose'].y
                    ankle_height = mid_ankle[1]
                    if abs(nose_height - ankle_height) < 0.3:
                        ground_score += 25

        # Verificar orientação do corpo
        vertical_alignment = abs(mid_shoulder[1] - mid_hip[1])
        is_horizontal = vertical_alignment < 0.15

        if is_horizontal:
            if not nearby_furniture:  # Apenas pontuar se não estiver em móvel
                ground_score += 30

                # Verificar altura em relação ao chão
                avg_height = (mid_shoulder[1] + mid_hip[1]) / 2
                if avg_height - mid_ankle[1] < 0.2:  # Muito próximo ao chão
                    ground_score += 25

        # Verificar assimetria do corpo (quedas tendem a ser assimétricas)
        shoulder_asymmetry = abs(
            landmarks['left_shoulder'].y - landmarks['right_shoulder'].y)
        hip_asymmetry = abs(landmarks['left_hip'].y - landmarks['right_hip'].y)
        if shoulder_asymmetry > 0.1 or hip_asymmetry > 0.1:
            ground_score += 15

        # Critérios mais rigorosos para queda
        is_fall = (
            ground_score > 70 and  # Score alto
            body_parts_near_ground >= 2 and  # Partes próximas ao chão
            # Não está em móvel
            not any(f['type'] in ['couch', 'bed'] for f in (nearby_furniture or [])) and
            # Realmente próximo ao chão
            abs(landmarks['nose'].y - mid_ankle[1]) < 0.3
        )

        return is_fall, ground_score

    def detect_fall(self, frame):
        if frame is None:
            return frame

        height, width = frame.shape[:2]
        results = self.model(frame)
        people_detected = False  # Flag para indicar se alguma pessoa foi detectada

        if len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                if box.cls.cpu().numpy()[0] == 0:  # pessoa
                    conf = box.conf.cpu().numpy()[0]
                    if conf > 0.5:
                        people_detected = True  # Pessoa detectada com confiança suficiente
                        x1, y1, x2, y2 = map(int, box.xyxy.cpu().numpy()[0])

                        # Identificar pessoa
                        person_id = self.get_person_id(
                            (x1, y1, x2, y2), width, height)

                        # Inicializar dados da pessoa se não existirem
                        if person_id not in self.people_tracking:
                            self.people_tracking[person_id] = {
                                'position': ((x1 + x2)/(2*width), (y1 + y2)/(2*height)),
                                'last_seen': time.time(),
                                'fall_start_time': None,
                                'is_fallen': False,
                                'prev_nose_pos': None,
                                'alert_sent': False
                            }

                        person_data = self.people_tracking[person_id]

                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pose_results = self.pose.process(rgb_frame)

                        if pose_results.pose_landmarks:
                            current_nose_pos = np.array([
                                pose_results.pose_landmarks.landmark[
                                    self.mp_pose.PoseLandmark.NOSE].y
                            ])

                            # Detectar móveis próximos
                            nearby_furniture = self.detect_furniture(
                                frame, (x1, y1, x2, y2))

                            is_on_ground, ground_score = self.is_falling(
                                pose_results.pose_landmarks,
                                person_data.get('prev_nose_pos'),
                                nearby_furniture
                            )

                            current_time = time.time()
                            if is_on_ground:
                                if not person_data['fall_start_time']:
                                    person_data['fall_start_time'] = current_time
                                    status_text = f"Person {
                                        person_id}: Possible fall..."
                                    box_color = (0, 255, 255)
                                else:
                                    immobility_time = current_time - \
                                        person_data['fall_start_time']
                                    if immobility_time >= self.immobility_duration:
                                        if not person_data['is_fallen']:
                                            person_data['is_fallen'] = True
                                            if not person_data['alert_sent']:
                                                self.detections_history.append(
                                                    datetime.now())
                                                send_alert(
                                                    f"Person {person_id} has fallen!")
                                                person_data['alert_sent'] = True

                                        status_text = f"Person {person_id}: FALLEN! {
                                            int(immobility_time)}s"
                                        box_color = (0, 0, 255)
                                    else:
                                        status_text = f"Person {person_id}: Analyzing... {
                                            int(immobility_time)}s"
                                        box_color = (0, 255, 255)
                            else:
                                person_data['fall_start_time'] = None
                                person_data['is_fallen'] = False
                                person_data['alert_sent'] = False
                                status_text = f"Person {person_id}: Monitoring"
                                box_color = (0, 255, 0)

                            # Atualizar dados de rastreamento
                            person_data.update({
                                'prev_nose_pos': current_nose_pos,
                                'last_seen': current_time
                            })

                            # Desenhar retângulo e texto
                            cv2.rectangle(frame, (x1, y1),
                                          (x2, y2), box_color, 2)
                            cv2.putText(frame, status_text, (x1, y1-10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, box_color, 2)

                            # Opcional: Visualizar móveis detectados
                            for furniture in nearby_furniture:
                                fx1, fy1, fx2, fy2 = furniture['box']
                                cv2.rectangle(frame, (fx1, fy1),
                                              (fx2, fy2), (255, 255, 0), 1)
                                cv2.putText(frame, furniture['type'], (fx1, fy1-5),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

        # Se nenhuma pessoa foi detectada, limpar todos os estados
        if not people_detected:
            self.people_tracking.clear()  # Limpar rastreamento
            # Desenhar status de "No people detected"
            cv2.putText(frame, "No people detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        return frame

    def detect_furniture(self, frame, person_box):
        """Detecta móveis próximos à pessoa"""
        results = self.model(frame)
        x1_person, y1_person, x2_person, y2_person = person_box
        person_bottom = y2_person
        person_center = (x1_person + x2_person) / 2

        nearby_furniture = []

        if len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls.cpu().numpy()[0])
                if cls_id in self.furniture_classes:
                    x1, y1, x2, y2 = map(int, box.xyxy.cpu().numpy()[0])
                    furniture_center = (x1 + x2) / 2

                    # Verificar proximidade horizontal
                    horizontal_distance = abs(person_center - furniture_center)
                    is_near_horizontally = horizontal_distance < (
                        x2 - x1) * 0.7

                    # Verificar relação vertical
                    vertical_relation = abs(person_bottom - y1)
                    is_near_vertically = vertical_relation < 50  # Ajustável

                    if is_near_horizontally and is_near_vertically:
                        nearby_furniture.append({
                            'type': self.furniture_classes[cls_id],
                            'box': (x1, y1, x2, y2),
                            'height': y2 - y1,
                            'class_id': cls_id,
                            'distance': horizontal_distance
                        })

        return sorted(nearby_furniture, key=lambda x: x['distance'])


# Instância global do detector
fall_detector = FallDetector()


def process_frame(frame):
    if frame is None:
        return None
    return fall_detector.detect_fall(frame)
