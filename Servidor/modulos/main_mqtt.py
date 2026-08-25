#   Módulo de Comunicación MQTT para el Proceso Principal (SBC Hardware)
#   Autor: José Ramonda
#   Modificado: 13/7/2026

#   Módulo MQTT Rústico de Control
#   Autor: José Ramonda
#   Fecha: 13/7/2026

import paho.mqtt.client as mqtt
import config
from . import accesos

from . import nexo


cliente_sbc = mqtt.Client()




def publicar_mensaje(topico, payload):
    """Publica usando el cliente global ya conectado. NO BLOQUEA EL HILO."""
    global cliente_sbc
    try:
        # Al publicar sobre el cliente que ya ejecuta loop_forever(),
        # la librería Paho gestiona la salida inmediatamente sin bloquear.
        cliente_sbc.publish(topico, payload, qos=1)
        print(f"[MQTT PUB SUCCESS] {topico} -> {payload}")
        return True
    except Exception as e:
        print(f"[MQTT PUB ERROR] No se pudo publicar: {e}")
        return False

#Listener
def _on_message(client, userdata, msg):
    """El switch-case donde derivás cada acción según el tópico"""
    topico = msg.topic
    payload_crudo = msg.payload.decode("utf-8") # Recibe: "0x0A,987654321"
    
    # Si el payload contiene una coma, lo podamos para quedarnos solo con el nodo
    if "," in payload_crudo:
        nodo = payload_crudo.split(",")[0] # Se queda con "0x0A"
    else:
        nodo = payload_crudo # Por si acaso llega un mensaje viejo sin chat_id
    # Convertimos los bytes del payload a string para operar cómodos
    
    nodo = int(nodo, 16) if nodo.startswith("0x") else int(nodo)
    
    # --- ACÁ ESTÁ TU SWITCH-CASE ---
    if topico == "sbc/cmd/abrir":
        print(f"[ACCION] Ejecutando apertura del nodo {nodo} por bus serie...")
        nexo.encolar(nodo,config.CMD_DOOR,b"")
        
    elif topico == "sbc/cmd/foto":
        print(f"[ACCION] Encolando pedido de fotografia para el nodo {nodo}...")
        nexo.encolar(nodo,config.CMD_TAKE_PH,b"")
        
    elif topico == "sbc/cmd/progmode":

        nexo.encolar(nodo, config.CMD_PROGMODE, b"") 
        print(f"[MQTT->SERIE] Encolado CMD_PROGMODE [START] para el nodo {nodo}")

    elif topico == "sbc/cmd/actualiza":
        accesos.cargar_padron_a_ram()


    elif topico == "sbc/cmd/ip_solicitud":
        # Por si el bot te pide la IP de un nodo en caliente
        print(f"[ACCION] Bot solicita IP. Buscando y respondiendo...")
        # ip_encontrada = nexo.obtener_ip_nodo(payload)
        # publicar_mensaje("sbc/nodo/ip_respuesta", ip_encontrada)
        


    else:
        print(f"[MQTT WARN] Tópico sin handler asignado: {topico}")





def arrancar_listener_global():
    """Conecta el cliente global y lo deja escuchando en su hilo"""
    global cliente_sbc
    cliente_sbc.on_message = _on_message
    
    try:
        cliente_sbc.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
        cliente_sbc.subscribe("sbc/cmd/#", qos=1)
        print("[MQTT LISTENER] Cliente global conectado y escuchando 'sbc/#'")
        
        # loop_forever() maneja la red, reconexiones y el procesamiento de envíos
        cliente_sbc.loop_forever()
        
    except Exception as e:
        print(f"[MQTT ERROR] Falló el listener global: {e}")