import json
import re
from dataclasses import dataclass
from pathlib import Path


STATE_DIR = "_state"
STATE_FILE = "works.json"


@dataclass(frozen=True)
class WorkHistory:
    cumulative_issue_count: int
    seen_issues: tuple[str, ...]
    last_issue: str | None


def _state_path(output_root: Path) -> Path:
    return output_root / STATE_DIR / STATE_FILE


def _load_state(output_root: Path) -> dict:
    path = _state_path(output_root)

    if not path.exists():
        return {"version": 1, "works": {}}

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"PDF履歴ファイルの形式が不正です: {path}")

    data.setdefault("version", 1)
    data.setdefault("works", {})
    return data


def _save_state(output_root: Path, data: dict) -> None:
    path = _state_path(output_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        file.write("\n")

    temp.replace(path)


def infer_history_from_existing_pdfs(
    output_root: Path,
    work_title: str,
) -> WorkHistory:
    """既存PDF名から、履歴ファイル導入前の累計話数を推定する。"""

    pattern = re.compile(
        rf"^{re.escape(work_title)}_(\d{{3}})-(\d{{3}})(?:_(.+))?\.pdf$"
    )

    max_issue_number = 0
    last_issue: str | None = None

    if output_root.exists():
        for pdf_file in output_root.rglob("*.pdf"):
            match = pattern.match(pdf_file.name)
            if match is None:
                continue

            end_number = int(match.group(2))
            if end_number >= max_issue_number:
                max_issue_number = end_number
                last_issue = match.group(3)

    return WorkHistory(
        cumulative_issue_count=max_issue_number,
        seen_issues=(),
        last_issue=last_issue,
    )


def update_work_history(
    output_root: Path,
    work_title: str,
    current_issues: list[str],
) -> WorkHistory:
    """
    作品の累計掲載話数を更新する。

    - 通常は、過去に記録済みの号 + 今回初めて見えた号で累計する。
    - 履歴ファイルがまだ無い作品は、既存の集約PDF名から過去話数を復元する。
    - そのため、元画像を整理して現在1号分しか残っていなくても、
      過去に2話以上PDF化済みなら読み切りには戻らない。
    """

    current_issues = sorted(set(current_issues))
    state = _load_state(output_root)
    works = state["works"]
    stored = works.get(work_title)

    if stored is None:
        inferred = infer_history_from_existing_pdfs(
            output_root,
            work_title,
        )
        inferred_count = inferred.cumulative_issue_count

        if inferred_count == 0:
            cumulative = len(current_issues)
        elif len(current_issues) > inferred_count:
            # 過去分を含めて元画像が残っているケース。
            cumulative = len(current_issues)
        elif (
            current_issues
            and inferred.last_issue
            and inferred.last_issue not in current_issues
        ):
            # 過去PDFだけ残し、元画像は新しい号だけ残しているケース。
            cumulative = inferred_count + len(current_issues)
        else:
            cumulative = max(
                inferred_count,
                len(current_issues),
            )

        seen_issues = set(current_issues)
    else:
        cumulative = int(
            stored.get("cumulative_issue_count", 0)
        )
        seen_issues = set(
            stored.get("seen_issues", [])
        )
        new_issues = set(current_issues) - seen_issues
        cumulative += len(new_issues)
        seen_issues.update(current_issues)
        cumulative = max(cumulative, len(seen_issues))

    last_issue = (
        current_issues[-1]
        if current_issues
        else (
            stored.get("last_issue")
            if stored
            else None
        )
    )

    works[work_title] = {
        "cumulative_issue_count": cumulative,
        "seen_issues": sorted(seen_issues),
        "last_issue": last_issue,
    }
    _save_state(output_root, state)

    return WorkHistory(
        cumulative_issue_count=cumulative,
        seen_issues=tuple(sorted(seen_issues)),
        last_issue=last_issue,
    )
