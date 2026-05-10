# -*- coding: utf-8 -*-
"""NAS-Verwaltung — Polski (pl)."""

NAS_ADMIN_PL: dict[str, str] = {
    "nas_admin.title": "Zarządzanie NAS (akcje)",
    "nas_admin.subtitle": (
        "Konserwacja NAS z podwyższonymi uprawnieniami przez SSH (sudo): bezpieczne wysunięcie USB, testy SMART, "
        "kontrola RAID i konserwacja systemu (fstrim/e2scrub), krótkie miganie LED zatoki, test brzęczyka. "
        "Wymaga „Pełny dostęp” w nagłówku oraz sudo dla użytkownika SSH."
    ),
    "nas_admin.section_usb": "USB",
    "nas_admin.section_smart": "Test SMART",
    "nas_admin.section_maintenance": "Konserwacja RAID i systemów plików",
    "nas_admin.section_hw": "LED i brzęczyk",
    "nas_admin.usb_mount": "Punkt montowania:",
    "nas_admin.disk": "Dysk:",
    "nas_admin.test_type": "Rodzaj testu:",
    "nas_admin.led_slot": "LED zatoki:",
    "nas_admin.smart_short": "Krótki",
    "nas_admin.smart_long": "Długi",
    "nas_admin.smart_conv": "Transport (conveyance)",
    "nas_admin.btn_usb_refresh": "Odśwież listę USB",
    "nas_admin.btn_usb_eject": "Bezpieczne wysunięcie",
    "nas_admin.btn_disk_refresh": "Odśwież dyski",
    "nas_admin.btn_smart_start": "Uruchom test SMART",
    "nas_admin.btn_mdcheck": "Uruchom kontrolę RAID",
    "nas_admin.btn_mdcheck_status": "Stan kontroli RAID",
    "nas_admin.btn_fstrim": "Uruchom TRIM teraz (fstrim)",
    "nas_admin.btn_e2scrub": "Czyszczenie ext4 (e2scrub_all)",
    "nas_admin.btn_led_refresh": "Odśwież sloty LED",
    "nas_admin.btn_led_blink": "Identyfikacja LED (12 s migania)",
    "nas_admin.btn_beep": "Test brzęczyka (ugbeep)",
    "nas_admin.log_usb_done": "[USB] Wykryto {n} punkt(ów) montowania.",
    "nas_admin.log_disk_done": "[Dysk] Znaleziono {n} urządzeń blokowych.",
    "nas_admin.log_led_done": "[LED] Znaleziono {n} slot(ów) w /sys/class/leds.",
    "nas_admin.msg_need_usb": "Brak montowania USB",
    "nas_admin.msg_need_usb_body": (
        "Kliknij „Odśwież listę USB” i wybierz punkt montowania (często /mnt/@usb/…)."
    ),
    "nas_admin.msg_need_disk": "Nie wybrano dysku",
    "nas_admin.msg_need_disk_body": "Kliknij „Odśwież dyski” i wybierz urządzenie /dev.",
    "nas_admin.msg_need_led": "Brak slotu LED",
    "nas_admin.msg_need_led_body": (
        "Brak diskN w /sys/class/leds — użyj „Odśwież sloty LED”; ten model może nie mieć LED zatok."
    ),
    "nas_admin.confirm_eject_t": "Wysunąć USB?",
    "nas_admin.confirm_eject_b": "Odmontuj/wysuń:\n{path}\n\nUpewnij się, że nic nie zapisuje na urządzeniu.",
    "nas_admin.confirm_smart_t": "Uruchomić test SMART?",
    "nas_admin.confirm_smart_b": "Cel: {disk}\nTyp: {kind}\n\nUwaga: testy długie mogą trwać i obciążać dysk.",
    "nas_admin.confirm_maint_t": "Czynność konserwacji NAS",
    "nas_admin.confirm_mdcheck_b": (
        "Uruchomić teraz mdcheck_start.service?\n\n"
        "Uruchamia zaplanowany przepływ kontroli/scrub RAID (zależy od konfiguracji UGOS/mdadm)."
    ),
    "nas_admin.confirm_fstrim_b": (
        "Uruchomić teraz fstrim.service?\n\n"
        "Wykonuje TRIM na zamontowanych obsługiwanych systemach plików — możliwy krótki skok I/O."
    ),
    "nas_admin.confirm_e2scrub_b": (
        "Uruchomić teraz e2scrub_all.service?\n\n"
        "Online sprawdzenie metadanych ext4 — możliwe obciążenie I/O."
    ),
    "nas_admin.confirm_led_t": "Identyfikacja LED?",
    "nas_admin.confirm_led_b": (
        "Zatoka {slot}: LED miga ~12 s (timer), potem wraca do poprzedniego stanu.\n\n"
        "Tylko identyfikacja obudowy — nie zmienia RAID/danych."
    ),
    "nas_admin.confirm_beep_t": "Przetestować brzęczyk?",
    "nas_admin.confirm_beep_b": "Wywołuje /usr/sbin/ugbeep (lub zapasowy beep) — krótki sygnał.",
    "nas_admin.subtitle_extended": (
        "Rozszerzona administracja: zasilanie/WoL, codzienne planowe wyłączanie, wysunięcie USB UGOS, SMART, "
        "konserwacja RAID/systemów plików, wzmocnienie SSH z drop-in i rollbackiem, kluczowe usługi UGOS, NGINX, earlyOOM, Samba, LED i brzęczyk. "
        "Wymaga pełnego dostępu i sudo."
    ),
    "nas_admin.section_power": "Zasilanie i Wake-on-LAN",
    "nas_admin.power_boot": "Po utracie zasilania (przycisk zasilania):",
    "nas_admin.wake_on": "Wake-on-LAN:",
    "nas_admin.btn_power_read": "Odczytaj power.conf",
    "nas_admin.btn_power_save": "Zapisz power.conf",
    "nas_admin.btn_wol_apply": "Zapisz WoL do power.conf",
    "nas_admin.section_sched_shutdown": "Codzienne planowe wyłączenie (cron.d)",
    "nas_admin.sched_enable": "Włącz codziennie",
    "nas_admin.sched_daily_time": "Czas (HH:MM, 24 h)",
    "nas_admin.btn_sched_read": "Odczytaj cron",
    "nas_admin.btn_sched_write": "Zapisz cron",
    "nas_admin.btn_usb_ugos_eject": "UGOS wyjście USB (USBDiskStop)",
    "nas_admin.btn_smart_log": "Dziennik testów",
    "nas_admin.btn_mdcheck_progress": "Postęp",
    "nas_admin.section_ssh": "SSH (drop-in)",
    "nas_admin.ssh_profile": "Profil",
    "nas_admin.btn_ssh_apply": "Zastosuj profil",
    "nas_admin.btn_ssh_confirm": "Potwierdź SSH OK",
    "nas_admin.btn_ssh_rollback": "Rollback",
    "nas_admin.section_services": "Kluczowe usługi UGOS",
    "nas_admin.service_name": "Jednostka (*.service)",
    "nas_admin.btn_svc_start": "Start",
    "nas_admin.btn_svc_stop": "Stop",
    "nas_admin.btn_svc_restart": "Restart",
    "nas_admin.btn_svc_log": "Dziennik",
    "nas_admin.section_nginx": "NGINX",
    "nas_admin.btn_nginx_reload": "Przeładuj (ugnginx)",
    "nas_admin.btn_nginx_recovery": "Odzyskiwanie konfiguracji (ROM/kopia)",
    "nas_admin.section_earlyoom": "earlyOOM",
    "nas_admin.btn_earlyoom_read": "Wczytaj plik",
    "nas_admin.btn_earlyoom_save": "Zapisz i uruchom ponownie usługę",
    "nas_admin.section_samba": "Samba",
    "nas_admin.smb_share": "Udział:",
    "nas_admin.btn_smb_refresh": "Odśwież udziały",
    "nas_admin.btn_smb_recycle_empty": "Opróżnij kosze",
    "nas_admin.btn_smb_wizard": "Szybki udział",
    "nas_admin.msg_invalid": "Nieprawidłowe dane",
    "nas_admin.msg_power_invalid": "Sprawdź wartości powerbutton / wakeonlan.",
    "nas_admin.confirm_power_t": "Zapisać power.conf?",
    "nas_admin.confirm_power_b": "Po utracie zasilania: {pb}\nWake-on-LAN: {wo}\n\nZapisuje /etc/power.conf (sudo).",
    "nas_admin.confirm_wol_t": "Zapisać WoL do power.conf?",
    "nas_admin.confirm_wol_b": "Zapisuje bieżący wybór Wake-on-LAN do /etc/power.conf.",
    "nas_admin.msg_sched_time": "Nieprawidłowy czas — użyj HH:MM (24 h).",
    "nas_admin.confirm_sched_t": "Ustawić planowe wyłączenie?",
    "nas_admin.confirm_sched_b": "Codziennie o {h}:{m} — zapisuje /etc/cron.d/nas_admin_timed_shutdown.",
    "nas_admin.confirm_sched_disable_t": "Usunąć planowe wyłączenie?",
    "nas_admin.confirm_sched_disable_b": "Usuwa plik cron planowego wyłączenia.",
    "nas_admin.usb_busy_t": "USB może być używane",
    "nas_admin.usb_busy_b": "lsof/fuser zgłasza aktywność. Kontynuować mimo to?",
    "nas_admin.confirm_ugos_usb": "Wysunąć USB UGOS?\n{path}\n\nWywołuje USBDiskStop, sync, odmontowanie.",
    "nas_admin.confirm_earlyoom_t": "Zapisać earlyOOM?",
    "nas_admin.confirm_earlyoom_b": "Nadpisuje /etc/default/earlyoom i restartuje earlyoom.service.",
    "nas_admin.log_smb_shares": "[Samba] {n} udział(ów).",
    "nas_admin.log_smb_path_missing": "[Samba] Ścieżka nie znaleziona — sprawdź testparm / nazwę udziału.",
    "nas_admin.msg_smb_share": "Wybierz udział (nie „global”).",
    "nas_admin.confirm_recycle_t": "Opróżnić kosze?",
    "nas_admin.confirm_recycle_b": (
        "Udział „{share}”: typowe kosze zostaną opróżnione (możliwe obciążenie I/O)."
    ),
    "nas_admin.smb_wizard_name": "Nazwa udziału",
    "nas_admin.smb_wizard_name_p": "Krótka nazwa (A–Z, 0-9, . _ -)",
    "nas_admin.smb_wizard_path": "Ścieżka na NAS",
    "nas_admin.smb_wizard_path_p": "Bezwzględna, np. /volume1/folder",
    "nas_admin.msg_smb_path": "Ścieżka musi być na wolumenie UGOS (np. /volume1/…).",
    "nas_admin.confirm_smb_wizard_t": "Utworzyć udział Samba?",
    "nas_admin.confirm_smb_wizard_b": "Dodać udział „{name}” w „{path}” do smb.conf i przeładować smbd?",
    "nas_admin.msg_svc_unit": "Podaj jednostkę (np. storage_serv.service).",
    "nas_admin.confirm_svc_t": "Potwierdź akcję usługi",
    "nas_admin.confirm_svc_b": "{action}\nJednostka:\n{unit}",
    "nas_admin.svc_act_start": "Start",
    "nas_admin.svc_act_stop": "Stop",
    "nas_admin.svc_act_restart": "Restart",
    "nas_admin.nginx_recover_title": "Odzyskiwanie NGINX",
    "nas_admin.nginx_recover_prompt": (
        "Wpisz dokładnie RESTORE, aby potwierdzić (przywraca /rom/etc/nginx do /etc/nginx):"
    ),
    "nas_admin.nginx_recover_t2": "Uruchomić odzyskiwanie NGINX?",
    "nas_admin.nginx_recover_b2": "Przywraca konfigurację NGINX z ROM/kopii — krótka przerwa możliwa.",
    "nas_admin.confirm_ssh_t": "Zastosować profil wzmocnienia SSH?",
    "nas_admin.confirm_ssh_b": (
        "Profil „{profile}” jako drop-in. Po przeładowaniu przetestuj logowanie. "
        "Bez potwierdzenia automatyczny rollback przez at (~4 min)."
    ),
    "nas_admin.confirm_ssh_rollback_t": "Cofnąć konfigurację SSH?",
    "nas_admin.confirm_ssh_rollback_b": "Przywraca kopię drop-in lub usuwa plik.",
}
