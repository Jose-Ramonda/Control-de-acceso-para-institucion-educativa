#   Módulo de Gestión de Accesos NFC y Persistencia CSV
#   Autor: José Ramonda
#   Fecha: 15/7/2026

import os
import csv
import datetime

# Buscamos las rutas absolutas para que no dependa de dónde ejecutes el bot.py
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_PADRON_CSV = os.path.join(DIRECTORIO_ACTUAL, 'accesos_autorizados.csv')
RUTA_HISTORIAL_CSV = os.path.join(DIRECTORIO_ACTUAL, 'log_accesos.csv')

# Diccionario global en RAM: { "HEXA_UID": contador_int }
_ram_uids = {}

def cargar_padron_a_ram():
    """
    Lee el CSV de credenciales NFC ignorando delimitadores extraños, 
    BOM de UTF-8 y retornos de carro (\r).
    """
    global _ram_uids
    _ram_uids.clear()
    
    if not os.path.exists(RUTA_PADRON_CSV):
        print(f"[ACCES ERROR] No existe el archivo en la ruta: {os.path.abspath(RUTA_PADRON_CSV)}")
        return

    try:
        with open(RUTA_PADRON_CSV, mode='r', encoding='utf-8-sig') as f:
            contenido = f.read()
            
        # Detectamos automáticamente si el CSV usa ';' o ','
        delimitador = ';' if ';' in contenido else ','
        
        import io
        f_io = io.StringIO(contenido)
        lector = csv.DictReader(f_io, delimiter=delimitador)
        
        for i, fila in enumerate(lector):
            # Limpieza exhaustiva de claves y valores (quita \r, \n y espacios)
            fila_limpia = {}
            for k, v in fila.items():
                if k is not None and v is not None:
                    fila_limpia[k.strip()] = v.strip()

            uid_hexa = fila_limpia.get("UID", "").upper()
            habilitado = fila_limpia.get("habilitado", "").lower()
            titular = fila_limpia.get("titular", "Desconocido")

            if habilitado in ["true", "1", "si"]:
                try:
                    contador_actual = int(fila_limpia.get("contador", -1))
                except ValueError:
                    contador_actual = -1
                
                # Cargamos en RAM
                _ram_uids[uid_hexa] = {
                    "contador": contador_actual,
                    "titular": titular
                }

        print(f"[ACCES SUCCESS] {len(_ram_uids)} UIDs habilitadas cargadas en RAM de forma exitosa.")
        print(f"[ACCES DEBUG] Estado de RAM: {_ram_uids}")
        
    except Exception as e:
        print(f"[ACCES ERROR] Error crítico al leer el archivo CSV: {e}")

def validar(pld):   # El payload del comando NFC, retorna si abrió o no y a nombre de quien 

    try:
        # 1. Normalización de entrada
        if isinstance(pld, str): #te dice el tipo de dato, si es string

            if len(pld) < 20:
                print(f"[ACCES ERROR] String HEX menor a 20 caracteres (10 bytes). Recibido: {len(pld)}")
                return False, "ERROR_TRAMA"
            
            in_uid = pld[0:14].upper() # 7 bytes = 14 chars Hex
            in_contador = int(pld[14:20], 16) # Últimos 3 bytes de contador en Hex
            
        elif isinstance(pld, (bytes, bytearray)): #si son bytes los pasamos a string

            if len(pld) < 10:
                print(f"[ACCES ERROR] Payload en bytes menor a 10 bytes: {len(pld)}")
                return False, "ERROR_TRAMA"
            
            in_uid = pld[0:7].hex().upper()
            in_contador = int.from_bytes(pld[7:10], byteorder='big')
            
        else:
            print(f"[ACCES ERROR] Tipo de dato no soportado en payload: {type(pld)}")
            return False, "ERROR_TIPO"

        global _ram_uids

        print(f"\n--- [ACCES CHECK] ---")
        print(f" > UID Procesada: '{in_uid}'")
        print(f" > Contador Recibido: {in_contador}")

        
        if in_uid in _ram_uids:
            datos_ram = _ram_uids[in_uid]
            
            # Soporta tanto si en RAM guardaste solo el int o el dict {"contador": x, "titular": y}
            if isinstance(datos_ram, dict):
                contador_guardado = datos_ram["contador"]
                titular = datos_ram["titular"]
            else:
                contador_guardado = datos_ram
                titular = "Titular_RAM"

            print(f" > Estado en RAM -> Contador Guardado: {contador_guardado} | Titular: '{titular}'")

            #Evaluación de condiciones de seguridad (Anti-clonación / Rolling Counter)
            es_tag_nuevo = (contador_guardado == -1)
            es_contador_valido = (in_contador > contador_guardado and in_contador < contador_guardado + 10)

            if es_contador_valido or es_tag_nuevo:
                print(f" [ACCES GRANTED] Ingreso Autorizado para {titular}")
                
                # Actualizamos la RAM
                if isinstance(_ram_uids[in_uid], dict):
                    _ram_uids[in_uid]["contador"] = in_contador
                else:
                    _ram_uids[in_uid] = in_contador

                # Persistencia en CSV
                _actualizar_contador_en_csv(in_uid, in_contador)
                return True, titular
            else:
                print(f" [ACCES DENIED] Fallo de contador. Recibido={in_contador}, Esperado > {contador_guardado}")
                return False, f"CLONACION:{titular}"
        else:
            print(f" [ACCES DENIED] La UID '{in_uid}' NO existe en la _ram_uids.")
            print(f" UIDs disponibles en RAM: {list(_ram_uids.keys())}")
            return False, "DESCONOCIDO"

    except Exception as e:
        print(f"[ACCES ERROR] Falló validación: {e}")
        return False, "ERROR_CRITICO"


def registrar_evento_en_log(uid_hexa, titular, nombre_nodo, estado):
    """
    Asienta de forma irreversible en log_accesos.csv el resultado del intento.
    Campos: Fecha_Hora ; Estado ; UID ; Titular ; Nodo
    """
    fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existe_archivo = os.path.exists(RUTA_HISTORIAL_CSV)
    
    try:
        with open(RUTA_HISTORIAL_CSV, mode='a', encoding='utf-8-sig', newline='') as f:
            escritor = csv.writer(f, delimiter=',')
            if not existe_archivo:
                # Cabecera amigable para Excel
                escritor.writerow(["Fecha_Hora", "Estado", "UID", "Titular", "Nodo"])
            
            escritor.writerow([fecha_hora, estado, uid_hexa, titular, nombre_nodo])
        print(f"[LOG] Grabado en CSV -> {estado} | {titular} | {nombre_nodo}")
    except Exception as e:
        print(f"[ACCES ERROR] No se pudo escribir el log de accesos: {e}")


def _actualizar_contador_en_csv(uid_actualizar, nuevo_contador):
    """Pisa el contador en el padrón manteniendo el delimitador ';'"""
    filas_nuevas = []
    try:
        with open(RUTA_PADRON_CSV, mode='r', encoding='utf-8-sig') as f:
            lector = csv.DictReader(f, delimiter=',')
            cabecera = lector.fieldnames
            for fila in lector:
                if fila["UID"].strip().upper() == uid_actualizar:
                    fila["contador"] = str(nuevo_contador)
                filas_nuevas.append(fila)
                
        with open(RUTA_PADRON_CSV, mode='w', encoding='utf-8-sig', newline='') as f:
            escritor = csv.DictWriter(f, fieldnames=cabecera, delimiter=',')
            escritor.writeheader()
            escritor.writerows(filas_nuevas)
    except Exception as e:
        print(f"[ACCES ERROR] No se pudo actualizar el contador: {e}")



def bloquear_uid_en_csv(uid_a_bloquear):

    uid_a_bloquear = uid_a_bloquear.strip().upper()
    filas_nuevas = []
    
    try:
        # 1. Modificamos la columna 'habilitado' en el archivo físico
        with open(RUTA_PADRON_CSV, mode='r', encoding='utf-8-sig') as f:
            lector = csv.DictReader(f, delimiter=',')
            cabecera = lector.fieldnames
            for fila in lector:
                if fila["UID"].strip().upper() == uid_a_bloquear:
                    fila["habilitado"] = "false"
                filas_nuevas.append(fila)
                
        with open(RUTA_PADRON_CSV, mode='w', encoding='utf-8-sig', newline='') as f:
            escritor = csv.DictWriter(f, fieldnames=cabecera, delimiter=',')
            escritor.writeheader()
            escritor.writerows(filas_nuevas)
            
        print(f"[ACCES] UID {uid_a_bloquear} deshabilitada en el CSV.")
        
        # 2. Recarga limpia: pisamos la RAM leyendo el CSV recién guardado
        cargar_padron_a_ram()
        
    except Exception as e:
        print(f"[ACCES ERROR] No se pudo bloquear el UID: {e}")