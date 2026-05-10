# -*- coding: utf-8 -*-
"""NAS-Verwaltung — Italiano (it)."""

NAS_ADMIN_IT: dict[str, str] = {
    "nas_admin.title": "Gestione NAS (azioni)",
    "nas_admin.subtitle": (
        "Manutenzione privilegiata sul NAS via SSH (sudo): espulsione USB sicura, autotest SMART, "
        "controllo RAID e manutenzione OS (fstrim/e2scrub), lampeggio LED bay breve, test buzzer. "
        "Richiede «Accesso completo» nell’intestazione e sudo valido per l’utente SSH."
    ),
    "nas_admin.section_usb": "USB",
    "nas_admin.section_smart": "Autotest SMART",
    "nas_admin.section_maintenance": "Manutenzione RAID e filesystem",
    "nas_admin.section_hw": "LED e buzzer",
    "nas_admin.usb_mount": "Punto di montaggio:",
    "nas_admin.disk": "Disco:",
    "nas_admin.test_type": "Tipo:",
    "nas_admin.led_slot": "LED bay:",
    "nas_admin.smart_short": "Breve",
    "nas_admin.smart_long": "Lungo",
    "nas_admin.smart_conv": "Trasporto (conveyance)",
    "nas_admin.btn_usb_refresh": "Aggiorna elenco USB",
    "nas_admin.btn_usb_eject": "Espulsione sicura",
    "nas_admin.btn_disk_refresh": "Aggiorna dischi",
    "nas_admin.btn_smart_start": "Avvia test SMART",
    "nas_admin.btn_mdcheck": "Avvia controllo RAID",
    "nas_admin.btn_mdcheck_status": "Stato controllo RAID",
    "nas_admin.btn_fstrim": "Esegui TRIM ora (fstrim)",
    "nas_admin.btn_e2scrub": "Scrub ext4 (e2scrub_all)",
    "nas_admin.btn_led_refresh": "Aggiorna slot LED",
    "nas_admin.btn_led_blink": "Identifica LED (lampeggio 12 s)",
    "nas_admin.btn_beep": "Test buzzer (ugbeep)",
    "nas_admin.log_usb_done": "[USB] Trovati {n} mount.",
    "nas_admin.log_disk_done": "[Disco] Trovati {n} dispositivi a blocchi.",
    "nas_admin.log_led_done": "[LED] {n} slot sotto /sys/class/leds.",
    "nas_admin.msg_need_usb": "Nessun mount USB",
    "nas_admin.msg_need_usb_body": (
        "Fare clic su «Aggiorna elenco USB» e scegliere un mount rilevato (spesso sotto /mnt/@usb/…)."
    ),
    "nas_admin.msg_need_disk": "Nessun disco selezionato",
    "nas_admin.msg_need_disk_body": "Fare clic su «Aggiorna dischi» e scegliere un dispositivo /dev.",
    "nas_admin.msg_need_led": "Nessuno slot LED",
    "nas_admin.msg_need_led_body": (
        "Nessun diskN sotto /sys/class/leds — usare «Aggiorna slot LED»; il modello potrebbe non esporre LED bay."
    ),
    "nas_admin.confirm_eject_t": "Espellere USB?",
    "nas_admin.confirm_eject_b": "Smonta/espelle:\n{path}\n\nAssicurarsi che non ci siano scritture in corso.",
    "nas_admin.confirm_smart_t": "Avviare test SMART?",
    "nas_admin.confirm_smart_b": "Destinazione: {disk}\nTipo: {kind}\n\nI test lunghi possono durare e caricare il disco.",
    "nas_admin.confirm_maint_t": "Azione di manutenzione NAS",
    "nas_admin.confirm_mdcheck_b": (
        "Avviare ora mdcheck_start.service?\n\n"
        "Avvia il flusso di scrub/controllo RAID pianificato (dipende da UGOS/mdadm)."
    ),
    "nas_admin.confirm_fstrim_b": (
        "Avviare ora fstrim.service?\n\n"
        "Esegue TRIM su filesystem montati supportati — possibile picco di IO."
    ),
    "nas_admin.confirm_e2scrub_b": (
        "Avviare ora e2scrub_all.service?\n\n"
        "Controllo metadata ext4 online — possibile carico IO."
    ),
    "nas_admin.confirm_led_t": "Identificare LED?",
    "nas_admin.confirm_led_b": (
        "Bay {slot}: il LED lampeggia ~12 s (timer), poi torna allo stato precedente.\n\n"
        "Solo identificazione chassis — non modifica RAID/dati."
    ),
    "nas_admin.confirm_beep_t": "Testare il buzzer?",
    "nas_admin.confirm_beep_b": "Chiama /usr/sbin/ugbeep (o fallback beep) — tono breve.",
    "nas_admin.subtitle_extended": (
        "Amministrazione estesa: alimentazione/WoL, spegnimento pianificato giornaliero, espulsione USB UGOS, SMART, "
        "manutenzione RAID/FS, hardening SSH con drop-in e rollback, servizi core UGOS, NGINX, earlyOOM, Samba, LED e buzzer. "
        "Richiede accesso completo e sudo."
    ),
    "nas_admin.section_power": "Alimentazione e Wake-on-LAN",
    "nas_admin.power_boot": "Dopo mancanza corrente (pulsante alimentazione):",
    "nas_admin.wake_on": "Wake-on-LAN:",
    "nas_admin.btn_power_read": "Leggi power.conf",
    "nas_admin.btn_power_save": "Salva power.conf",
    "nas_admin.btn_wol_apply": "Scrivi WoL in power.conf",
    "nas_admin.section_sched_shutdown": "Spegnimento giornaliero pianificato (cron.d)",
    "nas_admin.sched_enable": "Abilita giornaliero",
    "nas_admin.sched_daily_time": "Ora (HH:MM, 24 h)",
    "nas_admin.btn_sched_read": "Leggi cron",
    "nas_admin.btn_sched_write": "Scrivi cron",
    "nas_admin.btn_usb_ugos_eject": "Espulsione UGOS (USBDiskStop)",
    "nas_admin.btn_smart_log": "Log autotest",
    "nas_admin.btn_mdcheck_progress": "Avanzamento",
    "nas_admin.section_ssh": "SSH (drop-in)",
    "nas_admin.ssh_profile": "Profilo",
    "nas_admin.btn_ssh_apply": "Applica profilo",
    "nas_admin.btn_ssh_confirm": "Conferma SSH OK",
    "nas_admin.btn_ssh_rollback": "Rollback",
    "nas_admin.section_services": "Servizi core UGOS",
    "nas_admin.service_name": "Unità (*.service)",
    "nas_admin.btn_svc_start": "Avvia",
    "nas_admin.btn_svc_stop": "Ferma",
    "nas_admin.btn_svc_restart": "Riavvia",
    "nas_admin.btn_svc_log": "Journal",
    "nas_admin.section_nginx": "NGINX",
    "nas_admin.btn_nginx_reload": "Ricarica (ugnginx)",
    "nas_admin.btn_nginx_recovery": "Ripristino config (ROM/backup)",
    "nas_admin.section_earlyoom": "earlyOOM",
    "nas_admin.btn_earlyoom_read": "Carica file",
    "nas_admin.btn_earlyoom_save": "Salva e riavvia servizio",
    "nas_admin.section_samba": "Samba",
    "nas_admin.smb_share": "Condivisione:",
    "nas_admin.btn_smb_refresh": "Aggiorna condivisioni",
    "nas_admin.btn_smb_recycle_empty": "Svuota cartelle cestino",
    "nas_admin.btn_smb_wizard": "Condivisione rapida",
    "nas_admin.msg_invalid": "Input non valido",
    "nas_admin.msg_power_invalid": "Controllare i valori powerbutton / wakeonlan.",
    "nas_admin.confirm_power_t": "Salvare power.conf?",
    "nas_admin.confirm_power_b": "Dopo mancanza corrente: {pb}\nWake-on-LAN: {wo}\n\nScrive /etc/power.conf (sudo).",
    "nas_admin.confirm_wol_t": "Scrivere WoL in power.conf?",
    "nas_admin.confirm_wol_b": "Scrive la selezione Wake-on-LAN attuale in /etc/power.conf.",
    "nas_admin.msg_sched_time": "Ora non valida — usare HH:MM (24 h).",
    "nas_admin.confirm_sched_t": "Impostare spegnimento pianificato?",
    "nas_admin.confirm_sched_b": "Giornaliero alle {h}:{m} — scrive /etc/cron.d/nas_admin_timed_shutdown.",
    "nas_admin.confirm_sched_disable_t": "Rimuovere spegnimento pianificato?",
    "nas_admin.confirm_sched_disable_b": "Elimina il file cron dello spegnimento pianificato.",
    "nas_admin.usb_busy_t": "USB potrebbe essere in uso",
    "nas_admin.usb_busy_b": "lsof/fuser segnala attività. Continuare comunque?",
    "nas_admin.confirm_ugos_usb": "Espulsione USB UGOS?\n{path}\n\nChiama USBDiskStop, sync, smontaggio.",
    "nas_admin.confirm_earlyoom_t": "Salvare earlyOOM?",
    "nas_admin.confirm_earlyoom_b": "Sovrascrive /etc/default/earlyoom e riavvia earlyoom.service.",
    "nas_admin.log_smb_shares": "[Samba] {n} condivisione/i.",
    "nas_admin.log_smb_path_missing": "[Samba] Percorso non trovato — verificare testparm / nome condivisione.",
    "nas_admin.msg_smb_share": "Scegli una condivisione (non «global»).",
    "nas_admin.confirm_recycle_t": "Svuotare le cartelle cestino?",
    "nas_admin.confirm_recycle_b": (
        "Condivisione «{share}»: le cartelle cestino comuni verranno svuotate (possibile carico IO)."
    ),
    "nas_admin.smb_wizard_name": "Nome condivisione",
    "nas_admin.smb_wizard_name_p": "Nome corto (A–Z, 0–9, . _ -)",
    "nas_admin.smb_wizard_path": "Percorso sul NAS",
    "nas_admin.smb_wizard_path_p": "Assoluto, es. /volume1/cartella",
    "nas_admin.msg_smb_path": "Il percorso deve essere su volume UGOS (es. /volume1/…).",
    "nas_admin.confirm_smb_wizard_t": "Creare condivisione Samba?",
    "nas_admin.confirm_smb_wizard_b": "Aggiungere condivisione «{name}» a «{path}» in smb.conf e ricaricare smbd?",
    "nas_admin.msg_svc_unit": "Indicare un’unità (es. storage_serv.service).",
    "nas_admin.confirm_svc_t": "Confermare azione servizio",
    "nas_admin.confirm_svc_b": "{action}\nUnità:\n{unit}",
    "nas_admin.svc_act_start": "Avvia",
    "nas_admin.svc_act_stop": "Ferma",
    "nas_admin.svc_act_restart": "Riavvia",
    "nas_admin.nginx_recover_title": "Ripristino NGINX",
    "nas_admin.nginx_recover_prompt": "Digitare esattamente RESTORE per confermare (ripristina /rom/etc/nginx in /etc/nginx):",
    "nas_admin.nginx_recover_t2": "Eseguire ripristino NGINX?",
    "nas_admin.nginx_recover_b2": "Ripristina la config NGINX da ROM/backup — possibile breve interruzione.",
    "nas_admin.confirm_ssh_t": "Applicare profilo hardening SSH?",
    "nas_admin.confirm_ssh_b": (
        "Profilo «{profile}» come drop-in. Dopo ricarico, verificare login. Senza conferma rollback automatico con at (~4 min)."
    ),
    "nas_admin.confirm_ssh_rollback_t": "Rollback config SSH?",
    "nas_admin.confirm_ssh_rollback_b": "Ripristina il drop-in di backup o rimuove il file.",
}
