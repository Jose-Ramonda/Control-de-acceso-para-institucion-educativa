#   Archivo de librería de interfaz serial del protocolo Ramobdbus
#   Autor: José Ramonda
#   Ultima modificación: 8/7/2026

import threading
import serial
import struct
import time
import queue
import config
from modulos import nexo


ser = None #Creo el objeto serial global, lo incializo luego

def crc16_esp(data: bytes, seed=0xFFFF):
    crc = (~seed) & 0xFFFF   # igual que en ROM

    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0x8408
            else:
                crc >>= 1
            crc &= 0xFFFF

    return (~crc) & 0xFFFF

def sender(id, cmd, payload):   #Funcion que manda comandos 
    
    header = struct.pack('BBB', id, cmd, len(payload))
    crc = crc16_esp(header + payload)

    trama = (
            struct.pack('B', config.START_BYTE)
            + header
            + payload
            + struct.pack('<H', crc)
        )
    ser.write(trama)

def listener():
    byte = ser.read(1)

    if not byte:
        return None # Si hay timeout devuelvo None -> error
    
    # Extraemos el valor numérico con [0] para comparar con la macro
    if byte[0] != config.START_BYTE:
        return None    

    id = ser.read(1) # Leo encabezado

    if not id:
        return None
    
    if id[0] != config.MASTER_ID:
        return None

    cmd = ser.read(1)
    if not cmd:
        return None


    sz = ser.read(1)
    if not sz:
        return None
    
    payload = b"" # Inicializamos el payload vacío por defecto
    if sz[0] > 0:
        payload = ser.read(sz[0])
        if len(payload) != sz[0]:
            return None
            
    crc_recibido = ser.read(2)
    if len(crc_recibido) < 2:
        return None
    
    # Desempaquetamos el CRC recibido (Little Endian)
    crc = struct.unpack('<H', crc_recibido)[0]

    crc_calculado = crc16_esp(id + cmd + sz + payload) #Aca me complica el payload
    
    if crc != crc_calculado:
        return None

    return cmd[0], payload


def comunicacion_task(cola_salida, cola_entrada):    
    global ser
    ser = serial.Serial(
        port=config.PORT,
        baudrate=config.BAUD_RATE,
        timeout=config.SERIAL_TIMEOUT
    )

    estados_nodos = {}
    for id_nodo in config.NODOS_ID:
        estados_nodos[id_nodo] = {
            "status": "ONLINE",
            "n_retry": 0,
            "last": time.time()
        }

    while True:     
        for id_nodo in config.NODOS_ID:
            if estados_nodos[id_nodo]["status"] == "OFFLINE":
                # TODO: Lógica de reconexión paulatina aquí si se desea
                continue

            # 1. Definimos variables LOCALES por cada nodo en esta iteración
            data = {"cmd": config.CMD_POLL, "payload": b""}
            
            # 2. Obtenemos comando o hacemos polling
            try:
                data = cola_salida[id_nodo].get_nowait()
            except queue.Empty:
                data = {"cmd": config.CMD_POLL, "payload": b""}

            # 3. Transmisión
            sender(id_nodo, data["cmd"], data["payload"])

            # 4. Recepción
            res = listener()
            
            if res is None:
                # Fallo de respuesta / Timeout
                estados_nodos[id_nodo]["n_retry"] += 1
                
                # Si falló un comando real (no polling), lo volvemos a encolar para no perderlo
                if data["cmd"] != config.CMD_POLL:
                    cola_salida[id_nodo].put(data)

                if estados_nodos[id_nodo]["n_retry"] >= config.MAX_REINTENTOS:
                    estados_nodos[id_nodo]["n_retry"] = 0
                    estados_nodos[id_nodo]["status"] = "OFFLINE"
                    print(f"[SERIAL WARN] Nodo {hex(id_nodo)} pasó a OFFLINE")
                    alerta_offline = {
                        "evento": "NODO_CAIDO",
                        "id_nodo": id_nodo
                    }
                    cola_entrada.put(alerta_offline)

                
                # Descartamos basura del buffer serie tras un timeout/error
                ser.reset_input_buffer()

            else:
                # Llegó respuesta válida: reseteamos contador de reintentos
                estados_nodos[id_nodo]["n_retry"] = 0
                cmd_recibido, payload_recibido = res

                if cmd_recibido == config.CMD_ACK:
                    #print("[DEBUG BUS] Fue un misero ACK, no va a la cola_entrada.")
                    pass # Se procesó OK por el nodo, no requiere más acción

                elif cmd_recibido == config.CMD_NACK and data["cmd"] != config.CMD_POLL:
                    # El nodo rechazó la trama, re-encolamos para reintentar
                    cola_salida[id_nodo].put(data)

                else:
                    # Novedad o evento enviado por el nodo -> Creamos DICCIONARIO NUEVO (sin referencias compartidas)
                    indata = {
                        "id_nodo": id_nodo,
                        "cmd": cmd_recibido,
                        "payload": payload_recibido
                    }
                    print(f"[DEBUG BUS] Encolando evento a la entrada evento {indata['cmd']}")
                    cola_entrada.put(indata)

            # 5. TIEMPO DE GUARDA OBLIGATORIO: Se ejecuta SIEMPRE al final de atender cada nodo
            time.sleep(config.POLLING_TIME)
