#   Máquina de Estados Principal del Bot (ConversationHandler)
#   Autor: José Ramonda
#   Modificado 11/7/2026


from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    MessageHandler, filters, CallbackQueryHandler
)
from . import auth
from . import menu
from . import callbacks

# Definición de Estados (0, 1, 2, 3)
ESPERANDO_USER, ESPERANDO_CLAVE, EN_MENU_USUARIO, ESPERANDO_CLAVE_ADMIN = range(4)

async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Punto de entrada: Evalúa si ya está logueado o inicia el flujo."""
    if "logueado" not in context.user_data:
        context.user_data["logueado"] = False
        context.user_data["usuario"] = None
        context.user_data["rol"] = "INVITADO"

    if context.user_data["logueado"]:
        await update.message.reply_text(
            text=f"Sesión activa: {context.user_data['usuario']}. Menú disponible:",
            reply_markup=menu.menu_usuario()
        )
        return EN_MENU_USUARIO

    await update.message.reply_text("Sistema SBC. Por favor, ingrese su nombre de usuario:")
    return ESPERANDO_USER

async def capturar_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario_ingresado = update.message.text
    datos = auth.cargar_datos()
    
    if usuario_ingresado in datos.get("usuarios", {}):
        context.user_data["usuario"] = usuario_ingresado
        await update.message.reply_text(f"Usuario '{usuario_ingresado}' reconocido. Ingrese su contraseña:")
        return ESPERANDO_CLAVE
    else:
        await update.message.reply_text("Usuario no registrado. Intente nuevamente:")
        return ESPERANDO_USER

async def capturar_clave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clave_ingresada = update.message.text
    usuario = context.user_data["usuario"]
    chat_id_telegram = update.message.chat_id # <-- Capturamos la ID de Telegram

    try:
        await update.message.delete()
    except Exception:
        pass

    if auth.validar_acceso(usuario, clave_ingresada):
        # [NUEVO] Vinculamos de forma permanente el ID en el JSON antes de dar acceso
        auth.vincular_telegram_id(usuario, chat_id_telegram)
        
        context.user_data["logueado"] = True
        context.user_data["rol"] = "USUARIO"
        
        await update.message.reply_text(
            text=f"¡Acceso Concedido! Bienvenido {usuario}.\nMenú de operaciones:",
            reply_markup=menu.menu_usuario()
        )
        return EN_MENU_USUARIO
    else:
        await update.message.reply_text("Contraseña incorrecta. Intente nuevamente:")
        return ESPERANDO_CLAVE

# --- FUNCIÓN NUEVA PARA VALIDAR LA CLAVE DE ADMIN ---
async def capturar_clave_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clave_ingresada = update.message.text
    usuario = context.user_data["usuario"]

    try:
        await update.message.delete()
    except Exception:
        pass

    if auth.validar_admin(usuario, clave_ingresada):
        context.user_data["rol"] = "ADMIN"
        await update.message.reply_text(
            text=f"MODO ADMINISTRADOR ACTIVADO\nSesión: {usuario}\n\nMenú de gestión:",
            reply_markup=menu.menu_administrador()
        )
        return EN_MENU_USUARIO 
    else:
        await update.message.reply_text("Clave de administrador incorrecta. Volviendo a menú:")
        await update.message.reply_text(
            text="Menú de operaciones:",
            reply_markup=menu.menu_usuario()
        )
        return EN_MENU_USUARIO

async def comando_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Operación cancelada. Sesión cerrada.")
    return ConversationHandler.END


# --- CONSTRUCCIÓN DE LA MÁQUINA DE ESTADOS ---
def obtener_maquina_estados():
    return ConversationHandler(
        entry_points=[CommandHandler("start", comando_start)],
        states={
            ESPERANDO_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, capturar_usuario)],
            ESPERANDO_CLAVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, capturar_clave)],
            
            EN_MENU_USUARIO: [
                CommandHandler("start", comando_start),
                # Escucha botones de usuario:
                CallbackQueryHandler(callbacks.procesar_botones_usuario, pattern="^usr_"),
                # Escucha botones de admin
                CallbackQueryHandler(callbacks.procesar_botones_admin, pattern="^adm_"),
                # Escucha botones cmd
                CallbackQueryHandler(callbacks.procesar_comandos_hardware, pattern="^cmd_"),
                #Ataja mensajes basura
                MessageHandler(filters.ALL & ~filters.COMMAND, capturar_texto_invalido_menu)
            ],
            # ACÁ ESTÁ EL PUENTE: Vinculamos el estado 3 con su función capturadora
            ESPERANDO_CLAVE_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, capturar_clave_admin)],
        },
        fallbacks=[CommandHandler("cancelar", comando_cancelar)],
        per_message=False  # Esto silencia el warning de trackeo de mensajes
    )


async def capturar_texto_invalido_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ataja cualquier texto crudo tipeado por error mientras se muestra el menú"""
    await update.message.reply_text(
        text="Comando no reconocido. Ingrese /start para ver el menu."
    )
    return EN_MENU_USUARIO # Mantenemos la máquina plantada en el estado de menú