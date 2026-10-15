# pioneer_control
Keyboard teleoperation of a **Pioneer 3-DX** in **CoppeliaSim** through **ROS 2 Jazzy**, with a
real-time Matplotlib bar graph of the robot's 16 ultrasonic sensors.

```
teleop_node ──/cmd_vel (geometry_msgs/Twist)──▶ CoppeliaSim (Lua script + simROS2)
                                                      │
sensor_viz_node ◀──/ultrasonic_sensors (std_msgs/Float32MultiArray, 16 values)──┘
```

| Component | Role | Topic / Type |
|---|---|---|
| `teleop_node` | Reads the keyboard, publishes velocity commands | pub `/cmd_vel` — `geometry_msgs/msg/Twist` |
| CoppeliaSim script (`coppeliasim/pioneer_ros2.lua`) | Drives the wheels, reads the 16 sonars | sub `/cmd_vel`, pub `/ultrasonic_sensors` — `std_msgs/msg/Float32MultiArray` |
| `sensor_viz_node` | Live bar graph of the 16 distances | sub `/ultrasonic_sensors` |

Notes:
- A reading of **1.0 m means "nothing detected"** (the sensors' maximum range).
- The simulator **stops the robot if no `/cmd_vel` arrives for 0.5 s** (safety timeout).
  The teleop node publishes continuously at ~10 Hz, so this only triggers when it is closed.

## Package layout

```
pioneer_control/
├── README.md
├── package.xml
├── setup.py / setup.cfg
├── resource/pioneer_control
├── coppeliasim/pioneer_ros2.lua      # robot script to paste into CoppeliaSim
├── scenes/                           # saved CoppeliaSim scene (pioneer_scene.ttt)
└── pioneer_control/
    ├── __init__.py
    ├── teleop_node.py
    └── sensor_viz_node.py
```

## 1. Requirements

- Ubuntu with **ROS 2 Jazzy** installed in `/opt/ros/jazzy`
- **CoppeliaSim EDU** with the **simROS2** plugin
- Python packages and build tools:

```bash
sudo apt update
sudo apt install -y python3-matplotlib python3-numpy python3-tk python3-colcon-common-extensions
```

## 2. Build

```bash
mkdir -p ~/ros2_ws/src
cp -r pioneer_control ~/ros2_ws/src/        # or unzip the submission into ~/ros2_ws/src
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select pioneer_control --symlink-install
source install/setup.bash
ros2 pkg executables pioneer_control
```

Expected output of the last command:

```
pioneer_control sensor_viz_node
pioneer_control teleop_node
```

> Every new terminal needs `source ~/ros2_ws/install/setup.bash`, otherwise
> `Package 'pioneer_control' not found`.

## 3. Prepare the CoppeliaSim scene

**Option A — use the saved scene:** open `scenes/pioneer_scene.ttt` (File → Open scene…).

**Option B — build it yourself:**

1. Start CoppeliaSim **from a terminal where ROS 2 is sourced** (needed for simROS2):
   ```bash
   source /opt/ros/jazzy/setup.bash
   cd ~/CoppeliaSim_Edu_*        # your CoppeliaSim folder
   ./coppeliaSim.sh
   ```
2. Model browser → `robots/mobile` → drag **Pioneer p3dx** into the scene.
3. Add walls / cuboids around the robot (Model browser → `infrastructure/walls`, or
   Add → Primitive shape → Cuboid). In each object's properties make sure it is **Detectable**
   (and **Static** so the robot can't push it).
4. Double-click the robot's **script icon**, delete its contents, and paste
   `coppeliasim/pioneer_ros2.lua`.
   The script expects the robot to be named `PioneerP3DX` with children `leftMotor`,
   `rightMotor` and `ultrasonicSensor` (×16) — adjust the paths if your names differ.
5. Save the scene (File → Save scene as…).

## 4. Run (4 terminals)

**Terminal 1 — simulator**
```bash
source /opt/ros/jazzy/setup.bash
cd ~/CoppeliaSim_Edu_* && ./coppeliaSim.sh
```
Open the scene and press **▶ Play**.

**Terminal 2 — check the topics**
```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list                             # /cmd_vel and /ultrasonic_sensors must appear
ros2 topic echo /ultrasonic_sensors --once  # 16 numbers
```

**Terminal 3 — visualization**
```bash
source ~/ros2_ws/install/setup.bash
ros2 run pioneer_control sensor_viz_node
```
A window opens with 16 bars: green (> 0.6 m), orange (0.3–0.6 m), red (< 0.3 m).
Close the window or press Ctrl-C to quit.

**Terminal 4 — teleoperation** (click inside this terminal before pressing keys)
```bash
source ~/ros2_ws/install/setup.bash
ros2 run pioneer_control teleop_node
```

Start order: simulator (playing) → visualization → teleoperation.

## 5. Controls

| Key | Action |
|---|---|
| `w` / `s` | forward / backward |
| `a` / `d` | rotate left / right |
| `q` / `e` | forward + turn left / right |
| `space` | stop |
| `+` / `-` | speed up / slow down |
| `x` or Ctrl-C | quit (robot is stopped) |

Default speeds can be changed with parameters:

```bash
ros2 run pioneer_control teleop_node --ros-args -p linear_speed:=0.5 -p angular_speed:=1.0
```

## 6. Debugging

```bash
ros2 node list
ros2 node info /teleop_node          # Publishers: /cmd_vel
ros2 node info /sensor_viz_node      # Subscribers: /ultrasonic_sensors
ros2 topic hz /ultrasonic_sensors    # ~20 Hz
ros2 topic echo /cmd_vel
# drive without the teleop node (-r 10 keeps publishing, so the 0.5 s timeout doesn't stop it):
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

| Problem | Fix |
|---|---|
| `require('simROS2')` error / no topics | Start CoppeliaSim from a terminal with ROS 2 sourced; press ▶ Play. |
| `object does not exist` in the Lua script | Robot/children named differently — fix the paths in the script. |
| Robot ignores keys | Click the teleop terminal so it has keyboard focus. |
| All bars stay at 1.0 | Obstacles not **Detectable**, or farther than 1 m. |
| Plot window never appears | `sudo apt install python3-tk`; on Wayland try `export MPLBACKEND=TkAgg`. |
| Terminal acts strangely after a crash | Type `reset` and press Enter. |


   **Demo video:**
   https://youtu.be/-KO93iTG9uo 

