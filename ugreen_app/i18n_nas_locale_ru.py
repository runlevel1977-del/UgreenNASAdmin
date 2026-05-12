# -*- coding: utf-8 -*-
"""NAS-Verwaltung — Русский (ru)."""

NAS_ADMIN_RU: dict[str, str] = {
    "nas_admin.title": "Управление NAS (действия)",
    "nas_admin.subtitle": (
        "Привилегированное обслуживание NAS по SSH (sudo): безопасное извлечение USB, самотесты SMART, "
        "проверка RAID и обслуживание ОС (fstrim/e2scrub), краткое мигание индикатора отсека, проверка бипера. "
        "Требуется «Полный доступ» в заголовке и работающий sudo для пользователя SSH."
    ),
    "nas_admin.section_usb": "USB",
    "nas_admin.section_smart": "Самотест SMART",
    "nas_admin.section_maintenance": "Обслуживание RAID и файловых систем",
    "nas_admin.section_hw": "Индикатор и бипер",
    "nas_admin.usb_mount": "Точка монтирования:",
    "nas_admin.disk": "Диск:",
    "nas_admin.test_type": "Тип:",
    "nas_admin.led_slot": "Индикатор отсека:",
    "nas_admin.smart_short": "Короткий",
    "nas_admin.smart_long": "Длинный",
    "nas_admin.smart_conv": "Транспортировка (conveyance)",
    "nas_admin.btn_usb_refresh": "Обновить список USB",
    "nas_admin.btn_usb_eject": "Безопасное извлечение",
    "nas_admin.btn_disk_refresh": "Обновить диски",
    "nas_admin.btn_smart_start": "Запустить SMART-тест",
    "nas_admin.btn_mdcheck": "Запустить проверку RAID",
    "nas_admin.btn_mdcheck_status": "Статус проверки RAID",
    "nas_admin.btn_fstrim": "Выполнить TRIM сейчас (fstrim)",
    "nas_admin.btn_e2scrub": "Проверка ext4 (e2scrub_all)",
    "nas_admin.btn_led_refresh": "Обновить слоты LED",
    "nas_admin.btn_led_blink": "Идентификация LED (мигание 12 с)",
    "nas_admin.btn_beep": "Тест бипера (ugbeep)",
    "nas_admin.log_usb_done": "[USB] Обнаружено точек монтирования: {n}.",
    "nas_admin.log_disk_done": "[Диск] Найдено блочных устройств: {n}.",
    "nas_admin.log_led_done": "[LED] Слотов в /sys/class/leds: {n}.",
    "nas_admin.msg_need_usb": "Нет USB-монтирования",
    "nas_admin.msg_need_usb_body": (
        "Нажмите «Обновить список USB» и выберите найденную точку монтирования (часто /mnt/@usb/…)."
    ),
    "nas_admin.msg_need_disk": "Диск не выбран",
    "nas_admin.msg_need_disk_body": "Нажмите «Обновить диски» и выберите устройство /dev.",
    "nas_admin.msg_need_led": "Нет слота LED",
    "nas_admin.msg_need_led_body": (
        "Нет diskN в /sys/class/leds — используйте «Обновить слоты LED»; модель может не поддерживать индикацию отсеков."
    ),
    "nas_admin.confirm_eject_t": "Извлечь USB?",
    "nas_admin.confirm_eject_b": "Размонтировать/извлечь:\n{path}\n\nУбедитесь, что запись на устройство не выполняется.",
    "nas_admin.confirm_smart_t": "Запустить SMART-тест?",
    "nas_admin.confirm_smart_b": "Цель: {disk}\nТип: {kind}\n\nПримечание: длинные тесты могут длиться долго и нагружать диск.",
    "nas_admin.confirm_maint_t": "Действие обслуживания NAS",
    "nas_admin.confirm_mdcheck_b": (
        "Запустить mdcheck_start.service сейчас?\n\n"
        "Запускает запланированный RAID scrub/проверку (зависит от UGOS/mdadm)."
    ),
    "nas_admin.confirm_fstrim_b": (
        "Запустить fstrim.service сейчас?\n\n"
        "TRIM для поддерживаемых смонтированных файловых систем — возможна краткая нагрузка на Ввод‑Вывод."
    ),
    "nas_admin.confirm_e2scrub_b": (
        "Запустить e2scrub_all.service сейчас?\n\n"
        "Онлайн-проверка метаданных ext4 — возможная нагрузка Ввод‑Вывод."
    ),
    "nas_admin.confirm_led_t": "Идентификация LED?",
    "nas_admin.confirm_led_b": (
        "Отсек {slot}: LED мигает ~12 с (таймер), затем восстанавливает предыдущий режим.\n\n"
        "Только идентификация корпуса — RAID и данные не затрагиваются."
    ),
    "nas_admin.confirm_beep_t": "Протестировать бипер?",
    "nas_admin.confirm_beep_b": "Вызывает /usr/sbin/ugbeep (или запасной beep) — короткий звук.",
    "nas_admin.subtitle_extended": (
        "Расширенное управление: питание/WoL, ежедневное расписание выключения, извлечение USB UGOS, SMART, "
        "обслуживание RAID/ФС, усиление SSH через drop-in с откатом, ключевые службы UGOS, NGINX, earlyOOM, Samba, LED и бипер. "
        "Требуется полный доступ и sudo."
    ),
    "nas_admin.section_power": "Питание и Wake-on-LAN",
    "nas_admin.power_boot": "После потери питания (кнопка питания):",
    "nas_admin.wake_on": "Wake-on-LAN:",
    "nas_admin.btn_power_read": "Читать power.conf",
    "nas_admin.btn_power_save": "Сохранить power.conf",
    "nas_admin.btn_wol_apply": "Записать WoL в power.conf",
    "nas_admin.section_sched_shutdown": "Ежедневное расписание выключения (cron.d)",
    "nas_admin.sched_enable": "Включить ежедневно",
    "nas_admin.sched_daily_time": "Время (ЧЧ:ММ, 24 ч)",
    "nas_admin.btn_sched_read": "Читать cron",
    "nas_admin.btn_sched_write": "Записать cron",
    "nas_admin.btn_usb_ugos_eject": "Извлечение UGOS (USBDiskStop)",
    "nas_admin.btn_smart_log": "Журнал самотеста",
    "nas_admin.btn_mdcheck_progress": "Прогресс",
    "nas_admin.section_ssh": "SSH (drop-in)",
    "nas_admin.ssh_profile": "Профиль",
    "nas_admin.btn_ssh_apply": "Применить профиль",
    "nas_admin.btn_ssh_confirm": "Подтвердить SSH OK",
    "nas_admin.btn_ssh_rollback": "Откат",
    "nas_admin.section_services": "Ключевые службы UGOS",
    "nas_admin.service_name": "Юнит (*.service)",
    "nas_admin.btn_svc_start": "Запуск",
    "nas_admin.btn_svc_stop": "Остановка",
    "nas_admin.btn_svc_restart": "Перезапуск",
    "nas_admin.btn_svc_log": "Журнал",
    "nas_admin.btn_support_snapshot": "Диагностический снимок",
    "nas_admin.section_nginx": "NGINX",
    "nas_admin.btn_nginx_reload": "Перезагрузить (ugnginx)",
    "nas_admin.btn_nginx_recovery": "Восстановление конфигурации (ROM/резервная копия)",
    "nas_admin.section_earlyoom": "earlyOOM",
    "nas_admin.btn_earlyoom_read": "Загрузить файл",
    "nas_admin.btn_earlyoom_save": "Сохранить и перезапустить службу",
    "nas_admin.section_samba": "Samba",
    "nas_admin.smb_share": "Общий ресурс:",
    "nas_admin.btn_smb_refresh": "Обновить ресурсы",
    "nas_admin.btn_smb_recycle_empty": "Очистить корзины",
    "nas_admin.btn_smb_wizard": "Быстрый ресурс",
    "nas_admin.msg_invalid": "Неверный ввод",
    "nas_admin.msg_need_ip": "Сначала введите IP-адрес NAS в заголовке.",
    "nas_admin.msg_power_invalid": "Проверьте значения powerbutton / wakeonlan.",
    "nas_admin.confirm_power_t": "Сохранить power.conf?",
    "nas_admin.confirm_power_b": "После потери питания: {pb}\nWake-on-LAN: {wo}\n\nЗаписывает /etc/power.conf (sudo).",
    "nas_admin.confirm_wol_t": "Записать WoL в power.conf?",
    "nas_admin.confirm_wol_b": "Записывает текущий выбор Wake-on-LAN в /etc/power.conf.",
    "nas_admin.msg_sched_time": "Неверное время — используйте ЧЧ:ММ (24 ч).",
    "nas_admin.confirm_sched_t": "Задать расписание выключения?",
    "nas_admin.confirm_sched_b": "Ежедневно в {h}:{m} — записывает /etc/cron.d/nas_admin_timed_shutdown.",
    "nas_admin.confirm_sched_disable_t": "Удалить расписание выключения?",
    "nas_admin.confirm_sched_disable_b": "Удаляет cron-файл расписания выключения.",
    "nas_admin.usb_busy_t": "USB может использоваться",
    "nas_admin.usb_busy_b": "lsof/fuser сообщают об активности. Продолжить?",
    "nas_admin.confirm_ugos_usb": "Извлечение USB UGOS?\n{path}\n\nВызывает USBDiskStop, sync, размонтирование.",
    "nas_admin.confirm_earlyoom_t": "Сохранить earlyOOM?",
    "nas_admin.confirm_earlyoom_b": "Перезаписывает /etc/default/earlyoom и перезапускает earlyoom.service.",
    "nas_admin.log_smb_shares": "[Samba] ресурсов: {n}.",
    "nas_admin.log_smb_path_missing": "[Samba] Путь не найден — проверьте testparm / имя ресурса.",
    "nas_admin.msg_smb_share": "Выберите ресурс (не «global»).",
    "nas_admin.confirm_recycle_t": "Очистить корзины?",
    "nas_admin.confirm_recycle_b": (
        "Ресурс «{share}»: типичные каталоги корзины будут очищены (возможна нагрузка Ввод‑Вывод)."
    ),
    "nas_admin.smb_wizard_name": "Имя ресурса",
    "nas_admin.smb_wizard_name_p": "Краткое имя (A–Z, 0‑9, . _ -)",
    "nas_admin.smb_wizard_path": "Путь на NAS",
    "nas_admin.smb_wizard_path_p": "Абсолютный, напр. /volume1/folder",
    "nas_admin.msg_smb_path": "Путь должен быть на томе UGOS (напр. /volume1/…).",
    "nas_admin.confirm_smb_wizard_t": "Создать ресурс Samba?",
    "nas_admin.confirm_smb_wizard_b": "Добавить ресурс «{name}» к «{path}» в smb.conf и перезагрузить smbd?",
    "nas_admin.msg_svc_unit": "Укажите юнит (напр. storage_serv.service).",
    "nas_admin.confirm_svc_t": "Подтвердите действие со службой",
    "nas_admin.confirm_svc_b": "{action}\nЮнит:\n{unit}",
    "nas_admin.svc_act_start": "Запуск",
    "nas_admin.svc_act_stop": "Остановка",
    "nas_admin.svc_act_restart": "Перезапуск",
    "nas_admin.nginx_recover_title": "Восстановление NGINX",
    "nas_admin.nginx_recover_prompt": (
        "Введите точно RESTORE для подтверждения (восстанавливает /rom/etc/nginx в /etc/nginx):"
    ),
    "nas_admin.nginx_recover_t2": "Запустить восстановление NGINX?",
    "nas_admin.nginx_recover_b2": "Восстанавливает конфиг NGINX из ROM/резервной копии — возможна краткая пауза.",
    "nas_admin.confirm_ssh_t": "Применить профиль усиления SSH?",
    "nas_admin.confirm_ssh_b": (
        "Профиль «{profile}» как drop-in. После перезагрузки проверьте вход. Без подтверждения автоматический откат через at (~4 мин)."
    ),
    "nas_admin.confirm_ssh_rollback_t": "Откатить конфигурацию SSH?",
    "nas_admin.confirm_ssh_rollback_b": "Восстанавливает резервный drop-in или удаляет файл.",
}
