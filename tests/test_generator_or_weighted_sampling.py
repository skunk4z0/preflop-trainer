import random

from core.generator import _or_hand_weight, _weighted_or_hand_choice


def test_or_hand_weight_rules() -> None:
    assert _or_hand_weight("23o") == 0.2
    assert _or_hand_weight("76o") == 1.0
    assert _or_hand_weight("A2o") == 1.0
    assert _or_hand_weight("22") == 1.0


def test_weighted_or_sampling_biases_away_from_very_weak_offsuit() -> None:
    random.seed(0)
    population = ["23o", "A2o"]
    count_23o = 0
    count_a2o = 0

    for _ in range(1000):
        hand = _weighted_or_hand_choice(population)
        if hand == "23o":
            count_23o += 1
        elif hand == "A2o":
            count_a2o += 1

    assert count_23o < count_a2o * 0.5
