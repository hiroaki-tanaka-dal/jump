from dataclasses import dataclass


@dataclass
class MangaEntry:
    title: str
    start_page: int
    end_page: int | None = None

    @property
    def page_count(self) -> int | None:
        if self.end_page is None:
            return None

        return self.end_page - self.start_page + 1