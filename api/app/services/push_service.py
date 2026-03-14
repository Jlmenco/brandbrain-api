"""
Push Notification Service — envia notificacoes via Expo Push API.
Documentacao: https://docs.expo.dev/push-notifications/sending-notifications/
"""
import logging
import httpx

logger = logging.getLogger("app.push")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_push(token: str, title: str, body: str, data: dict | None = None) -> bool:
    """
    Envia uma push notification para um dispositivo via Expo Push API.
    Retorna True se enviado com sucesso, False caso contrario.
    """
    if not token or not token.startswith("ExponentPushToken["):
        logger.debug("Token invalido ou vazio, ignorando push: %s", token)
        return False

    payload = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "data": data or {},
    }

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                EXPO_PUSH_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            result = resp.json()
            # Expo retorna {"data": {"status": "ok"}} ou {"data": {"status": "error", ...}}
            status = result.get("data", {}).get("status", "")
            if status == "ok":
                logger.info("Push enviado para %s: %s", token[:30], title)
                return True
            else:
                logger.warning("Push falhou para %s: %s", token[:30], result)
                return False
    except httpx.HTTPError as e:
        logger.error("Erro HTTP ao enviar push: %s", str(e))
        return False


def send_push_to_users(users: list, title: str, body: str, data: dict | None = None) -> int:
    """
    Envia push para uma lista de usuarios que tenham push_token registrado.
    Retorna o numero de envios bem-sucedidos.
    """
    sent = 0
    for user in users:
        token = getattr(user, "push_token", None)
        if token and send_push(token, title, body, data):
            sent += 1
    return sent
