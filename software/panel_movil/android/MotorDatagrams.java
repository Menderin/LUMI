package cl.lumi.panel;
import android.content.Context;
import android.os.SystemClock;
import java.io.IOException;
import java.net.DatagramSocket;
import java.net.DatagramPacket;
import java.net.InetAddress;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

/** One ordered exchange at a time; never retransmit a motion packet. */
final class MotorDatagrams {
    private DatagramSocket socket;
    private long request;
    private volatile String trace="Sin envíos UDP";
    String trace() { return trace; }
    private final java.util.ArrayDeque<String> recent=new java.util.ArrayDeque<>();
    private void note(String value) {
        trace=value;
        if(recent.size()>=128) recent.removeFirst();
        recent.addLast(SystemClock.elapsedRealtime()+" "+value);
    }
    synchronized void save(Context context) {
        try (java.io.FileOutputStream out=context.openFileOutput("control-enlace.log",Context.MODE_PRIVATE)) {
            for(String line:recent) out.write((line+"\n").getBytes(StandardCharsets.UTF_8));
        } catch(IOException ignored) { }
    }
    synchronized JSONObject exchange(Context context,String action,JSONObject body) throws Exception {
        if (socket == null || socket.isClosed()) {
            socket = new DatagramSocket();
            try {
                EspWifiRoute.bind(context,socket);
                socket.connect(InetAddress.getByName("192.168.4.1"),8082);
            } catch (Exception error) { socket.close(); socket=null; throw error; }
        }
        long id=++request & 0xffffffffL;
        body.put("request",id).put("action",action);
        byte[] data=body.toString().getBytes(StandardCharsets.UTF_8);
        int waitMs=action.equals("ping") || action.equals("habilitar") ? 600 : 180;
        long started=SystemClock.elapsedRealtime();
        try {
            note("TX "+action+" #"+id+" seq="+body.optLong("seq",-1));
            byte[] reply=DatagramRoundTrip.exchange(socket,data,waitMs,bytes ->
                new JSONObject(new String(bytes,StandardCharsets.UTF_8)).optLong("request",-1)==id);
            JSONObject result=new JSONObject(new String(reply,StandardCharsets.UTF_8));
                note("ACK "+action+" #"+id+" "+(SystemClock.elapsedRealtime()-started)+" ms ok="+result.optBoolean("ok"));
                if (!result.optBoolean("ok")) {
                    JSONObject bank=result.optJSONObject("banco");
                    throw new IOException("Orden rechazada: " + (bank == null ? result.optString("mensaje") :
                        bank.optString("fallo")+" · "+bank.optString("ultimo_rechazo")+
                        " · intervalo "+bank.optLong("intervalo_orden_ms")+" ms"));
                }
                return result;
        } catch (Exception error) {
            socket.close(); socket=null;
            if(error instanceof SocketTimeoutException) {
                String failure="Sin ACK UDP de "+action+" #"+id+" en "+waitMs+" ms; no se confirmó la recepción";
                note(failure);
                save(context);
                throw new IOException(failure,error);
            }
            note("ERROR "+action+" #"+id+" "+error.getMessage());
            save(context);
            throw error;
        }
    }
    synchronized void close() { if(socket != null) socket.close(); socket=null; }
}
