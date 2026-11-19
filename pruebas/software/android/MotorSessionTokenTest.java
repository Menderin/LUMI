package cl.lumi.panel;
public final class MotorSessionTokenTest {
    static void check(boolean value) { if (!value) throw new AssertionError(); }
    static void blocked(MotorSessionToken s,long now) throws Exception {
        try { s.command(now); throw new AssertionError("Expected rejection"); }
        catch (Exception expected) { }
    }
    public static void main(String[] args) throws Exception {
        MotorSessionToken s=new MotorSessionToken();
        blocked(s,0);
        check(s.update(42,1,0,50000,123,5)==0);
        long[] cmd=s.command(20);
        check(cmd[0]==42 && cmd[1]==1 && cmd[2]==1 && cmd[3]==123);
        // Neither ESP uptime nor network RTT is converted into a deadline.
        check(s.update(42,1,1,50100,124,110)==0);
        check(s.command(215)[3]==124);
        check(s.update(42,1,0,50050,123,220)==-1);
        check(s.command(230)[2]==3);
        check(s.update(42,2,3,50200,125,240)==0);
        check(s.command(250)[1]==2);
        blocked(s,740);
        check(s.update(99,1,0,10,900,800)==1);
        check(s.command(801)[2]==1);
        s.clear(); blocked(s,802);
        check(s.update(99,1,0,0xfffffff0L,901,900)==0);
        check(s.update(99,1,0,15,902,920)==0);
        check(s.command(921)[3]==902);
        System.out.println("PASS token session: freshness, ordering, sequence, epoch, reboot, clear, uptime wrap");
    }
}
