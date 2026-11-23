package cl.lumi.panel;

public final class VideoFrameFlowTest {
    static void check(boolean value,String message){if(!value)throw new AssertionError(message);}
    public static void main(String[] args)throws Exception{
        check(VideoFrameStats.waitMillis(1000,1033,true)==67,"Espera debe descontar trabajo");
        check(VideoFrameStats.waitMillis(1000,1140,true)==0,"No agregar espera si ya tarda mas de100ms");
        check(VideoFrameStats.waitMillis(1000,1033,false)==467,"Reintento con espera tras fallo");
        VideoFrameStats stats=new VideoFrameStats();
        for(int i=0;i<21;i++){
            stats.record("frame"+i,i*100);
            stats.record("frame"+i,i*100+20); // Redibujar la misma imagen no suma FPS.
        }
        check(Math.abs(stats.fps(2000)-10)<.001,"Debe medir10FPS unicos");
        check(stats.fps(5000)==0,"No conservar FPS si cesa el video");
        stats.reset();stats.record("nuevo",5000);check(stats.fps(5000)==0,"Primer frame sin FPS inventados");
        LatestFrameSlot<Integer> slot=new LatestFrameSlot<>();
        check(slot.offer(1),"Primera imagen solicita UI");
        for(int i=2;i<=100;i++)check(!slot.offer(i),"No acumular callbacks");
        check(slot.take()==100,"Consumir la mas reciente");
        check(slot.offer(101),"Siguiente imagen solicita UI otra vez");
        check(slot.take()==101,"No perder siguiente imagen");
        check(slot.take()==null,"Sin duplicar entregas");
        System.out.println("VideoFrameFlow: OK (ritmo10FPS, cuadros unicos, entrega del mas reciente)");
    }
}
