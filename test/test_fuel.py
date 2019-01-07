from openap.fuel import FuelFlow

ff = FuelFlow('JT15D-4')

ff.plot_engine_fuel_flow()

def test_all():
    assert round(ff.at_thrust_ratio(0.1), 4) == 0.0305
    assert round(ff.at_thrust_ratio(0.9), 4) == 0.1521