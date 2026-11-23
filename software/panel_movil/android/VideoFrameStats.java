package cl.lumi.panel;

import java.util.ArrayDeque;

/** Cuenta fotogramas distintos realmente dibujados; reloj monotonico del movil. */
final class VideoFrameStats {
    private final ArrayDeque<Long> drawn=new ArrayDeque<>();
    private String lastId;
    static long waitMillis(long start,long end,boolean success){
        return Math.max(0,(success?100:500)-Math.max(0,end-start));
    }
    void reset(){drawn.clear();lastId=null;}
    void record(String frameId,long now){
        trim(now);
        if(frameId==null||frameId.equals(lastId))return;
        lastId=frameId;drawn.addLast(now);
    }
    double fps(long now){
        trim(now);
        if(drawn.size()<2)return 0;
        long elapsed=drawn.getLast()-drawn.getFirst();
        return elapsed>0?(drawn.size()-1)*1000d/elapsed:0;
    }
    private void trim(long now){
        while(!drawn.isEmpty() && now-drawn.getFirst()>2000)drawn.removeFirst();
    }
}
