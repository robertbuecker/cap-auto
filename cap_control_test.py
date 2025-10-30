from cap_auto.cap_control import CAPControl, CAPInstance

def test_cap_control():
    cap = CAPControl()
    assert cap is not None

def test_cap_instance():
    cap_instance = CAPInstance()
    assert cap_instance is not None