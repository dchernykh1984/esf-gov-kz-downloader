"""Captions for the printed forms, in Russian and optionally Kazakh.

The official blank is bilingual. Only the captions are translated: document
content (counterparty names, addresses, item descriptions) is stored in a
single field and is reproduced exactly as the sender entered it.

Kazakh is filled in where the wording is the settled accounting term. Entries
with no Kazakh fall back to Russian alone rather than carry a guessed
translation onto a tax form.
"""

from __future__ import annotations

RUS = "rus"
KAZ_RUS = "kaz+rus"
LANGUAGES = (RUS, KAZ_RUS)

# key -> (Russian, Kazakh or None)
_LABELS: dict[str, tuple[str, str | None]] = {
    # Document headings
    "invoice_title": ("Счёт-фактура", "Шот-фактура"),
    "awp_title": (
        "Акт выполненных работ (оказанных услуг)",
        "Орындалған жұмыстардың (көрсетілген қызметтердің) актісі",
    ),
    "reg_number": ("Регистрационный номер", "Тіркеу нөмірі"),
    "status": ("Статус", "Мәртебесі"),
    # Sections
    "section_a": ("Раздел A. Общий раздел", "A бөлімі. Жалпы бөлім"),
    "section_b": (
        "Раздел B. Реквизиты поставщика",
        "B бөлімі. Жеткізушінің деректемелері",
    ),
    "section_c": ("Раздел C. Реквизиты получателя", "C бөлімі. Алушының деректемелері"),
    "section_d": ("Раздел D. Реквизиты грузоотправителя и грузополучателя", None),
    "section_e": ("Раздел E. Договор (контракт)", "E бөлімі. Шарт (келісімшарт)"),
    "section_f": ("Раздел F. Документы, подтверждающие поставку", None),
    "section_g": (
        "Раздел G. Данные по товарам, работам, услугам",
        "G бөлімі. Тауарлар, жұмыстар, көрсетілетін қызметтер бойынша деректер",
    ),
    "section_i": ("Раздел I. Реквизиты поверенного (оператора) поставщика", None),
    "section_j": ("Раздел J. Реквизиты поверенного (оператора) получателя", None),
    "section_k": ("Раздел K. Дополнительные сведения", "K бөлімі. Қосымша мәліметтер"),
    # Common fields
    "num": ("Номер", "Нөмірі"),
    "date": ("Дата выписки", "Жазылған күні"),
    "turnover_date": ("Дата совершения оборота", "Айналым жасалған күн"),
    "invoice_type": ("Тип", "Түрі"),
    "tin": ("ИИН/БИН", "ЖСН/БСН"),
    "name": ("Наименование", "Атауы"),
    "address": ("Адрес", "Мекенжайы"),
    "country": ("Код страны", "Ел коды"),
    "nds_certificate": ("Свидетельство по НДС", None),
    "nds_date": ("Дата постановки на учёт по НДС", None),
    "bank": ("Банк", "Банк"),
    "iik": ("ИИК", "ЖСК"),
    "bik": ("БИК", "БСК"),
    "kbe": ("КБе", "Кбе"),
    "consignor": ("Грузоотправитель", "Жүк жөнелтуші"),
    "consignee": ("Грузополучатель", "Жүк алушы"),
    "contract": ("Договор (контракт)", "Шарт (келісімшарт)"),
    "contract_num": ("Номер договора", "Шарт нөмірі"),
    "contract_date": ("Дата договора", "Шарт күні"),
    "payment_term": ("Условия оплаты", "Төлем шарттары"),
    "transport": ("Способ отправления", "Жөнелту тәсілі"),
    "warrant": ("Доверенность", "Сенімхат"),
    "destination": ("Пункт назначения", "Баратын жері"),
    "delivery_doc": ("Документ, подтверждающий поставку", None),
    "additional_info": ("Дополнительные сведения", "Қосымша мәліметтер"),
    "operator": ("Оператор", "Оператор"),
    "currency": ("Валюта", "Валюта"),
    # Goods table
    "row_no": ("№", "№"),
    "description": ("Наименование ТРУ", "ТЖҚ атауы"),
    "tnved_name": ("Наименование по ТН ВЭД", None),
    "unit_code": ("Код ТН ВЭД", None),
    "unit": ("Ед. изм.", "Өлшем бірлігі"),
    "quantity": ("Кол-во", "Саны"),
    "unit_price": ("Цена за единицу", "Бірлік бағасы"),
    "price_without_tax": ("Стоимость без НДС", "ҚҚС-сыз құны"),
    "excise_rate": ("Акциз, ставка", None),
    "excise_amount": ("Акциз, сумма", None),
    "turnover_size": ("Размер оборота", "Айналым мөлшері"),
    "nds_rate": ("НДС, ставка", "ҚҚС, мөлшерлемесі"),
    "nds_amount": ("НДС, сумма", "ҚҚС, сомасы"),
    "price_with_tax": ("Стоимость с НДС", "ҚҚС-пен құны"),
    "declaration": ("Декларация на товары", None),
    "origin": ("Признак происхождения", None),
    "total": ("Итого", "Барлығы"),
    # Acts
    "act_type": ("Вид акта", None),
    "performed_date": ("Дата выполнения работ", "Жұмыстың орындалған күні"),
    "executor": ("Исполнитель (поставщик)", "Орындаушы (жеткізуші)"),
    "client": ("Заказчик (получатель)", "Тапсырыс беруші (алушы)"),
    "works": ("Выполненные работы (оказанные услуги)", None),
    "work_name": ("Наименование работ (услуг)", "Жұмыстардың (қызметтердің) атауы"),
    "appendix": ("Приложение", "Қосымша"),
    "stock_info": ("Сведения об использовании запасов заказчика", None),
    # Footer
    "generated_note": (
        "Печатная форма сформирована из XML, полученного через API ИС ЭСФ. "
        "Юридически значимым документом является подписанный ЭЦП XML.",
        None,
    ),
}


def label(key: str, language: str = RUS) -> str:
    """Return the caption for `key`, bilingual when asked and available."""
    russian, kazakh = _LABELS.get(key, (key, None))
    if language == KAZ_RUS and kazakh:
        return f"{kazakh} / {russian}"
    return russian
