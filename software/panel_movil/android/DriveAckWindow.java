package cl.lumi.panel;
import java.util.LinkedHashMap;
import java.util.Iterator;
import java.util.Map;

/** Bounded outstanding heartbeats; never authorizes arming or changes ESP watchdog. */
final class DriveAckWindow {
    static final int WAIT_MS=45, SILENCE_MS=200, MAX_MISSES=4;
    private final LinkedHashMap<Long,Long> pending=new LinkedHashMap<>();
    private long confirmedAt=-1,lastLatency,lastStarted;
    private int misses;
    void reset() { pending.clear();confirmedAt=-1;misses=0; }
    void sent(long request,long now) throws java.io.IOException {
        if(confirmedAt>=0 && now-confirmedAt>=SILENCE_MS)
            throw new java.io.IOException("Enlace sin confirmaciones durante 200 ms; requiere nuevo rearme");
        if(confirmedAt<0) confirmedAt=now;
        pending.put(request,now);
        while(pending.size()>8) pending.remove(pending.keySet().iterator().next());
    }
    boolean acknowledge(long request,long now) {
        if(confirmedAt>=0 && now-confirmedAt>=SILENCE_MS) return false;
        Long sent=pending.remove(request);
        if(sent==null || now<sent || now-sent>=SILENCE_MS) return false;
        // Do not treat an older ACK as newer than the last confirmed command.
        for(Iterator<Map.Entry<Long,Long>> it=pending.entrySet().iterator();it.hasNext();)
            if(it.next().getKey()<request) it.remove();
        confirmedAt=now;lastLatency=now-sent;lastStarted=sent;misses=0;return true;
    }
    boolean missed(long now) { ++misses;return misses<MAX_MISSES && now-confirmedAt<SILENCE_MS; }
    int misses() { return misses; }
    long latency() { return lastLatency; }
    long started() { return lastStarted; }
    int waitBudget(long now) { return (int)Math.max(1,Math.min(WAIT_MS,SILENCE_MS-(now-confirmedAt))); }
}
