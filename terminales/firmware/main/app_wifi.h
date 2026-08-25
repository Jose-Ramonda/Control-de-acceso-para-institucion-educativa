/*
*   Archivo de cabeecera de manager de conexión WiFI
*   Autor: José Ramonda
*   Ultima actualización: 10/4/2026
*/

#define WIFI_FAIL_MSJ 0x01

#define WIFI_PRENDER_MSJ 0
#define WIFI_CHNG_SSID_MSJ 1
#define WIFI_CHNG_PASS_MSJ 2
#define WIFI_APAGAR_MSJ 3


void app_wifi_com_task(void *pvParameters);
