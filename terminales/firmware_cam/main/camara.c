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
#include "uart_cam.h"


static const char *TAG = "CAMARA";
static esp_http_client_handle_t http_client = NULL;
static char url_servidor[128] = "";
static SemaphoreHandle_t cmd_sem = NULL;

#if ESP_CAMERA_SUPPORTED
static camera_config_t camera_config = {
    .pin_pwdn = CAM_PIN_PWDN,
    .pin_reset = CAM_PIN_RESET,
    .pin_xclk = CAM_PIN_XCLK,
    .pin_sccb_sda = CAM_PIN_SIOD,
    .pin_sccb_scl = CAM_PIN_SIOC,

    .pin_d7 = CAM_PIN_D7,
    .pin_d6 = CAM_PIN_D6,
    .pin_d5 = CAM_PIN_D5,
    .pin_d4 = CAM_PIN_D4,
    .pin_d3 = CAM_PIN_D3,
    .pin_d2 = CAM_PIN_D2,
    .pin_d1 = CAM_PIN_D1,
    .pin_d0 = CAM_PIN_D0,
    .pin_vsync = CAM_PIN_VSYNC,
    .pin_href = CAM_PIN_HREF,
    .pin_pclk = CAM_PIN_PCLK,

    //XCLK 20MHz or 10MHz for OV2640 double FPS (Experimental)
    .xclk_freq_hz = 20000000,
    .ledc_timer = LEDC_TIMER_0,
    .ledc_channel = LEDC_CHANNEL_0,

    .pixel_format = PIXFORMAT_JPEG, //YUV422,GRAYSCALE,RGB565,JPEG
    .frame_size = FRAMESIZE_SVGA,    //QQVGA-UXGA, For ESP32, do not use sizes above QVGA when not JPEG. The performance of the ESP32-S series has improved a lot, but JPEG mode always gives better frame rates.

    .jpeg_quality = 12, //0-63, for OV series camera sensors, lower number means higher quality
    .fb_count = 2,       //When jpeg mode is used, if fb_count more than one, the driver will work in continuous mode.
    .fb_location = CAMERA_FB_IN_PSRAM,
    .grab_mode = CAMERA_GRAB_WHEN_EMPTY,
};

static esp_err_t init_camera(void)
{
    //initialize the camera
    //nvs_flash_init();
    esp_err_t err = esp_camera_init(&camera_config);
    if (err != ESP_OK)
    {
        ESP_LOGE(TAG, "Camera Init Failed");
        return err;
    }

    return ESP_OK;
}

#endif
void init_http_client() {//Inicicaliza cliente HTTP
    
    esp_http_client_config_t config = {
        .url = url_servidor, // Dirección destino
        .method = HTTP_METHOD_POST,               // Vamos a enviar datos, no a pedir
        .timeout_ms = 3000,                       // Si Node-RED no responde en 3s, abortamos
        .keep_alive_enable = true,                // Pedimos que la conexión TCP quede abierta
    };
    
    // Inicializamos el cliente con esa configuración
    http_client = esp_http_client_init(&config);
    
    // Pegamos la primera "etiqueta" en la caja: Le decimos al servidor que no corte la llamada
    esp_http_client_set_header(http_client, "Connection", "keep-alive");
}

esp_err_t send_pic(uint8_t *buffer, size_t len) {
    if (buffer == NULL || len == 0) {
        return ESP_ERR_INVALID_ARG;
    }

    // Por seguridad, si el tubo se destruyó, lo volvemos a crear
    if (http_client == NULL) {
        init_http_client();
    }

    // Pegamos la segunda "etiqueta": Le avisamos a Node-RED que los bytes son un JPEG
    esp_http_client_set_header(http_client, "Content-Type", "image/jpeg");

    // Metemos la foto adentro de la "caja" (Asignamos el payload)
    esp_http_client_set_post_field(http_client, (const char *)buffer, len);

    //Contador de 3 retys
    int conter = 0;
    // ¡DESPACHAMOS EL PAQUETE! (Esta función bloquea la tarea hasta que termina)
    esp_err_t err = esp_http_client_perform(http_client);


    while(err != ESP_OK){
        
        conter++;
        if(conter <3){
        ESP_LOGW(TAG,"ERROR AL ENVIAR INTENTO %d",conter);
        err = esp_http_client_perform(http_client);
        } else{
        // Como hubo un error de red, el "tubo" quedó sucio o roto.
        // Lo destruimos y lo ponemos en NULL para que la próxima foto fuerce un init nuevo.
        esp_http_client_cleanup(http_client);
        http_client = NULL;
        return err;
        }
    }

    ESP_LOGI(TAG,"ENVIADO BEM");
    return err; // Devolvemos el resultado a la camara_task
}

void url_task(void *pvParameters){
    nvs_handle_t nvs;
    if (nvs_open("url", NVS_READONLY, &nvs) == ESP_OK) {
        size_t url_len = sizeof(url_servidor);

        memset(url_servidor, 0, sizeof(url_servidor));
        if (nvs_get_str(nvs, "url", (char*)url_servidor, &url_len) != ESP_OK) {
            url_servidor[0] = '\0';
        }
        nvs_close(nvs);
    }
    MessageBufferHandle_t buff = get_msjbuff_url();
    uint8_t entry_buffer[256];
    while (1)
    {
        if(xMessageBufferReceive(buff, entry_buffer, 256, portMAX_DELAY)){
            uint16_t puerto = entry_buffer[4] | (entry_buffer[5] << 8); //Configuro el puerto
            snprintf(url_servidor, sizeof(url_servidor), "http://%d.%d.%d.%d:%d/upload",entry_buffer[0], entry_buffer[1], entry_buffer[2], entry_buffer[3], puerto);
            nvs_handle_t nvs_write;
            // Abrimos en modo READWRITE
            if (nvs_open("url", NVS_READWRITE, &nvs_write) == ESP_OK) {
                
                // Pisamos el valor de la key "url" con el nuevo string
                esp_err_t err_set = nvs_set_str(nvs_write, "url", url_servidor);
                
                if (err_set == ESP_OK) {
                    // CRÍTICO: nvs_commit es el que físicamente graba los electrones en la Flash
                    nvs_commit(nvs_write); 
                    ESP_LOGI("URL_TASK", "URL guardada exitosamente en NVS.");
                } else {
                    ESP_LOGE("URL_TASK", "Falló nvs_set_str: %s", esp_err_to_name(err_set));
                }
                
                // Cerramos siempre la llave
                nvs_close(nvs_write);
            }
            
            if(http_client !=NULL){
                esp_http_client_cleanup(http_client);
                http_client = NULL;
            }
            init_http_client();
        }

    }

}

void camara_task(void *pvParameters)
{
#if ESP_CAMERA_SUPPORTED
    if(ESP_OK != init_camera()) {
        return;
    }
    cmd_sem = get_fotosem();

    xTaskCreate(url_task, "URL", 4096, NULL, 4, NULL);
    
    while (1)
    {
        if (xSemaphoreTake(cmd_sem, portMAX_DELAY) == pdTRUE) {
            
            // 1. Encender Flash
            gpio_set_level(FLASH, 1);
            
            // 2. Pequeña guarda para que el sensor ajuste ganancia/luz si el flash estaba apagado
            vTaskDelay(pdMS_TO_TICKS(40));

            // 3. Obtener la foto más reciente (el driver descarta los frames viejos solo)
            camera_fb_t *pic = esp_camera_fb_get();

            if (pic) {
                // 4. Enviar imagen por HTTP
                send_pic(pic->buf, pic->len);
                
                // 5. Devolver el buffer al pool DMA
                esp_camera_fb_return(pic);
                
                gpio_set_level(FLASH, 0);

                // Notificar por UART interna
                uint8_t coso[2] = {UART_CAM_PH_CMD, 0x00};
                cam_uart_send(coso, 2);
            } else {
                ESP_LOGE(TAG, "Fallo al capturar frame");
                gpio_set_level(FLASH, 0);
            }
        } 
    }
#endif
}