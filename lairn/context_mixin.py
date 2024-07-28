from lairn.common import get_student_age_today
from lairn.config import MAIN_DIR
from lairn.curriculum.load import load_curricula
from lairn.curriculum.models import Curriculum
from lairn.learn_artifact import load_evaluations, LearnLogArtifact, load_artifacts
from lairn.learn_log import LearnLogMessage, load_logs


class ContextMixinClassLevel2:
    CURRICULA_PATH = MAIN_DIR / "Schullehrplan_Grundschule_Zusammenfassungen" / "Schuljahre 1-2" / "pydantic"
    ARTIFACTS_PATH = MAIN_DIR / "artifacts"
    LOGS_PATH = MAIN_DIR / "slack_log_messages"

    @property
    def student_age(self) -> int:
        return get_student_age_today()

    def load_curricula(self) -> dict[str, Curriculum]:
        return load_curricula(self.CURRICULA_PATH)

    def load_evaluations(self) -> dict[str, LearnLogArtifact]:
        return load_evaluations(self.ARTIFACTS_PATH)

    def load_artifacts(self, must_include_tags: list[str] | None = None) -> list[LearnLogArtifact]:
        return load_artifacts(self.ARTIFACTS_PATH, must_include_tags)

    def load_logs(self) -> list[LearnLogMessage]:
        return load_logs(self.LOGS_PATH)

    def load_defaults(
        self,
    ) -> tuple[dict[str, Curriculum], dict[str, LearnLogArtifact], list[LearnLogMessage]]:
        return self.load_curricula(), self.load_evaluations(), self.load_logs()