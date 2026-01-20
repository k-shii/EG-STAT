from egstat.curves import normalized_profile, list_profiles


def test_profiles_exist():
    profiles = list_profiles()
    assert "balanced" in profiles
    assert "torque_biased" in profiles
    assert "top_end" in profiles


def test_normalized_in_range():
    for prof in list_profiles():
        for x in [0.0, 0.2, 0.5, 0.8, 1.0]:
            y = normalized_profile(prof, x)
            assert 0.0 <= y <= 1.0
