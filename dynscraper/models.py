from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Quote:
    text: str
    author: str
    tags: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["tags"] = list(self.tags)
        return d

    @classmethod
    def from_api(cls, item: dict) -> "Quote":
        return cls(
            text=clean(item["text"]),
            author=item["author"]["name"],
            tags=tuple(item.get("tags", [])),
        )


def clean(text: str) -> str:
    return text.strip().strip('“”"').strip()
