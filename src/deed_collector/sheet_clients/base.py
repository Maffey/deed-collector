from abc import ABC, abstractmethod

from deed_collector.real_estate.property_listing import PropertyListing


class BaseSheetClient(ABC):
    @abstractmethod
    def append_listing(self, listing: PropertyListing) -> None: ...
