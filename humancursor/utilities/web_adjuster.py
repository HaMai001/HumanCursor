import random
import numpy as np

from selenium.common.exceptions import MoveTargetOutOfBoundsException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By

from humancursor.utilities.human_curve_generator import HumanizeMouseTrajectory
from humancursor.utilities.calculate_and_randomize import generate_random_curve_parameters, calculate_absolute_offset


class WebAdjuster:
    def __init__(self, driver):
        self.__driver = driver
        self.__action = ActionChains(self.__driver, duration=0 if not isinstance(driver, Firefox) else 1)
        self.origin_coordinate = [0, 0]

    def move_to(
        self,
        element_or_pos,
        origin_coordinates=None,
        absolute_offset=False,
        relative_position=None,
        human_curve=None,
        steady=False
    ):
        """Moves the cursor, trying to mimic human behaviour!"""
        origin = origin_coordinates or self.origin_coordinate
        self._refetch_mouse(origin, random_point=(self.origin_coordinate == [0, 0]))

        pre_origin = tuple(origin)
        if isinstance(element_or_pos, list):
            if absolute_offset:
                x, y = element_or_pos[0], element_or_pos[1]
            else:
                x, y = (
                    element_or_pos[0] + pre_origin[0],
                    element_or_pos[1] + pre_origin[1],
                )
        else:
            script = "return { x: Math.round(arguments[0].getBoundingClientRect().left), y: Math.round(arguments[0].getBoundingClientRect().top) };"
            destination = self.__driver.execute_script(script, element_or_pos)
            if relative_position is None:
                x_random_off = random.randint(30, 70)/100
                y_random_off = random.randint(30, 70)/100

                x = destination["x"] + (element_or_pos.size["width"] * x_random_off)
                y = destination["y"] + (element_or_pos.size["height"] * y_random_off)
            else:
                abs_exact_offset = calculate_absolute_offset(element_or_pos, relative_position)
                x_exact_off, y_exact_off = abs_exact_offset[0], abs_exact_offset[1]
                x = destination["x"] + x_exact_off
                y = destination["y"] + y_exact_off

        (
            offset_boundary_x,
            offset_boundary_y,
            knots_count,
            distortion_mean,
            distortion_st_dev,
            distortion_frequency,
            tween,
            target_points,
        ) = generate_random_curve_parameters(
            self.__driver, [origin[0], origin[1]], [x, y]
        )
        if steady:
            offset_boundary_x, offset_boundary_y = 10, 10
            distortion_mean, distortion_st_dev, distortion_frequency = 1.2, 1.2, 1
        if not human_curve:
            human_curve = HumanizeMouseTrajectory(
                [origin[0], origin[1]],
                [x, y],
                offset_boundary_x=offset_boundary_x,
                offset_boundary_y=offset_boundary_y,
                knots_count=knots_count,
                distortion_mean=distortion_mean,
                distortion_st_dev=distortion_st_dev,
                distortion_frequency=distortion_frequency,
                tween=tween,
                target_points=target_points,
            )

        points = np.array([origin] + human_curve.points).round().astype(np.int32)
        arr_offset = np.diff(points, axis=0)
        for x_offset, y_offset in arr_offset:
            self.__action.move_by_offset(x_offset, y_offset)
        try:
            self.__action.perform()
        except MoveTargetOutOfBoundsException:
            self.__action.move_to_element(element_or_pos).perform()
            print(
                "MoveTargetOutOfBoundsException, Cursor Moved to Point, but without Human Trajectory!"
            )
        
        last_mouse_location = points[-1].tolist()
        self.origin_coordinate = last_mouse_location
        return last_mouse_location
    
    def _refetch_mouse(self, origin_coordinate, random_point:bool = False):
        """Update mouse positon"""
        body = self.__driver.find_element(By.TAG_NAME, 'body')
        size = body.size
        if random_point:
            random_x = (size['width'] * random.randint(10, 90)) // 100
            random_y = (size['height'] * random.randint(10, 90)) // 100
            self.__action.move_to_element_with_offset(body, random_x-size['width']//2, random_y-size['height']//2).perform()
            self.origin_coordinate = [random_x, random_y]
        else:
            x, y = origin_coordinate
            self.__action.move_to_element_with_offset(body, x-size['width']//2, y-size['height']//2).perform()
            self.origin_coordinate = [x, y]
            