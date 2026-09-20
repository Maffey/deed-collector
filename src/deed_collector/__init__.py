from deed_collector.scaper.otodom import OtodomScraper


def main() -> None:
    url = "https://www.otodom.pl/pl/oferta/wykonczony-dom-ogrod-98m-przy-lesie-bez-prowizji-bezposrednio-ID4wx3M"
    scraper = OtodomScraper()
    scraper.run(url)


if __name__ == '__main__':
    main()