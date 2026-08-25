#   Módulo MQTT Unificado para el Bot de Telegram (Optimizado)
#   Autor: José Ramonda

import os
import json
import asyncio
import paho.mqtt.client as mqtt
from telegram import Bot
import botconfig

DICCIONARIO_NODOS = {
    "0xa": "Acceso Frente",
    "0x14": "Acceso Patio",
    "0x1e": "Acceso Bicicletero"
}

_bot_inyector = Bot(token=botconfig.TELEGRAM_TOKEN)
_cliente_mqtt = None

# ----------------------------------------------------
# 1. ENVIAR COMANDOS AL MAIN (NO BLOQUEANTE)
# ----------------------------------------------------
def publicar_comando(accion, payload):
    """Publica el comando reutilizando el cliente global persistente"""
    global _cliente_mqtt
    if _cliente_mqtt is None:
        print(f"[BOT-MQTT ERROR] Cliente MQTT no inicializado al intentar publicar {accion}")
        return False
    try:
        topico = f"sbc/cmd/{accion}"
        # Publicacion inmediata: el loop de fondo gestiona el socket y el handshake
        _cliente_mqtt.publish(topico, payload, qos=1)
        print(f"[BOT-MQTT CMD ENVIADO] Topico: {topico} | Payload: {payload}")
        return True
    except Exception as e:
        print(f"[BOT-MQTT ERROR] Falló la publicación: {e}")
        return False

# ----------------------------------------------------
# 2. LISTENER Y DESPACHO DE NOTIFICACIONES
# ----------------------------------------------------
async def enviar_directo_sincrono(chat_id, evento, nombre_nodo, data):
    """Despacha Texto o Foto a Telegram"""
    async with _bot_inyector:
        nombre_coloquial = DICCIONARIO_NODOS.get(nombre_nodo, f"Nodo {nombre_nodo}")
        try:
            if evento == "puerta_ok":
                texto = f"Confirmado: El acceso {nombre_nodo} ha sido abierto de forma correcta."
                await _bot_inyector.send_message(chat_id=chat_id, text=texto)
                
            elif evento == "alerta":
                if data == "DESCONECTADO":
                    texto = f"ALERTA - {nombre_coloquial} desconectado"
                else:
                    texto = (
                        f"¡ALERTA CRITICA DE SEGURIDAD!\n\n"
                        f"Se ha detectado un intento de acceso con una tarjeta CLONADA.\n"
                        f"Titular: {data}\n"
                        f"Acceso: {nombre_nodo}\n\n"
                        f"La tarjeta implicada ha sido BLOQUEADA en el sistema automáticamente."
                    )
                await _bot_inyector.send_message(chat_id=chat_id, text=texto)

            elif evento == "foto_solicitada_ok":
                if os.path.exists(data):
                    with open(data, 'rb') as foto:
                        await _bot_inyector.send_photo(
                            chat_id=chat_id, 
                            photo=foto, 
                            caption=f"Captura de control solicitada para {nombre_nodo}."
                        )
                else:
                    await _bot_inyector.send_message(chat_id=chat_id, text=f"Error: Archivo no encontrado en {nombre_nodo}.")
                    
            elif evento == "foto_espontanea_ok":
                if os.path.exists(data):
                    with open(data, 'rb') as foto:
                        await _bot_inyector.send_photo(
                            chat_id=chat_id, 
                            photo=foto, 
                            caption=f"Alerta: Están tocando el timbre en {nombre_nodo}."
                        )
                else:
                    await _bot_inyector.send_message(chat_id=chat_id, text=f"Alerta: Timbre en {nombre_nodo} (Foto no disponible).")

            elif evento == "foto_error":
                await _bot_inyector.send_message(chat_id=chat_id, text=f"Alerta de hardware en {nombre_nodo}: Falló la cámara.\nDetalle: {data}")

            elif evento == "timbre_sin_foto":
                await _bot_inyector.send_message(chat_id=chat_id, text=f"Alerta: Timbre en {nombre_nodo} (Fallo de carga).")

        except Exception as e_envio:
            print(f"[BOT-MQTT ERROR] Error en envío a chat {chat_id}: {e_envio}")


def _on_message_notificaciones(client, userdata, msg):
    """Callback de recepción para notificaciones entrantes"""
    try:
        payload_dict = json.loads(msg.payload.decode("utf-8"))
        
        destino = payload_dict["destino"]
        evento = payload_dict["evento"]
        id_nodo = payload_dict["nodo"]  
        data = payload_dict["data"]
        
        nombre_nodo = DICCIONARIO_NODOS.get(id_nodo, id_nodo)
        print(f"[BOT-MQTT IN] Evento: {evento.upper()} | Nodo: {nombre_nodo} | Destino: {destino}")
        
        eventos_validos = ["puerta_ok", "foto_solicitada_ok", "foto_espontanea_ok", "foto_error", "timbre_sin_foto", "alerta"]
        if evento not in eventos_validos:
            return

        if destino == "all":
            from . import auth
            datos_credenciales = auth.cargar_datos()
            for usuario, datos in datos_credenciales.get("usuarios", {}).items():
                user_id_dinamico = datos.get("user_id")
                if user_id_dinamico:
                    asyncio.run(enviar_directo_sincrono(int(user_id_dinamico), evento, nombre_nodo, data))
        else:
            asyncio.run(enviar_directo_sincrono(int(destino), evento, nombre_nodo, data))
            
        print("[BOT-MQTT SUCCESS] Despachado a API de Telegram.")

        if evento in ["foto_solicitada_ok", "foto_espontanea_ok"] and os.path.exists(data):
            try:
                os.remove(data)
                print(f"[BOT-MQTT] Imagen temporal eliminada: {data}")
            except Exception as e_borrado:
                print(f"[BOT-MQTT ERROR] Fallo al eliminar archivo: {e_borrado}")

    except Exception as e:
        print(f"[BOT-MQTT ERROR] Error en callback de notificación: {e}")


def iniciar_escucha_notificaciones(app_telegram=None):
    """Inicializa la sesión MQTT persistente para comandos y notificaciones"""
    global _cliente_mqtt
    _cliente_mqtt = mqtt.Client()
    _cliente_mqtt.on_message = _on_message_notificaciones
    
    try:
        _cliente_mqtt.connect(botconfig.MQTT_BROKER, botconfig.MQTT_PORT, keepalive=60)
        _cliente_mqtt.subscribe("sbc/notify", qos=1)
        _cliente_mqtt.loop_start()
        print("[BOT-MQTT] Cliente MQTT persistente conectado y en escucha sobre 'sbc/notify'")
    except Exception as e:
        print(f"[BOT-MQTT ERROR] No se pudo conectar cliente MQTT global: {e}")