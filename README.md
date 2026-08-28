# Control de acceso para institución educativa
Repositorio del proyecto final de carrera "Control de acceso para institución educativa" de la Facultad de Ciencias Exactas Ingeniería y Agrimensura de la Universidad Nacional de Rosario. Desarrollado por José Ramonda y dirigido por Prof. Ing. Daniel Marquez.
La explicación detallada del desarrollo se encuentra en el informe subido.

El directorio "Servidor" contiene los archivos de implementación del servidor para funcionar en cualquier dispositivo con Linux. Para utilizar instalar Mosquitto y Node-Red, clonar el repositorio, copiar el backup de Node-Red (configurar seguridad de acceso). Luego crear entorno virtual y configurar los archivos "main.py" y "bot/bot.py" como servicios.
Configuraciones importantes: 
-Añadir archivo de texto plano con token de API de Telegram
-Configurar en "bot/botconfig.py" la ruta del archivo
-Para implementación en Raspberry Pi, activar uso de UART y cambiar la dirección del puerto serie. 
-Establezca sus propias credenciales de acceso al bot, así como su propio padrón de accesos.

El directorio "terminales" incluye los proyectos de ESP-IDF donde se programó el firmware de las placas de desarrollo ESP32 Devkit y ESP32-CAM, y los arcivos de Kicad de diseño de una PCB para el prototipado.

Para consultas comunicarse a josenramonda@gmail.com
