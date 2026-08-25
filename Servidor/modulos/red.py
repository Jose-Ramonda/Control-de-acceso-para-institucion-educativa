import subprocess
import socket
from modulos.nexo import encolar
import config
import math
import time

# Constantes de subcomandos de flujo de wifi
TIPO_SSID = 1 # WIFI_CHNG_SSID_MSJ
TIPO_PASS = 2 # WIFI_CHNG_PASS_MSJ
TIPO_WIFI_ON = 0 # encender wifi


# --- 1. EXTRAER NOMBRE DE LA RED ---
def obtener_nombre_wifi_activa():
    try:
        # Intento 1: SSID real en el aire del dispositivo wifi conectado
        comando = "nmcli -t -f active,ssid dev wifi | grep '^sí\\|^yes' | cut -d: -f2"
        salida = subprocess.check_output(comando, shell=True, text=True).strip()
        if salida:
            return salida.split('\n')[0]
            
        # Intento 2: Consultar la conexión 802-11 activa
        cmd_conn = "nmcli -t -f TYPE,NAME connection show --active | grep '802-11-wireless' | cut -d: -f2"
        perfil = subprocess.check_output(cmd_conn, shell=True, text=True).strip()
        if perfil:
            cmd_ssid = f"nmcli -g 802-11-wireless.ssid connection show '{perfil}' 2>/dev/null"
            ssid_real = subprocess.check_output(cmd_ssid, shell=True, text=True).strip()
            return ssid_real if ssid_real else perfil

        print("[NET AUTO] No hay ninguna red Wi-Fi conectada actualmente.")
        return None
        
    except subprocess.CalledProcessError as e:
        print(f"[NET AUTO ERROR] Falló la consulta a nmcli: {e}")
        return None


# --- 2. EXTRAER CONTRASEÑA ---
def extraer_credenciales_wifi(nombre_red):
    try:
        # Intento 1: Buscar directo por el nombre recibido
        comando_psk = f"sudo nmcli -s -g 802-11-wireless-security.psk connection show '{nombre_red}' 2>/dev/null"
        password = subprocess.check_output(comando_psk, shell=True, text=True).strip()
        
        # Intento 2: Si falló, buscar el nombre de perfil asociado en nmcli (ej: netplan-wlan0-Ramonda)
        if not password or len(password) == 64:
            cmd_perfil = "nmcli -t -f TYPE,NAME connection show | grep '802-11-wireless' | cut -d: -f2"
            perfiles = subprocess.check_output(cmd_perfil, shell=True, text=True).strip().split('\n')
            for p in perfiles:
                if p:
                    cmd_p = f"sudo nmcli -s -g 802-11-wireless-security.psk connection show '{p}' 2>/dev/null"
                    res = subprocess.check_output(cmd_p, shell=True, text=True).strip()
                    if res and len(res) != 64:
                        password = res
                        break
        
        # Intento 3: Si sigue vacío o con hash de 64 caracteres, leer el archivo YAML en texto plano
        if not password or len(password) == 64:
            cmd_grep = "sudo grep -rh 'password:' /etc/netplan/ 2>/dev/null | head -n1 | awk '{print $2}' | tr -d '\"'"
            password_netplan = subprocess.check_output(cmd_grep, shell=True, text=True).strip()
            if password_netplan:
                password = password_netplan

        if not password:
            return None
        return password
    except Exception:
        return None


# --- 3. OBTENER IP DEL SERVIDOR ---
def obtener_ip_sbc():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


# ==========================================
# LA FUNCIÓN RECOLECTORA FINAL
# ==========================================
def obtener_datos_red_completos():
    """
    Rejunta SSID, Password e IP de forma 100% automática.
    Retorna (ssid, password, ip) o (None, None, None) si falla.
    """
    print("[NET] Analizando entorno de red...")
    
    ssid = obtener_nombre_wifi_activa()
    if not ssid:
        return None, None, None
        
    password = extraer_credenciales_wifi(ssid)
    if not password:
        print(f"[NET] No se pudo obtener la clave para {ssid}")
        return None, None, None
        
    ip_sbc = obtener_ip_sbc()
    
    print(f"[NET] -> ÉXITO: SSID='{ssid}' | IP='{ip_sbc}'")
    print(f"PASSWORD: {password}")
    return ssid, password, ip_sbc


def despachar_url_servidor(ip_servidor, puerto=1880):
    """
    Convierte la IP y el puerto a 6 bytes y los encola para todos los nodos.
    """
    try:
        # 1. Convertimos la IP string ("192.168.136.91") a 4 bytes
        partes_ip = ip_servidor.split('.')
        ip_bytes = bytes([int(p) for p in partes_ip])
        
        # 2. Convertimos el puerto a 2 bytes en Little Endian (88, 7)
        puerto_bytes = puerto.to_bytes(2, byteorder='little')
        
        # 3. Concatenamos para crear el payload final de 6 bytes
        payload_server = ip_bytes + puerto_bytes
        
        # 4. Barremos el array de Nodos usando el for
        for id_nodo in config.NODOS_ID:
            encolar(id_nodo, config.CMD_URL, payload_server)
            
        print(f"[NET CFG] IP {ip_servidor}:{puerto} despachada a todos los nodos.")
        
    except Exception as e:
        print(f"[NET CFG ERROR] Fallo al armar la trama de IP: {e}")


def despachar_credenciales_chunks(ssid, password):
    """
    Toma las credenciales, las divide en pedazos de hasta 7 caracteres 
    y encola las tramas con la cabecera de 3 bytes para FreeRTOS.
    """
    if not ssid or not password:
        print("[NET WARN] SSID o Password nulos. Se omite el despacho de credenciales.")
        return

    MAX_PAYLOAD = 10
    HEADER_SIZE = 3
    MAX_DATA = MAX_PAYLOAD - HEADER_SIZE # Quedan 7 bytes libres para texto

    def encolar_texto(tipo, texto):
        texto_bytes = texto.encode('utf-8')
        total_bytes = len(texto_bytes)
        
        total_chunks = math.ceil(total_bytes / MAX_DATA)
        if total_chunks == 0: 
            return
            
        for id_nodo in config.NODOS_ID:
            for i in range(total_chunks):
                chunk_actual = i + 1
                inicio = i * MAX_DATA
                fin = inicio + MAX_DATA
                chunk_datos = texto_bytes[inicio:fin]
                
                cabecera = bytes([tipo, chunk_actual, total_chunks])
                payload_final = cabecera + chunk_datos
                
                encolar(id_nodo, config.CMD_WIFI, payload_final)
                
    # 1. Encolamos el SSID
    encolar_texto(TIPO_SSID, ssid)
    
    # 2. Encolamos la contraseña
    encolar_texto(TIPO_PASS, password)
    
    # 3. Encolamos el comando de conectar (Prender Wi-Fi)
    for id_nodo in config.NODOS_ID:
        encolar(id_nodo, config.CMD_WIFI, bytes([TIPO_WIFI_ON, 1, 1])) 
        
    print(f"[NET CFG] Credenciales despachadas en {MAX_DATA} bytes por trama.")


def hacer_ping(ip):
    """Ejecuta un ping rápido de 1 solo paquete a nivel sistema operativo."""
    comando = f"ping -c 1 -W 2 {ip}"
    try:
        res = subprocess.run(comando, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def net_monitor_task(func_encolar):
    """
    Hilo monitor simple: revisa el diccionario de config, 
    hace ping a cada IP registrada y reconecta si falla.
    """
    print("[NET MONITOR] Hilo monitor de red iniciado...")
    
    fallos_consecutivos = {}

    while True:
        if not config.ips_nodos:
            time.sleep(10)
            continue
            
        for id_nodo, ip in list(config.ips_nodos.items()):
            if hacer_ping(ip):
                fallos_consecutivos[id_nodo] = 0
            else:
                fallos_consecutivos[id_nodo] = fallos_consecutivos.get(id_nodo, 0) + 1
                
                if fallos_consecutivos[id_nodo] >= 3:
                    print(f"[NET ALERT] Nodo {hex(id_nodo)} perdido. Forzando reconexión Wi-Fi...")
                    payload_reconexion = bytes([TIPO_WIFI_ON, 1, 1])
                    func_encolar(id_nodo, config.CMD_WIFI, payload_reconexion)
                    fallos_consecutivos[id_nodo] = 0
                    
        time.sleep(60)


if __name__ == "__main__":
    s, p, i = obtener_datos_red_completos()
    if s:
        print("Todo listo para empaquetar y enviar al ESP32.")