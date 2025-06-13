# NIKKE LobbyBurst Mod Manager
A tool that uses a modified version of [anosu Spine Viewer](https://github.com/anosu/Spine-Viewer) to view [NIKKE](https://nikke-en.com/) Spine animations from modded bundles, and it works to manage your lobby/burst mods. The tool basically replaces original files with a copy of your modded files when you "activate" the mod, and it restores the original file replacing the copy of the modded file when you "deactivate" the mod.


#### IMPORTANT: This mod manager works with a specific name structure for the modded files `[ID]_[skin_code]_[type]_[Author]_[ModName]`, examples:
```
c010_00_lobby_Swapper_EVESkin03SwapOverRapi
c162_01_lobby_Na0h_MiharaCake
c470_00_burst_Hiccup_RedHoodClothesLess
c470_00_lobby_Hiccup_RedHoodClothesLess
```



## Requirements to use the tool:

  - Double-click on _install_requirements.bat_ to install the required dependencies and Python 3.13.
  - Download and install [Microsoft C++ Build Tools](https://aka.ms/vs/17/release/vs_BuildTools.exe), and after that install the necessary dependencies following [this video guide](https://files.catbox.moe/vqsuix.mp4).
  
  NOTE: The requirements listed in "requirements.txt" are only for my GUI script, you will need to install the ones necessary for anosu's Spine Viewer separately (Electron, Node.js, etc) if you want to build the Spine viewer yourself.




## Usage:

1. Go to your NMM **"mods"** folder and create a new folder **"lobby_burst"**.
2. Move your mods renamed to the specific name structure described above on this readme, to that created folder **"lobby_burst"**.

<img src="https://files.catbox.moe/awq4yk.png" width="500"/>

3. Double-click on _LBMM.bat_ to launch the mod manager.
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



