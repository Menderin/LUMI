idf_component_register(SRCS "main.cpp" "wifi_banco.cpp" INCLUDE_DIRS "." REQUIRES esp_driver_gpio esp_driver_ledc esp_driver_usb_serial_jtag esp_timer esp_hw_support esp_wifi esp_event esp_netif esp_http_server nvs_flash json esp_http_client)
target_compile_options(${COMPONENT_LIB} PRIVATE -std=gnu++17)

