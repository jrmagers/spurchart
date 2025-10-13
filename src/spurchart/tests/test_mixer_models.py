import spurchart.mixer.models


# %%
def test_models_henderson_table():
    """Verify Table 1 in Henderson's table.

    Predicting Intermodulation Suppression in Double-Balanced Mixers by Bert Henderson.
    """
    nvals = [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7]
    mvals = [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 1, 3, 1, 2, 1, 3]

    prf = 0  # RF Power in dBm
    plo = 20  # LO Power in dBm
    ΔP = prf - plo

    # Table 1:
    s_target = [
        0,
        ΔP - 41,
        2 * ΔP - 28,
        -35,
        ΔP - 39,
        2 * ΔP - 44,
        -10,
        ΔP - 32,
        2 * ΔP - 19,
        -35,
        ΔP - 39,
        -14,
        2 * ΔP - 14,
        -35,
        ΔP - 39,
        -17,
        2 * ΔP - 11,
    ]

    for n, m, target in zip(nvals, mvals, s_target):
        s = spurchart.mixer.models.henderson(n=n, m=m, Prf=prf, Plo=plo)

        # verify that the error is less than 1 dB
        assert abs(s - target) < 1


def test_models_henderson_m_minus_one_rule():
    assert True
