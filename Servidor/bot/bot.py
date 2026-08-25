#   Archivo principal que ejecuta bot de telegram
#   Autor: José Ramonda
#   Ultima modificación 17/7/2026

import botconfig
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from mods import estados
from mods import MQTT

async def detectar_archivo_csv(update, context):
    """Ataja el documento recibido, valida el nombre y lo escribe directo en el disco"""
    documento = update.message.document
    nombre_archivo = documento.file_name

    if nombre_archivo != "accesos_autorizados.csv":
        await update.message.reply_text(f"Archivo rechazado. Debe llamarse exactamente: `accesos_autorizados.csv`")
        return

    try:
        await update.message.reply_text("Recibido. Sobreescribiendo archivo en el servidor...")
        
        # Bajamos la copia nueva de los servidores de Telegram
        archivo_tg = await context.bot.get_file(documento.file_id)
        
        # Lo guardamos pisando de forma directa el archivo externo configurado
        await archivo_tg.download_to_drive(custom_path=botconfig.RUTA_PADRON_CSV)
        MQTT.publicar_comando("actualiza","")
        await update.message.reply_text("¡Archivo `accesos_autorizados.csv` sobreescrito con éxito!")
    except Exception as e:
        print(f"[BOT ERROR] Falló la sobreescritura del CSV: {e}")
        await update.message.reply_text(f"Error al guardar el archivo: {e}")

def main():
    app = ApplicationBuilder().token(botconfig.TELEGRAM_TOKEN).build()

    maquina_de_estados = estados.obtener_maquina_estados()
    app.add_handler(maquina_de_estados)
    
    # Registramos el cazador de archivos adjuntos
    app.add_handler(MessageHandler(filters.Document.ALL, detectar_archivo_csv), group=1)
    
    MQTT.iniciar_escucha_notificaciones(app)
    
    print("[BOT] Servidor SBC escuchando peticiones en Telegram...")
    app.run_polling()

if __name__ == '__main__':
    main()