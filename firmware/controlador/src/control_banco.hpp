#pragma once
#include <cstdint>
#include <cstring>

// Candidate for the next supervised test. Do not infer a current limit from PWM.
constexpr int BANK_PWM_PERCENT = 20;
constexpr int BANK_DUTY = BANK_PWM_PERCENT * 10;
constexpr uint32_t BANK_MAX_PULSE_MS = 500;
// Only the ESP monotonic clock decides ticket age and watchdog expiry.
struct BancoMotor {
    struct Ticket { uint32_t value = 0, epoch = 0, issued = 0; };
    Ticket tickets[16];
    uint32_t boot, epoch = 1, seq = 0, expires = 0, pulse_start = 0;
    uint32_t next_ticket, ticket_slot = 0;
    bool armed = false, pulsing = false;
    int duty = 0;
    const char* fault = "inicio";
    const char* rejection = "ninguno";
    uint32_t last_rx = 0, gap_ms = 0;
    explicit BancoMotor(uint32_t id) : boot(id), next_ticket(id ^ 0x718cab13U) {}
    uint32_t issue_ticket(uint32_t now) {
        if (++next_ticket == 0) ++next_ticket;
        tickets[ticket_slot++ % 16] = {next_ticket, epoch, now};
        return next_ticket;
    }
    bool fresh_ticket(uint32_t now, uint32_t value, uint32_t max_age) const {
        for (const auto& t : tickets)
            if (value && t.value == value && t.epoch == epoch && now - t.issued < max_age) return true;
        return false;
    }
    void stop(const char* reason, bool explicit_stop = false) {
        bool active = armed || pulsing;
        if (active || explicit_stop) ++epoch;
        armed = pulsing = false; duty = 0;
        if (active || !strcmp(fault,"inicio") || !strcmp(fault,"ninguno")) fault = reason;
    }
    void tick(uint32_t now) {
        if (!armed) return;
        if (pulsing && now - pulse_start >= BANK_MAX_PULSE_MS) stop("pulso_agotado");
        else if (static_cast<int32_t>(expires - now) <= 0) stop("caducidad");
    }
    bool command(uint32_t now, uint32_t id, uint32_t lease, uint32_t sequence,
                 uint32_t ticket, int mode, int target) {
        tick(now);
        gap_ms = now - last_rx; last_rx = now;
        if (id != boot || lease != epoch || sequence <= seq) {
            rejection = id != boot ? "reinicio_o_dispositivo" :
                lease != epoch ? "rearme_antiguo" : "secuencia_repetida";
            stop(rejection); return false;
        }
        seq = sequence;
        if (mode < 1 || mode > 2 || (mode == 1 && target != 0) ||
            (mode == 2 && target != BANK_DUTY && target != -BANK_DUTY)) {
            rejection = "orden_invalida"; stop(rejection); return false;
        }
        if (!fresh_ticket(now,ticket,mode == 1 ? 1000 : 250)) {
            rejection = "token_vencido"; stop(rejection); return false;
        }
        if (mode == 1) {
            if (armed) { rejection = "rearme_repetido"; stop(rejection); return false; }
            armed = true; expires = now + 5000; fault = rejection = "ninguno"; return true;
        }
        if (!armed) { rejection = "no_habilitado"; return false; }
        if (duty * target < 0) { rejection = "parar_antes_de_invertir"; stop(rejection); return false; }
        if (!pulsing) { pulsing = true; pulse_start = now; }
        duty = target; expires = now + 250; fault = rejection = "ninguno"; return true;
    }
};

// Memory only: no GPIO or physical motor commands.
inline bool banco_selftest() {
    BancoMotor b(42);
    auto t = b.issue_ticket(0);
    if (b.command(0,42,1,1,t,2,BANK_DUTY) || b.duty) return false;
    if (!b.command(10,42,1,2,t,1,0) || b.duty) return false;
    if (!b.command(20,42,1,3,t,2,BANK_DUTY)) return false;
    t = b.issue_ticket(20);
    if (!b.command(125,42,1,4,t,2,BANK_DUTY)) return false;
    b.tick(374); if (!b.armed) return false;
    b.tick(375); if (b.armed || b.duty || b.epoch != 2) return false;
    if (b.command(376,42,1,5,t,2,BANK_DUTY)) return false;
    if (strcmp(b.fault,"caducidad") || strcmp(b.rejection,"rearme_antiguo")) return false;
    t = b.issue_ticket(380);
    if (!b.command(380,42,2,6,t,1,0)) return false;
    if (!b.command(390,42,2,7,t,2,BANK_DUTY)) return false;
    if (b.command(400,42,2,8,t,2,-BANK_DUTY) || b.armed) return false;
    BancoMotor gap(4); t=gap.issue_ticket(0);
    if (!gap.command(0,4,1,1,t,1,0)) return false;
    if (!gap.command(10,4,1,2,t,2,BANK_DUTY)) return false;
    t=gap.issue_ticket(10);
    if (!gap.command(161,4,1,3,t,2,BANK_DUTY)) return false;
    gap.tick(410); if (!gap.armed) return false;
    gap.tick(411); if (gap.armed || strcmp(gap.fault,"caducidad")) return false;
    BancoMotor pulse(9);
    if (!pulse.command(0,9,1,1,pulse.issue_ticket(0),1,0)) return false;
    for (uint32_t i=0;i<BANK_MAX_PULSE_MS/100;++i)
        if (!pulse.command(i*100,9,1,i+2,pulse.issue_ticket(i*100),2,BANK_DUTY)) return false;
    pulse.tick(BANK_MAX_PULSE_MS); if (pulse.armed || pulse.duty) return false;
    BancoMotor stale(5);
    t = stale.issue_ticket(0);
    if (!stale.command(0,5,1,1,t,1,0)) return false;
    if (stale.command(251,5,1,2,t,2,BANK_DUTY) || stale.armed) return false;
    t = stale.issue_ticket(300);
    if (!stale.command(300,5,2,3,t,1,0)) return false;
    stale.stop("parada",true);
    if (stale.command(310,5,2,4,t,1,0)) return false;
    BancoMotor replay(6);
    t = replay.issue_ticket(0);
    if (!replay.command(0,6,1,1,t,1,0)) return false;
    if (!replay.command(10,6,1,2,t,2,BANK_DUTY)) return false;
    if (replay.command(20,6,1,2,t,2,BANK_DUTY) || replay.armed) return false;
    BancoMotor wrap(7); t = wrap.issue_ticket(UINT32_MAX-100);
    if (!wrap.command(UINT32_MAX-90,7,1,1,t,1,0)) return false;
    if (!wrap.command(20,7,1,2,t,2,BANK_DUTY)) return false;
    wrap.tick(270); if (wrap.armed) return false;
    BancoMotor invalid(8); t=invalid.issue_ticket(0);
    if (!invalid.command(0,8,1,1,t,1,0)) return false;
    if (invalid.command(10,8,1,2,t,2,BANK_DUTY+1) || invalid.armed) return false;
    return true;
}
