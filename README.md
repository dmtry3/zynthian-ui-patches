# Zynthian UI Patch: MIDI CC Auto-Focus (`vangelis`)

Патч для ветки **`vangelis`** (`zynthian/zynthian-ui`): при повороте замапленной ручки на внешнем MIDI-контроллере экран **Control** автоматически переключается на нужную цепочку (chain), процессор (устройство/плагин) и страницу энкодеров с этим параметром.

## Возможности

- **Авто-переключение на устройство и энкодеры:**
  - **Global / Absolute MIDI Learn** — переключает на нужную цепочку (Chain), процессор и страницу энкодеров (включая специальные процессоры: ALSA Mixer, Audio Player, Tempo).
  - **Chain MIDI Learn** (включая авто-замапленные CC движков) — переключает процессор (MIDI-FX / Synth / Audio-FX / Mixer) и страницу энкодеров внутри активной цепочки.
- **Только когда уже открыт экран Control:** не прерывает работу в Mixer, Admin, секвенсоре (ZynPad / Pattern Editor), браузере пресетов, режиме `select` или во время `MIDI Learn`.
- **Защита от паразитных срабатываний:**
  - Игнорирует внутренние источники CC (ZynStep-автоматизация, MIDI-плеер, engine feedback от setBfree и т.д.) — реагирует только на внешние MIDI-контроллеры.
  - Если замапленный параметр уже находится среди 4 текущих энкодеров, перерисовка не выполняется.
  - Учитывает `midi_bank_change` (CC 0 / CC 32).
- **Быстро выключаемая опция с сохранением в конфиг:**
  - Доступна сразу в двух меню:
    1. **Control Options** (долгий/Bold-клик на любом энкодере на экране Control) -> `☑ MIDI Auto-Focus`
    2. **Chain Options** (боковая панель цепи -> Chain Options) -> `☑ MIDI Auto-Focus`
  - Сохраняется в `/zynthian/config/zynthian_envars.sh` в переменную `ZYNTHIAN_UI_MIDI_CC_AUTOFOCUS` (`1` по умолчанию, `0` — выключено).

## Затронутые файлы в `zynthian-ui`

- `zyngui/zynthian_gui_config.py` — параметр `midi_cc_autofocus` (`ZYNTHIAN_UI_MIDI_CC_AUTOFOCUS`, default `1`).
- `zyngine/zynthian_chain_manager.py` — метод `get_midi_cc_zctrls(zmip, midi_chan, cc_num)`.
- `zyngui/zynthian_gui_control.py` — обработчик авто-фокуса в `cb_midi_cc`, переключение цепочки/процессора/страницы энкодеров и переключатель в Control Options.
- `zyngui/zynthian_gui_chain_options.py` — переключатель `MIDI Auto-Focus` в Chain Options.

## Установка на Zynthian

### Быстрая установка в одну команду (прямо с Zynthian)

```bash
curl -fsSL https://raw.githubusercontent.com/dmtry3/zynthian-ui-patches/main/install.sh | bash
```

Скрипт склонирует репозиторий в `/root/zynthian-ui-patches` (или обновит, если уже склонирован), применит патч к `/zynthian/zynthian-ui`, проверит синтаксис Python и перезапустит сервис `zynthian`.

### Установка через `git clone`

```bash
git clone https://github.com/dmtry3/zynthian-ui-patches.git /root/zynthian-ui-patches
cd /root/zynthian-ui-patches
./install.sh
```

## Проверка статуса и откат патча

Проверить, установлен ли патч:

```bash
/root/zynthian-ui-patches/install.sh --status
```

Откатить патч (например, перед обновлением Zynthian):

```bash
/root/zynthian-ui-patches/install.sh --revert
```

> Примечание: перед `update_zynthian.sh` рекомендуется откатить патч (`./install.sh --revert`), обновиться и снова применить его (`./install.sh`).

## Проверка тестами

```bash
ZYNTHIAN_UI_DIR=/zynthian/zynthian-ui python3 -m unittest discover -s tests -v
```
