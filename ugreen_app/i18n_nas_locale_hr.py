# -*- coding: utf-8 -*-
"""NAS-Verwaltung — Hrvatski (hr)."""

NAS_ADMIN_HR: dict[str, str] = {
    "nas_admin.title": "Upravljanje NAS-om (akcije)",
    "nas_admin.subtitle": (
        "Privilegirano održavanje NAS-a putem SSH-a (sudo): sigurno izbacivanje USB-a, SMART samotestovi, "
        "RAID provjera i održavanje OS-a (fstrim/e2scrub), kratko treperenje LED ladicom, probni zvučnik. "
        "Zahtijeva «Potpuni pristup» u zaglavju i sudo za SSH korisnika."
    ),
    "nas_admin.section_usb": "USB",
    "nas_admin.section_smart": "SMART samotest",
    "nas_admin.section_maintenance": "RAID i održavanje datotečnog sustava",
    "nas_admin.section_hw": "LED i zvučnik",
    "nas_admin.usb_mount": "Točka montiranja:",
    "nas_admin.disk": "Disk:",
    "nas_admin.test_type": "Test:",
    "nas_admin.led_slot": "LED ladice:",
    "nas_admin.smart_short": "Kratak",
    "nas_admin.smart_long": "Dug",
    "nas_admin.smart_conv": "Prijenos (conveyance)",
    "nas_admin.btn_usb_refresh": "Osvježi popis USB-a",
    "nas_admin.btn_usb_eject": "Sigurno izbacivanje",
    "nas_admin.btn_disk_refresh": "Osvježi diskove",
    "nas_admin.btn_smart_start": "Pokreni SMART test",
    "nas_admin.btn_mdcheck": "Pokreni RAID provjeru",
    "nas_admin.btn_mdcheck_status": "Stanje RAID provjere",
    "nas_admin.btn_fstrim": "Pokreni TRIM sada (fstrim)",
    "nas_admin.btn_e2scrub": "ext4 čišćenje (e2scrub_all)",
    "nas_admin.btn_led_refresh": "Osvježi LED slotove",
    "nas_admin.btn_led_blink": "LED identifikacija (treperenje 12 s)",
    "nas_admin.btn_beep": "Probni zvučnik (ugbeep)",
    "nas_admin.log_usb_done": "[USB] Detektirano {n} točka/e montiranja.",
    "nas_admin.log_disk_done": "[Disk] Nađeno {n} blok uređaja.",
    "nas_admin.log_led_done": "[LED] {n} slot(ova) ispod /sys/class/leds.",
    "nas_admin.msg_need_usb": "Nema USB montiranja",
    "nas_admin.msg_need_usb_body": (
        "Kliknite «Osvježi popis USB-a» i odaberite montiranje (često pod /mnt/@usb/…)."
    ),
    "nas_admin.msg_need_disk": "Nije odabran disk",
    "nas_admin.msg_need_disk_body": "Kliknite «Osvježi diskove» i odaberite /dev uređaj.",
    "nas_admin.msg_need_led": "Nema LED slota",
    "nas_admin.msg_need_led_body": (
        "Nema diskN ispod /sys/class/leds — pokušajte «Osvježi LED slotove»; model možda nema ladice LED-ove."
    ),
    "nas_admin.confirm_eject_t": "Izbaciti USB?",
    "nas_admin.confirm_eject_b": "Demontiraj/izbaci:\n{path}\n\nPazite da nema aktivnog pisanja na uređaj.",
    "nas_admin.confirm_smart_t": "Pokrenuti SMART test?",
    "nas_admin.confirm_smart_b": "Cilj: {disk}\nVrsta: {kind}\n\nDugi testovi mogu trajati i opterećivati disk.",
    "nas_admin.confirm_maint_t": "Akcija održavanja NAS-a",
    "nas_admin.confirm_mdcheck_b": (
        "Pokrenuti mdcheck_start.service odmah?\n\n"
        "Pokreće zakazani RAID scrub/provjera tijek (ovisno o UGOS/mdadm)."
    ),
    "nas_admin.confirm_fstrim_b": (
        "Pokrenuti fstrim.service odmah?\n\nTRIM za podržane montirane FS — kratko povećanje IO-a moguće."
    ),
    "nas_admin.confirm_e2scrub_b": (
        "Pokrenuti e2scrub_all.service odmah?\n\nOnline provjera ext4 metadata — moguće IO opterećenje."
    ),
    "nas_admin.confirm_led_t": "LED identifikacija?",
    "nas_admin.confirm_led_b": (
        "Ladica {slot}: LED treperi ~12 s (timer), zatim se vraća.\n\n"
        "Samo identifikacija kućišta — ne mijenja RAID/podatke."
    ),
    "nas_admin.confirm_beep_t": "Testirati zvučnik?",
    "nas_admin.confirm_beep_b": "Poziva /usr/sbin/ugbeep (ili beep rezervni) — kratak ton.",
    "nas_admin.subtitle_extended": (
        "Proširena administracija: napajanje/WoL, dnevno zakazano gašenje, UGOS USB izbacivanje, SMART, "
        "RAID/FS održavanje, SSH drop-in sa vraćanjem, jezgrene UGOS usluge, NGINX, earlyOOM, Samba, LED i zvučnik. "
        "Zahtijeva puni pristup i sudo."
    ),
    "nas_admin.section_power": "Napajanje i Wake-on-LAN",
    "nas_admin.power_boot": "Nakon pada napajanja (gumb napajanja):",
    "nas_admin.wake_on": "Wake-on-LAN:",
    "nas_admin.btn_power_read": "Pročitaj power.conf",
    "nas_admin.btn_power_save": "Spremi power.conf",
    "nas_admin.btn_wol_apply": "Zapiši WoL u power.conf",
    "nas_admin.section_sched_shutdown": "Dnevno zakazano gašenje (cron.d)",
    "nas_admin.sched_enable": "Uključi dnevno",
    "nas_admin.sched_daily_time": "Vrijeme (HH:MM, 24 h)",
    "nas_admin.btn_sched_read": "Pročitaj cron",
    "nas_admin.btn_sched_write": "Zapiši cron",
    "nas_admin.btn_usb_ugos_eject": "UGOS izbacivanje (USBDiskStop)",
    "nas_admin.btn_smart_log": "Log samotesta",
    "nas_admin.btn_mdcheck_progress": "Napredak",
    "nas_admin.section_ssh": "SSH (drop-in)",
    "nas_admin.ssh_profile": "Profil",
    "nas_admin.btn_ssh_apply": "Primijeni profil",
    "nas_admin.btn_ssh_confirm": "Potvrdi SSH OK",
    "nas_admin.btn_ssh_rollback": "Vrati nazad",
    "nas_admin.section_services": "Jezgrene UGOS usluge",
    "nas_admin.service_name": "Jedinica (*.service)",
    "nas_admin.btn_svc_start": "Start",
    "nas_admin.btn_svc_stop": "Stop",
    "nas_admin.btn_svc_restart": "Restart",
    "nas_admin.btn_svc_log": "Journal",
    "nas_admin.section_nginx": "NGINX",
    "nas_admin.btn_nginx_reload": "Reload (ugnginx)",
    "nas_admin.btn_nginx_recovery": "Obnova konfiguracije (ROM/sigurnosna kopija)",
    "nas_admin.section_earlyoom": "earlyOOM",
    "nas_admin.btn_earlyoom_read": "Učitaj datoteku",
    "nas_admin.btn_earlyoom_save": "Spremi i ponovno pokreni uslugu",
    "nas_admin.section_samba": "Samba",
    "nas_admin.smb_share": "Share:",
    "nas_admin.btn_smb_refresh": "Osvježi shareove",
    "nas_admin.btn_smb_recycle_empty": "Isprazni recycle mape",
    "nas_admin.btn_smb_wizard": "Brzi share",
    "nas_admin.msg_invalid": "Neispravan unos",
    "nas_admin.msg_power_invalid": "Provjerite powerbutton / wakeonlan vrijednosti.",
    "nas_admin.confirm_power_t": "Spremiti power.conf?",
    "nas_admin.confirm_power_b": "Nakon pada: {pb}\nWoL: {wo}\n\nPiše /etc/power.conf (sudo).",
    "nas_admin.confirm_wol_t": "Zapisati WoL u power.conf?",
    "nas_admin.confirm_wol_b": "Zapisuje trenutni Wake-on-LAN izbor u /etc/power.conf.",
    "nas_admin.msg_sched_time": "Neispravno vrijeme — koristite HH:MM (24 h).",
    "nas_admin.confirm_sched_t": "Postaviti zakazano gašenje?",
    "nas_admin.confirm_sched_b": "Dnevno u {h}:{m} — piše /etc/cron.d/nas_admin_timed_shutdown.",
    "nas_admin.confirm_sched_disable_t": "Ukloniti zakazano gašenje?",
    "nas_admin.confirm_sched_disable_b": "Briše cron datoteku za zakazano gašenje.",
    "nas_admin.usb_busy_t": "USB možda je u upotrebi",
    "nas_admin.usb_busy_b": "lsof/fuser javlja aktivnost. Ipak nastaviti?",
    "nas_admin.confirm_ugos_usb": "UGOS USB izbacivanje?\n{path}\n\nPoziva USBDiskStop, sync, umount.",
    "nas_admin.confirm_earlyoom_t": "Spremiti earlyOOM?",
    "nas_admin.confirm_earlyoom_b": "Prepisuje /etc/default/earlyoom i ponovno pokreće earlyoom.service.",
    "nas_admin.log_smb_shares": "[Samba] {n} share(ova).",
    "nas_admin.log_smb_path_missing": "[Samba] Put nije nađen — provjerite testparm / ime sharea.",
    "nas_admin.msg_smb_share": "Odaberite share (ne «global»).",
    "nas_admin.confirm_recycle_t": "Isprazniti recycle mape?",
    "nas_admin.confirm_recycle_b": "Share «{share}»: uobičajene recycle mape bit će ispražnjene (moguće IO opterećenje).",
    "nas_admin.smb_wizard_name": "Ime sharea",
    "nas_admin.smb_wizard_name_p": "Kratko ime (A–Z, 0-9, . _ -)",
    "nas_admin.smb_wizard_path": "Put na NAS-u",
    "nas_admin.smb_wizard_path_p": "Apsolutno, npr. /volume1/mapu",
    "nas_admin.msg_smb_path": "Put mora biti na UGOS volumenu (npr. /volume1/…).",
    "nas_admin.confirm_smb_wizard_t": "Stvoriti Samba share?",
    "nas_admin.confirm_smb_wizard_b": "Dodati share «{name}» na «{path}» u smb.conf i reload smbd?",
    "nas_admin.msg_svc_unit": "Unesite jedinicu (npr. storage_serv.service).",
    "nas_admin.confirm_svc_t": "Potvrdi akciju usluge",
    "nas_admin.confirm_svc_b": "{action}\nJedinica:\n{unit}",
    "nas_admin.svc_act_start": "Start",
    "nas_admin.svc_act_stop": "Stop",
    "nas_admin.svc_act_restart": "Restart",
    "nas_admin.nginx_recover_title": "NGINX obnova",
    "nas_admin.nginx_recover_prompt": (
        "Upišite točno RESTORE za potvrdu (vraća /rom/etc/nginx u /etc/nginx):"
    ),
    "nas_admin.nginx_recover_t2": "Pokrenuti NGINX obnovu?",
    "nas_admin.nginx_recover_b2": "Vraća NGINX konfiguraciju iz ROM/sigurnosne kopije — moguć kratki prekid.",
    "nas_admin.confirm_ssh_t": "Primijeniti SSH profil ojačanja?",
    "nas_admin.confirm_ssh_b": (
        "Profil «{profile}» kao drop-in. Nakon ponovnog učitavanja testirajte prijavu. "
        "Bez potvrde automatski rollback putem at (~4 min)."
    ),
    "nas_admin.confirm_ssh_rollback_t": "Vratiti SSH konfiguraciju?",
    "nas_admin.confirm_ssh_rollback_b": "Vraća rezervni drop-in ili briše datoteku.",
}
