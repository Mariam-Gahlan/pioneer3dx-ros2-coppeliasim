#!/usr/bin/env python3
"""
teleop_node.py  -  Keyboard teleoperation for the Pioneer 3-DX in CoppeliaSim.

Reads single key presses from the terminal (non-blocking, no extra libraries:
uses the standard `termios`/`tty`/`select` modules) and publishes
geometry_msgs/msg/Twist messages on /cmd_vel.

Keys
----
    w : forward            s : backward
    a : turn left          d : turn right
    q : forward + left     e : forward + right
    SPACE : STOP (zero-velocity Twist)
    + / - : increase / decrease speed by 10 %
    Ctrl-C : quit (a final STOP is published)
"""

import select
import sys
import termios
import tty

from geometry_msgs.msg import Twist
import rclpy
from rclpy.node import Node

HELP = """
---------------------------------------------
 Pioneer 3-DX keyboard teleop  (topic /cmd_vel)
---------------------------------------------
        q    w    e
        a  SPACE  d
             s
 w/s : forward / backward
 a/d : rotate left / right
 q/e : curve forward-left / forward-right
 SPACE : stop      + / - : speed up / down
 Ctrl-C : quit
---------------------------------------------
"""

# key -> (linear direction, angular direction)
KEY_BINDINGS = {
    'w': (1.0, 0.0),
    's': (-1.0, 0.0),
    'a': (0.0, 1.0),    # positive angular.z = counter-clockwise = left
    'd': (0.0, -1.0),
    'q': (1.0, 1.0),
    'e': (1.0, -1.0),
    ' ': (0.0, 0.0),    # stop
}


class TeleopNode(Node):
    def __init__(self):
        super().__init__('teleop_node')

        # Parameters (can be changed with --ros-args -p linear_speed:=0.5)
        self.declare_parameter('linear_speed', 0.3)    # m/s
        self.declare_parameter('angular_speed', 0.8)   # rad/s
        self.declare_parameter('publish_rate', 10.0)   # Hz
        self.linear_speed = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value
        rate = self.get_parameter('publish_rate').value

        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)

        # Current command, re-published at a fixed rate so the robot keeps
        # moving until another key (or SPACE) changes it.
        self.lin_dir = 0.0
        self.ang_dir = 0.0
        self.period = 1.0 / rate

    def make_twist(self):
        msg = Twist()
        msg.linear.x = self.lin_dir * self.linear_speed
        msg.angular.z = self.ang_dir * self.angular_speed
        return msg

    def publish_current(self):
        self.publisher_.publish(self.make_twist())

    def handle_key(self, key):
        """Update the current command from one key press. Returns False to quit."""
        if key == '\x03':                      # Ctrl-C in raw mode
            return False
        if key in KEY_BINDINGS:
            self.lin_dir, self.ang_dir = KEY_BINDINGS[key]
        elif key == '+':
            self.linear_speed *= 1.1
            self.angular_speed *= 1.1
        elif key == '-':
            self.linear_speed *= 0.9
            self.angular_speed *= 0.9
        else:
            return True                        # ignore unknown keys

        t = self.make_twist()
        print(f'\rkey={key!r:5} linear.x={t.linear.x:+.2f} m/s   '
              f'angular.z={t.angular.z:+.2f} rad/s      ', end='', flush=True)
        return True


def get_key(timeout):
    """Return one character if a key was pressed within `timeout` s, else ''."""
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    return sys.stdin.read(1) if ready else ''


def main(args=None):
    rclpy.init(args=args)
    node = TeleopNode()

    # Save terminal settings and switch to raw mode (one char at a time, no Enter).
    old_settings = termios.tcgetattr(sys.stdin)
    print(HELP)
    try:
        tty.setraw(sys.stdin.fileno())
        running = True
        while running and rclpy.ok():
            key = get_key(node.period)        # waits at most one publish period
            if key:
                running = node.handle_key(key)
            node.publish_current()
    except KeyboardInterrupt:
        pass
    finally:
        # Always stop the robot and restore the terminal.
        node.lin_dir = node.ang_dir = 0.0
        node.publish_current()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        print('\nStopped. Bye!')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
