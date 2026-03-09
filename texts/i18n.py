"""
Двуязычные тексты интерфейса (ru / en).
Анкета (имя, качества, описания) не переводится — показываем как написал пользователь.
"""

# Язык по умолчанию, если не выбран
DEFAULT_LANG = "ru"
SUPPORTED_LANGS = ("ru", "en")

T = {
    "ru": {
        "language_question": "🌐 <b>Выбери язык / Choose your language</b>",
        "welcome_1": "Добро пожаловать в Co-founder 👋\n\nЗдесь ты сможешь найти людей, с которыми хочется расти, думать и создавать что-то совершенно новое. Это место для тех, кто хочет развиваться и создавать, а не просто листать.",
        "welcome_2": "Ты найдёшь себе партнёра не по случайности, а по ценностям, целям, стилю мышления, толерантности к риску и т.д.\n\nТы:\n✏️ пройдёшь тесты и лучше поймёшь себя\n📚 получишь доступ к обучающим материалам\n🤝 сможешь находить бизнес-партнёров и собирать команды для проекта, стартапа или любой общей идеи",
        "welcome_btn_gas": "Газ 🚀",
        "welcome_btn_cool": "Круто! 🤩",
        "birth_date_question": "✏️ <b>Укажи дату рождения</b>\n\n<i>Например: 31.07.2009 или 31 июля 2009</i>",
        "birth_date_error": "❌ Укажи дату рождения корректно (например 31.07.2009 или 31 июля 2009). Возраст: от 1 до 120 лет.",
        "legal_agreement": """<b>Перед началом важно договориться 🤝</b>

⚠️ <b>Обрати внимание:</b>

• Мы обрабатываем минимальные данные профиля
(имя, номер телефона, имя пользователя телеграм, возраст, фото, ответы на тесты)

• Данные используются только внутри сервиса

• Мы не передаём данные третьим лицам

• Ты можешь удалить профиль в любой момент

⚠️ <b>Важно:</b>

Результаты тестов и оценки совместимости носят <b>информационный характер.</b> Они <b>не являются персональной рекомендацией</b>, не гарантируют успех проекта, партнёрства или команды. Окончательные решения ты принимаешь <b>самостоятельно.</b>

<b>Продолжая, ты подтверждаешь, что:</b>
— ознакомился с условиями
— даёшь согласие на обработку персональных данных
— понимаешь ограничения ответственности сервиса""",
        "learning_mode_message": """🎓 <b>Сейчас тебе доступен обучающий режим</b>

<b>Здесь ты можешь:</b>
— лучше понять себя, свои сильные стороны и то, в чём ты реально хорош;
— познакомиться с миром бизнеса и стартапов через простые и интересные уроки.

Когда тебе исполнится 14 лет, откроются все возможности бота 🚀""",
        "telegram_access_request": """🔐 <b>Разреши доступ к Telegram ID</b>

Он нужен, чтобы бот мог работать, отправлять обучающие сообщения и быть с тобой на связи.""",
        "telegram_phone_access_request": """🔐 <b>Разреши доступ к Telegram ID и номеру телефона</b>

Они нужны, чтобы бот корректно работал и мы могли быть с тобой на связи.""",
        "name_request": """✏️ <b>Как к тебе обращаться?</b>

<i>Это имя будет отображаться у тебя в профиле.</i>""",
        "name_request_profile": """👤 <b>Укажи своё имя</b>

<i>Это имя будет отображаться в твоей анкете и поможет другим понять, как к тебе обращаться.</i>""",
        "photo_request": """📸 <b>Добавь своё фото</b>

<i>Фото будет отображаться в твоей анкете и поможет другим лучше узнать тебя.</i>""",
        "short_description_request": """✍️ <b>Краткое описание</b>

<i>Напиши в 2-3 предложениях, кто ты и чем занимаешься.
Это будет видно в списке партнеров.</i>

Пример: "Разработчик с опытом в стартапах. Ищу со-основателя для EdTech проекта."

Максимум 200 символов.""",
        "full_description_request": """📝 <b>Полное описание</b>

<i>Расскажи подробнее о себе, своем опыте, интересах и целях.
Что ты хочешь создать? Какие у тебя навыки?</i>

Максимум 1000 символов.""",
        "quality_1_request": "⭐ Введи своё <b>первое</b> качество (например: целеустремлённость).",
        "quality_2_request": "⭐ Введи <b>второе</b> качество.",
        "quality_3_request": "⭐ Введи <b>третье</b> качество.",
        "reg_skip_hint": "\n\nМожно нажать «Пропустить» и заполнить позже в разделе «Партнёры».",
        "success_registration": "✅ Регистрация завершена! Добро пожаловать!",
        "success_registration_offer_test": (
            "✅ <b>Регистрация завершена!</b>\n\n"
            "Пройди основной тест — он нужен для подбора партнёров и отображения совместимости."
        ),
        "contact_request_hint": "📱 Нажми кнопку ниже, чтобы отправить контакт",
        "contact_please_send": "Пожалуйста, отправь контакт кнопкой ниже.",
        "registration_cancelled": "❌ Регистрация отменена.",
        "accept_and_continue": "Принимаю и продолжаю ✅",
        "change_language": "🌐 Сменить язык",
        "edit_profile": "✏️ Изменить",
        "delete_profile": "🗑 Удалить профиль",
        "language_updated": "✅ Язык изменён.",
        # Главное меню и навигация
        "main_menu_title": "🏠 <b>Главное меню</b>",
        "menu_learning": "📚",
        "menu_partners": "🤝",
        "menu_info": "ℹ️ Информация",
        "menu_profile": "👤",
        "menu_premium": "⭐️ Co-founder Subscription",
        "menu_main": "🏠 Главное меню",
        "choose_menu_item": "Выберите пункт меню:",
        "back_from_partners": "Вы вышли из раздела Партнеры. Выберите пункт меню:",
        "partners_title": "🤝 <b>Поиск партнёров</b>",
        "partners_no_users": "Вы просмотрели всех доступных пользователей.\nПопробуйте позже, когда появятся новые анкеты!",
        "partners_intro": "Используйте кнопки ниже для действий с анкетой.",
        "partners_main_test_required": (
            "У тебя не пройден основной тест. Он нужен для подбора партнёров и отображения совместимости.\n\n"
            "Нажми «Пройти тест», чтобы перейти к основному тесту."
        ),
        "partners_fill_profile": "Для использования раздела необходимо заполнить:\n• {fields}\n\nПерейдите в профиль и заполните недостающие данные.",
        "partners_field_short_desc": "краткое описание",
        "partners_field_full_desc": "полное описание",
        "partners_field_qualities": "3 главных качества",
        "partners_access_denied": "⛔ <b>Доступ ограничен</b>\n\nОбратитесь в поддержку.",
        "partners_error_try_again": "Произошла ошибка. Попробуйте ещё раз или выйдите из раздела Партнеры.",
        "partners_btn_take_test": "📋 Пройти тест",
        "quality_emoji_prompt": "Выбери смайлик для этого качества:",
        "quality_no_emoji_in_text": "❌ Нельзя использовать эмодзи в тексте. Смайлик можно выбрать позже.",
        "card_no_name": "Без имени",
        "card_years": "лет",
        "card_compatibility": "Совместимость",
        "card_qualities_heading": "Главные качества",
        "card_more": "Подробнее",
        "card_why_compatibility": "🔗 Почему такая совместимость",
        "card_expand_btn": "📖 Развернуть",
        "card_collapse_btn": "📖 Свернуть",
        "error_try_later": "Произошла ошибка. Попробуйте позже.",
        "not_registered_use_start": "❌ Ты ещё не зарегистрирован. Используй /start",
        # Профиль (подписи и кнопки)
        "profile_section": "👤 <b>Профиль</b>",
        "profile_name": "Имя",
        "profile_age": "Возраст",
        "profile_about": "О себе",
        "profile_qualities": "Главные качества",
        "profile_more": "Подробнее",
        "not_specified": "Не указано",
        "profile_tests": "📝 Тесты",
        "profile_people": "👥 Люди",
        "profile_premium": "⭐️ Co-founder Subscription",
        "profile_back": "◀️ Назад",
        "back_inline": "⬅ Назад",
        "choose_section": "Выберите раздел:",
        "edit_profile_title": "✏️ <b>Редактирование профиля</b>\n\nЧто ты хочешь изменить?",
        "edit_photo": "📸 Фото",
        "edit_short_description": "✍️ Краткое описание",
        "edit_full_description": "📝 Полное описание",
        "edit_quality_1": "⭐ 1 качество",
        "edit_quality_2": "⭐ 2 качество",
        "edit_quality_3": "⭐ 3 качество",
        "delete_confirm_title": "⚠️ <b>Удаление профиля</b>\n\nТы уверен, что хочешь удалить свой профиль?\nВсе твои данные будут удалены без возможности восстановления.",
        "delete_yes": "✅ Да, удалить",
        "delete_cancel": "❌ Отмена",
        "cancel_profile_saved": "Отмена. Профиль сохранён.",
        "btn_skip": "⏭ Пропустить",
        "btn_cancel": "❌ Отмена",
        "btn_pass_main_test": "📋 Пройти основной тест",
        "btn_my_profile": "📊 Мой профиль",
        "btn_other_tests": "📝 Пройти другие тесты",
        "test_completed_title": "✅ Тест завершён!",
        "test_completed_thanks": "Спасибо за прохождение теста. Твои ответы сохранены и будут использованы для подбора совместимых партнёров.",
        "test_completed_profile_saved": "📊 Твой профиль рассчитан и сохранён.",
        "test_start_btn": "▶️ Начать тест",
        "test_finish_btn": "✅ Завершить тест",
        "test_next_question_btn": "➡️ Следующий вопрос",
        "tests_main_btn": "📋 Основной тест (10 вопросов)",
        "tests_roles_btn": "🎭 Ролевые предпочтения",
        "tests_ethics_btn": "⚖️ Ценности и этика",
        "tests_goals_btn": "🎯 Цели и мотивация",
        "tests_risk_btn": "🎲 Толерантность к риску",
        "tests_decision_btn": "🤔 Стиль принятия решений",
        "tests_comm_btn": "💬 Стиль коммуникации",
        "tests_about_btn": "ℹ️ О тестах",
        "learning_btn_show": "Я ещё покажу 😎",
        "profile_not_found": "❌ Профиль не найден.",
        "profile_deleted": "✅ Профиль удалён. Используй /start для новой регистрации.",
        "profile_delete_error": "❌ Ошибка при удалении профиля.",
        "btn_send_contact": "📱 Отправить контакт",
        "lang_russian": "Русский",
        "lang_english": "English",
        "edit_current_copyable": "Сейчас (можно скопировать):",
        "people_search_coming_soon": "Функция в разработке.",
        "favorites_empty_text": "Здесь будут люди, которых ты добавил в избранное (кнопка 🌟 в поиске партнёров).",
        "favorites_load_error": "Не удалось загрузить анкету.",
        "favorites_load_list_error": "Не удалось загрузить список. Попробуйте позже.",
        "favorites_empty_all": "В избранном никого не осталось. Добавляйте анкеты кнопкой 🌟 в разделе «🤝 Партнёры».",
        "matches_empty_text": "Здесь будут люди, с которыми у тебя взаимный интерес.",
        "matches_empty_hint": "Пока ни с кем нет совпадений. Лайкайте анкеты в разделе «🤝 Партнёры» — когда кто-то ответит лайком, вы оба появятся здесь.",
        "matches_list_title": "Люди, с которыми у вас взаимный интерес:",
        "matches_btn_dm": "💬 {name} — в ЛС",
        "edit_name_title": "✏️ <b>Изменение имени</b>\n\nВведи новое имя:",
        "edit_name_error": "❌ Имя: от 2 до 50 символов, только буквы.",
        "edit_photo_title": "📸 <b>Изменение фото</b>",
        "edit_photo_request": "Отправь новое фото:",
        "edit_short_desc_error": "❌ Краткое описание: от 10 до 200 символов.",
        "edit_full_desc_error": "❌ Полное описание: от 20 до 1000 символов.",
        "edit_quality_error": "❌ Укажи качество от 2 до 50 символов.",
        "edit_quality_emoji_error": "Ошибка. Попробуйте снова.",
        "like_notification_text": "🤝 <b>Кто-то проявил интерес</b>\n\n{swiper_name} отметил(а) вашу анкету.\n\nНажмите «Посмотреть», чтобы открыть анкету и ответить.",
        "like_notification_btn_view": "👀 Посмотреть",
        "super_like_message": "🔥 <b>Супер-лайк!</b> Контакт партнёра — переходи в ЛС.",
        "btn_go_to_dm": "💬 Перейти в ЛС",
        "match_title": "🎉 <b>БУУУУМ — это мэтч!</b>",
        "match_message": "У вас взаимный интерес. Удачно пообщаться!",
        "profile_unavailable": "Анкета этого пользователя недоступна.",
        "like_sent_message": "🤝 Вы проявили интерес. Если будет совпадение — мы сообщим!",
        "swipe_action_done": "Вы ответили на анкету.",
        "tests_about_title": "ℹ️ <b>О тестах</b>",
        "tests_about_text": "Тесты помогут тебе лучше понять себя, свои сильные стороны и предпочтения.\n\n<b>Основной тест</b> (10 вопросов) — обязательный тест, который оценивает все критерии совместимости.\n\n<b>Дополнительные тесты</b> (по 10 вопросов каждый) — для более глубокого анализа:\n• Ролевые предпочтения (Hustler/Hacker/Hipster)\n• Ценности и этика\n• Цели и мотивация\n• Толерантность к риску\n• Стиль принятия решений\n• Стиль коммуникации\n\nРезультаты тестов используются для подбора совместимых партнёров.",
        "test_not_found": "❌ Тест не найден",
        "test_info_questions_count": "Количество вопросов:",
        "test_info_ready": "Готов начать?",
        "test_main_already_completed": "Основной тест уже пройден. Перепройти его нельзя.",
        "test_already_completed": "ℹ️ Этот тест уже пройден. Пройди его снова для обновления результатов.",
        "test_question_not_found": "❌ Вопрос не найден",
        "test_question_format": "❓ <b>Вопрос {num} из {total}</b>\n\n{text}",
        "error_start_required": "❌ Ошибка. Начни с /start",
        "error_photo_process": "Не удалось обработать фото. Попробуй ещё раз.",
        "error_photo_please": "Пожалуйста, отправь фото.",
        "card_user_fallback": "Пользователь",
        "test_main_name": "Основной тест",
        "test_main_desc": "10 вопросов для оценки всех критериев совместимости",
        "test_roles_name": "Ролевые предпочтения",
        "test_roles_desc": "10 вопросов для определения роли (Hustler/Hacker/Hipster)",
        "test_ethics_name": "Ценности и этика",
        "test_ethics_desc": "10 вопросов для оценки этических принципов",
        "test_goals_name": "Цели и мотивация",
        "test_goals_desc": "10 вопросов для понимания мотивации и целей",
        "test_risk_name": "Толерантность к риску",
        "test_risk_desc": "10 вопросов для оценки отношения к риску",
        "test_decision_name": "Стиль принятия решений",
        "test_decision_desc": "10 вопросов для понимания стиля принятия решений",
        "test_comm_name": "Стиль коммуникации",
        "test_comm_desc": "10 вопросов для оценки стиля общения",
        # Раздел Люди
        "people_title": "👥 <b>Люди</b>",
        "people_intro": "Здесь ты можешь искать единомышленников, смотреть избранных и совпадения.",
        "people_search": "🔍 Поиск людей",
        "people_favorites": "🌟 Избранные",
        "people_matches": "🤝 Совпадения",
        "favorites_back_to_people": "🔙 В раздел Люди",
        "favorites_back": "◀️ Назад",
        "favorites_next": "Далее ▶️",
        # Тесты
        "tests_title": "📝 <b>Тесты</b>",
        "tests_intro": "Выбери тест, который хочешь пройти:\n\n",
        "tests_main_label": "• <b>Основной тест</b> — обязательный тест из 10 вопросов\n",
        "tests_extra_label": "• <b>Дополнительные тесты</b> — для более точной оценки (по 10 вопросов каждый)",
        # Обучение
        "learning_title": "📚 <b>Обучение</b>",
        "learning_choose_module": "Выбери модуль:",
        "learning_module": "Модуль",
        "learning_choose_lesson": "Выбери урок о бизнесе и стартапах:",
        "lessons_coming": "Уроки в разработке.",
        "lesson_back_to_module": "⬅ К модулю",
        "learning_module_1": "Модуль 1",
        "learning_module_2": "Модуль 2",
        "lesson_1_title": "Что такое стартап",
        "lesson_1_content": """📌 <b>Урок 1: Что такое стартап</b>

<b>Стартап</b> — это молодой проект или компания, которая создаёт что-то новое и старается быстро расти.

<b>Чем стартап отличается от обычного бизнеса:</b>

• <b>Идея.</b> Часто решает конкретную проблему людей с помощью технологии или нового подхода.

• <b>Скорость.</b> Стартапы экспериментируют, пробуют, меняют продукт — им важно быстро понять, что нужно клиенту.

• <b>Масштаб.</b> Цель — не просто «свой магазин», а продукт или сервис, которым могут пользоваться много людей.

• <b>Команда.</b> Один человек редко тянет всё сам — поэтому ищут со-основателей и единомышленников.

Стартап — это не обязательно IT: это может быть образование, экология, услуги, медицина. Главное — идея, рост и команда.""",
        "lesson_2_title": "Откуда берутся идеи для бизнеса",
        "lesson_2_content": """📌 <b>Урок 2: Откуда берутся идеи для бизнеса</b>

Хорошая бизнес-идея чаще всего вырастает из <b>проблемы</b>, которую ты видишь вокруг себя.

<b>Как искать идеи:</b>

• <b>Свой опыт.</b> Что тебе самому не хватало? Что раздражало в школе, в кружках, в приложениях?

• <b>Окружение.</b> На что жалуются друзья, родители, учителя? Какие задачи они решают с трудом?

• <b>Тренды.</b> Что меняется в мире: технологии, привычки, законы? Новые возможности часто появляются на стыке изменений.

<b>Правило:</b> проблема, которую чувствуют многие, — уже возможность. Не обязательно придумывать «гениальное» — достаточно честно решить то, что мешает людям (или тебе).""",
        # Информация и премиум
        "info_title": "ℹ️ <b>Информация</b>",
        "info_text": "Co-founder Bot - это место для поиска партнёров и единомышленников.\n\nЗдесь ты можешь:\n• Пройти тесты и узнать о себе больше\n• Получить доступ к обучающим материалам\n• Найти партнёров для проектов и стартапов\n• Собрать команду для реализации идей",
        "instruction_title": "📖 <b>Инструкция по боту</b>",
        "instruction_text": "1. Заполни свой профиль\n2. Пройди тесты для лучшего понимания себя\n3. Изучи обучающие материалы\n4. Найди партнёров через раздел Знакомства\n5. Общайся и создавай проекты вместе!",
        "premium_title": "⭐ <b>Co-founder Subscription</b>",
        "premium_text": "Расширенные возможности в разработке.",
        # Подписка: экран предложения
        "subscription_benefits_title": "⭐ <b>Co-founder Subscription</b>\n\nТы получаешь:\n\n🔥 <b>1 супер-лайк</b> — контакт партнёра сразу, без ожидания взаимного лайка\n❤️ <b>1 лайк в неделю</b> — отмечай понравившиеся анкеты\n⭐ <b>5 избранных</b> — сохраняй до 5 анкет в избранное\n\nСтоимость: <b>{price} звёзд</b> (Telegram Stars).\n\nЕсли звёзд нет — купить можно по <a href=\"{url}\">ссылке</a>.",
        "subscription_btn_pay": "💳 Оплатить",
        "subscription_btn_show_code": "📋 Показать код",
        "subscription_btn_i_paid": "✅ Я оплатил",
        "subscription_btn_back_profile": "◀️ Вернуться в профиль",
        "subscription_how_to_title": "📋 <b>Как оплатить</b>\n\nДля максимально быстрой оплаты:\n\n1️⃣ Нажми «Показать код» — тебе придёт твой персональный код.\n2️⃣ Отправь этот код одним сообщением в нашу группу оплаты.\n3️⃣ Бот проверит сообщение и моментально удалит его.\n4️⃣ Подписка активируется — тебе придёт поздравление.\n5️⃣ Нажми «Я оплатил» после отправки кода в группу.",
        "subscription_code_screen": "📋 <b>Твой код для оплаты</b>\n\nОтправь этот код <b>одним сообщением</b> в группу:\n\n<a href=\"{group_url}\">Перейти в группу оплаты</a>\n\nКод (скопируй):\n<code>{code}</code>\n\nПосле отправки кода в группу нажми «Я оплатил».",
        "subscription_congrats": "🎉 <b>Поздравляем с покупкой подписки!</b>\n\nТебе доступны: супер-лайк 🔥, 1 лайк в неделю и 5 избранных.",
        "subscription_not_yet": "⏳ Подписка ещё не активирована.\n\nОтправь свой код в группу оплаты и нажми «Я оплатил» снова.",
        "subscription_already": "✅ У тебя уже есть активная подписка.\n\nЖми «Вернуться в профиль» — и пользуйся супер-лайком в разделе Партнёры.",
        "subscription_back_to_profile": "Вернуться в профиль",
        "subscription_admin_give": "🎉 <b>Тебе выдали подписку на месяц!</b>\n\nСпасибо за вклад в проект. Теперь тебе доступны: супер-лайк 🔥, 1 лайк в неделю и 5 избранных.",
        "limit_likes_week": "⛔ Не более {limit} лайков в неделю. Лимит исчерпан. Попробуйте через несколько дней.",
        "likes_left_info": "❤️ У тебя осталось <b>{remaining}</b> из <b>{limit}</b> лайков на эту неделю.",
        "likes_no_left_info": "⛔ Ты использовал все <b>{limit}</b> лайков на эту неделю.",
        "likes_unlimited_info": "❤️ У тебя нет ограничений по лайкам на эту неделю.",
        "limit_bookmarks_week": "⛔ Не более 5 добавлений в избранное в неделю. Лимит исчерпан. Попробуйте через несколько дней.",
        "limit_favorites_total": "⛔ В избранном может быть не более 5 анкет. Удалите кого-то из избранного или оформите подписку.",
        "card_super_like_btn": "🔥",
    },
    "en": {
        "language_question": "🌐 <b>Choose your language</b>",
        "welcome_1": "Welcome to Co-founder 👋\n\nHere you can find people you want to grow, think and build something new with. This is a place for those who want to develop and create, not just scroll.",
        "welcome_2": "You'll find a partner not by chance, but by values, goals, way of thinking, risk tolerance, etc.\n\nYou will:\n✏️ take tests and understand yourself better\n📚 get access to learning materials\n🤝 find business partners and build teams for a project, startup or any shared idea",
        "welcome_btn_gas": "Go 🚀",
        "welcome_btn_cool": "Cool! 🤩",
        "birth_date_question": "✏️ <b>Enter your date of birth</b>\n\n<i>E.g.: 31.07.2009 or July 31, 2009</i>",
        "birth_date_error": "❌ Enter a valid date of birth (e.g. 31.07.2009). Age: 1–120 years.",
        "legal_agreement": """<b>Before we start — a few things 🤝</b>

⚠️ <b>Please note:</b>

• We process minimal profile data
(name, phone, Telegram username, age, photo, test answers)

• Data is used only within the service

• We do not share data with third parties

• You can delete your profile at any time

⚠️ <b>Important:</b>

Test results and compatibility scores are <b>for information only.</b> They are <b>not personal advice</b> and do not guarantee success of a project, partnership or team. You make your own decisions.

<b>By continuing, you confirm that you:</b>
— have read the terms
— consent to the processing of your personal data
— understand the limitations of the service""",
        "learning_mode_message": """🎓 <b>You now have access to learning mode</b>

<b>Here you can:</b>
— understand yourself better, your strengths and what you're good at;
— explore the world of business and startups through simple, engaging lessons.

When you turn 14, all bot features will unlock 🚀""",
        "telegram_access_request": """🔐 <b>Allow access to your Telegram ID</b>

It's needed so the bot can work, send you lessons and stay in touch.""",
        "telegram_phone_access_request": """🔐 <b>Allow access to Telegram ID and phone number</b>

They're needed for the bot to work correctly and for us to stay in touch.""",
        "name_request": """✏️ <b>What should we call you?</b>

<i>This name will be shown in your profile.</i>""",
        "name_request_profile": """👤 <b>Enter your name</b>

<i>This name will appear in your profile and help others know what to call you.</i>""",
        "photo_request": """📸 <b>Add your photo</b>

<i>It will be shown in your profile and help others get to know you.</i>""",
        "short_description_request": """✍️ <b>Short description</b>

<i>In 2–3 sentences, who you are and what you do.
This will be visible in the partners list.</i>

Example: "Developer with startup experience. Looking for a co-founder for an EdTech project."

Max 200 characters.""",
        "full_description_request": """📝 <b>Full description</b>

<i>Tell more about yourself, your experience, interests and goals.
What do you want to build? What are your skills?</i>

Max 1000 characters.""",
        "quality_1_request": "⭐ Enter your <b>first</b> strength (e.g. determination).",
        "quality_2_request": "⭐ Enter your <b>second</b> strength.",
        "quality_3_request": "⭐ Enter your <b>third</b> strength.",
        "reg_skip_hint": "\n\nYou can tap «Skip» and fill this in later in Partners.",
        "success_registration": "✅ Registration complete! Welcome!",
        "success_registration_offer_test": (
            "✅ <b>Registration complete!</b>\n\n"
            "Take the main test — it's needed for matching partners and showing compatibility."
        ),
        "contact_request_hint": "📱 Tap the button below to share your contact",
        "contact_please_send": "Please send your contact using the button below.",
        "registration_cancelled": "❌ Registration cancelled.",
        "accept_and_continue": "I accept and continue ✅",
        "change_language": "🌐 Change language",
        "edit_profile": "✏️ Edit",
        "delete_profile": "🗑 Delete profile",
        "language_updated": "✅ Language changed.",
        "main_menu_title": "🏠 <b>Main menu</b>",
        "menu_learning": "📚",
        "menu_partners": "🤝",
        "menu_info": "ℹ️ Information",
        "menu_profile": "👤",
        "menu_premium": "⭐️ Co-founder Subscription",
        "menu_main": "🏠 Main menu",
        "choose_menu_item": "Choose a menu item:",
        "back_from_partners": "You left Partners. Choose a menu item:",
        "partners_title": "🤝 <b>Partner search</b>",
        "partners_no_users": "You've seen all available users.\nTry again later when new profiles appear!",
        "partners_intro": "Use the buttons below to act on the profile.",
        "partners_main_test_required": (
            "You haven't completed the main test. It's needed to match partners and show compatibility.\n\n"
            "Tap «Take test» to go to the main test."
        ),
        "partners_fill_profile": "To use this section you need to fill in:\n• {fields}\n\nGo to your profile and complete the missing fields.",
        "partners_field_short_desc": "short description",
        "partners_field_full_desc": "full description",
        "partners_field_qualities": "3 key strengths",
        "partners_access_denied": "⛔ <b>Access restricted</b>\n\nContact support.",
        "partners_error_try_again": "Something went wrong. Try again or leave the Partners section.",
        "partners_btn_take_test": "📋 Take test",
        "limit_likes_week": "⛔ Up to {limit} likes per week. Limit reached. Try again in a few days.",
        "likes_left_info": "❤️ You have <b>{remaining}</b> out of <b>{limit}</b> likes left for this week.",
        "likes_no_left_info": "⛔ You have used all <b>{limit}</b> likes for this week.",
        "likes_unlimited_info": "❤️ You have no like limit for this week.",
        "limit_bookmarks_week": "⛔ Up to 5 additions to favorites per week. Limit reached. Try again in a few days.",
        "quality_emoji_prompt": "Choose an emoji for this strength:",
        "quality_no_emoji_in_text": "❌ Don't use emoji in the text. You can pick an emoji next.",
        "card_no_name": "No name",
        "card_years": "years",
        "card_compatibility": "Compatibility",
        "card_qualities_heading": "Key strengths",
        "card_more": "More",
        "card_why_compatibility": "🔗 Why this compatibility",
        "card_expand_btn": "📖 Expand",
        "card_collapse_btn": "📖 Collapse",
        "error_try_later": "Something went wrong. Try again later.",
        "not_registered_use_start": "❌ You're not registered yet. Use /start",
        "profile_section": "👤 <b>Profile</b>",
        "profile_name": "Name",
        "profile_age": "Age",
        "profile_about": "About",
        "profile_qualities": "Key strengths",
        "profile_more": "More",
        "not_specified": "Not specified",
        "profile_tests": "📝 Tests",
        "profile_people": "👥 People",
        "profile_premium": "⭐️ Co-founder Subscription",
        "profile_back": "◀️ Back",
        "back_inline": "⬅ Back",
        "choose_section": "Choose a section:",
        "edit_profile_title": "✏️ <b>Edit profile</b>\n\nWhat do you want to change?",
        "edit_photo": "📸 Photo",
        "edit_short_description": "✍️ Short description",
        "edit_full_description": "📝 Full description",
        "edit_quality_1": "⭐ 1 strength",
        "edit_quality_2": "⭐ 2 strength",
        "edit_quality_3": "⭐ 3 strength",
        "delete_confirm_title": "⚠️ <b>Delete profile</b>\n\nAre you sure you want to delete your profile?\nAll your data will be permanently deleted.",
        "delete_yes": "✅ Yes, delete",
        "delete_cancel": "❌ Cancel",
        "cancel_profile_saved": "Cancelled. Profile saved.",
        "btn_skip": "⏭ Skip",
        "btn_cancel": "❌ Cancel",
        "btn_pass_main_test": "📋 Take main test",
        "btn_my_profile": "📊 My profile",
        "btn_other_tests": "📝 Take other tests",
        "test_completed_title": "✅ Test complete!",
        "test_completed_thanks": "Thank you for taking the test. Your answers have been saved and will be used to match compatible partners.",
        "test_completed_profile_saved": "📊 Your profile has been calculated and saved.",
        "test_start_btn": "▶️ Start test",
        "test_finish_btn": "✅ Finish test",
        "test_next_question_btn": "➡️ Next question",
        "tests_main_btn": "📋 Main test (10 questions)",
        "tests_roles_btn": "🎭 Role preferences",
        "tests_ethics_btn": "⚖️ Values and ethics",
        "tests_goals_btn": "🎯 Goals and motivation",
        "tests_risk_btn": "🎲 Risk tolerance",
        "tests_decision_btn": "🤔 Decision-making style",
        "tests_comm_btn": "💬 Communication style",
        "tests_about_btn": "ℹ️ About tests",
        "learning_btn_show": "I'll show you 😎",
        "profile_not_found": "❌ Profile not found.",
        "profile_deleted": "✅ Profile deleted. Use /start for new registration.",
        "profile_delete_error": "❌ Error deleting profile.",
        "btn_send_contact": "📱 Send contact",
        "lang_russian": "Russian",
        "lang_english": "English",
        "edit_current_copyable": "Current (can copy):",
        "people_search_coming_soon": "Feature coming soon.",
        "favorites_empty_text": "Here will be people you added to favorites (🏷 button in Partners).",
        "favorites_load_error": "Failed to load profile.",
        "favorites_load_list_error": "Failed to load list. Try again later.",
        "favorites_empty_all": "No one left in favorites. Add profiles with 🏷 in Partners.",
        "matches_empty_text": "Here will be people with mutual interest.",
        "matches_empty_hint": "No matches yet. Like profiles in Partners — when someone likes back, you'll both appear here.",
        "matches_list_title": "People with mutual interest:",
        "matches_btn_dm": "💬 {name} — DM",
        "edit_name_title": "✏️ <b>Edit name</b>\n\nEnter new name:",
        "edit_name_error": "❌ Name: 2–50 characters, letters only.",
        "edit_photo_title": "📸 <b>Edit photo</b>",
        "edit_photo_request": "Send new photo:",
        "edit_short_desc_error": "❌ Short description: 10–200 characters.",
        "edit_full_desc_error": "❌ Full description: 20–1000 characters.",
        "edit_quality_error": "❌ Enter 2–50 characters.",
        "edit_quality_emoji_error": "Error. Try again.",
        "like_notification_text": "🤝 <b>Someone showed interest</b>\n\n{swiper_name} liked your profile.\n\nTap «View» to open the profile and respond.",
        "like_notification_btn_view": "👀 View",
        "super_like_message": "🔥 <b>Super like!</b> Partner's contact — go to DM.",
        "btn_go_to_dm": "💬 Go to DM",
        "match_title": "🎉 <b>BOOM — it's a match!</b>",
        "match_message": "You have mutual interest. Good luck chatting!",
        "profile_unavailable": "This user's profile is unavailable.",
        "like_sent_message": "🤝 You showed interest. If there's a match — we'll notify you!",
        "swipe_action_done": "You responded to the profile.",
        "tests_about_title": "ℹ️ <b>About tests</b>",
        "tests_about_text": "Tests help you understand yourself better, your strengths and preferences.\n\n<b>Main test</b> (10 questions) — required test that evaluates all compatibility criteria.\n\n<b>Additional tests</b> (10 questions each) — for deeper analysis:\n• Role preferences (Hustler/Hacker/Hipster)\n• Values and ethics\n• Goals and motivation\n• Risk tolerance\n• Decision-making style\n• Communication style\n\nTest results are used to match compatible partners.",
        "test_not_found": "Test not found",
        "test_info_questions_count": "Number of questions:",
        "test_info_ready": "Ready to start?",
        "test_main_already_completed": "Main test already completed. Cannot retake.",
        "test_already_completed": "This test is already completed. Retake to update results.",
        "test_question_not_found": "Question not found",
        "test_question_format": "❓ <b>Question {num} of {total}</b>\n\n{text}",
        "error_start_required": "❌ Error. Start with /start",
        "error_photo_process": "Could not process photo. Try again.",
        "error_photo_please": "Please send a photo.",
        "card_user_fallback": "User",
        "test_main_name": "Main test",
        "test_main_desc": "10 questions to evaluate all compatibility criteria",
        "test_roles_name": "Role preferences",
        "test_roles_desc": "10 questions to determine role (Hustler/Hacker/Hipster)",
        "test_ethics_name": "Values and ethics",
        "test_ethics_desc": "10 questions to evaluate ethical principles",
        "test_goals_name": "Goals and motivation",
        "test_goals_desc": "10 questions to understand motivation and goals",
        "test_risk_name": "Risk tolerance",
        "test_risk_desc": "10 questions to evaluate attitude to risk",
        "test_decision_name": "Decision-making style",
        "test_decision_desc": "10 questions to understand decision-making style",
        "test_comm_name": "Communication style",
        "test_comm_desc": "10 questions to evaluate communication style",
        "people_intro": "Here you can find like-minded people, view favorites and matches.",
        "people_search": "🔍 Search people",
        "people_favorites": "⭐ Favorites",
        "people_matches": "🤝 Matches",
        "favorites_back_to_people": "🔙 Back to People",
        "favorites_back": "◀️ Back",
        "favorites_next": "Next ▶️",
        "tests_title": "📝 <b>Tests</b>",
        "tests_intro": "Choose a test to take:\n\n",
        "tests_main_label": "• <b>Main test</b> — required 10-question test\n",
        "tests_extra_label": "• <b>Additional tests</b> — for more accurate assessment (10 questions each)",
        "learning_title": "📚 <b>Learning</b>",
        "learning_choose_module": "Choose a module:",
        "learning_module": "Module",
        "learning_choose_lesson": "Choose a lesson about business and startups:",
        "lessons_coming": "Lessons coming soon.",
        "lesson_back_to_module": "⬅ Back to module",
        "learning_module_1": "Module 1",
        "learning_module_2": "Module 2",
        "lesson_1_title": "What is a startup",
        "lesson_1_content": """📌 <b>Lesson 1: What is a startup</b>

A <b>startup</b> is a young project or company that creates something new and aims to grow fast.

<b>How startups differ from regular business:</b>

• <b>Idea.</b> Often solves a real problem people have, using technology or a new approach.

• <b>Speed.</b> Startups experiment, try things, change the product — they need to learn quickly what the customer needs.

• <b>Scale.</b> The goal isn’t just “my shop” but a product or service that many people can use.

• <b>Team.</b> One person rarely does everything — so they look for co-founders and like-minded people.

A startup isn’t only IT: it can be education, sustainability, services, healthcare. What matters is the idea, growth, and team.""",
        "lesson_2_title": "Where business ideas come from",
        "lesson_2_content": """📌 <b>Lesson 2: Where business ideas come from</b>

A good business idea usually grows from a <b>problem</b> you see around you.

<b>How to find ideas:</b>

• <b>Your own experience.</b> What did you miss? What was annoying at school, in clubs, in apps?

• <b>Your environment.</b> What do friends, family, teachers complain about? What do they find hard to do?

• <b>Trends.</b> What’s changing in the world: tech, habits, laws? New opportunities often appear where things change.

<b>Rule:</b> a problem that many people feel is already an opportunity. You don’t need a “genius” idea — just honestly solve what bothers people (or you).""",
        "info_title": "ℹ️ <b>Information</b>",
        "info_text": "Co-founder Bot is a place to find partners and like-minded people.\n\nHere you can:\n• Take tests and learn more about yourself\n• Access learning materials\n• Find partners for projects and startups\n• Build a team to bring ideas to life",
        "instruction_title": "📖 <b>Bot guide</b>",
        "instruction_text": "1. Fill in your profile\n2. Take tests to understand yourself better\n3. Explore the learning materials\n4. Find partners in the People section\n5. Connect and build projects together!",
        "premium_title": "⭐ <b>Co-founder Subscription</b>",
        "premium_text": "More features coming soon.",
        "subscription_benefits_title": "⭐ <b>Co-founder Subscription</b>\n\nYou get:\n\n🔥 <b>1 super like</b> — see partner's contact right away, no mutual like needed\n❤️ <b>1 like per week</b> — mark profiles you like\n⭐ <b>5 favorites</b> — save up to 5 profiles in favorites\n\nPrice: <b>{price} stars</b> (Telegram Stars).\n\nIf you don't have stars — you can buy them via this <a href=\"{url}\">link</a>.",
        "subscription_btn_pay": "💳 Pay",
        "subscription_btn_show_code": "📋 Show code",
        "subscription_btn_i_paid": "✅ I paid",
        "subscription_btn_back_profile": "◀️ Back to profile",
        "subscription_how_to_title": "📋 <b>How to pay</b>\n\nFor the fastest payment:\n\n1️⃣ Tap «Show code» — you'll get your personal code.\n2️⃣ Send this code in one message to our payment group.\n3️⃣ The bot will check and delete the message.\n4️⃣ Subscription activates — you'll get a congrats message.\n5️⃣ Tap «I paid» after sending the code.",
        "subscription_code_screen": "📋 <b>Your payment code</b>\n\nSend this code in <b>one message</b> to the group:\n\n<a href=\"{group_url}\">Go to payment group</a>\n\nCode (copy):\n<code>{code}</code>\n\nAfter sending the code, tap «I paid».",
        "subscription_congrats": "🎉 <b>Congratulations on your subscription!</b>\n\nYou now have: super like 🔥, 1 like per week, and 5 favorites.",
        "subscription_not_yet": "⏳ Subscription not activated yet.\n\nSend your code to the payment group and tap «I paid» again.",
        "subscription_already": "✅ You already have an active subscription.\n\nTap «Back to profile» and use the super like in Partners.",
        "subscription_back_to_profile": "Back to profile",
        "limit_favorites_total": "⛔ You can have at most 5 favorites. Remove someone or get a subscription.",
        "card_super_like_btn": "🔥",
    },
}


def t(lang: str, key: str, **kwargs: object) -> str:
    """Текст по ключу для языка. Если ключа нет — fallback на ru. Если передан kwargs — подстановка {key} в строку."""
    if lang not in T:
        lang = DEFAULT_LANG
    s = T[lang].get(key) or T[DEFAULT_LANG].get(key) or key
    if kwargs:
        try:
            s = s.format(**kwargs)
        except KeyError:
            pass
    return s


def text_options(key: str) -> set[str]:
    """Все варианты текста для ключа (ru + en) — для F.text.in_(...) в хендлерах."""
    out = set()
    for lang in SUPPORTED_LANGS:
        if key in T.get(lang, {}):
            out.add(T[lang][key])
    return out or {key}
