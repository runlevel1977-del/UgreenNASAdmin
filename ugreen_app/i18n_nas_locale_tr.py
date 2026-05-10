# -*- coding: utf-8 -*-
"""NAS-Verwaltung — Türkçe (tr)."""

NAS_ADMIN_TR: dict[str, str] = {
    "nas_admin.title": "NAS yönetimi (eylemler)",
    "nas_admin.subtitle": (
        "SSH (sudo) ile ayrıcalıklı NAS bakımı: güvenli USB çıkarma, SMART öz-testleri, "
        "RAID denetimi ve işletim sistemi bakımı (fstrim/e2scrub), kısa kasa LED yanıp sönmesi, bip testi. "
        "Başlıkta «Tam erişim» ve SSH kullanıcısı için çalışan sudo gerekir."
    ),
    "nas_admin.section_usb": "USB",
    "nas_admin.section_smart": "SMART öz-testi",
    "nas_admin.section_maintenance": "RAID ve dosya sistemi bakımı",
    "nas_admin.section_hw": "LED ve bip",
    "nas_admin.usb_mount": "Bağlama noktası:",
    "nas_admin.disk": "Disk:",
    "nas_admin.test_type": "Test:",
    "nas_admin.led_slot": "Kasa LED:",
    "nas_admin.smart_short": "Kısa",
    "nas_admin.smart_long": "Uzun",
    "nas_admin.smart_conv": "Taşıma (conveyance)",
    "nas_admin.btn_usb_refresh": "USB listesini yenile",
    "nas_admin.btn_usb_eject": "Güvenli çıkarma",
    "nas_admin.btn_disk_refresh": "Diskleri yenile",
    "nas_admin.btn_smart_start": "SMART testini başlat",
    "nas_admin.btn_mdcheck": "RAID denetimini başlat",
    "nas_admin.btn_mdcheck_status": "RAID denetim durumu",
    "nas_admin.btn_fstrim": "TRIM çalıştır (fstrim)",
    "nas_admin.btn_e2scrub": "ext4 taraması (e2scrub_all)",
    "nas_admin.btn_led_refresh": "LED yuvalarını yenile",
    "nas_admin.btn_led_blink": "LED tanıma (12 sn yanıp sönme)",
    "nas_admin.btn_beep": "Bip testi (ugbeep)",
    "nas_admin.log_usb_done": "[USB] {n} bağlama noktası algılandı.",
    "nas_admin.log_disk_done": "[Disk] {n} blok aygıtı bulundu.",
    "nas_admin.log_led_done": "[LED] /sys/class/leds altında {n} yuva.",
    "nas_admin.msg_need_usb": "USB bağlama yok",
    "nas_admin.msg_need_usb_body": (
        "«USB listesini yenile»ye tıklayıp algılanan bir bağlamayı seçin (genelde /mnt/@usb/…)."
    ),
    "nas_admin.msg_need_disk": "Disk seçilmedi",
    "nas_admin.msg_need_disk_body": "«Diskleri yenile»ye tıklayıp bir /dev aygıtı seçin.",
    "nas_admin.msg_need_led": "LED yuvası yok",
    "nas_admin.msg_need_led_body": (
        "/sys/class/leds altında diskN yok — «LED yuvalarını yenile»yi deneyin; model kasa LED’lerini desteklemiyor olabilir."
    ),
    "nas_admin.confirm_eject_t": "USB çıkarılsın mı?",
    "nas_admin.confirm_eject_b": "Ayır ve çıkar:\n{path}\n\nAygıtta yazma olmadığından emin olun.",
    "nas_admin.confirm_smart_t": "SMART testi başlatılsın mı?",
    "nas_admin.confirm_smart_b": "Hedef: {disk}\nTür: {kind}\n\nNot: uzun testler zaman alır ve diski yüklüyebilir.",
    "nas_admin.confirm_maint_t": "NAS bakım eylemi",
    "nas_admin.confirm_mdcheck_b": (
        "mdcheck_start.service şimdi başlatılsın mı?\n\n"
        "Zamanlanmış RAID scrub/denetim akışını başlatır (UGOS/mdadm yapılandırmasına bağlı)."
    ),
    "nas_admin.confirm_fstrim_b": (
        "fstrim.service şimdi başlatılsın mı?\n\n"
        "Bağlı desteklenen dosya sistemlerinde TRIM — kısa süre IO yükü olabilir."
    ),
    "nas_admin.confirm_e2scrub_b": (
        "e2scrub_all.service şimdi başlatılsın mı?\n\n"
        "Çevrimiçi ext4 meta verisi denetimi — IO yüklü olabilir."
    ),
    "nas_admin.confirm_led_t": "LED tanıma?",
    "nas_admin.confirm_led_b": (
        "Kasa {slot}: LED yaklaşık 12 sn yanıp söner (zamanlayıcı), sonra eski tetiklemeye döner.\n\n"
        "Yalnız kasa tanıması — RAID/veriyi değiştirmez."
    ),
    "nas_admin.confirm_beep_t": "Bip test edilsin mi?",
    "nas_admin.confirm_beep_b": "/usr/sbin/ugbeep (veya beep yedek) çağrılır — kısa bip.",
    "nas_admin.subtitle_extended": (
        "Geniş yönetim: güç/WoL, günlük zamanlanmış kapatma, UGOS USB çıkarma, SMART, "
        "RAID/FS bakımı, geri almalı SSH drop-in sertleştirme, UGOS çekirdek hizmetleri, NGINX, earlyOOM, Samba, LED ve bip. "
        "Tam erişim ve sudo gerekir."
    ),
    "nas_admin.section_power": "Güç ve Wake-on-LAN",
    "nas_admin.power_boot": "Güç kesintisinden sonra (güç düğmesi):",
    "nas_admin.wake_on": "Wake-on-LAN:",
    "nas_admin.btn_power_read": "power.conf oku",
    "nas_admin.btn_power_save": "power.conf kaydet",
    "nas_admin.btn_wol_apply": "WoL’u power.conf’a yaz",
    "nas_admin.section_sched_shutdown": "Günlük zamanlanmış kapatma (cron.d)",
    "nas_admin.sched_enable": "Günlüğü etkinleştir",
    "nas_admin.sched_daily_time": "Saat (SS:DD, 24 s)",
    "nas_admin.btn_sched_read": "cron oku",
    "nas_admin.btn_sched_write": "cron yaz",
    "nas_admin.btn_usb_ugos_eject": "UGOS çıkarma (USBDiskStop)",
    "nas_admin.btn_smart_log": "Öz-test günlüğü",
    "nas_admin.btn_mdcheck_progress": "İlerleme",
    "nas_admin.section_ssh": "SSH (drop-in)",
    "nas_admin.ssh_profile": "Profil",
    "nas_admin.btn_ssh_apply": "Profili uygula",
    "nas_admin.btn_ssh_confirm": "SSH OK doğrula",
    "nas_admin.btn_ssh_rollback": "Geri al",
    "nas_admin.section_services": "UGOS çekirdek hizmetleri",
    "nas_admin.service_name": "Birim (*.service)",
    "nas_admin.btn_svc_start": "Başlat",
    "nas_admin.btn_svc_stop": "Durdur",
    "nas_admin.btn_svc_restart": "Yeniden başlat",
    "nas_admin.btn_svc_log": "Günlük",
    "nas_admin.section_nginx": "NGINX",
    "nas_admin.btn_nginx_reload": "Yeniden yükle (ugnginx)",
    "nas_admin.btn_nginx_recovery": "Yapılandırma kurtarma (ROM/yedek)",
    "nas_admin.section_earlyoom": "earlyOOM",
    "nas_admin.btn_earlyoom_read": "Dosya yükle",
    "nas_admin.btn_earlyoom_save": "Kaydet ve hizmeti yeniden başlat",
    "nas_admin.section_samba": "Samba",
    "nas_admin.smb_share": "Paylaşım:",
    "nas_admin.btn_smb_refresh": "Paylaşımları yenile",
    "nas_admin.btn_smb_recycle_empty": "Geri dönüşüm klasörlerini boşalt",
    "nas_admin.btn_smb_wizard": "Hızlı paylaşım",
    "nas_admin.msg_invalid": "Geçersiz girdi",
    "nas_admin.msg_power_invalid": "powerbutton / wakeonlan değerlerini kontrol edin.",
    "nas_admin.confirm_power_t": "power.conf kaydedilsin mi?",
    "nas_admin.confirm_power_b": "Kesinti sonrası: {pb}\nWake-on-LAN: {wo}\n\n/etc/power.conf yazar (sudo).",
    "nas_admin.confirm_wol_t": "WoL power.conf’a yazılsın mı?",
    "nas_admin.confirm_wol_b": "Geçerli Wake-on-LAN seçimini /etc/power.conf dosyasına yazar.",
    "nas_admin.msg_sched_time": "Geçersiz saat — SS:DD (24 saat) kullanın.",
    "nas_admin.confirm_sched_t": "Zamanlanmış kapatma ayarlansın mı?",
    "nas_admin.confirm_sched_b": "Günlük {h}:{m} — /etc/cron.d/nas_admin_timed_shutdown yazar.",
    "nas_admin.confirm_sched_disable_t": "Zamanlanmış kapatma kaldırılsın mı?",
    "nas_admin.confirm_sched_disable_b": "Zamanlanmış kapatma için cron dosyasını siler.",
    "nas_admin.usb_busy_t": "USB kullanımda olabilir",
    "nas_admin.usb_busy_b": "lsof/fuser etkinlik bildirdi. Yine de devam edilsin mi?",
    "nas_admin.confirm_ugos_usb": "UGOS USB çıkarma?\n{path}\n\nUSBDiskStop, sync, unmount çağrılır.",
    "nas_admin.confirm_earlyoom_t": "earlyOOM kaydedilsin mi?",
    "nas_admin.confirm_earlyoom_b": "/etc/default/earlyoom dosyasının üzerine yazar ve earlyoom.service’i yeniden başlatır.",
    "nas_admin.log_smb_shares": "[Samba] {n} paylaşım.",
    "nas_admin.log_smb_path_missing": "[Samba] Yol bulunamadı — testparm / paylaşım adını kontrol edin.",
    "nas_admin.msg_smb_share": "Bir paylaşım seçin («global» değil).",
    "nas_admin.confirm_recycle_t": "Geri dönüşüm klasörleri boşaltılsın mı?",
    "nas_admin.confirm_recycle_b": (
        "«{share}» paylaşımı: yaygın geri dönüşüm klasörleri boşaltılır (IO yükü olabilir)."
    ),
    "nas_admin.smb_wizard_name": "Paylaşım adı",
    "nas_admin.smb_wizard_name_p": "Kısa ad (A–Z, 0-9, . _ -)",
    "nas_admin.smb_wizard_path": "NAS üzerindeki yol",
    "nas_admin.smb_wizard_path_p": "Mutlak, örn. /volume1/klasör",
    "nas_admin.msg_smb_path": "Yol bir UGOS biriminde olmalı (örn. /volume1/…).",
    "nas_admin.confirm_smb_wizard_t": "Samba paylaşımı oluşturulsun mu?",
    "nas_admin.confirm_smb_wizard_b": "«{name}» paylaşımını «{path}» konumunda smb.conf’a ekleyip smbd’yi yeniden yüklesin mi?",
    "nas_admin.msg_svc_unit": "Bir birim girin (örn. storage_serv.service).",
    "nas_admin.confirm_svc_t": "Hizmet eylemini onayla",
    "nas_admin.confirm_svc_b": "{action}\nBirim:\n{unit}",
    "nas_admin.svc_act_start": "Başlat",
    "nas_admin.svc_act_stop": "Durdur",
    "nas_admin.svc_act_restart": "Yeniden başlat",
    "nas_admin.nginx_recover_title": "NGINX kurtarma",
    "nas_admin.nginx_recover_prompt": (
        "Onaylamak için tam olarak RESTORE yazın (/rom/etc/nginx → /etc/nginx):"
    ),
    "nas_admin.nginx_recover_t2": "NGINX kurtarma çalıştırılsın mı?",
    "nas_admin.nginx_recover_b2": "NGINX yapılandırmasını ROM/yedekten geri yükler — kısa süre kesinti olabilir.",
    "nas_admin.confirm_ssh_t": "SSH sertleştirme profili uygulansın mı?",
    "nas_admin.confirm_ssh_b": (
        "«{profile}» profili drop-in olarak. Yeniden yüklemeden sonra oturumu test edin. "
        "Onaysız yaklaşık 4 dakikada at ile otomatik geri alma."
    ),
    "nas_admin.confirm_ssh_rollback_t": "SSH yapılandırması geri alınsın mı?",
    "nas_admin.confirm_ssh_rollback_b": "Yedek drop-in’i geri yükler veya dosyayı kaldırır.",
}
