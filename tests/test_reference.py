import numpy as np
import pytest
from model.ideal_adc import quantize,reconstruct,transitions,LSB
from model.sar_reference import convert,top_plates
from analysis.metrics import static_metrics,spectral_metrics


def test_all_codes_and_boundaries():
    points=list(-.5+(np.arange(256)+.5)*LSB)
    for v in transitions():points.extend([v-.001*LSB,v,v+.001*LSB])
    points.extend([-.6,-.5,.5,.6])
    points.extend(np.random.default_rng(20261017).uniform(-.6,.6,10000))
    for v in points:assert convert(float(v))[0]==quantize(v)


def test_charge_polarity():
    for v in [-.49,-.125,0,.183,.49]:
        for d in range(256):
            p,n=top_plates(v,d)
            assert p-n==pytest.approx(-.5+d/256-v,abs=1e-14)


def test_quantization_error():
    v=np.linspace(-.5,.5,20001)
    assert np.max(np.abs(reconstruct(quantize(v))-v))<=LSB/2+1e-15
    with pytest.raises(ValueError):quantize(float('nan'))


def test_static_metric_known_errors():
    t=transitions();m=static_metrics(t)
    assert m['max_abs_dnl_lsb']<1e-12 and m['max_abs_inl_lsb']<1e-12
    offset=t+2*LSB
    assert static_metrics(offset)['offset_lsb']==pytest.approx(2)
    t[100]=t[99]
    assert static_metrics(t)['missing_interior_codes']==1


def test_fft_known_harmonic_and_quantizer():
    n=np.arange(4096);k=41
    x=.45*np.sin(2*np.pi*k*n/4096)+.0045*np.sin(2*np.pi*2*k*n/4096)
    m=spectral_metrics(x,100000,k)
    assert m['thd_db']==pytest.approx(-40,abs=.01)
    assert m['sinad_db']==pytest.approx(40,abs=.01)
    ideal=spectral_metrics(reconstruct(quantize(.472*np.sin(2*np.pi*k*n/4096))),100000,k)
    assert 7.7<ideal['enob']<8.1
