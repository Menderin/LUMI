package cl.lumi.panel;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;

public final class DriveAckWindowTest {
    static void check(boolean condition,String message) { if(!condition) throw new AssertionError(message); }
    static long now() { return TimeUnit.NANOSECONDS.toMillis(System.nanoTime()); }
    static byte[] bytes(long value) { return Long.toString(value).getBytes(StandardCharsets.UTF_8); }
    static void rules() throws Exception {
        DriveAckWindow w=new DriveAckWindow();
        w.sent(1,0);check(w.missed(45),"one lost ACK must be tolerated");
        w.sent(2,50);check(w.acknowledge(1,70),"late ACK accepted for recent outstanding request");
        check(w.latency()==70,"late ACK RTT is measured from original request");
        check(w.started()==0,"late ACK must retain the original send timestamp");
        check(!w.acknowledge(999,80),"unknown ACK rejected");
        check(!w.acknowledge(1,80),"duplicate ACK rejected");
        w.reset();w.sent(3,100);check(!w.acknowledge(2,101),"old gesture ACK rejected");
        w.reset();
        for(int i=0;i<4;++i) { w.sent(i+1,i*50);check(w.missed(i*50+45)==(i<3),"fourth timeout ends window"); }
        w.reset();w.sent(1,0);
        check(!w.acknowledge(1,200),"late confirmation must not revive expired grace");
        try { w.sent(2,200);throw new AssertionError("silence must prevent next motion"); }
        catch(java.io.IOException expected) { }
        w.reset();w.sent(3,500);check(w.acknowledge(3,501),"explicit new gesture can start new window");
    }
    static void radio(int lostAcks,boolean delayFirst,boolean expectStop) throws Exception {
        try(DatagramSocket server=new DatagramSocket(0,InetAddress.getLoopbackAddress());
            DatagramSocket client=new DatagramSocket()) {
            client.connect(InetAddress.getLoopbackAddress(),server.getLocalPort());
            ScheduledExecutorService threads=Executors.newScheduledThreadPool(2);
            List<Long> sent=new ArrayList<>();Set<Long> confirmed=new HashSet<>();
            Future<List<Long>> received=threads.submit(() -> {
                List<Long> ids=new ArrayList<>();server.setSoTimeout(300);int port=-1;
                while(true) {
                    DatagramPacket packet=new DatagramPacket(new byte[100],100);
                    try { server.receive(packet); } catch(SocketTimeoutException finished) { return ids; }
                    if(port<0) port=packet.getPort();
                    check(port==packet.getPort(),"socket/port must survive isolated ACK loss");
                    long id=Long.parseLong(new String(packet.getData(),0,packet.getLength(),StandardCharsets.UTF_8));
                    ids.add(id);
                    if(ids.size()<=lostAcks) continue;
                    SocketAddress peer=packet.getSocketAddress();
                    Runnable reply=() -> { try { server.send(new DatagramPacket(bytes(id),bytes(id).length,peer)); }
                        catch(Exception error) { throw new RuntimeException(error); } };
                    if(delayFirst) threads.schedule(reply,70,TimeUnit.MILLISECONDS);else reply.run();
                }
            });
            DriveAckWindow w=new DriveAckWindow();boolean stopped=false;
            try {
                for(long id=1;id<=6;++id) {
                    long started=now();
                    try { w.sent(id,started); } catch(java.io.IOException expired) { stopped=true;break; }
                    sent.add(id);
                    try {
                        byte[] reply=DatagramRoundTrip.exchange(client,bytes(id),w.waitBudget(now()),data ->
                            w.acknowledge(Long.parseLong(new String(data,StandardCharsets.UTF_8)),now()));
                        confirmed.add(Long.parseLong(new String(reply,StandardCharsets.UTF_8)));
                    } catch(SocketTimeoutException timeout) { if(!w.missed(now())) { stopped=true;break; } }
                    long rest=50-(now()-started);if(rest>0) Thread.sleep(rest);
                }
                List<Long> observed=received.get(2,TimeUnit.SECONDS);
                check(stopped==expectStop,"unexpected link outcome");
                check(observed.equals(sent),"every packet must be a new command; never replay missing command");
                check(new HashSet<>(observed).size()==observed.size(),"no retransmissions");
                if(delayFirst) check(confirmed.contains(1L),"delayed reply must be consumed during later exchange");
                if(expectStop) check(sent.size()<=4,"bounded missing-ACK stop");
                else check(sent.size()==6,"isolated losses must not terminate gesture");
            } finally { threads.shutdownNow(); }
        }
    }
    public static void main(String[] args) throws Exception {
        rules();
        radio(1,false,false);
        radio(2,false,false);
        radio(0,true,false);
        radio(100,false,true);
        System.out.println("PASS bounded ACK window: isolated/consecutive loss, late ACK, stable socket, fresh commands, total blackout, reset/no revival");
    }
}
