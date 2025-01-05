from numpy import random
import numpy as np
import pandas as pd
from typing import List, Dict
from dataclasses import dataclass
import copy


# A couple of helper functions here to manage consistent validations
def _check_acceptable_pct(pct: float, label: str = ""):
    """Checks to make sure that a percentage is formatted correctly -- eg,
    a float which satisfies 0 <= x < 1.

    Args:
        pct (float): The proposed value.
        label (str): The kwarg we're validating.

    Raises:
        ValueError: Raised if a float's value is bad
        TypeError: Raised if an incompatible number is provided
    """
    msg = f"({label}) must be a float of at least zero and less than 1"
    try:
        if pct >= 0 and pct < 1:
            pass
        else:
            raise ValueError(msg)
    except TypeError:
        raise TypeError(msg)


def _check_acceptable_list_floats(obj: List[float], label: str):
    """Checks to make sure our lists-of-percentages are formatted correctly.

    Args:
        obj (List[float]): The proposed List[float] object.
        label (str): The kwarg we're validating.

    Raises:
        TypeError: Raised if not iterable.
        BaseException: Raised if internal values aren't valid.
    """

    # First we want to make sure it's an iterable
    if hasattr(obj, "__iter__"):
        pass
    else:
        raise TypeError(f"({label}) must be an iterable")

    # Then we'd want to make sure that values in the iterable are consistent
    # with the desired format
    try:
        for element in obj:
            _check_acceptable_pct(element)
    except Exception:
        raise BaseException(
            f"({label}) expects an iterable where values are at least zero and less than 1"
        )


@dataclass
class SolarSimResult:
    """Containerizes the sim results"""

    p_success: float
    total_battery_capacity: float
    total_accessible_capacity: float
    avg_net_consumption: float
    raw_outcomes: List[float] = None


class Battery:
    """Typical properites and methods of Battery system, at least as far as we are
    interested.
    """

    def __init__(
        self,
        capacity_KWh: float,
        reserve_pct: float,
        degredation_profile: List[float] = [],
    ):
        """Simulates a battery object with given capacity in KWh; a percentage to keep
        in reserve; and a degredation profile.

        Args:
            capacity_KWh (float): Total KWh capacity of the battery.
            reserve_pct (float): A percentage of the total capacity to keep in reserve,
            such as 5% represented as 0.05.
            degredation_profile (List[float], optional): An array of percentages by
            which the total capacity of the battery should degrade year-over-year,
            represented as [x, x] where capacity degrades x% per year for two years.
            Defaults to [].
        """

        # Make sure the reserve_pct is in the correct format, and the values in a given
        # degredation_profile are acceptable
        _check_acceptable_pct(reserve_pct, "reserve_pct")
        _check_acceptable_list_floats(degredation_profile, "degredation_profile")

        self.capacity = capacity_KWh
        self.reserve = reserve_pct
        self.degredation_profile = degredation_profile

    def degrade(self):
        """Degrades the battery's total KWh capacity using values from the
        provided degredation profile in a multi-year scenario.
        """

        if self.degredation_profile:
            pct = self.degredation_profile.pop(0)
            self.capacity = self.capacity - (self.capacity * pct)
        else:
            pass

    def accessible_capacity(self) -> float:
        """Calculate the current accessible capacity of the specific battery. This
        calculation is basically (capacity - reserve capacity).

        Returns:
            float: The accessible capacity of the battery
        """

        return self.capacity - (self.capacity * self.reserve)


class NetConsumptionProfile:
    """The net consumption profile for a given time period. We assume that net
    consumption is normally distributed.
    """

    def __init__(
        self,
        avg_net_consumption_KWh: float,
        stdv_net_consumpetion_KWh: float,
        degredation_profile: List[float] = [],
    ):
        """The net consumption profile in KWh of your system, assumed to be normally
        distributed. Net consumption is considered as
        (Total Production (KWh) - Total Consumption (KWh)), such that a system which
        produces more than it consumes has a positive net consumption, and a system
        which consumes more than it produces has a negative net consumption.

        Args:
            avg_net_consumption_KWh (float): The average net consumption of your system.
            stdv_net_consumpetion_KWh (float): The STDEV of your net consumption.
            degredation_profile (List[float], optional): An array of percentages by
            which the profile itself should degrade year-over-year,
            represented as [x, x] where the average degrades x% per year for two years.
            This allows you to consider cases where your house becomes less efficient
            or your energy consumption grows relative to your energy production.
            Defaults to [].
        """
        _check_acceptable_list_floats(degredation_profile, "degredation_profile")
        self.avg = avg_net_consumption_KWh
        self.stdv = stdv_net_consumpetion_KWh
        self.degredation_profile = degredation_profile

    def degrade(self):
        """Degrades the average net consumption using values from the provided
        degredation profile. Only applicable in multi-year simulations.
        """

        if self.degredation_profile:
            pct = self.degredation_profile.pop(0)
            self.avg = self.avg - (self.avg * pct)

        else:
            pass

    def draw(self) -> float:
        """Draw a random net consumption for the day.

        Returns:
            float: Net consupmtion in KWh
        """

        return random.normal(self.avg, self.stdv)


class SolarBatterySim:
    """For a given month's typical net KWh consumption, with a given total battery
    capacity and number of simulations, calculate the probability that you could
    self-isolate off-grid for a given number of consecutive days.
    """

    def __init__(
        self,
        label: str,
        n_simulations: int,
        n_consecutive_days: int,
        batteries: List[Battery],
        profile: NetConsumptionProfile,
        n_years: int = None,
        copy_objects: bool = True,
    ):
        """For a given NetConsumptionProfile and Battery system, run n_simulations
        to determine the probability that you could self-isolate off-grid for a given
        number of n_consecutive_days.

        Args:
            label (str): _description_
            n_simulations (int): _description_
            n_consecutive_days (int): _description_
            batteries (List[Battery]): _description_
            profile (NetConsumptionProfile): _description_
            n_years (int, optional): _description_. Defaults to None.
            copy_objects: (bool): _description_
        """

        self.label: str = label
        self.n_simulations: int = n_simulations
        self.n_days: int = n_consecutive_days
        self.n_years: int = n_years

        # In the event the Profile and Batteries will be used in
        # other sims we want to protect against object overwrite
        if copy_objects:
            self.batteries: List[Battery] = [
                copy.deepcopy(battery) for battery in batteries
            ]
            self.profile: NetConsumptionProfile = copy.deepcopy(profile)
        else:
            self.batteries: List[Battery] = batteries
            self.profile: NetConsumptionProfile = profile

        # Store reset points, callable
        self._batteries_on_init: List[Battery] = batteries
        self._profile_on_init: NetConsumptionProfile = profile

    def _reset_sim(self):
        """Resets the sim to its init point so that further sims can
        be run on the same set of objects
        """
        self.batteries = self._batteries_on_init
        self.profile = self._profile_on_init

    def simple_sim(self, return_array: bool = False) -> SolarSimResult:
        """Run a sim for n consecutive days with a given set of batteries
        and a given consumption profile.

        Args:
            return_array (bool, optional): If True, it will return the full result
            of the simulation. NOTE: This is given as an array of length n_simulations
            where each float is the calculated total net consumption of a single
            simulation. Defaults to False.

        Returns:
            float: Percent chance of success (Case where net consumption is positive)
            tuple(float, list): A tuple of percent chance of success and the array
            of all results.
        """

        # Given our batteries in their current state, calculate the total
        # accessible battery capacity
        total_battery_capacity = sum([battery.capacity for battery in self.batteries])
        total_accessible_capacity = sum(
            [battery.accessible_capacity() for battery in self.batteries]
        )

        # Results container
        results = []

        # Now we just run the math with random drawings from a normal distribution
        # and record the results for each of n simulations
        for run in range(self.n_simulations):

            total_net_consumption = sum(
                [self.profile.draw() for i in range(self.n_days)]
            )
            results.append(total_accessible_capacity + total_net_consumption)

        # Now we can just calculate our percent chance of success
        pct_success = round((sum(np.array(results) > 0) / self.n_simulations), 4)

        # And finally return
        if not return_array:
            return SolarSimResult(
                pct_success,
                total_battery_capacity,
                total_accessible_capacity,
                self.profile.avg,
            )
        else:
            return SolarSimResult(
                pct_success,
                total_battery_capacity,
                total_accessible_capacity,
                self.profile.avg,
                results,
            )

    def multi_year_sim(
        self,
        n_years: int,
        return_arrays: bool = False,
        reset_sim: bool = True,
    ) -> Dict[str, SolarSimResult]:
        """Calculates probability of success over N years with considering each
        component's built-in degredation profile.

        Args:
            n_years (int): The number of years to simulate.
            return_arrays (bool, optional): Whether each run of the simulation
            for a given year returns the associated array of all results.
            Defaults to False.
            return_battery_capacity (bool, optional): Whether to return the

        Returns:
            dict(label, results): A dictionary with modified labels as keys
            and results as values.
        """

        results = {}

        # For a multi-year sim we need to degrade our performance
        # according to the given profile
        for year in range(n_years):

            # So, we'll just run the simple sim for the given year
            label = self.label + f"_y{year}"

            if return_arrays:
                result, arr = self.simple_sim(return_array=True)
                results[label] = (result, arr)
            else:
                result = self.simple_sim()
                results[label] = result

            # Now we can degrade performance for the next cycle
            self.profile.degrade()
            for battery in self.batteries:
                battery.degrade()

        # To prevent the simulation itself from degrading on multiple runs, we default
        # to the init conditions
        if reset_sim:
            self._reset_sim()

        # And now we can return
        return results
