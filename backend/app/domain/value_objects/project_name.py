"""Value Object para validação do nome de projeto."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectName:
    """Value Object imutável para nome de projeto (3-100 caracteres)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        object.__setattr__(self, "value", stripped)
        self._validate()

    def _validate(self) -> None:
        if not self.value:
            raise ValueError("Nome do projeto não pode ser vazio")
        if len(self.value) < 3:
            raise ValueError("Nome do projeto deve ter no mínimo 3 caracteres")
        if len(self.value) > 100:
            raise ValueError("Nome do projeto não pode exceder 100 caracteres")

    def __str__(self) -> str:
        return self.value
