# About

Andrew and I really want to buy a **large** array of batteries to help backup the house
in the event of an outage. Living in Houston, in 2024 alone, we saw about seven nonconsecutive
days worth of outages with the longest lasting for four consecutive days. Given that
we had solar installed in 2023 a battery backup system is particularly attractive, but
before we dive in we need to consider whether a given system is likely to meet our needs. 

Because we've been using a `Raspberry Pi` to pull data from our solar installs into a local
`HomeAssistant` instance, we have granular (every three minutes) data about how much energy
we produce and how much energy we consume. We primarily serve this data into HomeAssistant for
monitoring, where our **actual production** is evaluated against a **forecast production**
so that we have visibility into how the system is performing and whether it is performing as
expected.

From here it's also very easy to push the data into a local `InfluxDB` instance for
longer term storage. As of JAN 2025, we have a little over a full year's worth of historical
data about our system. I want to use this data to try and answer the following questions:

* Given a historical net consumption behavior *p* and a battery capacity *c*, what is the 
probability that a capacity *c* can get us through an outage of *n* consecutive days?
* Given that the battery's performance will degrade over time, how can I consider multiple
years of performance loss?
* Given that our solar system will also likely degrade and/or our net consumption will
worsen, how can I consider multiple years of these changes?

# How to Use This Model

To create a `SolarBatterySim`, you'll need to define your `NetConsumptionProfile` and
a set of `Battery` objects you are interested in simulating.

```python
from solar_sim import SolarBatterySim, Battery, NetConsumptionProfile

battery = Battery(capacity_KWh = 13.5,
                  reserve_pct = 0.05,
                  degredation_profile = [0.1, 0.05, 0.05])

profile = NetConsumptionProfile(avg_net_consumption_KWh = -3.4645,
                                stdv_net_consumption_KWh = 10.004,
                                degredation_profile = [0.01, 0.01, 0.01, 0.01, 0.01])

sim = SolarBatterySim(label="Test_sim",
    n_simulations=200_000,
    n_consecutive_days=4,
    batteries=[battery],
    profile=profile,
)
```
## Net Consumption Profiles
Your `NetConsumptionProfile` (*p*) should describe your typical net consumption in a given
period, where you've got enough data to calculate an average and a standard deviation.
The underlying model assumes that your net consumption is normally distributed, and when
simulating, values will randomly be drawn from this distribution.

You want to make sure you define your net consumption as:

$$\text{Net Consumption (KWh)} = \text{Total Production (KWh)} - \text{Total Consuption (KWh)}$$

This means that, for the model, if you are producing more than you consume, you have a 
positive net consumption; and if you are consuming more than you produce, you have a negative
net consumption.

## Batteries
Each `Battery` should describe its capacity (*c*) and a percent left in reserve, as
we found that batteries would never actually deplete to zero. This meant that batteries
have an *accessible capacity* which is different from its actual capacity. The model
calculates this accessible capacity as:

$$\text{Accessible Capacity (KWh)} = \text{Total Capacity (KWh)} - \text{Reserve (KWh)}$$

Each time a model evaluates an outcome, it considers the *accessible capacity* only.

## Degredation Profiles
Degredation profiles are only required if you are interested in simulating a year-over-year
scenario where you are specifying *by how much a system degrades in a year*,
such that the total capacity (*c*) or net consumption profile (*p*) worsen. In the case
of batteries, the total capacity is reduced; and in the case of consumption profiles, the
average net consumption is reduced.

This allows you to game out situations where both the batteries and your net behavior worsen
over time; or either or neither worsen. Note that because each battery and profile is
an independent object, you can specify distinct degredation curves for each.

$$\text{Degraded Value (KWh)} = \text{Original Value (KWh)} - (\text{Original Value }\times \text{ Percent})$$

# Simulation

Essentially the way this works is we are simulating *n* consecutive days of net consumption,
summing that behavior, and then adding in the accessible capacity of the battery system.

For example, let's say we're interested in getting through 4 consecutive days off the grid
and we have the following known variables:

```
# Net consumption for four days - these are all negative, meaning all days we consumed
# more energy than we produced
day_one_net_consumption = -10
day_two_net_consumption = -5
day_three_net_consumption = -12
day_four_net_consumption = -7

# Then we have our total battery capacity
battery = 30

# But not all of it is accessible, because of a 5% reserve
battery_actual = 30 - 30 * 0.95
battery_actual = 28.5
```
At this point, finding out whether we'd get through the outage just requires summing
everything together:

$$ \text{Total Net Consumption} = \text{Daily Net Consumption} + \text{Battery Capacity}$$
$$ \text{Total Net Consumption} = (-10+-5+-12+-7) + 28.5$$
$$ \text{Total Net Consumption} = -5.5\text{ KWh}$$

The result of this simulation is a fail:  because we'd be short 5.5 KWh, we wouldn't make
it through the outage with this battery system and this rate of consumption.

When you create your `SolarBatterySim`, this is everything that's happening under the hood.
Specifying `n_simulations` allows you to determine how many total of these simulations will
be run to determine the probability of success of a given setup.

This is the simplest simulation, and you can build it by calling `SolarBatterySim().simple_sim()`
like in the following example:

```python
sim = SolarBatterySim(
    label="Test_sim",
    n_simulations=200_000,
    n_consecutive_days=4,
    batteries=[battery_one, battery_two, battery_three],
    profile=profile,
)

sim.simple_sim()
```

More complex simulations consider by how much the total system degrades so that you can
estimate year-over-year changes in probabilities of success; battery capacity; and net consumption.
Getting value out of this means you've also populated degredation curves for each element
you want to consider as degrading.

```python
sim.multi_year_sim(n_years=10)
```

The output will generally be a `SolarSimResult` dataclass object, where you can easily
access details about the simulation which may interest you:

```python
@dataclass
class SolarSimResult:
    """Containerizes the sim results"""

    p_success: float
    total_battery_capacity: float
    total_accessible_capacity: float
    avg_net_consumption: float
    raw_outcomes: List[float] = None
```

For more implementation examples, please see `/docs/simulation_personal.ipynb` or `/docs/demo_sim.ipynb`.

# Outcomes
To give you a preview of how I used this framework, I followed the following steps:

* Pulled historical data for hurricane season months (July, August, September)
* Determined my average net consumption for those months
* Created a system of batteries, each with the same capacity, reserve, and degredation profile
* Created a `SolarBatterySim` for each month with its associated net consumption profile and
the same set of batteries
* Ran this simulation for ten year-over-year periods to see how the probability of success
changed over time and with different modifications to energy consumption

![img](/docs/p_success_no_change.png)
![img](/docs/p_success_10.png)
![img](/docs/p_success_20.png)

As we can see from this, if we make *no* changes to our energy consumption in a 4-day outage,
40.5KWh is not enough to get us through it. But, if we can reduce our energy consumption
by up to 20% during an outage, our net consumption profile changes so drastically that
we can hit a 90+% chance of getting through.

At this point, the question can pivot to, "What's the minimum acceptable likelihood?" and
"What's the minimum required capacity?" to meet that likelihood.