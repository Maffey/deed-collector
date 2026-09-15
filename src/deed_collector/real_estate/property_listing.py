import datetime
from dataclasses import dataclass
from functools import cached_property

from deed_collector.real_estate.market import MarketType
from deed_collector.real_estate.providers import Provider


@dataclass(frozen=True, slots=True)
class PropertyListing:
    # TODO pydantic? would allow some nice validation, for now let's keep it as-is
    created_date: datetime.date
    provider: Provider
    url: str
    address: str
    price: float  # PLN
    area: float  # m²
    number_of_rooms: int
    year_of_construction: int
    market_type: MarketType


    @cached_property
    def price_per_square_meter(self):
        return self.price / self.area
