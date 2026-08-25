#   Módulo de Autenticación - Lectura de JSON
#   Autor: José Ramonda

import json
import os

# Buscamos la ruta absoluta del JSON para que no haya errores si ejecutamos desde otra carpeta
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_JSON = os.path.join(DIRECTORIO_ACTUAL, 'credenciales.json')

def cargar_datos():
    """Abre el archivo JSON y lo convierte en diccionario. Devuelve {} si falla."""
    try:
        with open(RUTA_JSON, 'r') as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        print("[AUTH ERROR] No se encontró credenciales.json")
        return {}
    except json.JSONDecodeError:
        print("[AUTH ERROR] El JSON está mal formateado (revisá las comillas o comas)")
        return {}

def validar_acceso(usuario, clave_ingresada):
    """Verifica si el usuario existe y si su clave de acceso coincide."""
    datos = cargar_datos()
    usuarios = datos.get("usuarios", {})
    
    # 1. Chequeamos si el usuario existe en el diccionario
    if usuario in usuarios:
        clave_real = usuarios[usuario].get("clave_acceso", "")
        
        # 2. Chequeamos que coincida y que no sea una clave vacía de seguridad
        if clave_real != "" and clave_real == clave_ingresada:
            return True
            
    return False

def validar_admin(usuario, clave_ingresada):
    """Verifica si el usuario tiene privilegios de administrador y si la clave coincide."""
    datos = cargar_datos()
    usuarios = datos.get("usuarios", {})
    
    if usuario in usuarios:
        clave_admin_real = usuarios[usuario].get("clave_admin", "")
        
        if clave_admin_real != "" and clave_admin_real == clave_ingresada:
            return True
            
    return False

def validar_dev(clave_ingresada):
    """Valida la clave maestra de desarrollador."""
    datos = cargar_datos()
    clave_dev_real = datos.get("pass_dev", "")
    
    if clave_dev_real != "" and clave_dev_real == clave_ingresada:
        return True
        
    return False

def obtener_informe_usuarios():
    """
    Recorre el JSON y clasifica a cada usuario según el estado de sus claves.
    Devuelve un diccionario con los nombres y sus respectivos privilegios.
    """
    datos = cargar_datos()
    usuarios = datos.get("usuarios", {})
    informe = {}

    for nombre, claves in usuarios.items():
        clave_acc = claves.get("clave_acceso", "")
        clave_adm = claves.get("clave_admin", "")

        # Caso 1: Ambas claves vacías -> Es un slot libre de reserva
        if clave_acc == "" and clave_adm == "":
            informe[nombre] = "RESERVA (Inactivo)"
        
        # Caso 2: Tiene clave de acceso pero no de admin -> Usuario Estándar
        elif clave_acc != "" and clave_adm == "":
            informe[nombre] = "USUARIO"
        
        # Caso 3: Tiene ambas claves configuradas -> Administrador
        elif clave_acc != "" and clave_adm != "":
            informe[nombre] = "ADMINISTRADOR"
        
        # Caso 4: Caso raro/inconsistente (Tiene clave de admin pero no de acceso)
        else:
            informe[nombre] = "ERROR: Clave admin activa sin clave de acceso"

    return informe


def vincular_telegram_id(usuario, chat_id):
    """
    Busca al usuario en el JSON y le asigna de forma permanente su user_id de Telegram.
    Devuelve True si la operación fue exitosa.
    """
    datos = cargar_datos()
    if not datos or "usuarios" not in datos:
        return False
        
    usuarios = datos["usuarios"]
    if usuario in usuarios:
        # Asignamos o actualizamos la ID numérica de Telegram
        usuarios[usuario]["user_id"] = int(chat_id)
        
        try:
            with open(RUTA_JSON, 'w') as archivo:
                json.dump(datos, archivo, indent=2)
            print(f"[AUTH] ID {chat_id} vinculada exitosamente a '{usuario}'")
            return True
        except Exception as e:
            print(f"[AUTH ERROR] No se pudo escribir en credenciales.json: {e}")
            return False
            
    return False

def vincular_telegram_id(usuario, chat_id):
    """
    Busca al usuario en el JSON y le asigna de forma permanente su user_id de Telegram.
    Devuelve True si la operacion fue exitosa.
    """
    datos = cargar_datos()
    if not datos or "usuarios" not in datos:
        return False
        
    usuarios = datos["usuarios"]
    if usuario in usuarios:
        # Asignamos la ID numerica de Telegram
        usuarios[usuario]["user_id"] = int(chat_id)
        
        try:
            with open(RUTA_JSON, 'w') as archivo:
                json.dump(datos, archivo, indent=2)
            print(f"[AUTH] ID {chat_id} vinculada exitosamente a '{usuario}'")
            return True
        except Exception as e:
            print(f"[AUTH ERROR] No se pudo escribir en credenciales.json: {e}")
            return False
            
    return False