package cl.lumi.panel;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.*;
import android.net.*;
import android.os.*;
import android.provider.Settings;
import android.util.Base64;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;

/** Banco NUC de vision. Esta actividad no contiene transporte de motores. */
public class VisionActivity extends Activity {
    private final Handler ui=new Handler(Looper.getMainLooper());
    private final ExecutorService frames=Executors.newSingleThreadExecutor();
    private final ExecutorService commands=Executors.newSingleThreadExecutor();
    private volatile long epoch;
    private volatile boolean connected, foreground;
    private volatile Network wifi;
    private volatile String base="http://10.42.0.1:8080";
    private boolean busy, reviewMode, enrollmentOpen, reviewSeen;
    private TextView status, detail, notice;
    private Button connect, enroll, capture, confirm, repeat, cancel, follow, review;
    private LinearLayout enrollment;
    private SnapshotView video;
    private String phase="desconectado";
    private final VideoFrameStats displayStats=new VideoFrameStats();
    private final LatestFrameSlot<VideoUpdate> pendingVideo=new LatestFrameSlot<>();
    private long frameLoadMs;
    private long lastVideoLog;
    private final ControlWifiPower wifiPower=new ControlWifiPower();
    private String videoFormat="JPEG/JSON";
    private static final class FrameRouteUnavailable extends IOException {}
    private static final class VideoUpdate {
        final long generation,loadMs;
        final JSONObject snapshot;
        final Bitmap bitmap;
        final String error;
        VideoUpdate(long generation,long loadMs,JSONObject snapshot,Bitmap bitmap,String error){
            this.generation=generation;this.loadMs=loadMs;this.snapshot=snapshot;this.bitmap=bitmap;this.error=error;
        }
    }

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        base=getPreferences(0).getString("nuc_url",base);
        LinearLayout root=new LinearLayout(this);
        root.setBackgroundColor(0xff112220);
        setContentView(root);
        root.setOnApplyWindowInsetsListener((view,insets)->{
            view.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),
                            insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        root.requestApplyInsets();
        LinearLayout camera=new LinearLayout(this);
        camera.setOrientation(1); camera.setPadding(dp(12),dp(8),dp(12),dp(8));
        root.addView(camera,new LinearLayout.LayoutParams(0,-1,1));
        label(camera,"LUMI · VISIÓN DEL NUC",18,0xffb7ead5);
        video=new SnapshotView();
        camera.addView(video,new LinearLayout.LayoutParams(-1,0,1));
        status=label(camera,"Conecta el móvil al Wi-Fi del NUC",16,0xfff0faf6);
        detail=label(camera,"Movimiento restringido · solo visión",13,0xffb7ead5);
        notice=label(camera,"",14,0xfff4ce8c);
        ScrollView scroll=new ScrollView(this);
        root.addView(scroll,new LinearLayout.LayoutParams(dp(248),-1));
        LinearLayout menu=new LinearLayout(this);
        menu.setOrientation(1); menu.setPadding(dp(12),dp(8),dp(12),dp(8));
        menu.setBackgroundColor(0xffeef6f2); scroll.addView(menu);
        label(menu,"Laboratorio · v0.8.2",17,0xff112220);
        button(menu,"Elegir Wi-Fi del NUC").setOnClickListener(v->{
            disconnect(); startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS));
        });
        connect=button(menu,"Conectar al NUC");
        connect.setOnClickListener(v->{if(connected) disconnect(); else connect();});
        button(menu,"Dirección del NUC").setOnClickListener(v->address());
        enroll=button(menu,"Enrolar persona");
        enroll.setOnClickListener(v->{
            enrollmentOpen=!enrollmentOpen;
            enrollment.setVisibility(enrollmentOpen?View.VISIBLE:View.GONE);
            if(enrollmentOpen && (phase.equals("espera") || phase.equals("fallo"))) action("iniciar");
        });
        enrollment=new LinearLayout(this); enrollment.setOrientation(1);
        menu.addView(enrollment); enrollment.setVisibility(View.GONE);
        label(enrollment,"1. Toca un recuadro\n2. Captura el giro\n3. Revisa y confirma",14,0xff183f35);
        button(enrollment,"Seleccionar por número").setOnClickListener(v->choosePerson());
        capture=button(enrollment,"Comenzar captura"); capture.setOnClickListener(v->action("capturar"));
        review=button(enrollment,"Ver recortes"); review.setOnClickListener(v->toggleReview());
        confirm=button(enrollment,"Confirmar enrolamiento"); confirm.setOnClickListener(v->action("confirmar"));
        repeat=button(enrollment,"Nuevo enrolamiento"); repeat.setOnClickListener(v->action("repetir"));
        cancel=button(enrollment,"Cancelar"); cancel.setOnClickListener(v->action("cancelar"));
        follow=button(menu,"Iniciar seguimiento visual");
        follow.setOnClickListener(v->action(phase.equals("perdido")?"reanudar":"iniciar_seguimiento"));
        Button movement=button(menu,"Movimiento no disponible"); movement.setEnabled(false);
        label(menu,"La ESP y los motores no se controlan desde esta versión.",13,0xff37564c);
        buttons();
    }

    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private TextView label(LinearLayout parent,String text,int size,int color){
        TextView t=new TextView(this);t.setText(text);t.setTextSize(size);t.setTextColor(color);
        t.setPadding(0,dp(4),0,dp(4));parent.addView(t);return t;
    }
    private Button button(LinearLayout parent,String text){
        Button b=new Button(this);b.setText(text);b.setAllCaps(false);b.setMinHeight(dp(48));
        b.setContentDescription(text);parent.addView(b,new LinearLayout.LayoutParams(-1,-2));return b;
    }
    private Network wifiNetwork(){
        ConnectivityManager cm=(ConnectivityManager)getSystemService(CONNECTIVITY_SERVICE);
        for(Network n:cm.getAllNetworks()){
            NetworkCapabilities c=cm.getNetworkCapabilities(n);
            if(c!=null && c.hasTransport(NetworkCapabilities.TRANSPORT_WIFI))return n;
        }
        return null;
    }
    private void address(){
        EditText input=new EditText(this);input.setSingleLine();input.setText(base);
        new AlertDialog.Builder(this).setTitle("Dirección del NUC").setMessage("IP del NUC en su Wi-Fi y puerto 8080")
            .setView(input).setPositiveButton("Guardar",(d,w)->{
                String candidate=input.getText().toString().trim();
                if(!candidate.startsWith("http://"))candidate="http://"+candidate;
                try{
                    URL u=new URL(candidate);
                    if(!u.getProtocol().equals("http") || u.getHost().isEmpty() || !u.getPath().isEmpty())
                        throw new Exception();
                    disconnect();base=candidate;
                    getPreferences(0).edit().putString("nuc_url",base).apply();
                    notice.setText("Dirección guardada: "+base);
                }catch(Exception error){notice.setText("Dirección inválida. Ejemplo: http://10.42.0.1:8080");}
            }).setNegativeButton("Cancelar",null).show();
    }
    private void connect(){
        wifi=wifiNetwork();
        if(wifi==null){notice.setText("Primero conéctate al Wi-Fi del NUC desde Ajustes.");return;}
        wifiPower.acquire(this);
        connected=true; long generation=++epoch;
        phase="conectando";connect.setText("Desconectar");notice.setText("Conectando a "+base);buttons();
        frames.execute(()->poll(generation));
    }
    private void disconnect(){
        wifiPower.release();
        connected=false;epoch++;busy=false;reviewMode=false;reviewSeen=false;phase="desconectado";
        if(video!=null)video.clear();
        if(connect!=null){connect.setText("Conectar al NUC");status.setText("Sin conexión");buttons();}
    }
    private JSONObject request(String path,JSONObject body,Network network,String address)throws Exception{
        long requestStart=SystemClock.elapsedRealtime();
        if(network==null)throw new IOException("No hay red Wi-Fi seleccionada");
        HttpURLConnection c=(HttpURLConnection)network.openConnection(new URL(address+path));
        c.setConnectTimeout(2000);
        c.setReadTimeout(path.startsWith("/api/vision/frame")?1200:5000);
        c.setUseCaches(false);
        boolean responseRead=false;
        try{
            if(body!=null){
                c.setRequestMethod("POST");c.setDoOutput(true);
                c.setRequestProperty("Content-Type","application/json");
                byte[] bytes=body.toString().getBytes(StandardCharsets.UTF_8);
                c.setFixedLengthStreamingMode(bytes.length);
                try(OutputStream out=c.getOutputStream()){out.write(bytes);}
            }
            int code=c.getResponseCode();
            long headersAt=SystemClock.elapsedRealtime();
            InputStream raw=code<400?c.getInputStream():c.getErrorStream();
            if(raw==null)throw new IOException("HTTP "+code);
            ByteArrayOutputStream out=new ByteArrayOutputStream();
            try(InputStream in=raw){byte[] buffer=new byte[8192];int n;
                while((n=in.read(buffer))!=-1){out.write(buffer,0,n);if(out.size()>4*1024*1024)throw new IOException("Respuesta demasiado grande");}}
            responseRead=true; // Cuerpo leido y cerrado: permitir reutilizacion de conexion HTTP/1.1.
            long bodyAt=SystemClock.elapsedRealtime();
            JSONObject response;
            if(path.equals("/api/vision/frame.jpg") && code==404)throw new FrameRouteUnavailable();
            if(path.equals("/api/vision/frame.jpg") && code==200){
                String metadata=c.getHeaderField("X-Lumi-Metadata");
                if(metadata==null)throw new IOException("Imagen sin metadatos de selección");
                response=new JSONObject(metadata);
                response.put("_jpeg_bytes",out.toByteArray());
            }else response=new JSONObject(new String(out.toByteArray(),StandardCharsets.UTF_8));
            if(path.startsWith("/api/vision/frame") && bodyAt-lastVideoLog>=2000){
                lastVideoLog=bodyAt;
                android.util.Log.d("LUMI_VIDEO","cabeceras_ms="+(headersAt-requestStart)+
                    " cuerpo_ms="+(bodyAt-headersAt)+" json_ms="+(SystemClock.elapsedRealtime()-bodyAt)+" bytes="+out.size());
            }
            if(code>=400)throw new IOException(response.optString("error","HTTP "+code));
            return response;
        }finally{if(!responseRead)c.disconnect();}
    }
    private Bitmap decode(JSONObject response)throws Exception{
        Object raw=response.opt("_jpeg_bytes");
        byte[] bytes=raw instanceof byte[]?(byte[])raw:Base64.decode(response.getString("jpeg"),Base64.DEFAULT);
        Bitmap b=BitmapFactory.decodeByteArray(bytes,0,bytes.length);
        if(b==null)throw new IOException("Imagen inválida");return b;
    }
    private void deliver(VideoUpdate next){
        if(pendingVideo.offer(next))ui.post(()->{
            VideoUpdate current=pendingVideo.take();
            if(current==null||current.generation!=epoch||!connected)return;
            if(current.error!=null){
                phase="reconectando";status.setText("Reconectando al NUC…");
                notice.setText(current.error+" · Reintentando por Wi-Fi");video.clear();buttons();return;
            }
            frameLoadMs=current.loadMs;
            videoFormat=current.snapshot.optString("_formato_video","JPEG/JSON");
            update(current.snapshot.optJSONObject("estado"));
            if(!reviewMode)video.show(current.bitmap,current.snapshot);
        });
    }
    private void poll(long generation){
        long lastWifiCheck=0;
        boolean binary=true;
        while(connected && foreground && generation==epoch){
            long start=SystemClock.elapsedRealtime();
            boolean success=false;
            try{
                Network current=wifi;
                if(current==null || start-lastWifiCheck>=1000){
                    Network available=wifiNetwork();
                    if(current==null || available==null || !current.equals(available))current=available;
                    lastWifiCheck=start;wifi=current;
                }
                if(current==null)throw new IOException("Wi-Fi desconectado");
                // El frame ya contiene estado y contrato: un GET atomico por iteracion.
                JSONObject frame;
                try{frame=request(binary?"/api/vision/frame.jpg":"/api/vision/frame",null,current,base);}
                catch(FrameRouteUnavailable error){
                    binary=false;
                    frame=request("/api/vision/frame",null,current,base);
                }
                final String format=binary?"JPEG binario":"JPEG/JSON";
                JSONObject state=frame.optJSONObject("estado");
                if(state==null || !state.optString("servidor").equals("lumi-vision-nuc-v1"))
                    throw new IOException("Este destino no es el servidor de visión del NUC");
                frame.getString("frame_id");
                Bitmap bitmap=decode(frame);
                frame.remove("_jpeg_bytes");frame.remove("jpeg");
                frame.put("_formato_video",format);
                long load=SystemClock.elapsedRealtime()-start;
                deliver(new VideoUpdate(generation,load,frame,bitmap,null));
                success=true;
            }catch(Exception error){
                wifi=null;
                deliver(new VideoUpdate(generation,0,null,null,
                    error.getMessage()!=null?error.getMessage():"No se pudo recibir la imagen"));
            }
            long wait=VideoFrameStats.waitMillis(start,SystemClock.elapsedRealtime(),success);
            try{if(wait>0)Thread.sleep(wait);}catch(InterruptedException error){return;}
        }
    }
    private void update(JSONObject state){
        if(state==null)return;
        phase=state.optString("estado");
        status.setText(phase+" · "+state.optString("mensaje"));
        detail.setText(String.format(java.util.Locale.getDefault(),
            "%s · NUC: %.1f FPS / %.0f ms · App: %s · Carga: %d ms\nMovimiento restringido · %s · %s",
            state.optString("metodo"),state.optDouble("fps"),state.optDouble("procesamiento_ms"),
            reviewMode?"revisión":String.format(java.util.Locale.getDefault(),"%.1f FPS",displayStats.fps(SystemClock.elapsedRealtime())),frameLoadMs,videoFormat,wifiPower.status()));
        notice.setText((phase.equals("preparando")||phase.equals("enrolando"))?
            "Gira despacio · "+(int)Math.ceil(state.optDouble("segundos_restantes"))+" s restantes":
            phase.equals("revision")?"Revisa identidad y vistas en TODOS los recortes antes de confirmar.":
            phase.equals("seleccionando")?"Toca el recuadro de la persona que quieres enrolar.":"");
        if(!phase.equals("revision")){reviewSeen=false;if(reviewMode){reviewMode=false;review.setText("Ver recortes");}}
        buttons();
    }
    private void buttons(){
        boolean ready=connected && !busy && !phase.equals("conectando") && !phase.equals("reconectando");
        enroll.setEnabled(ready);capture.setEnabled(ready&&phase.equals("seleccionado"));
        confirm.setEnabled(ready&&phase.equals("revision")&&reviewSeen);
        review.setEnabled(ready&&phase.equals("revision"));
        repeat.setEnabled(ready);cancel.setEnabled(ready);
        follow.setEnabled(ready&&(phase.equals("listo")||phase.equals("perdido")));
        follow.setText(phase.equals("perdido")?"Reanudar seguimiento visual":"Iniciar seguimiento visual");
    }
    private void choosePerson(){
        if(!connected||busy||video.snapshot==null||reviewMode||
            (!phase.equals("seleccionando")&&!phase.equals("seleccionado"))){
            notice.setText("Pulsa Enrolar y espera los recuadros de la cámara.");return;
        }
        final JSONObject image=video.snapshot;
        JSONArray boxes=image.optJSONArray("cajas");
        if(boxes==null||boxes.length()==0){notice.setText("Todavía no hay personas detectadas.");return;}
        String[] labels=new String[boxes.length()];
        for(int i=0;i<labels.length;i++)labels[i]="Persona "+(i+1);
        new AlertDialog.Builder(this).setTitle("Persona en esta imagen").setItems(labels,(d,index)->{
            try{JSONObject body=new JSONObject();body.put("frame_id",image.getString("frame_id"));
                body.put("candidato",index);send("/api/vision/seleccionar",body);
            }catch(JSONException error){notice.setText("Espera una nueva imagen.");}
        }).setNegativeButton("Cancelar",null).show();
    }
    private void action(String name){
        try{JSONObject body=new JSONObject();body.put("accion",name);send("/api/enrolamiento",body);}
        catch(JSONException error){notice.setText(error.getMessage());}
    }
    private void send(String path,JSONObject body){
        if(!connected || busy)return;
        busy=true;buttons();long generation=epoch;Network network=wifi;String address=base;
        commands.execute(()->{
            String failure=null;
            try{request(path,body,network,address);}catch(Exception error){failure=error.getMessage();}
            final String result=failure;
            ui.post(()->{if(generation!=epoch)return;busy=false;buttons();
                if(result!=null){notice.setText(result);Toast.makeText(this,result,Toast.LENGTH_LONG).show();}});
        });
    }
    private void toggleReview(){
        if(reviewMode){reviewMode=false;review.setText("Ver recortes");buttons();return;}
        if(!connected||busy)return;
        busy=true;buttons();long generation=epoch;Network network=wifi;String address=base;
        commands.execute(()->{
            try{
                JSONObject image=request("/api/vision/revision",null,network,address);
                Bitmap bitmap=decode(image);
                ui.post(()->{if(generation!=epoch)return;busy=false;reviewMode=true;reviewSeen=true;
                    video.show(bitmap,null);review.setText("Volver a cámara");buttons();});
            }catch(Exception error){ui.post(()->{if(generation!=epoch)return;busy=false;buttons();notice.setText(error.getMessage());});}
        });
    }
    @Override protected void onResume(){super.onResume();foreground=true;}
    @Override protected void onPause(){foreground=false;disconnect();super.onPause();}
    @Override protected void onDestroy(){disconnect();frames.shutdownNow();commands.shutdownNow();super.onDestroy();}

    private class SnapshotView extends View {
        private Bitmap bitmap;
        private JSONObject snapshot;
        private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        SnapshotView(){super(VisionActivity.this);setBackgroundColor(0xff081412);
            setContentDescription("Cámara del NUC. Toca un recuadro para seleccionar a la persona.");}
        void clear(){bitmap=null;snapshot=null;displayStats.reset();invalidate();}
        void show(Bitmap b,JSONObject data){bitmap=b;snapshot=data;invalidate();}
        @Override protected void onDraw(Canvas canvas){
            super.onDraw(canvas);if(bitmap==null)return;
            FrameMapping map=new FrameMapping(bitmap.getWidth(),bitmap.getHeight(),getWidth(),getHeight());
            canvas.save();canvas.translate(map.left,map.top);canvas.scale(map.scale,map.scale);
            paint.setStyle(Paint.Style.FILL);paint.setColor(Color.WHITE);paint.setFilterBitmap(true);
            canvas.drawBitmap(bitmap,0,0,paint);
            if(snapshot!=null){
                displayStats.record(snapshot.optString("frame_id",null),SystemClock.elapsedRealtime());
                JSONArray boxes=snapshot.optJSONArray("cajas");
                if(boxes!=null)for(int i=0;i<boxes.length();i++){
                    JSONArray b=boxes.optJSONArray(i);if(b==null)continue;
                    int selected=snapshot.optInt("seleccionado",-1),target=snapshot.optInt("objetivo",-1);
                    paint.setColor(i==target?0xff32e889:i==selected?0xff66dbff:0xffffcc55);
                    paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(3);
                    canvas.drawRect((float)b.optDouble(0),(float)b.optDouble(1),(float)b.optDouble(2),(float)b.optDouble(3),paint);
                    paint.setStyle(Paint.Style.FILL);paint.setTextSize(18);
                    canvas.drawText("Persona "+(i+1),(float)b.optDouble(0),Math.max(20,(float)b.optDouble(1)-5),paint);
                }
            }
            canvas.restore();
        }
        @Override public boolean onTouchEvent(MotionEvent event){
            if(event.getAction()!=MotionEvent.ACTION_UP)return true;
            performClick();
            if(bitmap==null||snapshot==null||reviewMode||busy)return true;
            if(!phase.equals("seleccionando")&&!phase.equals("seleccionado"))return true;
            float[] point=new FrameMapping(bitmap.getWidth(),bitmap.getHeight(),getWidth(),getHeight())
                .imagePoint(event.getX(),event.getY());
            if(point==null)return true;
            JSONArray boxes=snapshot.optJSONArray("cajas");int chosen=-1;
            if(boxes!=null)for(int i=0;i<boxes.length();i++){
                JSONArray b=boxes.optJSONArray(i);if(b==null)continue;
                if(point[0]>=b.optDouble(0)&&point[0]<=b.optDouble(2)&&point[1]>=b.optDouble(1)&&point[1]<=b.optDouble(3)){
                    if(chosen!=-1){notice.setText("Recuadros superpuestos: separa a las personas antes de seleccionar.");return true;}
                    chosen=i;
                }
            }
            if(chosen<0){notice.setText("Toca dentro de un recuadro.");return true;}
            try{
                JSONObject body=new JSONObject();body.put("frame_id",snapshot.getString("frame_id"));body.put("candidato",chosen);
                send("/api/vision/seleccionar",body);
            }catch(JSONException error){notice.setText("Espera la siguiente imagen e inténtalo otra vez.");}
            return true;
        }
        @Override public boolean performClick(){super.performClick();return true;}
    }
}
