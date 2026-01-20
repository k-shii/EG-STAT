from egstat.solver import design_candidates


def test_design_candidates_returns_some():
    cands = design_candidates(
        target_power_kw=120,
        target_power_rpm=6500,
        redline_rpm=7000,
        profile="balanced",
        disp_min_cc=1500,
        disp_max_cc=3000,
        disp_step_cc=250,
        cylinders_list=[4, 6],
        bmep_max_kpa=2000,
        piston_speed_max_mps=30,
        top_n=5,
    )
    assert len(cands) > 0
    assert cands[0].score <= cands[-1].score


def test_design_candidates_impossible_returns_empty():
    cands = design_candidates(
        target_power_kw=300,            # high target
        target_power_rpm=6500,
        redline_rpm=7000,
        profile="balanced",
        disp_min_cc=1000,
        disp_max_cc=2000,
        disp_step_cc=250,
        cylinders_list=[3, 4],
        bmep_max_kpa=900,               # very strict
        piston_speed_max_mps=15,        # very strict
        top_n=5,
    )
    assert cands == []
