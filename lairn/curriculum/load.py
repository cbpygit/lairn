from pathlib import Path

from lairn.curriculum.models import Curriculum


def load_curricula(path: Path) -> dict[str, Curriculum]:
    if not isinstance(path, Path):
        path = Path(path)

    curricula = dict()
    for file in path.glob("*.json"):
        with open(file, "r") as f:
            curriculum = Curriculum.model_validate_json(f.read())
        curricula[curriculum.subject] = curriculum
    return curricula
