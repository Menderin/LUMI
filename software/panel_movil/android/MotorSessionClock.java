package cl.lumi.panel;

/** Pure Java clock/session logic; tested without an Android device. */
final class MotorSessionClock {
    private long boot, epoch, seq, remoteSeq, uptime, received, remoteAtReceipt, rtt;
    private boolean ready;

    synchronized int update(long nextBoot, long nextEpoch, long nextSeq, long nextUptime,
                                long requestStarted, long responseReceived) throws Exception {
        for (long value : new long[]{nextBoot, nextEpoch, nextSeq, nextUptime})
            if (value < 0 || value > 0xffffffffL) throw new Exception("Estado inválido");
        if (responseReceived < requestStarted) throw new Exception("Reloj local inválido");
        boolean reboot = ready && boot != nextBoot;
        // A GET can arrive after a newer command ACK. Never roll session state back.
        if (ready && !reboot && (nextUptime < uptime || nextSeq < remoteSeq || nextEpoch < epoch))
            return -1;
        if (!ready || reboot) seq = nextSeq;
        else seq = Math.max(seq, nextSeq);
        boot = nextBoot; epoch = nextEpoch; remoteSeq = nextSeq; uptime = nextUptime;
        received = responseReceived; rtt = responseReceived - requestStarted;
        remoteAtReceipt = nextUptime + rtt / 2;
        ready = true;
        return reboot ? 1 : 0;
    }

    synchronized long[] command(long now) throws Exception {
        long age = now - received;
        if (!ready || age < 0 || age >= 500) throw new Exception("Sin estado vigente");
        if (rtt >= 250) throw new Exception("Wi-Fi lento: estado tardó " + rtt + " ms; vuelve a conectar");
        if (seq >= 0xffffffffL) throw new Exception("Secuencia agotada");
        ++seq;
        return new long[]{boot, epoch, seq, (remoteAtReceipt + age + 180) & 0xffffffffL};
    }

    synchronized void clear() { ready = false; }
}
