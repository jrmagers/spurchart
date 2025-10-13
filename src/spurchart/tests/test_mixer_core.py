import spurchart.mixer.core


def test_mixer_products():
    products = spurchart.mixer.core.mixer_products(2, 2)

    target = {
        (-2, 1),
        (-2, 2),
        (-1, 1),
        (-1, 2),
        (0, 1),
        (0, 2),
        (1, -2),
        (1, -1),
        (1, 0),
        (1, 1),
        (1, 2),
        (2, -2),
        (2, -1),
        (2, 0),
        (2, 1),
        (2, 2),
    }

    assert target == set(products)
