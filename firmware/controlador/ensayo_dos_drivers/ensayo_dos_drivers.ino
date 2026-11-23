// Banco independiente LUMI. Arduino-ESP32 2.0.17 (PlatformIO fijado).
// Antes de cargar: motores SIN alimentacion, jumper ENB retirado y GPIO9 libre.
#include <Arduino.h>

constexpr uint8_t RPWM=17, LPWM=16, R_EN=15, L_EN=7;
constexpr uint8_t ENA=6, IN1=4, IN2=5, IN3=18, IN4=8, ENB=9;
constexpr uint8_t BOOT=0;
constexpr uint8_t CH_R=0, CH_L=1, CH_A=2, CH_B=3;
constexpr uint8_t DUTY=153; // 60% de255, NO limita corriente.
constexpr uint32_t PWM_HZ=1000, PULSO_MS=500, REPOSO_MS=1000;

bool izquierdo=false, habilitado=false, activo=false, pwmListo=false;
uint32_t inicio=0, ultimaParada=0, cambioBoton=0;
int botonAnterior=HIGH, botonEstable=HIGH;

void pararTodo(){
    // Inhibir potencia antes de tocar direccion.
    digitalWrite(R_EN,LOW);digitalWrite(L_EN,LOW);
    digitalWrite(ENA,LOW);digitalWrite(ENB,LOW);
    if(pwmListo){
        ledcWrite(CH_R,0);ledcWrite(CH_L,0);
        ledcWrite(CH_A,0);ledcWrite(CH_B,0);
    }
    digitalWrite(IN1,LOW);digitalWrite(IN2,LOW);
    digitalWrite(IN3,LOW);digitalWrite(IN4,LOW);
    activo=false;
    ultimaParada=millis();
}
void desarmar(){pararTodo();habilitado=false;}
void seleccionar(bool izquierda){
    desarmar();izquierdo=izquierda;
    Serial.println(izquierdo?"IZQUIERDO L298N seleccionado. H habilita.":"DERECHO BTS7960 seleccionado. H habilita.");
}
void iniciar(bool adelante){
    uint32_t ahora=millis();
    if(!pwmListo||!habilitado||activo||digitalRead(BOOT)==LOW||
       uint32_t(ahora-ultimaParada)<REPOSO_MS){
        Serial.println("Sin pulso: pulsa H, suelta BOOT y espera1s desde parada.");return;
    }
    // No conservar comandos pendientes para repetir movimientos despues.
    while(Serial.available()){
        char pendiente=Serial.read();
        if(pendiente=='s'||pendiente=='S'||pendiente==' '){desarmar();return;}
    }
    if(izquierdo){
        digitalWrite(IN1,adelante?HIGH:LOW);digitalWrite(IN2,adelante?LOW:HIGH);
        digitalWrite(IN3,adelante?HIGH:LOW);digitalWrite(IN4,adelante?LOW:HIGH);
        ledcWrite(CH_A,DUTY);ledcWrite(CH_B,DUTY);
    }else{
        // Entradas opuestas a cero antes de habilitar ambos semipuentes.
        ledcWrite(CH_R,0);ledcWrite(CH_L,0);
        digitalWrite(R_EN,HIGH);digitalWrite(L_EN,HIGH);
        ledcWrite(adelante?CH_R:CH_L,DUTY);
    }
    inicio=millis();activo=true;
}
void setup(){
    const uint8_t salidas[]={R_EN,L_EN,RPWM,LPWM,ENA,ENB,IN1,IN2,IN3,IN4};
    for(uint8_t pin:salidas){digitalWrite(pin,LOW);pinMode(pin,OUTPUT);}
    pinMode(BOOT,INPUT_PULLUP);
    const uint8_t canales[]={CH_R,CH_L,CH_A,CH_B};
    bool ok=true;
    for(uint8_t ch:canales){ok=(ledcSetup(ch,PWM_HZ,8)>0)&&ok;ledcWrite(ch,0);}
    if(ok){
        ledcAttachPin(RPWM,CH_R);ledcAttachPin(LPWM,CH_L);
        ledcAttachPin(ENA,CH_A);ledcAttachPin(ENB,CH_B);
        pwmListo=true;
    }
    desarmar();
    Serial.begin(115200);
    // Sin esperar conexion serie; arranque siempre detenido.
}
void loop(){
    uint32_t ahora=millis();
    // Prioridad al corte antes de leer comandos o imprimir.
    if(activo && uint32_t(ahora-inicio)>=PULSO_MS)desarmar();
    if(!Serial){if(activo||habilitado)desarmar();return;}
    int boton=digitalRead(BOOT);
    // Pulsacion bruta detiene ya; debounce solo afecta seleccion en reposo.
    if(boton==LOW && activo){desarmar();botonEstable=LOW;}
    if(boton!=botonAnterior){botonAnterior=boton;cambioBoton=ahora;}
    if(uint32_t(ahora-cambioBoton)>=30 && boton!=botonEstable){
        botonEstable=boton;
        if(boton==LOW)seleccionar(!izquierdo);
    }
    if(!Serial.available())return;
    char c=Serial.read();
    if(c=='s'||c=='S'||c==' '){desarmar();Serial.println("PARADO / desarmado");return;}
    if(activo)return; // Ninguna orden queda en cola para invertir/repetir.
    if(c=='d'||c=='D')seleccionar(false);
    else if(c=='i'||c=='I')seleccionar(true);
    else if(c=='h'||c=='H'){
        if(pwmListo && digitalRead(BOOT)==HIGH){habilitado=true;Serial.println("Habilitado: F/B da UN pulso de500ms; S o BOOT detiene.");}
        else Serial.println("No habilitado: revisar PWM/BOOT.");
    }
    else if(c=='f'||c=='F')iniciar(true);
    else if(c=='b'||c=='B')iniciar(false);
    else if(c=='?')Serial.println("D derecho / I izquierdo / H habilitar / F adelante / B atras / S parar.60%,500ms. Rehabilitar tras cada pulso.");
}
