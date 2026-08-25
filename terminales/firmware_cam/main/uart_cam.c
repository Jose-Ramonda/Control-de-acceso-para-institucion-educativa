/*
*   Este arcivo contiene las funciones/tareas relativas a la inicializacion
*   De la interefaz UART así como de la recepcion y envio de mensajes
*
*   Autor: José Ramonda
*   Actualizado 21/1/2026
*/
#include <stdio.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_err.h"
#include "freertos/message_buffer.h"


#include "driver/uart.h"      // UART
#include "driver/gpio.h"      // GPIO



#include "uart_cam.h"
#include "config.h"


static QueueHandle_t uart_cola;
static const char *TAG = "UART_2";


static MessageBufferHandle_t WF_BUFF ;
static MessageBufferHandle_t URL_BUFF;
static SemaphoreHandle_t foto_sem;


void cam_uart_init(void){       //Tarea, que se autodestruye mejor que función, la funcion perdura, la función queda

    

    uart_config_t uart_config = {       //Creamos estructura de configuraciones de uart
        .baud_rate = UART_BAUD_RATE,    //Esto viende del config
        .data_bits = UART_DATA_8_BITS,  //Palabras de 8 bits macro del idf
        .parity = UART_PARITY_DISABLE,  //Sin bit de paridad de idf
        .stop_bits = UART_STOP_BITS_1,  // 1 bit de stopp
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,  
        .source_clk = UART_SCLK_APB,
    };


    ESP_ERROR_CHECK(uart_driver_install(UART_PORT,UART_RX_BUF_SIZE,UART_TX_BUF_SIZE,UART_EVENT_QUEUE_SIZE,&uart_cola,0));

    ESP_ERROR_CHECK(uart_param_config(UART_PORT, &uart_config)); //Configurar el UART y verificar
    
   
    ESP_ERROR_CHECK(uart_set_pin(UART_PORT,UART_TX_PIN,UART_RX_PIN,UART_RTS_PIN,UART_PIN_NO_CHANGE));   //Configuramos pines uart, solo Tx y Rx ya que los demas no se usan en rs485, son para control de flujo por hardware

    ESP_ERROR_CHECK(uart_set_mode(UART_PORT, UART_MODE_UART));
   
    ESP_LOGI("UART 2", "UART inicializado correctamente");

    WF_BUFF = xMessageBufferCreate(256);
    URL_BUFF = xMessageBufferCreate(64);
    foto_sem = xSemaphoreCreateBinary();
}



MessageBufferHandle_t get_msjbuff_wf(void){
    return WF_BUFF;
}

MessageBufferHandle_t get_msjbuff_url(void){
    return URL_BUFF;
}
SemaphoreHandle_t get_fotosem(void){
    return foto_sem;
}

void cam_uart_rx_task(void *pvParameters) {
    uart_event_t event;
    ESP_LOGI("UART 2","TAREA DE RX");     
    uint8_t temp_rx_buf[140];

    while(1) {
        // 1. Esperar un evento de la cola (Bloqueo total sin CPU)
        if(xQueueReceive(uart_cola, (void *)&event, portMAX_DELAY)) {
            
            // 2. ¿Qué pasó en la UART?
            switch(event.type) {
                
                case UART_DATA: { 
                    int n = uart_read_bytes(UART_PORT, temp_rx_buf, event.size, pdMS_TO_TICKS(50));
                    
                    uint8_t checksum = 0;
                    
                    if( n >= 4 && temp_rx_buf[0] == 0xAA ){


                        uint8_t payload_len = temp_rx_buf[2];
                        ESP_LOGI(TAG, "RX RAW [%d bytes]: Cmd=0x%02X Len=%d", n, temp_rx_buf[1], payload_len);
                        
                        // Imprimir el buffer de bytes en Hexadecimal
                        ESP_LOG_BUFFER_HEX_LEVEL(TAG, temp_rx_buf, n, ESP_LOG_INFO);

                        // Si la trama trae payload, imprimible como string seguro
                        if (payload_len > 0 && (3 + payload_len) <= n) {
                            ESP_LOGI(TAG, "Payload String: %.*s", payload_len, (char*)&temp_rx_buf[3]);
                        }


                        for(int i = 1; i < (temp_rx_buf[2] + 3); i++){
                            checksum ^= temp_rx_buf[i];
                        }
                        
                        uint8_t posicion_checksum = temp_rx_buf[2] + 3; 

                        if(checksum != temp_rx_buf[posicion_checksum]){
                            ESP_LOGE(TAG, "ERROR de CHECKSUM");
                            
                            uint8_t bf[2] = { UART_CAM_NOK_CMD, 0x00 };
                            cam_uart_send(bf, 2);
                            break;
                        }
                        
                        // Si no brokeó, hacer cosas
                        switch (temp_rx_buf[1])
                        {
                        case UART_CAM_PH_CMD:
                            xSemaphoreGive(foto_sem);
                            break;
                        case UART_CAM_WFON_CMD:
                            xMessageBufferSend(WF_BUFF, &temp_rx_buf[1], 2 + temp_rx_buf[2], pdMS_TO_TICKS(50));
                            break;
                        case UART_CAM_WFOFF_CMD:
                            xMessageBufferSend(WF_BUFF, &temp_rx_buf[1], 2 + temp_rx_buf[2], pdMS_TO_TICKS(50));
                            break;
                        case UART_CAM_WFRECONFIG_CMD:
                            xMessageBufferSend(WF_BUFF, &temp_rx_buf[1], 2 + temp_rx_buf[2], pdMS_TO_TICKS(50));
                            break;
                        case UART_CAM_PASS_CMD:
                            xMessageBufferSend(WF_BUFF, &temp_rx_buf[1], 2 + temp_rx_buf[2], pdMS_TO_TICKS(50));
                            break;
                        case UART_CAM_SSID_CMD:
                            xMessageBufferSend(WF_BUFF, &temp_rx_buf[1], 2 + temp_rx_buf[2], pdMS_TO_TICKS(50));
                            break;
                        case UART_CAM_URL_CMD:
                            //Aca mando directamente el payload
                            xMessageBufferSend(URL_BUFF, &temp_rx_buf[3], temp_rx_buf[2], pdMS_TO_TICKS(50));
                            break;
                        default:
                            break;
                        }
                        ESP_LOGI(TAG, "Trama válida recibida! Comando: 0x%02X", temp_rx_buf[1]);
                    }
                    break;
                } 

                case UART_FIFO_OVF:
                    ESP_LOGW("UART", "Hardware FIFO saturado (Overflow)");
                    uart_flush_input(UART_PORT);
                    xQueueReset(uart_cola);
                    break;

                case UART_BUFFER_FULL:
                    ESP_LOGW("UART", "Ring Buffer lleno");
                    uart_flush_input(UART_PORT);
                    xQueueReset(uart_cola);
                    break;

                case UART_BREAK:
                    //ESP_LOGI("UART", "Detección de línea en BREAK");
                    break;

                default:
                    // Otros eventos (errores de paridad, etc.)
                    break;
            }
        }
    }
    vTaskDelete(NULL); // Por buena práctica, si sale del loop se borra
}


void cam_uart_send(uint8_t *trama, int len){

    uint8_t checksum = 0;
    for (int i = 0; i < len; i++) {
        checksum ^= trama[i];
    }
    uint8_t exit[len+2];
    exit[0]=0xAA;   //byte de start
    memcpy(&exit[1],trama,len);//payload
    exit[len+1]=checksum;
    uart_write_bytes(UART_PORT, (const char*)exit,sizeof(exit));
}