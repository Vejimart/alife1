"""
Most of this is meant to work without any intervention, so feel free to run the
script, lean back and enjoy the wonders of evolution :D

However, there are a couple of ways to interact with the simulation:

* I grouped together the things that I adjusted most frequently on the
  __innit__ method of the Alife1App class, so I wouldn't have to go search for
  them every time I wanted to change something. Feel free to experiment and
  change those values to see what happens (Not that you can't change anything
  else if you want to :) ).

* During execution, click on  a cat to display a graphical representation of
  it's sensors and print some information about it to console.

* Click on an empty space to stop showing a cat's sensors.

I hope you can get something good out of watching this code, but I think it's
important for you to know that at some point my biggest priority was getting it
finished, not crafting a good and mantainable piece of software.

-March 2021.
"""

import pygame
import pygame.gfxdraw
import math
import random
from evolution import EvolutionOptions, Brain
import activation_functions
import os
import catnames  # I can't believe this library exists... anyway, less work for me xD
import colorsys


# A few helper functions

def get_distance(point1, point2):
    return math.sqrt(((point2[0] - point1[0]) ** 2) + ((point2[1] - point1[1]) ** 2))


def int_to_hms_string(number):
    seconds = number % 60
    number = int(number / 60)
    minutes = number % 60
    number = int(number / 60)
    hours = number
    return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)


# Base object, it contains some common stuff for other objects and will be
# inherited by them

class SimulationBaseObject:
    instances = []

    def __init__(self):
        self.position = [0, 0]
        self.rotation = 0
        self.world_position = [0, 0]
        self.world_rotation = 0
        self.parent = None
        self.children = []
        self.child_depth = 0
        self.draw_enabled = True
        self.tags = []
        self.__class__.instances.append(self)
        self.position_constraints = {
            "min_x": -float("inf"),
            "max_x": float("inf"),
            "min_y": -float("inf"),
            "max_y": float("inf"),
        }

        self.update()

    def set_child_depth(self):
        if self.parent is None:
            self.child_depth = 0
        else:
            self.child_depth = self.parent.child_depth + 1

        for child in self.children:
            child.set_child_depth()

    def set_parent(self, parent):
        if self.parent is not None:
            self.parent.children.remove(self)

        self.parent = parent
        if (self.parent is not None) and (self not in self.parent.children):
            self.parent.children.append(self)

        self.set_child_depth()

        self.update()

        self.instances = self.instances.sort(key=lambda instance: instance.child_depth)

    # Takes a point in local space and translates it to world space
    def get_world_position(self, local_position):
        r = math.sqrt((local_position[0] ** 2) + (local_position[1] ** 2))
        theta = math.atan2(local_position[1], local_position[0])

        x = r * math.cos(theta + self.world_rotation)
        y = r * math.sin(theta + self.world_rotation)

        world_position = [local + world for local, world in zip([x, y], self.world_position)]

        return world_position

    # Takes a point in world space and translates it to local space
    def get_local_position(self, world_position):
        distance = get_distance(self.world_position, world_position)
        distance_x = world_position[0] - self.world_position[0]
        distance_y = world_position[1] - self.world_position[1]

        angle = math.atan2(distance_y, distance_x)

        angle -= self.world_rotation

        x = math.cos(angle) * distance
        y = math.sin(angle) * distance
        return[x, y]

    # Takes a rotation in local space and translates it to world space
    def get_world_rotation(self, local_rotation):
        world_rotation = local_rotation + self.world_rotation

        world_rotation = math.fmod(world_rotation, math.pi * 2)

        return world_rotation

    # Takes a rotation in world space and translates it to local space
    def get_local_rotation(self, world_rotation):
        return world_rotation - self.world_rotation

    # Ensures object's children will follow the parent
    def update(self):
        if self.parent is not None:
            self.world_rotation = self.parent.get_world_rotation(self.rotation)
            self.world_position = self.parent.get_world_position(self.position)
        else:
            self.world_rotation = self.rotation
            self.world_position = self.position

        for child in self.children:
            child.update()

    # To be implemented by the other classes that inherit from this one
    # It's meant to happen once every frame
    # Should contain code to be executed every frame
    def frame(self, delta_time):
        pass

    # Ensures world space position and rotation stay up to date when setting
    # position and rotation in local space
    def set_position_rotation(self, new_position=None, new_rotation=None):
        update = False
        if new_position is not None:
            self.position = new_position
            update = True

        if new_rotation is not None:
            self.rotation = new_rotation
            update = True

        if update:
            self.update()

    # Allows to increment position and rotation without going beyond the
    # previously established boundaries
    def increment_position_rotation(self, position_increment=None, rotation_increment=None):
        update = False
        if position_increment is not None:
            new_position = [original + increment for original, increment in zip(self.position, position_increment)]
            if new_position[0] < self.position_constraints["min_x"]:
                new_position[0] = self.position_constraints["min_x"]

            if new_position[0] > self.position_constraints["max_x"]:
                new_position[0] = self.position_constraints["max_x"]

            if new_position[1] < self.position_constraints["min_y"]:
                new_position[1] = self.position_constraints["min_y"]

            if new_position[1] > self.position_constraints["max_y"]:
                new_position[1] = self.position_constraints["max_y"]

            self.position = new_position

            update = True

        if rotation_increment is not None:
            self.rotation += rotation_increment
            update = True

        if update:
            self.update()

    # To be implemented by the other classes that inherit from this one
    # It's meant to happen once every frame
    # Should contain code to draw the object
    def draw(self):
        pass

    # Will be called once every frame to draw every object and it's children
    def draw_children(self):
        for child in self.children:
            if child.draw_enabled:
                child.draw()
                child.draw_children()

    # Call this method to remove an object without leaving zombie references
    # It removes children objects as well
    def destroy(self):
        SimulationBaseObject.instances.remove(self)

        if self.parent is not None:
            self.parent.children.remove(self)

        for child in self.children:
            child.parent = None
            child.destroy()


# A sensor that "sees" an area defined by a radius (max_range) and a field of view (fov_angle)
# It outputs the distance to the closest object detected

class SectorSensor(SimulationBaseObject):
    def __init__(self, position, rotation, max_range, fov_angle, detection_tag, debug_surface, debug_color,
                 ignore_tag=None):
        super().__init__()
        self.position = position
        self.rotation = rotation
        self.max_range = max_range
        self.fov_angle = fov_angle
        self.debug_surface = debug_surface
        self.debug_color = debug_color
        self.min_distance = self.max_range
        self.min_distance_normalized = 1
        self.draw_enabled = False

        # The sensor will detect objects containing detection_tag
        # Optionally, it will ignore objects containing ignore_tag
        self.detection_tag = detection_tag
        self.ignore_tag = ignore_tag

    def frame(self, delta_time):
        self.min_distance = self.max_range
        for instance in SimulationBaseObject.instances:
            if (self.detection_tag in instance.tags) and (self.ignore_tag not in instance.tags):
                distance = get_distance(self.world_position, instance.world_position)

                detection = False
                if distance < self.max_range:
                    local_position = self.get_local_position(instance.world_position)
                    angle = math.atan2(local_position[1], local_position[0])
                    half_fov = self.fov_angle / 2

                    if -half_fov < angle < half_fov:
                        detection = True

                    if detection:
                        self.min_distance = min(self.min_distance, distance)

        self.min_distance_normalized = self.min_distance / self.max_range

    def draw(self):
        stop_angle = self.fov_angle / 2
        start_angle = -stop_angle

        pygame.gfxdraw.pie(
            self.debug_surface,
            int(self.world_position[0]),
            int(self.world_position[1]),
            int(self.max_range),
            int(math.degrees(self.get_world_rotation(start_angle))),
            int(math.degrees(self.get_world_rotation(stop_angle))),
            self.debug_color
        )

        if self.min_distance < self.max_range:
            pygame.gfxdraw.pie(
                self.debug_surface,
                int(self.world_position[0]),
                int(self.world_position[1]),
                int(self.min_distance),
                int(math.degrees(self.get_world_rotation(start_angle))),
                int(math.degrees(self.get_world_rotation(stop_angle))),
                self.debug_color
            )


# Burgers to be consumed by the cats
class Burger(SimulationBaseObject):
    burger_instances = []

    def __init__(self, surface, energy):
        super().__init__()
        Burger.burger_instances.append(self)
        self.surface = surface
        self.radius = 25
        self.energy = energy
        self.color = (255, 255, 200)
        self.draw_circle = False

        self.tags.append("Burger")

        self.picture = None
        try:
            picture_path = os.path.join("res", "burger_sprite_50x50.png")
            self.picture = pygame.image.load(picture_path)
        finally:
            pass

    def draw(self):

        if self.draw_circle:
            pygame.draw.circle(
                self.surface,
                self.color,
                [int(component) for component in self.world_position],
                self.radius,
            )

        if self.picture is not None:
            picture_position = (
                self.world_position[0] - (self.picture.get_width() / 2),
                self.world_position[1] - (self.picture.get_height() / 2)
            )

            self.surface.blit(self.picture, picture_position)

    def got_eaten(self, eater):
        eater.energy += self.energy
        Burger.burger_instances.remove(self)
        self.destroy()


class Cat(SimulationBaseObject):
    cat_instances = []

    def __init__(self, surface, sensor_surface, initial_energy, split_threshold, sensor_range, evolution_options):
        super().__init__()
        Cat.cat_instances.append(self)
        self.name = catnames.gen() + "_" + str(random.randint(0, 1000))
        self.alive_seconds = 0
        self.ancestor_count = 0
        self.total_burgers_eaten = 0
        self.track_minutes = 3
        self.tracker_seconds = 60 * self.track_minutes
        self.burger_tracker = list()
        self.burger_rate = 0
        self.surface = surface
        self.radius = 28
        self.notch_width = 2
        random_color = colorsys.hsv_to_rgb(random.random(), 1, 1)
        self.body_color = (
            random_color[0] * 255,
            random_color[1] * 255,
            random_color[2] * 255
        )
        self.notch_color = (255, 255, 255)
        self.movement_velocity = 0
        self.rotation_velocity = 0
        self.initial_energy = initial_energy
        self.energy = self.initial_energy
        self.split_threshold = split_threshold
        self.evolution_options = evolution_options
        self.brain = None
        self.brain_complexity = None
        self.is_immortal = False
        self.use_brain = True
        self.sensors = dict()
        self.sensor_surface = sensor_surface
        self.sensors_range = sensor_range

        self.tags.append("Cat")
        # The following tag is used to make cat sensors ignore it's parent cat.
        self.tags.append(str(id(self)))

        self.picture = None
        try:
            picture_directory = os.path.join("res", "cats")
            picture_name = random.choice(os.listdir(picture_directory))
            picture_path = os.path.join(picture_directory, picture_name)
            self.picture = pygame.image.load(picture_path)
        finally:
            pass

        burger_sensor_debug_color = (50, 255, 50)

        self.sensors["burger_left"] = SectorSensor(
            position=[0, 0],
            rotation=math.radians(-30),
            max_range=self.sensors_range,
            fov_angle=math.radians(30),
            detection_tag="Burger",
            debug_surface=sensor_surface,
            debug_color=burger_sensor_debug_color
        )

        self.sensors["burger_front"] = SectorSensor(
            position=[0, 0],
            rotation=0,
            max_range=self.sensors_range,
            fov_angle=math.radians(30),
            detection_tag="Burger",
            debug_surface=sensor_surface,
            debug_color=burger_sensor_debug_color
        )

        self.sensors["burger_right"] = SectorSensor(
            position=[0, 0],
            rotation=math.radians(30),
            max_range=self.sensors_range,
            fov_angle=math.radians(30),
            detection_tag="Burger",
            debug_surface=sensor_surface,
            debug_color=burger_sensor_debug_color
        )

        cat_sensor_debug_color = (255, 100, 255)

        self.sensors["cat_left"] = SectorSensor(
            position=[0, 0],
            rotation=math.radians(-30),
            max_range=self.sensors_range,
            fov_angle=math.radians(30),
            detection_tag="Cat",
            debug_surface=sensor_surface,
            debug_color=cat_sensor_debug_color,
            ignore_tag=str(id(self))
        )

        self.sensors["cat_front"] = SectorSensor(
            position=[0, 0],
            rotation=0,
            max_range=self.sensors_range,
            fov_angle=math.radians(30),
            detection_tag="Cat",
            debug_surface=sensor_surface,
            debug_color=cat_sensor_debug_color,
            ignore_tag=str(id(self))
        )

        self.sensors["cat_right"] = SectorSensor(
            position=[0, 0],
            rotation=math.radians(30),
            max_range=self.sensors_range,
            fov_angle=math.radians(30),
            detection_tag="Cat",
            debug_surface=sensor_surface,
            debug_color=cat_sensor_debug_color,
            ignore_tag=str(id(self))
        )

        for key, sensor in self.sensors.items():
            sensor.set_parent(self)

    def set_debug_draw(self, value):
        for sensor in self.sensors.values():
            sensor.draw_enabled = value

    def check_point_inside(self, point):
        distance = get_distance(self.world_position, point)
        return distance < self.radius

    def new_brain(self):
        self.brain = Brain(
            input_keys=[
                "burger_detector_left",
                "burger_detector_front",
                "burger_detector_right",
                "cat_detector_left",
                "cat_detector_front",
                "cat_detector_right",
                "x",
                "y",
                "rotation_sin",
                "rotation_cos",
                "bias"
            ],
            output_nodes={
                "translation_velocity": activation_functions.fun_sigmoid,
                "rotation_velocity": activation_functions.fun_sigmoid,
            },
            evolution_options=self.evolution_options
        )
        self.brain.allow_recurrency = True
        self.brain.randomize_genotype()
        """for i in range(0, 2):
            self.brain.random_insert_node()"""
        for i in range(0, int(len(self.brain.input_keys)/2)):
            self.brain.random_new_connection()
        self.brain.build_network()
        self.brain_complexity = len(
            [gene for gene in self.brain.genotype.values() if gene["enable"] is True]
        )

    def clone_brain(self, original_brain):
        self.brain = original_brain.clone()
        self.brain.build_network()
        self.brain_complexity = len(
            [gene for gene in self.brain.genotype.values() if gene["enable"] is True]
        )

    def frame(self, delta_time):
        # Get input values
        inputs = dict()
        inputs["burger_detector_left"] = self.sensors["burger_left"].min_distance_normalized
        inputs["burger_detector_front"] = self.sensors["burger_front"].min_distance_normalized
        inputs["burger_detector_right"] = self.sensors["burger_right"].min_distance_normalized
        inputs["cat_detector_left"] = self.sensors["cat_left"].min_distance_normalized
        inputs["cat_detector_front"] = self.sensors["cat_front"].min_distance_normalized
        inputs["cat_detector_right"] = self.sensors["cat_right"].min_distance_normalized
        inputs["x"] = self.position[0] / self.position_constraints["max_x"]
        inputs["y"] = self.position[1] / self.position_constraints["max_y"]
        inputs["rotation_sin"] = math.sin(self.rotation)
        inputs["rotation_cos"] = math.cos(self.rotation)
        inputs["bias"] = 1

        # Activate network

        self.brain.network.set_inputs(inputs)

        self.brain.network.activate()

        outputs = self.brain.network.get_outputs()

        if self.use_brain:
            self.movement_velocity = (outputs["translation_velocity"] - 0.5) * 400
            self.rotation_velocity = (outputs["rotation_velocity"] - 0.5) * (math.pi * 4)

        # Move and split

        rotation_increment = self.rotation_velocity * delta_time

        movement_magnitude = self.movement_velocity * delta_time

        movement_delta_x = math.cos(self.rotation) * movement_magnitude
        movement_delta_y = math.sin(self.rotation) * movement_magnitude

        movement_vector = [movement_delta_x, movement_delta_y]

        self.increment_position_rotation(movement_vector, rotation_increment)

        movement_cost = abs(movement_magnitude) / 100
        rotation_cost = abs(rotation_increment) / (math.pi * 2)
        time_cost = delta_time
        self.energy -= movement_cost + rotation_cost + time_cost

        if self.energy > self.split_threshold:
            self.split()

        # Check if cat is dead

        if self.energy <= 0:
            if not self.is_immortal:
                Cat.cat_instances.remove(self)
                self.destroy()
            else:
                self.energy = 0

        # Check if there's something to eat

        for instance in SimulationBaseObject.instances:
            if "Burger" in instance.tags:
                distance = get_distance(self.world_position, instance.world_position)
                if distance < (self.radius + instance.radius + 30):
                    self.energy += (time_cost * 2)
                if distance < (self.radius + instance.radius):
                    instance.got_eaten(self)

                    self.total_burgers_eaten += 1

                    self.burger_tracker.append(self.tracker_seconds)

        # Upgrade burger rate

        self.burger_rate = len(self.burger_tracker)

    def call_every_second(self):
        self.alive_seconds += 1
        for index in range(0, len(self.burger_tracker)):
            self.burger_tracker[index] -= 1
        self.burger_tracker = [number for number in self.burger_tracker if number > 0]

    def split(self):
        new_cat = Cat(
            self.surface,
            self.sensor_surface,
            self.initial_energy,
            self.split_threshold,
            self.sensors_range,
            self.evolution_options
        )

        self.energy -= new_cat.energy
        new_cat.position = self.position
        new_cat.rotation = self.rotation
        new_cat.set_parent(self.parent)
        new_cat.position_constraints = self.position_constraints.copy()
        new_cat.ancestor_count = self.ancestor_count + 1
        new_cat.clone_brain(self.brain)

    def draw(self):
        pygame.draw.circle(
            self.surface,
            self.body_color,
            [int(component) for component in self.world_position],
            self.radius,
        )

        line_endpoint_x = math.cos(self.world_rotation) * self.radius
        line_endpoint_y = math.sin(self.world_rotation) * self.radius
        line_endpoint = [
            self.world_position[0] + line_endpoint_x,
            self.world_position[1] + line_endpoint_y
        ]

        if self.picture is None:
            pygame.draw.line(
                self.surface,
                self.notch_color,
                self.world_position,
                line_endpoint,
                self.notch_width
            )
        else:
            rotated_picture = pygame.transform.rotate(
                self.picture,
                -math.degrees(self.world_rotation) - 90
            )

            picture_position = (
                self.world_position[0] - (rotated_picture.get_width()/2),
                self.world_position[1] - (rotated_picture.get_height() / 2)
            )

            self.surface.blit(rotated_picture, picture_position)


class Leaderboard(SimulationBaseObject):
    def __init__(self, surface):
        super().__init__()
        self.surface = surface

        text_font_path = os.path.join("res", "font", "LifeSavers-Regular.ttf")
        self.text_font = pygame.font.Font(text_font_path, 16)
        header_font_path = os.path.join("res", "font", "LifeSavers-Bold.ttf")
        self.header_font = pygame.font.Font(header_font_path, 20)

        self.scoreboard_color = (180, 150, 150)
        self.scoreboard_width = 260
        self.scoreboard_height = 900
        self.leaders = []

        self.set_position_rotation(
            new_position=(
                (self.surface.get_width()/2) - self.scoreboard_width,
                -(self.surface.get_height()/2)
            )
        )

        self.canvas = pygame.Surface(
            (self.scoreboard_width, self.scoreboard_height),
        )

    def draw(self):

        pygame.draw.rect(
            self.canvas,
            self.scoreboard_color,
            pygame.Rect(
                (0, 0),
                (self.scoreboard_width, self.scoreboard_height)
            )
        )

        header = self.header_font.render("TOP BURGER HUNTERS", True, (0, 0, 0))
        self.canvas.blit(header, (20, 15))

        x = 10
        for index, cat in enumerate(self.leaders):
            y = (index * 140) + 50

            cat_x = x + 32
            cat_y = y + 50

            pygame.draw.circle(
                self.canvas,
                cat.body_color,
                [cat_x, cat_y],
                cat.radius,
            )

            if cat.picture is not None:
                self.canvas.blit(
                    cat.picture,
                    (
                        cat_x - int(cat.picture.get_width() / 2),
                        cat_y - int(cat.picture.get_height() / 2)
                    )
                )

            energy_int = int(cat.energy)

            lines = list()
            lines.append("    " + cat.name)
            lines.append("Burgers ({} min): ".format(cat.track_minutes) + "{:,}".format(cat.burger_rate))
            lines.append("Energy: " + "{:,}".format(energy_int))
            lines.append("Age: " + int_to_hms_string(cat.alive_seconds))
            lines.append("Brain Complexity: " + "{:,}".format(cat.brain_complexity))
            lines.append("Ancestors: " + "{:,}".format(cat.ancestor_count))

            text_height = 0
            text_y = y + 5
            for line in lines:
                text = self.text_font.render(line, True, (0, 0, 0))
                text_y += text_height
                self.canvas.blit(text, (x+65, text_y))
                text_height = text.get_height()

            pygame.draw.rect(
                self.canvas,
                (0, 0, 0),
                pygame.Rect((x, y), (self.scoreboard_width - 20, 135)),
                3
            )

        total_cats = len(Cat.cat_instances)
        cats_str = "Alive cats: " + str(total_cats)
        time_img = self.header_font.render(cats_str, True, (0, 0, 0))
        self.canvas.blit(time_img, (x, 790))

        total_seconds = int(pygame.time.get_ticks() / 1000)
        time_str = "Total time: " + int_to_hms_string(total_seconds)
        time_img = self.header_font.render(time_str, True, (0, 0, 0))
        self.canvas.blit(time_img, (x, 830))

        self.surface.blit(
            self.canvas,
            self.world_position
        )


class Arena(SimulationBaseObject):
    def __init__(self, width, height, surface):
        super().__init__()
        self.limits = dict()
        self.width = width
        self.height = height
        self.surface = surface
        self.color = (100, 100, 200)

        self.limits["min_x"] = -self.width / 2
        self.limits["max_x"] = self.width / 2
        self.limits["min_y"] = -self.height / 2
        self.limits["max_y"] = self.height / 2

    def draw(self):
        self.surface.fill(
            self.color,
            pygame.Rect(
                (self.limits["min_x"], self.limits["min_y"]),
                (self.width, self.height)
            )
        )


class Alife1App:
    def __init__(self):

        self.evolution_options = EvolutionOptions()

        ##############################################################################
        #          Change these settings to configure the evolution process          #
        ##############################################################################

        # Maximum amount of burgers that can exist at the same time
        self.max_burgers = 10

        # How often (in milliseconds) will burgers appear, if there are
        # less than max_burgers
        self.burger_timer_period = 1000

        # Minimum amount of cats. Random cats will appear if there are less
        # than this number
        self.min_cats = 15

        # How far away (in pixels) will cats be capable of seeing burgers and other
        # cats
        self.sensor_max_range = 400

        # How much energy a cat gains after eating a burger
        self.burger_energy = 40

        # How much energy a cat has when it spawns
        self.initial_cat_energy = 40

        # Cats will split when they reach this amount of energy
        # Parent cat will lose initial_cat_energy after doing it
        self.cat_split_threshold = 300

        # All probabilities are represented with a number between 0(0%) and 1(100%)

        # How likely is it for a gene to be mutated (Either connection gene or node
        # gene)
        self.evolution_options.gene_mutation_probability = 0.1

        # How likely it is for a mutated connection gene to change it's weight by
        # adding perturbation_delta
        self.evolution_options.weight_perturbation_probability = 0.8

        # perturbation_delta is a random number chosen such that
        # -perturbation_max_delta < perturbation_delta < perturbation_max_delta
        self.evolution_options.weight_perturbation_max_delta = 0.5

        # If a gene is not mutated by adding perturbation_delta, then it will be
        # asigned a random number chosen such that
        # -weight_random_mutation_range < number < weight_random_mutation_range
        self.evolution_options.weight_random_mutation_range = 3

        # How likely it is for a connection gene to be disabled
        self.evolution_options.connection_disable_probability = 0.001

        # How likely it is to insert a new node that splits an existing connection
        # when a cat splits
        self.evolution_options.node_insertion_chance = 0.1

        # How likely it is to create a new connection between existing nodes
        # when a cat splits
        self.evolution_options.new_connection_chance = 0.1

        # Available activation functions. Nodes will have an activation function
        # chosen at random from this list when they are created, or when an
        # existing node is mutated. More activation functions can be appended
        # to this list if desired.
        self.evolution_options.activation_functions.append(activation_functions.fun_sigmoid)

        ##############################################################################

        # Set to true if you want to control a "cat"
        # (It will be a circle without a cat picture on it)
        self.allow_test_cat = False

        self.window_width = 1440
        self.window_height = 900
        pygame.init()

        self.display = pygame.display.set_mode((self.window_width, self.window_height))

        self.max_framerate = 60

        self.backgorund_color = (0, 0, 0)
        self.clock = pygame.time.Clock()

        self.selected_cat = None

        self.layers = dict()

        self.layers["burgers"] = pygame.Surface(
            (self.window_width, self.window_height),
            flags=pygame.SRCALPHA
        )
        self.layers["cats"] = pygame.Surface(
            (self.window_width, self.window_height),
            flags=pygame.SRCALPHA
        )
        self.layers["sensors"] = pygame.Surface(
            (self.window_width, self.window_height),
            flags=pygame.SRCALPHA
        )
        self.layers["overlay"] = pygame.Surface(
            (self.window_width, self.window_height),
            flags=pygame.SRCALPHA
        )
        self.layers["arena"] = pygame.Surface(
            (self.window_width, self.window_height),
            flags=pygame.SRCALPHA
        )

        self.root = SimulationBaseObject()
        self.root.set_position_rotation([self.window_width / 2, self.window_height / 2])

        self.arena = Arena(self.window_width - 260, self.window_height, self.layers["arena"])
        self.arena.set_parent(self.root)
        self.arena.set_position_rotation([-(260/2), 0])

        self.leaderboard = Leaderboard(
            surface=self.layers["overlay"]
        )
        self.leaderboard.set_parent(self.root)

        if self.allow_test_cat:
            self.testCat = Cat(
                self.layers["cats"],
                self.layers["sensors"],
                self.initial_cat_energy,
                self.cat_split_threshold,
                self.sensor_max_range,
                self.evolution_options
            )
            self.testCat.set_parent(self.arena)
            self.testCat.is_immortal = True
            self.testCat.use_brain = False
            self.testCat.position_constraints["min_x"] = self.arena.limits["min_x"]
            self.testCat.position_constraints["max_x"] = self.arena.limits["max_x"]
            self.testCat.position_constraints["min_y"] = self.arena.limits["min_y"]
            self.testCat.position_constraints["max_y"] = self.arena.limits["max_y"]
            self.testCat.body_color = (64, 255, 64)
            self.testCat.new_brain()
            self.testCat.picture = None

        self.spawn_burgers(self.max_burgers)
        self.spawn_random_cats(self.min_cats)

        self.ONE_SECOND_TIMER_EVENT = pygame.USEREVENT + 1
        pygame.time.set_timer(self.ONE_SECOND_TIMER_EVENT, 1000)

        self.BURGER_TIMER_EVENT = pygame.USEREVENT + 2
        pygame.time.set_timer(self.BURGER_TIMER_EVENT, self.burger_timer_period)

    def spawn_burgers(self, number):
        for i in range(0, number):
            burger = Burger(self.layers["burgers"], self.burger_energy)
            x = random.randint(self.arena.limits["min_x"], self.arena.limits["max_x"])
            y = random.randint(self.arena.limits["min_y"], self.arena.limits["max_y"])
            burger.set_parent(self.arena)
            burger.set_position_rotation([x, y], 0)

    def spawn_random_cats(self, number):
        for i in range(0, number):
            random_cat = Cat(
                self.layers["cats"],
                self.layers["sensors"],
                self.initial_cat_energy,
                self.cat_split_threshold,
                self.sensor_max_range,
                self.evolution_options
            )

            random_cat.set_parent(self.arena)
            random_cat.position_constraints["min_x"] = self.arena.limits["min_x"]
            random_cat.position_constraints["max_x"] = self.arena.limits["max_x"]
            random_cat.position_constraints["min_y"] = self.arena.limits["min_y"]
            random_cat.position_constraints["max_y"] = self.arena.limits["max_y"]
            random_cat.new_brain()

            half_width = int(self.window_width / 2)
            half_height = int(self.window_height / 2)

            position = [
                random.randint(-half_width, half_width),
                random.randint(-half_height, half_height)
            ]

            rotation = random.uniform(0, math.radians(360))

            random_cat.set_position_rotation(position, rotation)

    def print_selected_cat_info(self):
        cat = self.selected_cat

        print("")
        print("##########################")
        print("")

        print(self.selected_cat.name)
        print("")
        print("Burgers ({} min): ".format(cat.track_minutes) + "{:,}".format(cat.burger_rate))
        print("Energy: " + "{:,}".format(cat.energy))
        print("Age: " + int_to_hms_string(cat.alive_seconds))
        print("Brain Complexity: " + "{:,}".format(cat.brain_complexity))
        print("Ancestors: " + "{:,}".format(cat.ancestor_count))
        print("Input nodes:")
        for node in cat.brain.input_keys:
            print("   ", node)
        print("Output nodes:")
        for node in cat.brain.output_nodes.items():
            print("   ", node)
        print("Active genes:")
        for node in [gene for gene in cat.brain.genotype.values() if gene["enable"] is True]:
            print("   ", node)
        print("Full genotype:")
        for gene in cat.brain.genotype.values():
            print("    " + str(gene))

        print("")
        print("##########################")
        print("")

    def run(self):
        while True:
            # Pygame event processing
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()

                # Click on a cat to display it's sensors and print information about it
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.selected_cat is not None:
                            self.selected_cat.set_debug_draw(False)
                            self.selected_cat = None

                        for cat in Cat.cat_instances:
                            if cat.check_point_inside(event.pos):
                                self.selected_cat = cat

                        if self.selected_cat is not None:
                            self.selected_cat.set_debug_draw(True)
                            self.print_selected_cat_info()

                # A timer that triggers once every second. Some things get updated here
                elif event.type == self.ONE_SECOND_TIMER_EVENT:
                    Cat.cat_instances.sort(key=lambda this_cat: this_cat.burger_rate, reverse=True)
                    for cat in Cat.cat_instances:
                        cat.call_every_second()

                    self.leaderboard.leaders = Cat.cat_instances[0:5]

                    if len(Cat.cat_instances) < self.min_cats:
                        self.spawn_random_cats(1)

                # A dedicated timer for burger spawning. It allows to controll the burger spawn
                # rate independently from other things
                elif event.type == self.BURGER_TIMER_EVENT:
                    if len(Burger.burger_instances) < self.max_burgers:
                        self.spawn_burgers(1)

            # Polling

            # In case you want to control a "cat"
            if self.allow_test_cat:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_UP]:
                    self.testCat.movement_velocity = 200
                elif keys[pygame.K_DOWN]:
                    self.testCat.movement_velocity = -200
                else:
                    self.testCat.movement_velocity = 0

                if keys[pygame.K_LEFT]:
                    self.testCat.rotation_velocity = -(math.pi * 2)
                elif keys[pygame.K_RIGHT]:
                    self.testCat.rotation_velocity = (math.pi * 2)
                else:
                    self.testCat.rotation_velocity = 0

            # Simulation step

            delta_time = self.clock.tick(self.max_framerate) / 1000
            for instance in SimulationBaseObject.instances:
                instance.frame(delta_time)

            # Clear display and surfaces

            self.display.fill(self.backgorund_color)
            for key, surface in self.layers.items():
                surface.fill((0, 0, 0, 0))

            # Draw things

            self.root.draw_children()

            # Update display and surfaces

            surface_names = [
                "arena",
                "burgers",
                "cats",
                "sensors",
                "overlay"
            ]

            for surface_name in surface_names:
                self.display.blit(self.layers[surface_name], (0, 0))

            pygame.display.update()


if __name__ == '__main__':
    app = Alife1App()
    app.run()
