/*
*   Archivo de cabecera de manager de manejo de la camara OV2640 del módulo ESP32CAM
*   Se nutre de comoponente "espressif/esp32-camera"
*   Autor: José Ramonda
*   Ultima actualización: 6/5/2026
*   Nota de autor: si hago andar esta mierda me retiro glorioso
*/

// ESP32Cam (AiThinker) PIN Map -> del camera_pinout.h del ejemplo

#define CAM_PIN_PWDN 32
#define CAM_PIN_RESET -1 //software reset will be performed
#define CAM_PIN_XCLK 0
#define CAM_PIN_SIOD 26
#define CAM_PIN_SIOC 27

#define CAM_PIN_D7 35
#define CAM_PIN_D6 34
#define CAM_PIN_D5 39
#define CAM_PIN_D4 36
#define CAM_PIN_D3 21
#define CAM_PIN_D2 19
#define CAM_PIN_D1 18
#define CAM_PIN_D0 5
#define CAM_PIN_VSYNC 25
#define CAM_PIN_HREF 23
#define CAM_PIN_PCLK 22


#define FLASH 4

void camara_task(void *pvParameters);