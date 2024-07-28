from hashlib import sha256
from pathlib import Path

# from langchain_core.pydantic_v1 import BaseModel, Field
from pydantic import BaseModel, Field


class LearnLogArtifact(BaseModel):
    date: str = Field(
        description="The date this artifact relates to. Depending on context, either a date when learning "
        "activities took place, or the date when a certificate or similar was issued. Use ISO 8601 format."
    )
    school_subject: str | None = Field(description="The school subject this artifact relates to, if any.")
    tags: list[str] = Field(description="Tags that describe this artifact.")
    content: str = Field(description="The content of the artifact.")

    @property
    def identifier(self) -> str:
        """Return identifier composed of date, subject and SHA256 hash of content."""
        content_hash = sha256(self.content.encode()).hexdigest()[:8]
        return f"{self.date}_{self.school_subject}_{content_hash}"

    def str_format(self) -> str:
        return f"""
## {self.date} - {self.school_subject}

Tags: {", ".join(self.tags)}

{self.content.strip()}
"""


def load_artifacts(path: Path, must_include_tags: list[str] | None = None) -> list[LearnLogArtifact]:
    if not isinstance(path, Path):
        path = Path(path)

    artifacts = []
    for file in path.glob("*.json"):
        with open(file, "r") as f:
            artifact = LearnLogArtifact.model_validate_json(f.read())

        if must_include_tags is not None:
            if not all(tag in artifact.tags for tag in must_include_tags):
                continue

        artifacts.append(artifact)
    return artifacts


def load_evaluations(path: Path, class_level: int = 1) -> dict[str, LearnLogArtifact]:
    artifacts = load_artifacts(path, must_include_tags=["Zeugnis", f"Klasse {class_level}"])
    return {artifact.school_subject: artifact for artifact in artifacts}
