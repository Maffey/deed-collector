from deed_collector.scaper.otodom import OtodomScraper
from deed_collector.scaper.scraper_factory import ScraperFactory


def main() -> None:
    # TODO something better than argparse?
    url = "https://www.otodom.pl/pl/oferta/wykonczony-dom-ogrod-98m-przy-lesie-bez-prowizji-bezposrednio-ID4wx3M"
    scraper = ScraperFactory.get_scraper(url)
    property_listing = scraper.run()
    print(property_listing)


if __name__ == '__main__':
    main()