# -*- coding: utf-8 -*-
"""NAS-Verwaltung — Français (fr)."""

NAS_ADMIN_FR: dict[str, str] = {
    "nas_admin.title": "Gestion NAS (actions)",
    "nas_admin.subtitle": (
        "Maintenance privilégiée du NAS via SSH (sudo) : éjection USB sécurisée, auto-tests SMART, "
        "contrôle RAID et maintenance du système (fstrim/e2scrub), clignotement d’identification d’une baie LED, test du buzzer. "
        "Nécessite « Accès complet » dans l’en-tête et sudo pour l’utilisateur SSH."
    ),
    "nas_admin.section_usb": "USB",
    "nas_admin.section_smart": "Auto-test SMART",
    "nas_admin.section_maintenance": "Maintenance RAID et système de fichiers",
    "nas_admin.section_hw": "LED et buzzer",
    "nas_admin.usb_mount": "Point de montage :",
    "nas_admin.disk": "Disque :",
    "nas_admin.test_type": "Test :",
    "nas_admin.led_slot": "LED de baie :",
    "nas_admin.smart_short": "Court",
    "nas_admin.smart_long": "Long",
    "nas_admin.smart_conv": "Transport (conveyance)",
    "nas_admin.btn_usb_refresh": "Actualiser la liste USB",
    "nas_admin.btn_usb_eject": "Éjection sécurisée",
    "nas_admin.btn_disk_refresh": "Actualiser les disques",
    "nas_admin.btn_smart_start": "Lancer le test SMART",
    "nas_admin.btn_mdcheck": "Lancer le contrôle RAID",
    "nas_admin.btn_mdcheck_status": "État du contrôle RAID",
    "nas_admin.btn_fstrim": "Lancer le TRIM maintenant (fstrim)",
    "nas_admin.btn_e2scrub": "Scrub ext4 (e2scrub_all)",
    "nas_admin.btn_led_refresh": "Actualiser les emplacements LED",
    "nas_admin.btn_led_blink": "Identification LED (clignotement 12 s)",
    "nas_admin.btn_beep": "Test buzzer (ugbeep)",
    "nas_admin.log_usb_done": "[USB] {n} point(s) de montage détecté(s).",
    "nas_admin.log_disk_done": "[Disque] {n} périphérique(s) bloc trouvé(s).",
    "nas_admin.log_led_done": "[LED] {n} emplacement(s) sous /sys/class/leds.",
    "nas_admin.msg_need_usb": "Aucun montage USB",
    "nas_admin.msg_need_usb_body": (
        "Cliquez sur « Actualiser la liste USB » et choisissez un montage détecté (souvent sous /mnt/@usb/…)."
    ),
    "nas_admin.msg_need_disk": "Aucun disque sélectionné",
    "nas_admin.msg_need_disk_body": "Cliquez sur « Actualiser les disques » et choisissez un périphérique /dev.",
    "nas_admin.msg_need_led": "Aucun emplacement LED",
    "nas_admin.msg_need_led_body": (
        "Pas de diskN sous /sys/class/leds — utilisez « Actualiser les emplacements LED » ; ce modèle peut ne pas exposer de LED de baie."
    ),
    "nas_admin.confirm_eject_t": "Éjecter l’USB ?",
    "nas_admin.confirm_eject_b": "Démonter/éjecter :\n{path}\n\nAssurez-vous qu’aucune écriture n’est en cours sur le périphérique.",
    "nas_admin.confirm_smart_t": "Lancer le test SMART ?",
    "nas_admin.confirm_smart_b": (
        "Cible : {disk}\nType : {kind}\n\nRemarque : les tests longs peuvent durer et charger le disque."
    ),
    "nas_admin.confirm_maint_t": "Action de maintenance NAS",
    "nas_admin.confirm_mdcheck_b": (
        "Démarrer mdcheck_start.service maintenant ?\n\n"
        "Déclenche le flux de contrôle/scrub RAID planifié (dépend de la configuration UGOS/mdadm)."
    ),
    "nas_admin.confirm_fstrim_b": (
        "Démarrer fstrim.service maintenant ?\n\n"
        "Effectue le TRIM sur les systèmes de fichiers montés pris en charge — pic d’E/S possible."
    ),
    "nas_admin.confirm_e2scrub_b": (
        "Démarrer e2scrub_all.service maintenant ?\n\n"
        "Vérification en ligne des métadonnées ext4 — charge d’E/S possible."
    ),
    "nas_admin.confirm_led_t": "Identification LED ?",
    "nas_admin.confirm_led_b": (
        "Baie {slot} : la LED clignote ~12 s (minuterie), puis revient à l’état précédent.\n\n"
        "Identification du châssis uniquement — ne modifie pas le RAID ni les données."
    ),
    "nas_admin.confirm_beep_t": "Tester le buzzer ?",
    "nas_admin.confirm_beep_b": "Appelle /usr/sbin/ugbeep (ou repli sur beep) — bref signal sonore.",
    "nas_admin.subtitle_extended": (
        "Administration étendue : alimentation/WoL, arrêt planifié quotidien, éjection USB UGOS, SMART, "
        "maintenance RAID/FS, durcissement SSH avec drop-in et retour arrière, services cœur UGOS, NGINX, earlyOOM, Samba, LED et buzzer. "
        "Nécessite l’accès complet et sudo."
    ),
    "nas_admin.section_power": "Alimentation et Wake-on-LAN",
    "nas_admin.power_boot": "Après une coupure (bouton d’alimentation) :",
    "nas_admin.wake_on": "Wake-on-LAN :",
    "nas_admin.btn_power_read": "Lire power.conf",
    "nas_admin.btn_power_save": "Enregistrer power.conf",
    "nas_admin.btn_wol_apply": "Écrire le WoL dans power.conf",
    "nas_admin.section_sched_shutdown": "Arrêt planifié quotidien (cron.d)",
    "nas_admin.sched_enable": "Activer quotidien",
    "nas_admin.sched_daily_time": "Heure (HH:MM, 24 h)",
    "nas_admin.btn_sched_read": "Lire cron",
    "nas_admin.btn_sched_write": "Écrire cron",
    "nas_admin.btn_usb_ugos_eject": "Éjection UGOS (USBDiskStop)",
    "nas_admin.btn_smart_log": "Journal des auto-tests",
    "nas_admin.btn_mdcheck_progress": "Progression",
    "nas_admin.section_ssh": "SSH (drop-in)",
    "nas_admin.ssh_profile": "Profil",
    "nas_admin.btn_ssh_apply": "Appliquer le profil",
    "nas_admin.btn_ssh_confirm": "Confirmer SSH OK",
    "nas_admin.btn_ssh_rollback": "Retour arrière",
    "nas_admin.section_services": "Services cœur UGOS",
    "nas_admin.service_name": "Unité (*.service)",
    "nas_admin.btn_svc_start": "Démarrer",
    "nas_admin.btn_svc_stop": "Arrêter",
    "nas_admin.btn_svc_restart": "Redémarrer",
    "nas_admin.btn_svc_log": "Journal",
    "nas_admin.section_nginx": "NGINX",
    "nas_admin.btn_nginx_reload": "Recharger (ugnginx)",
    "nas_admin.btn_nginx_recovery": "Récupération de config (ROM/sauvegarde)",
    "nas_admin.section_earlyoom": "earlyOOM",
    "nas_admin.btn_earlyoom_read": "Charger le fichier",
    "nas_admin.btn_earlyoom_save": "Enregistrer et redémarrer le service",
    "nas_admin.section_samba": "Samba",
    "nas_admin.smb_share": "Partage :",
    "nas_admin.btn_smb_refresh": "Actualiser les partages",
    "nas_admin.btn_smb_recycle_empty": "Vider les dossiers corbeille",
    "nas_admin.btn_smb_wizard": "Partage rapide",
    "nas_admin.msg_invalid": "Saisie invalide",
    "nas_admin.msg_power_invalid": "Vérifiez les valeurs powerbutton / wakeonlan.",
    "nas_admin.confirm_power_t": "Enregistrer power.conf ?",
    "nas_admin.confirm_power_b": "Après coupure : {pb}\nWake-on-LAN : {wo}\n\nÉcrit /etc/power.conf (sudo).",
    "nas_admin.confirm_wol_t": "Écrire le WoL dans power.conf ?",
    "nas_admin.confirm_wol_b": "Écrit la sélection Wake-on-LAN actuelle dans /etc/power.conf.",
    "nas_admin.msg_sched_time": "Heure invalide — utilisez HH:MM (24 h).",
    "nas_admin.confirm_sched_t": "Configurer l’arrêt planifié ?",
    "nas_admin.confirm_sched_b": "Quotidien à {h}:{m} — écrit /etc/cron.d/nas_admin_timed_shutdown.",
    "nas_admin.confirm_sched_disable_t": "Supprimer l’arrêt planifié ?",
    "nas_admin.confirm_sched_disable_b": "Supprime le fichier cron de l’arrêt planifié.",
    "nas_admin.usb_busy_t": "L’USB est peut-être utilisé",
    "nas_admin.usb_busy_b": "lsof/fuser signale une activité. Continuer quand même ?",
    "nas_admin.confirm_ugos_usb": "Éjection USB UGOS ?\n{path}\n\nAppelle USBDiskStop, sync, démontage.",
    "nas_admin.confirm_earlyoom_t": "Enregistrer earlyOOM ?",
    "nas_admin.confirm_earlyoom_b": "Écrase /etc/default/earlyoom et redémarre earlyoom.service.",
    "nas_admin.log_smb_shares": "[Samba] {n} partage(s).",
    "nas_admin.log_smb_path_missing": "[Samba] Chemin introuvable — vérifiez testparm / nom du partage.",
    "nas_admin.msg_smb_share": "Choisissez un partage (pas « global »).",
    "nas_admin.confirm_recycle_t": "Vider les dossiers corbeille ?",
    "nas_admin.confirm_recycle_b": (
        "Partage « {share} » : les dossiers corbeille habituels seront vidés (charge d’E/S possible)."
    ),
    "nas_admin.smb_wizard_name": "Nom du partage",
    "nas_admin.smb_wizard_name_p": "Court nom (A–Z, 0–9, . _ -)",
    "nas_admin.smb_wizard_path": "Chemin sur le NAS",
    "nas_admin.smb_wizard_path_p": "Absolu, ex. /volume1/dossier",
    "nas_admin.msg_smb_path": "Le chemin doit être sur un volume UGOS (ex. /volume1/…).",
    "nas_admin.confirm_smb_wizard_t": "Créer un partage Samba ?",
    "nas_admin.confirm_smb_wizard_b": (
        "Ajouter le partage « {name} » vers « {path} » dans smb.conf et recharger smbd ?"
    ),
    "nas_admin.msg_svc_unit": "Indiquez une unité (ex. storage_serv.service).",
    "nas_admin.confirm_svc_t": "Confirmer l’action sur le service",
    "nas_admin.confirm_svc_b": "{action}\nUnité :\n{unit}",
    "nas_admin.svc_act_start": "Démarrer",
    "nas_admin.svc_act_stop": "Arrêter",
    "nas_admin.svc_act_restart": "Redémarrer",
    "nas_admin.nginx_recover_title": "Récupération NGINX",
    "nas_admin.nginx_recover_prompt": (
        "Saisissez exactement RESTORE pour confirmer (restaure /rom/etc/nginx dans /etc/nginx) :"
    ),
    "nas_admin.nginx_recover_t2": "Lancer la récupération NGINX ?",
    "nas_admin.nginx_recover_b2": "Restaure la configuration NGINX depuis la ROM/la sauvegarde — brève interruption possible.",
    "nas_admin.confirm_ssh_t": "Appliquer le profil de durcissement SSH ?",
    "nas_admin.confirm_ssh_b": (
        "Profil « {profile} » en drop-in. Après rechargement, testez la connexion. Sans confirmation, retour automatique via at (~4 min)."
    ),
    "nas_admin.confirm_ssh_rollback_t": "Annuler la config SSH ?",
    "nas_admin.confirm_ssh_rollback_b": "Restaure le drop-in de sauvegarde ou supprime le fichier.",
}
