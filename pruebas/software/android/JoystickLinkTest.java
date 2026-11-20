package cl.lumi.panel;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;
public final class JoystickLinkTest {
    static void check(boolean value) { if(!value) throw new AssertionError(); }
    static byte[] text(String s) { return s.getBytes(StandardCharsets.UTF_8); }
    static void transport(int delay,int timeout,boolean succeed,boolean staleFirst) throws Exception {
        try(DatagramSocket server=new DatagramSocket(0,InetAddress.getLoopbackAddress());
            DatagramSocket client=new DatagramSocket()) {
            client.connect(InetAddress.getLoopbackAddress(),server.getLocalPort());
            ExecutorService executor=Executors.newSingleThreadExecutor();
            Future<Integer> result=executor.submit(() -> {
                byte[] buffer=new byte[100];DatagramPacket p=new DatagramPacket(buffer,buffer.length);
                server.setSoTimeout(1000);server.receive(p);
                check(new String(p.getData(),0,p.getLength(),StandardCharsets.UTF_8).equals("request7"));
                if(staleFirst) server.send(new DatagramPacket(text("ack6"),4,p.getSocketAddress()));
                Thread.sleep(delay);
                server.send(new DatagramPacket(text("ack7"),4,p.getSocketAddress()));
                server.setSoTimeout(60);
                try { server.receive(p);return 2; } catch(SocketTimeoutException expected) { return 1; }
            });
            try {
                byte[] reply=DatagramRoundTrip.exchange(client,text("request7"),timeout,
                    bytes -> new String(bytes,StandardCharsets.UTF_8).equals("ack7"));
                check(succeed && new String(reply,StandardCharsets.UTF_8).equals("ack7"));
            } catch(SocketTimeoutException error) { check(!succeed); }
            finally { try { check(result.get(2,TimeUnit.SECONDS)==1); } finally { executor.shutdownNow(); } }
        }
    }
    public static void main(String[] args) throws Exception {
        check(JoystickDirection.classify(0,-100,100).equals("adelante"));
        check(JoystickDirection.classify(0,100,100).equals("atras"));
        check(JoystickDirection.classify(-100,0,100).equals("izquierda"));
        check(JoystickDirection.classify(100,0,100).equals("derecha"));
        check(JoystickDirection.classify(0,-24,100).equals("parar"));
        check(JoystickDirection.classify(0,-25,100).equals("adelante"));
        check(JoystickDirection.classify(Float.NaN,0,100).equals("parar"));
        check(JoystickDirection.classify(0,-100,0).equals("parar"));
        check(JoystickDirection.bank(0,-30,100,null).equals("parar"));
        check(JoystickDirection.bank(0,-30,100,"adelante").equals("adelante"));
        check(JoystickDirection.bank(51,-50,100,"adelante").equals("adelante"));
        check(JoystickDirection.bank(80,-30,100,"adelante").equals("derecha"));
        check(JoystickDirection.bank(0,50,100,"adelante").equals("atras"));
        LinkProbeStats stable=new LinkProbeStats();
        for(int i=0;i<12;++i) stable.add(5,i*50);
        check(stable.acceptable());
        LinkProbeStats slow=new LinkProbeStats();
        for(int i=0;i<12;++i) slow.add(150,i*210);
        check(!slow.acceptable());
        LinkProbeStats loss=new LinkProbeStats();
        for(int i=0;i<12;++i) loss.add(5,i*50);
        loss.fail();check(!loss.acceptable());
        transport(140,100,false,false); // Reproduces old app's premature ACK timeout.
        transport(140,180,true,false);
        transport(20,180,true,true); // Discard unrelated request; do not retransmit.
        System.out.println("PASS joystick geometry, invalid input, probe thresholds, real UDP delayed/lost correlation, no retransmit");
    }
}
