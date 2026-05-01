# -*- coding: utf-8 -*-
"""Tab „Netzwerkgeräte“ + vollständiger health.telegram_hint für Locales außer de/en."""

from __future__ import annotations

# Nur Locales, die in i18n.py via BACKUP + Basis-Dict gemerged werden.
SUPPLEMENT_DEVICES_TELEGRAM: dict[str, dict[str, str]] = {
    "hr": {
        "tab.devices": "🖧 Mrežni uređaji",
        "nav.devices": "🖧  Uređaji",
        "devices.title": "Uređaji (ona što NAS vidi)",
        "devices.subtitle": (
            "Mreža: ARP/susjedstvo i sl. USB: u lsusb nema kontrolera ili port-hubova — "
            "samo stvarni krajnji uređaji (npr. stickovi); pohrana i putem lsblk kad je TRAN=usb."
        ),
        "devices.search": "Traži uređaje",
        "devices.scanning": "Upit na NAS putem SSH-a…",
        "devices.empty": "(Nema unosa.)",
        "devices.needs_ssh": "Povežite SSH na NAS, zatim ponovo odaberite „Traži uređaje“.",
        "devices.kind_lan": "LAN",
        "devices.kind_usb": "USB",
        "devices.kind_usb_lun": "USB pohrana",
        "devices.col_kind": "Vrsta",
        "devices.col_name": "Naziv / ID",
        "devices.col_ipv4": "IPv4",
        "devices.col_detail": "Detalji",
        "health.telegram_hint": (
            "Token i ID chata dolaze iz ⚙️ postavki. Ovaj odjeljak kontrolira pragove čuvara i testove. "
            "Također: „NAS centralni nadzor“ ispod — isti pragovi, radi na NAS-u putem cron-a "
            "(PC može biti isključen). Napomena: upozorenja o SSH prijavi obično dolaze iz revizije "
            "sigurnosti NAS-a (svaka nova SSH sesija), a ne iz diskovnih pragova ovdje. Ova aplikacija "
            "koristi SSH keepalive kako sesije ne bi često padale (manje ponovnih prijava); na UGOS-u "
            "možete pokušati označiti IP vašeg računala kao pouzdan ili smanjiti tu vrstu obavještenja."
        ),
    },
    "fr": {
        "tab.devices": "🖧 Appareils réseau",
        "nav.devices": "🖧  Appareils",
        "devices.title": "Appareils (vus par le NAS)",
        "devices.subtitle": (
            "Réseau : ARP/voisins, etc. USB : pas de contrôleurs ni hubs de ports dans lsusb — "
            "uniquement les périphériques finaux réels (ex. clés USB) ; stockage aussi via lsblk si TRAN=usb."
        ),
        "devices.search": "Analyser les appareils",
        "devices.scanning": "Interrogation du NAS en SSH…",
        "devices.empty": "(Aucune entrée.)",
        "devices.needs_ssh": "Établissez une session SSH vers le NAS, puis relancez « Analyser les appareils ».",
        "devices.kind_lan": "LAN",
        "devices.kind_usb": "USB",
        "devices.kind_usb_lun": "Volume USB",
        "devices.col_kind": "Type",
        "devices.col_name": "Nom / ID",
        "devices.col_ipv4": "IPv4",
        "devices.col_detail": "Détails",
        "health.telegram_hint": (
            "Le jeton et l'identifiant de chat proviennent des ⚙️ Paramètres. Cette section contrôle "
            "les seuils de surveillance et les tests. Aussi : « surveillance centrale NAS » ci-dessous — "
            "mêmes seuils, exécution sur le NAS via cron (le PC peut être éteint). Note : les alertes de "
            "connexion SSH proviennent souvent de l'audit de sécurité du NAS (chaque nouvelle session SSH), "
            "et non des seuils disque ici. Cette application utilise le keepalive SSH pour que les sessions "
            "tombent moins souvent (moins de reconnexions) ; sur UGOS vous pouvez souvent marquer l'IP de "
            "votre PC comme fiable ou réduire ce type de notification."
        ),
    },
    "es": {
        "tab.devices": "🖧 Dispositivos de red",
        "nav.devices": "🖧  Dispositivos",
        "devices.title": "Dispositivos (vistos por el NAS)",
        "devices.subtitle": (
            "Red: ARP/vecinos, etc. USB: en lsusb no aparecen controladores ni hubs — solo dispositivos finales "
            "reales (p. ej. pendrives); almacenamiento también vía lsblk si TRAN=usb."
        ),
        "devices.search": "Buscar dispositivos",
        "devices.scanning": "Consultando el NAS por SSH…",
        "devices.empty": "(Sin entradas.)",
        "devices.needs_ssh": "Conecte SSH al NAS y pulse otra vez «Buscar dispositivos».",
        "devices.kind_lan": "LAN",
        "devices.kind_usb": "USB",
        "devices.kind_usb_lun": "Volumen USB",
        "devices.col_kind": "Tipo",
        "devices.col_name": "Nombre / ID",
        "devices.col_ipv4": "IPv4",
        "devices.col_detail": "Detalles",
        "health.telegram_hint": (
            "El token y el ID de chat provienen de ⚙️ Configuración. Esta sección controla los umbrales "
            "del vigilante y las pruebas. Además: «vigilancia central NAS» abajo — mismos umbrales, se ejecuta "
            "en el NAS vía cron (el PC puede estar apagado). Nota: las alertas de inicio de sesión SSH suelen "
            "provenir de la auditoría de seguridad del NAS (cada nueva sesión SSH), no de los umbrales de disco "
            "aquí. Esta app usa keepalive SSH para que las sesiones caigan menos a menudo (menos reinicios de "
            "sesión); en UGOS puede marcar la IP de su PC como de confianza o reducir ese tipo de notificación."
        ),
    },
    "it": {
        "tab.devices": "🖧 Dispositivi di rete",
        "nav.devices": "🖧  Dispositivi",
        "devices.title": "Dispositivi (visti dal NAS)",
        "devices.subtitle": (
            "Rete: ARP/vicini, ecc. USB: in lsusb niente controller o hub di porta — solo endpoint reali "
            "(es. chiavette); storage anche via lsblk se TRAN=usb."
        ),
        "devices.search": "Cerca dispositivi",
        "devices.scanning": "Interrogazione del NAS via SSH…",
        "devices.empty": "(Nessuna voce.)",
        "devices.needs_ssh": "Connetti SSH al NAS, poi tocca di nuovo «Cerca dispositivi».",
        "devices.kind_lan": "LAN",
        "devices.kind_usb": "USB",
        "devices.kind_usb_lun": "Volume USB",
        "devices.col_kind": "Tipo",
        "devices.col_name": "Nome / ID",
        "devices.col_ipv4": "IPv4",
        "devices.col_detail": "Dettagli",
        "health.telegram_hint": (
            "Token e ID chat provengono da ⚙️ Impostazioni. Questa sezione controlla soglie di guardia e test. "
            "Inoltre: «sorveglianza centrale NAS» sotto — stesse soglie, eseguita sul NAS via cron (il PC può "
            "essere spento). Nota: gli avvisi su accesso SSH spesso derivano dall'audit di sicurezza del NAS "
            "(ogni nuova sessione SSH), non dalle soglie disco qui. L'app usa keepalive SSH così le sessioni "
            "cadono meno spesso (meno ri-login); su UGOS si può spesso dichiarare attendibile l'IP del PC o "
            "ridurre quel tipo di notifica."
        ),
    },
    "pl": {
        "tab.devices": "🖧 Urządzenia sieciowe",
        "nav.devices": "🖧  Urządzenia",
        "devices.title": "Urządzenia (widziane przez NAS)",
        "devices.subtitle": (
            "Sieć: ARP/sąsiedztwo itd. USB: w lsusb bez kontrolerów ani hubów portów — tylko rzeczywiste urządzenia "
            "końcowe (np. pendrive'y); dyski także przez lsblk gdy TRAN=usb."
        ),
        "devices.search": "Skanuj urządzenia",
        "devices.scanning": "Zapytanie do NAS przez SSH…",
        "devices.empty": "(Brak pozycji.)",
        "devices.needs_ssh": "Nawiąż SSH z NAS-em, następnie ponownie wybierz „Skanuj urządzenia”.",
        "devices.kind_lan": "LAN",
        "devices.kind_usb": "USB",
        "devices.kind_usb_lun": "Wolumen USB",
        "devices.col_kind": "Rodzaj",
        "devices.col_name": "Nazwa / ID",
        "devices.col_ipv4": "IPv4",
        "devices.col_detail": "Szczegóły",
        "health.telegram_hint": (
            "Token i ID czatu pochodzą z ⚙️ Ustawień. Ta sekcja steruje progami strażnika i testami. Dodatkowo: "
            "„centralny monitoring NAS” poniżej — te same progi, działa na NAS-ie przez cron (komputer może być "
            "wyłączony). Uwaga: alerty o logowaniu SSH zwykle pochodzą z audytu bezpieczeństwa NAS (każda nowa sesja "
            "SSH), a nie z progów dysku tutaj. Aplikacja używa keepalive SSH, by sesje rzadziej się zrywały (mniej "
            "ponownych logowań); w UGOS można często zaufać IP komputera lub ograniczyć ten typ powiadomień."
        ),
    },
    "ru": {
        "tab.devices": "🖧 Сетевые устройства",
        "nav.devices": "🖧  Устройства",
        "devices.title": "Устройства (как видит NAS)",
        "devices.subtitle": (
            "Сеть: ARP/соседи и т.п. USB: в lsusb без контроллеров и USB-хабов — только реальные конечные устройства "
            "(например флешки); носители также через lsblk при TRAN=usb."
        ),
        "devices.search": "Сканировать устройства",
        "devices.scanning": "Запрос к NAS по SSH…",
        "devices.empty": "(Нет записей.)",
        "devices.needs_ssh": "Подключите SSH к NAS, затем снова нажмите «Сканировать устройства».",
        "devices.kind_lan": "LAN",
        "devices.kind_usb": "USB",
        "devices.kind_usb_lun": "USB-том",
        "devices.col_kind": "Тип",
        "devices.col_name": "Имя / ID",
        "devices.col_ipv4": "IPv4",
        "devices.col_detail": "Подробности",
        "health.telegram_hint": (
            "Токен и ID чата берутся из ⚙️ Настроек. Этот раздел задаёт пороги сторожа и тесты. Также: «центральный "
            "надзор NAS» ниже — те же пороги, выполняется на NAS через cron (ПК может быть выключен). Примечание: "
            "уведомления о входе по SSH обычно приходят из журнала безопасности NAS (каждая новая SSH-сессия), а не "
            "от дисковых порогов здесь. Приложение использует SSH keepalive, чтобы сессии реже обрывались (меньше "
            "повторных входов); в UGOS можно пометить IP вашего ПК как доверенный или снизить этот тип уведомлений."
        ),
    },
    "tr": {
        "tab.devices": "🖧 Ağ aygıtları",
        "nav.devices": "🖧  Aygıtlar",
        "devices.title": "Aygıtlar (NAS’ın gördüğü)",
        "devices.subtitle": (
            "Ağ: ARP/komşu vb. USB: lsusb’da denetleyici veya port hub yok — yalnızca gerçek uç aygıtlar (ör. "
            "bellek anahtarları); TRAN=usb ise depolama ayrıca lsblk ile."
        ),
        "devices.search": "Aygıtları tara",
        "devices.scanning": "NAS’a SSH ile sorgulanıyor…",
        "devices.empty": "(Kayıt yok.)",
        "devices.needs_ssh": "NAS ile SSH kurun, ardından «Aygıtları tara»ya yeniden basın.",
        "devices.kind_lan": "LAN",
        "devices.kind_usb": "USB",
        "devices.kind_usb_lun": "USB birimi",
        "devices.col_kind": "Tür",
        "devices.col_name": "Ad / kimlik",
        "devices.col_ipv4": "IPv4",
        "devices.col_detail": "Ayrıntılar",
        "health.telegram_hint": (
            "Jeton ve sohbet kimliği ⚙️ Ayarlar’dan gelir. Bu bölüm koruma eşiklerini ve testleri yönetir. Ayrıca: "
            "aşağıdaki «NAS merkezi izleme» — aynı eşikler, cron ile NAS üzerinde çalışır (bilgisayar kapalı olabilir). "
            "Not: SSH oturumu açma uyarıları genelde NAS güvenlik denetiminden gelir (her yeni SSH oturumu), buradaki "
            "disk eşiklerinden değil. Uygulama oturumların daha seyrek düşmesi için SSH keepalive kullanır (daha az "
            "yeniden giriş); UGOS’ta bilgisayarınızın IP’sine güven verebilir veya bu bildirim türünü azaltabilirsiniz."
        ),
    },
    "ko": {
        "tab.devices": "🖧 네트워크 장치",
        "nav.devices": "🖧  장치",
        "devices.title": "장치 (NAS가 보는 대로)",
        "devices.subtitle": (
            "네트워크: ARP/이웃 등. USB: lsusb에는 컨트롤러·포트 허브 없음 — 실제 끝단 장치(예: USB 메모리)만; "
            "TRAN=usb일 때 저장 장치는 lsblk로도 표시."
        ),
        "devices.search": "장치 검색",
        "devices.scanning": "NAS에 SSH로 조회 중…",
        "devices.empty": "(항목 없음.)",
        "devices.needs_ssh": "NAS에 SSH로 연결한 뒤 «장치 검색»을 다시 누르세요.",
        "devices.kind_lan": "LAN",
        "devices.kind_usb": "USB",
        "devices.kind_usb_lun": "USB 볼륨",
        "devices.col_kind": "종류",
        "devices.col_name": "이름 / ID",
        "devices.col_ipv4": "IPv4",
        "devices.col_detail": "상세",
        "health.telegram_hint": (
            "토큰과 채팅 ID는 ⚙️ 설정에서 가져옵니다. 이 섹션에서는 가드 임계값과 테스트를 제어합니다. 또한 아래 "
            "«NAS 중앙 감시» — 동일한 임계값, cron으로 NAS에서 실행(PC 꺼짐 가능). 참고: SSH 로그인 알림은 보통 NAS "
            "보안 감사(새 SSH 세션)에서 오며, 여기 디스크 임계값과는 다릅니다. 이 앱은 SSH keepalive로 세션이 덜 "
            "끊기게 해 재로그인을 줄입니다. UGOS에서는 PC의 IP를 신뢰하도록 하거나 해당 알림 유형을 줄일 수 있습니다."
        ),
    },
    "zh": {
        "tab.devices": "🖧 网络设备",
        "nav.devices": "🖧  设备",
        "devices.title": "设备（NAS 视角）",
        "devices.subtitle": (
            "网络：ARP/邻居等。USB：lsusb 中不含控制器或端口集线器，仅真实终端设备（如 U 盘）；"
            "TRAN=usb 时存储设备另由 lsblk 显示。"
        ),
        "devices.search": "扫描设备",
        "devices.scanning": "正通过 SSH 查询 NAS…",
        "devices.empty": "（无条目。）",
        "devices.needs_ssh": "请先建立到 NAS 的 SSH 连接，再点「扫描设备」。",
        "devices.kind_lan": "局域网",
        "devices.kind_usb": "USB",
        "devices.kind_usb_lun": "USB 卷",
        "devices.col_kind": "类型",
        "devices.col_name": "名称 / ID",
        "devices.col_ipv4": "IPv4",
        "devices.col_detail": "详情",
        "health.telegram_hint": (
            "令牌和聊天 ID 来自 ⚙️ 设置。本节控制守护阈值与测试。另有下方「NAS 中央监视」— 相同阈值，"
            "由 cron 在 NAS 上运行（PC 可关闭）。说明：SSH 登录类提醒多来自 NAS 安全审计（每次新 SSH 会话），"
            "而非此处的磁盘阈值。本应用使用 SSH keepalive 减少会话断开，从而降低重复登录次数；"
            "在 UGOS 上可将您 PC 的 IP 设为受信任或调低该类通知。"
        ),
    },
}
