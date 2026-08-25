/*
*   Archivo de parametros de configuración y macros globales
*   Contenidos:
*       UART
*
*   Autor: José Ramonda
*   Actualizado: 25/5/2026
*/



#pragma once


//Parámetros generales
#define TIEMPO_TIMBRE 2000
#define TIEMPO_PUERTA 5000

//Comunicaciones e identificación

#define MASTER_ID 0            // ID del maestro
#define NODO_ID_DEFAULT 10          // ID de este nodo por ahora


//Parámetros de red
#define WIFI_RETRY_NUM 100


//NUMEROS DE COMANDO

//Control 
#define CMD_ACK 0
#define CMD_NACK 1
#define CMD_RESET 2
#define CMD_READY 2
#define CMD_DOOR 3
#define CMD_WIFI_FAIL 4
#define CMD_RECOVER 5
#define CMD_PROGMODE 6
#define CMD_TAKE_PH 7


//Flujo
#define CMD_NFC 100 
#define CMD_WIFI 101
#define CMD_UID 102
#define CMD_URL 103





//Pines GPIO
#define GPIO_DI_TIMBRE 25
#define GPIO_DO_RELE_TIMBRE 32
#define GPIO_DO_RELE_PUERTA 33


//variables globalísimas para ver tema tiempos
#include "esp_timer.h"
#include <stdint.h>

extern int64_t ti;
extern int64_t tf;
