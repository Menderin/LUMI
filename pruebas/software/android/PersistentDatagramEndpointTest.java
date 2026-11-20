package cl.lumi.panel;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
public final class PersistentDatagramEndpointTest {
    static void check(boolean ok,String why) { if(!ok) throw new AssertionError(why); }
    static byte[] bytes(String s) { return s.getBytes(StandardCharsets.UTF_8); }
    static void ping(DatagramSocket socket,String text) throws Exception {
        String result=new String(DatagramRoundTrip.exchange(socket,bytes(text),200,
            data -> new String(data,StandardCharsets.UTF_8).equals("reply:"+text)),StandardCharsets.UTF_8);
        check(result.equals("reply:"+text),"wrong reply");
    }
    public static void main(String[] args) throws Exception {
        try(DatagramSocket server=new DatagramSocket(0,InetAddress.getLoopbackAddress())) {
            ExecutorService worker=Executors.newSingleThreadExecutor();
            Future<List<Integer>> received=worker.submit(() -> {
                List<Integer> ports=new ArrayList<>();
                for(int i=0;i<6;++i) {
                    DatagramPacket p=new DatagramPacket(new byte[100],100);server.setSoTimeout(1500);server.receive(p);
                    ports.add(p.getPort());String text=new String(p.getData(),0,p.getLength(),StandardCharsets.UTF_8);
                    if(text.equals("drop")) continue;
                    byte[] answer=bytes("reply:"+text);server.send(new DatagramPacket(answer,answer.length,p.getSocketAddress()));
                }
                return ports;
            });
            PersistentDatagramEndpoint endpoint=new PersistentDatagramEndpoint();int[] bindings={0};
            PersistentDatagramEndpoint.Binder binder=s -> ++bindings[0];
            try {
                DatagramSocket first=endpoint.ensure("wifi-1",binder,InetAddress.getLoopbackAddress(),server.getLocalPort());
                ping(first,"before");
                try { DatagramRoundTrip.exchange(first,bytes("drop"),45,data -> true);throw new AssertionError("Expected missing reply"); }
                catch(SocketTimeoutException timeout) { endpoint.failed(timeout); }
                check(!first.isClosed(),"timeout closed data endpoint");
                check(endpoint.ensure("wifi-1",binder,InetAddress.getLoopbackAddress(),server.getLocalPort())==first,"socket changed after loss");
                ping(first,"recovered");
                endpoint.failed(new java.io.IOException("token_vencido"));
                endpoint.failed(new java.io.IOException("motion suspended after blackout"));
                check(!first.isClosed(),"protocol failure closed data endpoint");
                ping(first,"after-nack");
                DatagramSocket changed=endpoint.ensure("wifi-2",binder,InetAddress.getLoopbackAddress(),server.getLocalPort());
                check(first.isClosed() && changed!=first,"network change must rebind automatically");
                endpoint.failed(first,new SocketException("late error on old route"));
                check(!changed.isClosed(),"old route failure closed the new endpoint");ping(changed,"new-route");
                endpoint.failed(new SocketException("network endpoint invalid"));check(changed.isClosed(),"broken socket was kept");
                DatagramSocket restored=endpoint.ensure("wifi-2",binder,InetAddress.getLoopbackAddress(),server.getLocalPort());
                ping(restored,"socket-restored");
                List<Integer> ports=received.get(2,TimeUnit.SECONDS);
                check(ports.get(0).equals(ports.get(1)) && ports.get(1).equals(ports.get(2)) && ports.get(2).equals(ports.get(3)),"source port must survive timeout/NACK");
                check(bindings[0]==3,"unexpected socket recreation");
                try { endpoint.ensure("wifi-3",s -> { throw new java.io.IOException("bind failed"); },InetAddress.getLoopbackAddress(),server.getLocalPort());throw new AssertionError("bind must fail"); }
                catch(java.io.IOException expected) { }
                DatagramSocket afterBind=endpoint.ensure("wifi-3",binder,InetAddress.getLoopbackAddress(),server.getLocalPort());
                check(!afterBind.isClosed(),"bind failure prevented later recovery");
            } finally { endpoint.close();worker.shutdownNow(); }
        }
        System.out.println("PASS persistent UDP: loss then recovery, same port after NACK/suspension, route change, broken socket, bind failure recovery");
    }
}
