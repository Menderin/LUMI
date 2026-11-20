package cl.lumi.panel;
import java.util.concurrent.*;

/** Periodic source, independent from UI and from waiting for acknowledgement. */
final class MotionHeartbeat {
    static final long ACK_WARNING_MS=200, ACK_FAILURE_MS=500;
    static final class PulseEnded extends Exception { PulseEnded() { super("Pulso máximo finalizado"); } }
    interface Sender { void send(long run) throws Exception; }
    interface Failure { void failed(long run,Exception error); }
    private static final class Run {
        final long id,started,maxMs;long ackAt,lastAcknowledgedSend=-1;ScheduledFuture<?> timer;
        Run(long id,long now,long maxMs) { this.id=id;started=ackAt=now;this.maxMs=maxMs; }
    }
    private final MonoClock clock;
    private final ScheduledExecutorService timer=Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t=new Thread(r,"lumi-command-clock");t.setDaemon(true);return t;
    });
    private Run current;
    private long generation;
    MotionHeartbeat(MonoClock clock) { this.clock=clock; }
    synchronized long start(long maxMs,Sender sender,Failure failure) {
        stop();Run run=new Run(++generation,clock.now(),maxMs);current=run;
        run.timer=timer.scheduleWithFixedDelay(() -> tick(run,sender,failure),0,50,TimeUnit.MILLISECONDS);
        return run.id;
    }
    private void tick(Run run,Sender sender,Failure failure) {
        Exception reason=null;
        synchronized(this) {
            if(current!=run) return;
            long now=clock.now();
            if(now-run.started>=run.maxMs) reason=new PulseEnded();
            else if(now-run.ackAt>=ACK_FAILURE_MS) reason=new java.io.IOException("Sin confirmaciones durante 500 ms; mando detenido, canal de datos abierto");
        }
        if(reason==null) { try { sender.send(run.id); } catch(Exception error) { reason=error; } }
        if(reason!=null) {
            synchronized(this) { if(current!=run) return;stop(); }
            failure.failed(run.id,reason);
        }
    }
    synchronized boolean confirm(long run,long sentAt) {
        long now=clock.now();
        if(current==null || current.id!=run || now-current.ackAt>=ACK_FAILURE_MS ||
            sentAt<current.started || sentAt<=current.lastAcknowledgedSend || now-sentAt>=ACK_FAILURE_MS) return false;
        current.lastAcknowledgedSend=sentAt;
        current.ackAt=now;
        return true;
    }
    synchronized boolean running() { return current!=null; }
    synchronized boolean delayed(long run) { return current!=null && current.id==run && clock.now()-current.ackAt>=ACK_WARNING_MS; }
    synchronized void stop() { if(current!=null) { current.timer.cancel(false);current=null; } }
    synchronized void close() { stop();timer.shutdownNow(); }
}
