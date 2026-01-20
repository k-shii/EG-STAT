from egstat import units


def test_power_roundtrip():
    kw = 100.0
    hp = units.kw_to_hp(kw)
    kw2 = units.hp_to_kw(hp)
    assert abs(kw2 - kw) < 1e-9


def test_torque_roundtrip():
    nm = 200.0
    lbft = units.nm_to_lbft(nm)
    nm2 = units.lbft_to_nm(lbft)
    assert abs(nm2 - nm) < 1e-9


def test_pressure_roundtrip():
    psi = 14.7
    kpa = units.psi_to_kpa(psi)
    psi2 = units.kpa_to_psi(kpa)
    assert abs(psi2 - psi) < 1e-9


def test_volume_roundtrip():
    cc = 1998.0
    m3 = units.cc_to_m3(cc)
    cc2 = units.m3_to_cc(m3)
    assert abs(cc2 - cc) < 1e-9
