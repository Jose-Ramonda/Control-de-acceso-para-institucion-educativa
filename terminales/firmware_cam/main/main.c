
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "driver/uart.h"
#include "driver/gpio.h"
#include "nvs_flash.h"
#include "config.h"


#include "app_wifi.h"
#include "camara.h"
#include "esp_log.h"

#include "esp_err.h"

#include "uart_cam.h"



void app_main(void){ 
    
    
    cam_uart_init();
    xTaskCreate(cam_uart_rx_task,"WIFI",4096,NULL,3,NULL);

    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        // Si la memoria está corrupta o cambió el mapa de particiones, la borramos y reinstanciamos
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    
    vTaskDelay(pdMS_TO_TICKS(2000));

    xTaskCreate(app_wifi_com_task,"WIFI",4096,NULL,3,NULL);


    
    xTaskCreate(camara_task,"CAM",8192,NULL,3,NULL);
    gpio_reset_pin(FLASH);
    gpio_set_direction(FLASH, GPIO_MODE_OUTPUT);
    ESP_LOGW("INIT","COMENZANDO FLASH");
    gpio_set_level(FLASH, 1);
    vTaskDelay(pdMS_TO_TICKS(2000));
    gpio_set_level(FLASH, 0);

    //Forzar intento de conexión al resetar
    vTaskDelay(pdMS_TO_TICKS(400)); //dejamos descansar la alimentación
    uint8_t cmd_auto_connect[2] = {UART_CAM_WFON_CMD, 0x00};//El comandito
    MessageBufferHandle_t wf_buff = get_msjbuff_wf();//recuperamos el biuffer
    xMessageBufferSend(wf_buff, cmd_auto_connect, sizeof(cmd_auto_connect), portMAX_DELAY);//mandamos a conectar
}
   

