#if defined(LUMI_WIFI_BANK) && LUMI_WIFI_BANK
#include "control_banco.hpp"
#include <cmath>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include "cJSON.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "driver/usb_serial_jtag.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "esp_http_client.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "lwip/sockets.h"
#include "lwip/tcp.h"

#ifndef LUMI_ENABLE_POWER
#define LUMI_ENABLE_POWER 0
#endif
constexpr bool POWER = LUMI_ENABLE_POWER != 0;
static BancoMotor bank(0);
static SemaphoreHandle_t mutex;
static uint32_t now_ms() { return static_cast<uint32_t>(esp_timer_get_time() / 1000); }
static int applied = 0;
static bool network_ready = false; // Protected by mutex.
static bool http_selftest = false, station_connected = false;
static uint32_t http_requests = 0;
static bool udp_ready = false, udp_selftest = false;
static esp_err_t open_http_socket(httpd_handle_t, int fd) {
    // Control/status responses are small: do not wait for Nagle/delayed ACK batching.
    int enabled = 1;
    return setsockopt(fd,IPPROTO_TCP,TCP_NODELAY,&enabled,sizeof(enabled)) == 0 ? ESP_OK : ESP_FAIL;
}

static void outputs(int target) {
    if (!POWER) target = 0;
    if (applied * target < 0) target = 0;
    if (target == applied) return;
    // A zero-output interval is mandatory before any sign change.
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
    gpio_set_level(GPIO_NUM_4, target > 0);
    gpio_set_level(GPIO_NUM_5, target < 0);
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, std::abs(target) * 1023 / 1000);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
    applied = target;
}
static void stop(const char* reason) {
    xSemaphoreTake(mutex, portMAX_DELAY);
    bank.stop(reason, true);
    xSemaphoreGive(mutex);
}
static bool number(cJSON* body, const char* name, uint32_t& out) {
    cJSON* value = cJSON_GetObjectItemCaseSensitive(body, name);
    if (!cJSON_IsNumber(value) || !std::isfinite(value->valuedouble) ||
        value->valuedouble < 0 || value->valuedouble > UINT32_MAX ||
        std::floor(value->valuedouble) != value->valuedouble) return false;
    out = static_cast<uint32_t>(value->valuedouble); return true;
}
static esp_err_t respond(httpd_req_t* req, const char* json, bool ok = true) {
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    if (!ok) httpd_resp_set_status(req, "409 Conflict");
    return httpd_resp_send(req, json, HTTPD_RESP_USE_STRLEN);
}
// Shared snapshot; issuing a ticket does not enable or renew motion.
static void snapshot(char* message, size_t size, bool ok, uint32_t request = 0) {
    xSemaphoreTake(mutex, portMAX_DELAY);
    uint32_t now = now_ms();
    bank.tick(now);
    uint32_t ticket = bank.issue_ticket(now);
    const char* movement = bank.duty > 0 ? "adelante" : bank.duty < 0 ? "atras" : "parar";
    snprintf(message, size,
        "{\"ok\":%s,\"request\":%lu,\"mensaje\":\"%s\",\"camara\":false,\"modo\":\"motores_esp\",\"banco\":{\"enrolamiento\":\"no_disponible\","
        "\"protocolo_control\":3,\"ticket\":%lu,\"movimiento\":\"%s\",\"boot\":%lu,\"epoch\":%lu,\"seq\":%lu,\"uptime_ms\":%lu,"
        "\"habilitado\":%s,\"dry_run\":%s,\"pwm_ordenado\":%d,\"pwm_aplicado\":%d,"
        "\"fallo\":\"%s\",\"ultimo_rechazo\":\"%s\",\"intervalo_orden_ms\":%lu,"
        "\"canal\":\"A\",\"limite_pwm\":%d,\"max_pulso_ms\":%lu}}",
        ok ? "true" : "false", static_cast<unsigned long>(request),
        ok ? "Orden aceptada" : "Orden rechazada; revisar estado",
        static_cast<unsigned long>(ticket), movement,
        static_cast<unsigned long>(bank.boot), static_cast<unsigned long>(bank.epoch),
        static_cast<unsigned long>(bank.seq), static_cast<unsigned long>(now),
        bank.armed ? "true" : "false", POWER ? "false" : "true", bank.duty / 10,
        (bank.armed ? applied : 0) / 10, bank.fault, bank.rejection,
        static_cast<unsigned long>(bank.gap_ms), BANK_PWM_PERCENT, static_cast<unsigned long>(BANK_MAX_PULSE_MS));
    xSemaphoreGive(mutex);
}
static esp_err_t state_response(httpd_req_t* req, bool ok) {
    char message[1024];
    xSemaphoreTake(mutex, portMAX_DELAY); ++http_requests; xSemaphoreGive(mutex);
    snapshot(message,sizeof(message),ok);
    return respond(req,message,ok);
}
static bool accept(cJSON* body, int mode, int duty) {
    uint32_t boot = 0, epoch = 0, seq = 0, ticket = 0;
    bool valid = body && cJSON_IsObject(body) && number(body,"boot",boot) &&
        number(body,"epoch",epoch) && number(body,"seq",seq) && number(body,"ticket",ticket);
    xSemaphoreTake(mutex, portMAX_DELAY);
    bool accepted = valid && bank.command(now_ms(),boot,epoch,seq,ticket,mode,duty);
    if (!valid) bank.stop("peticion_invalida",true);
    xSemaphoreGive(mutex);
    return accepted;
}
static esp_err_t state(httpd_req_t* req) { return state_response(req, true); }
static esp_err_t command(httpd_req_t* req) {
    // Stop always wins and invalidates queued commands by advancing epoch.
    if (!strcmp(req->uri, "/api/motores/parar")) {
        stop("parada");
        char discard[160]; int remaining = req->content_len;
        if (remaining > 160) return respond(req, "{\"mensaje\":\"Parado; cuerpo excesivo\"}", false);
        while (remaining > 0) {
            int got = httpd_req_recv(req, discard, remaining);
            if (got <= 0) break;
            remaining -= got;
        }
        return respond(req, "{\"mensaje\":\"Salidas deshabilitadas\"}");
    }
    int mode = 0, duty = 0;
    if (!strcmp(req->uri, "/api/motores/habilitar")) mode = 1;
    else if (!strcmp(req->uri, "/api/motores/adelante")) { mode = 2; duty = BANK_DUTY; }
    else if (!strcmp(req->uri, "/api/motores/atras")) { mode = 2; duty = -BANK_DUTY; }
    if (!mode || req->content_len <= 0 || req->content_len > 160) {
        stop("peticion_invalida"); return respond(req, "{\"mensaje\":\"Orden no permitida\"}", false);
    }
    char buffer[161] = {}; int offset = 0;
    while (offset < req->content_len) {
        int got = httpd_req_recv(req, buffer + offset, req->content_len - offset);
        if (got <= 0) {
            stop("peticion_incompleta");
            return respond(req, "{\"mensaje\":\"Peticion incompleta\"}", false);
        }
        offset += got;
    }
    const char* end = nullptr;
    cJSON* body = cJSON_ParseWithOpts(buffer, &end, true);
    bool accepted = accept(body,mode,duty);
    cJSON_Delete(body);
    return state_response(req, accepted);
}
static void event(void*, esp_event_base_t, int32_t id, void*) {
    if (id == WIFI_EVENT_AP_STACONNECTED || id == WIFI_EVENT_AP_STADISCONNECTED) {
        xSemaphoreTake(mutex,portMAX_DELAY);
        station_connected = id == WIFI_EVENT_AP_STACONNECTED;
        if (!station_connected) bank.stop("wifi_desconectado",true);
        xSemaphoreGive(mutex);
    }
}
// Dedicated datagrams avoid HTTP head-of-line blocking. No retransmit of motion.
static void udp_server(void*) {
    int fd = socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    sockaddr_in address = {}; address.sin_family = AF_INET;
    address.sin_port = htons(8082); address.sin_addr.s_addr = htonl(INADDR_ANY);
    if (fd < 0 || bind(fd,reinterpret_cast<sockaddr*>(&address),sizeof(address)) != 0) {
        if (fd >= 0) close(fd);
        vTaskDelete(nullptr); return;
    }
    xSemaphoreTake(mutex,portMAX_DELAY); udp_ready = true; xSemaphoreGive(mutex);
    for (;;) {
        char data[513] = {}, reply[1024]; sockaddr_in peer = {}; socklen_t size = sizeof(peer);
        int got = recvfrom(fd,data,sizeof(data)-1,0,reinterpret_cast<sockaddr*>(&peer),&size);
        if (got <= 0) { vTaskDelay(pdMS_TO_TICKS(5)); continue; }
        cJSON* body = cJSON_ParseWithOpts(data,nullptr,true);
        uint32_t request = 0;
        cJSON* action = body ? cJSON_GetObjectItemCaseSensitive(body,"action") : nullptr;
        bool ok = body && number(body,"request",request) && cJSON_IsString(action);
        if (ok) {
            const char* name = action->valuestring;
            if (!strcmp(name,"ping")) { /* Read-only: no watchdog renewal. */ }
            else if (!strcmp(name,"parar")) stop("parada");
            else if (!strcmp(name,"habilitar")) ok = accept(body,1,0);
            else if (!strcmp(name,"adelante")) ok = accept(body,2,BANK_DUTY);
            else if (!strcmp(name,"atras")) ok = accept(body,2,-BANK_DUTY);
            else { ok = false; stop("orden_invalida"); }
        } else stop("peticion_invalida");
        cJSON_Delete(body);
        snapshot(reply,sizeof(reply),ok,request);
        sendto(fd,reply,strlen(reply),0,reinterpret_cast<sockaddr*>(&peer),size);
    }
}
static bool probe_udp() {
    // Only PING, never arm or drive physical outputs.
    int fd = socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if (fd < 0) return false;
    timeval timeout = {}; timeout.tv_usec = 200000;
    setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));
    sockaddr_in dst = {}; dst.sin_family = AF_INET; dst.sin_port = htons(8082);
    dst.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    bool valid = true;
    for (int i=0;i<3 && valid;++i) {
        const char* ping = "{\"action\":\"ping\",\"request\":17}";
        sendto(fd,ping,strlen(ping),0,reinterpret_cast<sockaddr*>(&dst),sizeof(dst));
        char data[1024] = {};
        int got = recv(fd,data,sizeof(data)-1,0);
        cJSON* json = got > 0 ? cJSON_Parse(data) : nullptr;
        cJSON* state = json ? cJSON_GetObjectItemCaseSensitive(json,"banco") : nullptr;
        cJSON* protocol = state ? cJSON_GetObjectItemCaseSensitive(state,"protocolo_control") : nullptr;
        cJSON* pwm = state ? cJSON_GetObjectItemCaseSensitive(state,"pwm_ordenado") : nullptr;
        valid = json && cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(json,"ok")) &&
            cJSON_IsNumber(protocol) && protocol->valueint == 3 &&
            cJSON_IsNumber(pwm) && pwm->valueint == 0 &&
            cJSON_IsFalse(cJSON_GetObjectItemCaseSensitive(state,"habilitado"));
        cJSON_Delete(json);
    }
    close(fd); return valid;
}
struct HttpProbe { char data[1024] = {}; size_t used = 0; };
static esp_err_t probe_event(esp_http_client_event_t* event) {
    auto* probe = static_cast<HttpProbe*>(event->user_data);
    if (event->event_id == HTTP_EVENT_ON_DATA) {
        if (probe->used + event->data_len >= sizeof(probe->data)) return ESP_FAIL;
        memcpy(probe->data + probe->used,event->data,event->data_len);
        probe->used += event->data_len;
    }
    return ESP_OK;
}
static bool probe_http() {
    // GET only. This never enables or requests any motor output.
    for (int i = 0; i < 12; ++i) {
        HttpProbe probe;
        esp_http_client_config_t config = {};
        config.url = "http://127.0.0.1:8080/api/estado";
        config.timeout_ms = 1500;
        config.event_handler = probe_event;
        config.user_data = &probe;
        auto client = esp_http_client_init(&config);
        if (!client) return false;
        esp_err_t result = esp_http_client_perform(client);
        int status = esp_http_client_get_status_code(client);
        esp_http_client_cleanup(client);
        cJSON* json = cJSON_Parse(probe.data);
        cJSON* state = json ? cJSON_GetObjectItemCaseSensitive(json,"banco") : nullptr;
        bool valid = result == ESP_OK && status == 200 && state &&
            cJSON_IsFalse(cJSON_GetObjectItemCaseSensitive(state,"habilitado")) &&
            cJSON_IsNumber(cJSON_GetObjectItemCaseSensitive(state,"pwm_ordenado")) &&
            cJSON_GetObjectItemCaseSensitive(state,"pwm_ordenado")->valueint == 0;
        cJSON_Delete(json);
        if (!valid) return false;
    }
    return true;
}
static void start_wifi() {
    // RAM storage: do not erase the previous user's NVS if initialization fails.
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_ap();
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, event, nullptr));
    wifi_config_t config = {};
    strcpy(reinterpret_cast<char*>(config.ap.ssid), "LUMI-BANCO");
    strcpy(reinterpret_cast<char*>(config.ap.password), "LumiMotores26");
    config.ap.ssid_len = strlen("LUMI-BANCO"); config.ap.channel = 1;
    config.ap.max_connection = 1; config.ap.authmode = WIFI_AUTH_WPA2_PSK;
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &config));
    ESP_ERROR_CHECK(esp_wifi_start());
    httpd_config_t http = HTTPD_DEFAULT_CONFIG();
    http.server_port = 8080; http.max_open_sockets = 4;
    http.open_fn = open_http_socket;
    http.lru_purge_enable = true;
    http.keep_alive_enable = true;
    http.keep_alive_idle = 3; http.keep_alive_interval = 1; http.keep_alive_count = 2;
    http.recv_wait_timeout = 1; http.send_wait_timeout = 1;
    http.uri_match_fn = httpd_uri_match_wildcard;
    httpd_handle_t server = nullptr;
    ESP_ERROR_CHECK(httpd_start(&server, &http));
    httpd_uri_t get = {}; get.uri = "/api/estado"; get.method = HTTP_GET; get.handler = state;
    ESP_ERROR_CHECK(httpd_register_uri_handler(server, &get));
    httpd_uri_t post = {}; post.uri = "/api/motores/*"; post.method = HTTP_POST; post.handler = command;
    ESP_ERROR_CHECK(httpd_register_uri_handler(server, &post));
    xSemaphoreTake(mutex,portMAX_DELAY);
    network_ready = true;
    xSemaphoreGive(mutex);
    const char* ready = "LUMI_WIFI_AP_READY ip=192.168.4.1 port=8080\n";
    usb_serial_jtag_write_bytes(ready,strlen(ready),0);
    xTaskCreate(udp_server,"control_udp",6144,nullptr,4,nullptr);
    vTaskDelay(pdMS_TO_TICKS(100));
    bool udp_tested = probe_udp();
    bool tested = probe_http();
    xSemaphoreTake(mutex,portMAX_DELAY);
    http_selftest = tested; udp_selftest = udp_tested;
    xSemaphoreGive(mutex);
}
extern "C" void app_main() {
    // Boot self-tests are independent of GPIO and never request physical movement.
    if (!banco_selftest()) abort();
    bank = BancoMotor(esp_random());
    mutex = xSemaphoreCreateMutex(); if (!mutex) abort();
    gpio_config_t pins = {};
    pins.pin_bit_mask = (1ULL<<4)|(1ULL<<5)|(1ULL<<6)|(1ULL<<7)|(1ULL<<15)|(1ULL<<16);
    pins.mode = GPIO_MODE_OUTPUT; ESP_ERROR_CHECK(gpio_config(&pins));
    for (auto pin : {GPIO_NUM_4,GPIO_NUM_5,GPIO_NUM_6,GPIO_NUM_7,GPIO_NUM_15,GPIO_NUM_16}) gpio_set_level(pin,0);
    ledc_timer_config_t timer = {}; timer.speed_mode = LEDC_LOW_SPEED_MODE;
    timer.duty_resolution = LEDC_TIMER_10_BIT; timer.timer_num = LEDC_TIMER_0;
    timer.freq_hz = 1000; timer.clk_cfg = LEDC_AUTO_CLK; ESP_ERROR_CHECK(ledc_timer_config(&timer));
    ledc_channel_config_t pwm = {}; pwm.gpio_num = 6; pwm.speed_mode = LEDC_LOW_SPEED_MODE;
    pwm.channel = LEDC_CHANNEL_0; pwm.timer_sel = LEDC_TIMER_0;
    ESP_ERROR_CHECK(ledc_channel_config(&pwm));
    usb_serial_jtag_driver_config_t usb = {}; usb.rx_buffer_size = 256; usb.tx_buffer_size = 1024;
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&usb));
    char ready[128];
    int ready_size=snprintf(ready,sizeof(ready),"LUMI_WIFI_BANK SELFTEST_PASS power=%d channel=A limit=%d%%\n",POWER?1:0,BANK_PWM_PERCENT);
    usb_serial_jtag_write_bytes(ready,ready_size,0);
    // HTTP runs in its own task. Motor expiry never waits for HTTP reads.
    xTaskCreate([](void*) { start_wifi(); vTaskDelete(nullptr); },"wifi_start",8192,nullptr,3,nullptr);
    uint32_t report = 0;
    for (;;) {
        xSemaphoreTake(mutex,portMAX_DELAY);
        bank.tick(now_ms()); outputs(bank.armed ? bank.duty : 0);
        if (now_ms() - report >= 1000) {
            char status[512];
            int n = snprintf(status,sizeof(status),
                "{\"wifi_bank\":true,\"selftest\":true,\"wifi_ready\":%s,\"uptime_ms\":%lu,\"power\":%s,\"armed\":%s,\"pwm\":%d,\"fault\":\"%s\",\"epoch\":%lu,\"seq\":%lu,\"gap_ms\":%lu,\"rejection\":\"%s\",\"http_test\":%s,\"http_requests\":%lu,\"phone_connected\":%s,\"protocol\":3,\"udp_ready\":%s,\"udp_test\":%s,\"pwm_limit\":%d,\"max_pulse_ms\":%lu}\n",
                network_ready?"true":"false",static_cast<unsigned long>(now_ms()),
                POWER ? "true":"false",bank.armed?"true":"false",applied,bank.fault,
                static_cast<unsigned long>(bank.epoch),static_cast<unsigned long>(bank.seq),
                static_cast<unsigned long>(bank.gap_ms),bank.rejection,
                http_selftest?"true":"false",static_cast<unsigned long>(http_requests),
                station_connected?"true":"false",udp_ready?"true":"false",udp_selftest?"true":"false",BANK_PWM_PERCENT,static_cast<unsigned long>(BANK_MAX_PULSE_MS));
            usb_serial_jtag_write_bytes(status,n,0); report = now_ms();
        }
        xSemaphoreGive(mutex);
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}
#endif
