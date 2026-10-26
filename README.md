# Debloat Samsung (and fine-tuning Genshin performance)

## 1. Purpose

This investigation has two objectives:

1. Remove unnecessary apps (debloat) from the phone.
2. Find the cause of the low frame rate and the stutter in Genshin Impact.

The game settings are Low-Medium quality and 60 FPS.

**WARNING:** DO NOT CHANGE THE GAME FILES OR THE GAME CLIENT. THE ANTI-CHEAT SYSTEM CAN FIND
THE CHANGES. THE GAME COMPANY CAN THEN BAN YOUR ACCOUNT. ALL CHANGES IN THIS DOCUMENT ARE IN
ANDROID AND SAMSUNG SETTINGS ONLY.

## 2. Summary of results

- The GPU is the limit. At its maximum clock (949 MHz) and 99% load, the GPU gives approximately
43 FPS in heavy scenes. The phone cannot keep 60 FPS in these scenes.
- Heat makes the problem worse. After 3 to 5 minutes, the phone reduces the CPU and GPU clocks
to control the temperature (thermal throttling). Then more frames are late.
- The stutter is from late frames. A frame must be ready in 16.7 ms for 60 FPS. A late frame
stays on the screen for 33 ms or 50 ms. You see this as stutter.
- RAM is not the limit. The free RAM stayed above 1.2 GB in all runs.
- The debloat and a cool start increased the average FPS by approximately 7%. The improvement
is largest in the first 4 minutes. After 5 minutes, heat removes most of the improvement.
- Android cannot reduce the render resolution of Genshin. The game ignores the Android
downscale function.
- You cannot increase the GPU limit without root. Although, root has high risk and a small benefit, so we do not recommend root your device unless you aware with the consequences.

## 3. Equipment and software


| Item        | Value                                                                       |
| ----------- | --------------------------------------------------------------------------- |
| Computer    | MacBook Pro with `adb` 34.0.5 (`/usr/local/bin/adb`) and Python 3           |
| Phone model | Galaxy A54 5G, SM-A546E (`a54xnsxx`)                                        |
| Chip (SoC)  | Exynos 1380 (`s5e8835`): 4x Cortex-A78 at 2.4 GHz, 4x Cortex-A55 at 2.0 GHz |
| GPU         | Mali-G68 MP5, maximum clock 949 MHz                                         |
| Software    | One UI 7, Android 15, build A546EXXSFDYI1, security patch 2025-09-01        |
| Bootloader  | Locked (`ro.boot.flash.locked=1`)                                           |
| Knox        | Not tripped (`ro.boot.warranty_bit=0`)                                      |
| Game        | Genshin Impact 7.1.0, target SDK 36                                         |


**NOTE**: Make sure your device already enabled with the developer options and the status is being `authorized`

## 4. Initial condition of the phone

These values are from the start of the investigation. The phone was idle and on charge.


| Item                | Value                                                                   |
| ------------------- | ----------------------------------------------------------------------- |
| RAM                 | 7.3 GB total. 3.3 GB available. RAM Plus is 4 GB. 46% of swap is in use |
| Storage             | 151 GB of 225 GB in use. 74 GB free. The game data uses 52 GB           |
| Temperature         | SoC (AP) 38 °C. Battery 35.8 °C. Thermal status 1 (light)               |
| Animation scales    | 1.0x                                                                    |
| Packages for user 0 | 435 system apps. 34 user apps. 16 disabled apps                         |


**NOTE**: The command `pm list packages` without `--user 0` gives the error
`SecurityException ... user 150`. User 150 is Secure Folder. ADB cannot get access to it.
This error has no effect. Use `--user 0` in all package commands.

### 4.1 Processes with high RAM use (phone idle)


| Process                                                     | RAM (PSS) | Remark                                            |
| ----------------------------------------------------------- | --------- | ------------------------------------------------- |
| system\_server                                              | 518 MB    | Android system. This is normal                    |
| Lark (`com.larksuite.suite` and `:wschannel`)               | 610 MB    | Highest CPU use of all apps                       |
| Device security (`sm.devicesecurity`)                       | 396 MB    | Very high. Possibly a scan was in progress        |
| System UI                                                   | 251 MB    | Normal                                            |
| Secure Folder (keyboard and Google Play services, user 150) | 195 MB    | A second copy of these apps runs in Secure Folder |
| Samsung Health (and `:remote`)                              | 168 MB    | Runs in the background                            |
| Telkomsel app                                               | 126 MB    | Runs in the background                            |


### 4.2 Game settings in Android


| Item                              | Value                         |
| --------------------------------- | ----------------------------- |
| Android game mode                 | Performance                   |
| Game mode changes (interventions) | None. Scale 1.0. No FPS limit |
| `game_auto_temperature_control`   | 0 (off)                       |
| App standby bucket                | 10 (active)                   |
| Background operation              | Allowed                       |
| Game Optimizing Service (GOS)     | 4.0.00.44                     |
| Game Booster                      | 7.0.01.73                     |


> No Android setting reduced the game performance. Thus, we recorded data while the user  
> played the game.

## 5. Tools

All tools are in the `scripts/` folder.


| Tool           | Function                                                                                             | Changes the phone                    |
| -------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `snapshot.sh`  | Records the condition of the phone to `logs/snapshots/<time>/`                                       | No                                   |
| `gcapture.py`  | Records the game frame rate, CPU, GPU, temperature and RAM 1 time each second to a CSV file          | No                                   |
| `debloat.sh`   | Removes the packages in a list for user 0. Records each removal in `logs/removed_packages.log`       | Yes                                  |
| `restore.sh`   | Installs again the packages that `debloat.sh` removed                                                | Yes                                  |
| `tune.sh`      | Applies or undoes the ADB settings of section 11. Records each change in `logs/settings_changes.log` | Yes (`apply`, `undo`). No (`status`) |
| `summarize.py` | Calculates the results of section 7.2 and 7.3 from one or more CSV files                             | No                                   |


### 5.1 Record the phone condition

1. Do this command: `scripts/snapshot.sh`.
2. Find the result in `logs/snapshots/<date-time>/`.

### 5.2 Record a game session

1. Open the game. Go into the game world.
2. Do this command: `python3 scripts/gcapture.py logs/captures/<name>.csv <seconds>`.
If the game is set to 45 FPS, add `--jank-ms 40`. See the note in 11.4.
3. Play the game until the time is complete.

The CSV file has these columns:


| Column                             | Source                                                  | Meaning                                                               |
| ---------------------------------- | ------------------------------------------------------- | --------------------------------------------------------------------- |
| `fps`, `frames`                    | `dumpsys SurfaceFlinger --latency <game layer>`         | Frames shown each second                                              |
| `worst_ms`                         | Same                                                    | The longest time between 2 frames in that second                      |
| `jank`                             | Same                                                    | The number of late frames (more than 25 ms, or the `--jank-ms` value) |
| `cpu0`, `cpu4`, `cpu7`             | `/sys/devices/system/cpu/cpuN/cpufreq/scaling_cur_freq` | Current CPU clock (MHz)                                               |
| `cpu0_max`, `cpu4_max`, `cpu7_max` | `.../scaling_max_freq`                                  | Current CPU clock limit. A decrease shows thermal throttling          |
| `gpu_mhz`, `gpu_busy`, `gpu_temp`  | `/sys/kernel/gpu/`                                      | GPU clock, GPU load (%), GPU temperature                              |
| `AP`, `SKIN`, `BAT`                | `dumpsys thermalservice`                                | SoC, surface and battery temperature (°C)                             |
| `thermal_status`                   | Same                                                    | Android thermal status. 0 is normal. 4 is critical                    |
| `mem_avail_mb`                     | `/proc/meminfo`                                         | Available RAM (MB)                                                    |
| `foreground`                       | —                                                       | 1 when the tool finds the game layer                                  |


### 5.3 How to read the data


| Condition          | Indication                                                                                                      |
| ------------------ | --------------------------------------------------------------------------------------------------------------- |
| Thermal throttling | `cpu*_max` and `gpu_mhz` decrease. At the same time, `AP` and `SKIN` increase                                   |
| GPU limit          | `gpu_busy` is 90% to 100% at 949 MHz when the FPS decreases                                                     |
| CPU limit          | `cpu4` and `cpu7` are at maximum, and the GPU load is low. Causes: loading, world streaming, shader compilation |
| RAM limit          | `mem_avail_mb` is very low. Android must then move or stop apps                                                 |


### 5.4 Compare the runs

1. Do this command: `python3 scripts/summarize.py logs/captures/genshin_run3.csv logs/captures/<name>.csv`.
2. To also get the minute-by-minute table, add `--minutes`.

The tool counts only gameplay seconds: the game layer is found and the FPS is 20 or more. This
removes the loading screens. Menus are not removed. Thus, the results can be different from
section 7.2 by approximately 1%.

## 6. Debloat

### 6.1 Method

The command `pm uninstall -k --user 0 <package>` removes an app for the main user only.
The app file stays in the system partition. Thus, you can install the app again at any time.
A factory reset also installs all apps again.

### 6.2 Package lists


| File                             | Contents                                                                                                                                                                                     |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `debloat/tier1_safe.txt`         | 13 packages. Facebook services, Samsung telemetry (`dqagent`), AR Emoji and stickers, Kids and parental controls, Smart Switch assistant, Easy mode widget, Dressroom                        |
| `debloat/tier2_optional.txt`     | 14 packages. Bixby, Link to Windows, OneDrive, Samsung Pass, Customization Service, Gemini, Google Meet, Hiya caller ID, Galaxy Watch stub. Remove these only if you do not use the function |
| `debloat/keep_do_not_remove.txt` | Packages that you must keep. The file gives the reason for each package                                                                                                                      |


**CAUTION:** DO NOT REMOVE THE GAME OPTIMIZING SERVICE (`com.samsung.android.game.gos`). ON
ONE UI 7, THE THERMAL THROTTLING CAN BECOME WORSE WITHOUT IT. ALSO KEEP KNOX, QUICK SHARE,
SMARTTHINGS PLATFORM, SAMSUNG ACCOUNT SERVICES AND DEVICE HEALTH SERVICES.

### 6.3 Remove packages

1. Do a test first. The test does not change the phone:
`scripts/debloat.sh debloat/tier1_safe.txt --dry-run`
2. Make sure that the list is correct.
3. Remove the packages: `scripts/debloat.sh debloat/tier1_safe.txt`
4. Make sure that each line shows `Success`.

### 6.4 Install the packages again

- To install all removed packages again, do this command: `scripts/restore.sh`
- To install one package again, do this command: `scripts/restore.sh <package>`

## 7. Test runs

### 7.1 Conditions


| Run  | File                                            | Cooler | Start temperature | Background apps | Changes applied                 | Gameplay time |
| ---- | ----------------------------------------------- | ------ | ----------------- | --------------- | ------------------------------- | ------------- |
| Test | `logs/captures/test_idle_5s.csv`                | —      | —                 | —               | None. Tool test only            | 0             |
| 1    | `logs/captures/genshin_run1_telemetry_only.csv` | On     | Cool              | Running         | None                            | 6 min         |
| 2    | `logs/captures/genshin_run2.csv`                | Off    | Hot (from Run 1)  | Running         | None                            | 7 min         |
| 3    | `logs/captures/genshin_run3.csv`                | Off    | Cool (AP 37.4 °C) | Stopped         | Tier 1 debloat, animations 0.5x | 8 min         |


All runs were set in game quality Low, 60 FPS, phone connected to the laptop USB port.

**NOTE**: Run 1 has no frame rate data. The first version of `gcapture.py` had a defect. See
section 9.

**NOTE**: In Run 2, the user removed the cooler at approximately the start. The exact time is
not known. Run 2 started with a hot phone. Thus, Run 2 is not a fully correct comparison.

### 7.2 Results

The values for Run 2 and Run 3 include gameplay seconds only. Menus and loading screens are
not included.


| Item                               | Run 1 (cooler) | Run 2 (no cooler, hot start) | Run 3 (no cooler, cool start, debloat) |
| ---------------------------------- | -------------- | ---------------------------- | -------------------------------------- |
| Average FPS                        | No data        | 43.9                         | **46.8**                               |
| Seconds below 45 FPS               | No data        | 65%                          | **21%**                                |
| Seconds below 55 FPS               | No data        | 85%                          | 93%                                    |
| Late frames (more than 25 ms)      | No data        | 32.1%                        | **26.4%**                              |
| Longest frame                      | No data        | 767 ms                       | 717 ms                                 |
| Time with GPU at 949 MHz           | 25%            | 35%                          | **47%**                                |
| Maximum GPU temperature            | **75 °C**      | 81 °C                        | 82 °C                                  |
| Maximum SoC (AP) temperature       | **57.1 °C**    | 59.7 °C                      | 59.5 °C                                |
| Maximum surface (SKIN) temperature | **44.6 °C**    | 46.7 °C                      | 46.2 °C                                |
| Maximum battery temperature        | **37 °C**      | 39.7 °C                      | 39.0 °C                                |
| Highest thermal status             | **3 (severe)** | 4 (critical)                 | 4 (critical)                           |
| Time at thermal status 4           | **0 s**        | 172 s                        | 186 s                                  |
| Lowest big-core clock limit        | 1440 MHz       | 960 MHz                      | 533 MHz                                |
| Minimum free RAM                   | 1342 MB        | 1291 MB                      | **1698 MB**                            |


### 7.3 Run 3 minute by minute


| Minute | Average FPS | Late frames | GPU temperature | SoC (AP) | Thermal status |
| ------ | ----------- | ----------- | --------------- | -------- | -------------- |
| 0      | 50.5        | 18%         | 68 °C           | 53.5 °C  | 2              |
| 1      | 47.2        | 22%         | 77 °C           | 56.7 °C  | 3              |
| 2      | 47.1        | 27%         | 78 °C           | 57.5 °C  | 3              |
| 3      | 48.3        | 23%         | 77 °C           | 56.7 °C  | 3              |
| 4      | 46.9        | 25%         | 81 °C           | 59.2 °C  | 3              |
| 5      | 45.3        | 30%         | 72 °C           | 56.8 °C  | 4              |
| 6      | 45.8        | 31%         | 70 °C           | 56.5 °C  | 4              |
| 7      | 45.7        | 31%         | 72 °C           | 57.1 °C  | 4              |
| 8      | 42.7        | 36%         | 70 °C           | 58.3 °C  | 4              |


The FPS decreases when the temperature increases. At minute 5, the thermal status becomes 4.
After that time, the late frames increase.

## 8. Somewhat a finding and analysis

### 8.1 The GPU is the limit

In Run 2, at 60 seconds, the GPU was at 949 MHz and 99% load. The game gave only 43 FPS.
In Run 3, minute 0, the phone was cool, and the average was 50.5 FPS. Thus, the phone cannot
keep 60 FPS at the current resolution, even when it is cool.

### 8.2 Heat makes the problem worse

The thermal status becomes 3 after approximately 3 minutes. Without the cooler, it becomes 4
after approximately 5 minutes. Then the phone decreases the CPU and GPU clocks. The GPU must
then do the same work at a lower clock. More frames are late.

### 8.3 The cooler decreases the temperature but does not stop throttling

With the cooler (Run 1), the thermal status did not go above 3. The GPU was 6 °C to 7 °C
cooler. Without the cooler (Runs 2 and 3), the thermal status became 4.

### 8.4 Laptop USB power is not sufficient

During Run 2, the battery current was negative at some times. The game used more power than
the laptop USB port supplied. The charge also heats the battery. The battery temperature
increased from 37.4 °C to 39.7 °C.

### 8.5 Effect of the debloat

The debloat and the stop of the background apps gave approximately 400 MB more free RAM.
The longest frame time decreased. But RAM was not the limit in any run. The debloat does not
change the GPU limit.

### 8.6 Android downscale does not operate on this game

We set the Android game mode downscale to 0.7x:
`adb shell cmd game set --downscale 0.7 com.miHoYo.GenshinImpact`

Android accepted the command, but when tested with the game open, the result was:

- The game window was full size (2340 x 1080). It had no compatibility scale.
- The game rendered at 1920 x 886 (approximately 82% of the screen). This is the resolution
from the game settings.
- With a 0.7x downscale, the resolution must be approximately 1638 x 756.

Thus, the game ignores the Android downscale. We removed the downscale. We set the game mode
to Performance again.

### 8.7 Can we increase the limit?

No, not with the hardware limit. There are several considerations and reasons:

- The GPU is at its maximum clock. Exynos 1380 does not allow a higher GPU clock.
- Samsung firmware controls the thermal limits. ADB cannot change them without root.
- Root trips Knox permanently. Samsung Pay, Secure Folder and some bank apps then stop. The
warranty becomes void.
- There is no reliable custom kernel for the A54 that increases the GPU clock.
- Higher thermal limits make the battery and the chip hotter. This can cause damage.

### 8.8 Why the debloat and the animation scales have a small effect

The two changes operate correctly. But they do not change the limits of the game.


| Change                | What it changes                                        | Why the effect on the game is small                                                                                |
| --------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| Tier 1 debloat        | Free RAM and background CPU use                        | RAM was not the limit (8.5). The GPU was at 949 MHz and 99% load (8.1). More free RAM does not make the GPU faster |
| Animation scales 0.5x | The duration of the Android window and menu animations | No effect in the game. The game draws its own frames. Only the Android menus feel faster                           |


The improvement in Run 3 (approximately 7%) came mostly from the cool start and the stop of
Lark. After thermal status 4 (minute 5), the improvement is gone (7.3).

The apps with the highest resource use (Lark, Samsung Health, Telkomsel) are not in the debloat
lists. To control them, see 11.1.

To get a better result, you must decrease the GPU work or the heat. See section 11.

## 9. Defects found and repaired


| Defect                                      | Cause                                                                                                                               | Repair                                                            |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `gcapture.py` recorded 0 FPS in Run 1       | The game makes a new render layer after the loading screen. The new layer has a new `#id`. The tool continued to read the old layer | The tool now finds the layer again after 3 seconds with no frames |
| `debloat.sh` removed only the first package | `adb shell` in the `while read` loop used the input of the loop                                                                     | The scripts now use `adb shell -n`                                |


## 10. Changes applied to the phone

All changes are recorded in `logs/settings_changes.log` and `logs/removed_packages.log`.


| Time                    | Change                                                            | Status                        |
| ----------------------- | ----------------------------------------------------------------- | ----------------------------- |
| 2026-10-25 19:15        | Animation scales: window, transition and animator from 1.0 to 0.5 | Active                        |
| 2026-10-25 19:15        | Tier 1 debloat: 13 packages removed for user 0                    | Active                        |
| 2026-10-25 19:15        | Game mode downscale 0.7x for Genshin                              | Removed (no effect, see 8.6)  |
| 2026-10-25, after Run 3 | Game mode for Genshin set to Performance again                    | Active (same as at the start) |


### 10.1 Undo all changes

1. Install the removed packages again: `scripts/restore.sh`
2. Set the animation scales to 1.0:
   ```bash
     for k in window_animation_scale transition_animation_scale animator_duration_scale; do
       adb shell settings put global $k 1.0
     done
   ```
3. Make sure that the game mode is Performance:
`adb shell cmd game list-modes com.miHoYo.GenshinImpact`

## 11. Recommendations

The user must do these steps, if you want to try it by yourself. The order is from the largest expected effect to the smallest.


| No. | Recommendation                                 | Procedure                                                                                                                                                    | Expected effect                                                                                                    |
| --- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| 1   | Set the game to 45 FPS                         | In the game, go to Settings &gt; Graphics &gt; FPS. Select 45                                                                                                | Stable 45 FPS. Less heat. Fewer late frames. The phone gave approximately 50 FPS when cool, so 45 FPS has a margin |
| 2   | Decrease the render resolution                 | In the game, go to Settings &gt; Graphics &gt; Render Resolution. Select one step lower                                                                      | Less GPU work for each frame. Less heat                                                                            |
| 3   | Set the display to 60 Hz                       | Go to Settings &gt; Display &gt; Motion smoothness. Select Standard                                                                                          | Less display power and heat. The game cannot use 120 Hz when it gives less than 60 FPS                             |
| 4   | Use the cooler                                 | Remove the phone case. Attach the cooler before you start the game                                                                                           | Thermal status stays at 3 or lower                                                                                 |
| 5   | Do not charge the battery during the game      | Use a 25 W USB PD wall charger. In Game Booster, set "Pause USB Power Delivery" to on                                                                        | No heat from the charge. The charger supplies the phone directly                                                   |
| 6   | Use a lower performance profile                | Go to Settings &gt; Battery &gt; Performance profile. Select Light. If this menu is not available, go to Game Booster &gt; Game performance. Select Standard | Lower but more stable clocks. Less heat. Possibly fewer stutters after minute 5                                    |
| 7   | Set the Samsung auto temperature control to on | `scripts/tune.sh apply` (see 11.1)                                                                                                                           | The game optimizing service can decrease the load before the thermal status becomes 4                              |
| 8   | Limit the background apps                      | `scripts/tune.sh apply` (see 11.1)                                                                                                                           | Lark and other heavy apps cannot run in the background during the game. The apps stay installed                    |
| 9   | Prepare the phone before the game              | Close Lark. Lock Secure Folder. Close all recent apps                                                                                                        | Approximately 800 MB more free RAM. Less CPU use in the background                                                 |
| 10  | Optional: Tier 2 debloat                       | `scripts/debloat.sh debloat/tier2_optional.txt`                                                                                                              | Small effect on general smoothness. No large effect on the game                                                    |


**CAUTION:** IF YOU USE A PELTIER (ELECTRIC) COOLER, WATER CAN COLLECT ON THE PHONE. THE WATER
CAN CAUSE DAMAGE. DO NOT USE THE COOLER IN A HUMID ROOM FOR A LONG TIME.

**NOTE**: Record each setting change in `logs/settings_changes.log`.

### 11.1 Apply the ADB settings with `tune.sh`

`tune.sh` applies recommendations 7 and 8. It records the values before and after each change
in `logs/settings_changes.log`. The other recommendations are in the game or in the phone
settings. `tune.sh` shows them as a list.

1. Look at the current values. This step does not change the phone: `scripts/tune.sh status`
2. Make sure that `debloat/restrict_background.txt` contains the correct apps.
3. Do a test first: `scripts/tune.sh apply --dry-run`
4. Apply the settings: `scripts/tune.sh apply`
5. Do the manual steps that `tune.sh` shows.

To undo the settings, do this command: `scripts/tune.sh undo`. The auto temperature control
becomes 0 (the value at the start). The apps become active and can run in the background.

### 11.2 Limit background apps without removal (manual procedure)

This procedure is an alternative to the debloat. It stops an app from running in the
background. The app stays installed. You can undo the change at any time. `tune.sh` does
the same steps for each app in `debloat/restrict_background.txt`.

1. Set the app to the restricted standby bucket:
`adb shell am set-standby-bucket com.larksuite.suite restricted`
2. Stop the background operation of the app:
`adb shell cmd appops set com.larksuite.suite RUN_ANY_IN_BACKGROUND ignore`
3. Do steps 1 and 2 again for other heavy apps, for example Samsung Health
(`com.sec.android.app.shealth`) and the Telkomsel app.
4. Make sure that the bucket is correct:
`adb shell am get-standby-bucket com.larksuite.suite`. The result must be `45` (restricted).

**CAUTION:** A RESTRICTED APP CAN DELAY ITS NOTIFICATIONS. DO NOT RESTRICT AN APP IF YOU MUST
GET ITS MESSAGES IMMEDIATELY.

To undo the change:

```bash
adb shell am set-standby-bucket com.larksuite.suite active
adb shell cmd appops set com.larksuite.suite RUN_ANY_IN_BACKGROUND allow
```

### 11.3 Expected results


| Configuration                       | Expected result                                           |
| ----------------------------------- | --------------------------------------------------------- |
| 45 FPS and cooler                   | Almost stable 45 FPS for the full session. Few stutters   |
| 60 FPS, lower resolution and cooler | Approximately 50 to 58 FPS. Some decreases in heavy areas |
| Stable 60 FPS in heavy areas        | Not possible on this chip                                 |


### 11.4 Next test (optional)

To verify recommendations 1 and 3 to 8, do Run 4:

1. Let the phone become cool. The SoC (AP) temperature must be less than 40 °C.
2. Do this command: `scripts/tune.sh apply`. Do the manual steps that it shows.
3. Attach the cooler.
4. Record 10 minutes of gameplay. Use the same area of the game as in Run 3:
`python3 scripts/gcapture.py logs/captures/genshin_run4.csv 600 --jank-ms 40`
5. Compare the results with Run 3:
`python3 scripts/summarize.py logs/captures/genshin_run3.csv logs/captures/genshin_run4.csv --minutes`

**NOTE**: At 45 FPS on a 60 Hz display, the frame times are 16.7 ms and 33 ms in turn. This is
normal. With the default limit of 25 ms, `gcapture.py` counts each 33 ms frame as a late
frame. Thus, use `--jank-ms 40` at 45 FPS. Run 3 used 25 ms. Thus, do not compare the late
frames of Run 3 and Run 4 directly. Compare the FPS, the seconds below 40 FPS and the longest
frame.