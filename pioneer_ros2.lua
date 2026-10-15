--lua
sim = require('sim')
simROS2 = require('simROS2')

-- Pioneer 3-DX ROS 2 interface (CoppeliaSim 4.x, Lua simulation script)
--  in : /cmd_vel  (geometry_msgs/msg/Twist)
--  out: /ultrasonic_sensors (std_msgs/msg/Float32MultiArray, 16 values)
--       or, if this plugin build lacks Float32MultiArray,
--       /ultrasonic/s0 ... /ultrasonic/s15 (std_msgs/msg/Float32 each)

local WHEEL_RADIUS = 0.0975   -- m
local WHEEL_BASE   = 0.331    -- m
local MAX_RANGE    = 1.0      -- m, published when nothing is detected
local CMD_TIMEOUT  = 0.5      -- s, stop if /cmd_vel goes silent

local function findObjects(root, prefix)
    local found = {}
    for _, h in ipairs(sim.getObjectsInTree(root, sim.handle_all, 0)) do
        local alias = sim.getObjectAlias(h, 0)
        if string.sub(alias, 1, #prefix) == prefix then
            table.insert(found, h)
        end
    end
    return found
end

function sysCall_init()
    robot = sim.getObject('..')
    leftMotor  = findObjects(robot, 'leftMotor')[1]
    rightMotor = findObjects(robot, 'rightMotor')[1]
    sensors    = findObjects(robot, 'ultrasonicSensor')
    if not leftMotor or not rightMotor then
        error('Could not find leftMotor/rightMotor inside the robot')
    end
    sim.addLog(sim.verbosity_scriptinfos, 'Found ' .. #sensors .. ' ultrasonic sensors')

    linVel, angVel = 0.0, 0.0
    lastCmdTime = 0

    cmdSub = simROS2.createSubscription('/cmd_vel', 'geometry_msgs/msg/Twist', 'cmdVelCallback')

    -- Try the array message first; fall back to 16 Float32 topics if unsupported
    local ok, pub = pcall(simROS2.createPublisher, '/ultrasonic_sensors', 'std_msgs/msg/Float32MultiArray')
    if ok then
        sonarPub = pub
        sim.addLog(sim.verbosity_scriptinfos, 'Publishing /ultrasonic_sensors (Float32MultiArray)')
    else
        sonarPubs = {}
        for i = 1, #sensors do
            sonarPubs[i] = simROS2.createPublisher('/ultrasonic/s' .. (i - 1), 'std_msgs/msg/Float32')
        end
        sim.addLog(sim.verbosity_scriptinfos, 'Float32MultiArray not supported by this plugin -> publishing /ultrasonic/s0..s15 (Float32)')
    end
    sim.addLog(sim.verbosity_scriptinfos, 'Pioneer ROS 2 interface ready')
end

function cmdVelCallback(msg)
    linVel = msg.linear.x
    angVel = msg.angular.z
    lastCmdTime = sim.getSystemTime()
end

function sysCall_actuation()
    if sim.getSystemTime() - lastCmdTime > CMD_TIMEOUT then
        linVel, angVel = 0.0, 0.0
    end
    local vLeft  = (linVel - angVel * WHEEL_BASE / 2) / WHEEL_RADIUS
    local vRight = (linVel + angVel * WHEEL_BASE / 2) / WHEEL_RADIUS
    sim.setJointTargetVelocity(leftMotor,  vLeft)
    sim.setJointTargetVelocity(rightMotor, vRight)
end

function sysCall_sensing()
    local distances = {}
    for i = 1, #sensors do
        local res, dist = sim.readProximitySensor(sensors[i])
        if res > 0 and dist < MAX_RANGE then
            distances[i] = dist
        else
            distances[i] = MAX_RANGE
        end
    end
    if sonarPub then
        simROS2.publish(sonarPub, {data = distances})
    elseif sonarPubs then
        for i = 1, #sonarPubs do
            simROS2.publish(sonarPubs[i], {data = distances[i]})
        end
    end
end

function sysCall_cleanup()
    if cmdSub then simROS2.shutdownSubscription(cmdSub) end
    if sonarPub then simROS2.shutdownPublisher(sonarPub) end
    if sonarPubs then
        for i = 1, #sonarPubs do simROS2.shutdownPublisher(sonarPubs[i]) end
    end
end
