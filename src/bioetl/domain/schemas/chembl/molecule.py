"""Pandera schema for ChEMBL molecule data."""
import pandera as pa
from pandera.typing import Series

from bioetl.domain.transform.normalizers import CHEMBL_ID_REGEX

OUTPUT_COLUMN_ORDER: list[str] = [
    "atc_classifications",
    "availability_type",
    "black_box_warning",
    "chemical_probe",
    "chirality",
    "cross_references",
    "dosed_ingredient",
    "first_approval",
    "first_in_class",
    "helm_notation",
    "inorganic_flag",
    "max_phase",
    "molecule_chembl_id",
    "molecule_hierarchy",
    "molecule_properties",
    "molecule_structures",
    "molecule_synonyms",
    "molecule_type",
    "natural_product",
    "oral",
    "orphan",
    "parenteral",
    "polymer_flag",
    "pref_name",
    "prodrug",
    "structure_type",
    "therapeutic_flag",
    "topical",
    "usan_stem",
    "usan_stem_definition",
    "usan_substem",
    "usan_year",
    "veterinary",
    "withdrawn_flag",
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "extracted_at",
]


class MoleculeSchema(pa.DataFrameModel):
    """Schema for molecule data."""
    atc_classifications: Series[str] = pa.Field(
        nullable=True, description="ATC-коды и описания"
    )
    availability_type: Series[float] = pa.Field(
        nullable=True, description="Тип доступности (0/1/2)"
    )
    black_box_warning: Series[float] = pa.Field(
        nullable=True, description="Флаг наличия black box warning"
    )
    chemical_probe: Series[float] = pa.Field(
        nullable=True, description="Флаг chemical probe"
    )
    chirality: Series[float] = pa.Field(
        nullable=True, description="Код хиральности"
    )
    cross_references: Series[str] = pa.Field(
        nullable=True, description="Внешние кросс-референсы"
    )
    dosed_ingredient: Series[bool] = pa.Field(
        nullable=True, description="Используется как дозируемый ингредиент"
    )
    first_approval: Series[float] = pa.Field(
        nullable=True, description="Год первого одобрения"
    )
    first_in_class: Series[float] = pa.Field(
        nullable=True, description="Флаг «первый в классе»"
    )
    helm_notation: Series[str] = pa.Field(
        nullable=True, description="HELM-нотация"
    )
    inorganic_flag: Series[float] = pa.Field(
        nullable=True, description="Флаг неорганического соединения"
    )
    max_phase: Series[float] = pa.Field(
        nullable=True, ge=0, le=4, description="Максимальная фаза клинических исследований"
    )
    molecule_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_REGEX.pattern, description="ChEMBL ID молекулы"
    )
    molecule_hierarchy: Series[str] = pa.Field(
        nullable=True, description="Иерархия молекулы"
    )
    molecule_properties: Series[str] = pa.Field(
        nullable=True, description="Физико-химические свойства молекулы"
    )
    molecule_structures: Series[str] = pa.Field(
        nullable=True, description="Структурные представления молекулы"
    )
    molecule_synonyms: Series[str] = pa.Field(
        nullable=True, description="Синонимы молекулы"
    )
    molecule_type: Series[str] = pa.Field(
        nullable=True, description="Тип молекулы (Small molecule, Protein, etc.)"
    )
    natural_product: Series[float] = pa.Field(
        nullable=True, description="Флаг природного происхождения"
    )
    oral: Series[bool] = pa.Field(
        nullable=True, description="Оральное применение"
    )
    orphan: Series[float] = pa.Field(
        nullable=True, description="Orphan-drug статус"
    )
    parenteral: Series[bool] = pa.Field(
        nullable=True, description="Парентеральное применение"
    )
    polymer_flag: Series[float] = pa.Field(
        nullable=True, description="Флаг полимерной природы"
    )
    pref_name: Series[str] = pa.Field(
        nullable=True, description="Предпочтительное название молекулы"
    )
    prodrug: Series[float] = pa.Field(
        nullable=True, description="Флаг «пролекарство»"
    )
    structure_type: Series[str] = pa.Field(
        nullable=True, description="Тип структурного представления"
    )
    therapeutic_flag: Series[bool] = pa.Field(
        nullable=True, description="Является терапевтическим агентом"
    )
    topical: Series[bool] = pa.Field(
        nullable=True, description="Наружное применение"
    )
    usan_stem: Series[str] = pa.Field(
        nullable=True, description="USAN stem"
    )
    usan_stem_definition: Series[str] = pa.Field(
        nullable=True, description="Определение USAN stem"
    )
    usan_substem: Series[str] = pa.Field(
        nullable=True, description="USAN substem"
    )
    usan_year: Series[float] = pa.Field(
        nullable=True, description="Год присвоения USAN"
    )
    veterinary: Series[float] = pa.Field(
        nullable=True, description="Флаг ветеринарного применения"
    )
    withdrawn_flag: Series[bool] = pa.Field(
        nullable=True, description="Снят ли с рынка"
    )

    # Generated columns
    hash_row: Series[str] = pa.Field(
        str_matches=r"^[a-f0-9]{64}$", description="Хэш всей строки (64 hex)"
    )
    hash_business_key: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^[a-f0-9]{64}$",
        description="Хэш бизнес-ключа",
    )
    index: Series[int] = pa.Field(ge=0, description="Порядковый номер строки")
    database_version: Series[str] = pa.Field(nullable=True, description="Версия базы данных")
    extracted_at: Series[str] = pa.Field(nullable=True, description="Дата и время извлечения")

    class Config:
        """Pandera configuration."""
        strict = True
        coerce = True
        ordered = True

