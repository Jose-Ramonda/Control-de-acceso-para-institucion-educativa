idf_component_register(SRCS  "camara.c" 
                            "app_NFC.c" 
                            "app_wifi.c" 
                            "main.c" 
                            "app_uart.c" 
                            "protocol.c"
                            "DIO.c"
                            "uart_cam.c"
                    INCLUDE_DIRS "."
                    REQUIRES mbedtls 
                             esp-idf-pn532 
                             esp_wifi 
                             esp_event 
                             nvs_flash 
                             esp_http_client
                             esp_timer)