#   Módulo de Procesamiento de Callbacks de comandos
#   Autor: José Ramonda
#   Ultima modificación 17/7/2026

import os
from telegram import Update
from telegram.ext import ContextTypes
from . import menu
from . import auth
from . import MQTT
from . import padron  # Importamos tu módulo de persistencia NFC/CSV
import botconfig

# Definición de estados para la MEF
ESPERANDO_CLAVE_ADMIN = 3
EN_MENU_USUARIO = 2

async def procesar_botones_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interpreta los clicks del menú de usuario estándar y sus submenús"""
    query = update.callback_query
    await query.answer() 

    if query.data == "usr_abrir_menu":
        await query.edit_message_text(
            text="Seleccione que acceso desea abrir:",
            reply_markup=menu.submenu_nodos("abrir")
        )
        return EN_MENU_USUARIO

    elif query.data == "usr_foto_menu":
        await query.edit_message_text(
            text="Seleccione de que acceso desea tomar fotografia:",
            reply_markup=menu.submenu_nodos("foto")
        )
        return EN_MENU_USUARIO

    elif query.data == "usr_volver_raiz":
        await query.edit_message_text( # Cambiado a edit para no duplicar globos en pantalla
            text="Menu Principal:",
            reply_markup=menu.menu_usuario()
        )
        return EN_MENU_USUARIO

    elif query.data == "usr_ir_admin":
        await query.message.reply_text("Modo Administrador solicitado. Ingrese la clave de privilegios:")
        return ESPERANDO_CLAVE_ADMIN
        
    return EN_MENU_USUARIO


async def procesar_botones_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interpreta los clicks del menú de administración avanzada"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    # 1. Listar usuarios (Auditoría)
    if query.data == "adm_listar":
        reporte = auth.obtener_informe_usuarios()
        texto_informe = "**INFORME ACTUAL DE USUARIOS:**\n\n"
        for usuario, privilegio in reporte.items():
            texto_informe += f"`{usuario:<10}` : {privilegio}\n"
            
        await query.message.reply_text(text=texto_informe, parse_mode="Markdown")
        return EN_MENU_USUARIO

    # 2. Modificar credenciales (Deriva al submenú de edición)
    elif query.data == "adm_modificar":
        await query.message.reply_text("Función de edición en desarrollo. Próximamente se podrá modificar el JSON desde acá.")
        return EN_MENU_USUARIO

    # [NUEVO] 3. El admin solicita activar el Modo Programación por Hardware
    elif query.data == "adm_progmode_menu":
        await query.edit_message_text(
            text="Seleccioná qué acceso querés poner en Modo Programación:",
            reply_markup=menu.submenu_nodos("progmode")
        )
        return EN_MENU_USUARIO

# 4. El admin solicita descargar el Padrón CSV
    elif query.data == "adm_bajar_csv":
        import botconfig
        await query.message.reply_text("Generando extracción del padrón de accesos actual...")
        ruta_absoluta = os.path.abspath(botconfig.RUTA_PADRON_CSV)
        if os.path.exists(botconfig.RUTA_PADRON_CSV):
            with open(botconfig.RUTA_PADRON_CSV, "rb") as documento:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=documento,
                    filename="accesos_autorizados.csv",
                    caption="Acá tenés el padrón.\n\nModificalo en Excel (separador ';') y volvé a arrastrar el archivo modificado a este chat."
                )
        else:
            await query.message.reply_text(
                            f"Error: El archivo físico no existe.\n\n"
                            f"Ruta buscada:\n`{ruta_absoluta}`\n\n"
                            f"Verificá el nombre y la extensión en el disco.",
                            parse_mode="Markdown"
                        )
        return EN_MENU_USUARIO

    # 5. El admin toca "Subir CSV" -> Solo le damos instrucciones claras de qué hacer
    elif query.data == "adm_subir_csv":
        await query.message.reply_text(
            "Para subir una nueva planilla modificada, simplemente **arrastrá el archivo accesos_autorizados.csv directamente a este chat** como documento."
        )
        return EN_MENU_USUARIO

    # [NUEVO] 6. Volver al menú raíz de Admin desde el submenú de Nodos de programación
    elif query.data == "adm_volver_raiz":
        await query.edit_message_text(
            text="Menu de Administración:",
            reply_markup=menu.menu_administrador()
        )
        return EN_MENU_USUARIO

    # 7. Salir del modo administrador de forma segura
    elif query.data == "adm_volver_usr":
        context.user_data["rol"] = "USUARIO"
        await query.edit_message_text(
            text="Saliendo de Modo Admin. Volviendo a interfaz estándar:",
            reply_markup=menu.menu_usuario()
        )
        return EN_MENU_USUARIO

    return EN_MENU_USUARIO


async def procesar_comandos_hardware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ataja el click de selección final del submenú y gatilla MQTT (Abrir, Foto, START o STOP de Prog)"""
    query = update.callback_query
    await query.answer()
    
    orden = query.data  # "cmd_abrir_0x0A", "cmd_progmode_0x14" o "cmd_progstop_0x14"
    partes = orden.split("_")
    accion = partes[1]  # "abrir", "foto", "progmode" o "progstop"  
    nodo = partes[2]    # El nodo siempre es el nodo real: "0x0A", "0x14", etc.

    chat_id = query.message.chat_id

    # [CORREGIDO] Caso: El admin frena el modo programación de un nodo real
    if accion == "progstop":
        # Publicamos el comando de parada hacia la ESP: "0x14,STOP"
        payload_extendido = f"{nodo},STOP"
        MQTT.publicar_comando("progmode", payload_extendido)
        print(f"[CALLBACK PROG] Enviado STOP para nodo {nodo}")
                
        await query.edit_message_text(
            text=f"Operación finalizada. Modo configuración cerrado en nodo {nodo}.\n\nMenu de Administración:",
            reply_markup=menu.menu_administrador()
        )
        return EN_MENU_USUARIO

    # Flujo Estándar de comandos hacia el hardware (Abrir, Foto, o Inicio de Progmode)
    if accion == "progmode":
        payload_extendido = f"{nodo},START"  # Formato rústico para inicio: "0x14,START"
    else:
        payload_extendido = f"{nodo},{chat_id}" # Formato estándar: "0x0A,8816825051"

    exito = MQTT.publicar_comando(accion, payload_extendido)
    
    if exito:
        if accion == "progmode":
            # Le pasamos el nodo al menú para que el botón de stop sepa a quién apagar
            await query.edit_message_text(
                text=f"El acceso {nodo} se encuentra ahora en Modo Programación.\n\n"
                     f"Pasá los llaveros nuevos por la ticketera. Al terminar presioná abajo:",
                reply_markup=menu.menu_finalizar_progmode(nodo)
            )
            return EN_MENU_USUARIO
        else:
            mensaje = f"Orden enviada para {accion.upper()} en nodo {nodo}.\nEsperando respuesta del hardware..."
    else:
        mensaje = f"Error crítico: No se pudo conectar con el broker MQTT."
        
    await query.edit_message_text(
        text=f"{mensaje}\n\nMenú Principal:",
        reply_markup=menu.menu_usuario()
    )
    
    return EN_MENU_USUARIO