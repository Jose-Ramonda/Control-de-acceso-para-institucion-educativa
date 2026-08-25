#   Archivo de configuración de parámetros del sistema
#   Autor: José Ramonda
#   Ultima modificación: 8/7/2026

import os

# Configuración del Puerto Serie #######################################################
PORT = '/dev/ttyUSB1'
BAUD_RATE = 9600
SERIAL_TIMEOUT = 0.1           # 100ms de timeout nativo para pyserial

# Tiempos del Protocolo (en segundos)
POLLING_TIMEOUT = 0.2        # Timeout de espera ante no-respuesta de un esclavo
POLLING_TIME =  1# 0.05       # Tiempo entre ciclos de polling

# Límites
MAX_REINTENTOS = 12

#Id's y tramas específicas
START_BYTE = 0xAA
MASTER_ID = 0x00
NODOS_ID = (0x0A, 0x14, 0x1E)

# Comandos Ramodbus
#Control
CMD_ACK = 0
CMD_POLL = 0
CMD_NACK = 1
CMD_RESET = 2
CMD_READY = 2
CMD_DOOR = 3
CMD_WIFI_FAIL = 4
CMD_RECOVER = 5
CMD_PROGMODE = 6
CMD_TAKE_PH = 7

#Flujo
CMD_NFC = 100 
CMD_WIFI = 101
CMD_UID = 102
CMD_URL = 103

#Parametros MQTT
MQTT_BROKER = "localhost"
MQTT_PORT = 1883


#diccionario donde voy guardando las ip 
ips_nodos = {}