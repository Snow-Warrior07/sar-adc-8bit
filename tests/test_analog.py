import numpy as np
import pytest
from model.ideal_adc import quantize
from model.analog_frontend import AnalogConfig,AnalogFrontEnd


def test_disabled_imperfections_match():
    fe=AnalogFrontEnd(AnalogConfig.ideal())
    for v in np.random.default_rng(42).uniform(-.49,.49,2000):assert fe.convert(v)==quantize(v)


def test_fixed_capacitor_instance_and_seed():
    a=AnalogFrontEnd(seed=5);b=AnalogFrontEnd(seed=5)
    before=a.weights.copy()
    for _ in range(5):a.convert(.123)
    assert np.array_equal(a.weights,b.weights)
    assert np.array_equal(a.weights,before)
    assert not np.array_equal(a.weights,AnalogFrontEnd(seed=6).weights)


def test_offset_and_settling_are_observable():
    ideal=AnalogConfig.ideal();offset=AnalogConfig.ideal();offset.comparator_offset_v=2/256
    assert AnalogFrontEnd(offset).convert(.123)-AnalogFrontEnd(ideal).convert(.123)==2
    slow=AnalogConfig.ideal();slow.dac_tau_s=5e-6
    assert AnalogFrontEnd(slow).convert(.31)!=quantize(.31)


def test_noise_event_reproducibility_and_timeout():
    a=AnalogFrontEnd(seed=23);b=AnalogFrontEnd(seed=23)
    assert [a.convert(.123) for _ in range(100)]==[b.convert(.123) for _ in range(100)]
    cfg=AnalogConfig.ideal();cfg.delay_base_s=1e-6
    with pytest.raises(TimeoutError):AnalogFrontEnd(cfg).convert(.1)
