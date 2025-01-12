import cv2

# Configurações de vídeo
VIDEO_SETTINGS = {
    'WIDTH': 640,
    'HEIGHT': 480,
    'FPS': 30,
    'SOURCE': 0,  # 0 para webcam padrão
}

# Configuração da fonte de vídeo
VIDEO_SOURCE = VIDEO_SETTINGS['SOURCE']

# Configurações de detecção
FALL_DETECTION_SETTINGS = {
    'CONFIDENCE_THRESHOLD': 0.5,
    'FALL_DURATION_THRESHOLD': 1.0,     # segundos
    'HEIGHT_CHANGE_THRESHOLD': 0.3,     # % da altura do frame
    'HORIZONTAL_THRESHOLD': 0.15,       # diferença máxima entre ombro e quadril
    'FETAL_POSITION_THRESHOLD': 0.2,    # distância máxima entre joelho e quadril
    'HISTORY_SIZE': 10                  # frames para análise
}
