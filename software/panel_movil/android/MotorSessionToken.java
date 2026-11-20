package cl.lumi.panel;

/** Opaque ESP tickets. RTT is an upper bound on age at receipt, not a clock estimate. */
final class MotorSessionToken {
    static final long MOTION_BUDGET_MS=200; // 250 ms on ESP minus 50 ms delivery reserve.
    static final class NeedsRefresh extends Exception {
        NeedsRefresh() { super("Token sin margen de vigencia; solicitando estado fresco"); }
    }
    private long boot,epoch,seq,remoteSeq,uptime,received,ticket,ageAtReceipt,requestFloor;
    private boolean ready,motionLease;
    private long motionBoot,motionEpoch,motionTicket;
    synchronized int update(long nextBoot,long nextEpoch,long nextSeq,long nextUptime,
                            long nextTicket,long requestStarted,long responseReceived) throws Exception {
        for(long value:new long[]{nextBoot,nextEpoch,nextSeq,nextUptime,nextTicket})
            if(value<0 || value>0xffffffffL) throw new Exception("Estado inválido");
        if(responseReceived<requestStarted) throw new Exception("Tiempo de respuesta inválido");
        boolean reboot=ready && boot!=nextBoot;
        if(reboot && requestStarted<requestFloor) return -1;
        long delta=(nextUptime-uptime)&0xffffffffL;
        if(ready && !reboot && (delta>=0x80000000L || nextSeq<remoteSeq || nextEpoch<epoch)) return -1;
        requestFloor=!ready || reboot ? requestStarted : Math.max(requestFloor,requestStarted);
        if(reboot || (ready && nextEpoch!=epoch)) motionLease=false;
        seq=!ready || reboot ? nextSeq : Math.max(seq,nextSeq);
        boot=nextBoot;epoch=nextEpoch;remoteSeq=nextSeq;uptime=nextUptime;
        ticket=nextTicket;received=responseReceived;ageAtReceipt=responseReceived-requestStarted;ready=true;
        return reboot?1:0;
    }
    private long age(long now) { return !ready || now<received ? Long.MAX_VALUE : ageAtReceipt+now-received; }
    synchronized long[] command(long now,boolean motion) throws Exception {
        if(age(now)>=(motion?MOTION_BUDGET_MS:900)) throw new NeedsRefresh();
        if(seq>=0xffffffffL) throw new Exception("Secuencia agotada");
        return new long[]{boot,epoch,++seq,ticket};
    }
    synchronized void beginMotion(long now) throws Exception {
        if(age(now)>=MOTION_BUDGET_MS) throw new NeedsRefresh();
        motionBoot=boot;motionEpoch=epoch;motionTicket=ticket;motionLease=true;
    }
    synchronized long[] motionCommand() throws Exception {
        if(!ready || !motionLease || motionBoot!=boot || motionEpoch!=epoch)
            throw new Exception("Permiso del gesto finalizado; requiere nueva habilitación");
        if(seq>=0xffffffffL) throw new Exception("Secuencia agotada");
        return new long[]{motionBoot,motionEpoch,++seq,motionTicket};
    }
    synchronized void endMotion() { motionLease=false; }
    synchronized long[] identity() throws Exception {
        if(!ready) throw new Exception("Sin sesión; esperando recuperar datos");
        return new long[]{boot,epoch};
    }
    synchronized boolean needsRefresh(long now) { return age(now)>=100; }
    synchronized void clear() { ready=false;motionLease=false; }
}
