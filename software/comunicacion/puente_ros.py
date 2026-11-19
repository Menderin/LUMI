"""ROS 2 -> USB base. Run after sourcing ROS: python -m software.comunicacion.puente_ros."""
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String
from std_srvs.srv import SetBool
from .protocolo import Link, mix


class BaseBridge(Node):
    def __init__(self):
        super().__init__("lumi_puente_serie")
        self.declare_parameter("port", "/dev/ttyACM0")
        self.declare_parameter("separation_m", 0.0)
        self.declare_parameter("wheel_reference_mps", 0.0)
        self.width = float(self.get_parameter("separation_m").value)
        self.reference = float(self.get_parameter("wheel_reference_mps").value)
        mix(0, 0, self.width, self.reference)  # Refuse invented geometry.
        self.link = Link(self.get_parameter("port").value)
        self.enabled = False
        self.arm_seq = None
        self.command = None
        self.last_stamp = 0
        self.armed_once = False
        self.state_pub = self.create_publisher(String, "/base/estado", 1)
        self.create_subscription(TwistStamped, "/base/cmd_vel", self.velocity, QoSProfile(depth=1))
        self.create_service(SetBool, "/base/habilitar_banco", self.arm)
        self.create_timer(0.05, self.tick)

    def inhibit(self):
        self.enabled = False
        self.arm_seq = None
        self.command = None
        if self.link.fresh():
            self.link.send(0)

    def arm(self, request, response):
        if not request.data:
            self.inhibit()
            response.success, response.message = True, "Parada solicitada"
        elif not self.link.fresh():
            response.success, response.message = False, "Sin feedback vigente"
        else:
            self.command = None
            self.armed_once = False
            self.arm_seq = self.link.send(1)
            self.enabled = True
            response.success, response.message = True, "Rearme solicitado; esperar confirmación en /base/estado"
        return response

    def velocity(self, msg):
        if not self.enabled:
            return
        stamp = msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec
        age = (self.get_clock().now().nanoseconds - stamp) / 1e9
        v, w = msg.twist.linear, msg.twist.angular
        values = (v.x, v.y, v.z, w.x, w.y, w.z)
        if (not all(math.isfinite(x) for x in values) or any((v.y, v.z, w.x, w.y)) or
                stamp <= self.last_stamp or not 0 <= age < 0.15):
            self.inhibit()
            return
        self.last_stamp = stamp
        self.command = (mix(v.x, w.z, self.width, self.reference), time.monotonic(), stamp)

    def tick(self):
        state = self.link.poll()
        if not self.link.fresh():
            self.enabled = False
            self.arm_seq = None
            self.command = None
            return
        import json
        self.state_pub.publish(String(data=json.dumps(state)))
        if not self.enabled:
            return
        if self.arm_seq is not None:
            if state["seq"] < self.arm_seq:
                return
            self.arm_seq = None
            if not state["armed"]:
                self.inhibit()
                return
        if not state["armed"]:
            self.inhibit()
            return
        if self.command is None:
            if self.armed_once:
                self.inhibit()
            else:
                self.link.send(2, 0, 0)
            return
        wheels, received, stamp = self.command
        age = (self.get_clock().now().nanoseconds - stamp) / 1e9
        if time.monotonic() - received >= 0.15 or not 0 <= age < 0.15:
            self.inhibit()
            return
        self.armed_once = True
        self.link.send(2, *wheels)


def main():
    rclpy.init()
    node = None
    try:
        node = BaseBridge()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.link.close()
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
