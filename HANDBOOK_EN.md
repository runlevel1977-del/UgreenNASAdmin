# Ugreen NAS Admin – Complete manual for the app and usage

> **“Login Track” tab:** **`## 14. Login Track tab complete`**. **“NAS management” tab:** **`## 15. NAS management tab complete`** (blue PDF headings like other tabs). Short summaries partly in `HANDBUCH_STRUKTURIERT.md`. **ℹ Info → Manual** opens **`HANDBOOK_EN.pdf`** — rebuild with `python tools/build_handbook_en_pdf.py`, or newer chapters will be missing.

This edition is tab-centered: Description, buttons, operation, workflows and error cases are directly together for each area - without scattered addendums at the end.

## 1. Purpose of this manual

### From the area: 1. Purpose of this manual

This manual is written as a complete user guide for the **current app version**. It explains operation **tab by tab**, including input fields, buttons, typical processes, error patterns and sensible procedures in everyday life.
It is **not a short description** and not a marketing text, but rather a working instruction for real operations.

Important: The app works directly on your NAS in many areas. Changes are not “simulated” but directly affect files, services, containers and schedules. That's why this manual always describes **what a button actually triggers** and **when you shouldn't use it**.

---

---

## 2. App logic and security principle

### From the area: 2. App logic and security principle

The app has a modular structure: Dashboard, Scripts, Explorer, NAS↔NAS, Devices, Docker, Health, **NAS management**, Storage, ACL, Snapshots, Backup, Settings.
Almost all functions access the NAS via SSH. Without a valid connection, many actions are meaningless.

A central point is the protection mode:

- In Restricted Mode, risky actions are blocked.
- With `Full Rights` critical buttons are released.
- With 'Restrict' you activate the protection again.

The standard for productive environments is:

1. Analyze in normal mode.
2. Only activate full rights for specific interventions.
3. Restrict again after the procedure.

---

---

## 3. Header complete (all in one place)

### From the area: 3. Header area (header) – current version

Important to classify: The extensive connection fields are in the current UI`Settings`-Tab. The header **no longer** contains the old large connection block.

### 3.1 Header elements and effect

- `⚠ Full Rights` / `🔒 Restrict`
Toggles risk mode. Critical buttons in multiple tabs depend on this.

- Theme button (`☀ Light` / `🌙 Dark`)
Changes the color scheme of the interface.

- `ℹ Info`
Opens the info dialog with document buttons (`README`,`Handbuch`,`CHANGELOG`) and contact area.

- `📸 Screenshot`
Takes a screenshot of the app. Destination folder comes out`Settings -> Pfade -> Screenshot-Pfad`.

- `☕Coffee`
Opens the support link.

- SSH status badge
Shows whether the SSH connection is active.

- Model display
Shows the recognized NAS model as soon as it can be read via SSH.

- **UGOS/OS line** (directly under the model line)  
  After a successful read, shows among other things **`OS_VERSION`** and **`PRETTY_NAME`** from the NAS file **`/etc/os-release`**; if **`OS_IS_BETA=true`**, a **beta** hint is shown. **How it fills:** (1) after **Update everything** in the sidebar — `os-release` is read in the same **batched** SSH round-trip; (2) alternatively on the **first start of dashboard live polling** (Dashboard tab active, live loop begins) if the line is still empty. Without SSH, a short placeholder text remains.

### 3.2 What you shouldn't do in the header

- Do not start critical actions if SSH badge is not connected.
- Do not work permanently with full rights.

---

### From range: 22. Full reference: Header buttons (current UI)

### 22.1 `Full Rights` / `Restrict`

**Purpose:** Security clearance for critical actions.
**Prerequisite:** conscious confirmation.
**Effect:** Switches many`danger`-marked buttons free or closed again.
**Typical Error:** Permanently released and later accidental deletion/system action.

### 22.2 Theme button

**Purpose:** Switch light/dark theme.
**Effect:** purely visual, no NAS change.
**Typical error:** none, just display preference.

### 22.3 `Info`

**Purpose:** Open documentation and contact dialog.
**Effect:** No NAS action, only UI dialog.

### 22.4 `Screenshot`

**Purpose:** Save current app screen.
**Requirement:** Screenshot target path set sensibly in Settings.
**Effect:** PNG file in the target folder.
**Typical error:** empty/invalid destination path.

### 22.5 “Coffee”.

**Purpose:** Open support link.
**Effect:** Browser call.

---

### From the area: 64. Detailed catalog header: every visible button in the context

### 64.1 Coffee

Lightweight action button in the header.
Depending on the app logic, it is usually integrated as a quick trigger or utility function.

### 64.2 Screenshot

Instantly creates a snapshot of the app interface.
Storage location follows that set in Settings`screenshot_dir`.

### 64.3 Info

Opens the info dialog with:

- Document links (README/Manual/Changelog),
- Project/support links,
- Version/note text.

### 64.4 Theme / Language

Change appearance and text background.
Please note special dashboard rule after language change (German only).`de`, otherwise English).

### 64.5 Model display

Updates on connected SSH status and shows the detected NAS model.

### 64.6 UGOS/OS line (below the model)

Adds context: **UGOS build** (`OS_VERSION`) and **base OS** (`PRETTY_NAME` / `VERSION_ID` in one line), optional **beta** flag. Data comes from **`/etc/os-release`** on the NAS. **Refresh:** use **Update everything** (sidebar) or the **first** start of **dashboard live polling** if nothing is shown yet.

---

---

## 4. Sidebar and navigation complete

### From the area: 4. Sidebar and navigation

On the left is the fixed navigation with all main tabs.

### 4.1 Navigation points

- Dashboard
- Scripts
- Explorer
- NAS ↔ NAS
- Devices
- Docker
- System Health
- Login Track
- NAS management
- Storage
- Users (ACL)
- Snapshots
- Backup
- Settings

### 4.2 Tool buttons at the bottom of the sidebar

- `Update everything`
Starts an overall refresh of several areas (scripts list, NAS scan, Docker list, health overview, storage tab, …) over **SSH**. Since **v23.8.1** this usually runs as **one batched sudo command** with markers in the response (fewer round trips). If batching fails, the app **falls back** to the older **sequence of single commands**. The same cycle also reads **`/etc/os-release`** (for the **UGOS/OS line** in the header) and the list of active **`*_serv.service`** units on the NAS (for the **service combobox** in **NAS management**).

- `Health Snapshot`
Saves the current health status as a report.

---

### From area: 41. Full navigation explanation

The sidebar is not just “tab switching”, but a workflow:

1. `Settings` for basics.
2. `Dashboard` for a quick current overview.
3. `Health` for diagnosis.
4. `Docker` / `Scripts` / `Backup` for operational changes.
5. `Storage` / `ACL` / `Snapshots` for deep file and rights work.
6. `NAS↔NAS` for transfers.

Below:

- `Update All`: synchronizes multiple areas (**batched SSH run** since v23.8.1, with fallback; also refreshes **header UGOS/OS** and **NAS management → service list**).
- `Health Snapshot`: documents state.

Both are very valuable before/after changes.

---

---

## 5. Tab Settings complete (fields, buttons, setup, Telegram, SMTP)

### From section: 23. Full reference: Settings tab (fields and buttons)

### 23.1 Main buttons above

- **Load:** resets form to saved status.
- **Apply to current UI:** applies form data directly to the running app.
- **Save:** persists all settings.

### 23.2 Language area

- **Dropdown language:** Selection of the UI language.
- **Apply language:** activates selected language.

### 23.3 Connection fields

- `NAS IP`, `Port`, `User`, `Password`
- `Use SSH key`
- `SSH key path`
- `passphrase`

### 23.4 Connection buttons (including new SSH features)

- **Save connection:** saves all connection fields permanently in config.
- **PW Safe:** stores the current SSH password in the system keyring (safer than plain text in the form).
- **Create SSH key pair:** creates a new key pair on your PC (`ugreen_nas_admin` + `ugreen_nas_admin.pub`), copies the public key to clipboard, and can directly apply the private key path to the form.
- **Install public key on NAS:** does a one-time password-based SSH login to the selected target and appends the public key to `~/.ssh/authorized_keys`.
- **Profile +/x:** create/delete profile.

### 23.4.1 Why this SSH key workflow matters

- Key login removes repeated password entry for day-to-day operations.
- The same private key on your PC can be reused for UGREEN, QNAP, and other Linux systems.
- Automations (script tests, transfers, NAS↔NAS tools) become more stable and faster.
- The password is only needed for initial key installation.

### 23.4.2 Exact step-by-step flow (UGREEN + second NAS/QNAP)

1. In `Settings -> Connection`, first enter correct host/IP, port, user, and password.
2. Click `Create SSH key pair` and pick a target folder.
3. Optionally set a passphrase:
   - with passphrase: RSA 4096 (maximum compatibility),
   - without passphrase: preferred Ed25519 (modern/fast).
4. When prompted, apply the private key path into the form and enable `SSH key`.
5. Click `Save connection` so key path and options are persisted.
6. Click `Install public key on NAS` and select target:
   - **UGREEN:** uses the upper connection fields (IP/port/user/password),
   - **Second NAS/QNAP:** uses the second NAS profile below; SSH port is prompted.
7. After successful installation, the app uses the private key for later SSH logins.

### 23.4.3 What happens technically

- The app installs **only the public key** on the target system.
- The private key stays on your PC and is never copied to NAS.
- During installation, the app intentionally uses a one-time password SSH session (without key auth).
- On target, one key line is added to `~/.ssh/authorized_keys` (or detected as already present).

### 23.4.4 What to avoid

- Do not share the private key or copy it to NAS/cloud folders.
- After switching to key auth, do not keep outdated/wrong passwords in the form.
- For QNAP, enter the actual SSH port (not always 22).
- If anything fails, check in order: SSH service enabled, correct user, writable home directory.

### 23.5 SMB Secondary Profile

Fields:

- Profile name
- Host
- users
- password
- Save password (checkbox)

Buttons:

- Add profile
- Delete profile

### 23.6 Telegram

- Token + Chat ID fields
- Button for secret privacy (visible/hidden)

### 23.7 Email

- Host, Port, User, Password, From, To fields
- Checkboxes STARTTLS and SSL
- Secret privacy button

### 23.8 Paths

- Scripts path
- Compose path
- Explorer Root
- Screenshot destination path
- `Select folder` for screenshot path

### 23.9 Script Notify

Fields:

- script
- channel
- Trigger time

Buttons:

- Refresh
- Add
- Delete
- Sync

### 23.10 Create and install SSH key (complete guide)

This section explains the two new SSH buttons under `Settings -> Connection` so you can complete the full workflow inside the app.

**Button: `Create SSH key pair`**
- Creates a new SSH key pair on your PC (`ugreen_nas_admin` and `ugreen_nas_admin.pub`).
- Optionally asks for a passphrase:
  - with passphrase: RSA 4096 (very compatible),
  - without passphrase: Ed25519 (modern, fast).
- Copies the public key to clipboard.
- Can immediately apply the private key path into the connection fields and enable `SSH key`.

**Button: `Install public key on NAS`**
- Performs a one-time password SSH login (intentionally without key auth for this step).
- Appends the public key to `~/.ssh/authorized_keys` on the target.
- Offers target selection:
  - `UGREEN` via top fields (IP/port/user/password),
  - `Second NAS / QNAP` via SMB profile below (with separate SSH port prompt).

**Why this matters**
- After setup, app logins use key auth instead of entering passwords repeatedly.
- The same key pair can be reused across systems (UGREEN, QNAP, other Linux hosts).
- Automations like script tests, transfers, and NAS↔NAS operations become more stable.

**Recommended procedure (exact)**
1. In `Settings -> Connection`, enter host/IP, port, user, and password correctly.
2. Click `Create SSH key pair` and choose a folder.
3. Optionally set passphrase and confirm key creation.
4. When prompted, apply the private key path into the UI.
5. Click `Save connection`.
6. Click `Install public key on NAS` and choose target system.
7. Confirm success output; later SSH actions run via your private key.

**Important rules**
- Never share the private key or upload it to NAS.
- Only the public key belongs on target systems.
- For QNAP, always use the actual SSH port (do not assume 22).

---

### From the area: 39. Completely set up Telegram (from zero)

This section fully explains the Telegram setup so that Watcher, Tests and Daily Report work properly.

### 39.1 Requirements

You need:

- a Telegram account on mobile or desktop,
- Internet access from NAS (for outgoing connections to Telegram API),
- Access the Settings tab in the app.

### 39.2 Create a bot with BotFather

1. Open Telegram and search for `@BotFather`.
2. Start the chat and send `/start`.
3. Send `/newbot`.
4. Assign a display name for your bot (can be freely chosen).
5. Assign a unique username that ends in `bot` (e.g. `my_nas_alarm_bot`).
6. BotFather responds with a token in the format `123456789:AA...`.

This token is your API key. No shipping without tokens.

### 39.3 Determine chat ID (easy way)

Variant A (individual chat):

1. Open the chat with your new bot.
2. Send him a message (e.g. `test`) once for the chat to exist.
3. Open in browser:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Search for `"chat":{"id":...}` in the JSON response.
5. This number is the chat ID.

Variant B (group):

1. Create or use a group.
2. Add the bot to the group.
3. Send a message to the group.
4. Call `getUpdates` again.
5. Group ID is usually negative (e.g. `-100...`).

### 39.4 Enter token and chat ID in the app

Settings -> Telegram:

- `Bot Token`: Token from BotFather
- `Chat ID`: from `getUpdates`

Thereafter`Speichern`.

### 39.5 Test Telegram in Health

Health tab -> Telegram area:

- Press `Telegram test`.
- Check in the target chat whether the test message arrives.

If no message comes:

1. Check token (typo? old token?).
2. Check chat ID (real chat? Group instead of individual chat?).
3. Check NAS internet access (DNS/Firewall).
4. Look for HTTP error text in logs.

### 39.6 Typical Telegram errors

- **`chat not found`**
Bot hasn't received message from chat yet or wrong chat ID.

- **`Unauthorized`**
Token incorrect or revoked.

- **Message only comes sometimes**
Check cooldown/thresholds in the watcher.

- **Group chat doesn't work**
Bot not in group or missing group chat ID.

---

### From the range: 40. Complete email/SMTP setup (from zero)

### 40.1 Minimum values

Settings -> Email:

- SMTP host
- port
- users
- password
- From
- To
- STARTTLS or SSL suitable for the provider

### 40.2 Typical provider logic

- Port 587: mostly STARTTLS
- Port 465: mostly SSL/SMTPS

Don't activate both blindly. Always set appropriately for the provider.

### 40.3 Testing

- Run watcher test on NAS (if channel `email` or `both`).
- Send daily report test.

If shipping fails:

1. Check DNS resolution on the NAS.
2. Check SMTP credentials.
3. Check port/TLS/SSL combination.
4. Sender address allowed by provider?

---

### From the area: 65. Detailed catalog Settings: every field explained

### 65.1 Connection block

- Host/IP: Target address of the NAS
- Port: SSH port
- User: SSH user
- Password/Key: Authentication
- Sudo: required for privileged actions

### 65.2 Notification block

- Telegram tokens
- Telegram Chat ID
- SMTP Host/Port/User/Pass
- Transmitter/receiver
- TLS/SSL selection

### 65.3 Path/Tooling Block

- Screenshot directory
- local working directories
- optional tool paths

### 65.4 Second NAS profile

- Host
- users
- password
- Share/Path information

Benefits: Backup destination and NAS↔NAS.

---

---

## 6. Tab Dashboard complete (display, fan, operation)

### From Area: 24. Full Reference: Dashboard Tab

### 24.1 Elements

- Dashboard title
- Live notice (when live polling starts, **`/etc/os-release`** is read **once** if the **UGOS/OS header line** is still empty)
- Webcam button
- Metric tiles (including Network with **current interface configuration**, filter, and edit controls — see **42.3**)
- **Fans:** toolbar line **“Probe & map fans…”** (opens the probe/mapping dialog) plus two fan control tiles
- Docker Live
- scheduled script jobs

### 24.2 Fan control and mapping

**Buttons per tile (system left, CPU right):**

- **Silent / Standard / Max / Manual (%)**
- **Apply** (includes optional boot profile as before — see **42.6**)
- **Return UGOS control** (on the left tile only — shared handback to UGOS)

**“Probe & map fans…”**

- **SSH** required (same as the rest of the Dashboard); writes still use **sudo** with your stored password/usual privileges.
- The app scans e.g. **`/proc/it86/fan`** and **`/sys/class/hwmon/.../fan*_input`** and shows a **plain-text report**.
- Per tile you choose:
  - **PWM channel:** **Channel 1** (UGOS-typical `set` / `cpu`) vs **channel 2** (`set2` / `cpu2` / `fan2`) — which hardware path actually supports PWM depends on **model/driver**.
  - **RPM display:** **“Automatic…”** (system vs CPU heuristics as before) or a **specific sensor line** from the scan when several exist.
- **Save** writes locally under **`app_settings.json` → `dashboard`:** **`fan_slot0_use_pwm_secondary`**, **`fan_slot1_use_pwm_secondary`**, **`fan_slot0_rpm_key`**, **`fan_slot1_rpm_key`** (RPM choice lower-case; empty = automatic).
- The existing NAS **boot script** uses the same mapping via **`SLOT0_USE2`** / **`SLOT1_USE2`** in **`ugreen_fan_boot.env`**.

**Only one physical fan:** If the NAS exposes **one** tach source only, the **right** tile stays **without a second RPM** (“not readable”) — **no mirrored duplicate** on both sides.

**Control flow:** choose mode → **Apply** → observe → **Return UGOS control** if needed.

---

### From the area: 42. Dashboard complete: All visible functions in operation

### 42.1 CPU/RAM cards

Purpose: quick load diagnosis.

Interpretation:

- Short peaks are normal.
- permanently high load + high RAM pressure = check deeper in Docker/Health.

### 42.2 Volume Cards

Show occupancy and help early in “plate full” scenarios.

When occupancy increases:

1. Open Storage tab.
2. Determine top consumption.
3. Check backup/log/container paths.

### 42.3 Network

**Throughput (sparklines)**  
Below the configuration block: per physical NIC **estimated RX/TX rates** (from `/proc/net/dev`, from the second measurement onward). Useful for backup windows, NAS↔NAS transfers, and Docker pulls.

**Current configuration (from the NAS)**  
While the Dashboard tab is active and SSH works, the app runs **`ip -j addr`** and **`ip -j route`** on the NAS and shows for the selected interface, among other things:

- operational state, MAC (if reported by `ip`),
- **IPv4** and **prefix length**,
- whether the address appears **DHCP/dynamic** (JSON `dynamic` field) or typically **static**,
- whether this interface carries the **default IPv4 route** and which **gateway** applies.

This is the **live state at sample time** — it may differ from what UGOS stores persistently (the NAS UI may use its own DB/files).

**Choose interface**  
The **Interface** dropdown selects which NIC is described in the **Current configuration** text. The choice is saved **locally** in **`app_settings.json`** as **`dashboard.net_detail_iface`**.

**Limit sparklines to selected NICs**  
The field under the hint **“Sparklines: empty = all; or e.g. eth0,eth1”** only filters the **green throughput sparklines** — not what exists on the NAS. **Empty** = all physical interfaces as before. **Comma-separated names** (semicolon allowed) = only those interfaces in the sparklines, if present. **Save filter** writes **`dashboard.net_monitor_filter`** in **`app_settings.json`**.

**Changing values (advanced)**  
Fields: **IPv4**, **prefix** (e.g. `24`), **gateway**, **mode**:

- **Static (ip):** applies **runtime** settings with `ip -4 addr` / `ip -4 route` (via **sudo**). After reboot, UGOS or a service may override again.
- **DHCP renew:** on the NAS runs **`dhclient`** or **`dhcpcd`** for the chosen interface when available.

**Load from NAS** fills IPv4, prefix, gateway, and mode from the **last received live sample** for the currently selected interface (fills the fields only — nothing is changed until **Apply**).

**Apply (sudo)** needs **Full access** in the header (same danger gate as other risky actions) and shows **confirmation dialogs**. **Wrong IP or gateway can drop your SSH session** — use only in maintenance windows; keep serial/KVM/console in mind.

**Settings and `app_settings.json`**  
When you **Save** in **Settings**, **`dashboard`** and **`docker_update`** are **preserved** in the file so Dashboard preferences are not wiped — including **`net_detail_iface`**, **`net_monitor_filter`**, and **fan mapping** (**`fan_slot0_use_pwm_secondary`**, **`fan_slot1_use_pwm_secondary`**, **`fan_slot0_rpm_key`**, **`fan_slot1_rpm_key`**).

### 42.4 Docker tile

Shows running containers as a leading indicator.
If there is a discrepancy, switch to the Docker tab and check the list/logs.

### 42.5 Script Jobs tile

Shows scheduled jobs and ongoing activities.
Helps with correlation “load increase <-> cron job time”.

### 42.6 Fan control area (complete)

Above both tiles: **“Probe & map fans…”** → dialog with **scan log** and **Save** options for **PWM channel** and **RPM line** per tile (details **24.2**). Without a second tach source the **CPU** tile shows **no second RPM** (single-fan NAS).

Buttons/modes **per tile:**

- Silent
- Standard
- Max
- manual %
- Apply
- Return UGOS control (link on the **left** tile; same shared handback to UGOS as before)

Recommended process:

1. On a **new model** / odd layout: run **“Probe & map fans…”** once and save sensible channel/display choices.
2. Select mode.
3. Apply.
4. Observe for 1–2 minutes.
5. **Return UGOS control** if there are conflicts.

---

### From the area: 62. Practical instructions: Fan control including return to UGOS

1. Open the Dashboard tab.
2. Optional: **“Probe & map fans…”** — read the scan, set **PWM channel** and **RPM display** per tile, **Save**.
3. Read the fan area (system left, CPU right — with one physical fan the right tach may stay empty).
4. Select the desired mode.
5. Click **Apply**.
6. Observe for 1–2 minutes.
7. To end manual control: **Return UGOS control**.
8. Optionally switch the UGOS UI profile (standard/silent) to validate handover.

Error case “UGOS does not respond”:

- Execute the return button again.
- Check health/service status.
- Plan for a short waiting time, as the control does not always start visually immediately.

---

---

## 7. Tab Scripts complete (editor, test, operating sequence)

### From range: 25. Full reference: Scripts tab

### 25.1 Left action buttons

- Backup scripts locally
- Update
- TestHost
- Test Docker
- New file
- Delete
- Schedules
- PowerShell/SSH

### 25.2 Editor buttons

- Template `rsync`
- Template `restic`
- Template `rclone`
- Save (root)
- Save (user)

### 25.3 Fields

- filename
- Editor content

### 25.4 Log

- Runtime/error output for test and save.

---

### From the area: 43. Scripts tab complete: Every action in detail

### 43.1 `Backup` (back up scripts locally)

Purpose: local copy of NAS scripts.

To use:

- Version backup before changes.
- quick recovery.

### 43.2 `Update`

Reloads script list from NAS.

Always press before editing if changes could have been made at the same time.

### 43.3 `Testing (Host)`

Executes selected script directly on the NAS.

To use:

- realistic running test without cron.
- fastest way for syntax/path errors.

### 43.4 `Testing (Docker)`

Tests script in Docker test context.

Useful if the script is actually supposed to run as a Docker job later.

### 43.5 `New File`

Empties processing state for new script start.

### 43.6 `Delete`

Removes script. Critical.

Previously:

1. Check file name.
2. If necessary, make a local backup.

### 43.7 `Schedules`

Opens scheduler drawer and applies target script.

### 43.8 `PowerShell/SSH`

Manual debug/admin access.

### 43.9 Templates (`rsync`, `restic`, `rclone`)

Quick start for typical backup scripts.

Always check parameters after inserting:

- Source path
- Target path
- Credentials
- Excludes

### 43.10 Save (root/user)

`root`:

- for system-level paths if rights are necessary.

`user`:

- for less privileged processes.

Never save unclearly. Understand the target path and rights context beforehand.

---

---

## 8. Scheduler complete (all fields, cron, practice)

### From range: 26. Full reference: Scheduler Drawer

### 26.1 Input fields

- minute
- Hour
- day
- Month
- weekday
- First week (checkbox)

### 26.2 Execution buttons

- As a host job
- As a Docker job

### 26.3 Display

- Plain text time description
- Target script info

---

### From the area: 44. Scheduler complete: fields, interpretation, best practice

Cron fields:

- minute
- Hour
- day
- Month
- weekday

Option:

- first week (for specific monthly logic)

Buttons:

- Host job
- Docker job

Best practices:

1. First define the time technically (“3:30 a.m. daily”).
2. Set fields.
3. Plain text control in the drawer.
4. Write a job.
5. Note cron post check.

---

### From the area: 63. Practical instructions: Create and check the cron job properly

1. Scripts tab, open target shell script.
2. Open `Schedules`.
3. Set cron fields.
4. Read plain text.
5. Write `Host-Job` or `Docker-Job`.
6. Evaluate cron post check.
7. Check job list.
8. Test manually once.

If job doesn't run:

- Check path permissions.
- Check interpreter (`#!/bin/bash` or `python3`).
- Set environment variables explicitly.

---

---

## 9. Tab NAS Explorer complete

### From area: 27. Full reference: Explorer tab

### 27.1 Toolbar

- Scan NAS
- Upload
- Perms 755
- Delete NAS
- Delete PC
- PC->NAS
- NAS->PC
- Search

### 27.2 NAS context menu

- Load into editor
- Perms 755
- Copy path
- Upload files
- Upload folder
- Delete

### 27.3 PC context menu

- Open in Explorer
- Copy path
- Delete

### 27.4 Additional PC buttons

- drives
- High
- Select folder
- Update locally

---

### From the area: 45. Explorer complete: Work safely

### 45.1 `Scan NAS`

Reloads NAS file tree.

### 45.2 `Upload`

Loads local files to NAS.

Actively select the target folder on the left beforehand.

### 45.3 `Perms 755`

Sets rights to target path.

Only use if it is clear why.

### 45.4 `Delete NAS`

Deletes selected NAS objects.

Critical: Double check focus and selection.

### 45.5 `Delete PC`

Deletes selected local files.

### 45.6 `PC -> NAS` and `NAS -> PC`

Transfer between right and left side.

Always check both paths visually before transferring.

### 45.7 Search

Searches in the current NAS context.

### 45.8 Context menus

The context menus are equivalent action triggers to toolbar buttons, not just ads.

---

---

## 10. Tab NAS↔NAS complete

### From range: 28. Full reference: NAS↔NAS tab

### 28.1 Top buttons

- Scan Ugreen
- (Windows) SMB scan

### 28.2 Profile/Status Area

- SMB profile combo
- SMB status label

### 28.3 Context menus

- Upload to the other side
- Delete on current page

---

### From the range: 46. NAS↔NAS complete: SMB workflow

### 46.1 Requirements

- Second NAS profile in Settings complete.
- (Windows) SMB mechanism available.

### 46.2 Process

1. Scan Ugreen.
2. Scan SMB/Shares.
3. Select target paths left/right.
4. Trigger transfer via context menu.
5. Check result/error.

### 46.3 typical errors

- Host not reachable.
- Auth wrong.
- Share hidden/not shared.
- Rights for target path are missing.

---

---

## 11. Network devices tab complete

### From area: 29. Full reference: Device tab

### 29.1 Action

- Search devices

### 29.2 Result

- Table with child/name/IP/detail
- Status label (`scanning`, `empty`, error text)

---

### From the area: 47. Device tab complete

`Geräte suchen`starts Discovery via NAS-SSH.
Display contains LAN/USB information.

Error case:

- without SSH no data.
- If there is a discovery error, status output appears.

---

---

## 12. Tab Docker complete (buttons + operation directly together)

### From range: 30. Full reference: Docker tab

### 30.1 Creation/Catalog Group

- Build Docker
- Docker catalog
- New Docker
- Docker update

### 30.2 Management Group

- Exclusion list
- list
- Stop all containers
- start
- Stop
- Restart
- List (second position in the layout)

### 30.3 Diagnostic group

- Stats
- Inspect
- Delete
- Fix 777

### 30.4 Log/Compose area

- Live log start
- Live Log Stop
- Compose config
- Compose ps
- Compose up -d

### 30.5 fields

- Compose file path
- Container treeview selection

---

### From the area: 48. Docker complete: operation, updates, diagnostics

### 48.1 Create/Catalog

- Build Docker
- Docker catalog
- New Docker

Use catalog for image research, creation for concrete definition.

### 48.2 Update and mass actions

- Docker update (selective)
- list
- Exclusion list
- Stop everything

Selective updates are more production-safe than global.

### 48.3 Runtime Control

- start
- Stop
- Restart

Always work with a fresh list.

### 48.4 Diagnosis

- Stats (resources)
- Inspect (structure)
- Logs (historical/live)

### 48.5 Compose

- Enter compose file
- check config
- ps check
- run up -d

Before`up -d`always double check config.

### 48.6 Critical action `Delete`

Clarify beforehand:

- Where is persistent data located?
- Recovery path available?
- dependent services affected?

---

### From the range: 60. Practical guide: Safely update Docker service

Goal: An existing container should be updated without uncontrolled side effects.

1. Open Docker tab.
2. Click on 'List'.
3. Mark target container.
4. Call `Inspect` and note critical information (volumes, ports, Env).
5. Open `Logs` and note the baseline.
6. Run `Docker Update`.
7. Check the status again with `List` and `Inspect`.
8. Carry out functional testing from an application perspective.
9. In case of errors: stop/start container; if necessary, go back to the previous image.

Why this order is important:

Without a baseline from Inspect/Logs, it is often unclear later whether the error came from the update or was already there before.

---

---

## 13. Tab System & Health complete

### From area: 31. Full reference: Health-Tab

### 31.1 Main buttons

- Refresh Health
- Check RAID
- Check SMART
- Storage
- Scheduler inventory
- Save report
- Restart
- Shutdown

### 31.2 UGOS panel

- Title + refresh
- Service status label

Note:

- `Refresh UGOS services` reloads the current state of core NAS services.
- This panel speeds up troubleshooting (for example, quickly seeing if a core service is down before going deeper into Docker/scripts).

### 31.3 Telegram block

Fields:

- Enabled
- interval
- Disk warn/crit
- Temp
- Cooldown
- Fan min

Buttons:

- Telegram test
- Manual check

### 31.4 Watcher Block

Channel:

- Telegram / Email / Both

Checkboxes:

- Disc
- RAID
- Network ready
- Temp
- docker
- SMART service
- SMB/NFS services
- Maintenance timer
- systemd failed
- fan
- Login failures

Fields:

- Fan min
- Login window
- Login min
- Require containers
- Ignore patterns
- Auto restart names

Buttons:

- Save locally
- Install on NAS
- Test on NAS

### 31.5 Daily Report Block

- Enabled checkbox
- Save locally
- Install on NAS
- test
- **Report content (NAS script):** Since **v23.8.1** the daily report includes an **OS / UGOS** section (excerpt from **`/etc/os-release`**: e.g. `PRETTY_NAME`, `VERSION_ID`, `OS_VERSION`, `OS_IS_BETA`) — useful for support and version checks alongside the existing blocks.

---

## 14. Login Track tab complete

### From the area: Login Track — access by client IP

The **Login Track** tab (sidebar icon **🔐**, between **System & Health** and **NAS management**) shows **sign-ins, failed logins, and active connections** to the NAS — **focused on the client IP** (not internal NAS services). The app reads several log and status sources on the NAS over **SSH**, normalizes lines into **entries**, and lists them in a **read-only** log (text widget). **Live** mode is on by default: you mostly see **new** events since **opening the tab** or since **turning live on**; with **Refresh** or live off you can load **history** instead (about **30 days** `journalctl` window plus log tails).

### 14.1 Purpose and typical use

- **Who** signed in **when** via **SSH**, **SMB**, **UGOS app** (iPhone/PC), **UGOS web**, or an **open TCP connection**?
- **Live watch** while you test sign-in from phone/PC.
- **Review** older access after **Refresh** with live off.
- **Sort** by **date/time**, **IP**, **user**, **source**, or **outcome**; **export** to a text file; optionally **block an IP** via the UGOS block list.

**Scope:** Login Track does **not** replace the Telegram/email **guard** on **System & Health** (thresholds, RAID, temperature). It is a dedicated **access log** in the app.

### 14.2 Prerequisites

- **NAS IP** and **SSH** in the **header** / **Settings** — without a working session you get hints instead of entries.
- **Reading** logs is enough for display; **Block IP** writes **`/ugreen/.config/block_ip_list`** on the NAS over SSH with **sudo**. The **NAS IP** and **loopback** cannot be blocked.
- Leaving the tab **stops** live polling.

### 14.3 Tab layout

**Top**

- **Title** and **subtitle** (sources and live mode).
- **Refresh** — with **live on**: resets baseline and clears the list (waits for new lines). With **live off**: one **history** collect.
- **Export…** — saves the **visible** report (headers, sort, diagnostics) as a **text file** on the PC.
- **Block IP…** — IPv4 dialog; writes to the UGOS **block list** (see **14.9**).

**Sort and filters**

- **Sort by:** **Date / time**, **IP address**, **User**, **Source**, **Outcome**.
- **Newest / Z–A first** — for **date/time**, checked = newest on top; unchecked = oldest on top. **Date/time** sorts by **calendar day**, then **time of day**; rows **without** a parseable timestamp stay **at the bottom** (even when descending).
- **Live (since tab start only)** — default **on**. Baseline on first poll; noted in the header diagnostics.
- **Hide app session pings** — default **on**. Hides repeated UGOS session/VerifyToken noise; keeps real logins.

**List**

- **Read-only** (keyboard edit blocked); **select text** and **right-click** supported.
- **Columns:** `Time | IP | Source | Outcome | User | Detail`
- **Separator lines** between entries.
- Header: host, mode, entry count, sort order, diagnostics, SSH notes on errors.

### 14.4 Data sources on the NAS (technical)

One **bundled SSH command** returns sections marked **`@@SOURCE:…@@`** (history vs live sets differ slightly):

| Section | Content (short) |
|---------|-----------------|
| `ssh_journal` / `auth_log` | **OpenSSH** accepted/failed/invalid, sessions, disconnect |
| `log_serv` | UGOS **log_serv.slog** login and Samba audit |
| `ctl_serv` / `entry_serv` | UGOS app/web login, VerifyToken, biometrics, user-agent |
| `gateway_serv` | **gateway_serv_gin.slog** (login/session related) |
| `journal_ctl` | Short **journalctl** window (live) |
| `nas_conn` | **`ss`**: established TCP to common service ports |
| `last` / `lastlog` | Classic **last** output (history mode) |

The app’s own **collect** command echo is **filtered** so live view is not flooded with **sudo/journalctl** noise from this tool.

### 14.5 Source column (display)

Typical **Source** values:

- **SSH** — SSH sign-in / failure / disconnect
- **UGOS Samba** — SMB per UGOS log
- **UGOS iPhone** / **UGOS PC App** / **UGOS Web** — client from user-agent / module
- **UGOS login** — other UGOS login lines
- **NAS connection** — active connection from **`ss`**
- **last** — **last** output

**Outcome:** e.g. `ok`, `failed`, `info`, `session`.

### 14.6 Live vs history

| Setting | Behavior |
|---------|----------|
| **Live on** (default) | Polling about every **4 s** on tab focus. First round = **baseline**; then **deltas** only. Toggling live or **Refresh** resets baseline. |
| **Live off** | **Refresh** loads **history**; list kept until next refresh. |

**Live filter:** Treats `ok`/`failed` or timestamps near tab start (about **2 minutes** slack) as new — avoids old journal lines filling the live list.

### 14.7 Sorting in detail

- **Date / time:** chronological across mixed formats (`YYYY-MM-DD HH:MM:SS`, ISO with `T`/timezone, journal `Mon DD HH:MM:SS` with **inferred year**). Stable tie-break on original time string.
- **IP:** numeric IPv4, then time.
- **User / source / outcome:** alphabetical, then time.
- **Newest / Z–A first:** reverses primary order; **missing timestamps** stay **at the bottom**.

### 14.8 Export

- **Export…** — file dialog; empty list → load first.
- Exports the **visible** report after filters/sort, not raw SSH.

### 14.9 Block IP

- **Block IP…** or **right-click** a row with an IP.
- Confirmation; writes JSON list **`/ugreen/.config/block_ip_list`** on the NAS. Duplicate IPs are not added twice.
- **Not blockable:** **127.0.0.1** and the header **NAS IP**.
- Effect depends on **UGOS/firewall** using that list.

### 14.10 Troubleshooting and tips

- **“SSH response missing expected log sections”** — connection, permissions, or UGOS paths; read the note block.
- **Empty live list** — no new sign-in after baseline; test from another client; try **Hide app session pings** off.
- **Missing UGOS app login** — some sessions only log **verify/is_login**; check **ctl_serv** / **log_serv**.
- **Many SSH lines from this PC** — your admin session also logs; use the **IP** column for remote clients.
- **Entry cap** in session — large internal buffer; **export** during long live sessions if needed.

---

## 15. NAS management tab complete (actions over SSH/sudo)

A dedicated tab **between** “System & Health”, **Login Track**, and “Storage & Shares”. This tab is for **actions** on the NAS, not passive diagnostics. Commands run over SSH with **sudo**.

### 15.1 Layout, scrolling, and window size

- **Two columns:** All controls on the **left**, a **log** on the **right** showing SSH output for each action.
- **Scrolling (left):** The left column is **taller than the viewport** — scroll vertically with the **mouse wheel** while the pointer is **over the left column** (fields and buttons). The **scrollbar** on the right edge of the left column still works (drag or click track). Scrolling should feel **smooth** (scroll region updates with each wheel step).
- **Log width:** A **sash** (splitter) sits between the two panes. **Drag** it to balance width. On tab open, **~85%** goes to the **left pane**; buttons don’t share one “uniform” width per row, so long German labels cannot force an entire row to overflow. Start narrow on the log if you need more reading space.

### 15.2 Prerequisites and “Full access”

- **Writes or risky actions** (change files, reload services, maintenance, USB eject, SSH profiles, Samba, earlyOOM, NGINX recovery, …): **Full access** in the header and an SSH user with **sudo** (same idea as reboot/shutdown in Health).
- **Read-only / lists / status only:** e.g. USB list, disk list, LED slots, share list, read cron, read `power.conf`, **RAID check status** — often works **without** unlocking danger actions, as long as **SSH is connected**.
- **Always** read the **log** for errors; when unsure, do **read-only** steps first.

### 15.3 Recommended workflow

1. Read the short intro at the top of the tab.
2. **Refresh lists** (USB, disks, shares, …), then pick an item in the dropdown.
3. Read confirmation dialogs before any **write**.
4. After each action, check the **log** (`systemctl`, `smartctl`, `testparm`, etc.).

### 15.4 Areas at a glance

| Area | Purpose (short) | Typical NAS targets |
|------|-----------------|---------------------|
| Power & WoL | After power loss / Wake-on-LAN | `/etc/power.conf` (via `crudini`) |
| Scheduled shutdown | Daily shutdown at fixed time | `/etc/cron.d/nas_admin_timed_shutdown` |
| USB | Safe eject (UGOS) | `USBDiskStop`, `umount`, mounts under e.g. `/mnt/@usb/…` |
| SMART | Self-tests and log | `/dev/sd…`, `smartctl` |
| RAID & filesystem maintenance | RAID scrub, TRIM, ext4 scrub | `mdcheck`, `fstrim`, `e2scrub_all` (systemd) |
| SSH (drop-in) | Extra `sshd` rules with rollback | `/etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf` |
| UGOS core services | Start/stop/restart/log; combobox is **extended** with every active `*_serv` unit after **Update everything** | `*_serv.service` |
| NGINX | Reload or restore ROM config | `ugnginx-reload`, `/rom/etc/nginx`, … |
| earlyOOM | Tune low-memory killer | `/etc/default/earlyoom` |
| Samba | Shares, empty recycle, quick add | `smb.conf`, `testparm` |
| LED & beeper | Chassis identification | `/sys/class/leds/diskN`, `ugbeep` |

### 15.5 Power & Wake-on-LAN

- **Read:** Reads `power_boot` and `wake_on` from `/etc/power.conf` and fills the combos; may show raw lines in the log.
- **Save:** Writes selected values (usually `true`/`false`) with **sudo**. Only change what you understand (UGOS / NAS docs).
- **Write WoL to power.conf:** Writes the **current Wake-on-LAN** selection only (shortcut if you only adjust WoL).

### 15.6 Scheduled daily shutdown

- **App-managed file:** **Write cron** creates/updates only **`/etc/cron.d/nas_admin_timed_shutdown`**. If you never used that button, the file may be missing even though UGOS shuts down daily — the schedule might live in **another** `/etc/cron.d/*` file, **root’s crontab**, under **`/var/spool/cron/...`**, or **`/etc/crontab`** (often the **stock NAS UI** does **not** use the app file).
- **Read cron** prints several blocks: the app file (if present), **listing `/etc/cron.d/`**, **grep** for shutdown/poweroff/halt/**TimedShutdown** (UGOS often uses **`/sbin/TimedShutdown`** in the **root crontab**, not under `/etc/cron.d`), **direct reads of spool files** (when `crontab -l` is empty over SSH), **`/etc/crontab`**, and **systemd timers**. If everything is empty or only generic timers appear, the schedule may exist **only in the UGOS GUI** or another mechanism — check there. **SSH must be connected** (otherwise you only see “Not connected”). The first cron line with a shutdown-related keyword (including **TimedShutdown**) updates the **time fields** (checkbox on) when minute/hour can be parsed (if multiple weekday lines exist, this reflects the first matching line in the output).
- **Enable via this app:** **HH:MM** (24 h), then **Write cron** as above. **Real shutdown** — plan maintenance windows.
- **Disable here:** Removes only the **app file** (with confirmation) — a schedule configured elsewhere on the NAS may **continue** until changed there.

### 15.7 USB (UGOS)

1. **Refresh USB list** — finds typical USB mount paths.
2. Pick a mount, **UGOS eject:** shows **lsof/fuser**; warns if activity is seen; then **`USBDiskStop`** (if present), **`sync`**, **`umount`**. Close apps using the disk first.

### 15.8 SMART

- **Disks:** Refresh list, select a block device.
- **Test:** *short* (minutes), *long* (very long, heavy), *conveyance* — depends on disk/firmware.
- **Self-test log:** Prints recent SMART / test history from logs or `smartctl` as available on the system.

### 15.9 RAID & filesystem maintenance

- **Start RAID check:** Starts the systemd unit used for the scheduled RAID check flow (`mdcheck_start`), as UGOS defines it.
- **Status / Progress:** Read-only — shows current progress / md-related info.
- **fstrim / e2scrub_all:** Starts those **systemd** units — can cause **noticeable IO**; use during quiet periods.

### 14.10 SSH hardening (drop-in)

- **Profile** (*high* / *middle* / *low*): Writes a **drop-in** under `sshd_config.d`, runs **`sshd -t`** and **`systemctl reload ssh`** (or restart).
- **Auto-rollback:** If `at` exists on the NAS, schedules **delayed rollback** unless you confirm in time.
- **Confirm SSH OK:** Creates a **flag file** on the NAS and **removes** the planned `at` job — only click after a **second** SSH session succeeds.
- **Rollback:** Restores the **backup** of the old file or removes the drop-in if you get locked out.

**Important:** For *high*, verify all clients support the chosen algorithms.

### 15.11 UGOS core services

- **Dropdown:** Starts from a **fixed core list** of typical `*_serv` names. After each successful **Update everything** (sidebar), the app **appends every other active** unit whose name ends in **`_serv.service`** (sorted, no duplicates) — extra UGOS package services appear without waiting for an app update.
- **Start / Stop / Restart:** `systemctl` — may briefly interrupt services.
- **Journal:** Recent journal lines for the selected unit.
- **Support snapshot** (next to **Journal**, read-only): Writes to this tab’s **right-hand log** e.g. **`uname -a`**, an excerpt from **`/etc/os-release`**, a short **`journalctl`** slice for **`entry_serv`**, and **tail excerpts** from typical UGOS logs (`storage_serv`, `gateway_serv`, `docker_serv`, `networking.log`, `syslog`). **No** writes to NAS config — meant to **collect diagnostics** for support (copy text). **Requires** NAS IP in the header and SSH; if IP is missing, a warning dialog appears.

### 15.12 NGINX

- **Reload:** Runs UGOS **reload** (or `systemctl reload nginx`) and shows short status.
- **Config recovery:** After typing **`RESTORE`** in the dialog — copies **ROM/default nginx** into `/etc/nginx` and overwrites live config there. **Custom edits can be lost** — have backups.

### 15.13 earlyOOM

- **Load / Save:** Edits `/etc/default/earlyoom` and restarts the service. Parameter syntax matters — wrong settings can worsen OOM behavior.

### 15.14 Samba

1. **Refresh shares** — fills list from `testparm` / `smb.conf` (not `global` as target).
2. **Empty recycle:** Resolves share path and deletes contents of common **recycle** folders — **irreversible** for those files.
3. **Quick share:** Appends a simple block to `smb.conf`, validates with `testparm`, reloads **`smbd`**. Path must match a **UGOS volume** (e.g. `/volume1/…`).

### 15.15 LED & beeper

- **Refresh LED slots**, pick `diskN`, **Identify:** ~12 s blink to match bay to disk.
- **Beeper:** Short test tone via UGOS tool (model-dependent).

---

### From the area: 49. Health complete: All blocks working together

Health is a diagnostic center, not just a display.

### 49.1 Main buttons

- Refresh = overall condition
- RAID/SMART/Storage = partial analysis
- Scheduler inventory = quick check of scheduled jobs and status
- Save report = documentation

### 49.2 System buttons

- Restart
- Shutdown

Only during the scheduled maintenance window.

### 49.3 UGOS Dashboard

Quick look at core services.

### 49.4 Telegram Instant Monitor

Useful for local testing without full watcher deployment.

### 49.5 NAS Watcher

Configuration + Deploy + Test in the same area.

### 49.6 Daily Report

Daily status report (not an alarm replacement, but a history).

---

### From the area: 59. Practical instructions: Telegram alerting really robust

Many setups fail not because of the bot, but because of peripheral conditions. This complete sequence ensures a robust result:

1. Create bot (`@BotFather`, `/newbot`).
2. Secure tokens (do not post in screenshots).
3. Define target chat (individual chat or group).
4. Determine chat ID via `getUpdates`.
5. Enter token/chat ID in Settings.
6. Save.
7. Run Telegram test in the Health tab.
8. Confirm test message.
9. Deploy NAS Watcher.
10. Send watcher test.
11. Send Daily Report Test.
12. Check in the next 24 hours whether periodic messages arrive.

If individual steps fail, never do everything again immediately. Always keep the latest working version as a reference.

---

### From the area: 66. Detailed catalog Health-Watcher switch

Each switch defines whether a specific check should be active in the Watcher.

- UPS check: NUT status
- UGOS core services: core services
- SMART daemon: smartd active/enabled
- Network ready: wait-online service
- File services: SMB/NFS/wsdd2
- Maintenance timers: trim/sysstat/logrotate/backups
- RAID checks: mdstat/mdcheck
- Docker runtime checks

Recommendation:

First activate the security and availability critical checks. Then expand gradually to avoid a flood of alarms.

---

---

## 16. Tab Storage & Sharing complete

### From range: 32. Full reference: Storage tab

Buttons:

- Volumes/df
- Shares
- Refresh all
- Top20
- Disk scan
- Image to PC
- Image to NAS
- Restore from PC
- Restore from NAS

Fields:

- Top path
- Device combo
- Remote Image Path

---

### From the range: 50. Storage complete

### 50.1 Volumes/Shares

Row of buttons for status recording.

### 50.2 Top20

Find the largest directories based on paths.

### 50.3 Disk Image Operations

Strong tool for special cases.

Before each image/restore action:

1. Clearly select device.
2. Check target path.
3. plan enough memory/time.

---

---

## 17. Tab ACL complete

### From range: 33. Full reference: ACL tab

Buttons:

- Ads (stat)
- UGACL info
- chmod 755
- chmod 777 rec
- Apply chmod
- apply chown
- Users
- Groups

Fields:

- Target path
- chmod mode
- chown value

---

### From the range: 51. ACL complete

### 51.1 Diagnosis first

- Show
- UGACL info

### 51.2 Changes thereafter

- chmod 755 / 777 rec / custom
- chown apply

Rule:

- First test small, then roll out large.

---

---

## 18. Snapshots tab complete

### From range: 34. Full reference: Snapshots tab

Buttons:

- detect backend
- btrfs list
- zfs list
- snapper list
- btrfs create
- zfs create
- snapper create
- btrfs delete
- zfs delete
- snapper delete

Field:

- Base path

---

### From the range: 52. Snapshots complete

### 52.1 Detect backend

Necessary to select appropriate commands.

### 52.2 Lists and Creating

Before creating:

- Check base path.

### 52.3 Delete

Only with clear identification of the snapshot and fallback plan.

---

---

## 19. Tab Backup complete (Backup + Restore + Schedules together)

### From Range: 35. Full Reference: Backup Tab

### 35.1 Backup Block Buttons

- Docker+Scripts Backup
- User data backup
- All data backup
- Refresh Lists

### 35.2 Backup Fields

- Scope combo
- Volume combo
- User combo
- Dest mode combo
- NAS profile combo
- PCpath
- USB combo
- optional remove-on-copy checkbox

### 35.3 Restore block

Fields:

- Source mode (`nas`/`pc`)
- Archive path
- Target path

Buttons:

- Select file
- Start restore

### 35.4 Scheduled Backup

Buttons:

- Load from NAS
- Save to NAS
- Remove
- Create/Update

Fields:

- Job label
- Job type
- Cron fields
- Additional options

---

### From the range: 53. Backup complete

### 53.1 Scope/Volume/User

Controls what is backed up.

### 53.2 Target mode

- NAS
- PC
- USB
- second NAS profile

### 53.3 Backup buttons

- Docker+Scripts
- User Data
- All Data

### 53.4 Restore

Fields:

- source mode
- source archive
- target path

Buttons:

- file picker
- restore start

### 53.5 Scheduled Backup

Complete job management with cron logic.

---

### From the area: 61. Practical instructions: Backup and restore with verification

### 61.1 Create a full backup

1. Open backup tab.
2. Filter Scope/Volume/User.
3. Set target mode (NAS/PC/USB/second NAS).
4. Choose the appropriate backup button.
5. Check run.
6. Document archive path.

### 61.2 Perform a restore

1. Set source mode.
2. Select Source Archive.
3. Set target path.
4. Click 'Start Restore'.
5. Result check:
   - do files exist?
   - Are rights correct?
   - are services running again?

### 61.3 Follow-up inspection

- Health Refresh
- Test the affected app/container
- optional snapshot for a new stable stand

---

### From the area: 67. Detailed catalog backup-restore fields

### 67.1 Source Mode

Defines from which context the archive source comes:

- NAS file system
- local file system
- USB medium

### 67.2 Source Archives

Path to the specific backup file (e.g. tar.gz).
Must be accessible for the selected source mode.

### 67.3 Target Path

Restore target on NAS.

Important:

- Rights available?
- enough space?
- Target empty/overwritable?

---

### From the area: 76. Full workflow D: Backup strategy for multiple targets

The goal is to not just have a backup, but a usable recovery concept.

Strategy:

1. Primary target NAS internal (fast).
2. Secondary objective second NAS (risk separation).
3. Optional USB/offline for emergencies.

Implementation in the app:

1. Complete settings with second NAS.
2. Backup tab Select target mode for each run.
3. Set daily/weekly jobs in the scheduler.
4. Monthly restore test on test path.

Rule for real security:

A backup is only considered reliable once a restore has been tested successfully.

---

## 20. Info dialog complete

### From the area: 54. Info dialog complete

Document buttons:

- README
- manual
- CHANGELOG

Other elements:

- YouTube
- Support link
- Email contact
- About text

---

---

## 21. Overall operations, checklists, troubleshooting

### From the range: 19. Complete operation order (recommended)

1. Settings complete.
2. Check connection.
3. Dashboard + Health.
4. Building Docker services.
5. Test scripts, then scheduler.
6. Set backup targets.
7. Restore test in test path.
8. Deploy Watcher and Daily.

---

### From area: 20. Bug fixes by area

### 20.1 Connection

- SSH badge red: Check IP/Port/User/Auth.
- Key active, but password in the field: standardize auth path.

### 20.2 Docker

- List empty despite expected container: `List` first.
- Start fails: Check Inspect + Logs + Runtime in Health.

### 20.3 Backup/Restore

- Target profile missing: Check settings second profile.
- Restore without effect: Check archive path/mode/destination path.

### 20.4 Watcher/Daily

- Deploy ok, but no messages: check channel credentials and triggers.
- Too many messages: Adjust thresholds/checkboxes.

### 20.5 ACL/Explorer

- Unexpected rights effects: first read Stat/UGACL, then specifically change it.
- Deletion error: Check focus tree and path.

---

### From the area: 55. Checklists (operational)

### 55.1 Before critical change

1. Health Refresh
2. Snapshot/Backup
3. Individual change
4. Check logs/status
5. if necessary next change

### 55.2 Before Docker update

1. Current list
2. Check selection
3. Logs baseline
4. Update
5. Functional test

### 55.3 Before Restore

1. Check archive
2. Check target path
3. Save previous state
4. Restore
5. Check integrity

---

### From the range: 56. Large error patterns and clean response

### 56.1 “Everything seems broken”

Don't click everywhere. Sequence:

1. SSH
2. Health Refresh
3. Core Services
4. Storage
5. Docker Runtime

### 56.2 “Just one service broken”

1. Open the affected tab
2. Update list/status
3. Logs/Inspect
4. targeted correction

### 56.3 “Notifications are not coming”

1. Settings Credentials
2. Channel selection
3. Test buttons
4. NAS network

---

### From the area: 58. Practical instructions: First commissioning without gaps

These instructions will take you from the first start to the stable basic configuration without skipping any areas.

1. Start the app and select the theme/language so that you can immediately see the interface in your work context.
2. Open Settings and enter the connection data to the UGREEN NAS.
3. Test the SSH connection so that it is clear that the base is up and running.
4. Set a screenshot directory so that you can create documentation immediately if necessary.
5. Enter Telegram and/or SMTP and check with test.
6. Enter a second NAS profile if you want to use NAS-to-NAS transfers or second destinations for backups.
7. Save and then refresh the relevant tabs immediately afterwards.
8. Open the Health tab and run “Refresh” completely.
9. Check dashboard: load, volumes, docker, fan status.
10. Open the Scripts tab and make a backup of an existing script base.

If these ten points have been completed properly, the app is usually ready for everyday use and maintenance.

---

### From the area: 68. Safety rules for productive operation

1. Always take a health snapshot before major changes.
2. Always backup/snapshot before delete/restore actions.
3. Never touch multiple critical areas at the same time (e.g. Docker + ACL + Storage in one step).
4. Make changes sequentially and verifiably.
5. If you are unsure, test in a smaller scope first.

These rules reduce downtime and make sources of errors traceable.

---

### From the range: 69. Complete troubleshooting matrix

### 69.1 SSH does not connect

Symptom:

- No data in Dashboard/Health.

Test:

- Host/port correct?
- Network accessible?
- User/pass correct?
- SSH active on NAS?

### 69.2 Docker shows nothing

Symptom:

- Empty list or error text.

Test:

- Docker service running?
- User has necessary rights?
- Host communication stable?

### 69.3 Backup to second NAS missing

Symptom:

- No profile in selection.

Test:

- Settings saved for second NAS?
- Fields complete?
- Backup sources updated?

### 69.4 Telegram does not report

Symptom:

- No message during test.

Test:

- Token/Chat ID
- Network outbound
- Channel selection in Watcher/Daily

### 69.5 Fan profile reacts unexpectedly

Symptom:

- RPM does not jump as expected.

Test:

- selected mode correct?
- Pressed apply?
- UGOS return executed if conflict?

---

### From the range: 70. Maintenance plan for stable long-term use

Daily:

- Dashboard quick check
- Read alerts

Weekly:

- Health full refresh
- Check Docker/Storage abnormalities

Monthly:

- Backup-restore test in a small scope
- Review cron jobs and script versions
- Test notification channels

Quarterly:

- Clean up rights/ACL concept
- Update snapshot/backup strategy
- Compare documentation with current status

---

### From the area: 71. Glossary in operational language

- **UGOS**: UGREEN NAS operating system.
- **Watcher**: Running test process with alarm output.
- **Daily Report**: Daily summary.
- **Cron**: Scheduled job execution.
- **SMART**: Drive diagnostics.
- **mdcheck**: RAID checking mechanism.
- **NUT**: UPS management service.
- **SMB/NFS**: File sharing protocols.
- **Inspect**: Detailed container configuration.
- **Snapshot**: Snapshot of the file system state.

---

### From the area: 73. Full workflow A: Completely set up the new NAS

This workflow describes a complete initial commissioning including monitoring and backup.

Phase 1 - Connection:

1. Fill out the settings (SSH, User, Auth, Sudo).
2. Test connection.
3. Save.

Phase 2 - Visibility:

1. Load dashboard.
2. Health Refresh.
3. Check model display.

Phase 3 - Notification:

1. Set up Telegram (token/chat ID).
2. Set up SMTP (optional additionally).
3. Send test from Health.

Phase 4 - Operational Functions:

1. Save scripts.
2. Create scheduler test job.
3. Check Docker list.
4. Capture storage/ACL snapshot.

Phase 5 - Data Backup:

1. Set backup destination.
2. Start initial backup.
3. Check restore in small scope.

Phase 6 - continuous operation:

1. Deploy Watcher.
2. Enable Daily Report.
3. Apply maintenance plan according to Chapter 70.

---

### From the area: 74. Full workflow B: Resolve disruptions in production in a structured manner

Example: Services react with a delay, load increases, users report failures.

Step 1 - Situation picture:

- Read dashboard (CPU, RAM, network, volumes).
- Health Refresh.

Step 2 - Limitation:

- Check Docker Runtime status.
- Check core services.
- Check RAID/SMART.

Step 3 - Verification:

- For Docker problems: Logs + Inspect.
- For storage problems: Top20 + Volumes + Shares.
- For script problems: last cron jobs, test run manually.

Step 4 - Correction:

- Just one change at a time.
- Check the direct effect after each change.

Step 5 - Hedging:

- Snapshot/backup after stabilization.
- Document the cause briefly (internally or in the changelog).

This process prevents activism and reduces secondary errors.

---

### From the range: 75. Full workflow C: Planned maintenance without surprise failures

Preparation:

1. Define maintenance windows.
2. Capture affected services/containers.
3. Create backup/snapshot.

Implementation:

1. Selectively update Docker.
2. Check scripts/cron jobs.
3. Rights adjustments only targeted.
4. Update health after every big step.

Acceptance:

1. Core function test (user view).
2. Telegram/email test message.
3. Check performance baseline.

Rework:

1. note open points.
2. naechstes Wartungsfenster vorbereiten.

---

---

## 22. Graduation

### From the area: 21. End

This manual is intended as a complete operating basis for the current app.
If you use the sequences described and work with the respective safety rules for each area, you can use the app productively in a stable and controlled manner.

---

### From the range: 38. End note

This reference is intentionally complete and formulated specifically for each area.
If you use it as a workflow, the app can be operated in a stable and reproducible manner.

---

### From the area: 57. Graduation

This manual maps the current UI and functional logic and describes the app as a complete operational workflow.
Use it as a reference when working, not just in case of errors. This means that operation and changes remain comprehensible and stable.

---

### From the area: 72. Conclusion

The app is designed as an operations center: configure, check, change, verify.
This manual is therefore not short, but written as a complete working reference.
If you consistently apply the processes described, you will get reproducible results, fewer failures and significantly faster troubleshooting.

---

---
