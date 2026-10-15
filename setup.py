from glob import glob

from setuptools import find_packages, setup

package_name = 'pioneer_control'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml', 'README.md']),
        ('share/' + package_name + '/scenes', glob('scenes/*.ttt')),
        ('share/' + package_name + '/coppeliasim', glob('coppeliasim/*.lua')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Nancy',
    maintainer_email='your.email@example.com',
    description='Keyboard teleoperation and real-time ultrasonic visualization '
                'for a Pioneer 3-DX in CoppeliaSim using ROS 2',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'teleop_node = pioneer_control.teleop_node:main',
            'sensor_viz_node = pioneer_control.sensor_viz_node:main',
        ],
    },
)
