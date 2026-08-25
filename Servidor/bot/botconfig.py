#   Archivo de configuración del bot de telegram
#   Autor: José Ramonda
#   Última modificación : 11/7/2026


# --- CONFIGURACIÓN DE RED Y TELEGRAM ---

import os

from pathlib import Path

TOKEN_PATH = Path("/home/jose/token.txt")

def get_telegram_token() -> str:
    if not TOKEN_PATH.is_file():
        raise FileNotFoundError(f"No se encontro el archivo de credenciales en {TOKEN_PATH}")
    return TOKEN_PATH.read_text().strip()

# Uso
TOKEN = get_telegram_token()

# Parámetros MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_BASE_TOPIC = "sbc/cmd"

#Nodos
DICCIONARIO_NODOS = {
    "0x0A": "Acceso Frente",
    "0x14": "Acceso Patio",
    "0x1E": "Acceso Bicicletero"
}




# Forzamos la obtención de la ruta absoluta del archivo config.py real
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Si por alguna razón el path quedó apuntando adentro de 'bot', subimos un nivel
if BASE_DIR.endswith('bot'):
    BASE_DIR = os.path.dirname(BASE_DIR)

# Ahora BASE_DIR es sí o sí ~/Proyecto/SBC puro
RUTA_PADRON_CSV = os.path.join(BASE_DIR, 'modulos', 'accesos_autorizados.csv')