class ResolvedParams:
    """
    Merged parameter set produced by the ParameterResolver after all three sub-layers.
    Holds both request-level and chat-driven params, plus any recorded issues.
    """

    def __init__(self) -> None:
        self._values: dict[str, object] = {}
        self._issues: list[str] = []

    def put(self, name: str, value: object) -> None:
        self._values[name] = value

    def get(self, name: str) -> object | None:
        return self._values.get(name)

    def get_str(self, name: str) -> str | None:
        v = self._values.get(name)
        return str(v) if v is not None else None

    def has(self, name: str) -> bool:
        return name in self._values and self._values[name] is not None

    def record_issue(self, issue: str) -> None:
        self._issues.append(issue)

    def has_issues(self) -> bool:
        return bool(self._issues)

    def issues_summary(self) -> str:
        return "; ".join(self._issues)

    def all(self) -> dict[str, object]:
        return dict(self._values)
