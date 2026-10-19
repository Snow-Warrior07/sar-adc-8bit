from dataclasses import asdict
import numpy as np
from model.analog_frontend import AnalogConfig,AnalogFrontEnd,RTLAnalogAdapter
from model.ideal_adc import quantize
from tb.bridge import Bridge
from tools.common import phase,save


def run():
    values=np.random.default_rng(923).uniform(-.49,.49,1000)
    ideal=AnalogFrontEnd(AnalogConfig.ideal());nominal=AnalogFrontEnd()
    ideal_bad=0;errors=[]
    with Bridge() as b:
        b.reset()
        for vin in values:
            result,_,_=b.convert(float(vin),RTLAnalogAdapter(ideal,float(vin)))
            ideal_bad+=int(result!=quantize(vin));b.step()
            result,_,_=b.convert(float(vin),RTLAnalogAdapter(nominal,float(vin)))
            errors.append(int(result)-quantize(vin));b.step()
    save('config/nominal.json',asdict(nominal.config))
    return phase(4,'Behavioural analog model with actual RTL',[
        {'name':'all imperfections disabled: exact RTL equivalence','passed':ideal_bad==0,'conversions':1000,'mismatches':ideal_bad},
        {'name':'nominal combined analog model','passed':max(map(abs,errors))<=1,'conversions':1000,'max_code_difference':max(map(abs,errors))},
        {'name':'no late comparator decisions','passed':nominal.timeouts==0,'timeouts':nominal.timeouts}],
        {'nominal_code_error_histogram':{str(x):errors.count(x) for x in sorted(set(errors))},'fidelity':nominal.config.fidelity})


if __name__=='__main__':run()
