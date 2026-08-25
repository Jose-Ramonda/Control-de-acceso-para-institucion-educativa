import threading
import serial
import struct
import time
import queue

# --- CONFIGURACIÓN ---
SSID_RAM = "CTDR_PRIVADA"
PASS_RAM = "wifi3491"
NODO_ID = 0x0A
PORT = '/dev/ttyUSB1' 
BAUD = 9600
POLLING_TIME = 2
CMD_WIFI = 101

WIFI_CHNG_SSID_MSJ = 1
WIFI_CHNG_PASS_MSJ = 2
WIFI_PRENDER_MSJ = 0 
WIFI_APAGAR_MSJ = 3  

DATA_PER_CHUNK = 7 
START_BYTE = 0xAA
ejecutando = True

# Colas
cola_comandos = queue.Queue()
cola_tramas = queue.Queue()

def crc16_esp(data: bytes, seed=0xFFFF):
    crc = (~seed) & 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1: crc = (crc >> 1) ^ 0x8408
            else: crc >>= 1
            crc &= 0xFFFF
    return (~crc) & 0xFFFF

def generar_trama_ramodbus(payload):
    header = struct.pack('BBB', NODO_ID, CMD_WIFI, len(payload))
    crc_val = crc16_esp(header + payload)
    return struct.pack('B', START_BYTE) + header + payload + struct.pack('<H', crc_val)

def encolar_wifi_en_chunks(tipo, contenido_str):
    """Divide en trozos y mete tramas en la cola_tramas"""
    data_bytes = contenido_str.encode('ascii')
    
    if not data_bytes:
        payload = struct.pack('BBB', tipo, 1, 1) # Chunk 1 de 1
        cola_tramas.put(generar_trama_ramodbus(payload))
        return

    total_chunks = (len(data_bytes) + DATA_PER_CHUNK - 1) // DATA_PER_CHUNK
    
    for i in range(total_chunks):
        chunk_num = i + 1
        start = i * DATA_PER_CHUNK
        end = start + DATA_PER_CHUNK
        chunk_data = data_bytes[start:end]
        
        # Payload: [Tipo][Actual][Total][Data]
        payload = struct.pack('BBB', tipo, chunk_num, total_chunks) + chunk_data
        cola_tramas.put(generar_trama_ramodbus(payload))

def listener_serial(ser):
    global ejecutando
    while ejecutando:
        # 1. Sincronización: buscamos el 0xAA
        byte = ser.read(1)
        if not byte: continue
        if byte[0] != 0xAA: 
            # Si recibimos algo que no es AA, lo mostramos para ver qué es
            # print(f"DEBUG: Byte descartado: {byte[0]:02X}")
            continue

        # 2. Leer Header (ID, CMD, LEN)
        header = ser.read(3)
        if len(header) != 3: continue
        
        nodo_id, cmd_id, p_len = header[0], header[1], header[2]
        
        # 3. Leer Payload
        payload = ser.read(p_len)
        if len(payload) != p_len: continue
        
        # 4. Leer CRC
        crc = ser.read(2)
        if len(crc) != 2: continue

        # 5. PRINT DE DEBUG TOTAL
        print(f"\n[RX] NODO:{nodo_id} | CMD:{cmd_id} | LEN:{p_len}")
        if p_len > 0:
            # Decimal para ver la IP fácil
            dec_str = ' '.join(str(b) for b in payload)
            # Hexadecimal para ver si hay bytes de control
            hex_str = ' '.join(f"{b:02X}" for b in payload)
            
            print(f"  DEC: {dec_str}")
            print(f"  HEX: {hex_str}")
            
            # Si es largo 4, probamos si es IP
            if p_len == 4:
                print(f"  IP Sugerida: {'.'.join(str(b) for b in payload)}")
        
        print("-" * 40)

def sender(ser):
    global ejecutando
    while ejecutando:
        # 1. Ver si hay pedidos del usuario para encolar
        if not cola_comandos.empty():
            op = cola_comandos.get()
            if op == "0": 
                print("Encolando: PRENDER")
                encolar_wifi_en_chunks(WIFI_PRENDER_MSJ, "")
            elif op == "1": 
                print("Encolando: APAGAR")
                encolar_wifi_en_chunks(WIFI_APAGAR_MSJ, "")
            elif op == "2":
                print(f"Encolando SSID: {SSID_RAM} y PASS")
                encolar_wifi_en_chunks(WIFI_CHNG_SSID_MSJ, SSID_RAM)
                encolar_wifi_en_chunks(WIFI_CHNG_PASS_MSJ, PASS_RAM)
            elif op == "3":
                print("Encolando test FALLO")
                encolar_wifi_en_chunks(WIFI_CHNG_SSID_MSJ, SSID_RAM)
                encolar_wifi_en_chunks(WIFI_CHNG_PASS_MSJ, "error_123")

        # 2. Decidir qué enviar en este slot de tiempo
        if not cola_tramas.empty():
            trama = cola_tramas.get()
            # Mostramos info del chunk: trama[5] es actual, trama[6] es total
            print(f"TX -> Enviando Chunk {trama[5]}/{trama[6]}")
        else:
            # Polling normal (CMD 0)
            h_poll = struct.pack('BBB', NODO_ID, 0, 0)
            trama = struct.pack('B', START_BYTE) + h_poll + struct.pack('<H', crc16_esp(h_poll))
        
        ser.write(trama)
        time.sleep(POLLING_TIME)

def main():
    global ejecutando
    print("--- WiFi Tester Ramodbus (Chunks Base 1) ---")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        
        # Hilos
        t_listen = threading.Thread(target=listener_serial, args=(ser,), daemon=True)
        t_send = threading.Thread(target=sender, args=(ser,), daemon=True)
        
        t_listen.start()
        t_send.start()

        print("\nOpciones: 0:Conectar | 1:Desconectar | 2:Creds OK | 3:Creds Fail")
        while True:
            u_input = input(">> ")
            if u_input in ["0", "1", "2", "3"]:
                cola_comandos.put(u_input)
    except KeyboardInterrupt:
        print("\nCerrando...")
    finally:
        ejecutando = False
        ser.close()

if __name__ == "__main__":
    main()
