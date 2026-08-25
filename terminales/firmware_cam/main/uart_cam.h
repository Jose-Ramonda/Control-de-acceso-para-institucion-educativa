/*
*   Archivo de cabeecera de tareas de manejo de interfaz UART 2 
*   Para comunicación de ESP32 con coprosesador ESP32 CAM
*   Autor: José Ramonda
*   Ultima actualización: 21/1/2026
*/
#pragma once

#include <stdint.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/stream_buffer.h"


#include "driver/uart.h"

#define UART_PORT          UART_NUM_2
#define UART_BAUD_RATE     115200

#define UART_TX_PIN        14
#define UART_RX_PIN        15
#define UART_RTS_PIN       UART_PIN_NO_CHANGE

#define UART_RX_BUF_SIZE   2048
#define UART_TX_BUF_SIZE   0    // sin buffer TX

#define UART_EVENT_QUEUE_SIZE    10   //Tamaño de la cola de eventos UART
#define UART_RX_STREAMBUFFER_SIZE  2048



void cam_uart_init(void);
void cam_uart_rx_task(void *pvParameters);

void cam_uart_send(uint8_t *trama, int len);

MessageBufferHandle_t get_msjbuff_wf(void);
MessageBufferHandle_t get_msjbuff_url(void);
SemaphoreHandle_t get_fotosem(void);

//Comandos de intercambio con camara
#define UART_CAM_OK_CMD 1
#define UART_CAM_NOK_CMD 2
#define UART_CAM_PH_CMD  4

#define UART_CAM_URL_CMD 16
#define UART_CAM_SSID_CMD 32
#define UART_CAM_PASS_CMD 64
#define UART_CAM_WFRECONFIG_CMD 128
#define UART_CAM_WFON_CMD 254
#define UART_CAM_WFOFF_CMD 8





