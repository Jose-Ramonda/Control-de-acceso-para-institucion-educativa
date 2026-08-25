#   Modulo de funciones de sincronización de nodos qe gestiona reconexiones a la red
#   Autor: José Ramonda
#   Ultima modificación: 10/7/2026

import time
import config
from .nexo import encolar


def fragmentar_y_encolar_string(id_nodo, subcomando, texto_puro, chunk_size=8):
    """
    Parte un string en pedazos y los encola usando el sub-protocolo:
    Format: subcomando (1B) | chunk_actual (1B) | chunks_totales (1B) | data (NB)
    """
    data_bytes = texto_puro.encode('utf-8')
    total_bytes = len(data_bytes)
    
    # Calculamos cuántos fragmentos van a ser
    if total_bytes == 0:
        chunks_totales = 1
    else:
        chunks_totales = (total_bytes + chunk_size - 1) // chunk_size

    for i in range(chunks_totales):
        inicio = i * chunk_size
        fin = inicio + chunk_size
        chunk_data = data_bytes[inicio:fin]
        
        # Armamos el encabezado del sub-protocolo
        header = bytes([subcomando, i + 1, chunks_totales])
        payload_final = header + chunk_data
        
        # Mandamos al nexo para que lo meta en la cola física del nodo
        encolar(id_nodo, config.CMD_WIFI, payload_final)
        time.sleep(0.05)  # Pequeño delay para no saturar el buffer del driver serial


def sincronizar_red_nodos():
    """Despacha IPs, Puertos y Credenciales fragmentadas al levantar el servidor"""
    print("[CRON - SYNC] Iniciando secuencia de sincronización de red por el bus...")

    # 1. Parsear la IP del servidor a 4 bytes independientes
    # "192.168.1.45" -> [192, 168, 1, 45]
    ip_bytes = bytes(int(b) for b in config.SERVER_IP_LAN.split("."))
    
    # 2. Parsear el puerto de Node-RED (1880) a 2 bytes (High byte, Low byte)
    puerto = config.SERVER_PORT_HTTP
    puerto_bytes = bytes([puerto >> 8, puerto & 0xFF])
    
    # Subcomando 0x03: Configuración del socket de destino del servidor
    # Payload: Subcomando (1B) | ChunkAct (1B) | ChunkTot (1B) | IP (4B) | Puerto (2B)
    payload_server = bytes([0x03, 0x01, 0x01]) + ip_bytes + puerto_bytes

    for id_nodo in config.NODOS_ID:
        # A) Enviamos los parámetros del servidor web (IP y Puerto)
        encolar(id_nodo, config.CMD_WIFI, payload_server)
        
        # B) Enviamos el SSID fragmentado (Subcomando 0x01)
        fragmentar_y_encolar_string(id_nodo, subcomando=0x01, texto_puro=config.WIFI_SSID)
        
        # C) Enviamos la Contraseña fragmentada (Subcomando 0x02)
        fragmentar_y_encolar_string(id_nodo, subcomando=0x02, texto_puro=config.WIFI_PASS)

    print("[CRON - SYNC] Configuración de red empaquetada y encolada con éxito.")


def cron_task():
    """Hilo de vigilancia horaria"""
    print("[CRON] Hilo temporal acoplado.")
    
    # Sincronizamos las tiqueteras ni bien arranca el proceso principal
    sincronizar_red_nodos()
    
    wifi_encendido_hoy = False
    wifi_apagado_hoy = False
    
    while True:
        try:
            ahora = time.localtime()
            hora = ahora.tm_hour
            minuto = ahora.tm_min
            
            # 07:30 AM -> Conectar WiFi (Subcomando 0x04 | 0x01 (Encender))
            if hora == 7 and minuto == 30 and not wifi_encendido_hoy:
                print("[CRON] 07:30 AM: Conectando WiFi en las camaras...")
                for id_nodo in config.NODOS_ID:
                    encolar(id_nodo, config.CMD_WIFI, bytes([0x04, 0x01, 0x01, 0x01]))
                wifi_encendido_hoy = True
                wifi_apagado_hoy = False
            
            # 18:30 PM -> Desconectar WiFi (Subcomando 0x04 | 0x00 (Apagar))
            elif hora == 18 and minuto == 30 and not wifi_apagado_hoy:
                print("[CRON] 18:30 PM: Apagando WiFi de las camaras...")
                for id_nodo in config.NODOS_ID:
                    encolar(id_nodo, config.CMD_WIFI, bytes([0x04, 0x01, 0x01, 0x00]))
                wifi_apagado_hoy = True
                wifi_encendido_hoy = False
            
            if hora == 0 and minuto == 0:
                wifi_encendido_hoy = False
                wifi_apagado_hoy = False
                
            time.sleep(10)
        except Exception as e:
            print(f"[CRON ERROR]: {e}")
            time.sleep(5)