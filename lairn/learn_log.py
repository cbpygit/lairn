import json
import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, root_validator


def preprocess_text_field(text):
    # Escape unescaped quotation marks
    text = re.sub(r'(?<!\\)"', r'\\"', text)
    # Escape newlines and tabs
    text = text.replace("\n", "\\n").replace("\t", "\\t")
    return text


def custom_json_decoder(json_str):
    # Extract the "text" field
    text_match = re.search(r'"text":\s*"(.*)"(?=\s*})', json_str, re.DOTALL)
    if text_match:
        text_value = text_match.group(1)
        # Preprocess the "text" field
        fixed_text = preprocess_text_field(text_value)
        # Replace the original text with the fixed text in the JSON string
        json_str = json_str.replace(text_value, fixed_text)

    # print(json_str)
    return json.loads(json_str, strict=False)


class LearnLogMessage(BaseModel):
    user: str = Field(description="The user who created the message")
    timestamp: datetime = Field(description="The timestamp of the message")
    text: str = Field(description="The text of the message")

    @root_validator(pre=True)
    def transform_keys(cls, values):
        # Transform the keys to match the model's fields
        if "User" in values:
            values["user"] = values.pop("User")
        return values

    @classmethod
    def from_json_file(cls, file_path: Path) -> "LearnLogMessage":
        with open(file_path, "r", encoding="utf-8") as f:
            content = custom_json_decoder(f.read())
            return cls.model_validate(content)

    def str_fmt(self) -> str:
        return f"""
### Log Message

#### Time when log was created:
{self.timestamp.isoformat()}

#### Message text:
{self.text}
"""


def load_logs(path: Path) -> list[LearnLogMessage]:
    if not isinstance(path, Path):
        path = Path(path)

    logs = []
    for file in path.glob("*.json"):
        logs.append(LearnLogMessage.from_json_file(file))
    return logs
