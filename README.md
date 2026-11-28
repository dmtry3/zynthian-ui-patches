# Zynthian UI Patches (`vangelis`)

Набор патчей для ветки **`vangelis`** (`zynthian/zynthian-ui`).

---

## 1. MIDI CC Auto-Focus (`patches/midi-cc-autofocus.patch`)

При повороте замапленной ручки на внешнем MIDI-контроллере экран **Control** автоматически переключается на нужную цепочку (chain), процессор (устройство/плагин) и страницу энкодеров с этим параметром.

### Возможности

- **Авто-переключение на канал (цепочку), устройство и энкодеры с любого канала:**
  - **Global / Absolute MIDI Learn** — переключает на нужную цепочку (Chain), процессор и страницу энкодеров (включая специальные процессоры: ALSA Mixer, Audio Player, Tempo), с приоритетом выше авто-замапленных CC активной цепочки.
  - **Chain MIDI Learn** (`?`, режим по умолчанию) — работает с любого открытого канала в режиме **Control**: если текущий канал не имеет привязки на этот `(CH, CC)`, автоматически переключает на нужную цепочку, процессор и страницу энкодеров (и доставляет первый тик CC). Если один и тот же `(CH, CC)` замаплен на обеих цепочках, приоритет остаётся у активной цепочки.
  - **Авто-замапленные CC движков (`0xFF`)** — в режиме `MULTI` переключают на цепочку, назначенную на входящий MIDI-канал; в режиме `ACTI` сохраняют фокус на активной цепочке (а если у неё нет такого CC — переключают на цепочку этого MIDI-канала).
- **Только когда уже открыт экран Control:** не прерывает работу в Mixer, Admin, секвенсоре (Launcher / Pattern Editor), браузере пресетов, режиме `select` или во время `MIDI Learn`.
- **Защита от паразитных срабатываний:**
  - Игнорирует внутренние источники CC (ZynStep-автоматизация, MIDI-плеер, engine feedback от setBfree и т.д.) — реагирует только на внешние MIDI-контроллеры.
  - Если замапленный параметр уже находится среди 4 текущих энкодеров, перерисовка не выполняется.
  - Учитывает `midi_bank_change` (CC 0 / CC 32).
- **Быстро выключаемая опция с сохранением в конфиг:**
  - Доступна сразу в трёх меню:
    1. **Admin** (секция `MIDI`) -> `☑ MIDI Auto-Focus`
    2. **Control Options** (долгий/Bold-клик на любом энкодере на экране Control) -> `☑ MIDI Auto-Focus`
    3. **Chain Options** (боковая панель цепи -> Chain Options) -> `☑ MIDI Auto-Focus`
  - Сохраняется в `/zynthian/config/zynthian_envars.sh` в переменную `ZYNTHIAN_UI_MIDI_CC_AUTOFOCUS` (`1` по умолчанию, `0` — выключено).

### Затронутые файлы в `zynthian-ui`

- `zyngui/zynthian_gui_config.py` — параметр `midi_cc_autofocus` (`ZYNTHIAN_UI_MIDI_CC_AUTOFOCUS`, default `1`).
- `zyngine/zynthian_chain_manager.py` — метод `get_midi_cc_zctrls(zmip, midi_chan, cc_num)`.
- `zyngui/zynthian_gui_admin.py` — глобальный переключатель `MIDI Auto-Focus` в меню **Admin** (секция `MIDI`).
- `zyngui/zynthian_gui_control.py` — обработчик авто-фокуса в `cb_midi_cc`, переключение цепочки/процессора/страницы энкодеров и переключатель в Control Options.
- `zyngui/zynthian_gui_chain_options.py` — переключатель `MIDI Auto-Focus` в Chain Options.

---

## 2. PAD / Launcher: перемещение и обмен клипов удержанием F4 (`patches/launcher-hold-move-clip.patch`)

Быстрое перемещение и обмен местами (Swap) клипов в режиме **PAD / Launcher** без копирования через буфер обмена:

### Как пользоваться

1. Включите режим **PAD (Launcher)** и активируйте **ALT** (на V4 / MCP23017 `ALT` в Launcher включается автоматически).
2. Наведите курсор на нужный клип (MIDI-паттерн, аудио-клип Clippy, пустую ячейку для затирания или фразу в колонке Main).
3. **Зажмите `F4`** (`S4` на V4 / MCP23017; кнопка работает, когда отключён TTS):
   - На время удержания отключается авто-`Long Press`, исходная ячейка помечается значком `⇄` и оранжевой рамкой.
   - В заголовке отображается подсказка (`Move A1 → B3` для пустой ячейки, `Swap A1 ↔ B3` для занятой, `Clear B3` при переносе пустой ячейки поверх клипа, `Can't move A1 here` / `Can't clear here` для несовместимого типа).
   - Подсветка целевой ячейки и светодиод `F4` показывают статус: **зелёный** — перенос/обмен, **красно-оранжевый** — затирание (Clear), **оранжевый** — исходная/пустая без действия, **красный** — несовместимый тип (например, MIDI-паттерн на аудио-дорожку Clippy или на колонку Main).
4. **Не отпуская `F4`**, переведите курсор стрелками (`↑ ↓ ← →`) или энкодерами на целевую ячейку.
5. **Отпустите `F4`**:
   - **Клип → пустая ячейка** — перемещение (исходная ячейка очищается).
   - **Клип → занятая ячейка** — обмен местами (Swap) без потери данных.
   - **Пустая ячейка → занятая ячейка** — **затирание (Clear)** целевого клипа (паттерн очищается / аудио-клип выгружается).
   - Если не сдвигать курсор, перенести пустую ячейку на пустую или нажать `BACK` во время удержания — операция отменяется.
   - Если зажать `F4` на колонке **Main (Phrase)**, стрелки `↑ / ↓` (или энкодеры 3/4) сразу двигают всю фразу целиком вверх/вниз.

### Особенности реализации

- **MIDI-паттерны:** атомарный обмен паттернов через `libseq.removePattern` / `libseq.addPattern` с переносом имени (`name`), режима повтора (`repeat`), безопасной остановкой воспроизведения (`All Notes Off`) и синхронизацией буфера обмена `F1/F2`; затирание через `libseq.clearPattern` со сбросом имени и режима.
- **Аудио-клипы (Clippy):** полный обмен всех параметров контроллеров (`file`, `crop_start`, `crop_end`, `zoom`, `gain`, `warp`, `beats`, `mode`, `beat_slice`), корректная выгрузка клипа при переносе в пустой слот или затирании (`clear_clip`) и сохранение `gain` после загрузки.
- **Вне `ALT`-режима** поведение кнопки `F4` не меняется.

### Затронутые файлы в `zynthian-ui`

- `zyngine/zynthian_engine_clippy.py` — методы `swap_clips(proc_a, phrase_a, proc_b, phrase_b)` и `clear_clip(proc, phrase)`.
- `zyngui/zynthian_gui_mixer.py` — обработчик удержания `F4`/`S4` в `ALT + Launcher`, подсветка исходной/целевой ячейки, индикация заголовка и WSLED, обмен MIDI-паттернов и аудио-клипов.

---

## Установка на Zynthian

### Быстрая установка в одну команду (прямо с Zynthian)

```bash
curl -fsSL https://raw.githubusercontent.com/dmtry3/zynthian-ui-patches/main/install.sh | bash
```

Скрипт склонирует репозиторий в `/root/zynthian-ui-patches` (или обновит, если уже склонирован), настроит авто-применение патчей через systemd drop-in (`/etc/systemd/system/zynthian.service.d/zynthian-ui-patches.conf`), применит патчи к `/zynthian/zynthian-ui`, проверит синтаксис Python и перезапустит сервис `zynthian`.

### Установка через `git clone`

```bash
git clone https://github.com/dmtry3/zynthian-ui-patches.git /root/zynthian-ui-patches
cd /root/zynthian-ui-patches
./install.sh
```

Применить или откатить только один конкретный патч:

```bash
./apply-patch.sh --patch launcher-hold-move-clip.patch
./apply-patch.sh --patch launcher-hold-move-clip.patch --revert
```

## Авто-сохранение после обновлений Zynthian

При обновлении `update_zynthian.sh` выполняет `git checkout .` в `/zynthian/zynthian-ui` и перезапускает `zynthian.service`.
Установщик автоматически создаёт systemd drop-in `/etc/systemd/system/zynthian.service.d/zynthian-ui-patches.conf`:

```ini
[Service]
ExecStartPre=-/root/zynthian-ui-patches/install.sh --no-restart --no-hook --zynthian-ui-dir /zynthian/zynthian-ui
```

- `update_zynthian_sys.sh` перезаписывает только `zynthian.service` и не трогает `zynthian.service.d/`.
- Перед каждым запуском `zynthian.service` патчи проверяются и при необходимости автоматически накатываются обратно.
- Префикс `-` гарантирует, что при конфликте в будущем релизе Zynthian сервис всё равно запустится со стоковым UI.
- Для установки без systemd drop-in используйте `./install.sh --no-hook`.

## Проверка статуса и откат патчей

Проверить статус патчей и systemd-хука:

```bash
/root/zynthian-ui-patches/install.sh --status
```

Полностью удалить хук и откатить все патчи:

```bash
/root/zynthian-ui-patches/install.sh --revert
```

## Проверка тестами

```bash
ZYNTHIAN_UI_DIR=/zynthian/zynthian-ui python3 -m unittest discover -s tests -v
```
