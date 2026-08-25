/*
*   Archivo de progrma de manejo de entradas y salidas digitales
*   Nativas o extensas del módulo PCF8574
*
*   Autor: José Ramonda
*   Ultima modificación: 25/5/2026 ¡Que viva la patria!
*/

#include "DIO.h"

#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/timers.h"
#include "esp_log.h"
#include "soc/gpio_periph.h"

#include "config.h"
#include "protocol.h"



static SemaphoreHandle_t cmd_puerta = NULL;
static SemaphoreHandle_t cmd_foto = NULL;
static TimerHandle_t xTimbreTimer;




static void IRAM_ATTR timbre_isr_handler(void* arg) {
    if (cmd_foto != NULL) {
        BaseType_t xHigherPriorityTaskWoken = pdFALSE;
        gpio_intr_disable(GPIO_DI_TIMBRE);  //Desactivo en lo que suena el timbre
        // A. Avisamos a la tarea de la foto
        xSemaphoreGiveFromISR(cmd_foto, &xHigherPriorityTaskWoken);

        // B. Arrancamos el timer con el período mínimo para que responda YA
        if (xTimbreTimer != NULL) {
            xTimerStartFromISR(xTimbreTimer, &xHigherPriorityTaskWoken);
        }

        if (xHigherPriorityTaskWoken == pdTRUE) {
            portYIELD_FROM_ISR();
        }
    }
    //ESP_LOGI("TIMBRE","Timbre pulsado");
    gpio_set_level(GPIO_DO_RELE_TIMBRE,1);
}



void vTimbreCallback(TimerHandle_t xTimer) {
    gpio_set_level(GPIO_DO_RELE_TIMBRE,0);
    gpio_intr_enable(GPIO_DI_TIMBRE);//Acá la retomo, para evitar rebotes
    ESP_LOGI("IRQ","Volviendo del timer");

}

void dio_init(void){
    
    gpio_config_t io_conf = {
        .intr_type = GPIO_INTR_NEGEDGE,       // Interrupción cuando va a GND (bajada)
        .pin_bit_mask = (1ULL << GPIO_DI_TIMBRE), 
        .mode = GPIO_MODE_INPUT,               
        .pull_up_en = GPIO_PULLUP_ENABLE,     // Pull-up interno para mantenerlo en 3.3V
        .pull_down_en = GPIO_PULLDOWN_DISABLE
    };
    gpio_config(&io_conf);
    
    

    

    //Enganchamos el manejador al pin del timbre
    gpio_isr_handler_add(GPIO_DI_TIMBRE, timbre_isr_handler, NULL);

    //Agarro el semaforo correspondiente
    cmd_puerta = protocol_get_ctrl_sem(CMD_DOOR);
    cmd_foto = protocol_get_ctrl_sem(CMD_TAKE_PH);
    xTimbreTimer = xTimerCreate("TimerTimbre", pdMS_TO_TICKS(TIEMPO_TIMBRE), pdFALSE, (void *) 0, vTimbreCallback);

    

    
    
    gpio_set_direction(GPIO_DO_RELE_PUERTA, GPIO_MODE_OUTPUT);
    gpio_set_level(GPIO_DO_RELE_PUERTA, 0); // Arranca apagado
    gpio_set_direction(GPIO_DO_RELE_TIMBRE, GPIO_MODE_OUTPUT);
    gpio_set_level(GPIO_DO_RELE_TIMBRE, 0); // Arranca apagado

    xTaskCreate(puerta_task,"DOOR",2048,NULL,8,NULL);

}

void puerta_task(void *pvParameters) {
    
    if (cmd_puerta == NULL) {
        ESP_LOGE("PUERTA", "No se pudo obtener el semáforo de puerta");
        vTaskDelete(NULL);
    }


    while(1){
        if (xSemaphoreTake(cmd_puerta, portMAX_DELAY) == pdTRUE) {
            
            gpio_set_level(GPIO_DO_RELE_PUERTA,1);
            composer(CMD_DOOR,0,NULL,NULL);//Envío confirmación
            //Bloque de código que calcula el timepo posterior a la confirmación de apertura
            tf = esp_timer_get_time();
            if(ti >0){
                int64_t deltaTus = tf-ti;
                float delta_ms = (float)deltaTus / 1000.0f;
                ESP_LOGW("T_RESPUESTA", "========================================");
                ESP_LOGW("T_RESPUESTA", "TIEMPO TOTAL REACCIÓN: %.2f ms (%lld us)", delta_ms, deltaTus);
                ESP_LOGW("T_RESPUESTA", "========================================");
                ti =0;
            }


            vTaskDelay(pdMS_TO_TICKS(TIEMPO_PUERTA));
            gpio_set_level(GPIO_DO_RELE_PUERTA,0);

        }                               
    }
}