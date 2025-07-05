# NIKKE Lobby/Burst Mod Manager
A tool that uses a modified version of [anosu Spine Viewer](https://github.com/anosu/Spine-Viewer) to view [NIKKE](https://nikke-en.com/) Spine animations from modded bundles, and it works to manage your lobby/burst mods. The tool basically replaces original files with a copy of your modded files when you "activate" the mod, and it restores the original file replacing the copy of the modded file when you "deactivate" the mod.

### The script to download the viewer uses [NicKoehler's mediafire bulk downloader](https://github.com/NicKoehler/mediafire_bulk_downloader).


#### IMPORTANT: This mod manager works with a specific name structure for the modded files that is `[ID]-[skin_code]-[type]-[Author]-[ModName]` and for the event lobby files is `[ID]-[type]-[Author]-[ModName]`, examples:
```
c010-00-lobby-Swapper-EVESkin03SwapOverRapi
c162-01-lobby-Na0h-MiharaCake
c470-00-burst-Hiccup-RedHoodClothesLess
c470-00-lobby-Hiccup-RedHoodClothesLess
eventtitle_neverland_02-lobby-Na0h-NudeWaifusOnsen
```

To know how you should rename your event lobby mods go to the folder `AddressablesJSON` and check out the "ID" values in the JSON file `lobby_event_data.json`.

## Requirements to use the tool:

  - Double-click on _install_requirements.bat_ to install the required dependencies and Python 3.13.
  - Download and install [Microsoft C++ Build Tools](https://aka.ms/vs/17/release/vs_BuildTools.exe), and after that install the necessary dependencies following [this video guide](https://files.catbox.moe/vqsuix.mp4).
  
  NOTE: The requirements listed in "requirements.txt" are only for my GUI script, you will need to install the ones necessary for anosu's Spine Viewer separately (Electron, Node.js, etc) if you want to build the Spine viewer yourself. If you're not interested to build the Spine viewer then ignore this, the mod manager will download the portable version of the viewer ready for usage automatically when you install the requirements.




## Usage:

1. Go to your NMM **"mods"** folder and create a new folder **"lobby_burst"**.
2. Move your mods renamed to the specific name structure described above on this readme, to that created folder **"lobby_burst"**.

<img src="https://files.catbox.moe/6ia001.png" width="500"/>

3. Double-click on _NLBMM.pyw_ to launch the mod manager.
4. The manager will ask you for the path to your NMM **"lobby_burst"** folder path and the **"naps"** folder path, click OK on the message box.

<img src="https://files.catbox.moe/hbd3yl.png" width="300"/>

5. You will see this GUI:

<img src="https://files.catbox.moe/9clrj9.png" width="700"/>

6. Click on the Mods Folder `Browse...` button, navigate to your **"lobby_burst"** mods folder and select it.

<img src="https://files.catbox.moe/ftrm3x.png" width="500"/>

7. Click on the naps Folder `Browse...` button, navigate to your **"naps"** folder path and select it.

<img src="https://files.catbox.moe/ee34fb.png" width="500"/>

8. The mod manager will display the list with your mods like this:

<img src="https://files.catbox.moe/u13k8s.png" width="700"/>

9. The first time you set the paths the buttons will display kinda bugged, so just close the manager and relaunch it again to fix it:

<img src="https://files.catbox.moe/d9n5ui.png" width="700"/>

10. And that is it, you can start to use the manager now. Additionally you can create a shortcut for the manager on your Desktop doing double-click on _CREATE_SHORTCUT.bat_.


### Buttons:

`Preview`: Open the Spine viewer to load the Spine animation.

`Refresh Mods List`: If you renamed, moved or deleted the mods then use this button to refresh the mods list to display the changes.

`Activate/Deactivate`: Deactivate or activate mods.

`Clear`: Clear the search bar with one click.

`Search bar`: Useful to filter your mods list by author, mod name, etc.

<img src="https://files.catbox.moe/saceri.png" width="800"/>



