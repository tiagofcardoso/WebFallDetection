import cv2
import os
from config import VIDEO_SETTINGS, VIDEO_SOURCE


def get_video_capture():
    """Inicializa e configura a captura de vídeo"""
    max_attempts = 3
    cap = None

    for attempt in range(max_attempts):
        try:
            cap = cv2.VideoCapture(VIDEO_SOURCE)
            if not cap.isOpened():
                if attempt < max_attempts - 1:
                    print(f"Attempt {attempt + 1} failed, retrying...")
                    continue
                raise Exception(f"Could not open camera {VIDEO_SOURCE}")

            # Configurar propriedades da câmera
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_SETTINGS['WIDTH'])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_SETTINGS['HEIGHT'])
            cap.set(cv2.CAP_PROP_FPS, VIDEO_SETTINGS['FPS'])

            # Verificar configurações
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))

            # Testar frames
            for _ in range(3):
                ret, frame = cap.read()
                if not ret:
                    raise Exception("Failed to grab test frames")

            print(f"Camera initialized: {frame_width}x{
                  frame_height} @ {fps}fps")
            return cap

        except Exception as e:
            if attempt == max_attempts - 1:
                raise Exception(f"Failed to initialize camera: {str(e)}")
            if cap is not None:
                cap.release()

    return None
