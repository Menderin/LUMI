package cl.lumi.panel;
import java.util.Arrays;
/** Read-only probe metrics; thresholds reserve room below the ESP 250 ms watchdog. */
final class LinkProbeStats {
    private final long[] rtts=new long[20];
    private int samples, failures;
    private long previousUptime=-1, maxGap;
    void add(long rtt,long uptime) {
        if(rtt<0 || samples>=rtts.length) throw new IllegalArgumentException();
        rtts[samples++]=rtt;
        if(previousUptime>=0) maxGap=Math.max(maxGap,(uptime-previousUptime)&0xffffffffL);
        previousUptime=uptime;
    }
    void fail() { ++failures;previousUptime=-1; }
    private long percentile(double q) {
        if(samples==0) return -1;
        long[] ordered=Arrays.copyOf(rtts,samples);Arrays.sort(ordered);
        return ordered[(int)Math.ceil(q*samples)-1];
    }
    boolean acceptable() { return samples>=12 && failures==0 && percentile(.95)<120 && maxGap<200; }
    String summary() {
        return samples+" respuestas · "+failures+" sin respuesta\nRTT p50/p95/máx: "+percentile(.5)+" / "+percentile(.95)+" / "+percentile(1)+
            " ms\nIntervalo máx. recibido por ESP: "+maxGap+" ms\n"+
            (acceptable()?"Enlace apto para probar el mando":"Enlace irregular: no probar motores");
    }
}
