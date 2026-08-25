idf_component_register(SRCS "uart_cam.c"  "camara.c" 
                            "app_wifi.c"  
                            "main.c" 
                    INCLUDE_DIRS "."
                    REQUIRES mbedtls 
                             esp-idf-pn532 
                             esp_wifi 
                             esp_event 
                             nvs_flash 
                             esp_http_client)