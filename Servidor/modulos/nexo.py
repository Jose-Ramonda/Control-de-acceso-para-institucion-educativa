#   Archivo de librería intermedia entre libreria ramodbus 
#   Incluye funcion de API para encolar datos a enviar, funcion privada parser, hilo escucha cmd recibidos para parseo
#   Autor: José Ramonda
#   Ultima modificación: 10/7/2026

import queue
import time
import json
import time

import config       # Si config.py estuviera adentro, pero ojo...
from . import main_mqtt
from . import accesos
#Creo las colas del sistema

cola_entrada = queue.Queue() #Cola de entrada, que se parsea
cola_salida = {}    #arreglo (tupla) de colas, una por nodo, para enviar datos afuera
for id_nodo in config.NODOS_ID:
    cola_salida[id_nodo] = queue.Queue()



#Tiempo de ultimo comando nfc
last =0

def encolar(id_nodo, comando, payload=b""):# Función pública, con la llamada a la API se envian datos para enviar comandos

    if id_nodo in cola_salida:
        # Armamos la estructura idéntica a la que espera tu hilo serial
        packet = {
            "cmd": comando,
            "payload": payload
        }
        cola_salida[id_nodo].put(packet)
        print(f"[LOGICA] Comando {comando} encolado para el nodo {hex(id_nodo)}")
    else:
        print(f"[LOGICA ERROR] El nodo {hex(id_nodo)} no existe en el sistema.")


def parser(evento):

    cmd = evento["cmd"]
    id_nodo = evento["id_nodo"]
    payload = evento["payload"]

    topico_nodo = f"sbc/status/{hex(id_nodo)}"
    # no uso switch case porque en  python no es muy intuitivo, lo ifeo todo
    if cmd == config.CMD_DOOR:
        print(f"[PARSER - PUERTA] El nodo {hex(id_nodo)} reporta APERTURA DE LA PUERTA.")
        main_mqtt.publicar_mensaje(topico_nodo, "OK_PUERTA")

    elif cmd == config.CMD_READY:
        print(f"[PARSER - STATUS] El nodo {hex(id_nodo)} reporta que está listo.")
    
    elif cmd == config.CMD_WIFI:

        ip_detectada = ".".join(str(b) for b in payload)
        print(f"[PARSER - WIFI] El nodo {hex(id_nodo)} reporta IP: {ip_detectada}")
        main_mqtt.publicar_mensaje(topico_nodo, ip_detectada)
        
        config.ips_nodos[id_nodo] = ip_detectada

    elif cmd == config.CMD_TAKE_PH:
        print(f"[PARSER - CAMARA] El nodo {hex(id_nodo)} reporta fotografía tomada")
        main_mqtt.publicar_mensaje(topico_nodo,"OK_FOTO")

    elif cmd == config.CMD_NFC:
        #intento hacer la ruta de apertura lo mas rápida posible


        ahora = time.time()
        global last

        if (ahora - last) < 3.0 :
            return

            
        trama = payload.hex().upper()
        print(f"Intento de ingreso {trama}")
        last = time.time()
        exito, resultado = accesos.validar(trama)
        if exito:
            encolar(id_nodo,config.CMD_DOOR,b"")    #Primero que nada mando a abrir
            #Luego lo demas interno
            #titular = resultado   #Innecesario, porngo resultado   
            uid_hexa = payload[0:7].hex().upper() if len(payload) >= 7 else "ERROR"
            accesos.registrar_evento_en_log(uid_hexa,resultado,hex(id_nodo).upper(),"INGRESO")
            
        else:
            uid_hexa = payload[0:7].hex().upper() if len(payload) >= 7 else "ERROR"
            
            if resultado.startswith("CLONACION:"):
                titular_afectado = resultado.split(":")[1]
                
                # Asentamos el fraude en el log con el nodo en Hexa
                accesos.registrar_evento_en_log(uid_hexa, titular_afectado, hex(id_nodo).upper(), "ALERTA_CLON")
                
                # Bloqueo físico en CSV y recarga automática de RAM
                accesos.bloquear_uid_en_csv(uid_hexa)
                
                # 3. Despacho del JSON serializado hacia Node-RED / Bot de Telegram
                topico = "sbc/notify"
                exit_payload = {
                    "destino": "all",
                    "evento": "alerta",
                    "nodo": hex(id_nodo).upper(),
                    "data": titular_afectado
                }
                
                #Pasamos el diccionario a string JSON para que MQTT lo transmita limpio
                main_mqtt.publicar_mensaje(topico, json.dumps(exit_payload))
                            
            else:
                accesos.registrar_evento_en_log(uid_hexa,resultado,hex(id_nodo).upper(),"DESCONOCIDO")
    
    
    elif cmd == config.CMD_UID:
        # La ESP está en modo programación y leyó un tag (nuevo o viejo)
        uid_hexa = payload[0:7].hex().upper() if len(payload) >= 7 else "ERROR"
        print(f"[PARSER - PROGMODE] Capturado Tag en modo registro en nodo {hex(id_nodo).upper()}. UID: {uid_hexa}")
        
        # Llamamos a la función de accesos para meterla al CSV con habilitado=false y titular="Nuevo_NFC"
        # (Si la tarjeta ya existía en el archivo, la función no hace nada, evitando duplicados)
        accesos.agregar_uid_no_habilitada(uid_hexa)
    else:
        print(f"[PARSER ALERTA] Comando {cmd} desconocido o no implementado.")


def nexo_task():#hilo uqe escucha y llama a parsear
    
    print("[LOGICA] Hilo de lógica intermedia iniciado y escuchando...")

    while True:
        try:
            # Se bloquea acá esperando que el hilo serial le mande algo.
            # El timeout de 1 segundo es para que el hilo no quede inmortal y pueda cerrarse con Ctrl+C
            evento = cola_entrada.get(timeout=1)
            
            # El hilo serial te puede mandar "DATOS_NODO" o alertas como "NODO_CAIDO"
            if "evento" in evento and evento["evento"] == "NODO_CAIDO":
                print(f"[LOGICA ALERTA] El nodo {hex(evento['id_nodo'])} se ha ido OFFLINE.")
                topico = "sbc/notify"
                exit_payload = {
                    "destino": "all",
                    "evento": "alerta", # Mantenemos "alerta" para usar la misma ruta lógica en Node-RED
                    "nodo": hex(evento["id_nodo"]),
                    "data": "DESCONECTADO" # Texto que indica qué pasó con el nodo
                }
                
                # Pasamos el diccionario a string JSON para que MQTT lo transmita limpio
                main_mqtt.publicar_mensaje(topico, json.dumps(exit_payload))
            else:
                # Si no es una alerta del driver, es data cruda de un nodo: la pasamos al parser

                parser(evento)

        except queue.Empty:
            # No llegó nada en este segundo, volvemos a intentar (mantiene el bucle vivo)
            pass
