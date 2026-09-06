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
    serial_confirmed: bool = False
    serial_reason: str | None = None


def _state_path(output_root: Path) -> Path:
    return output_root / STATE_DIR / STATE_FILE


def _load_state(output_root: Path) -> dict:
    path = _state_path(output_root)

    if not path.exists():
        return {"version": 2, "works": {}}

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"PDF履歴ファイルの形式が不正です: {path}")

    data.setdefault("version", 2)
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

    serial_confirmed = max_issue_number >= 2

    return WorkHistory(
        cumulative_issue_count=max_issue_number,
        seen_issues=(),
        last_issue=last_issue,
        serial_confirmed=serial_confirmed,
        serial_reason=(
            "existing_pdf"
            if serial_confirmed
            else None
        ),
    )


def update_work_history(
    output_root: Path,
    work_title: str,
    current_issues: list[str],
    *,
    serial_signal: bool = False,
) -> WorkHistory:
    """
    作品の累計掲載話数と連載判定履歴を更新する。

    連載判定は一度確定したら保持する。
    - 累計2話以上: 連載確定
    - 累計1話でも serial_signal=True: 新連載として確定
      （現在は初回号に color + main が両方ある場合に使う）
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
            cumulative = len(current_issues)
        elif (
            current_issues
            and inferred.last_issue
            and inferred.last_issue not in current_issues
        ):
            cumulative = inferred_count + len(current_issues)
        else:
            cumulative = max(
                inferred_count,
                len(current_issues),
            )

        seen_issues = set(current_issues)
        serial_confirmed = inferred.serial_confirmed
        serial_reason = inferred.serial_reason
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
        serial_confirmed = bool(
            stored.get("serial_confirmed", False)
        )
        serial_reason = stored.get("serial_reason")

    if cumulative >= 2:
        serial_confirmed = True
        if serial_reason is None:
            serial_reason = "multiple_issues"
    elif serial_signal and not serial_confirmed:
        serial_confirmed = True
        serial_reason = "first_issue_color_and_main"

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
        "serial_confirmed": serial_confirmed,
        "serial_reason": serial_reason,
    }
    state["version"] = 2
    _save_state(output_root, state)

    return WorkHistory(
        cumulative_issue_count=cumulative,
        seen_issues=tuple(sorted(seen_issues)),
        last_issue=last_issue,
        serial_confirmed=serial_confirmed,
        serial_reason=serial_reason,
    )
