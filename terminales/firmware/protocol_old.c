/*
*   Este arcivo contiene las funciones/tareas relativas a la clasificación de
*   tramas recibidas por RS485, su verificación y el formateo para el envío
*
*   Autor: José Ramonda
*   Actualizado 21/1/2026
*/

#include "protocol.h"
#include "app_uart.h"
#include "config.h"

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/stream_buffer.h"

static uint16_t id_nodo = NODO_ID_DEFAULT;  //Por ahora

void parser_task(void *pvParameters) { // Las tareas de FreeRTOS deben recibir (void *pvParameters)
    StreamBufferHandle_t rx_stream = uart_get_rx_streambuffer();

    if (rx_stream == NULL) {
        ESP_LOGE("PROTOCOL", "El buffer no existe, abortando");
        vTaskDelete(NULL);
    }

    encabezado_t header;
    uint8_t byte_in;
    uint8_t state = WAIT_STATE;
    uint8_t data[MAX_PAYLOAD_SIZE];

    while (1) {
        // Leemos el primer byte disponible
        if (xStreamBufferReceive(rx_stream, &byte_in, 1, portMAX_DELAY) == 1) {

            switch (state) {
                case WAIT_STATE:
                    if (byte_in == PROTOCOL_START_BYTE) {
                        state = HEADER_READING_STATE;
                    }
                    break; // SIEMPRE break para esperar el siguiente byte o procesar

                case HEADER_READING_STATE:
                    // IMPORTANTE: Como ya tenemos un byte en 'byte_in', este es el ID.
                    header.id = byte_in;
                    
                    // Ahora sí, leemos el RESTO del encabezado (comand y data_size)
                    // Faltan 2 bytes para completar la estructura encabezado_t
                    if (xStreamBufferReceive(rx_stream, &header.comand, 2, pdMS_TO_TICKS(50)) == 2) {
                        if (header.id == id_nodo) {
                            state = (header.data_size > 0) ? PAYLOAD_READING_STATE : WAIT_STATE;
                            if (header.data_size == 0) {
                                ESP_LOGI("PROTOCOL", "Orden recibida sin payload: %d", header.comand);
                            }
                        } else {
                            state = WAIT_STATE; // No es para mí
                        }
                    } else {
                        state = WAIT_STATE; // Timeout o trama mal formada
                    }
                    break;

                case PAYLOAD_READING_STATE:
                    // Leemos el payload completo
                    if (xStreamBufferReceive(rx_stream, data, header.data_size, pdMS_TO_TICKS(100)) == header.data_size) {
                        ESP_LOGI("PROTOCOL", "Payload recibido correctamente");
                        // Aquí llamarías a la función que procesa la orden
                    }
                    state = WAIT_STATE;
                    break;
            }
        }
    }
}