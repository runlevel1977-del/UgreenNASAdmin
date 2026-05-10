# -*- coding: utf-8 -*-
"""NAS-Verwaltung — 한국어 (ko)."""

NAS_ADMIN_KO: dict[str, str] = {
    "nas_admin.title": "NAS 관리(작업)",
    "nas_admin.subtitle": (
        "SSH(sudo)를 통한 특권 유지보수: 안전한 USB 꺼내기, SMART 셀프 테스트, "
        "RAID 검사 및 OS 유지보수(fstrim/e2scrub), 베이 LED 짧게 점멸, 부저 테스트. "
        "헤더의 «전체 액세스»와 SSH 사용자에 대한 sudo가 필요합니다."
    ),
    "nas_admin.section_usb": "USB",
    "nas_admin.section_smart": "SMART 셀프 테스트",
    "nas_admin.section_maintenance": "RAID 및 파일 시스템 유지보수",
    "nas_admin.section_hw": "LED 및 부저",
    "nas_admin.usb_mount": "마운트 지점:",
    "nas_admin.disk": "디스크:",
    "nas_admin.test_type": "유형:",
    "nas_admin.led_slot": "베이 LED:",
    "nas_admin.smart_short": "단기",
    "nas_admin.smart_long": "장기",
    "nas_admin.smart_conv": "운송(conveyance)",
    "nas_admin.btn_usb_refresh": "USB 목록 새로 고침",
    "nas_admin.btn_usb_eject": "안전하게 꺼내기",
    "nas_admin.btn_disk_refresh": "디스크 새로 고침",
    "nas_admin.btn_smart_start": "SMART 테스트 시작",
    "nas_admin.btn_mdcheck": "RAID 검사 시작",
    "nas_admin.btn_mdcheck_status": "RAID 검사 상태",
    "nas_admin.btn_fstrim": "지금 TRIM 실행(fstrim)",
    "nas_admin.btn_e2scrub": "ext4 스크럽(e2scrub_all)",
    "nas_admin.btn_led_refresh": "LED 슬롯 새로 고침",
    "nas_admin.btn_led_blink": "LED 식별(12초 점멸)",
    "nas_admin.btn_beep": "부저 테스트(ugbeep)",
    "nas_admin.log_usb_done": "[USB] 마운트 {n}개 감지.",
    "nas_admin.log_disk_done": "[디스크] 블록 장치 {n}개.",
    "nas_admin.log_led_done": "[LED] /sys/class/leds 슬롯 {n}개.",
    "nas_admin.msg_need_usb": "USB 마운트 없음",
    "nas_admin.msg_need_usb_body": (
        "«USB 목록 새로 고침»을 눌러 감지된 마운트를 선택하세요(대개 /mnt/@usb/…)."
    ),
    "nas_admin.msg_need_disk": "디스크가 선택되지 않음",
    "nas_admin.msg_need_disk_body": "«디스크 새로 고침»을 누른 뒤 /dev 장치를 선택하세요.",
    "nas_admin.msg_need_led": "LED 슬롯 없음",
    "nas_admin.msg_need_led_body": (
        "/sys/class/leds에 diskN이 없음 — «LED 슬롯 새로 고침»을 사용하세요. 일부 모델은 베이 LED가 없습니다."
    ),
    "nas_admin.confirm_eject_t": "USB를 꺼내시겠습니까?",
    "nas_admin.confirm_eject_b": "언마운트/꺼내기:\n{path}\n\n디스크에 쓰기가 없어야 합니다.",
    "nas_admin.confirm_smart_t": "SMART 테스트를 시작할까요?",
    "nas_admin.confirm_smart_b": "대상: {disk}\n유형: {kind}\n\n장기 테스트는 시간이 길어지고 디스크 부하가 생길 수 있습니다.",
    "nas_admin.confirm_maint_t": "NAS 유지보수 동작",
    "nas_admin.confirm_mdcheck_b": (
        "지금 mdcheck_start.service를 시작할까요?\n\n"
        "예약된 RAID 스크럽/검사 흐름을 트리거합니다(UGOS/mdadm 설정에 따름)."
    ),
    "nas_admin.confirm_fstrim_b": (
        "지금 fstrim.service를 시작할까요?\n\n"
        "지원되는 마운트된 파일 시스템에서 TRIM — 짧은 I/O 증가가 있을 수 있습니다."
    ),
    "nas_admin.confirm_e2scrub_b": (
        "지금 e2scrub_all.service를 시작할까요?\n\n"
        "온라인 ext4 메타데이터 검사 — I/O 부하가 있을 수 있습니다."
    ),
    "nas_admin.confirm_led_t": "LED 식별?",
    "nas_admin.confirm_led_b": (
        "베이 {slot}: LED가 약 12초(타이머) 점멸 후 원래 상태로 복귀합니다.\n\n"
        "섀시 식별 전용 — RAID/데이터는 변경하지 않습니다."
    ),
    "nas_admin.confirm_beep_t": "부저를 테스트할까요?",
    "nas_admin.confirm_beep_b": "/usr/sbin/ugbeep(또는 beep 대체) 호출 — 짧은 신호음.",
    "nas_admin.subtitle_extended": (
        "확장 관리: 전원/WoL, 매일 예약 종료, UGOS USB 꺼내기, SMART, "
        "RAID/FS 유지보수, 되돌리기 포함 SSH 드롭인, UGOS 핵심 서비스, NGINX, earlyOOM, Samba, LED 및 부저. "
        "전체 액세스와 sudo가 필요합니다."
    ),
    "nas_admin.section_power": "전원 및 Wake-on-LAN",
    "nas_admin.power_boot": "정전 후(전원 버튼 정책):",
    "nas_admin.wake_on": "Wake-on-LAN:",
    "nas_admin.btn_power_read": "power.conf 읽기",
    "nas_admin.btn_power_save": "power.conf 저장",
    "nas_admin.btn_wol_apply": "WoL을 power.conf에 기록",
    "nas_admin.section_sched_shutdown": "매일 예약 종료(cron.d)",
    "nas_admin.sched_enable": "매일 활성화",
    "nas_admin.sched_daily_time": "시간(HH:MM, 24시)",
    "nas_admin.btn_sched_read": "cron 읽기",
    "nas_admin.btn_sched_write": "cron 기록",
    "nas_admin.btn_usb_ugos_eject": "UGOS 꺼내기(USBDiskStop)",
    "nas_admin.btn_smart_log": "셀프 테스트 로그",
    "nas_admin.btn_mdcheck_progress": "진행 상태",
    "nas_admin.section_ssh": "SSH(드롭인)",
    "nas_admin.ssh_profile": "프로필",
    "nas_admin.btn_ssh_apply": "프로필 적용",
    "nas_admin.btn_ssh_confirm": "SSH 확인",
    "nas_admin.btn_ssh_rollback": "되돌리기",
    "nas_admin.section_services": "UGOS 핵심 서비스",
    "nas_admin.service_name": "유닛(*.service)",
    "nas_admin.btn_svc_start": "시작",
    "nas_admin.btn_svc_stop": "중지",
    "nas_admin.btn_svc_restart": "다시 시작",
    "nas_admin.btn_svc_log": "저널",
    "nas_admin.section_nginx": "NGINX",
    "nas_admin.btn_nginx_reload": "다시 로드(ugnginx)",
    "nas_admin.btn_nginx_recovery": "설정 복구(ROM/백업)",
    "nas_admin.section_earlyoom": "earlyOOM",
    "nas_admin.btn_earlyoom_read": "파일 불러오기",
    "nas_admin.btn_earlyoom_save": "저장 후 서비스 재시작",
    "nas_admin.section_samba": "Samba",
    "nas_admin.smb_share": "공유:",
    "nas_admin.btn_smb_refresh": "공유 새로 고침",
    "nas_admin.btn_smb_recycle_empty": "휴지통 비우기",
    "nas_admin.btn_smb_wizard": "빠른 공유",
    "nas_admin.msg_invalid": "잘못된 입력",
    "nas_admin.msg_power_invalid": "powerbutton / wakeonlan 값을 확인하세요.",
    "nas_admin.confirm_power_t": "power.conf를 저장할까요?",
    "nas_admin.confirm_power_b": "정전 후 정책: {pb}\nWake-on-LAN: {wo}\n\n/etc/power.conf 기록(sudo).",
    "nas_admin.confirm_wol_t": "WoL을 power.conf에 기록할까요?",
    "nas_admin.confirm_wol_b": "현재 Wake-on-LAN 선택을 /etc/power.conf에 기록합니다.",
    "nas_admin.msg_sched_time": "시간 형식 오류 — HH:MM(24시) 형식 사용.",
    "nas_admin.confirm_sched_t": "예약 종료를 설정할까요?",
    "nas_admin.confirm_sched_b": "매일 {h}:{m}에 /etc/cron.d/nas_admin_timed_shutdown 기록.",
    "nas_admin.confirm_sched_disable_t": "예약 종료를 제거할까요?",
    "nas_admin.confirm_sched_disable_b": "예약 종료용 cron 파일을 삭제합니다.",
    "nas_admin.usb_busy_t": "USB가 사용 중일 수 있음",
    "nas_admin.usb_busy_b": "lsof/fuser에서 활동이 보고되었습니다. 계속할까요?",
    "nas_admin.confirm_ugos_usb": "UGOS USB 꺼내기?\n{path}\n\nUSBDiskStop, sync, 언마운트 호출.",
    "nas_admin.confirm_earlyoom_t": "earlyOOM을 저장할까요?",
    "nas_admin.confirm_earlyoom_b": "/etc/default/earlyoom을 덮어쓰고 earlyoom.service를 다시 시작합니다.",
    "nas_admin.log_smb_shares": "[Samba] 공유 {n}개.",
    "nas_admin.log_smb_path_missing": "[Samba] 경로를 찾을 수 없음 — testparm / 공유 이름 확인.",
    "nas_admin.msg_smb_share": "공유 하나를 선택하세요(«global» 제외).",
    "nas_admin.confirm_recycle_t": "휴지통 폴더를 비울까요?",
    "nas_admin.confirm_recycle_b": "공유 «{share}»: 일반 휴지통 폴더가 비워짩니다(I/O 부하 가능).",
    "nas_admin.smb_wizard_name": "공유 이름",
    "nas_admin.smb_wizard_name_p": "짧은 이름(A–Z, 0‑9, . _ -)",
    "nas_admin.smb_wizard_path": "NAS 경로",
    "nas_admin.smb_wizard_path_p": "절대 경로, 예: /volume1/folder",
    "nas_admin.msg_smb_path": "경로는 UGOS 볼륨이어야 합니다(예: /volume1/…).",
    "nas_admin.confirm_smb_wizard_t": "Samba 공유를 만들까요?",
    "nas_admin.confirm_smb_wizard_b": "«{path}»에 «{name}» 공유를 smb.conf에 추가하고 smbd를 다시 로드할까요?",
    "nas_admin.msg_svc_unit": "유닛을 입력하세요(예: storage_serv.service).",
    "nas_admin.confirm_svc_t": "서비스 동작 확인",
    "nas_admin.confirm_svc_b": "{action}\n유닛:\n{unit}",
    "nas_admin.svc_act_start": "시작",
    "nas_admin.svc_act_stop": "중지",
    "nas_admin.svc_act_restart": "다시 시작",
    "nas_admin.nginx_recover_title": "NGINX 복구",
    "nas_admin.nginx_recover_prompt": (
        "확인하려면 정확히 RESTORE를 입력(/rom/etc/nginx를 /etc/nginx로 복원):"
    ),
    "nas_admin.nginx_recover_t2": "NGINX 복구를 실행할까요?",
    "nas_admin.nginx_recover_b2": "ROM/백업에서 NGINX 설정 복구 — 짧은 중단 가능.",
    "nas_admin.confirm_ssh_t": "SSH 강화 프로필을 적용할까요?",
    "nas_admin.confirm_ssh_b": (
        "«{profile}» 프로필을 드롭인으로 적용. 재로드 후 로그인을 테스트하세요. "
        "확인 없으면 약 4분 뒤 at로 자동 되돌리기."
    ),
    "nas_admin.confirm_ssh_rollback_t": "SSH 설정 되돌릴까요?",
    "nas_admin.confirm_ssh_rollback_b": "백업 드롭인을 복원하거나 파일을 제거합니다.",
}
