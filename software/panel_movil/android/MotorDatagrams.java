package cl.lumi.panel;
import android.content.Context;
import android.net.Network;
import android.os.SystemClock;
import java.io.IOException;
import java.net.*;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

/** Persistent endpoint, independent receiver, and nonblocking motion publication. */
final class MotorDatagrams {
    interface Validity { boolean current(); }
    interface MotionReply { void received(JSONObject reply,Exception error); }
    static final class Rejected extends IOException {
        final JSONObject reply;
        Rejected(String message,JSONObject reply) { super(message);this.reply=reply; }
    }
    private final PersistentDatagramEndpoint endpoint=new PersistentDatagramEndpoint();
    private final AsyncDatagramPipe pipe=new AsyncDatagramPipe(data ->
        new JSONObject(new String(data,StandardCharsets.UTF_8)).getLong("request"),SystemClock::elapsedRealtime);
    private long request,observedGeneration;
    private volatile String trace="Esperando canal de datos";
    private final java.util.ArrayDeque<String> recent=new java.util.ArrayDeque<>();
    String trace() { return trace; }
    private synchronized void note(String text) {
        trace=text;if(recent.size()>=128) recent.removeFirst();recent.addLast(SystemClock.elapsedRealtime()+" "+text);
    }
    synchronized String report() {
        StringBuilder text=new StringBuilder();for(String line:recent) text.append(line).append('\n');return text.toString();
    }
    synchronized void save(Context context) {
        try(java.io.FileOutputStream out=context.openFileOutput("control-enlace.log",Context.MODE_PRIVATE)) {
            out.write(report().getBytes(StandardCharsets.UTF_8));
        } catch(IOException ignored) { }
    }
    private synchronized AsyncDatagramPipe.Receipt transmit(Context context,String action,JSONObject body,Validity validity,AsyncDatagramPipe.Observer observer) throws Exception {
        Network route=EspWifiRoute.current(context);
        DatagramSocket socket=endpoint.ensure(route,route::bindSocket,InetAddress.getByName("192.168.4.1"),8082);
        long generation=endpoint.generation();boolean changed=observedGeneration!=0 && observedGeneration!=generation;observedGeneration=generation;
        if(validity!=null && !validity.current()) return null;
        if(changed && validity!=null) throw new IOException("Cambió la red Wi-Fi; datos disponibles, requiere nueva habilitación");
        long id=++request & 0xffffffffL;
        body.put("request",id).put("action",action);
        if(validity!=null && (!body.has("seq") || body.getLong("seq")<=0)) throw new IOException("Orden de movimiento sin secuencia válida");
        note(validity==null?"TX "+action.toUpperCase(java.util.Locale.ROOT)+" #"+id+" · mensaje de control/consulta":
            "TX "+action+" #"+id+" · secuencia "+body.getLong("seq"));
        return pipe.send(socket,body.toString().getBytes(StandardCharsets.UTF_8),id,observer);
    }
    private JSONObject decode(AsyncDatagramPipe.Receipt receipt) throws Exception {
        if(receipt.error!=null) throw receipt.error;
        JSONObject result=new JSONObject(new String(receipt.reply,StandardCharsets.UTF_8));
        result.put("_request_started_ms",receipt.sentAt);
        note("RX #"+receipt.id+" · RTT "+(receipt.receivedAt-receipt.sentAt)+" ms · "+(result.optBoolean("ok")?"aceptado":"rechazado"));
        if(!result.optBoolean("ok")) {
            JSONObject bank=result.optJSONObject("banco");
            throw new Rejected("Orden rechazada: "+(bank==null?result.optString("mensaje"):
                bank.optString("fallo")+" · "+bank.optString("ultimo_rechazo")+" · intervalo "+bank.optLong("intervalo_orden_ms")+" ms"),result);
        }
        return result;
    }
    // Only explicit setup/stop/diagnostic commands wait. Never holds the sender lock while awaiting a reply.
    JSONObject exchange(Context context,String action,JSONObject body) throws Exception {
        int attempts=action.equals("parar")?3:1;
        for(int attempt=0;attempt<attempts;++attempt) {
            AsyncDatagramPipe.Receipt receipt=transmit(context,action,body,null,null);
            try { receipt.await(action.equals("ping") || action.equals("habilitar")?600:180);return decode(receipt); }
            catch(Exception error) {
                pipe.forget(receipt);endpoint.failed(receipt.socket,error);note("Datos pendientes: "+action+" · "+error.getMessage());
                if(error instanceof SocketTimeoutException && attempt+1<attempts) continue; // Only STOP can be repeated automatically.
                save(context);
                if(error instanceof SocketTimeoutException) throw new IOException("Sin respuesta a "+action+"; el canal permanece abierto",error);
                throw error;
            }
        }
        throw new IOException("No se confirmó la parada");
    }
    void sendMotion(Context context,String action,JSONObject body,Validity validity,MotionReply callback) throws Exception {
        long expectedBoot=body.getLong("boot"),expectedEpoch=body.getLong("epoch");
        transmit(context,action,body,validity,receipt -> {
            if(!validity.current()) return;
            try {
                JSONObject result=decode(receipt);JSONObject bank=result.getJSONObject("banco");
                if(bank.getLong("boot")!=expectedBoot || bank.getLong("epoch")!=expectedEpoch || !bank.optBoolean("habilitado"))
                    throw new Rejected("La ESP detuvo el gesto; requiere nueva habilitación",result);
                callback.received(result,null);
            } catch(Exception error) { endpoint.failed(receipt.socket,error);callback.received(null,error); }
        });
    }
    synchronized void close() { pipe.close();endpoint.close();observedGeneration=0; }
}
