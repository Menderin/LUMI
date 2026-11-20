package cl.lumi.panel;
public final class MotorSessionTokenTest {
    static void check(boolean value) { if(!value) throw new AssertionError(); }
    static void blocked(MotorSessionToken s,long now) throws Exception {
        try { s.command(now,true);throw new AssertionError("Stale token authorized motion"); }
        catch(MotorSessionToken.NeedsRefresh expected) { }
    }
    public static void main(String[] args) throws Exception {
        MotorSessionToken s=new MotorSessionToken();blocked(s,0);
        check(s.update(42,1,0,50000,123,0,5)==0);
        long[] cmd=s.command(20,true);
        check(cmd[0]==42 && cmd[1]==1 && cmd[2]==1 && cmd[3]==123);
        // The server's clock scale/origin never enters ticket freshness calculations.
        check(s.update(42,1,1,50100,124,100,110)==0);
        check(s.command(150,true)[3]==124);
        check(s.update(42,1,0,50050,123,90,160)==-1);
        check(s.command(170,true)[2]==3);
        check(s.update(42,2,3,50200,125,180,185)==0);
        check(s.command(190,true)[1]==2);
        blocked(s,380); // 5 ms transit + 195 ms since receipt consumes budget.
        check(s.update(99,1,0,10,900,790,800)==1);
        check(s.update(42,2,4,50210,126,780,801)==-1);
        check(s.command(801,true)[2]==1);
        s.clear();blocked(s,802);
        try { s.identity();throw new AssertionError("Missing session accepted"); } catch(Exception expected) { }
        check(s.update(99,1,0,0xfffffff0L,901,890,900)==0);
        check(s.update(99,1,0,15,902,910,920)==0);
        check(s.command(921,true)[3]==902);
        // Regression: a reply from a previous request is not a new 250 ms lease.
        MotorSessionToken late=new MotorSessionToken();
        late.update(5,1,0,900,11,0,180);
        check(late.needsRefresh(180));
        blocked(late,210); // Old code allowed this because receipt was only 30 ms ago.
        check(late.command(210,false)[3]==11); // Arming uses its distinct, larger ticket budget.
        late.update(5,1,1,920,12,211,216);
        check(late.command(220,true)[3]==12);
        MotorSessionToken slow=new MotorSessionToken();
        slow.update(5,1,0,900,11,0,250);blocked(slow,250);
        check(slow.needsRefresh(250));
        try { slow.update(5,1,0,901,12,300,299);throw new AssertionError("Negative RTT accepted"); }
        catch(Exception expected) { }
        MotorSessionToken lease=new MotorSessionToken();
        lease.update(7,1,0,100,31,0,5);lease.beginMotion(10);
        check(lease.motionCommand()[3]==31);
        lease.update(7,1,1,500,32,300,305);
        check(lease.motionCommand()[3]==31); // A telemetry ticket cannot replace the live gesture permit.
        lease.endMotion();
        try { lease.motionCommand();throw new AssertionError("Stopped gesture resumed"); } catch(Exception expected) { }
        lease.update(7,2,2,600,33,400,405);lease.beginMotion(410);
        lease.update(7,3,3,700,34,500,505);
        try { lease.motionCommand();throw new AssertionError("Epoch change retained gesture"); } catch(Exception expected) { }
        System.out.println("PASS token freshness and gesture lease: original request time, delayed ACK, RTT budget, refresh, ordering, epoch, reboot, wrap, clear");
    }
}
