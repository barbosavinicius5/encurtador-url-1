"""Value Object para validação da descrição de projeto."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectDescription:
    """Value Object imutável para descrição de projeto (opcional, máx 500 chars)."""

    value: str | None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.value is not None and len(self.value) > 500:
            raise ValueError("Descrição do projeto não pode exceder 500 caracteres")

    def __str__(self) -> str:
        return self.value or ""
