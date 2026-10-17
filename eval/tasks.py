"""Fixed, seeded task sets. Versioned by TASKSET_VERSION; change it when tasks change."""
import random
from caa.core.schemas import Task

TASKSET_VERSION = "v1"
RULES = [("zorb", "glim", 4), ("vex", "mool", 7), ("krin", "plod", 3), ("tavo", "sed", 9),
         ("brel", "nax", 5), ("quo", "fid", 6), ("jem", "tarn", 8), ("lorn", "pek", 2),
         ("wix", "dorm", 11), ("sael", "boun", 12)]


def _q(x, y, n, k, tt):
    return Task(intent=f"How many {y} in {k} {x}?", task_type=tt,
                meta={"expected": str(k * n), "feedback": f"1 {x} = {n} {y}"})


def build_tasks(seed: int = 7):
    rng = random.Random(seed)
    train = [_q(x, y, n, rng.randint(2, 9), "train") for x, y, n in RULES]
    test = [_q(x, y, n, k, "transfer") for x, y, n in RULES for k in rng.sample(range(10, 40), 3)]
    control = []
    for _ in range(10):
        a, b = rng.randint(1, 99), rng.randint(1, 99)
        control.append(Task(intent=f"What is {a} plus {b}?", task_type="control",
                            meta={"expected": str(a + b)}))
    return train, test, control
