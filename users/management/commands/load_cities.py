# users/management/commands/load_cities.py
from django.core.management.base import BaseCommand

from users.models import City


class Command(BaseCommand):
    help = "Загрузка городов США, Канады и Европы на их родных языках"

    def handle(self, *args, **options):
        cities_data = [
            # США (English)
            ("New York", "New York", "USA"),
            ("Los Angeles", "California", "USA"),
            ("Chicago", "Illinois", "USA"),
            ("Houston", "Texas", "USA"),
            ("Phoenix", "Arizona", "USA"),
            ("Philadelphia", "Pennsylvania", "USA"),
            ("San Antonio", "Texas", "USA"),
            ("San Diego", "California", "USA"),
            ("Dallas", "Texas", "USA"),
            ("San Jose", "California", "USA"),
            ("Austin", "Texas", "USA"),
            ("Jacksonville", "Florida", "USA"),
            ("Fort Worth", "Texas", "USA"),
            ("Columbus", "Ohio", "USA"),
            ("Charlotte", "North Carolina", "USA"),
            ("San Francisco", "California", "USA"),
            ("Indianapolis", "Indiana", "USA"),
            ("Seattle", "Washington", "USA"),
            ("Denver", "Colorado", "USA"),
            ("Washington", "District of Columbia", "USA"),
            ("Boston", "Massachusetts", "USA"),
            ("El Paso", "Texas", "USA"),
            ("Nashville", "Tennessee", "USA"),
            ("Detroit", "Michigan", "USA"),
            ("Portland", "Oregon", "USA"),
            # Канада (English and French)
            ("Toronto", "Ontario", "Canada"),
            ("Montreal", "Quebec", "Canada"),
            ("Vancouver", "British Columbia", "Canada"),
            ("Calgary", "Alberta", "Canada"),
            ("Edmonton", "Alberta", "Canada"),
            ("Ottawa", "Ontario", "Canada"),
            ("Winnipeg", "Manitoba", "Canada"),
            ("Québec", "Quebec", "Canada"),
            ("Hamilton", "Ontario", "Canada"),
            ("Halifax", "Nova Scotia", "Canada"),
            ("London", "Ontario", "Canada"),
            ("Victoria", "British Columbia", "Canada"),
            ("Windsor", "Ontario", "Canada"),
            ("Saskatoon", "Saskatchewan", "Canada"),
            ("Regina", "Saskatchewan", "Canada"),
            # Великобритания (English)
            ("London", "England", "United Kingdom"),
            ("Birmingham", "England", "United Kingdom"),
            ("Manchester", "England", "United Kingdom"),
            ("Glasgow", "Scotland", "United Kingdom"),
            ("Liverpool", "England", "United Kingdom"),
            ("Edinburgh", "Scotland", "United Kingdom"),
            ("Leeds", "England", "United Kingdom"),
            ("Bristol", "England", "United Kingdom"),
            ("Sheffield", "England", "United Kingdom"),
            ("Newcastle upon Tyne", "England", "United Kingdom"),
            # Германия (German)
            ("Berlin", "Berlin", "Germany"),
            ("Hamburg", "Hamburg", "Germany"),
            ("München", "Bavaria", "Germany"),
            ("Köln", "North Rhine-Westphalia", "Germany"),
            ("Frankfurt am Main", "Hesse", "Germany"),
            ("Stuttgart", "Baden-Württemberg", "Germany"),
            ("Düsseldorf", "North Rhine-Westphalia", "Germany"),
            ("Dortmund", "North Rhine-Westphalia", "Germany"),
            ("Essen", "North Rhine-Westphalia", "Germany"),
            ("Leipzig", "Saxony", "Germany"),
            # Франция (French)
            ("Paris", "Île-de-France", "France"),
            ("Marseille", "Provence-Alpes-Côte d'Azur", "France"),
            ("Lyon", "Auvergne-Rhône-Alpes", "France"),
            ("Toulouse", "Occitanie", "France"),
            ("Nice", "Provence-Alpes-Côte d'Azur", "France"),
            ("Nantes", "Pays de la Loire", "France"),
            ("Strasbourg", "Grand Est", "France"),
            ("Montpellier", "Occitanie", "France"),
            ("Bordeaux", "Nouvelle-Aquitaine", "France"),
            ("Lille", "Hauts-de-France", "France"),
            # Италия (Italian)
            ("Roma", "Lazio", "Italy"),
            ("Milano", "Lombardy", "Italy"),
            ("Napoli", "Campania", "Italy"),
            ("Torino", "Piedmont", "Italy"),
            ("Palermo", "Sicily", "Italy"),
            ("Genova", "Liguria", "Italy"),
            ("Bologna", "Emilia-Romagna", "Italy"),
            ("Firenze", "Tuscany", "Italy"),
            ("Venezia", "Veneto", "Italy"),
            ("Verona", "Veneto", "Italy"),
            # Испания (Spanish)
            ("Madrid", "Community of Madrid", "Spain"),
            ("Barcelona", "Catalonia", "Spain"),
            ("Valencia", "Valencian Community", "Spain"),
            ("Sevilla", "Andalusia", "Spain"),
            ("Zaragoza", "Aragon", "Spain"),
            ("Málaga", "Andalusia", "Spain"),
            ("Murcia", "Region of Murcia", "Spain"),
            ("Palma de Mallorca", "Balearic Islands", "Spain"),
            ("Las Palmas de Gran Canaria", "Canary Islands", "Spain"),
            ("Bilbao", "Basque Country", "Spain"),
            # Нидерланды (Dutch)
            ("Amsterdam", "North Holland", "Netherlands"),
            ("Rotterdam", "South Holland", "Netherlands"),
            ("Den Haag", "South Holland", "Netherlands"),
            ("Utrecht", "Utrecht", "Netherlands"),
            ("Eindhoven", "North Brabant", "Netherlands"),
            ("Groningen", "Groningen", "Netherlands"),
            ("Leiden", "South Holland", "Netherlands"),
            ("Maastricht", "Limburg", "Netherlands"),
            ("Haarlem", "North Holland", "Netherlands"),
            ("Delft", "South Holland", "Netherlands"),
            # Бельгия (Dutch/French)
            ("Brussel", "Brussels-Capital Region", "Belgium"),
            ("Antwerpen", "Flanders", "Belgium"),
            ("Gent", "Flanders", "Belgium"),
            ("Charleroi", "Wallonia", "Belgium"),
            ("Liège", "Wallonia", "Belgium"),
            ("Brugge", "Flanders", "Belgium"),
            # Швейцария (German/French/Italian)
            ("Zürich", "Zurich", "Switzerland"),
            ("Genève", "Geneva", "Switzerland"),
            ("Basel", "Basel-Stadt", "Switzerland"),
            ("Lausanne", "Vaud", "Switzerland"),
            ("Bern", "Bern", "Switzerland"),
            ("Luzern", "Lucerne", "Switzerland"),
            # Австрия (German)
            ("Wien", "Vienna", "Austria"),
            ("Graz", "Styria", "Austria"),
            ("Linz", "Upper Austria", "Austria"),
            ("Salzburg", "Salzburg", "Austria"),
            ("Innsbruck", "Tyrol", "Austria"),
            # Швеция (Swedish)
            ("Stockholm", "Stockholm County", "Sweden"),
            ("Göteborg", "Västra Götaland", "Sweden"),
            ("Malmö", "Skåne", "Sweden"),
            ("Uppsala", "Uppsala County", "Sweden"),
            ("Linköping", "Östergötland", "Sweden"),
            # Норвегия (Norwegian)
            ("Oslo", "Oslo", "Norway"),
            ("Bergen", "Vestland", "Norway"),
            ("Stavanger", "Rogaland", "Norway"),
            ("Trondheim", "Trøndelag", "Norway"),
            ("Drammen", "Viken", "Norway"),
            # Дания (Danish)
            ("København", "Capital Region", "Denmark"),
            ("Aarhus", "Central Denmark Region", "Denmark"),
            ("Odense", "Region of Southern Denmark", "Denmark"),
            ("Aalborg", "North Denmark Region", "Denmark"),
            ("Esbjerg", "Region of Southern Denmark", "Denmark"),
            # Финляндия (Finnish)
            ("Helsinki", "Uusimaa", "Finland"),
            ("Espoo", "Uusimaa", "Finland"),
            ("Tampere", "Pirkanmaa", "Finland"),
            ("Vantaa", "Uusimaa", "Finland"),
            ("Turku", "Southwest Finland", "Finland"),
            # Португалия (Portuguese)
            ("Lisboa", "Lisbon", "Portugal"),
            ("Porto", "Porto", "Portugal"),
            ("Braga", "Braga", "Portugal"),
            ("Coimbra", "Coimbra", "Portugal"),
            ("Faro", "Faro", "Portugal"),
            # Ирландия (English/Irish)
            ("Dublin", "Leinster", "Ireland"),
            ("Cork", "Munster", "Ireland"),
            ("Limerick", "Munster", "Ireland"),
            ("Galway", "Connacht", "Ireland"),
            ("Waterford", "Munster", "Ireland"),
            # Польша (Polish)
            ("Warszawa", "Masovian", "Poland"),
            ("Kraków", "Lesser Poland", "Poland"),
            ("Łódź", "Łódź", "Poland"),
            ("Wrocław", "Lower Silesian", "Poland"),
            ("Poznań", "Greater Poland", "Poland"),
            # Чехия (Czech)
            ("Praha", "Prague", "Czech Republic"),
            ("Brno", "South Moravian", "Czech Republic"),
            ("Ostrava", "Moravian-Silesian", "Czech Republic"),
            ("Plzeň", "Plzeň", "Czech Republic"),
            ("Liberec", "Liberec", "Czech Republic"),
            # Венгрия (Hungarian)
            ("Budapest", "Budapest", "Hungary"),
            ("Debrecen", "Hajdú-Bihar", "Hungary"),
            ("Szeged", "Csongrád-Csanád", "Hungary"),
            ("Miskolc", "Borsod-Abaúj-Zemplén", "Hungary"),
            ("Pécs", "Baranya", "Hungary"),
            # Греция (Greek - written in Latin script for simplicity)
            ("Athens", "Attica", "Greece"),
            ("Thessaloniki", "Central Macedonia", "Greece"),
            ("Patras", "Western Greece", "Greece"),
            ("Heraklion", "Crete", "Greece"),
            ("Larissa", "Thessaly", "Greece"),
        ]

        cities_created = 0
        cities_updated = 0

        for city_name, region, country in cities_data:
            city, created = City.objects.update_or_create(
                name=city_name,
                defaults={"region": region, "country": country, "is_active": True},
            )

            if created:
                cities_created += 1
                self.stdout.write(f"Создан город: {city_name}, {region}, {country}")
            else:
                cities_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Успешно загружено городов: создано {cities_created}, обновлено {cities_updated}"
            )
        )
