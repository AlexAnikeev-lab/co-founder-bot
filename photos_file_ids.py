# Сгенерировано/обновлено скриптами upload_photos_for_file_id.py и upload_photos_for_file_id_en.py.
# Не редактируй вручную. Чтобы обновить — заново запусти нужный скрипт.

REGISTRATION_PHOTO_FILE_IDS = {
    "welcome_1": "AgACAgIAAxkDAAMYab0z9mA5wFxaPeovs7w36blnk0QAAtkUaxu7B-hJl5et0daB1pMBAAMCAAN3AAM6BA",
    "welcome_2": "AgACAgIAAxkDAAMZab0z_Mcyn4orwqicxGGRXJLEaIoAAtoUaxu7B-hJ4WUIaWoqPJ8BAAMCAAN3AAM6BA",
    "age": "AgACAgIAAxkDAAMaab00AozBiClg6bfl7SDY62fdG9MAAtsUaxu7B-hJT8baX_1xy94BAAMCAAN3AAM6BA",
    "legal": "AgACAgIAAxkDAAMbab00CRJAVpWQ6Pu3Mgf2Pr0bx7gAAtwUaxu7B-hJR7WwKWjVt6UBAAMCAAN3AAM6BA",
    "learning_mode": "AgACAgIAAxkDAAMbab00CRJAVpWQ6Pu3Mgf2Pr0bx7gAAtwUaxu7B-hJR7WwKWjVt6UBAAMCAAN3AAM6BA",
    "telegram": "AgACAgIAAxkDAAMcab00EWG4VmppwnjfPo_ZbW5DGyEAAt0Uaxu7B-hJZ4hODNbtVmwBAAMCAAN3AAM6BA",
    "name": "AgACAgIAAxkDAAMdab00Fga99FS1ZNnemC7Vj1lCF38AAt4Uaxu7B-hJa7KNEManeN0BAAMCAAN3AAM6BA",
    "photo": "AgACAgIAAxkDAAMeab00HHciDInGj_mwocQTDptOkTYAAt8Uaxu7B-hJTxzUDueBvnUBAAMCAAN3AAM6BA",
    "short_desc": "AgACAgIAAxkDAAMiab00NP9CsxTUnndbZYeYpbjTSPYAAuMUaxu7B-hJzShvfPWdZh0BAAMCAAN3AAM6BA",
    "full_desc": "AgACAgIAAxkDAAMjab00OhWby__slNfanRSgUF2-NmEAAuQUaxu7B-hJ3z5MrAIPCtoBAAMCAAN3AAM6BA",
    "quality_1": "AgACAgIAAxkDAAMfab00IuqrLnjb5CorPZZdzw5Hx98AAuAUaxu7B-hJypZl4DdZ9MgBAAMCAAN3AAM6BA",
    "quality_2": "AgACAgIAAxkDAAMgab00J8gOdS_cQ5K6pGTUXp1v-TYAAuEUaxu7B-hJbX3Xl5mT1GEBAAMCAAN3AAM6BA",
    "quality_3": "AgACAgIAAxkDAAMhab00LaUcO3yfbwYlxBX5ro7-U88AAuIUaxu7B-hJu-10rnOEhCABAAMCAAN3AAM6BA",
    "success": "AgACAgIAAxkDAAMkab00P3QCAVitjKXOFXcvHKAX6QEAAuUUaxu7B-hJLb4yDZx8w-ABAAMCAAN3AAM6BA",
}

REGISTRATION_PHOTO_FILE_IDS_EN = {
    "welcome_1": "AgACAgIAAxkDAAMlab00S5qC_x9ZTb47XVAIa0tn_s8AAuYUaxu7B-hJey_yN_LqVrsBAAMCAAN3AAM6BA",
    "welcome_2": "AgACAgIAAxkDAAMmab00TnVi_VTaIAcF23KxejeoBe8AAucUaxu7B-hJwnUCCPW5qEsBAAMCAAN3AAM6BA",
    "age": "AgACAgIAAxkDAAMnab00Ulw3gmj17c7gLbZ2Fgv_g0UAAugUaxu7B-hJbMqZvtdxECkBAAMCAAN3AAM6BA",
    "legal": "AgACAgIAAxkDAAMoab00VglIW2G_cW6e0P8t3lHkRUQAAukUaxu7B-hJW8lb8dTk4i4BAAMCAAN3AAM6BA",
    "learning_mode": "AgACAgIAAxkDAAMoab00VglIW2G_cW6e0P8t3lHkRUQAAukUaxu7B-hJW8lb8dTk4i4BAAMCAAN3AAM6BA",
    "telegram": "AgACAgIAAxkDAAMpab00WV7p-UkgoEFgyc53Lh46LYEAAuoUaxu7B-hJVVmnxl3XyrcBAAMCAAN3AAM6BA",
    "name": "AgACAgIAAxkDAAMqab00YHKX6DjIfFCLnBkJU5EeBtcAAusUaxu7B-hJrhaa9exxsGQBAAMCAAN3AAM6BA",
    "quality_1": "AgACAgIAAxkDAAMrab00aIGefGl1f3igGhSqc0_SSD8AAuwUaxu7B-hJNIeQne_-L64BAAMCAAN3AAM6BA",
    "quality_2": "AgACAgIAAxkDAAMsab00aiyCeGDvshffb1qXYHpLb6UAAu0Uaxu7B-hJkJBbdKIQ9_wBAAMCAAN3AAM6BA",
    "quality_3": "AgACAgIAAxkDAAMtab00bdBFfRe7PRgKpb5It5NUFb4AAu4Uaxu7B-hJK9wAAaA5Xh7VAQADAgADdwADOgQ",
    "short_desc": "AgACAgIAAxkDAAMuab00b3LjTfYylLasOoGHeAQQ5AwAAu8Uaxu7B-hJvGvwJVsaB1kBAAMCAAN3AAM6BA",
    "full_desc": "AgACAgIAAxkDAAMvab00cUndIqRz5fi4IM1nIEWgxWsAAvAUaxu7B-hJqaiXrMrFO1EBAAMCAAN3AAM6BA",
    "success": "AgACAgIAAxkDAAMwab00dcgVMSz9nDa-GA-nQojl6doAAvEUaxu7B-hJWamFyngtlN4BAAMCAAN3AAM6BA",
}
