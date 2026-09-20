from deed_collector.scraper import ScraperFactory


def main() -> None:
    # TODO something better than argparse?
    url = "https://www.otodom.pl/pl/oferta/wykonczony-dom-ogrod-98m-przy-lesie-bez-prowizji-bezposrednio-ID4wx3M"
    with ScraperFactory.create(url) as scraper:
        property_listing = scraper.run(url)
    print(property_listing)


if __name__ == "__main__":
    main()
