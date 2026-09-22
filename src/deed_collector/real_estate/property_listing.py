from dataclasses import dataclass

from deed_collector.real_estate.market import MarketType
from deed_collector.real_estate.providers import Provider


@dataclass(frozen=True, slots=True)
class PropertyListing:
    # TODO pydantic? would allow some nice validation, for now let's keep it as-is
    provider: Provider
    url: str
    address: str
    price: float  # PLN
    area: float  # m²
    number_of_rooms: int
    year_of_construction: int | None
    market_type: MarketType

    @property
    def price_per_square_meter(self) -> float:
        return self.price / self.area

    def to_sheet_row(self) -> list[str | float | int]:
        """Converts the dataclass instance into a row suitable for Sheet-like software."""
        return [
            self.provider,
            self.url,
            self.address,
            self.price,
            self.area,
            self.number_of_rooms,
            self.year_of_construction if self.year_of_construction is not None else "",
            self.market_type,
        ]
