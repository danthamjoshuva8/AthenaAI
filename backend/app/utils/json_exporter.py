import json
from pathlib import Path


class JsonExporter:

    @staticmethod
    def save(data: dict, file_name: str):
        """
        Saves JSON to backend/output/<file_name>.
        Replaces the file if it already exists.
        """

        output_dir = Path("backend/output")
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / file_name

        with file_path.open("w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False,
                default=str
            )

        return file_path