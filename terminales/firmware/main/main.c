
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "driver/uart.h"
#include "driver/gpio.h"

#include "config.h"
#include "app_uart.h"
#include "protocol.h"
#include "DIO.h"

#include "app_wifi.h"
#include "app_NFC.h"
#include "camara.h"
#include "esp_log.h"
#include "driver/i2c_master.h"
#include "esp_err.h"
#include "nvs_flash.h"
#include "uart_cam.h"

    //Medicion de tiempos de respuesta
    int64_t ti =0;
    int64_t tf =0;


void reset_task(void *pvParameters) {
    
    SemaphoreHandle_t cmd_sem = protocol_get_ctrl_sem(CMD_RESET);
    if (cmd_sem == NULL) {
        ESP_LOGE("RESET", "No se pudo obtener el semáforo de reset");
        esp_restart();
    }

    while(1){
        if (xSemaphoreTake(cmd_sem, portMAX_DELAY) == pdTRUE) {
            esp_restart();
        }                               
    }
}

void app_main(void){ 

    //Inicializar el protocolo y la comunicación serial:
    protocol_params_t parametros;
    parametros.ctrl_cmds =10;
    parametros.st_cmds =10;
    parametros.masterid= MASTER_ID;
    parametros.nodoid = NODO_ID_DEFAULT;

    parametros.dispatcher_priority = 8;
    parametros.buffer_getter = uart_get_rx_streambuffer;
    parametros.dispatcher_stack =4096;

    parametros.sender = app_uart_send;
    parametros.parser_priority = 7;
    parametros.parser_stack = 4096;
    
    uart_init();
    xTaskCreate(uart_rx_task,"RX_TASK",4096,NULL,10,NULL);
    protocol_init(&parametros);


    cam_uart_init();
    xTaskCreate(cam_uart_rx_task,"WIFI",4096,NULL,9,NULL);
    //Inicializar las tareas


    xTaskCreate(app_wifi_com_task,"WIFI",4096,NULL,3,NULL);
    nfc_init();
    dio_init();

    
    xTaskCreate(camara_task,"CAM",4096,NULL,3,NULL);

    xTaskCreate(reset_task,"RST",512,NULL,20,NULL);
    composer(CMD_READY,0,NULL,NULL);

}
   

