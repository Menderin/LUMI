package cl.lumi.panel;

/** Tickets are opaque: Android never estimates the ESP clock. */
final class MotorSessionToken {
    private long boot, epoch, seq, remoteSeq, uptime, received, ticket;
    private boolean ready;
    synchronized int update(long nextBoot, long nextEpoch, long nextSeq, long nextUptime,
                            long nextTicket, long responseReceived) throws Exception {
        for (long value : new long[]{nextBoot,nextEpoch,nextSeq,nextUptime,nextTicket})
            if (value < 0 || value > 0xffffffffL) throw new Exception("Estado inválido");
        boolean reboot = ready && boot != nextBoot;
        // GET may complete after a newer datagram ACK; do not roll the session back.
        // Unsigned modular uptime comparison also supports the ESP's 49-day wrap.
        long delta = (nextUptime - uptime) & 0xffffffffL;
        if (ready && !reboot && (delta >= 0x80000000L || nextSeq < remoteSeq || nextEpoch < epoch))
            return -1;
        if (!ready || reboot) seq = nextSeq;
        else seq = Math.max(seq,nextSeq);
        boot=nextBoot; epoch=nextEpoch; remoteSeq=nextSeq; uptime=nextUptime;
        ticket=nextTicket; received=responseReceived; ready=true;
        return reboot ? 1 : 0;
    }
    synchronized long[] command(long now) throws Exception {
        if (!ready || now < received || now-received >= 500)
            throw new Exception("Sin estado vigente; vuelve a habilitar");
        if (seq >= 0xffffffffL) throw new Exception("Secuencia agotada");
        return new long[]{boot,epoch,++seq,ticket};
    }
    synchronized boolean needsRefresh(long now) { return !ready || now-received >= 100; }
    synchronized void clear() { ready=false; }
}
