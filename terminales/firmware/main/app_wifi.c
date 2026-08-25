/*
*   Archivo de programa de manager de conexión WiFI
*   Basado en ejemplo wifi/getting_started/station_example_main.c
*   Autor: José Ramonda
*   Ultima actualización: 10/4/2026
*/


#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"



#include "esp_log.h"


#include "freertos/message_buffer.h"

#include "app_wifi.h"
#include "config.h"
#include "protocol.h"
#include "uart_cam.h"

static const char *TAG = "wifi station"; 



void encolar(uint8_t* data, uint8_t tipo){
    uint8_t l = (uint8_t)strlen((char*)data);
    uint8_t buff[l+2];
    buff[0]=tipo;
    buff[1]=l;
    memcpy(&buff[2],data,l);
    cam_uart_send(buff,l+2);
}
void app_wifi_com_task(void *pvParameters){
    //Agarro el buffer correspondiente para comunicar y sincronizar desde el protocolo
    MessageBufferHandle_t buff = cmd_buff_getter(CMD_WIFI);
    uint8_t entry_buffer[PROTOCOL_MAX_PAYLOAD_SIZE];
    int n;

    //Buffers auxiliares de credenciales
    uint8_t aux_nombre_red[32];  //Credenciales de acceso
    uint8_t aux_clave[64]; 


    int max_data_per_chunk = PROTOCOL_MAX_PAYLOAD_SIZE - 3; // Lo que sobra para datos

    uint8_t flag =0;
    uint8_t short_cmd[2] = {0x00,0x00};
    while (1){

        
         //Esto esta bloqueado hasta que el master hable, ya sea como respuesta a una no-conexión que ennviamos antes o proque quizo cambiar las credenciales
        n = xMessageBufferReceive(buff, entry_buffer, PROTOCOL_MAX_PAYLOAD_SIZE, portMAX_DELAY);
        
        
        ESP_LOGI(TAG, " LLego %d RAW: %d %d %d %d %d %d %d %d %d %d", n,
                                                        entry_buffer[0],
                                                        entry_buffer[1],
                                                        entry_buffer[2],
                                                        entry_buffer[3],
                                                        entry_buffer[4],
                                                        entry_buffer[5],
                                                        entry_buffer[6],
                                                        entry_buffer[7],
                                                        entry_buffer[8],
                                                        entry_buffer[9]);
                                                        

        // Aseguramos que llegó al menos el encabezado completo
        if (n >= 3) {
            uint8_t tipo         = entry_buffer[0]; // 1 = SSID, 2 = Clave
            uint8_t chunk_actual = entry_buffer[1]; // Posición (0, 1, 2...)
            uint8_t total_chunks = entry_buffer[2]; // Cantidad total
            uint8_t data_len     = n - 3;           // Cuántos bytes de texto real llegaron

            // Calculamos en qué parte del arreglo local va este pedazo
            uint16_t offset = (chunk_actual - 1) * max_data_per_chunk;
            
            switch (tipo) {
                case WIFI_CHNG_SSID_MSJ: // Modifico SSID
                    ESP_LOGI(TAG,"CAMBIANDO SSID");
                    if (chunk_actual == 1) {
                        memset(aux_nombre_red, 0, sizeof(aux_nombre_red)); // Limpio todo en el primer mensaje
                    }
                    
                    // Verifico que no me pase del tamaño máximo de la variable
                    if ((offset + data_len) < sizeof(aux_nombre_red)) {
                        memcpy(&aux_nombre_red[offset], &entry_buffer[3], data_len); 
                    }

                    //Si terminé levanto la flag de que hay una version nueva
                    if(chunk_actual == total_chunks){
                        //Si termino de mandar, le mando a la camara el nombre nuevo y pongo en ready para hacer el cambio
                        encolar(aux_nombre_red,UART_CAM_SSID_CMD);
                        flag +=1;
                    }
                    break;

                case WIFI_CHNG_PASS_MSJ: // Modifico Contraseña
                    ESP_LOGI(TAG,"CAMBIANDO CONTRA");
                    if (chunk_actual == 1) {
                        memset(aux_clave, 0, sizeof(aux_clave)); // Limpio todo en el primer mensaje
                    }
                    
                    if ((offset + data_len) < sizeof(aux_clave)) {
                        memcpy(&aux_clave[offset], &entry_buffer[3], data_len);
                    }
                    //Si terminé levanto la flag de que hay una version nueva
                    if(chunk_actual == total_chunks){
                        //Si termino de mandar, le mando a la camara el nombre nuevo y pongo en ready para hacer el cambio
                        encolar(aux_clave,UART_CAM_PASS_CMD);
                        flag +=1;                    
                    }
                    break;

                case WIFI_PRENDER_MSJ: //Manda  aencender/reconectar
                    ESP_LOGI("TAG","MANDADO A CONECTAR");
                    short_cmd[0]=UART_CAM_WFON_CMD;
                    cam_uart_send(short_cmd, 2);
                    break;
                
                case WIFI_APAGAR_MSJ: //Apagar para ahorro de energía
                    ESP_LOGI("TAG","MANDADO A DESCONECTAR");
                    short_cmd[0]=UART_CAM_WFOFF_CMD;
                    cam_uart_send(short_cmd, 2);
                    break;

                default:
                    ESP_LOGW("WIFI", "PARAMETRO DESCONOCIDO TIPO: %d", tipo);
                    break;
            }

            // Si estan por cambiarse ambas, las cambio y reconecto
            if (flag ==2) {
                    flag=0;
                    short_cmd[0]=UART_CAM_WFRECONFIG_CMD;
                    cam_uart_send(short_cmd, 2);
            }
        }
    }
}

