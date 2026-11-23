package cl.lumi.panel;

/** Un solo envio UI pendiente. Nuevos resultados reemplazan al anterior. */
final class LatestFrameSlot<T> {
    private T value;
    private boolean posted;
    synchronized boolean offer(T next){
        value=next;
        if(posted)return false;
        posted=true;return true;
    }
    synchronized T take(){
        T next=value;value=null;posted=false;return next;
    }
}
