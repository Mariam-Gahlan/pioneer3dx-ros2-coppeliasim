#!/usr/bin/env python3
"""
Real-time bar graph of the Pioneer 3-DX's 16 ultrasonic sensors.

Listens to /ultrasonic_sensors (std_msgs/Float32MultiArray) and, as a fallback,
to /ultrasonic/s0 ... /ultrasonic/s15 (std_msgs/Float32 each).
"""
import matplotlib.pyplot as plt
import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Float32MultiArray

NUM_SENSORS = 16


class SensorVizNode(Node):
    def __init__(self):
        super().__init__('sensor_viz_node')
        self.declare_parameter('topic', '/ultrasonic_sensors')
        self.declare_parameter('max_range', 1.0)
        self.declare_parameter('warn_distance', 0.3)
        topic = self.get_parameter('topic').value
        self.max_range = self.get_parameter('max_range').value
        self.warn_distance = self.get_parameter('warn_distance').value
        self.readings = np.full(NUM_SENSORS, self.max_range)
        self.new_data = False
        self.msg_count = 0
        self.subscription = self.create_subscription(
            Float32MultiArray, topic, self.sensor_callback, 10)
        self.single_subs = [
            self.create_subscription(Float32, f'/ultrasonic/s{i}',
                                     lambda msg, i=i: self.single_callback(i, msg), 10)
            for i in range(NUM_SENSORS)]
        self.get_logger().info(f'Listening on {topic} (and /ultrasonic/s0..s15) ...')
        self.setup_plot()

    def sensor_callback(self, msg):
        data = np.asarray(msg.data, dtype=float)
        if data.size != NUM_SENSORS:
            return
        self.readings = np.clip(data, 0.0, self.max_range)
        self.new_data = True
        self.msg_count += 1

    def single_callback(self, index, msg):
        self.readings[index] = min(max(float(msg.data), 0.0), self.max_range)
        self.new_data = True
        if index == NUM_SENSORS - 1:
            self.msg_count += 1

    def setup_plot(self):
        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.fig.canvas.manager.set_window_title('Pioneer 3-DX ultrasonic sensors')
        idx = np.arange(NUM_SENSORS)
        self.bars = self.ax.bar(idx, self.readings, color='tab:blue', edgecolor='black')
        self.ax.set_xticks(idx)
        self.ax.set_xticklabels([f'S{i}' for i in idx])
        self.ax.set_ylim(0, self.max_range * 1.25)
        self.ax.set_xlabel('Sensor index (S0-S7 front, S8-S15 rear)')
        self.ax.set_ylabel('Distance [m]')
        self.ax.axhline(self.warn_distance, color='red', linestyle='--', linewidth=1,
                        label=f'warning ({self.warn_distance:.2f} m)')
        self.ax.legend(loc='upper left')
        self.title = self.ax.set_title('Waiting for data...')
        self.texts = [self.ax.text(i, 0, '', ha='center', va='bottom', fontsize=8) for i in idx]
        self.fig.tight_layout()
        plt.show(block=False)

    def update_plot(self):
        for i, (bar, value) in enumerate(zip(self.bars, self.readings)):
            bar.set_height(value)
            if value < self.warn_distance:
                bar.set_color('tab:red')
            elif value < self.max_range:
                bar.set_color('tab:orange')
            else:
                bar.set_color('tab:blue')
            bar.set_edgecolor('black')
            self.texts[i].set_position((i, value))
            self.texts[i].set_text(f'{value:.2f}')
        self.title.set_text(f'Ultrasonic distances  (messages received: {self.msg_count})')
        self.fig.canvas.draw_idle()


def main(args=None):
    rclpy.init(args=args)
    node = SensorVizNode()
    try:
        while rclpy.ok() and plt.fignum_exists(node.fig.number):
            for _ in range(50):
                rclpy.spin_once(node, timeout_sec=0.0)
            if node.new_data:
                node.update_plot()
                node.new_data = False
            plt.pause(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        plt.close('all')
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
