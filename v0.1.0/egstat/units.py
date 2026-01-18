from __future__ import annotations

# Core conversions used across EG-Stat.
# Internal calculations should use SI units:
# - power: W
# - torque: N*m
# - pressure: Pa
# - volume: m^3


HP_TO_W = 745.6998715822702  # mechanical horsepower (hp) to watts
LBFT_TO_NM = 1.3558179483314004
PSI_TO_PA = 6894.757293168
L_TO_M3 = 1e-3
CC_TO_M3 = 1e-6


def kw_to_hp(kw: float) -> float:
    return (kw * 1000.0) / HP_TO_W


def hp_to_kw(hp: float) -> float:
    return (hp * HP_TO_W) / 1000.0


def nm_to_lbft(nm: float) -> float:
    return nm / LBFT_TO_NM


def lbft_to_nm(lbft: float) -> float:
    return lbft * LBFT_TO_NM


def psi_to_kpa(psi: float) -> float:
    return (psi * PSI_TO_PA) / 1000.0


def kpa_to_psi(kpa: float) -> float:
    return (kpa * 1000.0) / PSI_TO_PA


def l_to_m3(liters: float) -> float:
    return liters * L_TO_M3


def m3_to_l(m3: float) -> float:
    return m3 / L_TO_M3


def cc_to_m3(cc: float) -> float:
    return cc * CC_TO_M3


def m3_to_cc(m3: float) -> float:
    return m3 / CC_TO_M3


def mm_to_m(mm: float) -> float:
    return mm / 1000.0


def m_to_mm(m: float) -> float:
    return m * 1000.0
