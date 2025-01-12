def send_alert(message=None):
    """
    Função simplificada de alerta que apenas imprime a mensagem
    """
    if message is None:
        message = "ALERT: Fall detected! Person needs help!"

    print(f"ALERT: {message}")
    return True
