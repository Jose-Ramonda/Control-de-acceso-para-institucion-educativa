/*
*   Archivo de programa de manager de conexión WiFI
*   Basado en ejemplo wifi/getting_started/station_example_main.c
*   Autor: José Ramonda
*   Ultima actualización: 10/4/2026
*/


#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"

#include "freertos/message_buffer.h"

#include "app_wifi.h"
#include "config.h"
#include "uart_cam.h"
/* FreeRTOS event group to signal when we are connected*/
static EventGroupHandle_t s_wifi_event_group;   //Event group de freertos, es como un arreglo de flags

#define WIFI_CONNECTED_BIT BIT0 
#define WIFI_FAIL_BIT      BIT1
#define WIFI_SSIDTOCHANGE_BIT BIT2
#define WIFI_PASSWORDTOCHANGE_BIT BIT3
#define WIFI_CREDENCIALSCHANGED_BIT BIT4
#define WIFI_MUSTBE_BIT BIT5
#define WIFI_SAVE_CREDENTIALS_BIT BIT6
#define WIFI_RETRYING_BIT BIT7


static uint8_t val = WIFI_FAIL_MSJ;
uint8_t ipmsj[7];
static const char *TAG = "wifi station"; 

static int s_retry_num = 0;


static uint8_t nombre_red[32];  //Credenciales de acceso
static uint8_t clave[64]; 


void wifi_save_credentials(void) {
    nvs_handle_t nvs;
    ESP_LOGI("TAG","Guardando CREDENCIALES");
    if (nvs_open("wifi", NVS_READWRITE, &nvs) == ESP_OK) {
        nvs_set_str(nvs, "ssid", (char*)nombre_red);
        nvs_set_str(nvs, "pass", (char*)clave);
        nvs_commit(nvs);
        nvs_close(nvs);

        ESP_LOGI(TAG, "Credenciales guardadas en NVS");
        
    } else {
        ESP_LOGE(TAG, "Error abriendo NVS para guardar");
    }
    xEventGroupClearBits(s_wifi_event_group,WIFI_SAVE_CREDENTIALS_BIT);
}

void app_wifi_conect(){     //Intenta conectar 10 veces
    if (s_retry_num < WIFI_RETRY_NUM && nombre_red[0] != '\0' && nombre_red[0] != ' ') {
            esp_wifi_connect();
            s_retry_num++;
            //xEventGroupSetBits(s_wifi_event_group,WIFI_RETRYING_BIT);
            ESP_LOGI(TAG, "retry to connect to the AP, n %d",s_retry_num);
        } else {
            xEventGroupClearBits(s_wifi_event_group,WIFI_RETRYING_BIT);
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);  //Quitar, inncesario, mandar desde aqui
            //composer(CMD_WIFI,1,&val,NULL);
            uint8_t buff[2]={UART_CAM_WFOFF_CMD,0x00};
            cam_uart_send(buff,2);

            ESP_LOGE(TAG,"FALLO AL CONECTAR WIFI");//Aca hacer otra cosa mas que un log
        }
}

static void event_handler(void* arg, esp_event_base_t event_base,   //modificado de ejemplo
                                int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) { 

        xEventGroupSetBits(s_wifi_event_group,WIFI_RETRYING_BIT); //Ante un start intento conectar

    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        xEventGroupClearBits(s_wifi_event_group, WIFI_CONNECTED_BIT);   //Si desconecta limpio la flag
        EventBits_t bits = xEventGroupGetBits(s_wifi_event_group);
        ESP_LOGI("TAG","EVENTO DISCONECTED");
        if (bits & WIFI_MUSTBE_BIT){    //Si se desconect y deberia estar conectado
            xEventGroupSetBits(s_wifi_event_group,WIFI_RETRYING_BIT); //Intenta reconectar
            ESP_LOGI("TAG","EVENTO DISCONECTED ento al if");
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "got ip:" IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;
        xEventGroupClearBits(s_wifi_event_group,WIFI_RETRYING_BIT);
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT); //Solo levanto con Ip
        //Enviar comando de confirmacion con ip
        

        ipmsj[0] = UART_CAM_WFON_CMD;
        ipmsj[1]= 0x04;

        uint32_t ip = event->ip_info.ip.addr;

        ipmsj[2] = ip & 0xFF;
        ipmsj[3] = (ip >> 8) & 0xFF;
        ipmsj[4] = (ip >> 16) & 0xFF;
        ipmsj[5] = (ip >> 24) & 0xFF;

        //composer(CMD_WIFI, 5, ipmsj, NULL);
        cam_uart_send(ipmsj,6);
        EventBits_t bits = xEventGroupGetBits(s_wifi_event_group);
        if (bits & WIFI_CREDENCIALSCHANGED_BIT){    //Estado startet+disconected->reconect
            xEventGroupClearBits(s_wifi_event_group,WIFI_CREDENCIALSCHANGED_BIT);
            xEventGroupSetBits(s_wifi_event_group,WIFI_SAVE_CREDENTIALS_BIT);
        }
    }
}

void app_wifi_reconfig(){
    ESP_LOGI("TAG","Probando recambiar CREDENCIALES");
    esp_wifi_disconnect(); //Por las dudas desconectamos

    wifi_config_t wifi_config = {0};    //Extraido del init del ejemplo
    //Modificado, paso las credenciales de mis variables globales
    strncpy((char*)wifi_config.sta.ssid, (char*)nombre_red, sizeof(wifi_config.sta.ssid));
    strncpy((char*)wifi_config.sta.password, (char*)clave, sizeof(wifi_config.sta.password));

    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config) );
    xEventGroupSetBits(s_wifi_event_group, WIFI_CREDENCIALSCHANGED_BIT);    //Levanto para reescribir en flash
    //Reviso el estado y reinicio/reconecto siempre que se cambien las credenciales
    EventBits_t bits = xEventGroupGetBits(s_wifi_event_group);
    if (bits & WIFI_MUSTBE_BIT){    //Estado startet+disconected->reconect
        app_wifi_conect();  //inteto conectar
    }
    else{
    xEventGroupSetBits(s_wifi_event_group, WIFI_MUSTBE_BIT);//seteo el estado correcto
    ESP_ERROR_CHECK(esp_wifi_start()); //Esto dispara el evento que llama  a conect
    esp_wifi_set_ps(WIFI_PS_NONE);
    }

}

void app_wifi_task(void *pvParameters){  //Reemplaza al app main del ejemplo
    while(1){
        EventBits_t bits = xEventGroupWaitBits(
            s_wifi_event_group,
            WIFI_SAVE_CREDENTIALS_BIT | WIFI_RETRYING_BIT, // ← ambos
            pdTRUE,        // limpia los que despertaron
            pdFALSE,       // ANY → cualquiera alcanza
            portMAX_DELAY
        );

        if (bits & WIFI_SAVE_CREDENTIALS_BIT) {
            wifi_save_credentials();
        }
        if (bits & WIFI_RETRYING_BIT) {
            app_wifi_conect();
        }
    }    
}

void wifi_init_sta(void){    //Codigo del ejemplo modificado

    //Init del event group
    s_wifi_event_group = xEventGroupCreate();




    //Cargar lo que hay en flash a  la ram
    nvs_handle_t nvs;
    if (nvs_open("wifi", NVS_READONLY, &nvs) == ESP_OK) {
        size_t ssid_len = sizeof(nombre_red);
        size_t pass_len = sizeof(clave);

        memset(nombre_red, 0, sizeof(nombre_red));
        memset(clave, 0, sizeof(clave));
        if (nvs_get_str(nvs, "ssid", (char*)nombre_red, &ssid_len) != ESP_OK) {
            nombre_red[0] = '\0';
        }

        if(nvs_get_str(nvs, "pass", (char*)clave, &pass_len) != ESP_OK){
            clave[0]='\0';
        }

        nvs_close(nvs);
    }

    //Inits del wifi
    ESP_ERROR_CHECK(esp_netif_init());  //esp-inicia funciones de red (stack TCP-IP)

    ESP_ERROR_CHECK(esp_event_loop_create_default());   //esp inicializa bus de eventos
    esp_netif_create_default_wifi_sta();    //preaprara para usar esp como cliente de una red

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT(); //estructura de config de wifi, dejamos default
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));           //inicializa segun configs

    //Init de los eventos de sistema
    esp_event_handler_instance_t instance_any_id;   //declaro handlers de eventos
    esp_event_handler_instance_t instance_got_ip;

    //Y los creo con el "create"
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, //Reaccionar a evento de wifi
                                                        ESP_EVENT_ANY_ID,   //cualquiera que sea
                                                        &event_handler,    //dispara la func handler
                                                        NULL,   //Sin otros argumentos
                                                        &instance_any_id)); //Esto que apunta no se
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,   //Evento IP
                                                        IP_EVENT_STA_GOT_IP,    //Solo el caso de obtenr io
                                                        &event_handler, //Mismo reactor
                                                        NULL,   //Mismo argumento
                                                        &instance_got_ip)); //misma duda


    //DE nuevo wifi, aca cargo las credenciales que tome de ram, desordenado pero como en el ejemplo                                                 
    wifi_config_t wifi_config = {0};
    //Modificado, paso las credenciales de mis variables globales
    strncpy((char*)wifi_config.sta.ssid, (char*)nombre_red, sizeof(wifi_config.sta.ssid));
    strncpy((char*)wifi_config.sta.password, (char*)clave, sizeof(wifi_config.sta.password));

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA) );
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config) );
    
    xTaskCreate(app_wifi_task,"wifx",4096,NULL,2,NULL);    //Si le bajo el stack cague
}



void app_wifi_com_task(void *pvParameters){

    int n;
    MessageBufferHandle_t buff = get_msjbuff_wf();
    uint8_t entry_buffer[256];

    wifi_init_sta();
    while (1){

        
         //Esto esta bloqueado hasta que el master hable, ya sea como respuesta a una no-conexión que ennviamos antes o proque quizo cambiar las credenciales
        n = xMessageBufferReceive(buff, entry_buffer,256, portMAX_DELAY);
        
        
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
        if (n >= 2) {
            uint8_t tipo         = entry_buffer[0]; // 1 = SSID, 2 = Clave
            uint8_t data_len     = entry_buffer[1];           // Cuántos bytes de texto real llegaron

            // Calculamos en qué parte del arreglo local va este pedazo
            
            
            switch (tipo) {
                case UART_CAM_SSID_CMD: // Modifico SSID (¡Ahora viene entero!)
                    ESP_LOGI(TAG, "CAMBIANDO SSID - Estructura plana recibida");
                    
                    // 1. Limpiamos el buffer global de la cámara de prepo
                    memset(nombre_red, 0, sizeof(nombre_red)); 
                    
                    // 2. Copia segura: nos aseguramos de no pasarnos de los 31 caracteres + cero terminal
                    if(data_len < sizeof(nombre_red)){
                        memcpy(nombre_red, &entry_buffer[2], data_len); 
                    } else break;

                    ESP_LOGI(TAG, "Nuevo SSID guardado en RAM: %s", (char*)nombre_red);

                    // La flag se va poruqe tengo otro comando para mandar a cambiar
                    //xEventGroupSetBits(s_wifi_event_group, WIFI_SSIDTOCHANGE_BIT);
                    break;
                case UART_CAM_PASS_CMD: // Modifico SSID (¡Ahora viene entero!)
                    ESP_LOGI(TAG, "CAMBIANDO Password - Estructura plana recibida");
                    
                    // 1. Limpiamos el buffer global de la cámara de prepo
                    memset(clave, 0, sizeof(clave)); 
                    
                    // 2. Copia segura: nos aseguramos de no pasarnos de los 31 caracteres + cero terminal
                    if(data_len < sizeof(clave)){
                        memcpy(clave, &entry_buffer[2], data_len); 
                    } else break;

                    ESP_LOGI(TAG, "Nuevo SSID guardado en RAM: %s", (char*)clave);

                    // La flag se va poruqe tengo otro comando para mandar a cambiar
                    //xEventGroupSetBits(s_wifi_event_group, WIFI_SSIDTOCHANGE_BIT);
                    break;

                case UART_CAM_WFON_CMD: //Manda  aencender/reconectar
                    ESP_LOGI("TAG","MANDADO A CONECTAR");
                    s_retry_num =0; //Siempre reinicio para intentar conectar
                    EventBits_t bits = xEventGroupGetBits(s_wifi_event_group);
                    if (bits & WIFI_MUSTBE_BIT){    //Estado startet+disconected->reconect
                        app_wifi_conect();  //inteto conectar
                        
                    }
                    else{
                        xEventGroupSetBits(s_wifi_event_group, WIFI_MUSTBE_BIT);//seteo el estado correcto
                        ESP_ERROR_CHECK(esp_wifi_start() ); //Esto dispara el evento que llama  a conect
                        esp_wifi_set_ps(WIFI_PS_NONE);
                        ESP_LOGI("TAG","ACA MANDE EL START");
                    }
                    break;
                
                case UART_CAM_WFOFF_CMD: //Apagar para ahorro de energía
                    xEventGroupClearBits(s_wifi_event_group, WIFI_MUSTBE_BIT);  //Limpia
                    esp_wifi_disconnect();  //Desconecta
                    esp_wifi_stop();    //Apaga
                    //No pasa nada si se hace dos veces, no afecta
                    break;
                case UART_CAM_WFRECONFIG_CMD: //Si lelga el mensaje de reconectar
                    app_wifi_reconfig();
                    break;
                default:
                    ESP_LOGW("WIFI", "PARAMETRO DESCONOCIDO TIPO: %d", tipo);
                    break;
            }

        }
    }
    
}

