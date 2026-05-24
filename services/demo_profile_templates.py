"""
Шаблоны анкет для демо-пользователей (RU / EN).
Названия компаний в кавычках «…».
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoProfileTemplate:
    language: str
    name: str
    city: str
    short_description: str
    full_description: str
    quality_1: str
    quality_2: str
    quality_3: str
    hustler_percent: int
    hacker_percent: int
    hipster_percent: int
    ethics_score: int
    goals_score: int
    risk_score: int
    decision_score: int
    comm_score: int
    profile_label: str = "Hybrid"

    def qualities_block(self) -> str:
        return f"💼|{self.quality_1}\n🚀|{self.quality_2}\n💻|{self.quality_3}"


RU_TEMPLATES: tuple[DemoProfileTemplate, ...] = (
    DemoProfileTemplate(
        "ru", "Алексей Демо", "Москва",
        "Основатель B2B SaaS: пилот с «Сбер» за 4 месяца, партнёрские продажи через «Яндекс».",
        "10+ лет в digital: маркетплейс с «Ozon», отдел продаж в «Тинькофф». Ищу co-founder в fintech — MVP и клиенты «VK».",
        "Сделки с «Газпром нефть»", "Пилот продукта в «Сбер»", "MVP для «Тинькофф»",
        48, 32, 20, 82, 76, 58, 71, 88,
    ),
    DemoProfileTemplate(
        "ru", "Мария Козлова", "Санкт-Петербург",
        "Product lead: запускала мобильный банкинг в «ВТБ», рост retention в «Avito» на 18%.",
        "7 лет в продукте: roadmap для «СберМаркет», A/B-тесты в «Lamoda». Ищу партнёра на edtech с аудиторией «Skillbox».",
        "Product discovery в «Avito»", "Метрики роста «Lamoda»", "Запуск фичи в «ВТБ»",
        35, 40, 25, 79, 81, 52, 74, 86,
    ),
    DemoProfileTemplate(
        "ru", "Дмитрий Орлов", "Казань",
        "Tech co-founder: микросервисы для «X5 Tech», сократил time-to-market на 30% в «Magnit».",
        "Backend 12 лет: highload в «Ozon», платёжный шлюз для «Тинькофф». Хочу строить logistics SaaS с пилотом «СДЭК».",
        "Архитектура в «X5 Tech»", "Highload «Ozon»", "Интеграция «СДЭК»",
        28, 52, 20, 75, 70, 65, 68, 72,
    ),
    DemoProfileTemplate(
        "ru", "Елена Смирнова", "Новосибирск",
        "Маркетинг B2B: лидоген для «1С», кампании с ROI 300% для «Контур».",
        "8 лет performance: контент для «Skyeng», outbound в «Битрикс24». Ищу co-founder-разработчика под HR-tech с «HeadHunter».",
        "Лиды для «Контур»", "Контент «Skyeng»", "Outbound «Битрикс24»",
        55, 22, 23, 84, 73, 48, 69, 90,
    ),
    DemoProfileTemplate(
        "ru", "Игорь Волков", "Екатеринбург",
        "Операционный директор: масштабировал франшизу «Додо» в регионе, P&L «СберЛогистика».",
        "15 лет ops: процессы в «X5 Retail Group», supply chain «Wildberries». Ищу tech-партнёра на retail SaaS.",
        "Франшиза «Додо»", "P&L «СберЛогистика»", "Supply chain «Wildberries»",
        62, 18, 20, 80, 78, 45, 77, 83,
    ),
    DemoProfileTemplate(
        "ru", "Анна Белова", "Краснодар",
        "UX/UI: редизайн приложения «СберБанк Онлайн», рост NPS в «Яндекс Go».",
        "6 лет design systems: исследования для «Тинькофф», продуктовый дизайн «VK Музыка». Ищу co-founder на health-tech с «DocMed».",
        "Редизайн «СберБанк Онлайн»", "NPS «Яндекс Go»", "Design «VK Музыка»",
        25, 28, 47, 77, 74, 55, 72, 85,
    ),
    DemoProfileTemplate(
        "ru", "Павел Кузнецов", "Ростов-на-Дону",
        "Sales enterprise: закрыл контракты с «Росатом» и «РЖД», pipeline $2M в «Kaspersky».",
        "9 лет B2B sales: аккаунты «Microsoft» в регионе, партнёрка «SAP». Ищу co-founder на cybersecurity с «Positive Technologies».",
        "Контракт «РЖД»", "Pipeline «Kaspersky»", "Аккаунты «Microsoft»",
        58, 25, 17, 81, 79, 50, 73, 87,
    ),
    DemoProfileTemplate(
        "ru", "Ольга Новикова", "Нижний Новгород",
        "Data analyst: дашборды для «МТС», прогноз спроса для «X5» с точностью 92%.",
        "5 лет analytics: ML-модели в «Yandex Cloud», BI для «Сбер». Ищу co-founder на agtech с пилотом «Русагро».",
        "Дашборды «МТС»", "Прогноз «X5»", "ML «Yandex Cloud»",
        30, 48, 22, 76, 82, 60, 70, 74,
    ),
    DemoProfileTemplate(
        "ru", "Сергей Морозов", "Самара",
        "Community & growth: 50k подписчиков для «Т‑Банк» блога, virality в «Telegram» каналах «Сбер».",
        "4 года content-led growth: SMM «VK», community «Ozon». Ищу co-founder на creator economy с «Winline» media.",
        "Growth «Т‑Банк»", "Virality «Telegram»", "Community «Ozon»",
        42, 30, 28, 73, 85, 68, 66, 91,
    ),
    DemoProfileTemplate(
        "ru", "Виктория Лебедева", "Уфа",
        "Legal & compliance: договоры для «Alfa-Bank», GDPR для «Luxoft» клиентов.",
        "11 лет legal tech: M&A support «Сбер», compliance «Yandex». Ищу co-founder на regtech с «ЦБ РФ» sandbox.",
        "Договоры «Alfa-Bank»", "GDPR «Luxoft»", "M&A «Сбер»",
        38, 35, 27, 88, 72, 42, 75, 80,
    ),
    DemoProfileTemplate(
        "ru", "Артём Соколов", "Воронеж",
        "Mobile dev: приложение 4.8★ для «Delivery Club», Flutter в «СберЗдоровье».",
        "7 лет iOS/Android: релизы «Yandex Eats», offline-first для «Magnit». Ищу co-founder на travel с «OneTwoTrip».",
        "App «Delivery Club»", "Flutter «СберЗдоровье»", "Offline «Magnit»",
        22, 55, 23, 74, 77, 63, 67, 78,
    ),
    DemoProfileTemplate(
        "ru", "Наталья Фёдорова", "Тюмень",
        "HR & recruiting: закрыла 40+ позиций в «Gazprom neft», employer brand «Sibur».",
        "8 лет talent: headhunting «McKinsey» alumni, HRIS «1С:ЗУП». Ищу co-founder на HR SaaS с «HeadHunter» API.",
        "Hiring «Gazprom neft»", "Brand «Sibur»", "HRIS «1С»",
        45, 28, 27, 83, 80, 47, 76, 89,
    ),
)

EN_TEMPLATES: tuple[DemoProfileTemplate, ...] = (
    DemoProfileTemplate(
        "en", "James Demo", "London",
        "B2B SaaS founder: pilot with «Stripe» in 3 months, enterprise pipeline via «Google».",
        "8+ years PLG: scaled at «Notion», GTM with «Amazon». Fintech co-founder — MVP, logos from «Microsoft».",
        "Deals with «Salesforce»", "Pilot at «Stripe»", "MVP for «Airbnb»",
        35, 45, 20, 78, 84, 62, 69, 81,
    ),
    DemoProfileTemplate(
        "en", "Emily Carter", "New York",
        "Product lead: launched mobile banking at «Chase», +22% retention at «Uber».",
        "7 years product: roadmap for «Shopify», experiments at «Spotify». Seeking co-founder for edtech with «Coursera» audience.",
        "Discovery at «Uber»", "Growth «Spotify»", "Launch at «Chase»",
        38, 42, 20, 80, 82, 54, 73, 88,
    ),
    DemoProfileTemplate(
        "en", "Michael Chen", "San Francisco",
        "Tech co-founder: microservices for «Netflix», cut time-to-market 30% at «DoorDash».",
        "12 years backend: highload at «Meta», payments for «PayPal». Building logistics SaaS with «FedEx» pilot.",
        "Architecture «Netflix»", "Highload «Meta»", "Integration «FedEx»",
        26, 54, 20, 76, 71, 66, 70, 75,
    ),
    DemoProfileTemplate(
        "en", "Sarah Johnson", "Berlin",
        "B2B marketing: lead gen for «SAP», 300% ROI campaigns for «HubSpot».",
        "8 years performance: content for «Duolingo», outbound at «Slack». Seeking dev co-founder for HR-tech with «LinkedIn».",
        "Leads for «HubSpot»", "Content «Duolingo»", "Outbound «Slack»",
        56, 20, 24, 85, 74, 49, 68, 91,
    ),
    DemoProfileTemplate(
        "en", "David Miller", "Toronto",
        "COO: scaled «Domino's» franchise region, P&L at «Shopify» logistics.",
        "15 years ops: processes at «Walmart», supply chain «Amazon». Seeking tech partner for retail SaaS.",
        "Franchise «Domino's»", "P&L «Shopify»", "Supply chain «Amazon»",
        60, 19, 21, 81, 79, 44, 78, 84,
    ),
    DemoProfileTemplate(
        "en", "Laura Williams", "Austin",
        "UX/UI: redesign for «Apple Wallet», NPS lift at «Lyft».",
        "6 years design systems: research for «Square», product design «Pinterest». Health-tech co-founder with «Teladoc».",
        "Redesign «Apple Wallet»", "NPS «Lyft»", "Design «Pinterest»",
        24, 30, 46, 77, 75, 56, 71, 86,
    ),
    DemoProfileTemplate(
        "en", "Robert Taylor", "Chicago",
        "Enterprise sales: closed «Boeing» and «GE», $2M pipeline at «Oracle».",
        "9 years B2B: «IBM» accounts, «SAP» partnerships. Cybersecurity co-founder with «CrowdStrike».",
        "Contract «Boeing»", "Pipeline «Oracle»", "Accounts «IBM»",
        57, 24, 19, 82, 80, 51, 74, 87,
    ),
    DemoProfileTemplate(
        "en", "Jessica Brown", "Seattle",
        "Data analyst: dashboards for «Verizon», 92% demand forecast for «Target».",
        "5 years analytics: ML at «Google Cloud», BI for «JPMorgan». Agtech co-founder with «Cargill» pilot.",
        "Dashboards «Verizon»", "Forecast «Target»", "ML «Google Cloud»",
        32, 47, 21, 75, 83, 61, 69, 76,
    ),
    DemoProfileTemplate(
        "en", "Chris Anderson", "Miami",
        "Community growth: 50k followers for «Coinbase» blog, virality on «Telegram» for «Binance».",
        "4 years content-led growth: SMM «TikTok», community «Discord». Creator economy with «Twitch» media.",
        "Growth «Coinbase»", "Virality «Telegram»", "Community «Discord»",
        41, 31, 28, 72, 86, 67, 65, 90,
    ),
    DemoProfileTemplate(
        "en", "Amanda Davis", "Dublin",
        "Legal & compliance: contracts for «Stripe», GDPR for «Accenture» clients.",
        "11 years legal tech: M&A «Goldman Sachs», compliance «Meta». Regtech co-founder with «FCA» sandbox.",
        "Contracts «Stripe»", "GDPR «Accenture»", "M&A «Goldman Sachs»",
        37, 36, 27, 89, 73, 41, 76, 81,
    ),
    DemoProfileTemplate(
        "en", "Kevin Wilson", "Denver",
        "Mobile dev: 4.8★ app for «Instacart», Flutter at «Google Health».",
        "7 years iOS/Android: releases «Uber Eats», offline-first «Walmart». Travel co-founder with «Expedia».",
        "App «Instacart»", "Flutter «Google Health»", "Offline «Walmart»",
        21, 56, 23, 73, 78, 64, 66, 77,
    ),
    DemoProfileTemplate(
        "en", "Rachel Martinez", "Boston",
        "HR & recruiting: 40+ hires at «Pfizer», employer brand «Moderna».",
        "8 years talent: «McKinsey» alumni, HRIS «Workday». HR SaaS co-founder with «LinkedIn» API.",
        "Hiring «Pfizer»", "Brand «Moderna»", "HRIS «Workday»",
        44, 29, 27, 84, 81, 48, 77, 88,
    ),
)

ALL_TEMPLATES: tuple[DemoProfileTemplate, ...] = RU_TEMPLATES + EN_TEMPLATES
