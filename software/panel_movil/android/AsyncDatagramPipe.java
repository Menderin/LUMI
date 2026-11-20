package cl.lumi.panel;
import java.net.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Independent receiver: no request ever blocks publication of a later command. */
final class AsyncDatagramPipe {
    interface IdReader { long read(byte[] reply) throws Exception; }
    interface Observer { void completed(Receipt receipt); }
    static final class Receipt {
        final long id,sentAt;
        final DatagramSocket socket;
        final Observer observer;
        final CountDownLatch ready=new CountDownLatch(1);
        private final AtomicBoolean done=new AtomicBoolean();
        volatile byte[] reply;
        volatile Exception error;
        volatile long receivedAt;
        Receipt(long id,long sentAt,DatagramSocket socket,Observer observer) {
            this.id=id;this.sentAt=sentAt;this.socket=socket;this.observer=observer;
        }
        void complete(byte[] data,Exception failure,long now) {
            if(!done.compareAndSet(false,true)) return;
            reply=data;error=failure;receivedAt=now;ready.countDown();
            if(observer!=null) observer.completed(this);
        }
        byte[] await(int timeoutMs) throws Exception {
            if(!ready.await(timeoutMs,TimeUnit.MILLISECONDS)) throw new SocketTimeoutException();
            if(error!=null) throw error;
            return reply;
        }
    }
    private final IdReader reader;
    private final MonoClock clock;
    private final ConcurrentHashMap<Long,Receipt> pending=new ConcurrentHashMap<>();
    private volatile DatagramSocket current;
    AsyncDatagramPipe(IdReader reader,MonoClock clock) { this.reader=reader;this.clock=clock; }
    private synchronized void attach(DatagramSocket socket) throws Exception {
        if(current==socket) return;
        DatagramSocket old=current;current=socket;
        if(old!=null) fail(old,new SocketException("Network endpoint replaced"));
        socket.setSoTimeout(100);
        Thread worker=new Thread(() -> receive(socket),"lumi-udp-receiver");worker.setDaemon(true);worker.start();
    }
    Receipt send(DatagramSocket socket,byte[] payload,long id,Observer observer) throws Exception {
        attach(socket);
        long now=clock.now();
        for(Receipt old:pending.values()) {
            if(now-old.sentAt>=1000 && pending.remove(old.id,old) && old.observer==null)
                old.complete(null,new SocketTimeoutException(),now);
            // Individual missing motion ACKs expire silently. Aggregate liveness is owned by MotionHeartbeat.
        }
        if(pending.size()>=64) throw new java.io.IOException("Too many outstanding requests");
        Receipt receipt=new Receipt(id,now,socket,observer);
        if(pending.putIfAbsent(id,receipt)!=null) throw new java.io.IOException("Duplicate request id");
        try { socket.send(new DatagramPacket(payload,payload.length)); }
        catch(Exception error) { pending.remove(id,receipt);receipt.complete(null,error,clock.now()); }
        return receipt;
    }
    void forget(Receipt receipt) { pending.remove(receipt.id,receipt); }
    private void receive(DatagramSocket socket) {
        while(current==socket && !socket.isClosed()) {
            try {
                DatagramPacket packet=new DatagramPacket(new byte[2048],2048);socket.receive(packet);
                byte[] reply=java.util.Arrays.copyOf(packet.getData(),packet.getLength());
                long id;
                try { id=reader.read(reply); } catch(Exception malformed) { continue; }
                Receipt receipt=pending.get(id);
                if(receipt!=null && receipt.socket==socket && pending.remove(id,receipt))
                    receipt.complete(reply,null,clock.now());
            } catch(SocketTimeoutException idle) { /* Receiver stays alive. */ }
            catch(Exception failure) {
                synchronized(this) { if(current==socket) current=null; }
                socket.close();fail(socket,failure);return;
            }
        }
    }
    private void fail(DatagramSocket socket,Exception failure) {
        for(Receipt receipt:pending.values())
            if(receipt.socket==socket && pending.remove(receipt.id,receipt)) receipt.complete(null,failure,clock.now());
    }
    synchronized void close() {
        DatagramSocket socket=current;current=null;
        if(socket!=null) { socket.close();fail(socket,new SocketException("Endpoint closed")); }
    }
}
