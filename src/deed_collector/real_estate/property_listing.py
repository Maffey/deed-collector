from dataclasses import dataclass
from datetime import UTC, date, datetime

from deed_collector.real_estate.market import MarketType
from deed_collector.real_estate.providers import Provider


@dataclass(frozen=True, slots=True)
class PropertyListing:
    provider: Provider
    url: str
    address: str
    price: float  # PLN
    area: float  # m²
    number_of_rooms: int
    year_of_construction: int | None
    market_type: MarketType
    comment: str = ""

    @property
    def price_per_square_meter(self) -> float | None:
        # Listings sometimes omit the area; guard the division and let the
        # sheet client write an empty cell instead of crashing on ZeroDivision.
        if self.area <= 0:
            return None
        return self.price / self.area

    @property
    def collected_date(self) -> date:
        """Date when the listing got scrapped."""
        # A bare calendar date carries no timezone, so derive today's date in
        # the machine's local timezone instead of assuming UTC.
        return datetime.now(UTC).astimezone().date()
