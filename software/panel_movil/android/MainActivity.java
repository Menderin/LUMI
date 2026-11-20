package cl.lumi.panel;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.view.MotionEvent;
import android.widget.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import org.json.JSONObject;

public class MainActivity extends Activity {
    private final Handler ui = new Handler();
    private final ExecutorService lectura = Executors.newSingleThreadExecutor();
    private final ExecutorService ordenes = Executors.newSingleThreadExecutor();
    private volatile String base;
    private volatile String direccion;
    private volatile boolean activo;
    private volatile boolean enviando;
    private ImageView video;
    private TextView estado, aviso, entradaMando, enlace;
    private Button probarEnlace;
    private volatile boolean probandoEnlace;
    private final ControlWifiPower wifiPower=new ControlWifiPower();
    private Button nuevo, confirmar, cancelar, habilitarMotor, enrolar;
    private LinearLayout opcionesEnrolamiento;
    private TextView titulo, modoTexto, sinCamara;
    private final MotorBankSession motorSession = new MotorBankSession();
    private final MotorDatagrams motorDatagrams = new MotorDatagrams();
    private volatile boolean espMode, permisoMotores;
    private volatile long controlVersion;
    private String lastControlFault=""; // UI thread only.
    private volatile boolean dataChannelReady,dataProbePending;
    private long lastDataProbeMs;
    private volatile boolean servidorIdentificado;
    private volatile long connectionVersion;
    private Joystick joystick;
    private volatile boolean mandoDisponible;
    private volatile boolean arming;
    private volatile long maxPulseMs=5000;
    private final MotionHeartbeat motionHeartbeat=new MotionHeartbeat(android.os.SystemClock::elapsedRealtime);

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        LinearLayout raiz = new LinearLayout(this);
        raiz.setBackgroundColor(0xff112220);
        setContentView(raiz);

        LinearLayout camara = new LinearLayout(this);
        camara.setOrientation(LinearLayout.VERTICAL);
        camara.setPadding(dp(16), dp(6), dp(16), dp(6));
        raiz.addView(camara, new LinearLayout.LayoutParams(0, -1, 1));
        titulo = texto(camara, "LUMI  ·  CÁMARA DE BANCO", 18);
        titulo.setTextColor(0xffb7ead5);
        video = new ImageView(this);
        video.setContentDescription("Vista de la cámara del robot");
        video.setBackgroundColor(0xff081412);
        video.setScaleType(ImageView.ScaleType.FIT_CENTER);
        camara.addView(video, new LinearLayout.LayoutParams(-1, 0, 1));
        sinCamara = texto(camara, "", 20);
        sinCamara.setTextColor(0xffb7ead5);
        sinCamara.setVisibility(android.view.View.GONE);
        estado = texto(camara, "Sin conexión", 15);
        estado.setTextColor(0xfff0faf6);
        entradaMando=texto(camara,"Gesto: centrado",14);
        entradaMando.setTextColor(0xffb7ead5);
        enlace=texto(camara,"",13);
        enlace.setTextColor(0xffb7ead5);
        aviso = texto(camara, "", 14);
        aviso.setTextColor(0xfff4ce8c);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        raiz.addView(scroll, new LinearLayout.LayoutParams(dp(260), -1));
        LinearLayout menu = new LinearLayout(this);
        menu.setOrientation(LinearLayout.VERTICAL);
        menu.setPadding(dp(10), dp(6), dp(10), dp(6));
        menu.setBackgroundColor(0xffeef6f2);
        scroll.addView(menu);
        modoTexto = texto(menu, "Laboratorio · v0.7.0", 16);
        boton(menu, "Elegir Wi-Fi de LUMI").setOnClickListener(v -> {
            detener();
            String pantalla = android.os.Build.VERSION.SDK_INT >= 29
                    ? android.provider.Settings.Panel.ACTION_WIFI
                    : android.provider.Settings.ACTION_WIFI_SETTINGS;
            try {
                startActivity(new android.content.Intent(pantalla));
            } catch (android.content.ActivityNotFoundException e) {
                startActivity(new android.content.Intent(android.provider.Settings.ACTION_WIFI_SETTINGS));
            }
        });
        boton(menu, "Conectar al robot").setOnClickListener(v ->
                conectar(getPreferences(0).getString("servidor", "http://10.42.0.1:8080")));
        boton(menu, "Conectar ESP · motores").setOnClickListener(v -> conectar("http://192.168.4.1:8080"));
        boton(menu, "Ajustes de conexión").setOnClickListener(v -> {
            detener();
            EditText ip = new EditText(this);
            ip.setSingleLine();
            ip.setInputType(17);
            ip.setHint("10.42.0.1:8080");
            ip.setText(getPreferences(0).getString("servidor", "http://10.42.0.1:8080")
                    .replaceFirst("^https?://", ""));
            new android.app.AlertDialog.Builder(this).setTitle("Dirección del robot")
                .setMessage("Usa la IP del equipo que ejecuta el servidor LUMI.")
                .setView(ip).setNegativeButton("Cerrar", null)
                .setPositiveButton("Guardar y conectar", (d, w) -> conectar(ip.getText().toString()))
                .show();
        });

        Button manual = boton(menu, "Control manual  ▾");
        habilitarMotor = boton(menu, "Habilitar canal A (5 s)");
        habilitarMotor.setVisibility(android.view.View.GONE);
        habilitarMotor.setOnClickListener(v -> {
            if(arming || !dataChannelReady) return;
            arming=true;habilitarMotor.setEnabled(false);
            enviar("/api/motores","habilitar",false);
        });
        probarEnlace=boton(menu,"Probar enlace · sin motores");
        probarEnlace.setOnClickListener(v -> probarEnlace());
        probarEnlace.setVisibility(android.view.View.GONE);
        joystick = new Joystick();
        menu.addView(joystick, new LinearLayout.LayoutParams(-1, dp(170)));
        joystick.setVisibility(android.view.View.GONE);
        Button parar = boton(menu, "Parar");
        parar.setTextColor(0xff8d201c);
        parar.setOnClickListener(v -> { joystick.centrar(); detener(); });

        enrolar = boton(menu, "Enrolar  ▾");
        LinearLayout opciones = new LinearLayout(this);
        opcionesEnrolamiento = opciones;
        opciones.setOrientation(LinearLayout.VERTICAL);
        menu.addView(opciones);
        opciones.setVisibility(android.view.View.GONE);
        nuevo = boton(opciones, "Iniciar nuevo enrolamiento");
        confirmar = boton(opciones, "Confirmar enrolamiento");
        cancelar = boton(opciones, "Cancelar");
        nuevo.setOnClickListener(v -> solicitar("nuevo"));
        confirmar.setOnClickListener(v -> solicitar("confirmar"));
        cancelar.setOnClickListener(v -> solicitar("cancelar"));
        manual.setOnClickListener(v -> {
            boolean abrir = joystick.getVisibility() != android.view.View.VISIBLE;
            detener();
            joystick.centrar();
            joystick.setVisibility(abrir ? android.view.View.VISIBLE : android.view.View.GONE);
            habilitarMotor.setVisibility(espMode && abrir ? android.view.View.VISIBLE : android.view.View.GONE);
            manual.setText(abrir ? "Control manual  ▴" : "Control manual  ▾");
            opciones.setVisibility(android.view.View.GONE);
            enrolar.setText("Enrolar  ▾");
            if (abrir) scroll.smoothScrollTo(0, manual.getTop());
        });
        enrolar.setOnClickListener(v -> {
            boolean abrir = opciones.getVisibility() != android.view.View.VISIBLE;
            detener();
            joystick.centrar();
            joystick.setVisibility(android.view.View.GONE);
            manual.setText("Control manual  ▾");
            opciones.setVisibility(abrir ? android.view.View.VISIBLE : android.view.View.GONE);
            enrolar.setText(abrir ? "Enrolar  ▴" : "Enrolar  ▾");
            if (abrir) scroll.post(() -> scroll.smoothScrollTo(0, enrolar.getTop()));
        });
        habilitar(false, "");
    }

    private int dp(int valor) {
        return Math.round(valor * getResources().getDisplayMetrics().density);
    }

    private void conectar(String entrada) {
        String destino = entrada.trim().replaceAll("/+$", "");
        if (!destino.contains("://")) destino = "http://" + destino;
        if (!destino.matches("https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?")) {
            aviso.setText("Dirección inválida. Ejemplo: 10.42.0.1:8080");
            return;
        }
        detener();
        ++connectionVersion;
        servidorIdentificado = false;
        dataChannelReady=false;lastDataProbeMs=0;
        base = destino;
        espMode = false;
        if(destino.equals("http://192.168.4.1:8080")) {
            wifiPower.acquire(this);
            getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        }
        else wifiPower.release();
        permisoMotores = false;
        motorSession.clear();
        video.setImageDrawable(null);
        getPreferences(0).edit().putString("servidor", destino).apply();
        aviso.setText("Conectando…");
        habilitar(false, "");
    }

    private TextView texto(LinearLayout padre, String valor, int size) {
        TextView t = new TextView(this);
        t.setText(valor);
        t.setTextSize(size);
        t.setPadding(0, 8, 0, 8);
        padre.addView(t);
        return t;
    }

    private Button boton(LinearLayout padre, String valor) {
        Button b = new Button(this);
        b.setText(valor);
        b.setAllCaps(false);
        padre.addView(b);
        return b;
    }

    private class Joystick extends android.view.View {
        private final android.graphics.Paint tinta =
                new android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);
        private float dx, dy;
        private int dedo = -1;
        private boolean gestoConectado;

        Joystick() {
            super(MainActivity.this);
            setContentDescription("Joystick manual. Arrastra hacia adelante, atrás, izquierda o derecha.");
        }

        private float radio() { return Math.min(getWidth(), getHeight()) * .38f; }

        @Override protected void onDraw(android.graphics.Canvas canvas) {
            float x = getWidth() / 2f, y = getHeight() / 2f, r = radio();
            tinta.setColor(mandoDisponible ? 0xffd1e7dd : 0xffe1e6e4);
            canvas.drawCircle(x, y, r, tinta);
            tinta.setColor(0xff52786b);
            canvas.drawLine(x-r, y, x+r, y, tinta);
            canvas.drawLine(x, y-r, x, y+r, tinta);
            tinta.setColor(mandoDisponible ? 0xff205e49 : 0xff808e88);
            canvas.drawCircle(x+dx, y+dy, r*.29f, tinta);
        }

        void centrar() {
            entradaMando.setText("Gesto: centrado · sin orden");
            dedo = -1;
            dx = dy = 0;
            invalidate();
        }

        @Override public boolean onTouchEvent(MotionEvent evento) {
            // El gesto visual también funciona sin conexión.
            int accion = evento.getActionMasked();
            int indice = evento.getActionIndex();
            if (accion == MotionEvent.ACTION_DOWN) {
                dedo = evento.getPointerId(indice);
                gestoConectado = mandoDisponible;
                getParent().requestDisallowInterceptTouchEvent(true);
            }
            if (accion == MotionEvent.ACTION_CANCEL || accion == MotionEvent.ACTION_UP
                    || (accion == MotionEvent.ACTION_POINTER_UP && evento.getPointerId(indice) == dedo)) {
                boolean parar = gestoConectado && direccion != null;
                centrar();
                if (parar) detener();
                getParent().requestDisallowInterceptTouchEvent(false);
                return true;
            }
            if (accion != MotionEvent.ACTION_DOWN && accion != MotionEvent.ACTION_MOVE) return true;
            indice = evento.findPointerIndex(dedo);
            if (indice < 0) {
                if(direccion != null) detener();
                centrar();
                return true;
            }
            float x = evento.getX(indice) - getWidth()/2f;
            float y = evento.getY(indice) - getHeight()/2f;
            float distancia = (float)Math.hypot(x, y);
            float r = radio();
            float factor = distancia > r ? r / distancia : 1;
            dx = x * factor;
            dy = y * factor;
            invalidate();
            String orden = espMode ? JoystickDirection.bank(x,y,r,direccion) : JoystickDirection.classify(x,y,r);
            entradaMando.setText("Gesto: "+orden+" · "+
                (probandoEnlace?"prueba de enlace":gestoConectado && mandoDisponible?"mando habilitado":"solo visual / deshabilitado"));
            if (!gestoConectado || !mandoDisponible || probandoEnlace) return true;
            if (orden.equals("parar")) {
                if (direccion != null) detener();
                return true;
            }
            if (espMode && (orden.equals("derecha") || orden.equals("izquierda"))) {
                if (direccion != null) detener();
                return true;
            }
            if (!orden.equals(direccion)) {
                if (espMode && direccion != null) {
                    detener();
                    aviso.setText("Suelta y habilita de nuevo para invertir.");
                    return true;
                }
                ++controlVersion;
                direccion = orden;
                ui.removeCallbacks(pulso);
                pulso.run();
            }
            return true;
        }
    }

    private final Runnable pulso = new Runnable() {
        @Override public void run() {
            String actual = direccion;
            if (actual == null || !activo || !mandoDisponible) return;
            if(!enviando) {
                enviando=true;
                enviar(espMode?"/api/motores":"/api/banco/movimiento",actual,true);
            }
            // In ESP mode an independent clock publishes; touch events never drive timing.
            if(!espMode) ui.postDelayed(this,160);
        }
    };

    private void detener() {
        ++controlVersion;
        permisoMotores = false;
        motionHeartbeat.stop();motorSession.endMotion();
        direccion = null;
        ui.removeCallbacks(pulso);
        if (base != null && servidorIdentificado)
            enviar(espMode ? "/api/motores" : "/api/banco/movimiento", "parar", false);
    }

    private void solicitar(String accion) {
        detener();
        enviar("/api/banco/enrolamiento", accion, false);
    }

    private void enviar(String ruta, String accion, boolean repetida) {
        String equipo = base;
        if (equipo == null) return;
        if(probandoEnlace && !accion.equals("parar")) return;
        long version = controlVersion;
        long connection = connectionVersion;
        boolean motor = ruta.equals("/api/motores");
        ordenes.execute(() -> {
            try {
                if (!equipo.equals(base) || connection != connectionVersion) return;
                if ((repetida || (motor && accion.equals("habilitar"))) &&
                        (version != controlVersion || !activo)) return;
                if (repetida && !accion.equals(direccion)) return;
                if(motor && repetida && !permisoMotores) return;
                if(motor && accion.equals("habilitar")) {
                    JSONObject ping=motorDatagrams.exchange(this,"ping",new JSONObject());
                    motorSession.updateReply(ping,android.os.SystemClock.elapsedRealtime());
                }
                if(motor && repetida) {
                    if(motorSession.needsRefresh()) {
                        JSONObject fresh=motorDatagrams.exchange(this,"ping",new JSONObject());
                        motorSession.updateReply(fresh,android.os.SystemClock.elapsedRealtime());
                        if(!fresh.getJSONObject("banco").optBoolean("habilitado"))
                            throw new Exception("La ESP está deshabilitada; vuelve a habilitar antes de mover");
                    }
                    if(!motionCurrent(equipo,connection,version,accion)) return;
                    motorSession.beginMotion();
                    motionHeartbeat.start(maxPulseMs,run -> {
                        if(!motionCurrent(equipo,connection,version,accion)) { motionHeartbeat.stop();return; }
                        motorDatagrams.sendMotion(this,accion,motorSession.motionCommand(),
                            () -> motionCurrent(equipo,connection,version,accion),(reply,error) -> {
                                if(!motionCurrent(equipo,connection,version,accion)) return;
                                if(error!=null) { motionFault(error,equipo,connection,version,accion);return; }
                                try {
                                    if(motorSession.updateReply(reply,android.os.SystemClock.elapsedRealtime())<0) return;
                                    if(!motionHeartbeat.confirm(run,reply.getLong("_request_started_ms"))) return;
                                    ui.post(() -> {
                                        if(motionCurrent(equipo,connection,version,accion) && aviso.getText().toString().startsWith("Confirmación retrasada")) aviso.setText("");
                                    });
                                } catch(Exception failed) { motionFault(failed,equipo,connection,version,accion); }
                            });
                        if(motionHeartbeat.delayed(run)) pendingMessage(connection,version,"Confirmación retrasada; canal de datos abierto");
                    },(run,error) -> motionFault(error,equipo,connection,version,accion));
                    pendingMessage(connection,version,"Mando periódico activo · envío independiente de respuestas");
                    return;
                }
                if(motor && accion.equals("habilitar") && (version!=controlVersion || !activo || connection!=connectionVersion)) return;
                JSONObject body=motor && !accion.equals("parar")?motorSession.command(repetida):new JSONObject();
                long started = android.os.SystemClock.elapsedRealtime();
                JSONObject respuesta = motor ? motorDatagrams.exchange(this,accion,body)
                    : json(equipo + ruta + "/" + accion, true, body);
                if (motor && respuesta.optJSONObject("banco") != null &&
                        connection == connectionVersion)
                    motorSession.updateReply(respuesta, started);
                if(motor && accion.equals("habilitar") && !respuesta.getJSONObject("banco").optBoolean("habilitado"))
                    throw new Exception("La habilitación no fue aceptada por la ESP");
                if (!repetida) ui.post(() -> {
                    if (!equipo.equals(base) || connection != connectionVersion) return;
                    if (motor && accion.equals("habilitar") && version == controlVersion && activo) {
                        permisoMotores = true;
                        ++controlVersion;
                        lastControlFault="";
                        habilitar(true,"");
                    }
                    aviso.setText(respuesta.optString("mensaje"));
                });
            } catch(MotorSessionToken.NeedsRefresh freshNeeded) {
                recoverControl(freshNeeded,motor,equipo,connection,accion);
            } catch(Exception e) {
                recoverControl(e,motor,equipo,connection,accion);
            } finally {
                if(repetida) enviando=false;
                if(motor && accion.equals("habilitar")) ui.post(() -> arming=false);
            }
        });
    }

    private boolean motionCurrent(String equipo,long connection,long version,String action) {
        return activo && permisoMotores && equipo.equals(base) && connection==connectionVersion && version==controlVersion && action.equals(direccion);
    }
    private void motionFault(Exception error,String equipo,long connection,long version,String action) {
        if(!motionCurrent(equipo,connection,version,action)) return;
        permisoMotores=false;direccion=null;motionHeartbeat.stop();motorSession.endMotion();
        if(error instanceof MotionHeartbeat.PulseEnded) {
            ui.post(() -> {
                if(connection!=connectionVersion || version!=controlVersion) return;
                detener();habilitar(false,"");aviso.setText("Pulso finalizado. Habilita de nuevo para otro ensayo.");
            });
        } else {
            dataChannelReady=false;
            if(!ordenes.isShutdown()) ordenes.execute(() -> recoverControl(error,true,equipo,connection,action));
        }
    }

    private void pendingMessage(long connection,long version,String message) {
        ui.post(() -> { if(activo && connection==connectionVersion && version==controlVersion) aviso.setText(message); });
    }

    // Runs on the ordered network worker. Suspension does not close the data endpoint.
    private void recoverControl(Exception error,boolean motor,String equipo,long connection,String action) {
        if(!equipo.equals(base) || connection!=connectionVersion) return;
        permisoMotores=false;direccion=null;++controlVersion;
        motionHeartbeat.stop();motorSession.endMotion();
        dataChannelReady=false;
        if(error instanceof MotorDatagrams.Rejected) {
            try { motorSession.updateReply(((MotorDatagrams.Rejected)error).reply,android.os.SystemClock.elapsedRealtime()); }
            catch(Exception ignored) { }
        }
        ui.post(() -> {
            if(!equipo.equals(base) || connection!=connectionVersion) return;
            ui.removeCallbacks(pulso);habilitar(false,"");habilitarMotor.setEnabled(false);
            lastControlFault=detalle(error);
            aviso.setText("Control suspendido: "+lastControlFault+"\nRecuperando datos; será necesario habilitar de nuevo.");
        });
        if(motor) {
            try {
                JSONObject stopped=motorDatagrams.exchange(this,"parar",new JSONObject());
                if(connection==connectionVersion && equipo.equals(base))
                    motorSession.updateReply(stopped,android.os.SystemClock.elapsedRealtime());
            } catch(Exception ignored) { /* Firmware watchdog remains independent. */ }
        }
    }

    // A read-only probe restores the data channel, never the movement permission.
    private void recoverDataChannel() { recoverDataChannel(false); }

    private void recoverDataChannel(boolean checkWhenReady) {
        long now=android.os.SystemClock.elapsedRealtime();
        if(!espMode || (!checkWhenReady && dataChannelReady) || dataProbePending || permisoMotores || arming || probandoEnlace || !activo || now-lastDataProbeMs<750) return;
        lastDataProbeMs=now;dataProbePending=true;
        long connection=connectionVersion;
        ordenes.execute(() -> {
            try {
                if(!activo || connection!=connectionVersion || permisoMotores || arming || probandoEnlace) return;
                JSONObject reply=motorDatagrams.exchange(this,"ping",new JSONObject());
                if(connection!=connectionVersion || !activo) return;
                motorSession.updateReply(reply,android.os.SystemClock.elapsedRealtime());
                // Local permission is false: stop any unexpectedly armed remote session.
                if(reply.getJSONObject("banco").optBoolean("habilitado")) {
                    reply=motorDatagrams.exchange(this,"parar",new JSONObject());
                    motorSession.updateReply(reply,android.os.SystemClock.elapsedRealtime());
                }
                ui.post(() -> {
                    if(connection!=connectionVersion || !activo) return;
                    boolean restored=!dataChannelReady;
                    dataChannelReady=true;
                    habilitarMotor.setEnabled(!permisoMotores && !probandoEnlace && !arming);
                    if(restored) aviso.setText("Canal de datos disponible. Pulsa Habilitar para continuar."+
                        (lastControlFault.isEmpty()?"":"\nÚltimo corte: "+lastControlFault));
                });
            } catch(Exception error) {
                dataChannelReady=false;
                ui.post(() -> {
                    if(connection==connectionVersion && activo) {
                        habilitarMotor.setEnabled(false);
                        aviso.setText("Recuperando canal de datos… "+detalle(error));
                    }
                });
            } finally { dataProbePending=false; }
        });
    }

    private void probarEnlace() {
        if(probandoEnlace || !espMode || !servidorIdentificado) return;
        detener();
        joystick.centrar();
        probandoEnlace=true;
        habilitar(false,"");
        habilitarMotor.setEnabled(false);
        probarEnlace.setEnabled(false);
        long connection=connectionVersion;
        aviso.setText("Midiendo 12 intercambios, sin habilitar motores…");
        ordenes.execute(() -> {
            LinkProbeStats stats=new LinkProbeStats();
            String failure="";
            try {
                wifiPower.acquire(this);
                // Keep the same data endpoint during the diagnostic too.
                // Firmware must be disabled before starting this read-only test.
                for(int i=0;i<12;++i) {
                    if(!activo || connection!=connectionVersion) return;
                    long started=android.os.SystemClock.elapsedRealtime();
                    try {
                        JSONObject result=motorDatagrams.exchange(this,"ping",new JSONObject());
                        JSONObject bank=result.getJSONObject("banco");
                        if(bank.optBoolean("habilitado")) throw new IllegalStateException("La ESP sigue habilitada; pulsa Parar");
                        motorSession.updateReply(result,started);
                        stats.add(android.os.SystemClock.elapsedRealtime()-started,bank.getLong("uptime_ms"));
                    } catch(IllegalStateException unsafe) { throw unsafe; }
                    catch(Exception error) { stats.fail();failure=detalle(error); }
                    long rest=50-(android.os.SystemClock.elapsedRealtime()-started);
                    if(rest>0) Thread.sleep(rest);
                }
                motorDatagrams.save(this);
                String summary=stats.summary()+(failure.isEmpty()?"":"\nÚltimo error: "+failure);
                try(java.io.FileOutputStream out=openFileOutput("prueba-enlace.txt",MODE_PRIVATE)) {
                    out.write((wifiPower.status()+"\n"+summary).getBytes(StandardCharsets.UTF_8));
                }
                ui.post(() -> {
                    if(connection!=connectionVersion || !activo) return;
                    new android.app.AlertDialog.Builder(this).setTitle("Prueba de enlace · motores deshabilitados")
                        .setMessage(wifiPower.status()+"\n"+summary)
                        .setPositiveButton("Cerrar",null)
                        .setNeutralButton("Copiar informe",(dialog,which) -> {
                            android.content.ClipboardManager clipboard=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
                            clipboard.setPrimaryClip(android.content.ClipData.newPlainText("LUMI enlace",summary+"\n\nÚltimos eventos de control:\n"+motorDatagrams.report()));
                        }).show();
                    aviso.setText(stats.acceptable()?"Prueba de enlace correcta; habilita para probar el mando.":"Enlace irregular. Copia el informe antes de probar motores.");
                });
            } catch(Exception error) {
                String message=detalle(error);
                ui.post(() -> { if(connection==connectionVersion) aviso.setText(message); });
            } finally {
                probandoEnlace=false;
                ui.post(() -> {
                    if(connection==connectionVersion) { probarEnlace.setEnabled(true);habilitarMotor.setEnabled(dataChannelReady); }
                });
            }
        });
    }

    private void habilitar(boolean disponible, String fase) {
        boolean bloqueado = fase.equals("enrolando") || fase.equals("aprobado");
        boolean permitido = disponible && !bloqueado;
        if (!permitido && mandoDisponible) {
            joystick.gestoConectado = false;
            if (direccion != null) detener();
        }
        mandoDisponible = permitido;
        joystick.invalidate();
        nuevo.setEnabled(!espMode && disponible && !bloqueado);
        confirmar.setEnabled(!espMode && disponible && fase.equals("aprobado"));
        cancelar.setEnabled(!espMode && disponible && !fase.equals("espera"));
    }

    private final Runnable consultar = new Runnable() {
        @Override public void run() {
            if (!activo) return;
            String equipo = base;
            long connection = connectionVersion;
            if (equipo == null) {
                ui.postDelayed(this, 350);
                return;
            }
            lectura.execute(() -> {
                long polledVersion=controlVersion;
                try {
                    long started = android.os.SystemClock.elapsedRealtime();
                    JSONObject s = json(equipo + "/api/estado", false);
                    if (connection != connectionVersion) return;
                    JSONObject banco = s.optJSONObject("banco");
                    boolean motor = s.optString("modo").equals("motores_esp");
                    if(motor && polledVersion!=controlVersion) return;
                    int sessionUpdate = motor && banco != null ? motorSession.update(banco, started) : 0;
                    if (sessionUpdate < 0) return;
                    Bitmap imagen = s.optBoolean("camara") ? foto(equipo + "/foto.jpg") : null;
                    ui.post(() -> {
                        if (!activo || !equipo.equals(base) || connection != connectionVersion) return;
                        if(motor && polledVersion!=controlVersion) return;
                        servidorIdentificado = banco != null;
                        if (sessionUpdate > 0) {
                            motionHeartbeat.stop();
                            permisoMotores = false;
                            direccion = null;
                            ++controlVersion;
                            aviso.setText("La ESP se reinició. Habilita de nuevo con la fuente revisada.");
                        }
                        espMode = motor;
                        if(motor) recoverDataChannel();
                        probarEnlace.setVisibility(motor?android.view.View.VISIBLE:android.view.View.GONE);
                        titulo.setText(motor ? "LUMI  ·  BANCO DE MOTORES" : "LUMI  ·  CÁMARA DE BANCO");
                        modoTexto.setText(motor ? "ESP · canal A · v0.7.0" : "Simulación · v0.7.0");
                        habilitarMotor.setVisibility(motor && joystick.getVisibility() == android.view.View.VISIBLE
                            ? android.view.View.VISIBLE : android.view.View.GONE);
                        enrolar.setVisibility(motor ? android.view.View.GONE : android.view.View.VISIBLE);
                        if (motor) opcionesEnrolamiento.setVisibility(android.view.View.GONE);
                        video.setVisibility(motor ? android.view.View.GONE : android.view.View.VISIBLE);
                        sinCamara.setVisibility(motor ? android.view.View.VISIBLE : android.view.View.GONE);
                        sinCamara.setText("Canal A · adelante / atrás\nLímite PWM: "+
                            (banco == null ? "—" : banco.optInt("limite_pwm"))+"% · pulso máximo: "+
                            (banco == null ? "—" : banco.optLong("max_pulso_ms"))+" ms");
                        video.setImageBitmap(imagen);
                        if (banco == null) {
                            estado.setText("Servidor conectado · actualizar servidor para habilitar el banco");
                            habilitar(false, "");
                        } else if (motor) {
                            maxPulseMs=Math.max(1,Math.min(5000,banco.optLong("max_pulso_ms",5000)));
                            boolean armado = banco.optBoolean("habilitado");
                            if(!armado) permisoMotores=false;
                            estado.setText((banco.optBoolean("dry_run") ? "Prueba lógica · salidas bloqueadas" : "Control real · canal A")
                                + "\n" + (armado ? "Habilitado" : "Deshabilitado")
                                + " · PWM ordenado: " + banco.optInt("pwm_ordenado") + "%"
                                + "\nEstado: " + banco.optString("fallo")
                                + " · " + banco.optString("ultimo_rechazo", "")
                                + "\nSin medición de corriente ni velocidad");
                            habilitar(permisoMotores && armado, "");
                            habilitarMotor.setEnabled(dataChannelReady && !permisoMotores && !probandoEnlace && !arming);
                        probarEnlace.setEnabled(!probandoEnlace);
                        enlace.setText(probandoEnlace?"Midiendo enlace sin motores…":wifiPower.status()+"\n"+motorDatagrams.trace());
                            if(aviso.getText().toString().equals("Conectando…")) aviso.setText(dataChannelReady?"Datos disponibles. Habilita antes de usar el mando.":"Comprobando canal de datos…");
                        } else {
                            String fase = banco.optString("enrolamiento");
                            long segundos = banco.optLong("segundos");
                            estado.setText("Cámara: " + (imagen == null ? "sin señal" : "en vivo")
                                + "\nMovimiento simulado: " + banco.optString("movimiento")
                                + "\nEnrolamiento simulado: " + fase
                                + (fase.equals("enrolando") ? " · " + segundos + " s" : ""));
                            habilitar(true, fase);
                            if (aviso.getText().toString().equals("Conectando…")) aviso.setText("");
                        }
                    });
                } catch (Exception e) {
                    ui.post(() -> {
                        if(!activo || !equipo.equals(base) || connection!=connectionVersion || polledVersion!=controlVersion) return;
                        // HTTP is telemetry. The UDP sender and firmware independently enforce loss of control.
                        if(espMode) {
                            enlace.setText("Telemetría HTTP temporalmente no disponible · "+motorDatagrams.trace());
                            recoverDataChannel(true);
                            return;
                        }
                        permisoMotores = false;
                        ++controlVersion;
                        direccion = null;
                        dataChannelReady=false;
                        motionHeartbeat.stop();motorSession.endMotion();
                        habilitarMotor.setEnabled(false);
                        estado.setText("Esperando telemetría HTTP");
                        aviso.setText("Esperando recuperar datos: "+detalle(e));
                        video.setImageDrawable(null);
                        habilitar(false, "");
                    });
                } finally {
                    ui.post(() -> {
                        if (activo) { ui.removeCallbacks(this); ui.postDelayed(this, 250); }
                    });
                }
            });
        }
    };

    private HttpURLConnection abrir(String url) throws Exception {
        HttpURLConnection c = EspWifiRoute.open(this, new URL(url));
        // Discovery may wait longer; command expiry is still enforced on the ESP.
        c.setConnectTimeout(2000);
        c.setReadTimeout(2000);
        c.setInstanceFollowRedirects(false);
        return c;
    }

    private String detalle(Exception error) {
        if (error instanceof java.net.SocketTimeoutException) return "Sin respuesta HTTP de estado (2 s)";
        if (error instanceof java.net.ConnectException) return "No responde el servidor del robot";
        if (error instanceof org.json.JSONException) return "El servidor devolvió un estado no válido";
        String message = error.getMessage();
        return message == null || message.length() == 0 ? error.getClass().getSimpleName() : message;
    }

    private JSONObject json(String url, boolean post) throws Exception {
        return json(url, post, new JSONObject());
    }

    private JSONObject json(String url, boolean post, JSONObject body) throws Exception {
        HttpURLConnection c = abrir(url);
        try {
            if (post) {
                c.setRequestMethod("POST");
                c.setDoOutput(true);
                byte[] payload = body.toString().getBytes(StandardCharsets.UTF_8);
                c.setFixedLengthStreamingMode(payload.length);
                c.setRequestProperty("Content-Type", "application/json");
                try (java.io.OutputStream stream = c.getOutputStream()) {
                    stream.write(payload);
                }
            }
            int code = c.getResponseCode();
            java.io.InputStream response = code >= 200 && code < 300
                ? c.getInputStream() : c.getErrorStream();
            if (response == null) throw new java.io.IOException("HTTP " + code);
            try (java.io.InputStream stream = response;
                 java.io.ByteArrayOutputStream bytes = new java.io.ByteArrayOutputStream()) {
                byte[] buffer = new byte[1024];
                int n;
                while ((n = stream.read(buffer)) != -1) {
                    if (bytes.size() + n > 16384) throw new java.io.IOException("Respuesta excesiva");
                    bytes.write(buffer, 0, n);
                }
                if (code < 200 || code >= 300) {
                    String message = "Solicitud rechazada";
                    try {
                        JSONObject error = new JSONObject(bytes.toString("UTF-8"));
                        message = error.optString("mensaje", message);
                        JSONObject bank = error.optJSONObject("banco");
                        if (bank != null) {
                            message += " · " + bank.optString("fallo")
                                + " · " + bank.optString("ultimo_rechazo")
                                + " · intervalo " + bank.optLong("intervalo_orden_ms") + " ms";
                        }
                    }
                    catch (org.json.JSONException ignored) { }
                    throw new java.io.IOException("HTTP " + code + ": " + message);
                }
                return new JSONObject(bytes.toString("UTF-8"));
            }
        } finally { c.disconnect(); }
    }

    private Bitmap foto(String url) {
        try {
            HttpURLConnection c = abrir(url);
            try (java.io.InputStream datos = c.getInputStream()) {
                return BitmapFactory.decodeStream(datos);
            } finally { c.disconnect(); }
        } catch (Exception e) { return null; }
    }

    @Override protected void onResume() {
        super.onResume();
        activo = true;
        if(base != null && base.equals("http://192.168.4.1:8080")) {
            wifiPower.acquire(this);
            getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        }
        consultar.run();
    }

    @Override protected void onPause() {
        activo = false;
        dataChannelReady=false;
        ui.removeCallbacks(consultar);
        joystick.centrar();
        detener();
        ordenes.execute(() -> motorDatagrams.save(this));
        wifiPower.release();
        getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        super.onPause();
    }

    @Override protected void onDestroy() {
        motionHeartbeat.close();
        lectura.shutdownNow();
        ordenes.execute(() -> motorDatagrams.close());
        ordenes.shutdown();
        super.onDestroy();
    }
}
