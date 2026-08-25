/*
*   Archivo de c de manejo de la camara OV2640 del módulo ESP32CAM
*   Se nutre de comoponente "espressif/esp32-camera"
*   Basado en ejemplo take_picture.c
*   Autor: José Ramonda
*   Ultima actualización: 6/5/2026
*/


#include "camara.h"



#include "sdkconfig.h"

#include <esp_log.h>
#include <esp_system.h>
#include <nvs_flash.h>
#include <sys/param.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_http_client.h"

#include "esp_camera.h"
#include "config.h"
#include "protocol.h"
#include "uart_cam.h"


static const char *TAG = "CAMARA";
static char url_servidor[126] = "";
static SemaphoreHandle_t cmd_sem = NULL;




void url_task(void *pvParameters){
    MessageBufferHandle_t buff = cmd_buff_getter(CMD_URL);
    uint8_t entry_buffer[PROTOCOL_MAX_PAYLOAD_SIZE];
    
    // Buffer temporal local: 3 bytes header + 128 max payload + 1 byte checksum
    uint8_t temp_buff[132]; 

    while (1)
    {
        if(xMessageBufferReceive(buff, entry_buffer, PROTOCOL_MAX_PAYLOAD_SIZE, portMAX_DELAY)){
            
            /*
            uint16_t puerto = entry_buffer[4] | (entry_buffer[5] << 8); 
            
            // Cocinamos el string de la URL
            snprintf(url_servidor, sizeof(url_servidor), "http://%d.%d.%d.%d:%d/upload",
                     entry_buffer[0], entry_buffer[1], entry_buffer[2], entry_buffer[3], puerto);
            
            ESP_LOGI(TAG, "URL del server: %s", url_servidor);
            
            uint8_t longitud_url = (uint8_t)strlen(url_servidor);

            // 1. Armamos el Header en el buffer temporal
            temp_buff[0] = UART_CAM_URL_CMD;  // Comando de URL
            temp_buff[1] = longitud_url;      // Longitud real del string

            // 2. COPIA CORRECTA: Metemos los caracteres en el buffer a partir del byte 3
            memcpy(&temp_buff[2], url_servidor, longitud_url);
            */
           temp_buff[0] = UART_CAM_URL_CMD;
           temp_buff[1] =6;
           memcpy(&temp_buff[2], entry_buffer, 6);

            cam_uart_send(temp_buff, 8);
        }
    }
}

void camara_task(void *pvParameters)
{
    cmd_sem = protocol_get_ctrl_sem(CMD_TAKE_PH);

    xTaskCreate(url_task,"URL",4096,NULL,4,NULL);
    while (1)
    {
        if (xSemaphoreTake(cmd_sem, portMAX_DELAY) == pdTRUE) {
            uint8_t buff[2] = {UART_CAM_PH_CMD, 0x00};
            cam_uart_send(buff,2);
            vTaskDelay(pdMS_TO_TICKS(700));
            xSemaphoreTake(cmd_sem,pdMS_TO_TICKS(500));//Es un cooldown para agarrar los rebotes del pulsador
        } 
    }

}

