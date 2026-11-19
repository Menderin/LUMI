#if !defined(LUMI_WIFI_BANK) || !LUMI_WIFI_BANK
#include <algorithm>
#include <charconv>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "driver/usb_serial_jtag.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#ifndef LUMI_ENABLE_POWER
#define LUMI_ENABLE_POWER 0
#endif
// Proposed S3 pins. Power stays disabled in the banco build.
constexpr gpio_num_t IN1 = GPIO_NUM_4, IN2 = GPIO_NUM_5, ENA = GPIO_NUM_6;
constexpr gpio_num_t IN3 = GPIO_NUM_7, IN4 = GPIO_NUM_15, ENB = GPIO_NUM_16;
constexpr bool POWER = LUMI_ENABLE_POWER != 0;
constexpr uint32_t WATCHDOG_MS = 250;
constexpr int LIMIT = 200; // 20% initial bench cap, not calibrated speed.

uint32_t ms() { return static_cast<uint32_t>(esp_timer_get_time() / 1000); }
uint16_t crc16(const std::string& s) {
    uint16_t crc = 0xffff;
    for (unsigned char c : s) {
        crc ^= static_cast<uint16_t>(c) << 8;
        for (int i = 0; i < 8; ++i)
            crc = crc & 0x8000 ? (crc << 1) ^ 0x1021 : crc << 1;
    }
    return crc;
}
template<typename T> bool integer(const std::string& s, T& v, int base = 10) {
    auto r = std::from_chars(s.data(), s.data() + s.size(), v, base);
    return !s.empty() && r.ec == std::errc() && r.ptr == s.data() + s.size();
}
struct Command { uint32_t boot, seq, deadline, mode; int left, right; };
bool parse(const std::string& line, Command& c) {
    auto last = line.rfind(' ');
    uint16_t crc;
    if (last == std::string::npos || !integer(line.substr(last + 1), crc, 16) ||
        crc != crc16(line.substr(0, last))) return false;
    std::vector<std::string> f;
    size_t begin = 0;
    for (size_t end = 0; end <= last; ++end) {
        if (end == last || line[end] == ' ') {
            f.push_back(line.substr(begin, end - begin)); begin = end + 1;
        }
    }
    return f.size() == 7 && f[0] == "L1" && integer(f[1], c.boot) &&
        integer(f[2], c.seq) && integer(f[3], c.deadline) && integer(f[4], c.mode) &&
        integer(f[5], c.left) && integer(f[6], c.right) && c.mode <= 2 &&
        c.left >= -LIMIT && c.left <= LIMIT && c.right >= -LIMIT && c.right <= LIMIT &&
        (c.mode == 2 || (c.left == 0 && c.right == 0));
}
struct Motor {
    gpio_num_t a, b; ledc_channel_t channel; int applied = 0;
    void set(int target) {
        if (!POWER) target = 0;
        // A sign reversal spends one complete control iteration at zero.
        if (applied * target < 0) target = 0;
        ledc_set_duty(LEDC_LOW_SPEED_MODE, channel, 0);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, channel);
        gpio_set_level(a, target > 0); gpio_set_level(b, target < 0);
        ledc_set_duty(LEDC_LOW_SPEED_MODE, channel, std::abs(target) * 1023 / 1000);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, channel);
        applied = target;
    }
};
extern "C" void app_main() {
    gpio_config_t pins = {};
    pins.pin_bit_mask = (1ULL << IN1) | (1ULL << IN2) | (1ULL << IN3) |
        (1ULL << IN4) | (1ULL << ENA) | (1ULL << ENB);
    pins.mode = GPIO_MODE_OUTPUT;
    ESP_ERROR_CHECK(gpio_config(&pins));
    for (auto pin : {IN1, IN2, IN3, IN4, ENA, ENB}) gpio_set_level(pin, 0);
    ledc_timer_config_t timer = {};
    timer.speed_mode = LEDC_LOW_SPEED_MODE; timer.duty_resolution = LEDC_TIMER_10_BIT;
    timer.timer_num = LEDC_TIMER_0; timer.freq_hz = 1000; timer.clk_cfg = LEDC_AUTO_CLK;
    ESP_ERROR_CHECK(ledc_timer_config(&timer));
    int idx = 0;
    for (auto pin : {ENA, ENB}) {
        ledc_channel_config_t ch = {};
        ch.gpio_num = pin; ch.speed_mode = LEDC_LOW_SPEED_MODE;
        ch.channel = static_cast<ledc_channel_t>(idx++); ch.timer_sel = LEDC_TIMER_0;
        ESP_ERROR_CHECK(ledc_channel_config(&ch));
    }
    Motor left{IN1, IN2, LEDC_CHANNEL_0}, right{IN3, IN4, LEDC_CHANNEL_1};
    usb_serial_jtag_driver_config_t usb = {}; usb.rx_buffer_size = 512; usb.tx_buffer_size = 2048;
    ESP_ERROR_CHECK(usb_serial_jtag_driver_install(&usb));
    const uint32_t boot = esp_random();
    uint32_t seq = 0, last_valid = 0, deadline = 0, last_report = 0;
    int requested_left = 0, requested_right = 0;
    bool armed = false, overflow = false;
    const char* fault = "boot";
    std::string line;
    auto stop = [&](const char* reason) {
        armed = false; requested_left = requested_right = 0; fault = reason;
        left.set(0); right.set(0);
    };
    for (;;) {
        uint32_t now = ms();
        if (armed && (now - last_valid >= WATCHDOG_MS || static_cast<int32_t>(deadline - now) <= 0))
            stop("expired");
        char bytes[128];
        int count = usb_serial_jtag_read_bytes(bytes, sizeof(bytes), 0);
        for (int i = 0; i < count; ++i) {
            char ch = bytes[i];
            if (ch == '\n') {
                Command c{};
                now = ms();
                if (overflow || !parse(line, c)) stop("invalid");
                else if (c.boot != boot || c.seq <= seq) stop("sequence");
                else {
                    seq = c.seq;
                    int32_t remaining = static_cast<int32_t>(c.deadline - now);
                    if (c.mode == 0) stop("disabled");
                    else if (remaining <= 0 || remaining > WATCHDOG_MS) stop("stale");
                    else if (c.mode == 1) {
                        // A repeated arm cannot conceal a lost drive stream.
                        stop("none"); armed = true; deadline = c.deadline; last_valid = now;
                    } else if (!armed) stop("not_armed");
                    else {
                        requested_left = c.left; requested_right = c.right;
                        deadline = c.deadline; last_valid = now; fault = "none";
                    }
                }
                line.clear(); overflow = false;
            } else if (ch != '\r' && !overflow) {
                if (line.size() >= 120 || ch < 32 || ch > 126) {
                    overflow = true; line.clear(); stop("invalid");
                } else line += ch;
            }
        }
        left.set(armed ? requested_left : 0); right.set(armed ? requested_right : 0);
        now = ms();
        if (now - last_report >= 50) {
            char msg[384];
            int n = snprintf(msg, sizeof(msg),
                "{\"v\":1,\"boot\":%lu,\"seq\":%lu,\"uptime_ms\":%lu,\"armed\":%s,\"dry_run\":%s,\"left\":%d,\"right\":%d,\"left_pwm\":%d,\"right_pwm\":%d,\"fault\":\"%s\"}\n",
                static_cast<unsigned long>(boot), static_cast<unsigned long>(seq),
                static_cast<unsigned long>(now), armed ? "true" : "false", POWER ? "false" : "true",
                requested_left, requested_right, left.applied, right.applied, fault);
            // Non-blocking telemetry keeps a disconnected host out of the control path.
            usb_serial_jtag_write_bytes(msg, n, 0); last_report = now;
        }
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

#endif
