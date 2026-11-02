# Environnement de la branche `Common_Spectrograph_driver`

Relevé sur le PC où la branche fonctionne (Windows 11, novembre 2026), configuration
Pixis + SpectraPro 2300i + cryostat Pasqal.

## 1. Environnement Python (conda)

Python 3.13, env conda `SilvaBot`. Versions exactes dans
[`environment_commonspectrometer.yml`](environment_commonspectrometer.yml) (paquets conda + pip).

```bash
conda env remove -n SilvaBot
conda env create -f dependencies/environment_commonspectrometer.yml
conda activate SilvaBot
```

Si une version épinglée n'est plus disponible, repartir de la version souple :

```bash
conda env create -f dependencies/environment_general.yml
conda install -n SilvaBot -c conda-forge pyyaml
conda run -n SilvaBot pip install pylablib==1.4.5 pyvisa==1.16.2 pyserial==3.5 scipy pandas numba pyft232 pyusb rpyc
```

À savoir :

- **Ne pas utiliser** `requirements.txt` à la racine ni `.conda/` dans le dépôt : ce n'est pas
  l'environnement qui tourne ici (`.conda/` est un Python 3.14 vide).
- Les `.bat` à la racine activent `.venv_new` / `.venv`, qui n'existent pas sur ce PC. Lancer à
  la main depuis la racine du dépôt :

  ```bash
  conda run -n SilvaBot python src/main.py
  ```

- Les drivers non utilisés par cette configuration importent des paquets absents de l'env
  (`requests`, `seabreeze`, `harvesters`, `zhinst`, `lakeshore`, `win32com`…). C'est normal, ils
  ne sont chargés que si `config.yaml` les active.

## 2. `src/config.yaml`

Fichier ignoré par git : il n'est **pas** sur la branche. Sans lui, `main.py` ne trouve pas sa
configuration (et `config_default.yaml` pointe vers un Thorlabs CCS200, pas vers le
spectrographe).

```bash
cp dependencies/config_commonspectrometer.yaml src/config.yaml
```

Puis adapter au poste :

| Clé | Valeur ici | À vérifier |
|---|---|---|
| `spectrometer.init_args.monochromator.init_args.port` | `COM5` | port du SpectraPro (Gestionnaire de périphériques) |
| `spectrometer.init_args.camera.init_args.hardware_params` | `sensor_height: 256`, `roi_y0: 138`, `roi_height: 54` | capteur Pixis du poste |
| `spectrometer.init_args.calibration` | `calibrations/pixis_sp2300i.yaml` | bonne paire caméra / monochromateur |
| `arduino.init_args.port` | `COM9` | port de l'Arduino |
| `cryostat.driver` | `drivers.CryoPasqal.CryoPasqal` | `false` dans `enabled` si pas de cryostat |

Le port du cryostat Pasqal est écrit en dur dans `src/drivers/CryoPasqal.py`
(`ASRL9::INSTR`, soit COM9), pas dans `config.yaml`.

## 3. Logiciels à installer hors Python

| Logiciel | Version ici | Pour |
|---|---|---|
| Princeton Instruments **PICam** | 5.14.7.2311 | caméra Pixis (pylablib charge `Picam.dll` depuis `C:\Program Files\Princeton Instruments\PICam\Runtime`) |
| **NI-VISA** Runtime | 21.5.0 | cryostat Pasqal via pyvisa (`pyvisa-py` n'est pas installé, pyvisa utilise `C:\Windows\System32\visa32.dll`) |
| Thorlabs ThorSpectra (CCS) | 3.36 | seulement si un CCS200 est utilisé (`TLCCS_64.dll` est déjà dans le dépôt) |

Les DLL Stresing (`ESLSCDLL.dll` v4) et Meadowlark (SLM) sont fournies dans `src/drivers/`.

## 4. Dossiers

`C:\TEMP` (fichier tampon `temp.h5`) est créé automatiquement au premier enregistrement.

## Diagnostic rapide

```bash
conda run -n SilvaBot python -c "import PyQt5, pyqtgraph, yaml, h5py, scipy, pylablib, pyvisa, serial; print('imports OK')"
conda run -n SilvaBot python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"
conda run -n SilvaBot python -c "from pylablib.devices import PrincetonInstruments as PI; print(PI.list_cameras())"
```

Le premier doit afficher `imports OK`. Le deuxième doit lister `ASRL9::INSTR` si le cryostat est
branché. Le troisième doit lister le Pixis, sinon PICam est absent ou la caméra est occupée
(LightField ouvert).
