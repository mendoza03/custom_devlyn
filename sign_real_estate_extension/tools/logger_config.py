import sys
from loguru import logger as _logger

def configure_logger(log_format = False):
    """
        Configura el logger para que muestre los mensajes en la consola.
        :param log_format: Formato del mensaje de log por default es: "<level>{time:YYYY-MM-DD HH:mm:ss.SSS}</level> | <level>{level: <8}</level> | <level>{name}</level>:<level>{function}</level>:<level>{line}</level> - <level>{message}</level>"
        :return: logger
    """
    _logger.remove()  # Elimina cualquier configuración previa
    if not log_format:
        log_format = "<level>{time:YYYY-MM-DD HH:mm:ss.SSS}</level> | <level>{level: <8}</level> | <level>{name}</level>:<level>{function}</level>:<level>{line}</level> - <level>{message}</level>"
    _logger.add(sys.stdout, format=log_format, catch=True, colorize=True)
    return _logger
