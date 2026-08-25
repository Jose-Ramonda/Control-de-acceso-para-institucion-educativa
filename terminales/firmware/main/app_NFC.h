/*
*   Archivo de cabecera de manager de lectura de datos NFC mediante sensor pn532
*   Se nutre de comoponente "garag__esp-idf-pn532", el cual es limitado, ya que el módulo pn532
*   no está pensado para operar con tags ntag213/15/16 si no con tags mifare. Se añaden funciones complementarias
*   Para expandir la librería así como las propias de la aplicación
*   Autor: José Ramonda
*   Ultima actualización: 27/4/2026
*/

#include "pn532_driver_spi.h"


//Modo de conectividad: I2C 
// I2C mode needs only SDA, SCL and IRQ pins. RESET pin will be used if valid.
// IRQ pin can be used in polling mode or in interrupt mode. Use menuconfig to select mode.

#define DUMMY_PIN (-1)  //Ya no mando pines válidos así no crea el bus, lo creo afuera
//#define RESET_PIN  (-1) //Para el modo i2c el oin no funciona, reseteo de forma manual
#define IRQ_PIN    (21) //Las interrupciones del componente deben activarse en el menuconfig

//PAra SPI
#define RESET_PIN      (-1)

#define SPI_CS         (5)
#define SPI_SCK        (18)
#define SPI_MISO       (19)
#define SPI_MOSI       (23)
#define SPI_HOST_NFC   (SPI3_HOST)//(SPI3_HOST)
#define SPI_CLOCKRATE 100000 //#define SPI_CLOCKRATE  (1000000)

//Comandos de NTAG 21X que no existen en la librería
#define NTAG_COMMAND_READ_CNT 0x39  //Comando leer contador
#define NTAG_COMMAND_READ      0X30
#define NTAG_COMMAND_FAST_READ 0X3A
#define NTAG_COMMAND_WRITE 0xA2
#define NTAG_COMMAND_PWD_AUTH 0x1B


//Direcciones de memoria
#define NTAG_ADDR_CNT   0x02   //Dirección del contador para acceder por readcounter
#define NTAG_ADDR_MIRROR_CNT    0x0A    //Dirección donde esta el contador copiado
//Direccion para configurar el espejo del contador y desde donde la clave
// MIRROR | RFUI | MIRROR_PAGE  | AUTH0
#define NTAG213_ADDR_MIRROR 0x29 
#define NTAG215_ADDR_MIRROR 0x83 
#define NTAG216_ADDR_MIRROR 0xE3
//Dirección para configurar el coontador, y las protecciones
// ACCESS | RFUI | RFUI | RFUI
#define NTAG213_ADDR_ACCES 0x2A 
#define NTAG215_ADDR_ACCES 0x84 
#define NTAG216_ADDR_ACCES 0xE4
//Dirección para el password (4 bytes)
#define NTAG213_ADDR_PWD 0x2B
#define NTAG215_ADDR_PWD 0x85 
#define NTAG216_ADDR_PWD 0xE5
//Dirección del ack del password (3 bytes)
#define NTAG213_ADDR_PACK 0x2C
#define NTAG215_ADDR_PACK 0x86 
#define NTAG216_ADDR_PACK 0xE6
//Valores de las páginas
#define NTAG_BYTE_RFUI 0x00 //bytes reservados valor por defecto 0
#define NTAG_BYTE_MIRROR 0x85 // espejo contador 01 | copiar a primer byte 00 | RFUI 0 | Modulacion fuerte 1 (por defecto) | RFUI 00  
#define NTAG_BYTE_MIRROR_PAGE 0x0A  //Espejar contador a página 10
#define NTAG_BYTE_AUTH0 0x04    //Proteger desde página 4 (deja libre la cofig)

#define NTAG_BYTE_ACCES 0x98 // prot 1 (proeje R&W) | CFGLCK 0 (bloquea NO TOCAR) | RFUI 0 | habilitar y protejer contador 11 | Limite de intentos 000 (tentativo)

#define PN532_RESPONSE_INCOMMUNICATETHRU    (0x43)//Adopto de la libreria pero no está implementado  


//Cosas específiccas de la especificación
#define HASH_OFFSET 14
#define PROG_TIMEOUT 50000 //Tiempo em ms que dura e modo programador de tags
//Funciones/tareas públicas
void nfc_init(void);
void quitari2c(void);