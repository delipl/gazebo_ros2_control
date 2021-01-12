# Copyright 2020 ROS2-Control Development Team (2020)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

import xacro
import yaml


def load_file(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    try:
        with open(absolute_file_path, 'r') as file:
            return file.read()
    except EnvironmentError:
        # parent of IOError, OSError *and* WindowsError where available
        return None


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)
    try:
        with open(absolute_file_path, 'r') as file:
            return yaml.safe_load(file)
    except EnvironmentError:
        # parent of IOError, OSError *and* WindowsError where available
        return None


def generate_launch_description():
    # moveit_cpp.yaml is passed by filename for now since it's node specific
    moveit_cpp_yaml_file_name = get_package_share_directory('rrbot_moveit_config') + '/config/moveit_cpp.yaml'
    gazebo = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('gazebo_ros'), 'launch'), '/gazebo.launch.py']),
             )

    robot_description_config = load_file('rrbot_description', 'urdf/rrbot.urdf')
    robot_description = {'robot_description': robot_description_config}

    robot_description_semantic_config = load_file('rrbot_moveit_config', 'config/rrbot.srdf')
    robot_description_semantic = {'robot_description_semantic': robot_description_semantic_config}

    kinematics_yaml = load_yaml('rrbot_moveit_config', 'config/kinematics.yaml')

    controllers_yaml = load_yaml('rrbot_moveit_config', 'config/ros_controllers.yaml')
    moveit_controllers = {'moveit_simple_controller_manager': controllers_yaml,
                          'moveit_controller_manager':
                          'moveit_simple_controller_manager/MoveItSimpleControllerManager'
                          }

    ompl_planning_pipeline_config = {'ompl': {
        'planning_plugin': 'ompl_interface/OMPLPlanner',
        'request_adapters': """default_planner_request_adapters/AddTimeOptimalParameterization default_planner_request_adapters/FixWorkspaceBounds default_planner_request_adapters/FixStartStateBounds default_planner_request_adapters/FixStartStateCollision default_planner_request_adapters/FixStartStatePathConstraints""" ,
        'start_state_max_bounds_error': 0.1}}
    ompl_planning_yaml = load_yaml('rrbot_moveit_config', 'config/ompl_planning.yaml')
    ompl_planning_pipeline_config['ompl'].update(ompl_planning_yaml)

    # MoveItCpp demo executable
    run_moveit_cpp_node = Node(name='run_moveit_cpp',
                               package='run_moveit_cpp',
                               # TODO(henningkayser): add debug argument
                               # prefix='xterm -e gdb --args',
                               executable='run_moveit_cpp',
                               output='screen',
                               parameters=[moveit_cpp_yaml_file_name,
                                           robot_description,
                                           robot_description_semantic,
                                           kinematics_yaml,
                                           ompl_planning_pipeline_config,
                                           moveit_controllers])

    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )

    spawn_entity = Node(package='gazebo_ros', executable='spawn_entity.py',
                        arguments=['-topic', 'robot_description',
                                   '-entity', 'rrbot'],
                        output='screen')

    # RViz
    rviz_config_file = get_package_share_directory('rrbot_moveit_config') + '/config/rviz_rrbot.rviz'
    rviz_node = Node(package='rviz2',
                     executable='rviz2',
                     name='rviz2',
                     output='log',
                     arguments=['-d', rviz_config_file],
                     parameters=[robot_description,
                                 robot_description_semantic])
    # Static TF
    static_tf = Node(package='tf2_ros',
                     executable='static_transform_publisher',
                     name='static_transform_publisher',
                     output='log',
                     arguments=['0.0', '0.0', '0.0', '0.0', '0.0', '0.0', 'world', 'single_rrbot_link1'])

    return LaunchDescription([
      gazebo,
      node_robot_state_publisher,
      run_moveit_cpp_node,
      rviz_node,
      static_tf,
      spawn_entity
    ])
