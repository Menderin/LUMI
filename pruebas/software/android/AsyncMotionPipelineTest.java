package cl.lumi.panel;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

public final class AsyncMotionPipelineTest {
    static void check(boolean ok,String why) { if(!ok) throw new AssertionError(why); }
    static long now() { return TimeUnit.NANOSECONDS.toMillis(System.nanoTime()); }
    static byte[] data(String s) { return s.getBytes(StandardCharsets.UTF_8); }
    static final class Server implements AutoCloseable {
        final DatagramSocket socket;
        final ScheduledExecutorService replies=Executors.newScheduledThreadPool(2);
        final List<Long> times=new CopyOnWriteArrayList<>(),ids=new CopyOnWriteArrayList<>();
        final List<Integer> ports=new CopyOnWriteArrayList<>();
        volatile boolean dropMotion;volatile boolean running=true;
        volatile long firstId;volatile SocketAddress client;
        Server(boolean drop) throws Exception {
            socket=new DatagramSocket(0,InetAddress.getLoopbackAddress());dropMotion=drop;
            Thread receiver=new Thread(() -> {
                while(running) try {
                    DatagramPacket packet=new DatagramPacket(new byte[200],200);socket.receive(packet);
                    String[] parts=new String(packet.getData(),0,packet.getLength(),StandardCharsets.UTF_8).split(":");
                    String kind=parts[0];long id=Long.parseLong(parts[1]);SocketAddress peer=packet.getSocketAddress();
                    if(kind.equals("M")) {
                        if(firstId==0) { firstId=id;client=peer; }
                        times.add(now());ids.add(id);ports.add(packet.getPort());
                        if(dropMotion || ids.size()%3==0) continue;
                    }
                    long delay=kind.equals("M")?150:kind.equals("SLOW")?400:0;
                    replies.schedule(() -> reply(id,peer),delay,TimeUnit.MILLISECONDS);
                } catch(Exception error) { if(running) throw new RuntimeException(error); }
            },"fake-esp");receiver.setDaemon(true);receiver.start();
        }
        void reply(long id,SocketAddress peer) {
            byte[] answer=data(Long.toString(id));
            try { socket.send(new DatagramPacket(answer,answer.length,peer)); } catch(Exception ignored) { }
        }
        public void close() { running=false;socket.close();replies.shutdownNow(); }
    }
    static void continuous() throws Exception {
        try(Server server=new Server(false);DatagramSocket socket=new DatagramSocket()) {
            socket.connect(InetAddress.getLoopbackAddress(),server.socket.getLocalPort());
            AsyncDatagramPipe pipe=new AsyncDatagramPipe(reply -> Long.parseLong(new String(reply,StandardCharsets.UTF_8)),AsyncMotionPipelineTest::now);
            MotionHeartbeat pump=new MotionHeartbeat(AsyncMotionPipelineTest::now);
            AtomicLong request=new AtomicLong();AtomicReference<Exception> failure=new AtomicReference<>();
            try {
                pump.start(2200,run -> {
                    long id=request.incrementAndGet();
                    pipe.send(socket,data("M:"+id),id,r -> { if(r.error==null) pump.confirm(run,r.sentAt); });
                },(run,error) -> failure.set(error));
                // A blocked 400 ms RPC must not block the periodic motion publisher or receiver.
                long rpc=request.incrementAndGet();
                AsyncDatagramPipe.Receipt slow=pipe.send(socket,data("SLOW:"+rpc),rpc,null);
                slow.await(800);
                Thread.sleep(950);pump.stop();
                check(failure.get()==null,"publisher failed under delayed/dropped ACKs: "+failure.get());
                check(server.times.size()>=20,"RPC/ACK waiting starved publication");
                long first=server.times.get(0);int beforeAck=0;
                for(long time:server.times) if(time-first<145) ++beforeAck;
                check(beforeAck>=2,"publisher waited for its first ACK");
                check(new HashSet<>(server.ids).size()==server.ids.size(),"motion replayed");
                check(new HashSet<>(server.ports).size()==1,"socket changed during stream");
                int stopped=server.times.size();Thread.sleep(120);
                check(server.times.size()==stopped,"commands continued after releasing control");
            } finally { pump.close();pipe.close(); }
        }
    }
    static void blackout() throws Exception {
        try(Server server=new Server(true);DatagramSocket socket=new DatagramSocket()) {
            socket.connect(InetAddress.getLoopbackAddress(),server.socket.getLocalPort());
            AsyncDatagramPipe pipe=new AsyncDatagramPipe(reply -> Long.parseLong(new String(reply,StandardCharsets.UTF_8)),AsyncMotionPipelineTest::now);
            MotionHeartbeat pump=new MotionHeartbeat(AsyncMotionPipelineTest::now);
            AtomicLong request=new AtomicLong();CountDownLatch suspended=new CountDownLatch(1);AtomicLong ended=new AtomicLong();
            try {
                long firstRun=pump.start(2000,run -> {
                    long id=request.incrementAndGet();pipe.send(socket,data("M:"+id),id,r -> { if(r.error==null) pump.confirm(run,r.sentAt); });
                },(run,error) -> { ended.set(run);suspended.countDown(); });
                check(suspended.await(1200,TimeUnit.MILLISECONDS),"missing ACKs never suspended control");
                check(!pump.running() && ended.get()==firstRun,"motion still active after blackout");
                check(!socket.isClosed(),"suspension killed the data channel");
                long id=request.incrementAndGet();pipe.send(socket,data("PING:"+id),id,null).await(400);
                int sent=server.times.size();server.reply(server.firstId,server.client);Thread.sleep(100);
                check(!pump.running() && server.times.size()==sent,"old ACK restarted motion");
                server.dropMotion=false;CountDownLatch pulseDone=new CountDownLatch(1);
                long newRun=pump.start(250,run -> {
                    long next=request.incrementAndGet();pipe.send(socket,data("M:"+next),next,r -> { if(r.error==null) pump.confirm(run,r.sentAt); });
                },(run,error) -> { check(error instanceof MotionHeartbeat.PulseEnded,"wrong pulse end");pulseDone.countDown(); });
                check(newRun!=firstRun && !pump.confirm(firstRun,now()),"old ACK authorized a new gesture");
                check(pulseDone.await(800,TimeUnit.MILLISECONDS),"pulse maximum did not stop");
            } finally { pump.close();pipe.close(); }
        }
    }
    public static void main(String[] args) throws Exception {
        continuous();blackout();
        System.out.println("PASS async pipeline: delayed/lost ACKs, blocked RPC without starving motion, same socket, release, blackout/data recovery, no automatic resume, max pulse");
    }
}
